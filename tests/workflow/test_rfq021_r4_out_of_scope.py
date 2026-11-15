"""RFQ-021-R4: a controlled run must not touch history it did not name.

The R3 review audited `PurchaseCompletionActions`. The R4 review found the
earlier stage: `V12WorkflowCoordinator.initialize_run_state()` and
`discover_pending()` both loop over `all_items()` and mutate any historical
order -- quarantine it, close it, skip it, recover its alerts -- *before*
`prepare_pending()` applies `_inquiry_ids`. So a one-order trial could rewrite
the state, events and alerts of every parked order in the ledger.

These tests are the negative proof. Each one sets up two orders with the same
mutation preconditions, scopes the coordinator to one of them, and asserts the
other keeps its exact state/events/alerts. The legacy unscoped coordinator is
covered too, because a scope must narrow the run without changing what an
unscoped run does.
"""

from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime
from uuid import uuid4

from src.sheets import WorksheetIdentity, WorksheetRow
from src.sheets.pending import query_pending_records
from src.workflow import WorkflowStateStore, WorkflowStatus
from src.workflow.v12_contracts import (
    AlertType,
    BusinessState,
    EventType,
    ReasonCode,
    WorkflowEvent,
)
from src.workflow.v12_flow import V12WorkflowCoordinator
from src.workflow.v12_store import V12Store, migrate_v12

NOW = datetime(2026, 11, 15, 2, tzinfo=UTC)
SHEET = WorksheetIdentity("synthetic-sheet", "2026")


class TwoRowReader:
    """Two orders on the same worksheet: row 3 and row 4, distinct models."""

    def __init__(self, status: str = "未发") -> None:
        self.rows = tuple(
            WorksheetRow(position, {
                "A": status,
                "C": "A",
                "D": "Synthetic Customer",
                "E": f"Mpn-{position}",
                "F": "Brand-X",
                "G": 7,
            })
            for position in (3, 4)
        )

    def read_rows(self, worksheet: WorksheetIdentity):
        assert worksheet == SHEET
        return self.rows


def _event(inquiry_id: str, event_type: EventType, at: datetime = NOW) -> WorkflowEvent:
    return WorkflowEvent(f"evt_{uuid4().hex}", inquiry_id, event_type, at, "workflow")


def _ledger(tmp_path):
    database = tmp_path / "workflow.sqlite3"
    workflow_store = WorkflowStateStore(database)
    migrate_v12(database, tmp_path / "backups", quiesce=lambda: nullcontext(), clock=lambda: NOW)
    return workflow_store, V12Store(database)


def _two_orders(tmp_path):
    """Enqueue both rows and return their real inquiry identities."""

    workflow_store, v12_store = _ledger(tmp_path)
    records = query_pending_records(TwoRowReader(), SHEET)
    assert len(records) == 2
    for record in records:
        assert workflow_store.enqueue(record, now=NOW) is True
    in_scope = workflow_store.inquiry_id_for(records[0].record_identity)
    out_of_scope = workflow_store.inquiry_id_for(records[1].record_identity)
    assert in_scope != out_of_scope
    return workflow_store, v12_store, records, in_scope, out_of_scope


def _coordinator(workflow_store, v12_store, *, inquiry_ids):
    return V12WorkflowCoordinator(
        workflow_store, v12_store, None, None, None, None, None, (),
        inquiry_ids=inquiry_ids,
    )


def _park(v12_store, inquiry_id, state, event_type=EventType.HUMAN_RESOLUTION_RECORDED):
    v12_store.set_business_state(inquiry_id, state, _event(inquiry_id, event_type))


def _open_data_quality_alert(v12_store, inquiry_id):
    return v12_store.raise_alert(
        inquiry_id=inquiry_id,
        alert_type=AlertType.DATA_QUALITY,
        reason_code=ReasonCode.INQUIRY_QUANTITY_INVALID,
        event=_event(inquiry_id, EventType.DATA_QUALITY_INVALID_INPUT),
    )


def _snapshot(v12_store, inquiry_id):
    return (
        v12_store.business_state(inquiry_id),
        tuple((e.event_type, e.reason_code) for e in v12_store.event_history(inquiry_id)),
        tuple((a.alert_type, a.reason_code) for a in v12_store.active_alerts(inquiry_id)),
    )


# --- initialize_run_state ----------------------------------------------------


