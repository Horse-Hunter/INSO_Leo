"""Recipient-scoped V1.2 notification scheduling with a fake-only transport."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from datetime import datetime
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

    def __init__(self, store: V12Store, transport: NotificationTransport) -> None:
        self._store = store
        self._transport = transport

    def run_due(self, *, now: datetime, limit: int = 16) -> int:
        commands = self._store.claim_due_notifications(now=now, limit=limit)
        sent_attempts = 0
        for command in commands:
            for recipient in command.recipients:
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
