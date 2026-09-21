"""Idempotent local Excel persistence for Research V1."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.workbook.workbook import Workbook as OpenpyxlWorkbook

INQUIRY_ID_HEADER = "_inquiry_id"
REMARKS_HEADER = "备注"
DEFAULT_SHEET_TITLE = "Research"


class ExcelOutputError(RuntimeError):
    """Base error for Research-owned Excel output."""


class ExcelConsistencyError(ExcelOutputError):
    """Raised when persisted workbook identity is ambiguous or inconsistent."""


class ExcelWriteError(ExcelOutputError):
    """Raised when a workbook cannot be durably saved."""


class ResearchExcelOutput:
    """Persist one logical Research record per inquiry_id."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def upsert(self, inquiry_id: str, *, remarks: str | None = None) -> None:
        workbook = self._load_or_create()
        worksheet = workbook.active
        inquiry_col, remarks_col = self._ensure_schema(workbook)

        matching_rows = [
            row
            for row in range(2, worksheet.max_row + 1)
            if worksheet.cell(row=row, column=inquiry_col).value == inquiry_id
        ]
        if len(matching_rows) > 1:
            raise ExcelConsistencyError(
                f"duplicate {INQUIRY_ID_HEADER} rows for inquiry_id"
            )

        if matching_rows:
            row = matching_rows[0]
        else:
            row = worksheet.max_row + 1
            worksheet.cell(row=row, column=inquiry_col, value=inquiry_id)

        if remarks is not None:
            worksheet.cell(row=row, column=remarks_col, value=remarks)

        self._save_atomically(workbook)

    def _load_or_create(self) -> OpenpyxlWorkbook:
        if self.path.exists():
            try:
                return load_workbook(self.path)
            except Exception as exc:  # openpyxl exposes multiple parse errors
                raise ExcelOutputError("unable to load Research workbook") from exc

        workbook = Workbook()
        workbook.active.title = DEFAULT_SHEET_TITLE
        return workbook

    def _ensure_schema(self, workbook: OpenpyxlWorkbook) -> tuple[int, int]:
        worksheet = workbook.active
        inquiry_col = self._find_unique_header(worksheet, INQUIRY_ID_HEADER)
        if inquiry_col is None:
            inquiry_col = self._next_header_column(worksheet)
            worksheet.cell(row=1, column=inquiry_col, value=INQUIRY_ID_HEADER)

        remarks_col = self._find_unique_header(worksheet, REMARKS_HEADER)
        if remarks_col is None:
            remarks_col = self._next_header_column(worksheet)
            worksheet.cell(row=1, column=remarks_col, value=REMARKS_HEADER)

        worksheet.column_dimensions[
            worksheet.cell(row=1, column=inquiry_col).column_letter
        ].hidden = True
        return inquiry_col, remarks_col

    @staticmethod
    def _find_unique_header(worksheet, header: str) -> int | None:
        columns = [
            column
            for column in range(1, worksheet.max_column + 1)
            if worksheet.cell(row=1, column=column).value == header
        ]
        if len(columns) > 1:
            raise ExcelConsistencyError(f"duplicate Excel header: {header}")
        return columns[0] if columns else None

    @staticmethod
    def _next_header_column(worksheet) -> int:
        if (
            worksheet.max_row == 1
            and worksheet.max_column == 1
            and worksheet.cell(row=1, column=1).value is None
        ):
            return 1
        return worksheet.max_column + 1

    def _save_atomically(self, workbook: OpenpyxlWorkbook) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{self.path.stem}.",
            suffix=self.path.suffix or ".xlsx",
            dir=self.path.parent,
        )
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            workbook.save(temp_path)
            os.replace(temp_path, self.path)
        except Exception as exc:
            try:
                temp_path.unlink(missing_ok=True)
            finally:
                raise ExcelWriteError("unable to save Research workbook") from exc
        finally:
            workbook.close()
