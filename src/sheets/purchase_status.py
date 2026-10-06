"""Owner-authorized, one-cell pending -> sent-to-purchasing transition."""
from dataclasses import replace
from typing import Protocol

from .brand_write import SheetRecordConflict, relocate_record
from .pending import SheetRecordIdentity, WorksheetIdentity, WorksheetRowReader
from .worksheet_schema import worksheet_schema


class PurchaseStatusWriter(Protocol):
    def write_purchase_status(self, worksheet: WorksheetIdentity, row_position: int) -> None: ...


def write_purchase_status_safely(
    reader: WorksheetRowReader, writer: PurchaseStatusWriter, identity: SheetRecordIdentity,
) -> bool:
    """Unique relocation, fresh read and read-back; idempotent after a prior write."""
    if identity.identifying_snapshot.status != "未发":
        raise SheetRecordConflict("original purchase status must be pending")
    def locate():
        rows = tuple(reader.read_rows(identity.worksheet))
        column = worksheet_schema(identity.worksheet.worksheet).status_column
        eligible = [r for r in rows if r.cells.get(column) in {"未发", "发给采购"}]
        normalized = [replace(r, cells={**r.cells, column: "未发"}) for r in eligible]
        target = relocate_record(identity, normalized)
        original = next(r for r in eligible if r.row_position == target.row_position)
        return original, original.cells[column] == "发给采购"

    locate()
    row, already_sent = locate()
    if already_sent:
        return False
    writer.write_purchase_status(identity.worksheet, row.row_position)
    _, sent = locate()
    if not sent:
        raise SheetRecordConflict("purchase status read-back did not confirm the write")
    return True
