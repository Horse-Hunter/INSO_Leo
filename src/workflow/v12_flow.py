"""Small fake-capable V1.2 coordinator around the unchanged V1.1 worker."""

from __future__ import annotations

import hashlib
import html
import sqlite3
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from src.research import ResearchInput, ResearchResult, ResearchStatus
from src.sheets import (
    PendingSheetRecord,
    SheetRecordIdentity,
    WorksheetIdentity,
    WorksheetRowReader,
    query_pending_records,
    usable_brand,
)
from src.sheets.brand_write import SheetRecordConflict
from src.sheets.purchase_status import current_purchase_status

from .service import ResearchExecutor, ResearchPreparationError, WorkflowWorker
from .store import WorkflowStateStore
from .v12_contracts import (
    EXECUTION_EVENT_TYPES,
    BusinessState,
    DuplicateCheckResult,
    DuplicateOutcome,
    EventType,
    NotificationCommand,
    NotificationKind,
    NotificationRecipient,
    PurchaseDraftCommand,
    PurchaseDraftResult,
    PurchaseOutcome,
    ReasonCode,
    WorkflowEvent,
    interrupted_business_state,
)
from .v12_faults import FaultScope, V12Fault
from .v12_notifications import V12NotificationWorker
from .v12_rules import (
    PostResearchRoute,
    PurchaseRoutingOutcome,
    build_ai_input,
    purchase_routing_decision,
    route_after_research,
    should_send_important_order_notification,
    validate_ai_recognition,
)
from .v12_store import V12DatabaseError, V12Store


@dataclass(frozen=True, slots=True)
class ResearchBusinessFacts:
    """Canonical V1.1 Research values needed by V1.2 decisions."""

    inventory_status: str
    estimated_total: Decimal | None
    market_minimum_reference_price: Decimal | None


class DuplicateChecker(Protocol):
    def check(
        self, inquiry_id: str, mpn: str, quantity: int, *, at: datetime
    ) -> DuplicateCheckResult: ...


class ResearchFactsProvider(Protocol):
    def get(self, inquiry_id: str) -> ResearchBusinessFacts | None: ...


class PurchaseDraftWriter(Protocol):
    """Prepare a draft; authorized production wiring may submit once."""

    def prepare(self, command: PurchaseDraftCommand) -> PurchaseDraftResult: ...


@dataclass(frozen=True, slots=True)
class V12FlowResult:
    inquiry_id: str
    business_state: BusinessState
    route: PostResearchRoute | None = None
    routing_outcome: PurchaseRoutingOutcome | None = None
    purchase_outcome: PurchaseOutcome | None = None
    waiting_reason: str | None = None


class FakePurchaseDraftWriter:
    """Pure fake AI recognition adapter. It cannot dispatch any INSO action."""

    def __init__(
        self,
        *,
        recognized_mpn: str | None = None,
        recognized_brand: str | None = None,
        recognized_quantity: int | None = None,
        completed_at: datetime,
    ) -> None:
        self._recognized = (recognized_mpn, recognized_brand, recognized_quantity)
        self._completed_at = completed_at
        self.commands: list[PurchaseDraftCommand] = []

    def prepare(self, command: PurchaseDraftCommand) -> PurchaseDraftResult:
        self.commands.append(command)
        mpn, brand, quantity = self._recognized
        if mpn is None and brand is None and quantity is None:
            mpn, brand, quantity = command.mpn, command.brand, command.quantity
        return validate_ai_recognition(
            command_id=command.command_id,
            completed_at=self._completed_at,
            expected_mpn=command.mpn,
            expected_brand=command.brand,
            expected_quantity=command.quantity,
            recognized_mpn=mpn,
            recognized_brand=brand,
            recognized_quantity=quantity,
        )


