from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from src.research.excel_output import (
    BRAND_HEADER,
    CANONICAL_HEADERS,
    ESTIMATED_TOTAL_HEADER,
    IMPORTANCE_HEADER,
    INQUIRY_ID_HEADER,
    MARKET_REFERENCE_HEADER,
    MPN_HEADER,
    QUANTITY_HEADER,
    REMARKS_HEADER,
    STOCK_HEADER,
    ExcelConsistencyError,
    ExcelWriteError,
    ResearchExcelOutput,
)


def _headers(path: Path) -> dict[str, int]:
    worksheet = load_workbook(path).active
    return {
        worksheet.cell(1, column).value: column
        for column in range(1, worksheet.max_column + 1)
    }


def test_upsert_is_idempotent_and_hides_inquiry_id(tmp_path: Path) -> None:
    path = tmp_path / "调研价格.xlsx"
    output = ResearchExcelOutput(path)

    output.upsert("inq_1", importance_raw="A", remarks="first")
    output.upsert("inq_1", importance_raw="B", remarks="updated")

    workbook = load_workbook(path)
    worksheet = workbook.active
    headers = _headers(path)
    inquiry_col = headers[INQUIRY_ID_HEADER]
    importance_col = headers[IMPORTANCE_HEADER]
    remarks_col = headers[REMARKS_HEADER]

    matching_rows = [
        row
        for row in range(2, worksheet.max_row + 1)
        if worksheet.cell(row, inquiry_col).value == "inq_1"
    ]
    assert matching_rows == [2]
    assert worksheet.cell(2, importance_col).value == "重要"
    assert worksheet.cell(2, remarks_col).value == "updated"
    assert (
        worksheet.column_dimensions[worksheet.cell(1, inquiry_col).column_letter].hidden
        is True
    )


@pytest.mark.parametrize(
    ("importance_raw", "expected"),
    [
        ("A", "重要"),
        ("B", "重要"),
        ("C", "普通"),
        ("", "普通"),
        (None, "普通"),
        ("a", "普通"),
    ],
)
def test_importance_is_excel_display_only(
    tmp_path: Path,
    importance_raw: str | None,
    expected: str,
) -> None:
    path = tmp_path / "调研价格.xlsx"
    ResearchExcelOutput(path).upsert(
        "inq_1",
        importance_raw=importance_raw,
    )

    workbook = load_workbook(path)
    worksheet = workbook.active
    headers = _headers(path)
    assert worksheet.cell(2, headers[IMPORTANCE_HEADER]).value == expected


def test_duplicate_inquiry_ids_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "调研价格.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append([INQUIRY_ID_HEADER, IMPORTANCE_HEADER, REMARKS_HEADER])
    worksheet.append(["inq_1", "普通", "a"])
    worksheet.append(["inq_1", "普通", "b"])
    workbook.save(path)

    with pytest.raises(ExcelConsistencyError):
        ResearchExcelOutput(path).upsert(
            "inq_1",
            importance_raw="C",
            remarks="new",
        )


def test_legacy_workbook_migrates_to_canonical_schema_without_data_loss(
    tmp_path: Path,
) -> None:
    path = tmp_path / "调研价格.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append([INQUIRY_ID_HEADER, IMPORTANCE_HEADER, REMARKS_HEADER])
    worksheet.append(["inq_legacy", "普通", "legacy remark"])
    worksheet.column_dimensions["A"].hidden = True
    workbook.save(path)
    workbook.close()

    ResearchExcelOutput(path).upsert(
        "inq_legacy",
        importance_raw="C",
        mpn="ABC-1",
    )

    migrated = load_workbook(path)
    worksheet = migrated.active
    headers = [
        worksheet.cell(row=1, column=column).value
        for column in range(1, worksheet.max_column + 1)
    ]
    assert headers == list(CANONICAL_HEADERS)
    assert worksheet.max_row == 2
    assert worksheet.cell(2, headers.index(INQUIRY_ID_HEADER) + 1).value == "inq_legacy"
    assert worksheet.cell(2, headers.index(IMPORTANCE_HEADER) + 1).value == "普通"
    assert worksheet.cell(2, headers.index(REMARKS_HEADER) + 1).value == "legacy remark"
    assert worksheet.cell(2, headers.index(MPN_HEADER) + 1).value == "ABC-1"
    assert all(
        worksheet.column_dimensions[
            worksheet.cell(1, headers.index(header) + 1).column_letter
        ].hidden
        is not True
        for header in CANONICAL_HEADERS
        if header != INQUIRY_ID_HEADER
    )
    inquiry_letter = worksheet.cell(
        1, headers.index(INQUIRY_ID_HEADER) + 1
    ).column_letter
    assert worksheet.column_dimensions[inquiry_letter].hidden is True


def test_unrecognized_schema_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "调研价格.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append([INQUIRY_ID_HEADER, "未知列"])
    worksheet.append(["inq_1", "must not be guessed"])
    workbook.save(path)
    workbook.close()

    with pytest.raises(ExcelConsistencyError, match="unrecognized"):
        ResearchExcelOutput(path).upsert("inq_1", importance_raw="A")

    unchanged = load_workbook(path).active
    assert unchanged.cell(1, 2).value == "未知列"
    assert unchanged.cell(2, 2).value == "must not be guessed"


def test_explicit_none_clears_stale_snapshot_values_without_duplicate(
    tmp_path: Path,
) -> None:
    path = tmp_path / "调研价格.xlsx"
    output = ResearchExcelOutput(path)
    output.upsert(
        "inq_1",
        importance_raw="A",
        mpn="ABC",
        brand="Acme",
        quantity=10,
        stock_label="货少",
        estimated_total=Decimal(80),
        market_reference="8",
        remarks="部分价格源暂时不可用",
    )

    output.upsert(
        "inq_1",
        importance_raw="C",
        mpn=None,
        brand=None,
        quantity=None,
        stock_label=None,
        estimated_total=None,
        market_reference=None,
        remarks=None,
    )

    worksheet = load_workbook(path).active
    headers = _headers(path)
    assert worksheet.max_row == 2
    assert worksheet.cell(2, headers[IMPORTANCE_HEADER]).value == "普通"
    for header in (
        MPN_HEADER,
        BRAND_HEADER,
        QUANTITY_HEADER,
        STOCK_HEADER,
        ESTIMATED_TOTAL_HEADER,
        MARKET_REFERENCE_HEADER,
        REMARKS_HEADER,
    ):
        assert worksheet.cell(2, headers[header]).value is None


def test_save_failure_is_wrapped_as_excel_write_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "调研价格.xlsx"

    def fail_save(self, filename) -> None:
        raise RuntimeError("synthetic save failure")

    monkeypatch.setattr(Workbook, "save", fail_save)

    with pytest.raises(ExcelWriteError, match="unable to save"):
        ResearchExcelOutput(path).upsert("inq_1", importance_raw="A")

    assert not path.exists()
