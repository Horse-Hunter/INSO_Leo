"""Manual one-shot lifecycle over the canonical SQLite hold/integrated cycle."""
import sqlite3
from dataclasses import replace
from types import SimpleNamespace

import pytest

from src.launcher.manual_order import (
    SingleRowReader,
    current_record,
)
from src.sheets import WorksheetIdentity, WorksheetRow
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_integration import V13HoldStore, V13IntegratedCycle
from src.workflow.v13_quotation import (
    QuotationOutcome,
    RowErrorReason,
    V13QuotationCycle,
    V13QuotationResult,
    V13Stopped,
)
from tests.inso.test_v13_quotation_read import NOW as QUOTE_NOW
from tests.inso.test_v13_quotation_read import quote
from tests.launcher.test_manual_order import prepared
from tests.workflow.test_v12_flow import SHEET
from tests.workflow.test_v13_quotation import Operations, Quotes


def setup_hold(tmp_path, monkeypatch, *, unbound=False):
    backend, _, store, ledger, source, _, _, inquiry = prepared(tmp_path, monkeypatch)
    source.rows[0] = WorksheetRow(3, {**source.rows[0].cells, "A": "发给采购"})
    record, _ = current_record(source, SHEET, 3)
    holds = V13HoldStore(ledger.database_path)
    holds.migrate()
    observed = record.record_identity
    if unbound:
        observed = replace(observed, identifying_snapshot=replace(observed.identifying_snapshot, model=""))
    old = V13QuotationResult(None if unbound else inquiry, None if unbound else observed,
        "", QuotationOutcome.ROW_FAILED, None,
        RowErrorReason.SOURCE_MPN_UNAVAILABLE if unbound else RowErrorReason.UPDATE_RESULT_UNCONFIRMED,
        source_worksheet=SHEET, source_row_position=3)
    key, _ = holds.hold(old, observed)
    return backend, store, source, inquiry, record, holds, key


def make_cycle(reader, store, holds, quotes, *, outcome=QuotationOutcome.NO_RECENT_QUOTE):
    cycle = V13QuotationCycle(reader=reader, store=store, operations=Operations(),
        clock=lambda: QUOTE_NOW, wait=lambda _: False, quote_reader=quotes)
    def update(result):
        return replace(result, outcome=outcome,
            row_error_reason=RowErrorReason.QUOTE_INPUT_WRITE_FAILED if outcome is QuotationOutcome.ROW_FAILED else None)
    return V13IntegratedCycle(reader=reader, store=store, holds=holds, cycle=cycle,
        updater_factory=lambda: SimpleNamespace(update_one=update), notify=lambda *a: None,
        observe=lambda *a: None)


@pytest.mark.parametrize("outcome", [QuotationOutcome.NO_RECENT_QUOTE,
    QuotationOutcome.UPDATED_INSERTED, QuotationOutcome.UPDATED_ALREADY_EXISTS])
@pytest.mark.parametrize("unbound", [True, False])
def test_old_barriers_only_close_after_normal_selected_row_settlement(tmp_path, monkeypatch, outcome, unbound):
    backend, store, source, inquiry, _record, holds, old_key = setup_hold(tmp_path, monkeypatch, unbound=unbound)
    quotes = Quotes([()] if outcome is QuotationOutcome.NO_RECENT_QUOTE else [(quote(model="OLD"),)])
    calls = []
    def runner(worksheet, *, source_reader, source_store, hold_store):
        assert old_key in {r[0] for r in holds.active()}  # Durable until returned terminal result.
        assert hold_store.active() == ()
        hold_store.close(old_key)  # Canonical close cannot remove a bypassed barrier early.
        assert old_key in {r[0] for r in holds.active()}
        assert [r.row_position for r in source_reader.read_rows(worksheet)] == [3]
        result = make_cycle(source_reader, source_store, hold_store, quotes, outcome=outcome).run(worksheet)
        calls.extend(result)
        assert old_key in {r[0] for r in holds.active()}
        return result
    source.rows.append(WorksheetRow(4, {"A": "发给采购", "C": "A", "E": "OTHER", "F": "BR", "G": 2}))
    backend._manual_quote = runner, holds
    backend._execute_order_action(("r", inquiry, "quotation", None, None))
    assert backend.get_manual_order_result().success and len(calls) == 1
    assert calls[0].outcome is outcome and holds.active() == ()
    # Normal automatic invocation can query the repaired source after NO_RECENT_QUOTE.
    if outcome is QuotationOutcome.NO_RECENT_QUOTE:
        automatic_quotes = Quotes([()])
        reader = SingleRowReader(source, SHEET, 3)
        output = make_cycle(reader, store, holds, automatic_quotes).run(SHEET)
        assert output[0].outcome is outcome and len(automatic_quotes.calls) == 1


