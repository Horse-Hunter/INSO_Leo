"""Synthetic Owner actions; no real browser, Sheets, procurement or SMTP."""
from datetime import timedelta
from decimal import Decimal
from threading import Thread
from types import SimpleNamespace

import pytest

from src.gui.contracts import Order, OrderStatus, RunState
from src.launcher import backend as launcher
from src.launcher.manual_order import SingleRowReader, current_record
from src.sheets import WorksheetRow
from src.workflow.v12_contracts import BusinessState, EventType, WorkflowEvent
from src.workflow.v12_flow import ResearchBusinessFacts
from tests.workflow.test_v12_flow import NOW, SHEET, _make_flow


class Reader:
    def __init__(self, model="OLD", brand="Brand", quantity=7, status="未发"):
        self.rows = [WorksheetRow(3, {"A": status, "C": "A", "D": "Customer", "E": model, "F": brand, "G": quantity})]
        self.reads = 0
    def read_rows(self, worksheet):
        self.reads += 1
        return tuple(self.rows)


def prepared(tmp_path, monkeypatch):
    facts = ResearchBusinessFacts("货足", Decimal(10), Decimal(2))
    flow, store, ledger, research, _checker, _, writer, _ = _make_flow(tmp_path, facts=facts)
    source = Reader()
    result, = flow.poll_and_process(source, SHEET, now=NOW)
    backend = launcher.ProductionBackend(root=tmp_path)
    backend._store, backend._v12_store = store, ledger
    backend._v12_composition = SimpleNamespace(coordinator=flow)
    backend._manual_reader = source
    backend._state = RunState.RUNNING
    backend._next_poll_at = NOW + timedelta(minutes=15)
    backend._history = (Order(result.inquiry_id, "OLD", "Brand", 7, "货足", None, None, OrderStatus.COMPLETED, importance="A"),)
    monkeypatch.setattr(launcher, "utc_now", lambda: NOW)
    monkeypatch.setattr(backend, "_refresh", lambda: None)
    monkeypatch.setattr(backend, "_refresh_history", lambda **kw: None)
    return backend, flow, store, ledger, source, research, writer, result.inquiry_id


def test_purchase_retry_rereads_changed_fields_reuses_coordinator_and_same_inquiry(tmp_path, monkeypatch):
    backend, _, store, ledger, source, research, writer, inquiry = prepared(tmp_path, monkeypatch)
    before = ledger.event_history(inquiry)
    source.rows[0] = WorksheetRow(3, {"A": "未发", "C": "S", "E": "FIXED", "F": "NewBrand", "G": 19})
    backend._execute_order_action(("request", inquiry, "purchase", None, None))
    assert backend.get_manual_order_result().success
    assert len(research.inputs) == 2 and len(writer.commands) == 2
    assert research.inputs[-1].mpn == "FIXED" and research.inputs[-1].quantity == 19
    assert writer.commands[-1].mpn == "FIXED" and writer.commands[-1].customer_tier == "A"
    assert writer.commands[-1].brand == "Brand-X"  # Existing Research resolves the brand.
    assert len(store.all_items()) == 1 and store.get_by_inquiry_id(inquiry).importance_raw == "S"
    after = {event.event_id: event for event in ledger.event_history(inquiry)}
    assert all(after[event.event_id] == event for event in before)
    assert backend.get_result_history()[0].model == "FIXED"


@pytest.mark.parametrize("event,state", [
    (EventType.SAVE_DISPATCH_ARMED, BusinessState.PURCHASE_DRAFTING),
    (EventType.SAVE_CLICK_COMPLETED, BusinessState.PURCHASE_DRAFTING),
    (EventType.SAVE_OUTCOME_UNKNOWN, BusinessState.PURCHASE_EXCEPTION),
    (EventType.PURCHASE_DATA_SAVED, BusinessState.PURCHASE_RECORDED),
])
def test_sent_and_ambiguous_purchase_never_research_or_resend(tmp_path, monkeypatch, event, state):
    backend, _, store, ledger, _source, research, writer, inquiry = prepared(tmp_path, monkeypatch)
    ledger.set_business_state(inquiry, state, WorkflowEvent("danger", inquiry, event, NOW, "workflow"))
    before = store.get_by_inquiry_id(inquiry)
    assert not backend.can_order_action(inquiry, "purchase")
    backend._execute_order_action(("request", inquiry, "purchase", None, None))
    assert not backend.get_manual_order_result().success
    assert len(research.inputs) == len(writer.commands) == 1
    assert store.get_by_inquiry_id(inquiry) == before


