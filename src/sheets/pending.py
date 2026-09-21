"""Pure domain objects and query behavior for pending Sheet records."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol, TypeAlias

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
    """Exact identifying values observed for the confirmed V1 columns."""

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


def query_pending_records(
    reader: WorksheetRowReader,
    worksheet: WorksheetIdentity,
) -> tuple[PendingSheetRecord, ...]:
    """Read a worksheet once and return rows whose A value is exactly 未发."""

    pending: list[PendingSheetRecord] = []
    for row in reader.read_rows(worksheet):
        status = row.cells.get("A")
        if status != "未发":
            continue

        snapshot = IdentifyingSnapshot(
            status=status,
            importance_raw=row.cells.get("C"),
            model=row.cells.get("E"),
            brand=row.cells.get("F"),
            quantity=row.cells.get("G"),
        )
        identity = SheetRecordIdentity(
            worksheet=worksheet,
            row_position=row.row_position,
            identifying_snapshot=snapshot,
        )
        pending.append(
            PendingSheetRecord(
                status=snapshot.status,
                importance_raw=snapshot.importance_raw,
                model=snapshot.model,
                brand=snapshot.brand,
                quantity=snapshot.quantity,
                row_position=row.row_position,
                record_identity=identity,
            )
        )

    return tuple(pending)
