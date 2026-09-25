"""Pure domain objects and query behavior for pending Sheet records."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol, TypeAlias

from .worksheet_schema import WorksheetSchema, worksheet_schema

CellValue: TypeAlias = str | int | float | bool | None


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


def query_pending_records(
    reader: WorksheetRowReader,
    worksheet: WorksheetIdentity,
) -> tuple[PendingSheetRecord, ...]:
    """Read once and return rows whose schema-specific status is exactly 未发."""

    schema = worksheet_schema(worksheet.worksheet)
    pending: list[PendingSheetRecord] = []
    for row in reader.read_rows(worksheet):
        status = row.cells.get(schema.status_column)
        if status != "未发":
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
