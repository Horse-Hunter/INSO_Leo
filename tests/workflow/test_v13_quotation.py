from datetime import timedelta
from types import SimpleNamespace

import pytest

from src.inso.duplicate_history import (
    DuplicateHistoryFailure,
    InsoDuplicateHistoryError,
)
from src.inso.quotation_read import InsoQuotationAuthenticationError
from src.sheets import (
    IdentifyingSnapshot,
    SheetRecordIdentity,
    WorksheetIdentity,
    WorksheetRow,
    query_pending_records,
    query_quotation_candidates,
)
from src.workflow.store import WorkflowStateStore
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_quotation import (
    QuotationOutcome,
    V13QuotationCycle,
    V13Stopped,
    read_v13_candidates,
)
from tests.inso.test_v13_quotation_read import NOW, quote

WS = WorksheetIdentity("fake-sheet", "Sheet1")


class Sheets:
    def __init__(self, rows):
        self.rows = rows
    def read_rows(self, worksheet):
        assert worksheet == WS
        return self.rows


def source(position, status="发给采购", model="MPN", brand="brand", quantity="5"):
    return WorksheetRow(position, {"A": status, "C": "A", "E": model, "F": brand, "G": quantity})


def item(position, model="MPN", **kwargs):
    identity = SheetRecordIdentity(WS, position, IdentifyingSnapshot("未发", "A", model, "brand", "5"))
    return SimpleNamespace(inquiry_id=f"original-{position}", record_identity=identity,
                           resolved_brand=None, brand_update_status=None, **kwargs)


class Store:
    def __init__(self, items):
        self.items = items
    def all_items(self):
        return self.items
    def get_by_inquiry_id(self, inquiry_id):
        return next(i for i in self.items if i.inquiry_id == inquiry_id)


class Operations:
    def __init__(self):
        self.events, self.tabs = [], []
        self.active, self.protected = None, False
    def open(self, inquiry_id):
        assert self.active is None
        tab = SimpleNamespace(inquiry_id=inquiry_id, closed=False)
        self.events.append(("open", inquiry_id))
        self.tabs.append(tab)
        self.active = tab
        return tab
    def close(self):
        if self.protected:
            return
        if self.active is not None:
            self.active.closed = True
            self.events.append(("close", self.active.inquiry_id))
            self.active = None
    def preserve(self):
        self.protected = True
        self.events.append(("preserve", self.active.inquiry_id))


class Quotes:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []
    def read(self, access, mpn):
        self.calls.append((access, mpn))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def cycle(responses, *, sources=None, items=None, wait=None, stop=lambda: False, fx=None):
    sheets = Sheets(sources if sources is not None else [source(2)])
    store = Store(items if items is not None else [item(2)])
    operations, quotes, waits = Operations(), Quotes(responses), []
    def fake_wait(seconds):
        assert operations.active is None
        waits.append(seconds)
        return False if wait is None else wait(seconds)
    service = V13QuotationCycle(reader=sheets, store=store, operations=operations,
                               clock=lambda: NOW, wait=fake_wait, stop_requested=stop,
                               quote_reader=quotes, fx_provider=fx)
    return service, operations, quotes, waits


def failure():
    return InsoDuplicateHistoryError(DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED)


def test_only_exact_sent_status_v12_pending_entry_unchanged():
    sheets = Sheets([source(2), source(3, "未发"), source(4, "采购已报价"), source(5, " 发给采购")])
    assert [r.row_position for r in query_quotation_candidates(sheets, WS)] == [2]
    assert [r.row_position for r in query_pending_records(sheets, WS)] == [3]


def test_moved_row_reuses_original_inquiry_and_opaque_identity():
    original = item(2)
    service, operations, _, waits = cycle([(quote(),)], sources=[source(12)], items=[original])
    result, = service.run(WS)
    assert result.inquiry_id == original.inquiry_id
    assert result.record_identity is original.record_identity
    assert result.record_identity.row_position == 2
    assert result.quotation.payload == quote().payload
    assert operations.tabs[0].closed
    assert waits == []


def test_real_workflow_store_identity_reused_without_enqueue_or_id_regeneration(tmp_path):
    store = WorkflowStateStore(tmp_path/"offline.sqlite3")
    sheets = Sheets([source(2, "未发")])
    record, = query_pending_records(sheets, WS)
    store.enqueue(record, now=NOW)
    original, = store.all_items()
    sheets.rows = [source(55)]
    candidate, = read_v13_candidates(sheets, WS, store)
    assert candidate.inquiry_id == original.inquiry_id
    assert candidate.record_identity == original.record_identity
    assert len(store.all_items()) == 1


def test_two_rows_each_fresh_tab_no_inter_row_cooldown():
    service, operations, _, waits = cycle([(), (quote(model="MPN2"),)],
        sources=[source(3, model="MPN2"), source(2)], items=[item(2), item(3, model="MPN2")])
    results = service.run(WS)
    assert [r.outcome for r in results] == [QuotationOutcome.NO_RECENT_QUOTE, QuotationOutcome.QUOTE_FOUND]
    assert [r.inquiry_id for r in results] == ["original-2", "original-3"]
    assert operations.events == [("open", "original-2"), ("close", "original-2"),
                                 ("open", "original-3"), ("close", "original-3")]
    assert operations.tabs[0] is not operations.tabs[1]
    assert all(tab.closed for tab in operations.tabs)
    assert waits == []