@pytest.mark.parametrize("failure", [V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE"),
    RuntimeError("synthetic unknown"), V13Stopped("STOP_REQUESTED"), None])
@pytest.mark.parametrize("unbound", [False, True])
def test_unsettled_manual_attempt_preserves_durable_old_hold_and_automatic_barrier(tmp_path, monkeypatch, failure, unbound):
    backend, store, source, inquiry, _, holds, old_key = setup_hold(tmp_path, monkeypatch, unbound=unbound)
    before = holds.active()
    def runner(*a, hold_store, **kw):
        assert hold_store.active() == () and holds.active() == before
        if failure is not None:
            raise failure
        return ()  # No terminal selected-row evidence is not settlement.
    backend._manual_quote = runner, holds
    with pytest.raises(V12Fault) as exc:
        backend._execute_order_action(("r", inquiry, "quotation", None, None))
    assert exc.value.scope is FaultScope.GLOBAL_STOP
    assert holds.active() == before and holds.active()[0][0] == old_key
    automatic_quotes = Quotes([()])
    assert make_cycle(SingleRowReader(source, SHEET, 3), store, holds, automatic_quotes).run(SHEET) == ()
    assert automatic_quotes.calls == []


@pytest.mark.parametrize("unbound", [False, True])
def test_refailure_persists_current_bound_hold_before_superseding_unresolved(tmp_path, monkeypatch, unbound):
    backend, _, _, inquiry, _, holds, old_key = setup_hold(tmp_path, monkeypatch, unbound=unbound)
    quotes = Quotes([(quote(model="OLD"),)])
    def runner(worksheet, *, source_reader, source_store, hold_store):
        result = make_cycle(source_reader, source_store, hold_store, quotes,
            outcome=QuotationOutcome.ROW_FAILED).run(worksheet)
        assert inquiry in {row[0] for row in holds.active()}
        return result
    backend._manual_quote = runner, holds
    backend._execute_order_action(("r", inquiry, "quotation", None, None))
    current, = holds.active()
    assert current[0] == inquiry and current[3] == RowErrorReason.QUOTE_INPUT_WRITE_FAILED.value
    assert current[4] == (1 if unbound else 2)
    if unbound:
        with sqlite3.connect(holds.path) as db:
            assert db.execute("SELECT active FROM workflow_v13_holds WHERE hold_key=?", (old_key,)).fetchone() == (0,)


def test_other_inquiry_worksheet_and_unresolved_row_holds_are_bytewise_untouched(tmp_path, monkeypatch):
    backend, _, _, inquiry, record, holds, old_key = setup_hold(tmp_path, monkeypatch, unbound=True)
    for bound, worksheet, row in [(True, SHEET, 3), (False, SHEET, 4),
        (False, WorksheetIdentity("other-sheet", "2026"), 3),
        (False, WorksheetIdentity(SHEET.spreadsheet, "OTHER"), 3)]:
        identity = replace(record.record_identity, worksheet=worksheet, row_position=row)
        result = V13QuotationResult("other-inquiry" if bound else None, identity, "OLD",
            QuotationOutcome.ROW_FAILED, None, RowErrorReason.SOURCE_IDENTITY_UNRESOLVED,
            source_worksheet=worksheet, source_row_position=row)
        holds.hold(result, identity)
    before = {r[0]: r for r in holds.active() if r[0] != old_key}
    def runner(worksheet, *, source_reader, source_store, hold_store):
        return make_cycle(source_reader, source_store, hold_store, Quotes([()])).run(worksheet)
    backend._manual_quote = runner, holds
    backend._execute_order_action(("r", inquiry, "quotation", None, None))
    assert {r[0]: r for r in holds.active()} == before


@pytest.mark.parametrize("unbound", [False, True])
def test_matching_confirmed_script_same_snapshot_never_bypassed(tmp_path, monkeypatch, unbound):
    backend, _, _, inquiry, record, holds, key = setup_hold(tmp_path, monkeypatch, unbound=unbound)
    holds.close(key)
    result = V13QuotationResult(None if unbound else inquiry, record.record_identity, "OLD",
        QuotationOutcome.ROW_FAILED, None, RowErrorReason.SOURCE_STATUS_NOT_UPDATED,
        source_worksheet=SHEET, source_row_position=3)
    holds.hold(result, record.record_identity)
    before = holds.active()
    backend._manual_quote = lambda *a, **kw: pytest.fail("must not repeat confirmed Script"), holds
    backend._execute_order_action(("r", inquiry, "quotation", None, None))
    assert not backend.get_manual_order_result().success and holds.active() == before


