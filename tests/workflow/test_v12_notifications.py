from __future__ import annotations

import sqlite3
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

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
from src.workflow.v12_store import V12DatabaseError, V12Store, migrate_v12

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


def test_existing_notification_check_requires_exact_context_and_recipients(tmp_path):
    store = prepared_store(tmp_path)
    cmd = command()
    check = lambda: store.notification_already_created(
        cmd.command_id, INQUIRY, cmd.kind, RECIPIENTS)
    assert not check()
    store.enqueue_notification(cmd)
    assert check()
    worker = V12NotificationWorker(store, FakeNotificationTransport({
        "a": (DeliveryOutcome.SENT,), "b": (DeliveryOutcome.SENT,),
    }))
    worker.run_due(now=NOW)
    assert check()
    assert not store.notification_already_created(
        cmd.command_id, INQUIRY, NotificationKind.DUPLICATE_ORDER, RECIPIENTS)
    assert not store.notification_already_created(
        cmd.command_id, INQUIRY, cmd.kind,
        (NotificationRecipient("a", "changed@example.invalid"), RECIPIENTS[1]))


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


def test_reenqueue_after_delivery_is_idempotent_and_never_resends(
    tmp_path: Path,
) -> None:
    """Re-routing one inquiry must not crash on, or repeat, its notification.

    A routed inquiry can legitimately need routing again (for example when the
    purchase draft is rejected). The command id is derived from inquiry+kind, so
    the second route re-enqueues the *same* command with a new ``created_at``.
    Treating that timestamp as part of the command's identity raised a database
    error before the purchase leg had even started.
    """

    store = prepared_store(tmp_path)
    store.enqueue_notification(command())
    transport = FakeNotificationTransport(
        {"a": (DeliveryOutcome.SENT,), "b": (DeliveryOutcome.SENT,)}
    )
    worker = V12NotificationWorker(store, transport)
    assert worker.run_due(now=NOW) == 2

    store.enqueue_notification(
        NotificationCommand(
            "cmd-notify-1",
            INQUIRY,
            NotificationKind.IMPORTANT_ORDER,
            RECIPIENTS,
            "subject",
            "text",
            None,
            NOW + timedelta(minutes=20),
        )
    )

    assert worker.run_due(now=NOW + timedelta(minutes=21)) == 0
    assert transport.calls == [("cmd-notify-1", "a"), ("cmd-notify-1", "b")]
    assert (
        sum(
            item.event_type is EventType.NOTIFICATION_DELIVERY_SUCCEEDED
            for item in store.event_history(INQUIRY)
        )
        == 2
    )


def test_reenqueue_with_different_content_is_still_a_conflict(tmp_path: Path) -> None:
    store = prepared_store(tmp_path)
    store.enqueue_notification(command())
    with pytest.raises(V12DatabaseError):
        store.enqueue_notification(
            NotificationCommand(
                "cmd-notify-1",
                INQUIRY,
                NotificationKind.IMPORTANT_ORDER,
                RECIPIENTS,
                "different subject",
                "text",
                None,
                NOW,
            )
        )
    with pytest.raises(V12DatabaseError):
        store.enqueue_notification(
            NotificationCommand(
                "cmd-notify-1",
                INQUIRY,
                NotificationKind.IMPORTANT_ORDER,
                (NotificationRecipient("a", "elsewhere@example.invalid"),),
                "subject",
                "text",
                None,
                NOW,
            )
        )


def test_each_recipient_starts_with_original_notification_body(tmp_path):
    from dataclasses import replace

    store = prepared_store(tmp_path)
    store.enqueue_notification(command())
    bodies = []

    class CapturingTransport(FakeNotificationTransport):
        def send_one(self, cmd, recipient):
            bodies.append(cmd.text_body)
            return super().send_one(cmd, recipient)

    transport = CapturingTransport({
        "a": (DeliveryOutcome.SENT,), "b": (DeliveryOutcome.SENT,),
    })
    worker = V12NotificationWorker(
        store, transport,
        prepare_content=lambda cmd, now: replace(cmd, text_body=cmd.text_body + " report"),
    )
    assert worker.run_due(now=NOW) == 2
    assert bodies == ["text report", "text report"]