def test_initialize_run_state_quarantines_only_the_named_orders(tmp_path):
    workflow_store, v12_store, _records, in_scope, out_of_scope = _two_orders(tmp_path)
    # Same precondition on both: a state that cannot be a safe read retry.
    for inquiry_id in (in_scope, out_of_scope):
        _park(v12_store, inquiry_id, BusinessState.RESEARCHING,
              EventType.RESEARCH_STARTED)

    before = _snapshot(v12_store, out_of_scope)
    _coordinator(workflow_store, v12_store, inquiry_ids=frozenset({in_scope})).initialize_run_state(now=NOW)

    assert v12_store.business_state(in_scope) is BusinessState.INTERRUPTED_UNSENT
    assert workflow_store.get_by_inquiry_id(in_scope).status is WorkflowStatus.MANUAL_REVIEW

    assert _snapshot(v12_store, out_of_scope) == before
    assert v12_store.business_state(out_of_scope) is BusinessState.RESEARCHING
    assert workflow_store.get_by_inquiry_id(out_of_scope).status is WorkflowStatus.QUEUED


def test_initialize_run_state_still_quarantines_everything_when_unscoped(tmp_path):
    workflow_store, v12_store, _records, first, second = _two_orders(tmp_path)
    for inquiry_id in (first, second):
        _park(v12_store, inquiry_id, BusinessState.RESEARCHING, EventType.RESEARCH_STARTED)

    _coordinator(workflow_store, v12_store, inquiry_ids=None).initialize_run_state(now=NOW)

    assert v12_store.business_state(first) is BusinessState.INTERRUPTED_UNSENT
    assert v12_store.business_state(second) is BusinessState.INTERRUPTED_UNSENT


# --- discover_pending: the alert-recovery branch -----------------------------


def test_discover_pending_does_not_recover_alerts_of_unnamed_orders(tmp_path):
    workflow_store, v12_store, _records, in_scope, out_of_scope = _two_orders(tmp_path)
    for inquiry_id in (in_scope, out_of_scope):
        _park(v12_store, inquiry_id, BusinessState.HUMAN_COMPLETED)
        _open_data_quality_alert(v12_store, inquiry_id)
    assert _snapshot(v12_store, out_of_scope)[2], "precondition: an open alert exists"

    before = _snapshot(v12_store, out_of_scope)
    _coordinator(workflow_store, v12_store, inquiry_ids=frozenset({in_scope})).discover_pending(
        TwoRowReader(), SHEET, now=NOW)

    assert _snapshot(v12_store, in_scope)[2] == (), "the named order is still cleaned up"
    assert _snapshot(v12_store, out_of_scope) == before


def test_discover_pending_does_not_close_an_unnamed_owner_completed_order(tmp_path):
    """The Owner marked both rows 成交 by hand; a row-3-only trial must not close row 4."""

    workflow_store, v12_store, _records, in_scope, out_of_scope = _two_orders(tmp_path)
    for inquiry_id in (in_scope, out_of_scope):
        _park(v12_store, inquiry_id, BusinessState.INTERRUPTED_UNSENT)

    before = _snapshot(v12_store, out_of_scope)
    # "成交" is a completed sheet status. It is no longer a *pending* row, so
    # discovery returns nothing; the mutation comes from the existing-item loop.
    assert query_pending_records(TwoRowReader(status="成交"), SHEET) == ()
    _coordinator(workflow_store, v12_store, inquiry_ids=frozenset({in_scope})).discover_pending(
        TwoRowReader(status="成交"), SHEET, now=NOW)

    assert v12_store.business_state(in_scope) is BusinessState.HUMAN_COMPLETED
    assert _snapshot(v12_store, out_of_scope) == before


def test_discover_pending_still_closes_owner_completed_rows_when_unscoped(tmp_path):
    workflow_store, v12_store, _records, first, second = _two_orders(tmp_path)
    for inquiry_id in (first, second):
        _park(v12_store, inquiry_id, BusinessState.HUMAN_COMPLETED)
        _open_data_quality_alert(v12_store, inquiry_id)

    _coordinator(workflow_store, v12_store, inquiry_ids=None).discover_pending(
        TwoRowReader(), SHEET, now=NOW)

    assert _snapshot(v12_store, first)[2] == ()
    assert _snapshot(v12_store, second)[2] == ()