class V12WorkflowCoordinator:
    """Run V1.2 decisions while delegating Research execution to V1.1."""

    def __init__(
        self,
        workflow_store: WorkflowStateStore,
        v12_store: V12Store,
        research: ResearchExecutor,
        duplicate_checker: DuplicateChecker,
        research_facts: ResearchFactsProvider,
        purchase_writer: PurchaseDraftWriter,
        notification_worker: V12NotificationWorker,
        recipients: tuple[NotificationRecipient, ...],
        *,
        stop_requested: Callable[[], bool] | None = None,
        on_result: Callable[[V12FlowResult], None] | None = None,
        inquiry_ids: frozenset[str] | None = None,
        row_wait: Callable[[float], bool] | None = None,
    ) -> None:
        self._workflow_store = workflow_store
        self._v12_store = v12_store
        self._research = research
        self._duplicate_checker = duplicate_checker
        self._research_facts = research_facts
        self._purchase_writer = purchase_writer
        self._notification_worker = notification_worker
        self._recipients = recipients
        self._stop_requested = stop_requested or (lambda: False)
        self._on_result = on_result
        self._inquiry_ids = inquiry_ids
        self._row_wait = row_wait or (lambda _seconds: False)
        self._row_closed = False
        self.pending_rows_seen = 0
        self._records: dict[str, PendingSheetRecord] = {}
        self._duplicate_results: dict[str, DuplicateCheckResult] = {}
        self._research_results: dict[str, ResearchResult] = {}
        self._last_inquiry_id: str | None = None
        self._current_reader = None

    def begin_poll_cycle(self) -> None:
        self._row_closed = False
        self.pending_rows_seen = 0

    def rerun_unsubmitted(self, inquiry_id, record, reader, *, now):
        """Explicit Owner retry through the original coordinator and submit guard."""
        item = self._workflow_store.get_by_inquiry_id(inquiry_id)
        if (record.status != "未发" or record.record_identity.worksheet != item.record_identity.worksheet
                or record.row_position != item.record_identity.row_position):
            raise ValueError("source row/status does not allow purchase retry")
        if not self._v12_store.manual_purchase_retry_allowed(inquiry_id):
            raise ValueError("purchase retry is unsafe")
        if not self._workflow_store.revive_item(item.id, record, now=now, manual_retry=True):
            raise ValueError("inquiry is still running")
        self._v12_store.reset_unsubmitted_purchase_for_manual_retry(inquiry_id)
        self._set_state(inquiry_id, BusinessState.QUEUED, EventType.HUMAN_RESOLUTION_RECORDED, now)
        self._research_results.pop(inquiry_id, None)
        self._duplicate_results.pop(inquiry_id, None)
        self._current_reader = reader
        self.begin_poll_cycle()
        return self.process_pending((record,), now=now)

    def _before_next_row(self) -> bool:
        if self._row_closed and self._row_wait(120):
            return False
        self._row_closed = False
        return not self._stop_requested()

    def initialize_run_state(self, *, now: datetime) -> None:
        """Quarantine prior unfinished work; never automatically resume it."""
        for item in self._workflow_store.all_items():
            try:
                state = self._v12_store.business_state(item.inquiry_id)
            except KeyError:
                state = None
            events = self._v12_store.event_history(item.inquiry_id)
            armed = any(e.event_type in {EventType.SAVE_DISPATCH_ARMED, EventType.SAVE_CLICK_COMPLETED} for e in events)
            try:
                purchase = self._v12_store.purchase_state(item.inquiry_id)
            except KeyError:
                purchase = None
            interrupted = interrupted_business_state(state, purchase, armed,
                execution_started=(item.status.value == "RESEARCHING" or item.attempt_count > 0
                    or any(e.event_type in EXECUTION_EVENT_TYPES for e in events)))
            if interrupted is None or interrupted is state:
                continue
            self._workflow_store.mark_interrupted(item.id, now=now)
            self._set_state(item.inquiry_id, interrupted,
                EventType.HUMAN_RESOLUTION_RECORDED, now)
    def run_notifications(self, *, now: datetime) -> int:
        """Deliver due commands independently of the purchase workflow."""

        return self._notification_worker.run_due(now=now)

    def poll_and_process(
        self,
        reader: WorksheetRowReader,
        worksheet: WorksheetIdentity,
        *,
        now: datetime,
    ) -> tuple[V12FlowResult, ...]:
        """Read pending rows through the existing Sheets schema and process fakes."""

        self._current_reader = reader
        records = query_pending_records(reader, worksheet)
        self.pending_rows_seen += len(records)
        for item in self._workflow_store.all_items():
            if item.record_identity.worksheet != worksheet:
                continue
            try:
                state = self._v12_store.business_state(item.inquiry_id)
            except KeyError:
                continue
            if state in {BusinessState.INTERRUPTED_UNSENT, BusinessState.INTERRUPTED_POSSIBLY_SENT}:
                try:
                    if current_purchase_status(reader, item.record_identity) == "发给采购":
                        self._set_state(item.inquiry_id, BusinessState.HUMAN_COMPLETED,
                            EventType.HUMAN_RESOLUTION_RECORDED, now)
                except SheetRecordConflict:
                    pass
        # Row movement preserves the existing inquiry_id, never creates another purchase.
        existing = self._workflow_store.all_items()
        normalized = []
        for record in records:
            matches = [i for i in existing if i.record_identity.worksheet == worksheet
                and i.record_identity.identifying_snapshot == record.record_identity.identifying_snapshot]
            if len(matches) == 1:
                record = replace(record, record_identity=matches[0].record_identity)
            normalized.append(record)
        return self.process_pending(tuple(normalized), now=now)

    def process_pending(
        self, records: tuple[PendingSheetRecord, ...], *, now: datetime
    ) -> tuple[V12FlowResult, ...]:
        enqueued: list[PendingSheetRecord] = []
        if self._inquiry_ids is not None:
            records = tuple(record for record in records
                            if self._workflow_store.inquiry_id_for(record.record_identity) in self._inquiry_ids)
        skipped: list[V12FlowResult] = []
        held: dict[str, str | None] = {}
        # Owner rule: a row whose quantity cell is not a number (a column
        # legend, a blank, a textual placeholder) is not an inquiry. It is held
        # out of the workflow with its own recorded reason instead of being
        # researched and drafted, and correcting the worksheet lets it resume
        # through the normal queue.
        #
        # The row is queued before it is held back: V1.2 state, events and
        # alerts are keyed to the queue's inquiry identity, so a reason can only
        # be recorded for a row the queue already knows about.
        for record in records:
            inquiry_id = self._workflow_store.inquiry_id_for(record.record_identity)
            enqueued_now = self._workflow_store.enqueue(record, now=now)
            if not enqueued_now and not self._is_skipped(inquiry_id):
                existing = self._workflow_store.get_by_inquiry_id(inquiry_id)
                if existing.record_identity.identifying_snapshot != record.record_identity.identifying_snapshot:
                    self._workflow_store.mark_interrupted(existing.id, now=now)
                    self._set_state(inquiry_id, BusinessState.SOURCE_CHANGED, EventType.SECURITY_CHECK_FAILED, now)
                    held[inquiry_id] = "SOURCE_CHANGED"
                    continue
            if (_quantity(record.quantity) is not None and isinstance(record.model, str)
                    and record.model.strip() and usable_brand(record.brand) and _tier(record.importance_raw)):
                if not enqueued_now and self._is_skipped(inquiry_id):
                    self._resume_after_input_fix(inquiry_id, record, now=now)
                if enqueued_now:
                    enqueued.append(record)
                continue
            item = self._workflow_store.get_by_inquiry_id(inquiry_id)
            demoted = self._workflow_store.mark_skipped_input(item.id, now=now)
            if demoted and not self._is_skipped(inquiry_id):
                self._v12_store.skip_invalid_quantity(inquiry_id, at=now,
                    reason_code=(ReasonCode.INQUIRY_QUANTITY_INVALID if _quantity(record.quantity) is None
                        else ReasonCode.INQUIRY_INPUT_INVALID))
            if demoted and self._is_skipped(inquiry_id):
                held[inquiry_id] = "INVALID_QUANTITY_SKIPPED"

        by_row = {
            _row_key(item.record_identity): item
            for item in self._workflow_store.all_items()
        }
        # A freshly read row supplies the routing facts for a new inquiry and
        # equally for one that an earlier poll released back to the queue.
        for record in records:
            item = by_row.get(_row_key(record.record_identity))
            if item is not None:
                self._records[item.inquiry_id] = record

        for record in enqueued:
            item = by_row[_row_key(record.record_identity)]
            self._set_state(
                item.inquiry_id,
                BusinessState.DUPLICATE_CHECK_PENDING,
                EventType.DUPLICATE_CHECK_STARTED,
                now,
            )
            self._v12_store.record_customer_snapshot(
                item.inquiry_id,
                record.customer_name,
                record.customer_name_source,
                at=now,
            )

        wrapped_research = _DuplicateThenResearch(self, now)
        worker = WorkflowWorker(self._workflow_store, wrapped_research)
        results: list[V12FlowResult] = list(skipped)
        # The durable queue is the only bound on this drain. Bounding it to the
        # rows this poll inserted stranded every inquiry an earlier poll had
        # released (for example while the production INSO session needed manual
        # handling), so its post-Research routing could never run again.
        remaining = {
            item.inquiry_id
            for item in by_row.values()
            if item.status.value in {"QUEUED", "RETRY_WAIT"}
            and item.inquiry_id in {self._workflow_store.inquiry_id_for(r.record_identity) for r in records}
            and not self._is_skipped(item.inquiry_id)
            and self._v12_store.business_state(item.inquiry_id) not in {
                BusinessState.INTERRUPTED_UNSENT, BusinessState.INTERRUPTED_POSSIBLY_SENT,
                BusinessState.HUMAN_COMPLETED, BusinessState.SOURCE_CHANGED,
            }
            and (self._inquiry_ids is None or item.inquiry_id in self._inquiry_ids)
        }
        remaining.update(held)
        ordered = list(dict.fromkeys(self._workflow_store.inquiry_id_for(r.record_identity)
            for r in sorted(records, key=lambda r: r.row_position)))
        while remaining and not self._stop_requested():
            if not ordered:
                break
            selected = ordered.pop(0)
            if selected not in remaining:
                continue
            if selected in held:
                if not self._before_next_row():
                    break
                remaining.remove(selected)
                results.append(self._result(selected, waiting_reason=held[selected]))
                continue
            due = [i for i in self._workflow_store.all_items() if i.inquiry_id in remaining
                   and i.inquiry_id == selected
                   and i.status.value in {"QUEUED", "RETRY_WAIT"}
                   and i.next_attempt_at is not None and i.next_attempt_at <= now]
            if not due:
                remaining.remove(selected)
                continue
            if not self._before_next_row():
                break
            item = worker.process_due_one(now=now, inquiry_ids=frozenset({selected}))
            if item is None:
                break
            inquiry_id = wrapped_research.last_inquiry_id
            if inquiry_id is None or inquiry_id not in remaining:
                break
            remaining.remove(inquiry_id)
            research_result = self._research_results.get(inquiry_id)
            if item.status.value in {"RETRY_WAIT", "RESEARCHING", "QUEUED"}:
                if research_result is not None and research_result.status is ResearchStatus.RETRYABLE_FAILURE:
                    self._notify_a_if_nonduplicate(inquiry_id, research_result, now)
                    self._workflow_store.finish_row_failure(item.id,
                        research_result.reason_code.value if research_result.reason_code else "RESEARCH_SOURCE_FAILURE", now=now)
                    self._set_state(inquiry_id, BusinessState.RESEARCH_FAILED, EventType.RESEARCH_FAILED, now)
                    results.append(self._result(inquiry_id, waiting_reason="RESEARCH_NOT_SUCCESSFUL"))
                    continue
                if research_result is not None:
                    self._notify_a_if_nonduplicate(inquiry_id, research_result, now)
                self._set_state(
                    inquiry_id,
                    BusinessState.RESEARCH_RETRY_WAIT,
                    EventType.RESEARCH_RETRY_SCHEDULED,
                    now,
                )
                results.append(
                    self._result(
                        inquiry_id,
                        waiting_reason="RESEARCH_RETRY_WAIT",
                    )
                )
            elif research_result is not None:
                results.append(self._route_after_research(inquiry_id, research_result, now))
        # The existing explicit recovery entry point already knows how to use
        # persisted Research. Wire it into the normal pending-row poll rather
        # than requeueing/deleting completed work or researching it again.
        for record in records:
            if self._stop_requested():
                break
            item = by_row.get(_row_key(record.record_identity))
            if (
                item is None or item.status.value != "COMPLETED"
                or item.record_identity.identifying_snapshot != record.record_identity.identifying_snapshot
                or not self._v12_store.duplicate_confirmation_pending(item.inquiry_id)
            ):
                continue
            try:
                if not self._before_next_row():
                    break
                confirmed = self._duplicate_checker.check(
                    item.inquiry_id, item.mpn, int(item.quantity), at=now
                )
            except Exception:  # noqa: BLE001 - a failed retry cannot be a negative answer
                confirmed = None
            if (
                isinstance(confirmed, DuplicateCheckResult)
                and confirmed.inquiry_id == item.inquiry_id
                and confirmed.outcome is DuplicateOutcome.CONFIRMED
                and not self._stop_requested()
            ):
                results.append(self.confirm_duplicate_and_route(
                    item.inquiry_id, confirmed, now=now, record=record
                ))
        return tuple(results)

    def confirm_duplicate_and_route(
        self,
        inquiry_id: str,
        result: DuplicateCheckResult,
        *,
        now: datetime,
        record: PendingSheetRecord | None = None,
        research_result: ResearchResult | None = None,
    ) -> V12FlowResult:
        """Resume a persisted route without executing Research a second time."""

        if result.inquiry_id != inquiry_id or result.outcome is not DuplicateOutcome.CONFIRMED:
            raise ValueError("routing requires a matching confirmed duplicate result")
        if self._v12_store.business_state(inquiry_id) is not BusinessState.ROUTING:
            raise ValueError("inquiry is not waiting for post-Research routing")
        record = record or self._records.get(inquiry_id) or self._pending_record(inquiry_id)
        research_result = research_result or self._research_results.get(inquiry_id)
        if research_result is None:
            item = self._workflow_store.get_by_inquiry_id(inquiry_id)
            if item.research_status is None:
                raise ValueError("completed Research result is not available")
            try:
                status = ResearchStatus(item.research_status)
            except ValueError as exc:
                raise ValueError("completed Research result is invalid") from exc
            research_result = ResearchResult(
                inquiry_id, status, resolved_brand=item.resolved_brand
            )
        self._records[inquiry_id] = record
        self._research_results[inquiry_id] = research_result
        self._duplicate_results[inquiry_id] = result
        self._v12_store.record_duplicate_result(result)
        return self._route_after_research(inquiry_id, research_result, now)

    def _pending_record(self, inquiry_id: str) -> PendingSheetRecord:
        item = self._workflow_store.get_by_inquiry_id(inquiry_id)
        customer_name, customer_source = self._v12_store.customer_snapshot(inquiry_id)
        snapshot = item.record_identity.identifying_snapshot
        return PendingSheetRecord(
            status=snapshot.status,
            importance_raw=item.importance_raw,
            model=item.mpn,
            brand=item.brand,
            quantity=item.quantity,
            row_position=item.record_identity.row_position,
            record_identity=item.record_identity,
            customer_name=customer_name,
            customer_name_source=customer_source,
        )

    def _check_duplicate(self, research_input: ResearchInput, *, at: datetime) -> None:
        inquiry_id = research_input.inquiry_id
        self._last_inquiry_id = inquiry_id
        self._set_state(
            inquiry_id,
            BusinessState.DUPLICATE_CHECKING,
            EventType.DUPLICATE_CHECK_STARTED,
            at,
        )
        try:
            result = self._duplicate_checker.check(
                inquiry_id,
                research_input.mpn,
                int(research_input.quantity),
                at=at,
            )
            if (
                not isinstance(result, DuplicateCheckResult)
                or result.inquiry_id != inquiry_id
            ):
                raise ValueError("duplicate result identity is invalid")
        except V12Fault:
            raise
        except (sqlite3.Error, V12DatabaseError) as exc:
            raise V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE") from exc
        except Exception:  # noqa: BLE001 - no lookup error becomes a negative result
            result = DuplicateCheckResult(
                inquiry_id,
                DuplicateOutcome.UNAVAILABLE,
                str(research_input.mpn),
                at,
                reason_code=ReasonCode.DUPLICATE_LOOKUP_UNAVAILABLE,
            )
        self._duplicate_results[inquiry_id] = result
        self._v12_store.record_duplicate_result(result)
        self._set_state(
            inquiry_id,
            BusinessState.RESEARCHING,
            EventType.RESEARCH_STARTED,
            at,
        )

    def _route_after_research(
        self, inquiry_id: str, research_result: ResearchResult, now: datetime
    ) -> V12FlowResult:
        try:
            previous_purchase = self._v12_store.purchase_state(inquiry_id)
        except KeyError:
            pass
        else:
            # Repeated polling/recovery must not reopen any existing purchase.
            return self._result(
                inquiry_id, purchase_outcome=previous_purchase,
                waiting_reason="PURCHASE_ALREADY_ATTEMPTED",
            )
        duplicate_result = self._duplicate_results[inquiry_id]
        route = route_after_research(duplicate_result)
        if route is PostResearchRoute.DUPLICATE_CONFIRMATION_REQUIRED:
            self._set_state(
                inquiry_id,
                BusinessState.ROUTING,
                EventType.DUPLICATE_CHECK_FAILED,
                now,
                duplicate_result.reason_code or ReasonCode.DUPLICATE_LOOKUP_UNAVAILABLE,
            )
            return self._result(inquiry_id, route=route, waiting_reason="DUPLICATE_CONFIRMATION_REQUIRED")
        if route is PostResearchRoute.DUPLICATE_STOP:
            self._set_state(inquiry_id, BusinessState.DUPLICATE_STOPPED, EventType.DUPLICATE_ORDER_DETECTED, now, ReasonCode.DUPLICATE_ORDER_DETECTED)
            self._enqueue_notification(
                inquiry_id,
                NotificationKind.DUPLICATE_ORDER,
                research_result,
                now,
                duplicate_result=duplicate_result,
            )
            return self._result(inquiry_id, route=route)
        self._notify_a_if_nonduplicate(inquiry_id, research_result, now)
        if research_result.status not in {ResearchStatus.SUCCESS, ResearchStatus.PARTIAL_SUCCESS}:
            self._set_state(inquiry_id, BusinessState.RESEARCH_FAILED, EventType.RESEARCH_FAILED, now)
            return self._result(inquiry_id, route=route, waiting_reason="RESEARCH_NOT_SUCCESSFUL")

        record = self._records.get(inquiry_id) or self._pending_record(inquiry_id)
        facts = self._research_facts.get(inquiry_id)
        tier = _tier(record.importance_raw)
        if facts is None or tier not in {"A", "B", "C"}:
            self._set_state(inquiry_id, BusinessState.ROUTING, EventType.IMPORTANT_ORDER_DECIDED, now)
            return self._result(inquiry_id, route=route, waiting_reason="RESEARCH_FACTS_OR_TIER_UNKNOWN")

        if should_send_important_order_notification(
            tier=tier,
            estimated_total=facts.estimated_total,
            inventory_status=facts.inventory_status,
        ):
            self._enqueue_notification(
                inquiry_id,
                NotificationKind.IMPORTANT_ORDER,
                research_result,
                now,
                facts=facts,
                tier=tier,
            )

        purchase_decision = purchase_routing_decision(
            tier=tier, estimated_total=facts.estimated_total
        )
        if purchase_decision.outcome is PurchaseRoutingOutcome.INDETERMINATE:
            self._set_state(inquiry_id, BusinessState.ROUTING, EventType.IMPORTANT_ORDER_DECIDED, now)
            return self._result(
                inquiry_id,
                route=route,
                routing_outcome=PurchaseRoutingOutcome.INDETERMINATE,
                waiting_reason="PURCHASE_ROUTING_INDETERMINATE",
            )

        quantity = _quantity(record.quantity)
        mpn = record.model.strip() if isinstance(record.model, str) else ""
        brand = research_result.resolved_brand or usable_brand(record.brand) or ""
        if self._current_reader is not None:
            try:
                if current_purchase_status(self._current_reader, record.record_identity) != "未发":
                    raise SheetRecordConflict("source status changed")
            except SheetRecordConflict:
                self._set_state(inquiry_id, BusinessState.SOURCE_CHANGED, EventType.SECURITY_CHECK_FAILED, now)
                return self._result(inquiry_id, waiting_reason="SOURCE_CHANGED")
        if quantity is None or not mpn or not brand.strip():
            self._set_state(inquiry_id, BusinessState.PURCHASE_EXCEPTION, EventType.SECURITY_CHECK_FAILED, now, ReasonCode.AI_RECOGNITION_MISMATCH)
            return self._result(inquiry_id, route=route, waiting_reason="PURCHASE_INPUT_INVALID")

        command_id = _command_id(inquiry_id, "purchase")
        command = PurchaseDraftCommand(
            command_id=command_id,
            inquiry_id=inquiry_id,
            customer_name=record.customer_name,
            customer_tier=tier,
            mpn=mpn,
            brand=brand.strip(),
            quantity=quantity,
            inventory_status=facts.inventory_status,
            estimated_total=facts.estimated_total,
            market_minimum_reference_price=facts.market_minimum_reference_price,
            quotation_type=purchase_decision.quotation_type.value,
            purchaser=purchase_decision.purchaser.value,
            ai_input=build_ai_input(mpn, brand.strip(), quantity),
        )
        self._set_state(inquiry_id, BusinessState.PURCHASE_DRAFT_PENDING, EventType.PURCHASE_DRAFT_STARTED, now)
        self._set_state(inquiry_id, BusinessState.PURCHASE_DRAFTING, EventType.PURCHASE_DRAFT_STARTED, now)
        self._v12_store.set_purchase_state(
            inquiry_id, command_id, PurchaseOutcome.PRE_SAVE_READY, at=now
        )
        try:
            result = self._purchase_writer.prepare(command)
        except (V12Fault, sqlite3.Error, V12DatabaseError):
            raise
        except Exception:
            if self._v12_store.purchase_state(inquiry_id) is not PurchaseOutcome.PRE_SAVE_READY:
                raise
            result = PurchaseDraftResult(command_id, PurchaseOutcome.VALIDATION_FAILED, now,
                reason_code=ReasonCode.CONTROL_NOT_FOUND)
        if result.command_id != command_id or result.outcome not in {
            PurchaseOutcome.AI_RECOGNIZED,
            PurchaseOutcome.VALIDATION_FAILED,
            PurchaseOutcome.SAVED,
            PurchaseOutcome.UNKNOWN_WRITE_OUTCOME,
            PurchaseOutcome.READ_ONLY_RECONCILIATION_REQUIRED,
            PurchaseOutcome.MANUAL_REVIEW,
            PurchaseOutcome.SUBMIT_UNCONFIRMED,
        }:
            result = PurchaseDraftResult(
                command_id, PurchaseOutcome.VALIDATION_FAILED, now,
                reason_code=ReasonCode.AI_RECOGNITION_MISMATCH,
            )
        if result.outcome in {PurchaseOutcome.AI_RECOGNIZED, PurchaseOutcome.VALIDATION_FAILED}:
            self._v12_store.set_purchase_state(
                inquiry_id, command_id, result.outcome,
                at=result.completed_at, reason_code=result.reason_code,
            )
        elif self._v12_store.purchase_state(inquiry_id) is not result.outcome:
            raise ValueError("submission outcome is not durably recorded")
        if result.outcome is PurchaseOutcome.SAVED:
            self._set_state(
                inquiry_id, BusinessState.PURCHASE_RECORDED,
                EventType.PURCHASE_DATA_SAVED, result.completed_at,
            )
        elif result.outcome is PurchaseOutcome.SUBMIT_UNCONFIRMED:
            self._set_state(inquiry_id, BusinessState.SUBMIT_UNCONFIRMED,
                EventType.SAVE_OUTCOME_UNKNOWN, result.completed_at, ReasonCode.SAVE_OUTCOME_UNKNOWN)
        elif result.outcome not in {PurchaseOutcome.AI_RECOGNIZED, PurchaseOutcome.VALIDATION_FAILED}:
            self._set_state(
                inquiry_id, BusinessState.PURCHASE_EXCEPTION,
                EventType.SAVE_OUTCOME_UNKNOWN, result.completed_at,
                ReasonCode.SAVE_OUTCOME_UNKNOWN,
            )
        if result.outcome is PurchaseOutcome.VALIDATION_FAILED:
            self._set_state(
                inquiry_id,
                BusinessState.PURCHASE_EXCEPTION,
                EventType.AI_RECOGNITION_MISMATCH,
                result.completed_at,
                ReasonCode.AI_RECOGNITION_MISMATCH,
            )
        return self._result(
            inquiry_id,
            route=route,
            routing_outcome=PurchaseRoutingOutcome.READY,
            purchase_outcome=result.outcome,
        )

    def _notify_a_if_nonduplicate(self, inquiry_id, research_result, now) -> None:
        duplicate = self._duplicate_results.get(inquiry_id)
        if (duplicate is None or duplicate.outcome is not DuplicateOutcome.CONFIRMED
                or duplicate.repeated is not False):
            return
        record = self._records.get(inquiry_id) or self._pending_record(inquiry_id)
        if _tier(record.importance_raw) == "A":
            self._enqueue_notification(
                inquiry_id, NotificationKind.IMPORTANT_ORDER, research_result, now,
                facts=self._research_facts.get(inquiry_id), tier="A",
            )

    def _enqueue_notification(
        self,
        inquiry_id: str,
        kind: NotificationKind,
        research_result: ResearchResult,
        now: datetime,
        *,
        facts: ResearchBusinessFacts | None = None,
        tier: str | None = None,
        duplicate_result: DuplicateCheckResult | None = None,
    ) -> None:
        # Resolve the row exactly like routing does: the durable queue, not this
        # poll's Sheet snapshot, decides what is processed, so an inquiry can
        # legitimately reach notification without a fresh row in ``_records``.
        # Indexing ``_records`` directly turned that into a KeyError that stopped
        # the whole runtime.
        command_id = _command_id(inquiry_id, kind.value.lower())
        if self._v12_store.notification_already_created(
            command_id, inquiry_id, kind, self._recipients,
        ):
            # Preserve original content through research retries; the delivery
            # worker alone retries pending recipients and never resends SENT.
            return
        record = self._records.get(inquiry_id) or self._pending_record(inquiry_id)
        if facts is None:
            facts = self._research_facts.get(inquiry_id)
        subject, body = _notification_content(
            kind, record, research_result, facts, tier, duplicate_result
        )
        command = NotificationCommand(
            command_id,
            inquiry_id,
            kind,
            self._recipients,
            subject,
            body,
            f"<html><body><pre>{html.escape(body)}</pre></body></html>",
            now,
        )
        self._v12_store.enqueue_notification(command)

    def _is_skipped(self, inquiry_id: str) -> bool:
        """Report whether this inquiry is currently held out of the workflow."""

        try:
            state = self._v12_store.business_state(inquiry_id)
        except KeyError:
            return False
        return state is BusinessState.INVALID_INPUT_SKIPPED

    def _resume_after_input_fix(
        self, inquiry_id: str, record: PendingSheetRecord, *, now: datetime
    ) -> None:
        """Re-open an inquiry whose worksheet row became valid again.

        The earlier skip was a data problem, not a business failure, so the row
        returns to the queue with its retry budget intact.
        """

        try:
            item = self._workflow_store.get_by_inquiry_id(inquiry_id)
        except KeyError:
            pass
        else:
            self._workflow_store.revive_item(item.id, record, now=now)
        self._set_state(
            inquiry_id,
            BusinessState.QUEUED,
            EventType.HUMAN_RESOLUTION_RECORDED,
            now,
        )

    def _set_state(
        self,
        inquiry_id: str,
        state: BusinessState,
        event_type: EventType,
        at: datetime,
        reason_code: ReasonCode | None = None,
    ) -> None:
        self._v12_store.set_business_state(
            inquiry_id,
            state,
            WorkflowEvent(
                f"evt_{uuid.uuid4().hex}",
                inquiry_id,
                event_type,
                at,
                "workflow",
                reason_code,
            ),
        )

    def _result(
        self,
        inquiry_id: str,
        *,
        route: PostResearchRoute | None = None,
        routing_outcome: PurchaseRoutingOutcome | None = None,
        purchase_outcome: PurchaseOutcome | None = None,
        waiting_reason: str | None = None,
    ) -> V12FlowResult:
        result = V12FlowResult(
            inquiry_id,
            self._v12_store.business_state(inquiry_id),
            route,
            routing_outcome,
            purchase_outcome,
            waiting_reason,
        )
        if self._on_result is not None:
            self._on_result(result)
        self._row_closed = waiting_reason not in {"RESEARCH_RETRY_WAIT", "DUPLICATE_CONFIRMATION_REQUIRED"}
        return result


