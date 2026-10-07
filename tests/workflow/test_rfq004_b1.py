import sqlite3
from dataclasses import replace

import pytest

from src.sheets import WorksheetIdentity, WorksheetRow
from src.sheets.brand_write import SheetRecordConflict
from src.sheets.quotation_candidates import relocate_quotation_source
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_quotation import QuotationOutcome, RowErrorReason
from tests.inso.test_v13_quotation_read import quote
from tests.workflow.test_v13_quotation import WS, cycle, failure, item, source


def test_valid_bad_valid_source_order_fresh_tabs_and_no_row_retry():
    service, operations, quotes, waits = cycle([(quote(),), ()],
        sources=[source(12, model="C"), source(11, model="orphan"), source(10)],
        items=[item(10), item(12, model="C")])
    results = service.run(WS)
    assert [r.source_row_position for r in results] == [10, 11, 12]
    assert [r.outcome for r in results] == [QuotationOutcome.QUOTE_FOUND,
        QuotationOutcome.ROW_FAILED, QuotationOutcome.NO_RECENT_QUOTE]
    assert results[1].row_error_reason is RowErrorReason.SOURCE_IDENTITY_UNRESOLVED
    assert results[1].inquiry_id is None and results[1].record_identity is None
    assert results[1].source_worksheet == WS
    assert [t.inquiry_id for t in operations.tabs] == ["original-10", "original-12"]
    assert len(quotes.calls) == 2 and operations.tabs[0] is not operations.tabs[1]
    assert all(t.closed for t in operations.tabs) and waits == []


def test_two_same_snapshots_at_original_positions_keep_distinct_inquiries():
    first, second = item(10), item(11)
    service, operations, _, waits = cycle([(), ()],
        sources=[source(10), source(11)], items=[second, first])
    results = service.run(WS)
    assert [r.inquiry_id for r in results] == [first.inquiry_id, second.inquiry_id]
    assert all(r.outcome is QuotationOutcome.NO_RECENT_QUOTE for r in results)
    assert results[0].record_identity is first.record_identity
    assert results[1].record_identity is second.record_identity
    assert len(operations.tabs) == 2 and waits == []


def test_original_position_replaced_unique_fallback_keeps_original_identity():
    original = item(10)
    service, _, _, _ = cycle([()], sources=[source(10, status="未发", model="other"), source(25)],
                             items=[original])
    result, = service.run(WS)
    assert result.inquiry_id == original.inquiry_id
    assert result.record_identity is original.record_identity
    assert result.record_identity.row_position == 10 and result.source_row_position == 25


def test_ambiguous_relocation_marks_related_rows_only_then_continues():
    service, operations, _, waits = cycle([()],
        sources=[source(10, status="未发", model="other"), source(25), source(26), source(27, model="valid")],
        items=[item(10), item(27, model="valid")])
    results = service.run(WS)
    assert [r.outcome for r in results] == [QuotationOutcome.ROW_FAILED, QuotationOutcome.ROW_FAILED,
                                          QuotationOutcome.NO_RECENT_QUOTE]
    assert all(r.row_error_reason is RowErrorReason.SOURCE_IDENTITY_AMBIGUOUS for r in results[:2])
    assert len(operations.tabs) == 1 and waits == []


def test_two_history_inquiries_competing_for_one_current_row_are_row_failure():
    service, operations, _, waits = cycle([()],
        sources=[source(20), source(30, model="valid")],
        items=[item(20), item(21), item(30, model="valid")])
    failed, valid = service.run(WS)
    assert failed.outcome is QuotationOutcome.ROW_FAILED
    assert failed.row_error_reason is RowErrorReason.SOURCE_IDENTITY_AMBIGUOUS
    assert failed.inquiry_id is None
    assert valid.inquiry_id == "original-30"
    assert len(operations.tabs) == 1 and waits == []


@pytest.mark.parametrize("mpn", ["", "   ", None, 123])
def test_missing_or_non_string_mpn_is_row_failure_then_next_row(mpn):
    service, operations, _, waits = cycle([()], sources=[source(2, model=mpn), source(3, model="valid")],
                                         items=[item(3, model="valid")])
    bad, valid = service.run(WS)
    assert bad.row_error_reason is RowErrorReason.SOURCE_MPN_UNAVAILABLE
    assert bad.outcome is QuotationOutcome.ROW_FAILED
    assert valid.outcome is QuotationOutcome.NO_RECENT_QUOTE
    assert len(operations.tabs) == 1 and waits == []


@pytest.mark.parametrize("field,value", [("A", "采购已报价"), ("E", "edited"), ("F", "edited"),
                                        ("G", "6"), ("C", "B")])
def test_preread_source_conflict_only_fails_current_row(field, value):
    service, operations, _, waits = cycle([()], sources=[source(2), source(3, model="valid")],
                                         items=[item(2), item(3, model="valid")])
    count = 0
    def read(worksheet):
        nonlocal count
        count += 1
        row = source(2)
        if count > 1:
            row = replace(row, cells={**row.cells, field: value})
        return [row, source(3, model="valid")]
    service._reader.read_rows = read
    bad, valid = service.run(WS)
    assert bad.row_error_reason is RowErrorReason.SOURCE_CHANGED
    assert bad.inquiry_id == "original-2" and bad.record_identity == item(2).record_identity
    assert valid.inquiry_id == "original-3"
    assert len(operations.tabs) == 1 and waits == []