@pytest.mark.parametrize("status", ["发给采购", "采购已报价", "成交"])
def test_purchase_current_status_gate_does_not_write_status(tmp_path, monkeypatch, status):
    backend, _, _, _, source, research, writer, inquiry = prepared(tmp_path, monkeypatch)
    source.rows[0] = WorksheetRow(3, {**source.rows[0].cells, "A": status})
    backend._execute_order_action(("request", inquiry, "purchase", None, None))
    assert not backend.get_manual_order_result().success
    assert len(research.inputs) == len(writer.commands) == 1
    assert source.rows[0].cells["A"] == status


@pytest.mark.parametrize("field,value,column", [("model", "FIXED", "E"), ("brand", "NEW", "F"),
    ("quantity", 22, "G"), ("importance", "S", "C")])
def test_edit_writes_only_one_raw_cell_and_updates_gui_after_readback(tmp_path, monkeypatch, field, value, column):
    backend, _, store, _, source, _, _, inquiry = prepared(tmp_path, monkeypatch)
    original = store.get_by_inquiry_id(inquiry)
    calls = []
    class Service:
        def spreadsheets(self): return self
        def values(self): return self
        def update(self, **kw):
            calls.append(kw)
            source.rows[0] = WorksheetRow(3, {**source.rows[0].cells, column: kw["body"]["values"][0][0]})
            return self
        def execute(self): return {}
    backend._manual_write_service = Service
    backend._execute_order_action(("request", inquiry, "edit", field, value))
    assert backend.get_manual_order_result().success
    assert len(calls) == 1 and calls[0]["range"] == f"'2026'!{column}3"
    assert calls[0]["valueInputOption"] == "RAW" and calls[0]["body"]["values"] == [[value]]
    assert getattr(backend.get_result_history()[0], field) == value
    assert store.get_by_inquiry_id(inquiry) == original  # Old submitted/input audit is not forged.
    assert source.rows[0].cells["A"] == "未发" and source.reads >= 3


def test_unconfirmed_write_keeps_old_display_and_never_repeats(tmp_path, monkeypatch):
    backend, _, _, _, _source, _, _, inquiry = prepared(tmp_path, monkeypatch)
    calls = []
    class Service:
        def spreadsheets(self): return self
        def values(self): return self
        def update(self, **kw): calls.append(kw); return self
        def execute(self): return {}
    backend._manual_write_service = Service
    backend._execute_order_action(("request", inquiry, "edit", "model", "FIXED"))
    assert not backend.get_manual_order_result().success
    assert backend.get_result_history()[0].model == "OLD" and len(calls) == 1


def test_only_idle_accepts_one_command_and_stop_cancels_queued_request(tmp_path, monkeypatch):
    backend, _, _, _, _, _, _, inquiry = prepared(tmp_path, monkeypatch)
    assert backend.request_order_action(inquiry, "purchase") is None
    assert backend.request_order_action(inquiry, "purchase") is not None
    backend.request_stop_after_cycle()
    assert backend._wait_between_polls(900)
    assert backend.get_manual_order_result() is None


def test_actor_is_serial_and_restarts_full_countdown_after_command(tmp_path, monkeypatch):
    backend, _, _, _, _, _, _, inquiry = prepared(tmp_path, monkeypatch)
    observed = []
    def execute(request):
        assert backend._manual_busy and not backend._poll_idle.is_set()
        assert not backend.can_order_action(inquiry, "edit")
        observed.append(request)
    monkeypatch.setattr(backend, "_execute_order_action", execute)
    assert backend.request_order_action(inquiry, "purchase") is None
    thread = Thread(target=lambda: backend._wait_between_polls(900))
    thread.start()
    from tests.launcher.test_backend import _wait_until
    assert _wait_until(lambda: bool(observed) and not backend._manual_busy)
    assert backend.get_status().next_poll_at == NOW + timedelta(minutes=15)
    backend._stop.set()
    thread.join(timeout=2)
    assert not thread.is_alive() and len(observed) == 1


