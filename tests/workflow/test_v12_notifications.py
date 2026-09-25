from __future__ import annotations

import sqlite3
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from src.workflow import WorkflowStateStore
from src.workflow.v12_contracts import (
    AlertType,
    DeliveryOutcome,
    DuplicateCheckResult,
    DuplicateOutcome,
    EventType,
    NotificationCommand,
    NotificationKind,
    NotificationRecipient,
    NotificationTransportResult,
    PurchaseOutcome,
    ReasonCode,
)
from src.workflow.v12_notifications import (
    FakeNotificationTransport,
    V12NotificationWorker,
)
from src.workflow.v12_store import V12Store, migrate_v12

NOW = datetime(2026, 9, 25, 8, tzinfo=UTC)
INQUIRY = "inq_0123456789abcdef01234567"
RECIPIENTS = (
    NotificationRecipient("a", "a@example.invalid"),
    NotificationRecipient("b", "b@example.invalid"),
)


def prepared_store(tmp_path: Path) -> V12Store:
    database = tmp_path / "workflow.sqlite3"
    WorkflowStateStore(database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO workflow_items (spreadsheet, worksheet, row_number, inquiry_id, "
            "record_identity_json, mpn_json, brand_json, quantity_json, importance_raw_json, "
            "status, attempt_count, next_attempt_at, created_at, updated_at) "
            "VALUES ('sheet-id','2026',4,?,'{}','\"MPN-1\"','\"Brand\"','10','\"A\"',"
            "'QUEUED',0,?,?,?)",
            (INQUIRY, NOW.isoformat(), NOW.isoformat(), NOW.isoformat()),
        )
    migrate_v12(
        database,
        tmp_path / "backups",
        quiesce=lambda: nullcontext(),
        clock=lambda: NOW,
    )
    return V12Store(database)


def command() -> NotificationCommand:
    return NotificationCommand(
        "cmd-notify-1", INQUIRY, NotificationKind.IMPORTANT_ORDER, RECIPIENTS,
        "subject", "text", None, NOW,
    )


def test_recipient_ledger_retries_only_failed_recipient_and_recovers_alert(
    tmp_path: Path,
) -> None:
    store = prepared_store(tmp_path)
    store.enqueue_notification(command())
    store.set_purchase_state(INQUIRY, "purchase-1", PurchaseOutcome.PRE_SAVE_READY, at=NOW)
    transport = FakeNotificationTransport(
        {
            "a": (DeliveryOutcome.SENT,),
            "b": (DeliveryOutcome.RETRYABLE_FAILURE, DeliveryOutcome.SENT),
        }
    )
    worker = V12NotificationWorker(store, transport)

    assert worker.run_due(now=NOW) == 2
    assert store.latest_active_alert(INQUIRY).alert_type is AlertType.NOTIFICATION_FAILED
    store.set_purchase_state(
        INQUIRY,
        "purchase-1",
        PurchaseOutcome.AI_RECOGNIZED,
        at=NOW + timedelta(seconds=1),
    )
    assert store.purchase_state(INQUIRY) is PurchaseOutcome.AI_RECOGNIZED

    assert worker.run_due(now=NOW + timedelta(seconds=59)) == 0
    assert worker.run_due(now=NOW + timedelta(minutes=1)) == 1
    assert transport.calls == [
        ("cmd-notify-1", "a"),
        ("cmd-notify-1", "b"),
        ("cmd-notify-1", "b"),
    ]
    assert store.active_alerts(INQUIRY) == ()
    history = store.event_history(INQUIRY)
    assert any(item.event_type is EventType.ALERT_RECOVERED for item in history)
    assert sum(item.event_type is EventType.NOTIFICATION_DELIVERY_SUCCEEDED for item in history) == 2
    assert any(item.event_type is EventType.NOTIFICATION_RETRY_SCHEDULED for item in history)


def test_retry_schedule_is_one_five_fifteen_minutes_then_stops(tmp_path: Path) -> None:
    store = prepared_store(tmp_path)
    store.enqueue_notification(command())
    transport = FakeNotificationTransport(
        {"a": (DeliveryOutcome.RETRYABLE_FAILURE,) * 4}
    )
    worker = V12NotificationWorker(store, transport)
    current = NOW
    expected_delays = (1, 5, 15)
    for index, delay in enumerate(expected_delays):
        assert worker.run_due(now=current) == (2 if index == 0 else 1)
        result = store.recipient_results("cmd-notify-1")[0]
        assert result.next_attempt_at == current + timedelta(minutes=delay)
        current = result.next_attempt_at
    assert worker.run_due(now=current) == 1
    assert store.recipient_results("cmd-notify-1")[0].outcome is DeliveryOutcome.PERMANENT_FAILURE
    assert worker.run_due(now=current + timedelta(days=1)) == 0
    assert len(transport.calls) == 5  # initial attempts include B's UNKNOWN result


def test_permanent_and_unknown_delivery_are_not_retried(tmp_path: Path) -> None:
    store = prepared_store(tmp_path)
    store.enqueue_notification(command())
    transport = FakeNotificationTransport(
        {
            "a": (DeliveryOutcome.PERMANENT_FAILURE,),
            "b": (DeliveryOutcome.UNKNOWN,),
        }
    )
    worker = V12NotificationWorker(store, transport)
    assert worker.run_due(now=NOW) == 2
    assert worker.run_due(now=NOW + timedelta(days=1)) == 0
    assert len(transport.calls) == 2
    assert {item.outcome for item in store.recipient_results("cmd-notify-1")} == {
        DeliveryOutcome.PERMANENT_FAILURE,
        DeliveryOutcome.UNKNOWN,
    }
    assert store.latest_active_alert(INQUIRY).reason_code in {
        ReasonCode.NOTIFICATION_PERMANENT,
        ReasonCode.NOTIFICATION_UNKNOWN,
    }


def test_transport_result_is_typed_and_workflow_does_not_classify_exceptions(
    tmp_path: Path,
) -> None:
    store = prepared_store(tmp_path)
    store.enqueue_notification(command())
    worker = V12NotificationWorker(
        store,
        FakeNotificationTransport(
            {
                "a": (
                    NotificationTransportResult(
                        DeliveryOutcome.RETRYABLE_FAILURE,
                        ReasonCode.NOTIFICATION_TRANSIENT,
                    ),
                ),
                "b": (DeliveryOutcome.SENT,),
            }
        ),
    )
    worker.run_due(now=NOW)
    results = {item.recipient_id: item for item in store.recipient_results("cmd-notify-1")}
    assert results["a"].outcome is DeliveryOutcome.RETRYABLE_FAILURE
    assert results["a"].reason_code is ReasonCode.NOTIFICATION_TRANSIENT
    assert results["b"].outcome is DeliveryOutcome.SENT
    assert results["b"].reason_code is ReasonCode.NOTIFICATION_SENT


def test_unknown_inflight_after_restart_is_never_retried(tmp_path: Path) -> None:
    store = prepared_store(tmp_path)
    store.enqueue_notification(command())
    claimed = store.claim_due_notifications(now=NOW)
    assert claimed
    assert store.recover_abandoned_notification_attempts(at=NOW + timedelta(seconds=1)) == 2
    restarted = V12Store(store.database_path)
    assert restarted.claim_due_notifications(now=NOW + timedelta(days=1)) == ()
    assert {item.outcome for item in restarted.recipient_results("cmd-notify-1")} == {
        DeliveryOutcome.UNKNOWN,
    }


class CanaryTransport:
    def send_one(self, _command, _recipient):
        raise TimeoutError("SECRET_CANARY_9F8C_smtp-response")


def test_notification_exception_canary_never_reaches_database_or_dto(tmp_path: Path) -> None:
    store = prepared_store(tmp_path)
    store.enqueue_notification(command())
    worker = V12NotificationWorker(store, CanaryTransport())
    worker.run_due(now=NOW)
    assert store.recipient_results("cmd-notify-1")[0].outcome is DeliveryOutcome.UNKNOWN
    assert store.recipient_results("cmd-notify-1")[0].reason_code is ReasonCode.NOTIFICATION_UNKNOWN
    assert store.recipient_results("cmd-notify-1")[0].next_attempt_at is None
    assert worker.run_due(now=NOW + timedelta(days=1)) == 0
    assert "SECRET_CANARY" not in repr(store.active_alerts(INQUIRY))
    assert "SECRET_CANARY" not in repr(store.event_history(INQUIRY))
    with sqlite3.connect(store.database_path) as connection:
        for (table,) in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'workflow_v12_%'"
        ):
            assert "SECRET_CANARY" not in repr(
                tuple(tuple(row) for row in connection.execute(f"SELECT * FROM {table}"))
            )