@pytest.mark.parametrize("when", ["scan", "preread"])
def test_shared_sheets_read_failure_still_global_stop(when):
    service, operations, _, waits = cycle([])
    count = 0
    def read(worksheet):
        nonlocal count
        count += 1
        if when == "scan" or count > 1:
            raise RuntimeError("synthetic unsafe provider details")
        return [source(2)]
    service._reader.read_rows = read
    with pytest.raises(V12Fault) as raised:
        service.run(WS)
    assert raised.value.scope is FaultScope.GLOBAL_STOP
    assert raised.value.reason == "SHEETS_READ_UNAVAILABLE"
    assert "provider" not in str(raised.value)
    assert operations.tabs == [] and waits == []


@pytest.mark.parametrize("method", ["all_items", "get_by_inquiry_id"])
def test_shared_ledger_database_failure_still_global_stop(method):
    service, operations, _, waits = cycle([])
    def broken(*args):
        raise sqlite3.DatabaseError("synthetic database details")
    setattr(service._store, method, broken)
    with pytest.raises(V12Fault) as raised:
        service.run(WS)
    assert raised.value.scope is FaultScope.GLOBAL_STOP
    assert raised.value.reason == "WORKFLOW_LEDGER_UNAVAILABLE"
    assert operations.tabs == [] and waits == []


def test_identity_disappearing_from_readable_ledger_is_row_failure():
    service, operations, _, waits = cycle([()], sources=[source(2), source(3, model="valid")],
                                         items=[item(2), item(3, model="valid")])
    get = service._store.get_by_inquiry_id
    def lookup(inquiry_id):
        if inquiry_id == "original-2":
            raise KeyError(inquiry_id)
        return get(inquiry_id)
    service._store.get_by_inquiry_id = lookup
    bad, valid = service.run(WS)
    assert bad.row_error_reason is RowErrorReason.SOURCE_IDENTITY_UNRESOLVED
    assert valid.outcome is QuotationOutcome.NO_RECENT_QUOTE
    assert len(operations.tabs) == 1 and waits == []


def test_conflict_after_inso_retry_wait_stops_row_without_extra_retry():
    service, operations, _, waits = cycle([failure(), ()], sources=[source(2), source(3, model="valid")],
                                         items=[item(2), item(3, model="valid")])
    def wait(seconds):
        service._reader.rows = [source(2, status="采购已报价"), source(3, model="valid")]
        return False
    service._wait = lambda seconds: waits.append(seconds) or wait(seconds)
    bad, valid = service.run(WS)
    assert bad.outcome is QuotationOutcome.ROW_FAILED
    assert bad.row_error_reason is RowErrorReason.SOURCE_CHANGED
    assert valid.outcome is QuotationOutcome.NO_RECENT_QUOTE
    assert len(operations.tabs) == 2 and waits == [120]


def test_competition_created_before_query_does_not_enter_inso():
    service, operations, _, waits = cycle([])
    get = service._store.get_by_inquiry_id
    def lookup(inquiry_id):
        result = get(inquiry_id)
        service._store.items.append(item(99))
        return result
    service._store.get_by_inquiry_id = lookup
    result, = service.run(WS)
    assert result.row_error_reason is RowErrorReason.SOURCE_IDENTITY_AMBIGUOUS
    assert operations.tabs == [] and waits == []


@pytest.mark.parametrize("worksheet", ["Sheet1", "SHAHAB"])
def test_original_position_strict_validation_and_persisted_updated_brand(worksheet):
    original = item(10)
    identity = replace(original.record_identity, worksheet=WorksheetIdentity("fake-sheet", worksheet))
    if worksheet == "SHAHAB":
        identity = replace(identity, identifying_snapshot=replace(identity.identifying_snapshot, importance_raw=None))
        row = WorksheetRow(10, {"B": "发给采购", "D": "MPN", "E": "resolved", "F": "5"})
    else:
        row = source(10, brand="resolved")
    assert relocate_quotation_source(identity, [row, replace(row, row_position=11)], expected_brand="resolved") is row
    with pytest.raises(SheetRecordConflict):
        relocate_quotation_source(identity, [row], expected_brand="brand")


def test_preread_original_ledger_identity_change_is_isolated():
    service, operations, _, waits = cycle([()], sources=[source(2), source(3, model="valid")],
                                         items=[item(2), item(3, model="valid")])
    original = service._store.items[0].record_identity
    get = service._store.get_by_inquiry_id
    def lookup(inquiry_id):
        result = get(inquiry_id)
        if inquiry_id == "original-2":
            result.record_identity = replace(original, row_position=99)
        return result
    service._store.get_by_inquiry_id = lookup
    failed, valid = service.run(WS)
    assert failed.row_error_reason is RowErrorReason.SOURCE_CHANGED
    assert failed.record_identity is original
    assert valid.outcome is QuotationOutcome.NO_RECENT_QUOTE
    assert len(operations.tabs) == 1 and waits == []


def test_preread_binding_to_another_inquiry_cannot_replace_original_id():
    service, operations, _, waits = cycle([])
    original = service._store.items[0]
    replacement = item(99)
    calls = 0
    def items():
        nonlocal calls
        calls += 1
        return [original] if calls == 1 else [replacement]
    service._store.all_items = items
    failed, = service.run(WS)
    assert failed.row_error_reason is RowErrorReason.SOURCE_CHANGED
    assert failed.inquiry_id == original.inquiry_id
    assert failed.record_identity is original.record_identity
    assert operations.tabs == [] and waits == []
