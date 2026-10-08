from dataclasses import replace

import pytest

from src.sheets import (
    IdentifyingSnapshot,
    SheetRecordIdentity,
    WorksheetIdentity,
    WorksheetRow,
)
from src.sheets.brand_write import SheetRecordConflict
from src.sheets.google_writer import GoogleSheetsPurchaseStatusWriter
from src.sheets.purchase_status import write_purchase_status_safely
from src.sheets.worksheet_schema import worksheet_schema


class Sheet:
    def __init__(self, title="2026", status="未发"):
        self.worksheet = WorksheetIdentity("synthetic-sheet", title)
        s = worksheet_schema(title)
        self.rows = [WorksheetRow(9, {s.status_column: status, s.model_column: "TEST-MPN",
                      s.quantity_column: 8, s.brand_column: "Brand",
                      **({s.importance_column: "A"} if s.importance_column else {})})]
        self.calls = []
        self.identity = SheetRecordIdentity(self.worksheet, 3,
            IdentifyingSnapshot("未发", "A" if s.importance_column else None, "TEST-MPN", "Brand", 8))

    def read_rows(self, _worksheet):
        return self.rows

    def write_purchase_status(self, worksheet, row_position):
        self.calls.append((worksheet, row_position))
        column = worksheet_schema(worksheet.worksheet).status_column
        self.rows = [replace(r, cells={**r.cells, column: "发给采购"})
                     if r.row_position == row_position else r for r in self.rows]


@pytest.mark.parametrize("title", ["2026", "shahab"])
def test_relocated_single_cell_transition_and_idempotence(title):
    sheet = Sheet(title)
    before = dict(sheet.rows[0].cells)
    assert write_purchase_status_safely(sheet, sheet, sheet.identity)
    assert sheet.calls == [(sheet.worksheet, 9)]
    column = worksheet_schema(title).status_column
    assert sheet.rows[0].cells == {**before, column: "发给采购"}
    assert not write_purchase_status_safely(sheet, sheet, sheet.identity)
    assert len(sheet.calls) == 1


@pytest.mark.parametrize("status", ["已发", "处理中", "", None])
def test_other_status_is_never_overwritten(status):
    sheet = Sheet(status=status)
    with pytest.raises(SheetRecordConflict):
        write_purchase_status_safely(sheet, sheet, sheet.identity)
    assert sheet.calls == []


@pytest.mark.parametrize("second_status", ["未发", "发给采购"])
def test_duplicate_or_mixed_status_matches_fail_closed(second_status):
    sheet = Sheet()
    sheet.rows.append(replace(sheet.rows[0], row_position=10,
                             cells={**sheet.rows[0].cells, "A": second_status}))
    with pytest.raises(SheetRecordConflict):
        write_purchase_status_safely(sheet, sheet, sheet.identity)
    assert sheet.calls == []


def test_changed_quantity_is_not_the_original_order():
    sheet = Sheet()
    sheet.rows[0] = replace(sheet.rows[0], cells={**sheet.rows[0].cells, "G": 9})
    with pytest.raises(SheetRecordConflict):
        write_purchase_status_safely(sheet, sheet, sheet.identity)
    assert sheet.calls == []


@pytest.mark.parametrize(("title", "column"), [("2026", "A"), ("shahab", "B")])
def test_google_writer_only_uses_status_cell(title, column):
    class Service:
        def spreadsheets(self): return self
        def values(self): return self
        def update(self, **kwargs):
            self.kwargs = kwargs
            return self
        def execute(self): return {}
    service = Service()
    GoogleSheetsPurchaseStatusWriter(service).write_purchase_status(WorksheetIdentity("test", title), 7)
    assert service.kwargs["range"] == f"'{title}'!{column}7"
    assert service.kwargs["body"]["values"] == [["发给采购"]]
    assert service.kwargs["valueInputOption"] == "RAW"


@pytest.mark.parametrize("title", ["2026", "SHAHAB"])
def test_quotation_terminal_is_satisfied_without_purchase_status_downgrade(title):
    from src.sheets.purchase_status import purchase_status_satisfied
    sheet = Sheet(title, status="采购已报价")
    assert purchase_status_satisfied(sheet, sheet.identity)
    assert not write_purchase_status_safely(sheet, sheet, sheet.identity)
    assert sheet.calls == []


@pytest.mark.parametrize("column,value", [("E", "CHANGED"), ("G", 9), ("C", "B"), ("F", "OTHER")])
def test_changed_quoted_snapshot_is_not_a_completed_purchase_proof(column, value):
    from src.sheets.purchase_status import purchase_status_satisfied
    sheet = Sheet(status="采购已报价")
    sheet.rows[0] = replace(sheet.rows[0], cells={**sheet.rows[0].cells, column: value})
    with pytest.raises(SheetRecordConflict):
        purchase_status_satisfied(sheet, sheet.identity)
    assert sheet.calls == []


def test_quotation_completion_between_fresh_reads_never_writes_backward():
    sheet = Sheet()
    original = sheet.read_rows
    calls = []
    def read(worksheet):
        calls.append(worksheet)
        if len(calls) == 2:
            sheet.rows[0] = replace(sheet.rows[0], cells={**sheet.rows[0].cells, "A": "采购已报价"})
        return original(worksheet)
    sheet.read_rows = read
    assert not write_purchase_status_safely(sheet, sheet, sheet.identity)
    assert sheet.calls == []


def test_mixed_pending_and_quoted_candidates_remain_ambiguous():
    sheet = Sheet(status="采购已报价")
    sheet.rows.append(replace(sheet.rows[0], row_position=10, cells={**sheet.rows[0].cells, "A": "未发"}))
    with pytest.raises(SheetRecordConflict):
        write_purchase_status_safely(sheet, sheet, sheet.identity)
    assert sheet.calls == []
