from collections.abc import Iterable

import pytest

from src.sheets import (
    IdentifyingSnapshot,
    SheetRecordIdentity,
    WorksheetIdentity,
    WorksheetRow,
)
from src.sheets.brand_write import (
    BrandCellNotBlankConflict,
    SheetRecordConflict,
    SheetsWriteError,
    relocate_record,
    write_brand_safely,
)


def worksheet() -> WorksheetIdentity:
    return WorksheetIdentity(spreadsheet="spreadsheet-id", worksheet="2026")


def identity(*, row_position: int = 4) -> SheetRecordIdentity:
    return SheetRecordIdentity(
        worksheet=worksheet(),
        row_position=row_position,
        identifying_snapshot=IdentifyingSnapshot(
            status="未发",
            importance_raw="A",
            model="MPN-1",
            brand=None,
            quantity=10,
        ),
    )


def row(
    row_position: int,
    *,
    status: object = "未发",
    importance_raw: object = "A",
    model: object = "MPN-1",
    brand: object = None,
    quantity: object = 10,
) -> WorksheetRow:
    return WorksheetRow(
        row_position=row_position,
        cells={
            "A": status,
            "C": importance_raw,
            "E": model,
            "F": brand,
            "G": quantity,
        },
    )


def shahab_worksheet() -> WorksheetIdentity:
    return WorksheetIdentity(spreadsheet="spreadsheet-id", worksheet="shahab")


def shahab_identity(*, row_position: int = 4) -> SheetRecordIdentity:
    return SheetRecordIdentity(
        worksheet=shahab_worksheet(),
        row_position=row_position,
        identifying_snapshot=IdentifyingSnapshot(
            status="未发",
            importance_raw=None,
            model="MPN-1",
            brand=None,
            quantity=10,
        ),
    )


def shahab_row(
    row_position: int,
    *,
    status: object = "未发",
    model: object = "MPN-1",
    brand: object = None,
    quantity: object = 10,
) -> WorksheetRow:
    return WorksheetRow(
        row_position=row_position,
        cells={
            "B": status,
            "D": model,
            "E": brand,
            "F": quantity,
        },
    )


class SequencedReader:
    def __init__(self, reads: Iterable[Iterable[WorksheetRow]]) -> None:
        self._reads = [tuple(items) for items in reads]
        self.calls: list[WorksheetIdentity] = []

    def read_rows(self, target: WorksheetIdentity) -> tuple[WorksheetRow, ...]:
        self.calls.append(target)
        if not self._reads:
            raise AssertionError("Unexpected reader call")
        return self._reads.pop(0)


class FakeBrandWriter:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.calls: list[tuple[WorksheetIdentity, int, str]] = []

    def write_brand(
        self,
        target: WorksheetIdentity,
        row_position: int,
        brand: str,
    ) -> None:
        if self.failure is not None:
            raise self.failure
        self.calls.append((target, row_position, brand))


def test_original_row_position_matching_snapshot_is_used() -> None:
    expected = row(4)

    resolved = relocate_record(identity(), [row(2, model="OTHER"), expected])

    assert resolved is expected


def test_inserted_rows_relocate_to_unique_snapshot_match() -> None:
    moved = row(7)

    resolved = relocate_record(
        identity(row_position=4),
        [row(4, model="OTHER"), moved],
    )

    assert resolved is moved


def test_missing_snapshot_match_is_a_conflict() -> None:
    with pytest.raises(SheetRecordConflict):
        relocate_record(identity(), [row(4, model="OTHER")])


def test_duplicate_snapshot_matches_are_a_conflict() -> None:
    with pytest.raises(SheetRecordConflict):
        relocate_record(
            identity(row_position=4),
            [row(5), row(8)],
        )


def test_original_position_does_not_bypass_standard_global_uniqueness() -> None:
    with pytest.raises(SheetRecordConflict):
        relocate_record(identity(), [row(4), row(8)])


def test_blank_brand_is_rechecked_then_targeted_write_is_allowed() -> None:
    reader = SequencedReader([[row(4)], [row(4)]])
    writer = FakeBrandWriter()

    result = write_brand_safely(reader, writer, identity(), "Resolved Brand")

    assert reader.calls == [worksheet(), worksheet()]
    assert writer.calls == [(worksheet(), 4, "Resolved Brand")]
    assert result.row_position == 4


