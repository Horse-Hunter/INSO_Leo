"""Explicit manual purchase episodes; all submission evidence is synthetic."""
import sqlite3
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from src.gui.app import _order_row_style
from src.gui.contracts import Order, OrderStatus
from src.launcher.v12_gui import read_v12_order_state
from src.sheets import query_pending_records
from src.workflow.v12_contracts import (
    AlertType,
    BusinessState,
    EventType,
    PurchaseDraftResult,
    PurchaseOutcome,
    ReasonCode,
    ReconciliationOutcome,
    ReconciliationResult,
    WorkflowEvent,
)
from src.workflow.v12_flow import ResearchBusinessFacts
from src.workflow.v12_store import FakeSaveReconciler
from tests.workflow.test_v12_flow import (
    NOW,
    SHEET,
    FakeSheetsReader,
    _confirmed_duplicate,
    _make_flow,
)


def alert_rows(ledger, inquiry):
    with sqlite3.connect(ledger.database_path) as db:
        return db.execute("SELECT alert_id,alert_type,scope_key,active,recovered_by_event_id FROM workflow_v12_active_alerts WHERE inquiry_id=?", (inquiry,)).fetchall()


@pytest.mark.parametrize("old_failure", ["ai", "duplicate"])
@pytest.mark.parametrize("fails_again", [False, True])
def test_manual_retry_recovers_only_prior_episode_and_can_raise_new_alert(tmp_path, old_failure, fails_again):
    flow, store, ledger, _, checker, _, writer, _ = _make_flow(tmp_path,
        facts=ResearchBusinessFacts("货足", Decimal(10), Decimal(2)))
    reader = FakeSheetsReader()
    record, = query_pending_records(reader, SHEET)
    inquiry = store.inquiry_id_for(record.record_identity)
    if old_failure == "ai":
        writer._recognized = ("WRONG", "Brand-X", 7)
        kind, scope = AlertType.PURCHASE_EXCEPTION, "ai-recognition"
    else:
        checker.result = _confirmed_duplicate(inquiry, at=NOW, repeated=True)
        kind, scope = AlertType.DUPLICATE_ORDER, ""
    flow.poll_and_process(reader, SHEET, now=NOW)
    old, = [row for row in alert_rows(ledger, inquiry) if row[1:3] == (kind.value, scope)]
    ledger.record_missing_customer(inquiry, NOW)
    for alert_type in (AlertType.SECURITY_EVENT, AlertType.NOTIFICATION_FAILED, AlertType.PURCHASE_EXCEPTION, AlertType.DATA_QUALITY):
        ledger.raise_alert(inquiry_id=inquiry, alert_type=alert_type,
            reason_code=ReasonCode.UNKNOWN_EXTERNAL_FAILURE,
            event=WorkflowEvent(f"unrelated-{alert_type}", inquiry, EventType.SECURITY_CHECK_FAILED, NOW, "workflow"))
    unrelated = {row[0] for row in alert_rows(ledger, inquiry) if row[0] != old[0]}
    before = {e.event_id: e for e in ledger.event_history(inquiry)}
    if not fails_again:
        checker.result = _confirmed_duplicate(inquiry, at=NOW, repeated=False)
        def success(command):
            # Fake-only canonical durable submission/reconciliation, no INSO I/O.
            ledger.set_purchase_state(inquiry, command.command_id, PurchaseOutcome.AI_RECOGNIZED, at=NOW)
            ledger.begin_save_dispatch(inquiry, at=NOW, save_and_send=True)
            ledger.record_submit_click(inquiry, at=NOW)
            outcome = ledger.reconcile_unknown_save(inquiry, FakeSaveReconciler(
                ReconciliationResult(ReconciliationOutcome.CONFIRMED_SAVED, NOW, saved_record_ref="rec_" + "0"*32, candidate_count=1, authoritative=True, verified_fields=("mpn", "submission_time", "new_record"))), at=NOW)
            return PurchaseDraftResult(command.command_id, outcome, NOW)
        writer.prepare = success
    reader.row = replace(reader.row, cells={**reader.row.cells, "E": "FIXED", "G": 9})
    record, = query_pending_records(reader, SHEET)
    result, = flow.rerun_unsubmitted(inquiry, record, reader, now=NOW + timedelta(minutes=1))
    after = {e.event_id: e for e in ledger.event_history(inquiry)}
    assert all(after[key] == event for key, event in before.items())
    rows = alert_rows(ledger, inquiry)
    recovered, = [row for row in rows if row[0] == old[0]]
    assert recovered[3] == 0 and recovered[4]
    assert after[recovered[4]].event_type is EventType.HUMAN_RESOLUTION_RECORDED
    assert sum(e.event_type is EventType.HUMAN_RESOLUTION_RECORDED for e in after.values()) == 1
    assert any(e.event_type is EventType.ALERT_RECOVERED for e in after.values())
    assert unrelated <= {row[0] for row in rows if row[3] == 1}
    current = [row for row in rows if row[1:3] == (kind.value, scope) and row[3] == 1]
    assert bool(current) == fails_again
    if fails_again:
        assert all(row[0] != old[0] for row in current)
    else:
        assert result.business_state is BusinessState.PURCHASE_RECORDED
        # Isolate the unrelated alerts to prove stale recovered alerts aren't projected.
        state = read_v12_order_state(ledger, inquiry)
        assert not any(a.alert_type.value == kind.value and a.reason_code in
            {ReasonCode.AI_RECOGNITION_MISMATCH.value, ReasonCode.DUPLICATE_ORDER_DETECTED.value} for a in state.active_alerts)


def test_success_without_unrelated_alerts_is_not_red_and_ordinary_resolution_does_not_recover(tmp_path):
    flow, _store, ledger, _, _, _, writer, _ = _make_flow(tmp_path,
        facts=ResearchBusinessFacts("货足", Decimal(10), Decimal(2)))
    reader = FakeSheetsReader()
    writer._recognized = ("WRONG", "Brand-X", 7)
    result, = flow.poll_and_process(reader, SHEET, now=NOW)
    inquiry = result.inquiry_id
    ledger.set_business_state(inquiry, BusinessState.QUEUED,
        WorkflowEvent("ordinary", inquiry, EventType.HUMAN_RESOLUTION_RECORDED, NOW, "workflow"))
    assert any(a.alert_type is AlertType.PURCHASE_EXCEPTION for a in ledger.active_alerts(inquiry))
    writer._recognized = (None, None, None)
    record, = query_pending_records(reader, SHEET)
    flow.rerun_unsubmitted(inquiry, record, reader, now=NOW + timedelta(minutes=1))
    state = read_v12_order_state(ledger, inquiry)
    order = Order(inquiry, "Mpn-1", "Brand-X", 7, "", None, None, OrderStatus.COMPLETED)
    assert not ledger.active_alerts(inquiry) and _order_row_style(order, NOW, state) != "error"