@pytest.mark.parametrize("attempt", [1, 2, 3, 4])
def test_shared_engine_success_on_any_attempt_with_fresh_tab_and_fake_180(attempt):
    service, operations, quotes, waits = cycle([failure()]*(attempt-1)+[(quote(),)])
    result, = service.run(WS)
    assert result.outcome is QuotationOutcome.QUOTE_FOUND
    assert len(quotes.calls) == attempt
    assert len(operations.tabs) == attempt
    assert len({id(tab) for tab in operations.tabs}) == attempt
    assert all(tab.closed for tab in operations.tabs)
    assert waits == [180]*(attempt-1)


def test_exhaustion_is_shared_global_stop_never_no_recent_quote():
    service, operations, quotes, waits = cycle([failure()]*4)
    with pytest.raises(V12Fault) as raised:
        service.run(WS)
    assert raised.value.scope is FaultScope.GLOBAL_STOP
    assert raised.value.reason == "INSO_QUERY_RETRIES_EXHAUSTED"
    assert len(quotes.calls) == 4
    assert waits == [180]*3
    assert all(tab.closed for tab in operations.tabs)


def test_fake_wait_shutdown_interrupts_before_new_tab():
    service, operations, quotes, waits = cycle([failure()], wait=lambda seconds: True)
    with pytest.raises(V13Stopped):
        service.run(WS)
    assert waits == [180]
    assert len(quotes.calls) == len(operations.tabs) == 1
    assert operations.tabs[0].closed


def test_auth_fault_global_stop_retains_page_and_does_not_process_next_row():
    service, operations, quotes, waits = cycle([InsoQuotationAuthenticationError("challenge")],
        sources=[source(2), source(3, model="MPN2")], items=[item(2), item(3, model="MPN2")])
    with pytest.raises(V12Fault) as raised:
        service.run(WS)
    assert raised.value.scope is FaultScope.GLOBAL_STOP
    assert raised.value.reason == "INSO_AUTHENTICATION_REQUIRED"
    assert operations.protected
    assert not operations.tabs[0].closed
    assert len(quotes.calls) == 1
    assert waits == []


@pytest.mark.parametrize("sources,items", [
    ([source(2)], []),
    ([source(2)], [item(2), item(3)]), ([source(2, quantity="6")], [item(2)]),
    ([source(2, brand="edited")], [item(2)]),
])
def test_orphan_ambiguous_or_changed_identity_never_invents_id(sources, items):
    service, operations, _, _ = cycle([], sources=sources, items=items)
    result, = service.run(WS)
    assert result.outcome is QuotationOutcome.ROW_FAILED
    assert result.row_error_reason.value in {"SOURCE_IDENTITY_UNRESOLVED", "SOURCE_IDENTITY_AMBIGUOUS"}
    assert operations.tabs == []


def test_persisted_brand_update_is_allowed_without_changing_original_identity():
    original = item(2)
    original.resolved_brand, original.brand_update_status = "resolved", "UPDATED"
    service, _, _, _ = cycle([()], sources=[source(9, brand="resolved")], items=[original])
    result, = service.run(WS)
    assert result.record_identity is original.record_identity
    assert result.outcome is QuotationOutcome.NO_RECENT_QUOTE


def test_status_changed_after_scan_fails_before_query():
    service, operations, _, _ = cycle([])
    sheets = service._reader
    calls = 0
    def read(worksheet):
        nonlocal calls
        calls += 1
        return [source(2)] if calls == 1 else [source(2, "采购已报价")]
    sheets.read_rows = read
    result, = service.run(WS)
    assert result.outcome is QuotationOutcome.ROW_FAILED
    assert result.row_error_reason.value == "SOURCE_CHANGED"
    assert operations.tabs == []


def test_no_recent_includes_old_only_and_future_only_without_wait():
    service, operations, _, waits = cycle([(quote(NOW-timedelta(hours=73)), quote(NOW+timedelta(seconds=1)))])
    result, = service.run(WS)
    assert result.outcome is QuotationOutcome.NO_RECENT_QUOTE
    assert result.quotation is None
    assert operations.tabs[0].closed
    assert waits == []


def test_stop_before_first_query_and_empty_source():
    service, operations, _, _ = cycle([], stop=lambda: True)
    with pytest.raises(V13Stopped):
        service.run(WS)
    assert operations.tabs == []
    service, operations, _, waits = cycle([], sources=[], items=[])
    assert service.run(WS) == ()
    assert operations.tabs == [] and waits == []


def test_cycle_selects_lower_rmb_equivalent_not_newest_and_preserves_original():
    from decimal import Decimal

    from tests.inso.test_v13_quotation_read import priced
    newer = priced(NOW, "1", "USD")
    older = priced(NOW-timedelta(hours=1), "6.0000", "RMB")
    fx = SimpleNamespace(get_quote=lambda: SimpleNamespace(rate=Decimal(7)))
    service, operations, quotes, waits = cycle([(newer, older)], fx=fx)
    result, = service.run(WS)
    assert result.quotation is older and result.quotation.payload[7] == "6.0000"
    assert len(quotes.calls) == 1 and waits == [] and operations.active is None


def test_official_fx_failure_is_global_stop_and_never_queries_next_order():
    from src.research.ecb_fx import EcbFxError
    from tests.inso.test_v13_quotation_read import priced
    def fail():
        raise EcbFxError("synthetic")
    fx = SimpleNamespace(get_quote=fail)
    service, _operations, quotes, _waits = cycle([(priced(NOW, "1", "USD"),)], fx=fx,
        sources=[source(2), source(3, model="OTHER")], items=[item(2), item(3, model="OTHER")])
    with pytest.raises(V12Fault) as raised:
        service.run(WS)
    assert raised.value.scope is FaultScope.GLOBAL_STOP and raised.value.reason == "V13_FX_UNAVAILABLE"
    assert len(quotes.calls) == 1
