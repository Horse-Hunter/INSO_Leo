"""Pure domain objects and query behavior for pending Sheet records."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, TypeAlias

from .worksheet_schema import WorksheetSchema, worksheet_schema

CellValue: TypeAlias = str | int | float | bool | None

# The Brand column is filled by the Owner, and it may hold a placeholder
# instead of a brand.  Owner decision (2026-09-30): a Brand cell that says
# ``unknown`` is not a brand — the row still needs one resolved, so the
# placeholder must never be treated as a known brand.  The rule is defined once
# here, because this module owns worksheet-cell semantics, and applied where a
# brand cell is consumed as a brand: the Research hand-off (both the freshly
# read row and its persisted copy in the queue) and the safe Brand write guard.
BRAND_PLACEHOLDERS = frozenset({"unknown"})


def usable_brand(value: CellValue) -> str | None:
    """Return the cell's brand when it is a real brand, otherwise ``None``.

    A blank cell and a placeholder cell both mean "no brand known", which is
    what makes the existing resolve-the-brand path apply to either.
    """

    if not isinstance(value, str):
        return None
    token = value.strip()
    if not token or token.casefold() in BRAND_PLACEHOLDERS:
        return None
    return token


class CustomerNameSource(StrEnum):
    SHAHAB_FIXED = "SHAHAB_FIXED"
    WORKSHEET_COLUMN_D = "WORKSHEET_COLUMN_D"
    UNCONFIGURED = "UNCONFIGURED"


@dataclass(frozen=True, slots=True)
class WorksheetIdentity:
    """Identity of a worksheet within a spreadsheet."""

    spreadsheet: str
    worksheet: str


@dataclass(frozen=True, slots=True)
class WorksheetRow:
    """A reader-observed worksheet row and its actual position."""

    row_position: int
    cells: Mapping[str, CellValue]


class WorksheetRowReader(Protocol):
    """Narrow boundary implemented by in-memory and future API readers."""

    def read_rows(self, worksheet: WorksheetIdentity) -> Iterable[WorksheetRow]: ...


@dataclass(frozen=True, slots=True)
class IdentifyingSnapshot:
    """Exact source values observed for the worksheet-specific V1 columns.

    importance_raw is None for SHAHAB because its normalized default is not a
    source observation.
    """

    status: CellValue
    importance_raw: CellValue
    model: CellValue
    brand: CellValue
    quantity: CellValue


@dataclass(frozen=True, slots=True)
class SheetRecordIdentity:
    """Composite identity; row position alone is never a permanent identity."""

    worksheet: WorksheetIdentity
    row_position: int
    identifying_snapshot: IdentifyingSnapshot


@dataclass(frozen=True, slots=True)
class PendingSheetRecord:
    """Raw fields for a row whose status is exactly the V1 pending value."""

    status: CellValue
    importance_raw: CellValue
    model: CellValue
    brand: CellValue
    quantity: CellValue
    row_position: int
    record_identity: SheetRecordIdentity
    customer_name: str | None = None
    customer_name_source: CustomerNameSource = CustomerNameSource.UNCONFIGURED


def query_pending_records(
    reader: WorksheetRowReader,
    worksheet: WorksheetIdentity,
) -> tuple[PendingSheetRecord, ...]:
    """Read once and return rows whose schema-specific status is exactly 未发."""
    return query_records_by_status(reader, worksheet, status="未发")


def query_records_by_status(
    reader: WorksheetRowReader, worksheet: WorksheetIdentity, *, status: str,
) -> tuple[PendingSheetRecord, ...]:
    """One-shot exact status read using the canonical schema and row parser."""
    wanted_status = status
    schema = worksheet_schema(worksheet.worksheet)
    pending: list[PendingSheetRecord] = []
    for row in reader.read_rows(worksheet):
        status = row.cells.get(schema.status_column)
        if status != wanted_status:
            continue

        snapshot = _source_snapshot(row, schema)
        identity = SheetRecordIdentity(
            worksheet=worksheet,
            row_position=row.row_position,
            identifying_snapshot=snapshot,
        )
        pending.append(
            PendingSheetRecord(
                status=snapshot.status,
                importance_raw=(
                    snapshot.importance_raw
                    if schema.importance_column is not None
                    else schema.default_importance
                ),
                model=snapshot.model,
                brand=snapshot.brand,
                quantity=snapshot.quantity,
                row_position=row.row_position,
                record_identity=identity,
                customer_name=_customer_name(row, schema),
                customer_name_source=(
                    CustomerNameSource.SHAHAB_FIXED
                    if schema.fixed_customer_name is not None
                    else CustomerNameSource.WORKSHEET_COLUMN_D
                    if schema.customer_name_column == "D"
                    else CustomerNameSource.UNCONFIGURED
                ),
            )
        )

    return tuple(pending)


def _customer_name(row: WorksheetRow, schema: WorksheetSchema) -> str | None:
    if schema.fixed_customer_name is not None:
        return schema.fixed_customer_name
    if schema.customer_name_column is None:
        return None
    value = row.cells.get(schema.customer_name_column)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _source_snapshot(
    row: WorksheetRow,
    schema: WorksheetSchema,
) -> IdentifyingSnapshot:
    return IdentifyingSnapshot(
        status=row.cells.get(schema.status_column),
        importance_raw=(
            row.cells.get(schema.importance_column)
            if schema.importance_column is not None
            else None
        ),
        model=row.cells.get(schema.model_column),
        brand=row.cells.get(schema.brand_column),
        quantity=row.cells.get(schema.quantity_column),
    )


def query_quotation_candidates(
    reader: WorksheetRowReader, worksheet: WorksheetIdentity,
) -> tuple[PendingSheetRecord, ...]:
    """V1.3 read-only source; never polls or changes a cell."""
    return query_records_by_status(reader, worksheet, status="发给采购")