def test_row_failed_without_durable_new_hold_does_not_release_old_barrier(tmp_path, monkeypatch):
    backend, _, _, inquiry, record, holds, _ = setup_hold(tmp_path, monkeypatch)
    before = holds.active()
    result = V13QuotationResult(inquiry, record.record_identity, "OLD", QuotationOutcome.ROW_FAILED,
        None, RowErrorReason.QUOTE_INPUT_WRITE_FAILED, source_worksheet=SHEET, source_row_position=3)
    backend._manual_quote = lambda *a, **kw: (result,), holds
    with pytest.raises(V12Fault):
        backend._execute_order_action(("r", inquiry, "quotation", None, None))
    assert holds.active() == before


@pytest.mark.parametrize("status", ["未发", "采购已报价", "成交"])
def test_quote_source_status_gate_preserves_old_barrier(tmp_path, monkeypatch, status):
    backend, _, source, inquiry, _, holds, _ = setup_hold(tmp_path, monkeypatch)
    before = holds.active()
    source.rows[0] = replace(source.rows[0], cells={**source.rows[0].cells, "A": status})
    backend._manual_quote = lambda *a, **kw: pytest.fail("invalid status"), holds
    backend._execute_order_action(("r", inquiry, "quotation", None, None))
    assert not backend.get_manual_order_result().success and holds.active() == before


@pytest.mark.parametrize("unbound", [False, True])
def test_confirmed_script_modified_source_uses_manual_anchor_and_settles(tmp_path, monkeypatch, unbound):
    backend, _, source, inquiry, record, holds, key = setup_hold(tmp_path, monkeypatch, unbound=unbound)
    holds.close(key)
    result = V13QuotationResult(None if unbound else inquiry, record.record_identity, "OLD",
        QuotationOutcome.ROW_FAILED, None, RowErrorReason.SOURCE_STATUS_NOT_UPDATED,
        source_worksheet=SHEET, source_row_position=3)
    holds.hold(result, record.record_identity)
    source.rows[0] = replace(source.rows[0], cells={**source.rows[0].cells, "E": "FIXED", "F": "NEW", "G": 19})
    quotes = Quotes([()])
    def runner(worksheet, *, source_reader, source_store, hold_store):
        return make_cycle(source_reader, source_store, hold_store, quotes).run(worksheet)
    backend._manual_quote = runner, holds
    backend._execute_order_action(("r", inquiry, "quotation", None, None))
    assert backend.get_manual_order_result().success and holds.active() == ()
    assert len(quotes.calls) == 1 and quotes.calls[0][1] == "FIXED"
    assert backend.get_result_history()[0].quantity == 19


def test_stop_during_manual_invocation_preserves_old_hold_even_with_returned_result(tmp_path, monkeypatch):
    backend, _, _, inquiry, record, holds, _ = setup_hold(tmp_path, monkeypatch)
    before = holds.active()
    result = V13QuotationResult(inquiry, record.record_identity, "OLD", QuotationOutcome.NO_RECENT_QUOTE,
        None, source_worksheet=SHEET, source_row_position=3)
    def runner(*a, **kw):
        backend._stop.set()
        return (result,)
    backend._manual_quote = runner, holds
    backend._execute_order_action(("r", inquiry, "quotation", None, None))
    assert holds.active() == before



def test_final_close_database_fault_rolls_back_all_matching_old_holds(tmp_path, monkeypatch):
    backend, _, _, inquiry, record, holds, _ = setup_hold(tmp_path, monkeypatch, unbound=True)
    bound = V13QuotationResult(inquiry, record.record_identity, "OLD", QuotationOutcome.ROW_FAILED,
        None, RowErrorReason.UPDATE_RESULT_UNCONFIRMED, source_worksheet=SHEET, source_row_position=3)
    holds.hold(bound, record.record_identity)
    before = holds.active()
    result = replace(bound, outcome=QuotationOutcome.NO_RECENT_QUOTE, row_error_reason=None)
    backend._manual_quote = lambda *a, **kw: (result,), holds
    original_connect = sqlite3.connect
    class FailBatch(sqlite3.Connection):
        def executemany(self, sql, rows):
            first = next(iter(rows))
            self.execute(sql, first)
            raise sqlite3.OperationalError("synthetic close transaction failure")
    monkeypatch.setattr(sqlite3, "connect", lambda *a, **kw: original_connect(*a, **kw, factory=FailBatch))
    with pytest.raises(V12Fault) as exc:
        backend._execute_order_action(("r", inquiry, "quotation", None, None))
    assert exc.value.scope is FaultScope.GLOBAL_STOP and holds.active() == before
