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
from .worksheet_schema import WorksheetSchema, worksheet_schema


class SheetRecordConflict(RuntimeError):
    """The original Sheet record cannot be identified safely."""


class BrandCellNotBlankConflict(SheetRecordConflict):
    """The worksheet-specific Brand cell is not blank and cannot be overwritten."""


class SheetsWriteError(RuntimeError):
    """A targeted Sheet write failed."""


class TargetedBrandWriter(Protocol):
    """Boundary that may update only one worksheet-specific Brand cell."""

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
    """Resolve an identity using one globally unique non-Brand source match."""

    current_rows = tuple(rows)
    return _unique_brand_candidate(identity, current_rows)


def write_brand_safely(
    reader: WorksheetRowReader,
    writer: TargetedBrandWriter,
    identity: SheetRecordIdentity,
    brand: str,
) -> BrandWriteResult:
    """Relocate, re-read, enforce blank-only Brand, and write one cell."""

    relocate_record(
        identity,
        reader.read_rows(identity.worksheet),
    )
    fresh_rows = tuple(reader.read_rows(identity.worksheet))
    target = _unique_brand_candidate(identity, fresh_rows)
    schema = worksheet_schema(identity.worksheet.worksheet)

    if not _is_blank(target.cells.get(schema.brand_column)):
        raise BrandCellNotBlankConflict(
            f"Brand column {schema.brand_column} is no longer blank"
        )

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
    schema = worksheet_schema(identity.worksheet.worksheet)
    matches = [
        row
        for row in rows
        if _matches_snapshot_without_brand(
            row,
            identity.identifying_snapshot,
            schema,
        )
    ]
    if len(matches) != 1:
        columns = "/".join(schema.relocation_columns)
        raise SheetRecordConflict(
            f"Brand relocation requires exactly one {columns} snapshot match"
        )
    return matches[0]


def _matches_snapshot_without_brand(
    row: WorksheetRow,
    snapshot: IdentifyingSnapshot,
    schema: WorksheetSchema,
) -> bool:
    if row.cells.get(schema.status_column) != snapshot.status:
        return False
    if (
        schema.importance_column is not None
        and row.cells.get(schema.importance_column) != snapshot.importance_raw
    ):
        return False
    return (
        row.cells.get(schema.model_column) == snapshot.model
        and row.cells.get(schema.quantity_column) == snapshot.quantity
    )


def _is_blank(value: object) -> bool:
    return value is None or value == ""
