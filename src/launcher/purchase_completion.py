"""Completion side effects, separate from irreversible INSO dispatch."""
import logging
import uuid
from datetime import UTC, datetime
from functools import partial

from src.sheets.purchase_status import (
    purchase_status_satisfied,
    write_purchase_status_safely,
)
from src.workflow.v12_contracts import (
    BusinessState,
    EventType,
    NotificationCommand,
    NotificationKind,
    NotificationRecipient,
    PurchaseOutcome,
    WorkflowEvent,
)

log = logging.getLogger(__name__)

from src.workflow.v12_safety import BrandPolicy, brand_matches
from src.workflow.v13_quotation import expected_source_brand

SOURCE_BRAND_MATCH = partial(brand_matches, policy=BrandPolicy.AI_BRAND_V1)

OWNER = NotificationRecipient("owner", "linan229@qq.com")


class PurchaseCompletionActions:
    def __init__(self, *, workflow_store, v12_store, reader, writer_factory, clock=None, follow_up_store=None, mail_evidence=None, automatic_admission=lambda inquiry_id, at: False):
        self._automatic_admission = automatic_admission
        self._mail_evidence = mail_evidence
        self.workflow_store = workflow_store
        self.v12_store = v12_store
        self.reader = reader
        self.writer_factory = writer_factory
        self.follow_up_store = follow_up_store
        self._clock = clock or (lambda: datetime.now(UTC))
        self._settled_status_ids: set[str] = set()

    def process(self, result, *, at):
        item = self.workflow_store.get_by_inquiry_id(result.inquiry_id)
        if self.v12_store.business_state(item.inquiry_id) is BusinessState.STATUS_WRITE_PENDING:
            return True
        if result.purchase_outcome in {PurchaseOutcome.SAVED, PurchaseOutcome.SUBMIT_UNCONFIRMED}:
            if self.v12_store.purchase_state(item.inquiry_id) is not result.purchase_outcome:
                raise ValueError("purchase success is not durable")
            if result.purchase_outcome is PurchaseOutcome.SUBMIT_UNCONFIRMED:
                if not self.v12_store.submit_click_proven(item.inquiry_id):
                    raise ValueError("unconfirmed submit has no durable click proof")
                self.notify(item.inquiry_id, "PURCHASE", "SAVE_OUTCOME_UNKNOWN", at=at)
            return self._write_back(item, at=at)
        if result.business_state is BusinessState.PURCHASE_EXCEPTION:
            code = next((e.reason_code.value for e in reversed(self.v12_store.event_history(item.inquiry_id))
                         if e.reason_code is not None), "PURCHASE_EXCEPTION")
            self.notify(item.inquiry_id, "PURCHASE", code, at=at)
        elif item.status.value in {"FAILED", "MANUAL_REVIEW"} or result.waiting_reason == "RESEARCH_RETRY_WAIT":
            self.notify(item.inquiry_id, "RESEARCH", item.last_error or "RESEARCH_FAILED", at=at)
        elif result.waiting_reason == "DUPLICATE_CONFIRMATION_REQUIRED":
            self.notify(item.inquiry_id, "DUPLICATE_CHECK", "DUPLICATE_LOOKUP_UNAVAILABLE", at=at)
        elif result.business_state in {BusinessState.INVALID_INPUT_SKIPPED, BusinessState.SOURCE_CHANGED}:
            self.notify(item.inquiry_id, "PURCHASE", result.business_state.value, at=at)
        return result.purchase_outcome not in {
            PurchaseOutcome.UNKNOWN_WRITE_OUTCOME, PurchaseOutcome.MANUAL_REVIEW,
            PurchaseOutcome.READ_ONLY_RECONCILIATION_REQUIRED,
        }

    def _write_back(self, item, *, at):
        if not self._automatic_admission(item.inquiry_id, at):
            return True  # local exclusion; never a new failure or mail
        if item.inquiry_id in self._settled_status_ids:
            return True
        try:
            brand = expected_source_brand(item)
            if purchase_status_satisfied(self.reader, item.record_identity, expected_brand=brand, brand_match=SOURCE_BRAND_MATCH):
                changed = False
            else:
                changed = write_purchase_status_safely(self.reader, self.writer_factory(),
                    item.record_identity, expected_brand=brand, brand_match=SOURCE_BRAND_MATCH)
        except Exception as exc:  # noqa: BLE001 - retry only status, never purchase
            self.v12_store.set_business_state(item.inquiry_id, BusinessState.STATUS_WRITE_PENDING,
                WorkflowEvent(f"evt_{uuid.uuid4().hex}", item.inquiry_id,
                    EventType.HUMAN_RESOLUTION_RECORDED, at, "sheets"))
            self.notify(item.inquiry_id, "SHEETS_WRITE_BACK", type(exc).__name__, at=at)
            return True
        # This is outside the status-write exception handler: a failed local
        # ledger is GLOBAL_STOP, not STATUS_WRITE_PENDING or another purchase.
        if changed and self.follow_up_store is not None:
            self.follow_up_store.record_confirmed(item.inquiry_id, confirmed_at=self._clock())
        self._settled_status_ids.add(item.inquiry_id)
        return True

    def retry_saved_statuses(self, *, at):
        for item in self.workflow_store.all_items():
            if not self._automatic_admission(item.inquiry_id, at):
                continue
            if item.inquiry_id in self._settled_status_ids:
                continue
            pending = self.v12_store.business_state(item.inquiry_id) is BusinessState.STATUS_WRITE_PENDING
            try:
                saved = self.v12_store.purchase_state(item.inquiry_id) is PurchaseOutcome.SAVED
            except KeyError:
                continue
            if saved and pending:
                # A held status write never becomes another write or purchase.
                # Only a fresh source proof can resolve its local projection.
                try:
                    satisfied = purchase_status_satisfied(self.reader, item.record_identity,
                        expected_brand=expected_source_brand(item), brand_match=SOURCE_BRAND_MATCH)
                except Exception as exc:  # noqa: BLE001 - failed read retains the existing pending hold
                    log.warning("Pending purchase status remains unresolved (%s)", type(exc).__name__)
                    continue
                if satisfied:
                    self.v12_store.set_business_state(item.inquiry_id, BusinessState.PURCHASE_RECORDED,
                        WorkflowEvent(f"evt_{uuid.uuid4().hex}", item.inquiry_id,
                            EventType.HUMAN_RESOLUTION_RECORDED, at, "sheets"))
                    self._settled_status_ids.add(item.inquiry_id)
            elif saved:
                self._write_back(item, at=at)

    def notify(self, inquiry_id, phase, reason, *, at):
        command_id = f"purchase-exception:{inquiry_id}:{phase}:{reason}"
        recipients = (OWNER,)
        if phase == "RESEARCH" and reason == "NO_MATCHING_PRODUCT":
            recipients += (NotificationRecipient("ops", "shawn@inso-hk.com"),)
            # Old owner-only commands are immutable. Version only this changed payload.
            command_id += ":recipients-v2"
        if self.v12_store.notification_already_created(
            command_id, inquiry_id, NotificationKind.PURCHASE_EXCEPTION, recipients,
        ):
            return
        item = self.workflow_store.get_by_inquiry_id(inquiry_id)
        try:
            outcome = self.v12_store.purchase_state(inquiry_id)
        except KeyError:
            outcome = None
        uncertain = outcome in {
            PurchaseOutcome.SUBMIT_UNCONFIRMED,
            PurchaseOutcome.UNKNOWN_WRITE_OUTCOME, PurchaseOutcome.MANUAL_REVIEW,
            PurchaseOutcome.READ_ONLY_RECONCILIATION_REQUIRED,
        }
        # Technical errors stay in the local state/alerts. Only a durable unknown
        # external effect can justify this immediate actionable notification.
        if not uncertain or self._mail_evidence is None:
            return
        import json
        reason = "SAVE_OUTCOME_UNKNOWN"
        command_id = f"purchase-unknown:{inquiry_id}"
        proof = self._mail_evidence(inquiry_id, reason, at=at,
                                    event=command_id, module="inquiry")
        if proof is None:
            return
        command = NotificationCommand(command_id, inquiry_id, NotificationKind.PURCHASE_EXCEPTION,
            recipients, f"【需要处理】采购写入待人工核对：{item.mpn}",
            f"型号：{item.mpn}\n情况：写入结果待人工核实，原订单被保护不会自动重做。\n"
            "请核对原INSO记录，尚不能认定本次发送成功或失败；禁止直接重发。",
            None, at, 2, json.dumps(proof, sort_keys=True))
        self.v12_store.observe_incident(command, proof, occurrence=proof["original_event"])