def test_human_populated_brand_is_a_conflict_and_is_not_written() -> None:
    reader = SequencedReader([[row(4)], [row(4, brand="Human Brand")]])
    writer = FakeBrandWriter()

    with pytest.raises(BrandCellNotBlankConflict):
        write_brand_safely(reader, writer, identity(), "Resolved Brand")

    assert writer.calls == []


def test_shifted_blank_and_populated_same_aceg_candidates_are_a_conflict() -> None:
    reader = SequencedReader(
        [
            [row(7), row(9, brand="Human Brand")],
        ]
    )
    writer = FakeBrandWriter()

    with pytest.raises(SheetRecordConflict):
        write_brand_safely(
            reader,
            writer,
            identity(row_position=4),
            "Resolved Brand",
        )

    assert writer.calls == []


def test_shifted_unique_candidate_with_populated_brand_is_a_brand_conflict() -> None:
    reader = SequencedReader(
        [
            [row(7, brand="Human Brand")],
            [row(7, brand="Human Brand")],
        ]
    )
    writer = FakeBrandWriter()

    with pytest.raises(BrandCellNotBlankConflict):
        write_brand_safely(
            reader,
            writer,
            identity(row_position=4),
            "Resolved Brand",
        )

    assert writer.calls == []


def test_row_moving_between_reads_is_relocated_before_write() -> None:
    reader = SequencedReader(
        [
            [row(7)],
            [row(7, model="OTHER"), row(9)],
        ]
    )
    writer = FakeBrandWriter()

    result = write_brand_safely(reader, writer, identity(), "Resolved Brand")

    assert writer.calls == [(worksheet(), 9, "Resolved Brand")]
    assert result.row_position == 9


def test_writer_failure_is_a_sheets_owned_write_error() -> None:
    reader = SequencedReader([[row(4)], [row(4)]])
    writer = FakeBrandWriter(RuntimeError("simulated failure"))

    with pytest.raises(SheetsWriteError) as raised:
        write_brand_safely(reader, writer, identity(), "Resolved Brand")

    assert isinstance(raised.value.__cause__, RuntimeError)


def test_shahab_unique_bdf_candidate_relocates_after_shift() -> None:
    moved = shahab_row(9)

    resolved = relocate_record(
        shahab_identity(row_position=4),
        [shahab_row(4, model="OTHER"), moved],
    )

    assert resolved is moved


def test_shahab_zero_and_multiple_bdf_candidates_are_conflicts() -> None:
    with pytest.raises(SheetRecordConflict):
        relocate_record(shahab_identity(), [shahab_row(4, model="OTHER")])

    with pytest.raises(SheetRecordConflict):
        relocate_record(shahab_identity(), [shahab_row(5), shahab_row(8)])


def test_shahab_brand_does_not_disambiguate_same_bdf_candidates() -> None:
    reader = SequencedReader(
        [[shahab_row(7), shahab_row(9, brand="Human Brand")]]
    )
    writer = FakeBrandWriter()

    with pytest.raises(SheetRecordConflict):
        write_brand_safely(
            reader,
            writer,
            shahab_identity(row_position=4),
            "Resolved Brand",
        )

    assert writer.calls == []


def test_shahab_blank_e_is_rechecked_then_targeted_write_is_allowed() -> None:
    reader = SequencedReader([[shahab_row(4)], [shahab_row(4)]])
    writer = FakeBrandWriter()

    result = write_brand_safely(
        reader,
        writer,
        shahab_identity(),
        "Resolved Brand",
    )

    assert reader.calls == [shahab_worksheet(), shahab_worksheet()]
    assert writer.calls == [(shahab_worksheet(), 4, "Resolved Brand")]
    assert result.row_position == 4


def test_shahab_human_populated_e_is_conflict_with_zero_writes() -> None:
    reader = SequencedReader(
        [[shahab_row(4)], [shahab_row(4, brand="Human Brand")]]
    )
    writer = FakeBrandWriter()

    with pytest.raises(BrandCellNotBlankConflict):
        write_brand_safely(
            reader,
            writer,
            shahab_identity(),
            "Resolved Brand",
        )

    assert writer.calls == []


def test_shahab_fresh_read_relocates_shifted_row_before_write() -> None:
    reader = SequencedReader(
        [
            [shahab_row(7)],
            [shahab_row(7, model="OTHER"), shahab_row(11)],
        ]
    )
    writer = FakeBrandWriter()

    result = write_brand_safely(
        reader,
        writer,
        shahab_identity(),
        "Resolved Brand",
    )

    assert writer.calls == [(shahab_worksheet(), 11, "Resolved Brand")]
    assert result.row_position == 11
