from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from src.research.excel_output import (
    ExcelConsistencyError,
    INQUIRY_ID_HEADER,
    REMARKS_HEADER,
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

    output.upsert("inq_1", remarks="first")
    output.upsert("inq_1", remarks="updated")

    workbook = load_workbook(path)
    worksheet = workbook.active
    headers = _headers(path)
    inquiry_col = headers[INQUIRY_ID_HEADER]
    remarks_col = headers[REMARKS_HEADER]

    matching_rows = [
        row
        for row in range(2, worksheet.max_row + 1)
        if worksheet.cell(row, inquiry_col).value == "inq_1"
    ]
    assert matching_rows == [2]
    assert worksheet.cell(2, remarks_col).value == "updated"
    assert worksheet.column_dimensions[
        worksheet.cell(1, inquiry_col).column_letter
    ].hidden is True


def test_duplicate_inquiry_ids_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "调研价格.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append([INQUIRY_ID_HEADER, REMARKS_HEADER])
    worksheet.append(["inq_1", "a"])
    worksheet.append(["inq_1", "b"])
    workbook.save(path)

    with pytest.raises(ExcelConsistencyError):
        ResearchExcelOutput(path).upsert("inq_1", remarks="new")