def test_notification_alert_recovers_and_duplicate_alert_becomes_latest_again(
    tmp_path: Path,
) -> None:
    store = prepared_store(tmp_path)
    store.record_duplicate_result(
        DuplicateCheckResult(
            INQUIRY,
            DuplicateOutcome.CONFIRMED,
            "MPN-1",
            NOW,
            repeated=True,
            historical_date=NOW - timedelta(hours=1),
            historical_quantity=2,
            quantity_equal=False,
            inso_quote=Decimal("12.50"),
        )
    )
    store.enqueue_notification(command())
    transport = FakeNotificationTransport(
        {
            "a": (DeliveryOutcome.RETRYABLE_FAILURE, DeliveryOutcome.SENT),
            "b": (DeliveryOutcome.SENT,),
        }
    )
    worker = V12NotificationWorker(store, transport)
    worker.run_due(now=NOW + timedelta(seconds=1))
    assert store.latest_active_alert(INQUIRY).alert_type is AlertType.NOTIFICATION_FAILED

    worker.run_due(now=NOW + timedelta(minutes=1, seconds=1))
    assert store.latest_active_alert(INQUIRY).alert_type is AlertType.DUPLICATE_ORDER
    active_types = {alert.alert_type for alert in store.active_alerts(INQUIRY)}
    assert active_types == {AlertType.DUPLICATE_ORDER}
    assert any(item.event_type is EventType.ALERT_RECOVERED for item in store.event_history(INQUIRY))
