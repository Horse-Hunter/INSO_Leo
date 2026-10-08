"""Owner-authorized, one-cell pending -> sent-to-purchasing transition."""
from dataclasses import replace
from typing import Protocol

from .brand_write import SheetRecordConflict, relocate_record
from .pending import SheetRecordIdentity, WorksheetIdentity, WorksheetRowReader
from .worksheet_schema import worksheet_schema


class PurchaseStatusWriter(Protocol):
    def write_purchase_status(self, worksheet: WorksheetIdentity, row_position: int) -> None: ...


def current_purchase_status(reader: WorksheetRowReader, identity: SheetRecordIdentity) -> str:
    """Read-only stable snapshot relocation, permitting only the status transition."""
    rows = tuple(reader.read_rows(identity.worksheet))
    column = worksheet_schema(identity.worksheet.worksheet).status_column
    eligible = [r for r in rows if r.cells.get(column) in {"未发", "发给采购"}]
    normalized = [replace(r, cells={**r.cells, column: "未发"}) for r in eligible]
    row = relocate_record(identity, normalized)
    schema = worksheet_schema(identity.worksheet.worksheet)
    actual = next(r for r in eligible if r.row_position == row.row_position)
    if actual.cells.get(schema.brand_column) != identity.identifying_snapshot.brand:
        raise SheetRecordConflict("source brand changed")
    return str(actual.cells[column])


def _locate_purchase_record(reader, identity, expected_brand, brand_match=None):
    if identity.identifying_snapshot.status != "未发":
        raise SheetRecordConflict("original purchase status must be pending")
    rows = tuple(reader.read_rows(identity.worksheet))
    schema = worksheet_schema(identity.worksheet.worksheet)
    eligible = [r for r in rows if r.cells.get(schema.status_column)
                in {"未发", "发给采购", "采购已报价"}]
    normalized = [replace(r, cells={**r.cells, schema.status_column: "未发"}) for r in eligible]
    target = relocate_record(identity, normalized)
    original = next(r for r in eligible if r.row_position == target.row_position)
    if original.cells[schema.status_column] != "未发":
        brand = identity.identifying_snapshot.brand if expected_brand is None else expected_brand
        actual_brand = original.cells.get(schema.brand_column)
        matches = actual_brand == brand or (brand_match is not None and brand_match(actual_brand, brand))
        if not matches:
            raise SheetRecordConflict("completed source brand changed")
    return original, original.cells[schema.status_column] != "未发"


def purchase_status_satisfied(reader, identity, *, expected_brand=None, brand_match=None) -> bool:
    """Fresh read-only identity proof of sent or further quotation-complete status."""
    _, satisfied = _locate_purchase_record(reader, identity, expected_brand, brand_match)
    if not satisfied:
        return False
    return _locate_purchase_record(reader, identity, expected_brand, brand_match)[1]


def write_purchase_status_safely(
    reader: WorksheetRowReader, writer: PurchaseStatusWriter, identity: SheetRecordIdentity,
    *, expected_brand=None, brand_match=None,
) -> bool:
    """Unique fresh relocation; later quotation state satisfies rather than regresses."""
    _locate_purchase_record(reader, identity, expected_brand, brand_match)
    row, satisfied = _locate_purchase_record(reader, identity, expected_brand, brand_match)
    if satisfied:
        return False
    writer.write_purchase_status(identity.worksheet, row.row_position)
    if not _locate_purchase_record(reader, identity, expected_brand, brand_match)[1]:
        raise SheetRecordConflict("purchase status read-back did not confirm the write")
    return True
