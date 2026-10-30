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

    def __init__(self, store: V12Store, transport: NotificationTransport, *, review_current=None, prepare_content=None, scope="all") -> None:
        self._review_current = review_current
        self._prepare_content, self._scope = prepare_content, scope
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
        commands = self._store.claim_due_notifications(now=now, limit=limit, scope=self._scope)
        sent_attempts = 0
        for command in commands:
            for recipient in command.recipients:
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
                        if prepared is None:
                            reason = "CURRENT_REVIEW_PENDING"
                        else:
                            command = prepared
                    except Exception:  # noqa: BLE001 - unavailable content defers without SMTP
                        reason = "CURRENT_REVIEW_PENDING"
                if reason is None:
                    reason = review_reason(command, now)
                if reason == "CURRENT_REVIEW_PENDING":
                    self._store.defer_notification_review(command.command_id, recipient.recipient_id)
                    continue
                if reason is not None:
                    self._store.suppress_notification(command.command_id, recipient.recipient_id, reason, at=now)
                    continue
                try:
                    result = self._transport.send_one(command, recipient)
                    if not isinstance(result, NotificationTransportResult):
                        result = _transport_result(DeliveryOutcome.UNKNOWN)
                except Exception:  # noqa: BLE001 - unexpected adapter errors are UNKNOWN
                    # Only the transport adapter can classify provider-specific errors.
                    result = _transport_result(DeliveryOutcome.UNKNOWN)
                self._store.record_notification_result(
                    command_id=command.command_id,
                    recipient_id=recipient.recipient_id,
                    outcome=result.outcome,
                    at=now,
                    reason_code=result.reason_code,
                )
                sent_attempts += 1
        return sent_attempts


def _transport_result(outcome: DeliveryOutcome) -> NotificationTransportResult:
    reason = {
        DeliveryOutcome.SENT: ReasonCode.NOTIFICATION_SENT,
        DeliveryOutcome.RETRYABLE_FAILURE: ReasonCode.NOTIFICATION_TRANSIENT,
        DeliveryOutcome.PERMANENT_FAILURE: ReasonCode.NOTIFICATION_PERMANENT,
        DeliveryOutcome.UNKNOWN: ReasonCode.NOTIFICATION_UNKNOWN,
    }[outcome]
    return NotificationTransportResult(outcome, reason)
