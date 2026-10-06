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
