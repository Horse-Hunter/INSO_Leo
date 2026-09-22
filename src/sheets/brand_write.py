"""Safe record relocation and blank-only Brand write orchestration."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from .pending import (
    IdentifyingSnapshot,
    SheetRecordIdentity,
    WorksheetIdentity,
    WorksheetRow,
    WorksheetRowReader,
)


class SheetRecordConflict(RuntimeError):
    """The original Sheet record cannot be identified safely."""


class BrandCellNotBlankConflict(SheetRecordConflict):
    """Brand column F is no longer blank and must not be overwritten."""


class SheetsWriteError(RuntimeError):
    """A targeted Sheet write failed."""


class TargetedBrandWriter(Protocol):
    """Boundary that may update only one Brand cell in column F."""

    def write_brand(
        self,
        worksheet: WorksheetIdentity,
        row_position: int,
        brand: str,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class BrandWriteResult:
    worksheet: WorksheetIdentity
    row_position: int


def relocate_record(
    identity: SheetRecordIdentity,
    rows: Iterable[WorksheetRow],
) -> WorksheetRow:
    """Resolve an identity using its original position, then a unique snapshot."""

    current_rows = tuple(rows)
    original = _row_at_position(current_rows, identity.row_position)
    if original is not None and _matches_snapshot(
        original, identity.identifying_snapshot
    ):
        return original

    return _unique_brand_candidate(identity, current_rows)


def write_brand_safely(
    reader: WorksheetRowReader,
    writer: TargetedBrandWriter,
    identity: SheetRecordIdentity,
    brand: str,
) -> BrandWriteResult:
    """Relocate, re-read, enforce blank-only F, and write one Brand cell."""

    relocate_record(
        identity,
        reader.read_rows(identity.worksheet),
    )
    fresh_rows = tuple(reader.read_rows(identity.worksheet))
    target = _unique_brand_candidate(identity, fresh_rows)

    if not _is_blank(target.cells.get("F")):
        raise BrandCellNotBlankConflict("Brand column F is no longer blank")

    try:
        writer.write_brand(
            identity.worksheet,
            target.row_position,
            brand,
        )
    except SheetsWriteError:
        raise
    except Exception as exc:
        raise SheetsWriteError("Targeted Brand write failed") from exc

    return BrandWriteResult(
        worksheet=identity.worksheet,
        row_position=target.row_position,
    )


def _unique_brand_candidate(
    identity: SheetRecordIdentity,
    rows: tuple[WorksheetRow, ...],
) -> WorksheetRow:
    matches = [
        row
        for row in rows
        if _matches_snapshot_without_brand(row, identity.identifying_snapshot)
    ]
    if len(matches) != 1:
        raise SheetRecordConflict(
            "Brand relocation requires exactly one A/C/E/G snapshot match"
        )
    return matches[0]


def _row_at_position(
    rows: tuple[WorksheetRow, ...],
    row_position: int,
) -> WorksheetRow | None:
    matches = [row for row in rows if row.row_position == row_position]
    if len(matches) > 1:
        raise SheetRecordConflict("Worksheet returned duplicate row positions")
    return matches[0] if matches else None


def _matches_snapshot(
    row: WorksheetRow,
    snapshot: IdentifyingSnapshot,
) -> bool:
    return (
        _matches_snapshot_without_brand(row, snapshot)
        and row.cells.get("F") == snapshot.brand
    )


def _matches_snapshot_without_brand(
    row: WorksheetRow,
    snapshot: IdentifyingSnapshot,
) -> bool:
    return (
        row.cells.get("A") == snapshot.status
        and row.cells.get("C") == snapshot.importance_raw
        and row.cells.get("E") == snapshot.model
        and row.cells.get("G") == snapshot.quantity
    )


def _is_blank(value: object) -> bool:
    return value is None or value == ""
