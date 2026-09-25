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
    ReasonCode,
)
from .v12_safety import sanitize_external_error
from .v12_store import V12Store


class NotificationTransport(Protocol):
    def send_one(
        self,
        command: NotificationCommand,
        recipient: NotificationRecipient,
    ) -> DeliveryOutcome: ...


class FakeNotificationTransport:
    """Deterministic test adapter; has no SMTP or credential dependency."""

    def __init__(self, outcomes: Mapping[str, tuple[DeliveryOutcome, ...]] = ()) -> None:
        self._outcomes = {key: deque(value) for key, value in dict(outcomes).items()}
        self.calls: list[tuple[str, str]] = []

    def send_one(
        self,
        command: NotificationCommand,
        recipient: NotificationRecipient,
    ) -> DeliveryOutcome:
        self.calls.append((command.command_id, recipient.recipient_id))
        queue = self._outcomes.get(recipient.recipient_id)
        if not queue:
            return DeliveryOutcome.UNKNOWN
        return queue.popleft()


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
                reason_code: ReasonCode | None = None
                try:
                    outcome = self._transport.send_one(command, recipient)
                    if not isinstance(outcome, DeliveryOutcome):
                        outcome = DeliveryOutcome.UNKNOWN
                        reason_code = ReasonCode.NOTIFICATION_UNKNOWN
                except Exception as exc:  # noqa: BLE001 - external adapter boundary
                    safe = sanitize_external_error(exc, subsystem="notification")
                    del exc
                    outcome = (
                        DeliveryOutcome.RETRYABLE_FAILURE
                        if safe.category.value == "TRANSIENT"
                        else DeliveryOutcome.UNKNOWN
                    )
                    reason_code = safe.reason_code
                if outcome is DeliveryOutcome.UNKNOWN and reason_code is None:
                    reason_code = ReasonCode.NOTIFICATION_UNKNOWN
                elif outcome is DeliveryOutcome.RETRYABLE_FAILURE and reason_code is None:
                    reason_code = ReasonCode.NOTIFICATION_TRANSIENT
                elif outcome is DeliveryOutcome.PERMANENT_FAILURE and reason_code is None:
                    reason_code = ReasonCode.NOTIFICATION_PERMANENT
                self._store.record_notification_result(
                    command_id=command.command_id,
                    recipient_id=recipient.recipient_id,
                    outcome=outcome,
                    at=now,
                    reason_code=reason_code,
                )
                sent_attempts += 1
        return sent_attempts
