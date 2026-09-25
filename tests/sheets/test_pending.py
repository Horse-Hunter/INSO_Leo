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


def shahab_row(
    position: int,
    *,
    status: object,
    model: object = None,
    brand: object = None,
    quantity: object = None,
) -> WorksheetRow:
    return WorksheetRow(
        row_position=position,
        cells={
            "B": status,
            "D": model,
            "E": brand,
            "F": quantity,
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


def test_shahab_pending_row_maps_to_unified_record_with_source_provenance() -> None:
    worksheet = WorksheetIdentity(spreadsheet="supplier-sheet", worksheet="shahab")
    reader = FakeWorksheetRowReader(
        [
            shahab_row(
                8,
                status="未发",
                model="SHAHAB-MPN",
                brand="Source Brand",
                quantity=40,
            )
        ]
    )

    record = query_pending_records(reader, worksheet)[0]

    assert record.status == "未发"
    assert record.importance_raw == "A"
    assert record.model == "SHAHAB-MPN"
    assert record.brand == "Source Brand"
    assert record.quantity == 40
    assert record.row_position == 8
    assert record.record_identity.worksheet == worksheet
    assert record.record_identity.identifying_snapshot == IdentifyingSnapshot(
        status="未发",
        importance_raw=None,
        model="SHAHAB-MPN",
        brand="Source Brand",
        quantity=40,
    )
    assert record.record_identity.identifying_snapshot.importance_raw is None


def test_shahab_pending_status_comparison_is_exact() -> None:
    worksheet = WorksheetIdentity(spreadsheet="supplier-sheet", worksheet="shahab")
    reader = FakeWorksheetRowReader(
        [
            shahab_row(2, status=" 未发"),
            shahab_row(3, status="未发 "),
            shahab_row(4, status="未發"),
            shahab_row(5, status="未发"),
        ]
    )

    records = query_pending_records(reader, worksheet)

    assert [record.row_position for record in records] == [5]


def test_uppercase_shahab_title_uses_shahab_schema_without_changing_identity() -> None:
    worksheet = WorksheetIdentity(spreadsheet="supplier-sheet", worksheet="SHAHAB")
    reader = FakeWorksheetRowReader(
        [
            shahab_row(
                8,
                status="未发",
                model="SHAHAB-MPN",
                brand="Source Brand",
                quantity=40,
            )
        ]
    )

    records = query_pending_records(reader, worksheet)

    assert [record.model for record in records] == ["SHAHAB-MPN"]
    assert records[0].importance_raw == "A"
    assert records[0].record_identity.worksheet == worksheet


def test_exact_2026_worksheet_reads_customer_from_column_d() -> None:
    worksheet = WorksheetIdentity(spreadsheet="supplier-sheet", worksheet="2026")
    reader = FakeWorksheetRowReader(
        [
            WorksheetRow(
                row_position=9,
                cells={
                    "A": "未发",
                    "C": "B",
                    "D": "  Customer B  ",
                    "E": "MPN-2026",
                    "F": "Brand",
                    "G": 12,
                },
            )
        ]
    )

    record = query_pending_records(reader, worksheet)[0]

    assert record.customer_name == "Customer B"
    assert record.importance_raw == "B"
    assert record.record_identity.worksheet.worksheet == "2026"


def test_2026_blank_customer_is_explicitly_missing_and_other_sheets_are_unknown() -> None:
    blank_2026 = WorksheetIdentity(spreadsheet="supplier-sheet", worksheet="2026")
    other = WorksheetIdentity(spreadsheet="supplier-sheet", worksheet="requests")
    blank_record = query_pending_records(
        FakeWorksheetRowReader(
            [WorksheetRow(3, {"A": "未发", "C": "C", "D": "  ", "E": "X", "F": "Y", "G": 1})]
        ),
        blank_2026,
    )[0]
    other_record = query_pending_records(
        FakeWorksheetRowReader([row(3, status="未发", importance="C", model="X")]),
        other,
    )[0]

    assert blank_record.customer_name is None
    assert other_record.customer_name is None
    assert other_record.importance_raw == "C"


def test_shahab_customer_name_is_fixed_value_without_tier_inference() -> None:
    worksheet = WorksheetIdentity(spreadsheet="supplier-sheet", worksheet="SHAHAB")
    record = query_pending_records(
        FakeWorksheetRowReader([shahab_row(4, status="未发", model="X")]),
        worksheet,
    )[0]

    assert record.customer_name == "SHAHAB"
    assert record.importance_raw == "A"
