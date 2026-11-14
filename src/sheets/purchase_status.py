"""Owner-authorized, one-cell pending -> sent-to-purchasing transition."""
from dataclasses import replace
from typing import Protocol

from .brand_write import SheetRecordConflict, relocate_record
from .pending import (
    SheetRecordIdentity,
    WorksheetIdentity,
    WorksheetRow,
    WorksheetRowReader,
)
from .worksheet_schema import worksheet_schema

PURCHASE_COMPLETED_STATUSES = frozenset({"发给采购", "采购已报价", "已报价给客户", "意向订单", "成交"})


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


def owner_resolved_status(reader: WorksheetRowReader, identity: SheetRecordIdentity) -> str | None:
    """The row's status when the Owner has already carried this order forward by hand.

    A stale order stays on the review list until something proves the human did the
    work. The Owner's own status cell is that proof, but the existing
    :func:`current_purchase_status` cannot be reused for it: that one accepts only
    ``未发``/``发给采购`` and refuses any brand change, which is exactly what a manual
    follow-up produces.

    So this narrows the worksheet to the completed-status rows, restores the status
    cell to the stored one, and then reuses the canonical relocation (which already
    ignores Brand and matches one unique importance/model/quantity snapshot). That
    tolerates the two fields the Owner legitimately edits — status and brand — and a
    row that moved, while staying strict about the article. No unique match, no
    completed status, or no row at all returns ``None`` and nothing is closed.
    """

    rows = tuple(reader.read_rows(identity.worksheet))
    schema = worksheet_schema(identity.worksheet.worksheet)
    column = schema.status_column
    eligible = [
        row for row in rows
        if isinstance(row.cells.get(column), str)
        and str(row.cells[column]).strip() in PURCHASE_COMPLETED_STATUSES
    ]
    if not eligible:
        return None
    stored_status = identity.identifying_snapshot.status
    normalized = [
        replace(row, cells={**row.cells, column: stored_status}) for row in eligible
    ]
    try:
        relocated = relocate_record(identity, normalized)
    except SheetRecordConflict:
        relocated = None
    if relocated is not None:
        actual = [row for row in eligible if row.row_position == relocated.row_position]
        if len(actual) == 1:
            return str(actual[0].cells[column]).strip()

    # The Owner may also have completed the model text after the order was created
    # (``N6210`` → ``CELERON-N6210``). That is still one article when exactly one
    # completed row carries the stored text and the same importance/quantity; two
    # candidates stay unproven and nothing is closed.
    stored_model = str(identity.identifying_snapshot.model or "").strip().casefold()
    if not stored_model:
        return None
    candidates = [
        row for row in eligible
        if stored_model in str(row.cells.get(schema.model_column) or "").strip().casefold()
        and row.cells.get(schema.quantity_column) == identity.identifying_snapshot.quantity
        and (schema.importance_column is None
             or row.cells.get(schema.importance_column) == identity.identifying_snapshot.importance_raw)
    ]
    if len(candidates) != 1:
        return None
    return str(candidates[0].cells[column]).strip()


def current_row_at_identity(reader: WorksheetRowReader, identity: SheetRecordIdentity) -> WorksheetRow | None:
    """The physical row this order occupies now, or ``None`` when it is not unique.

    Used only by the Owner's explicit "recover from the sheet" action: a human is
    pointing at the line they can see, so the physical anchor is the intended
    binding. Callers must not treat this as an automatic identity proof.
    """

    rows = tuple(reader.read_rows(identity.worksheet))
    anchors = [row for row in rows if row.row_position == identity.row_position]
    return anchors[0] if len(anchors) == 1 else None


def _locate_purchase_record(reader, identity, expected_brand, brand_match=None):
    if identity.identifying_snapshot.status != "未发":
        raise SheetRecordConflict("original purchase status must be pending")
    rows = tuple(reader.read_rows(identity.worksheet))
    schema = worksheet_schema(identity.worksheet.worksheet)
    eligible = [r for r in rows if r.cells.get(schema.status_column)
                in {"未发", *PURCHASE_COMPLETED_STATUSES}]
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