class _DuplicateThenResearch:
    def __init__(self, coordinator: V12WorkflowCoordinator, at: datetime) -> None:
        self.coordinator = coordinator
        self.at = at
        self.last_inquiry_id: str | None = None

    def execute(self, research_input: ResearchInput) -> ResearchResult:
        self.last_inquiry_id = research_input.inquiry_id
        self.coordinator._check_duplicate(research_input, at=self.at)
        try:
            result = self.coordinator._research.execute(research_input)
        except ResearchPreparationError:
            self.coordinator._set_state(
                research_input.inquiry_id, BusinessState.RESEARCH_RETRY_WAIT,
                EventType.RESEARCH_RETRY_SCHEDULED, self.at,
            )
            raise
        self.coordinator._research_results[research_input.inquiry_id] = result
        return result


def _tier(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    return "A" if normalized == "S" else normalized if normalized in {"A", "B", "C"} else None


def _quantity_is_numeric(value: object) -> bool:
    """Report whether a worksheet quantity cell holds a number at all.

    Owner rule: only a cell that is *not* a number is invalid input and is
    skipped. This deliberately does not reuse :func:`_quantity`, which also
    rejects zero and negatives; those keep their existing downstream handling.
    """

    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    return isinstance(value, str) and value.strip().isdecimal()


def _quantity(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.strip().isdecimal():
        parsed = int(value.strip())
        return parsed if parsed > 0 else None
    return None


def _row_key(identity: SheetRecordIdentity) -> tuple[str, str, int]:
    """Match the store's own uniqueness key, not the mutable cell snapshot."""

    return (
        identity.worksheet.spreadsheet,
        identity.worksheet.worksheet,
        identity.row_position,
    )


def _command_id(inquiry_id: str, purpose: str) -> str:
    digest = hashlib.sha256(f"{inquiry_id}:{purpose}".encode()).hexdigest()[:32]
    return f"v12_{digest}"


def _notification_content(
    kind: NotificationKind,
    record: PendingSheetRecord,
    research_result: ResearchResult,
    facts: ResearchBusinessFacts | None,
    tier: str | None,
    duplicate_result: DuplicateCheckResult | None,
) -> tuple[str, str]:
    model = record.model if isinstance(record.model, str) else "--"
    brand = research_result.resolved_brand or (record.brand if isinstance(record.brand, str) else "--")
    quantity = _quantity(record.quantity)
    customer = record.customer_name or "客户名称缺失"
    stock = facts.inventory_status if facts is not None else "待验证"
    market_price = _money(facts.market_minimum_reference_price) if facts else "--"
    total = _money(facts.estimated_total) if facts else "--"
    if kind is NotificationKind.IMPORTANT_ORDER:
        subject = f"【重要订单】【{tier}】{customer}｜{model}｜¥{total}｜{stock}"
        body = "\n".join((
            f"客户名称：{customer}", f"客户等级：{tier}", f"型号：{model}",
            f"品牌：{brand}", f"数量：{quantity if quantity is not None else '--'}",
            f"库存状态：{stock}", f"市场最低参考价：{market_price}",
            f"预估订单总价：{total}", "触发原因：重要订单规则命中", "请及时人工跟进该订单",
        ))
        return subject, body

    duplicate_details = "历史记录：待核对"
    if duplicate_result is not None:
        historical_date = (
            duplicate_result.historical_date.isoformat()
            if duplicate_result.historical_date is not None
            else "--"
        )
        history_quantity = duplicate_result.historical_quantity
        quantity_match = {
            True: "数量相等",
            False: "数量不相等",
            None: "数量关系待核对",
        }[duplicate_result.quantity_equal]
        quote = duplicate_result.inso_quote
        order_total = (
            _money(quote * quantity)
            if quote is not None and quantity is not None
            else "--"
        )
        duplicate_details = "\n".join((
            f"最近一笔 INSO 历史：日期={historical_date}；历史数量={history_quantity if history_quantity is not None else '--'}；{quantity_match}",
            f"制单人：{duplicate_result.creator or '--'}；INSO报价：{_money(quote)} {duplicate_result.currency or ''}".rstrip(),
            f"本次数量 × INSO报价 = {order_total}",
        ))
    duplicate_details += f"\nResearch库存：{stock}；市场参考价：{market_price}；预估总价：{total}"
    subject = f"【INSO重复订单】{customer}｜{model}"
    body = "\n".join((
        f"本次订单：客户={customer}；型号={model}；品牌={brand}；数量={quantity if quantity is not None else '--'}",
        duplicate_details,
        "请及时人工跟进该订单。",
    ))
    return subject, body


def _money(value: Decimal | None) -> str:
    return "--" if value is None else f"{value:,.2f}"