def test_sent_content_evidence_is_scoped_to_exact_recipient_attempt(tmp_path):
    import json
    from dataclasses import replace

    store = prepared_store(tmp_path)
    store.enqueue_notification(command())
    transport = FakeNotificationTransport({
        "a": (DeliveryOutcome.SENT,), "b": (DeliveryOutcome.UNKNOWN,),
    })
    worker = V12NotificationWorker(store, transport,
        prepare_content=lambda cmd, now: replace(cmd, text_body="base", delivery_content_kind="basic"))
    assert worker.run_due(now=NOW) == 2
    with sqlite3.connect(store.database_path) as db:
        rows = db.execute("SELECT event_type,attempt,payload_json FROM workflow_v12_events WHERE event_type LIKE 'NOTIFICATION_DELIVERY_%' ORDER BY rowid").fetchall()
    evidence = [json.loads(payload).get("notification_content") for _, _, payload in rows]
    assert len(evidence) == 2 and sum(item is not None for item in evidence) == 1
    sent = next(item for item in evidence if item is not None)
    assert sent["version"] == 1 and sent["kind"] == "basic" and sent["attempt"] == 1
    import hashlib
    expected = lambda obj: hashlib.sha256(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
    assert sent["command_id"] == command().command_id
    assert sent["content_sha256"] == expected(["subject", "base", None])
    assert sent["recipient_digest"] == expected([command().command_id, "a", "a@example.invalid"])


def test_content_evidence_failure_rolls_back_sent_to_unknown_after_recovery(tmp_path, monkeypatch):
    from dataclasses import replace

    import src.workflow.v12_store as store_module

    store = prepared_store(tmp_path)
    cmd = replace(command(), recipients=(RECIPIENTS[0],))
    store.enqueue_notification(cmd)
    transport = FakeNotificationTransport({"a": (DeliveryOutcome.SENT,)})
    worker = V12NotificationWorker(store, transport,
        prepare_content=lambda item, now: replace(item, delivery_content_kind="basic"))
    original = store_module._insert_event
    def fail_on_content(db, event, *, content_evidence=None):
        if content_evidence:
            raise RuntimeError("synthetic persistence failure")
        return original(db, event)
    monkeypatch.setattr(store_module, "_insert_event", fail_on_content)
    with pytest.raises(RuntimeError):
        worker.run_due(now=NOW)
    assert store.notification_delivery_states(cmd.command_id) == ("SENDING",)
    store.recover_abandoned_notification_attempts(at=NOW)
    assert store.notification_delivery_states(cmd.command_id) == ("UNKNOWN",)
    assert worker.run_due(now=NOW) == 0 and len(transport.calls) == 1

@pytest.mark.parametrize("field,value", [("command_id", "other"), ("inquiry_id", "other"),
    ("recipients", (NotificationRecipient("x", "x@example.invalid"),))])
def test_prepared_identity_change_never_reaches_transport(tmp_path, field, value):
    from dataclasses import replace
    store = prepared_store(tmp_path)
    store.enqueue_notification(command())
    transport = FakeNotificationTransport()
    worker = V12NotificationWorker(store, transport,
        prepare_content=lambda cmd, now: replace(cmd, **{field: value}))
    assert worker.run_due(now=NOW) == 0
    assert transport.calls == []
    assert store.notification_delivery_states(command().command_id) == ("PENDING", "PENDING")

def test_result_rejects_attempt_other_than_claimed_attempt(tmp_path):
    store = prepared_store(tmp_path)
    store.enqueue_notification(command())
    claimed, = store.claim_due_notifications(now=NOW)
    assert dict(claimed.delivery_attempts) == {"a": 1, "b": 1}
    with pytest.raises(V12DatabaseError):
        store.record_notification_result(command_id=claimed.command_id, recipient_id="a",
            outcome=DeliveryOutcome.SENT, at=NOW, expected_attempt=2)
    assert store.notification_delivery_states(claimed.command_id) == ("SENDING", "SENDING")

def test_success_evidence_uses_successful_retry_attempt(tmp_path):
    import json
    from dataclasses import replace
    store = prepared_store(tmp_path)
    cmd = replace(command(), recipients=(RECIPIENTS[0],))
    store.enqueue_notification(cmd)
    transport = FakeNotificationTransport({"a": (DeliveryOutcome.RETRYABLE_FAILURE, DeliveryOutcome.SENT)})
    worker = V12NotificationWorker(store, transport,
        prepare_content=lambda item, now: replace(item, delivery_content_kind="basic"))
    assert worker.run_due(now=NOW) == 1
    assert worker.run_due(now=NOW + timedelta(minutes=1)) == 1
    with sqlite3.connect(store.database_path) as db:
        payload, = db.execute("SELECT payload_json FROM workflow_v12_events WHERE event_type='NOTIFICATION_DELIVERY_SUCCEEDED'").fetchone()
    assert json.loads(payload)["notification_content"]["attempt"] == 2

@pytest.mark.parametrize("kind,outcome,expected", [
    ("basic", DeliveryOutcome.SENT, True), ("detailed", DeliveryOutcome.SENT, False),
    (None, DeliveryOutcome.SENT, False), ("basic", DeliveryOutcome.UNKNOWN, False),
])
def test_basic_delivery_proof_requires_exact_sent_recipient(tmp_path, kind, outcome, expected):
    from dataclasses import replace
    store = prepared_store(tmp_path)
    cmd = replace(command(), recipients=(RECIPIENTS[0],))
    store.enqueue_notification(cmd)
    transport = FakeNotificationTransport({"a": (outcome,)})
    transport.supports_delivery_preflight = True  # This test isolates ledger evidence.
    worker = V12NotificationWorker(store, transport,
        prepare_content=lambda item, now: replace(item, delivery_content_kind=kind))
    assert worker.run_due(now=NOW) == 1
    assert store.notification_received_basic(cmd.command_id, "a", "a@example.invalid") is expected
    assert not store.notification_received_basic(cmd.command_id, "a", "other@example.invalid")

def test_conflicting_or_duplicate_basic_evidence_is_rejected(tmp_path):
    from dataclasses import replace
    store = prepared_store(tmp_path)
    cmd = replace(command(), recipients=(RECIPIENTS[0],))
    store.enqueue_notification(cmd)
    worker = V12NotificationWorker(store, FakeNotificationTransport({"a": (DeliveryOutcome.SENT,)}),
        prepare_content=lambda item, now: replace(item, delivery_content_kind="basic"))
    assert worker.run_due(now=NOW) == 1
    assert store.notification_received_basic(cmd.command_id, "a", "a@example.invalid")
    assert any(event.event_type is EventType.NOTIFICATION_DELIVERY_SUCCEEDED for event in store.event_history(INQUIRY))
    with sqlite3.connect(store.database_path) as db:
        db.execute("INSERT INTO workflow_v12_events SELECT 'duplicate-test-event',inquiry_id,event_type,occurred_at,source_module,schema_version,reason_code,attempt,evidence_ref,payload_json FROM workflow_v12_events WHERE event_type='NOTIFICATION_DELIVERY_SUCCEEDED'")
    assert not store.notification_received_basic(cmd.command_id, "a", "a@example.invalid")


def test_content_evidence_without_claimed_attempt_never_commits_sent(tmp_path):
    from dataclasses import replace
    store = prepared_store(tmp_path)
    cmd = replace(command(), recipients=(RECIPIENTS[0],))
    store.enqueue_notification(cmd)
    claimed, = store.claim_due_notifications(now=NOW)
    with pytest.raises(V12DatabaseError):
        store.record_notification_result(command_id=cmd.command_id, recipient_id="a", outcome=DeliveryOutcome.SENT,
            at=NOW, content_command=replace(claimed, delivery_content_kind="basic"),
            recipient_address="a@example.invalid")
    assert store.notification_delivery_states(cmd.command_id) == ("SENDING",)

def test_waiting_supplements_cannot_starve_original_notice(tmp_path):
    from dataclasses import replace
    store = prepared_store(tmp_path)
    for index in range(16):
        item = replace(command(), command_id=f"business-supplement:{index:02}", recipients=(RECIPIENTS[0],))
        store.enqueue_notification(item)
    original = replace(command(), command_id="zzz-original", recipients=(RECIPIENTS[0],))
    store.enqueue_notification(original)
    transport = FakeNotificationTransport({"a": (DeliveryOutcome.SENT,)})
    worker = V12NotificationWorker(store, transport,
        prepare_content=lambda item, now: None if item.command_id.startswith("business-supplement:") else item)
    assert worker.run_due(now=NOW, limit=16) == 1
    assert transport.calls == [("zzz-original", "a")]
    assert store.notification_delivery_states("zzz-original") == ("SENT",)
    assert worker.run_due(now=NOW, limit=16) == 0