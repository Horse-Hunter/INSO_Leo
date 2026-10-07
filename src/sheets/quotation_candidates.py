"""Read-only relocation of an existing inquiry into the V1.3 source queue."""
from collections.abc import Iterable
from dataclasses import replace

from .brand_write import SheetRecordConflict, relocate_record
from .pending import SheetRecordIdentity, WorksheetRow
from .worksheet_schema import worksheet_schema


class QuotationSourceAmbiguous(SheetRecordConflict):
    """Safe row locations for a genuinely ambiguous relocation fallback."""
    def __init__(self, row_positions: tuple[int, ...]):
        super().__init__("SOURCE_IDENTITY_AMBIGUOUS")
        self.row_positions = row_positions


def relocate_quotation_source(
    identity: SheetRecordIdentity, rows: Iterable[WorksheetRow], *, expected_brand: object,
) -> WorksheetRow:
    """Verify the original position first, otherwise require unique relocation.

    Position anchors the EXISTING identity only after strict status/snapshot/
    expected-brand validation. Never generate or rewrite business identity.
    """
    schema = worksheet_schema(identity.worksheet.worksheet)
    eligible = tuple(row for row in rows
                     if row.cells.get(schema.status_column) == "发给采购"
                     and row.cells.get(schema.brand_column) == expected_brand)
    normalized = tuple(replace(row, cells={**row.cells, schema.status_column: "未发"})
                       for row in eligible)
    original = replace(identity, identifying_snapshot=replace(
        identity.identifying_snapshot, status="未发",
    ))
    anchored = tuple(row for row in normalized if row.row_position == identity.row_position)
    if len(anchored) == 1:
        try:
            target = relocate_record(original, anchored)
        except SheetRecordConflict:
            pass
        else:
            return next(row for row in eligible if row.row_position == target.row_position)
    try:
        target = relocate_record(original, normalized)
    except SheetRecordConflict:
        matches = []
        for row in normalized:
            try:
                relocate_record(original, (row,))
            except SheetRecordConflict:
                continue
            matches.append(row.row_position)
        if len(matches) > 1:
            raise QuotationSourceAmbiguous(tuple(matches)) from None
        raise
    return next(row for row in eligible if row.row_position == target.row_position)
