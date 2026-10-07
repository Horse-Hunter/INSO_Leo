"""Read-only relocation of an existing inquiry into the V1.3 source queue."""
from collections.abc import Iterable
from dataclasses import replace

from .brand_write import SheetRecordConflict, relocate_record
from .pending import SheetRecordIdentity, WorksheetRow
from .worksheet_schema import worksheet_schema


def relocate_quotation_source(
    identity: SheetRecordIdentity, rows: Iterable[WorksheetRow], *, expected_brand: object,
) -> WorksheetRow:
    """Reuse exact relocation, allowing only the authorized status transition.

    A persisted UPDATED Research brand may be supplied by Workflow; arbitrary
    human edits are not inferred. Return the actual moved row without changing
    the original identity or the source cells.
    """
    schema = worksheet_schema(identity.worksheet.worksheet)
    eligible = tuple(row for row in rows if row.cells.get(schema.status_column) == "发给采购")
    normalized = tuple(replace(row, cells={**row.cells, schema.status_column: "未发"})
                       for row in eligible)
    target = relocate_record(replace(identity, identifying_snapshot=replace(
        identity.identifying_snapshot, status="未发",
    )), normalized)
    actual = next(row for row in eligible if row.row_position == target.row_position)
    if actual.cells.get(schema.brand_column) != expected_brand:
        raise SheetRecordConflict("source brand changed")
    return actual
