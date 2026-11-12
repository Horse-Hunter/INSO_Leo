"""Recipient-scoped V1.2 notification scheduling with a fake-only transport."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime
from threading import Lock, get_ident
from typing import Protocol

from .v12_contracts import (
    DeliveryOutcome,
    NotificationCommand,
    NotificationRecipient,
    NotificationTransportResult,
    ReasonCode,
)
from .v12_store import V12Store


class NotificationTransport(Protocol):
    def send_one(
        self,
        command: NotificationCommand,
        recipient: NotificationRecipient,
    ) -> NotificationTransportResult: ...


class FakeNotificationTransport:
    """Deterministic test adapter; has no SMTP or credential dependency."""

    def __init__(
        self,
        outcomes: Mapping[
            str, tuple[DeliveryOutcome | NotificationTransportResult, ...]
        ] = (),
    ) -> None:
        self._outcomes = {key: deque(value) for key, value in dict(outcomes).items()}
        self.calls: list[tuple[str, str]] = []

    def send_one(
        self,
        command: NotificationCommand,
        recipient: NotificationRecipient,
    ) -> NotificationTransportResult:
        self.calls.append((command.command_id, recipient.recipient_id))
        queue = self._outcomes.get(recipient.recipient_id)
        if not queue:
            return _transport_result(DeliveryOutcome.UNKNOWN)
        result = queue.popleft()
        return result if isinstance(result, NotificationTransportResult) else _transport_result(result)


class V12NotificationWorker:
    """Claim/deliver one recipient at a time; delivery never controls purchase."""

    def __init__(self, store: V12Store, transport: NotificationTransport, *, review_current=None, prepare_content=None, guard_factory=None, clock=None, scope="all") -> None:
        self._review_current = review_current
        self._prepare_content, self._scope = prepare_content, scope
        self._clock, self._guard_factory = clock, guard_factory
        self._store = store
        self._transport = transport
        self._dispatch_lock = Lock()
        self._deferred = False
        self._dispatch_owner = None

    def defer_delivery(self):
        """Canonical launcher worker dispatches; callers only enqueue in SQLite."""
        with self._dispatch_lock:
            self._deferred = True
            self._dispatch_owner = None

    def bind_delivery_thread(self):
        with self._dispatch_lock:
            if self._dispatch_owner not in (None, get_ident()):
                raise RuntimeError("NOTIFICATION_WORKER_OWNERSHIP_LOST")
            self._dispatch_owner = get_ident()

    def run_due(self, *, now: datetime, limit: int = 16) -> int:
        with self._dispatch_lock:
            if self._deferred and self._dispatch_owner != get_ident():
                return 0  # No network on the shared browser actor.
        from datetime import timedelta

        def defer(command, recipient, at):
            next_at = at + timedelta(seconds=15) if command.command_id.startswith("business-supplement:") else None
            self._store.defer_notification_review(command.command_id, recipient.recipient_id, not_before=next_at)

        commands = self._store.claim_due_notifications(now=now, limit=limit, scope=self._scope)
        sent_attempts = 0
        for original_command in commands:
            for recipient in original_command.recipients:
                guard = None
                try:
                    command = original_command
                    expected_attempt = dict(original_command.delivery_attempts).get(recipient.recipient_id)
                    if type(expected_attempt) is not int or expected_attempt <= 0:
                        defer(command, recipient, self._clock() if self._clock is not None else now)
                        continue
                    from .notification_review import review_reason
                    command = replace(command, review=self._store.notification_review(command.command_id))
                    prior_reason = ("INCIDENT_ALREADY_NOTIFIED" if self._store.previous_incident_delivery_protected(command.review)
                                    else review_reason(command, now))
                    reason = prior_reason if prior_reason not in {None, "EVIDENCE_STALE"} else None
                    if reason is None and self._review_current is not None:
                        try:
                            reason = self._review_current(command, now)
                            if reason is None and command.review:
                                import json
                                proof = json.loads(command.review)
                                proof["verified_at"] = now.isoformat()
                                command = replace(command, review=json.dumps(proof, sort_keys=True))
                                self._store.refresh_notification_review(command.command_id, command.review)
                        except Exception:  # noqa: BLE001 - an unavailable review never permits sending
                            reason = "CURRENT_REVIEW_PENDING"
                    if reason is None and self._prepare_content is not None:
                        try:
                            prepared = self._prepare_content(command, now)
                            if prepared is None or (not isinstance(prepared, NotificationCommand)
                                  or prepared.command_id != original_command.command_id
                                  or prepared.inquiry_id != original_command.inquiry_id
                                  or prepared.kind != original_command.kind
                                  or prepared.created_at != command.created_at
                                  or prepared.payload_version != command.payload_version
                                  or prepared.review != command.review
                                  or prepared.recipients != original_command.recipients
                                  or prepared.delivery_attempts != original_command.delivery_attempts
                                  or prepared.delivery_content_kind not in {None, "basic", "detailed"}):
                                reason = "CURRENT_REVIEW_PENDING"
                            else:
                                command = prepared
                        except Exception:  # noqa: BLE001 - unavailable content defers without SMTP
                            reason = "CURRENT_REVIEW_PENDING"
                    if reason is None:
                        reason = review_reason(command, now)
                    if reason == "CURRENT_REVIEW_PENDING":
                        defer(command, recipient, self._clock() if self._clock is not None else now)
                        continue
                    if reason is not None:
                        self._store.suppress_notification(command.command_id, recipient.recipient_id, reason, at=now)
                        continue
                    # Supplements re-prove live eligibility and report freshness immediately
                    # before SMTP, using the actual injectable dispatch clock.
                    import json
                    dispatch_at = self._clock() if self._clock is not None else now
                    if json.loads(command.review or "{}").get("business_supplement"):
                        try:
                            reason = self._review_current(command, dispatch_at) if self._review_current else "CURRENT_REVIEW_PENDING"
                            if reason is None:
                                proof = json.loads(command.review)
                                proof["verified_at"] = dispatch_at.isoformat()
                                command = replace(command, review=json.dumps(proof, sort_keys=True))
                                self._store.refresh_notification_review(command.command_id, command.review)
                                guard = self._guard_factory(command, at=dispatch_at, clock=self._clock or (lambda: now)) if self._guard_factory is not None else None
                                if guard is None or self._review_current(command, dispatch_at) is not None:
                                    raise ValueError("SUPPLEMENT_GUARD_UNAVAILABLE")
                                base = replace(original_command, review=command.review)
                                prepared = self._prepare_content(base, dispatch_at) if self._prepare_content else None
                                if (not isinstance(prepared, NotificationCommand)
                                        or prepared.command_id != command.command_id
                                        or prepared.inquiry_id != command.inquiry_id or prepared.kind != command.kind
                                        or prepared.created_at != command.created_at
                                        or prepared.payload_version != command.payload_version
                                        or prepared.review != command.review or prepared.recipients != command.recipients
                                        or prepared.delivery_attempts != command.delivery_attempts
                                        or prepared.delivery_content_kind != "detailed"):
                                    reason = "CURRENT_REVIEW_PENDING"
                                else:
                                    command = replace(prepared, delivery_revision_guard=guard)
                                    reason = review_reason(command, dispatch_at)
                        except Exception:  # noqa: BLE001 - no SMTP if last recheck is unavailable
                            reason = "CURRENT_REVIEW_PENDING"
                        if reason == "CURRENT_REVIEW_PENDING":
                            defer(command, recipient, self._clock() if self._clock is not None else now)
                            continue
                        if reason is not None:
                            self._store.suppress_notification(command.command_id, recipient.recipient_id, reason, at=dispatch_at)
                            continue
                        try:
                            from datetime import datetime, timedelta
                            final_at = self._clock() if self._clock is not None else dispatch_at
                            completed = datetime.fromisoformat(command.delivery_report_completed_at)
                            reference = datetime.fromisoformat(command.delivery_report_reference_at)
                            if (not timedelta(0) <= final_at-dispatch_at <= timedelta(seconds=1)
                                    or not timedelta(0) <= final_at-completed <= timedelta(minutes=15)
                                    or not timedelta(0) <= final_at-reference <= timedelta(minutes=15)):
                                raise ValueError("SUPPLEMENT_FRESHNESS_UNCONFIRMED")
                            dispatch_at = final_at
                        except (TypeError, ValueError, OverflowError):
                            defer(command, recipient, self._clock() if self._clock is not None else now)
                            continue
                    if command.delivery_content_kind == "detailed" and not getattr(self._transport, "supports_delivery_preflight", False):
                        defer(command, recipient, self._clock() if self._clock is not None else now)
                        continue
                    try:
                        result = self._transport.send_one(command, recipient)
                        if not isinstance(result, NotificationTransportResult):
                            result = _transport_result(DeliveryOutcome.UNKNOWN)
                    except Exception:  # noqa: BLE001 - unexpected adapter errors are UNKNOWN
                        # Only the transport adapter can classify provider-specific errors.
                        result = _transport_result(DeliveryOutcome.UNKNOWN)
                    finished_at = self._clock() if self._clock is not None else now
                    if result.deferred_without_send:
                        defer(command, recipient, finished_at)
                        continue
                    self._store.record_notification_result(
                        command_id=command.command_id,
                        recipient_id=recipient.recipient_id,
                        outcome=result.outcome,
                        at=finished_at,
                        reason_code=result.reason_code,
                        content_command=command if command.delivery_content_kind else None,
                        recipient_address=recipient.address,
                        expected_attempt=expected_attempt,
                    )
                    sent_attempts += 1
                finally:
                    if guard is not None:
                        guard.close()
        return sent_attempts


def _transport_result(outcome: DeliveryOutcome) -> NotificationTransportResult:
    reason = {
        DeliveryOutcome.SENT: ReasonCode.NOTIFICATION_SENT,
        DeliveryOutcome.RETRYABLE_FAILURE: ReasonCode.NOTIFICATION_TRANSIENT,
        DeliveryOutcome.PERMANENT_FAILURE: ReasonCode.NOTIFICATION_PERMANENT,
        DeliveryOutcome.UNKNOWN: ReasonCode.NOTIFICATION_UNKNOWN,
    }[outcome]
    return NotificationTransportResult(outcome, reason)



def business_decision_snapshot(item, facts, tier, *, at):
    """Freeze verified routing facts; never present them as a fresh market read."""
    from decimal import Decimal

    from src.sheets.tp_brief import quantity_value

    from .automatic_admission import binding_key
    total = facts.estimated_total if facts is not None else None
    if not isinstance(total, Decimal) or not total.is_finite() or total <= 0:
        return None
    quantity = quantity_value(item.quantity)
    if quantity <= 0 or at.tzinfo is None:
        return None
    reference = facts.market_minimum_reference_price
    if reference is not None and (not isinstance(reference, Decimal) or not reference.is_finite() or reference <= 0):
        return None
    recorded = facts.recorded_at
    if recorded is not None and (recorded.tzinfo is None or recorded > at):
        return None
    return {"version": 1, "inquiry_id": item.inquiry_id, "source_binding": binding_key(item.record_identity),
        "quantity": quantity, "tier": tier, "inventory_status": facts.inventory_status,
        "estimated_total_rmb": str(total), "reference_unit_rmb": str(reference) if reference is not None else None,
        "recorded_at": recorded.isoformat() if recorded is not None else None, "decision_at": at.isoformat(), "price_sources": list(facts.price_sources)}


def current_business_tier(item, row):
    from types import SimpleNamespace

    from src.sheets.worksheet_schema import worksheet_schema

    from .v12_flow import _business_tier
    schema = worksheet_schema(item.record_identity.worksheet.worksheet)
    customer = schema.fixed_customer_name or (row.cells.get(schema.customer_name_column) if schema.customer_name_column else None)
    return _business_tier(SimpleNamespace(record_identity=item.record_identity, customer_name=customer,
        importance_raw=row.cells.get(schema.importance_column) if schema.importance_column else item.importance_raw))


def verified_business_snapshot(command, item, row):
    import json
    from decimal import Decimal, InvalidOperation

    from src.sheets.tp_brief import quantity_value

    from .automatic_admission import binding_key
    from .v12_rules import should_send_important_order_notification
    try:
        value = json.loads(command.review or "{}").get("business_decision")
        if not isinstance(value, dict) or value.get("version") != 1:
            return None
        total = Decimal(value["estimated_total_rmb"])
        stamp = datetime.fromisoformat(value["recorded_at"] or value["decision_at"])
        decision = datetime.fromisoformat(value["decision_at"])
        unit = Decimal(value["reference_unit_rmb"]) if value.get("reference_unit_rmb") is not None else None
        if (value.get("inquiry_id") != command.inquiry_id or command.inquiry_id != item.inquiry_id
                or value.get("source_binding") != binding_key(item.record_identity)
                or value.get("quantity") != quantity_value(item.quantity)
                or value.get("tier") != current_business_tier(item, row)
                or type(value.get("quantity")) is not int
                or stamp.tzinfo is None or decision.tzinfo is None or stamp > decision or decision > command.created_at
                or not total.is_finite() or total <= 0
                or unit is not None and (not unit.is_finite() or unit <= 0)
                or not should_send_important_order_notification(tier=value["tier"], estimated_total=total,
                    inventory_status=value.get("inventory_status"))):
            return None
        sources = value.get("price_sources", [])
        if not isinstance(sources, list) or any(x not in {"INSO","Findchips","华强","立创","正能量","IC.net"} for x in sources):
            return None
        return value
    except (ValueError, TypeError, KeyError, InvalidOperation):
        return None


def enqueue_important_amount_correction(store, workflow_store, facts_provider, original_command_id, *, now, owner_authorized=False, expected_basis=None):
    """Explicit Owner correction only: new idempotent content, never replay old SMTP or procurement."""
    import html
    import json

    from src.research import ResearchResult, ResearchStatus

    from .v12_contracts import NotificationKind
    from .v12_flow import _business_tier, _notification_content
    from .v12_rules import should_send_important_order_notification
    if owner_authorized is not True:
        raise ValueError("CORRECTION_OWNER_AUTHORIZATION_REQUIRED")
    original = store.notification_command(original_command_id)
    if original.kind is not NotificationKind.IMPORTANT_ORDER or not original.inquiry_id:
        raise ValueError("CORRECTION_ORIGINAL_INVALID")
    correction_id = original.command_id+":amount-correction-v1"
    if store.notification_already_created(correction_id, original.inquiry_id, original.kind, original.recipients):
        return correction_id
    states = store.notification_delivery_states(original.command_id)
    if (not states or not any(x in {"SENT", "UNKNOWN"} for x in states)
            or any(x not in {"SENT", "UNKNOWN", "SUPPRESSED"} for x in states)):
        raise ValueError("CORRECTION_ORIGINAL_DELIVERY_UNSETTLED")
    item = workflow_store.get_by_inquiry_id(original.inquiry_id)
    # Compare the current canonical row against the frozen original or the
    # explicitly verified legacy basis. Never silently use a later rerun.
    original_basis = json.loads(original.review or "{}").get("business_decision")
    basis = original_basis if isinstance(original_basis, dict) else expected_basis
    if not isinstance(basis, dict):
        raise TypeError("CORRECTION_ORIGINAL_BASIS_REQUIRED")
    facts = facts_provider.get(item.inquiry_id)
    from .v12_flow import pending_record_from_item
    record = pending_record_from_item(item, *store.customer_snapshot(item.inquiry_id))
    tier = _business_tier(record)
    if (facts is None or facts.recorded_at is None
            or not should_send_important_order_notification(tier=tier, estimated_total=facts.estimated_total, inventory_status=facts.inventory_status)):
        raise ValueError("CORRECTION_AMOUNT_UNVERIFIED")
    snapshot = business_decision_snapshot(item, facts, tier, at=now)
    if snapshot is None:
        raise ValueError("CORRECTION_AMOUNT_UNVERIFIED")
    for field in ("recorded_at", "estimated_total_rmb", "reference_unit_rmb", "quantity"):
        if snapshot.get(field) != basis.get(field):
            raise ValueError("CORRECTION_ORIGINAL_BASIS_CHANGED")
    if isinstance(original_basis, dict):
        snapshot = dict(original_basis)
    result = ResearchResult(item.inquiry_id, ResearchStatus(item.research_status), resolved_brand=item.resolved_brand)
    subject, body = _notification_content(original.kind, record, result, facts, tier, None)
    body = ("按要求补充此前重要询价通知的金额依据；本通知不会重新提交采购。\n"
        "以下为已记录的调研分流参考，并非当前市场价格、库存或采购成交价。\n"
        + business_snapshot_time(snapshot)+"\n参考价格来源："+
        ("、".join(snapshot["price_sources"]) or "原调研记录，来源标记未核实")+"\n"+body)
    proof = json.dumps({"correction_of":original.command_id,"business_decision":snapshot},sort_keys=True,ensure_ascii=False)
    store.enqueue_notification(NotificationCommand(correction_id,item.inquiry_id,original.kind,original.recipients,
        "【重要询价金额补充】"+subject,body,"<html><body><pre>"+html.escape(body)+"</pre></body></html>",now,2,proof))
    return correction_id



def business_snapshot_time(snapshot):
    from .automatic_admission import SHANGHAI
    recorded = snapshot.get("recorded_at")
    stamp = datetime.fromisoformat(recorded or snapshot["decision_at"]).astimezone(SHANGHAI)
    return ("调研记录时间：" if recorded else "分流依据留存时间：")+stamp.strftime("%Y-%m-%d %H:%M:%S 上海时间")+(
        "" if recorded else "（原调研时间未核实）")
