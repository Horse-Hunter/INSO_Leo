"""Synthetic working-time and durable follow-up tests; no live SMTP or Sheet writes."""
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from src.workflow.purchase_follow_up import (
    WORK_ZONE,
    PurchaseFollowUp,
    elapsed_working_time,
)
from src.workflow.v12_contracts import DeliveryOutcome, EventType, WorkflowEvent
from src.workflow.v12_notifications import (
    FakeNotificationTransport,
    V12NotificationWorker,
)
from src.workflow.v12_store import V12Store
from src.workflow.v13_follow_up_store import V13PurchaseFollowUpStore
from tests.workflow.test_rfq006_integration import fixture
from tests.workflow.test_v13_quotation import WS, source


def local(value):
    return datetime.fromisoformat(value).replace(tzinfo=WORK_ZONE)


@pytest.mark.parametrize("start,end,minutes", [
    ("2026-10-05T09:00", "2026-10-05T12:00", 180),
    ("2026-10-05T12:00", "2026-10-05T16:00", 180),
    ("2026-10-05T12:30", "2026-10-05T13:30", 0),
    ("2026-10-05T18:00", "2026-10-06T09:00", 0),
    ("2026-10-05T17:00", "2026-10-06T11:00", 180),
    ("2026-10-09T17:00", "2026-10-12T11:00", 180),
    ("2026-10-10T09:00", "2026-10-11T18:00", 0),
    ("2026-10-10T09:00", "2026-10-12T10:00", 60),
    ("2026-10-05T08:00", "2026-10-05T19:00", 480),
    ("2026-10-05T15:00", "2026-10-05T09:00", 0),
])
def test_working_time_excludes_breaks_nights_and_weekends(start, end, minutes):
    assert elapsed_working_time(local(start), local(end)) == timedelta(minutes=minutes)
    assert elapsed_working_time(local(start).astimezone(UTC), local(end).astimezone(UTC)) == timedelta(minutes=minutes)


def test_working_time_rejects_ambiguous_naive_timestamp():
    with pytest.raises(ValueError):
        elapsed_working_time(local("2026-10-05T09:00").replace(tzinfo=None), local("2026-10-05T10:00"))


def setup_follow_up(tmp_path, *, stamp=True):
    db, store, sheets, holds, ledger, quotes, make, _observed = fixture(tmp_path, [(), ()])
    iid = store.all_items()[0].inquiry_id
    start = local("2026-10-09T17:00")
    episodes = V13PurchaseFollowUpStore(db)
    episodes.migrate()
    if stamp:
        episodes.record_confirmed(iid, confirmed_at=start)
    now = [local("2026-10-12T11:00:01")]
    follow = PurchaseFollowUp(reader=sheets, workflow_store=store, v12_store=ledger, clock=lambda: now[0])
    return db, store, sheets, holds, ledger, quotes, make, follow, now, iid


def command_count(db):
    with sqlite3.connect(db) as connection:
        return connection.execute("SELECT count(*) FROM workflow_v12_notification_commands WHERE command_id LIKE 'purchase-follow-up:%'").fetchone()[0]


def test_threshold_is_strict_and_restart_deduplicates_both_recipients(tmp_path):
    db, store, sheets, _, ledger, _, _, follow, now, _iid = setup_follow_up(tmp_path)
    now[0] = local("2026-10-12T11:00")
    assert follow.run(WS) == 0  # Exactly three working hours, not over three.
    now[0] += timedelta(seconds=1)
    assert follow.run(WS) == 1
    restarted = PurchaseFollowUp(reader=sheets, workflow_store=store, v12_store=V12Store(db), clock=lambda: now[0])
    assert restarted.run(WS) == 0 and command_count(db) == 1
    transport = FakeNotificationTransport({"owner": (DeliveryOutcome.SENT,), "ops": (DeliveryOutcome.SENT,)})
    worker = V12NotificationWorker(ledger, transport)
    assert worker.run_due(now=now[0]) == 2
    assert {recipient for _, recipient in transport.calls} == {"owner", "ops"}
    assert worker.run_due(now=now[0]) == 0
    with sqlite3.connect(db) as connection:
        addresses = {r[0] for r in connection.execute("SELECT address FROM workflow_v12_notification_recipients")}
    assert addresses == {"linan229@qq.com", "shawn@inso-hk.com"}
    assert follow.run(WS) == 0


