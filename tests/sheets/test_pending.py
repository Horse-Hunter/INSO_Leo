from collections.abc import Iterable

from src.sheets import (
    IdentifyingSnapshot,
    WorksheetIdentity,
    WorksheetRow,
    query_pending_records,
)


class FakeWorksheetRowReader:
    def __init__(self, rows: Iterable[WorksheetRow]) -> None:
        self._rows = tuple(rows)
        self.read_worksheets: list[WorksheetIdentity] = []

    def read_rows(self, worksheet: WorksheetIdentity) -> tuple[WorksheetRow, ...]:
        self.read_worksheets.append(worksheet)
        return self._rows


def row(
    position: int,
    *,
    status: object,
    importance: object = None,
    model: object = None,
    brand: object = None,
    quantity: object = None,
) -> WorksheetRow:
    return WorksheetRow(
        row_position=position,
        cells={
            "A": status,
            "C": importance,
            "E": model,
            "F": brand,
            "G": quantity,
        },
    )


def test_exact_pending_row_is_mapped_with_composite_identity() -> None:
    worksheet = WorksheetIdentity(spreadsheet="supplier-sheet", worksheet="requests")
    reader = FakeWorksheetRowReader(
        [
            row(
                7,
                status="未发",
                importance=" A ",
                model="MPN-001",
                brand="Brand X",
                quantity=25,
            )
        ]
    )

    records = query_pending_records(reader, worksheet)

    assert reader.read_worksheets == [worksheet]
    assert len(records) == 1
    record = records[0]
    assert record.status == "未发"
    assert record.importance_raw == " A "
    assert record.model == "MPN-001"
    assert record.brand == "Brand X"
    assert record.quantity == 25
    assert record.row_position == 7
    assert record.record_identity.worksheet == worksheet
    assert record.record_identity.row_position == 7
    assert record.record_identity.identifying_snapshot == IdentifyingSnapshot(
        status="未发",
        importance_raw=" A ",
        model="MPN-001",
        brand="Brand X",
        quantity=25,
    )


def test_all_pending_rows_are_returned_in_reader_order() -> None:
    worksheet = WorksheetIdentity(spreadsheet="supplier-sheet", worksheet="requests")
    reader = FakeWorksheetRowReader(
        [
            row(2, status="未发", model="FIRST"),
            row(3, status="sent", model="SKIP"),
            row(9, status="未发", model="SECOND"),
        ]
    )

    records = query_pending_records(reader, worksheet)

    assert [record.model for record in records] == ["FIRST", "SECOND"]
    assert [record.row_position for record in records] == [2, 9]


def test_no_pending_rows_returns_empty_tuple() -> None:
    worksheet = WorksheetIdentity(spreadsheet="supplier-sheet", worksheet="requests")
    reader = FakeWorksheetRowReader([row(2, status="sent")])

    assert query_pending_records(reader, worksheet) == ()


def test_pending_status_comparison_is_exact() -> None:
    worksheet = WorksheetIdentity(spreadsheet="supplier-sheet", worksheet="requests")
    reader = FakeWorksheetRowReader(
        [
            row(2, status=" 未发"),
            row(3, status="未发 "),
            row(4, status="未發"),
            row(5, status="未发"),
        ]
    )

    records = query_pending_records(reader, worksheet)

    assert [record.row_position for record in records] == [5]


def test_row_position_is_not_a_standalone_permanent_identity() -> None:
    first_worksheet = WorksheetIdentity(spreadsheet="one", worksheet="requests")
    second_worksheet = WorksheetIdentity(spreadsheet="two", worksheet="requests")
    source_row = row(4, status="未发", model="SAME-POSITION")

    first_identity = query_pending_records(
        FakeWorksheetRowReader([source_row]), first_worksheet
    )[0].record_identity
    second_identity = query_pending_records(
        FakeWorksheetRowReader([source_row]), second_worksheet
    )[0].record_identity

    assert first_identity.row_position == second_identity.row_position == 4
    assert first_identity != second_identity