def test_current_source_reads_exact_original_row_and_refuses_deleted_row():
    source = Reader()
    source.rows.append(WorksheetRow(4, {"A": "未发", "E": "OTHER"}))
    record, status = current_record(source, SHEET, 3)
    assert record.model == "OLD" and status == "未发"
    assert len(SingleRowReader(source, SHEET, 3).read_rows(SHEET)) == 1
    source.rows.pop(0)
    with pytest.raises(ValueError): current_record(source, SHEET, 3)


@pytest.mark.parametrize("field,value", [("quantity", "0"), ("quantity", "-1"),
    ("quantity", "1.5"), ("quantity", "NaN"), ("importance", "X"),
    ("model", "  "), ("brand", ""), ("status", "未发")])
def test_invalid_edit_is_rejected_before_queue_or_write(tmp_path, monkeypatch, field, value):
    backend, _, _, _, _, _, _, inquiry = prepared(tmp_path, monkeypatch)
    assert backend.request_order_action(inquiry, "edit", field=field, value=value)
    assert backend._manual_request is None


def test_quote_rerun_changed_fields_binds_only_selected_original_row(tmp_path, monkeypatch):
    from src.launcher.manual_order import InquiryHolds
    from src.workflow.v13_quotation import QuotationOutcome, V13QuotationCycle
    from tests.workflow.test_v13_quotation import Operations, Quotes
    backend, _, store, _, source, _, _, inquiry = prepared(tmp_path, monkeypatch)
    original = store.get_by_inquiry_id(inquiry)
    source.rows = [WorksheetRow(3, {"A": "发给采购", "C": "B", "E": "FIXED", "F": "NewBrand", "G": 19}),
        WorksheetRow(4, {"A": "发给采购", "C": "A", "E": "OTHER", "F": "Brand", "G": 5})]
    holds = SimpleNamespace(active=lambda: (("another-inquiry", "", "", "ROW_FAILED", 1),), close=lambda key: closed.append(key))
    closed, outcomes = [], []
    quotes = Quotes([()])
    def runner(worksheet, *, source_reader, source_store, hold_store):
        assert isinstance(hold_store, InquiryHolds) and hold_store.active() == ()
        assert source_store.get_by_inquiry_id(inquiry).mpn == "FIXED"
        outcomes.extend(V13QuotationCycle(reader=source_reader, store=source_store,
            operations=Operations(), clock=lambda: NOW, wait=lambda _: False,
            quote_reader=quotes).run(worksheet))
    backend._manual_quote = runner, holds
    backend._execute_order_action(("request", inquiry, "quotation", None, None))
    assert backend.get_manual_order_result().success
    assert closed == [inquiry] and len(quotes.calls) == 1 and quotes.calls[0][1] == "FIXED"
    assert len(outcomes) == 1 and outcomes[0].inquiry_id == inquiry
    assert outcomes[0].outcome is QuotationOutcome.NO_RECENT_QUOTE
    assert store.get_by_inquiry_id(inquiry) == original
    assert backend.get_result_history()[0].quantity == 19


def test_confirmed_script_pending_same_source_never_repeats(tmp_path, monkeypatch):
    import json
    backend, _, _, _, source, _, _, inquiry = prepared(tmp_path, monkeypatch)
    source.rows[0] = WorksheetRow(3, {**source.rows[0].cells, "A": "发给采购"})
    called = []
    observed = json.dumps({"identifying_snapshot": {"model": "OLD", "brand": "Brand", "quantity": 7}})
    holds = SimpleNamespace(active=lambda: ((inquiry, "", observed, "SOURCE_STATUS_NOT_UPDATED", 1),),
        close=lambda key: called.append(key))
    backend._manual_quote = lambda *a, **kw: called.append("runner"), holds
    backend._execute_order_action(("request", inquiry, "quotation", None, None))
    assert not backend.get_manual_order_result().success and called == []