def test_new_confirmed_sending_episode_resets_clock_and_allows_one_new_reminder(tmp_path):
    db, _, _, _, _ledger, _, _, follow, now, iid = setup_follow_up(tmp_path)
    assert follow.run(WS) == 1
    follow.episodes.record_confirmed(iid, confirmed_at=now[0])
    assert follow.run(WS) == 0
    now[0] = local("2026-10-12T15:00:02")
    assert follow.run(WS) == 1 and follow.run(WS) == 0
    assert command_count(db) == 2


@pytest.mark.parametrize("status", ["采购已报价", "成交", "未发"])
def test_no_reminder_after_source_status_changes(tmp_path, status):
    db, _, sheets, _, _, _, _, follow, _, _ = setup_follow_up(tmp_path)
    sheets.rows = [source(2, status)]
    assert follow.run(WS) == 0 and command_count(db) == 0


def test_untimed_history_is_not_backfilled_or_notified(tmp_path):
    db, _, _, _, ledger, _, _, follow, _, iid = setup_follow_up(tmp_path, stamp=False)
    ledger.append_event(WorkflowEvent("legacy-saved", iid, EventType.PURCHASE_DATA_SAVED,
                                      local("2026-10-01T09:00"), "inso"))
    assert follow.run(WS) == 0 and command_count(db) == 0
    assert follow.episodes.latest(iid) is None


def test_moved_row_uses_canonical_identity_and_reports_current_location(tmp_path):
    db, _, sheets, _, ledger, _, _, follow, now, _ = setup_follow_up(tmp_path)
    sheets.rows = [source(9)]
    assert follow.run(WS) == 1
    commands = ledger.claim_due_notifications(now=now[0])
    assert "当前行：9" in commands[0].text_body
    assert command_count(db) == 1


def test_ambiguous_or_changed_row_never_receives_another_orders_timestamp(tmp_path):
    db, _, sheets, _, _, _, _, follow, _, _ = setup_follow_up(tmp_path)
    sheets.rows = [source(8), source(9)]
    assert follow.run(WS) == 0
    sheets.rows = [source(2, model="CORRECTED-OTHER")]
    assert follow.run(WS) == 0 and command_count(db) == 0


def test_follow_up_runs_before_hold_skip_and_does_not_change_hold_or_quote_outcome(tmp_path):
    from src.workflow.v13_quotation import (
        QuotationOutcome,
        RowErrorReason,
        V13QuotationResult,
    )
    db, store, _sheets, holds, _, quotes, make, follow, _, iid = setup_follow_up(tmp_path)
    identity = store.all_items()[0].record_identity
    held = V13QuotationResult(iid, identity, "MPN", QuotationOutcome.ROW_FAILED, None,
                              RowErrorReason.UPDATE_RESULT_UNCONFIRMED, WS, 2)
    holds.hold(held, identity)
    integrated = make()
    integrated.follow_up = follow.run
    assert integrated.run(WS) == ()
    assert command_count(db) == 1 and len(holds.active()) == 1
    assert not quotes.calls


def test_follow_up_recipient_retry_keeps_successful_recipient_settled(tmp_path):
    from src.workflow.v12_contracts import NotificationKind
    db, _, _, _, ledger, _, _, follow, now, _ = setup_follow_up(tmp_path)
    assert follow.run(WS) == 1
    transport = FakeNotificationTransport({"owner": (DeliveryOutcome.SENT,),
        "ops": (DeliveryOutcome.RETRYABLE_FAILURE, DeliveryOutcome.SENT)})
    worker = V12NotificationWorker(ledger, transport)
    assert worker.run_due(now=now[0]) == 2
    assert follow.run(WS) == 0
    now[0] += timedelta(minutes=2)
    assert worker.run_due(now=now[0]) == 1
    assert [recipient for _, recipient in transport.calls].count("owner") == 1
    assert [recipient for _, recipient in transport.calls].count("ops") == 2
    with sqlite3.connect(db) as connection:
        kinds = {row[0] for row in connection.execute("SELECT kind FROM workflow_v12_notification_commands")}
    assert kinds == {NotificationKind.PURCHASE_EXCEPTION.value}
    assert command_count(db) == 1
