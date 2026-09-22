"""Idempotent local Excel persistence for Research V1."""

from __future__ import annotations

import os
import tempfile
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment
from openpyxl.workbook.workbook import Workbook as OpenpyxlWorkbook

MPN_HEADER = "型号"
BRAND_HEADER = "品牌"
QUANTITY_HEADER = "数量"
IMPORTANCE_HEADER = "重要等级"
STOCK_HEADER = "货量标识"
ESTIMATED_TOTAL_HEADER = "预计订单总价"
MARKET_REFERENCE_HEADER = "市场最低参考价"
REMARKS_HEADER = "备注"
INQUIRY_ID_HEADER = "_inquiry_id"
VISIBLE_HEADERS = (
    MPN_HEADER,
    BRAND_HEADER,
    QUANTITY_HEADER,
    IMPORTANCE_HEADER,
    STOCK_HEADER,
    ESTIMATED_TOTAL_HEADER,
    MARKET_REFERENCE_HEADER,
    REMARKS_HEADER,
)
DEFAULT_SHEET_TITLE = "Research"


class ExcelOutputError(RuntimeError):
    """Base error for Research-owned Excel output."""


class ExcelConsistencyError(ExcelOutputError):
    """Raised when persisted workbook identity is ambiguous or inconsistent."""


class ExcelWriteError(ExcelOutputError):
    """Raised when a workbook cannot be durably saved."""


def importance_display_value(importance_raw: str | None) -> str:
    return "重要" if importance_raw in {"A", "B"} else "普通"


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


class ResearchExcelOutput:
    """Persist one logical complete Research record per inquiry_id."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def upsert(
        self,
        inquiry_id: str,
        *,
        importance_raw: str | None,
        remarks: str | None = None,
        mpn: str | None = None,
        brand: str | None = None,
        quantity: int | None = None,
        stock_label: str | None = None,
        estimated_total: Decimal | None = None,
        market_reference: str | None = None,
    ) -> None:
        workbook = self._load_or_create()
        worksheet = workbook.active
        columns = self._ensure_schema(workbook)
        inquiry_col = columns[INQUIRY_ID_HEADER]

        matching_rows = [
            row
            for row in range(2, worksheet.max_row + 1)
            if worksheet.cell(row=row, column=inquiry_col).value == inquiry_id
        ]
        if len(matching_rows) > 1:
            raise ExcelConsistencyError(
                f"duplicate {INQUIRY_ID_HEADER} rows for inquiry_id"
            )
        row = matching_rows[0] if matching_rows else worksheet.max_row + 1
        worksheet.cell(row=row, column=inquiry_col, value=inquiry_id)

        values: dict[str, object | None] = {
            IMPORTANCE_HEADER: importance_display_value(importance_raw),
            MPN_HEADER: mpn,
            BRAND_HEADER: brand,
            QUANTITY_HEADER: quantity,
            STOCK_HEADER: stock_label,
            ESTIMATED_TOTAL_HEADER: _decimal_text(estimated_total),
            MARKET_REFERENCE_HEADER: market_reference,
        }
        for header, value in values.items():
            if value is not None:
                worksheet.cell(row=row, column=columns[header], value=value)
        if remarks is not None:
            worksheet.cell(row=row, column=columns[REMARKS_HEADER], value=remarks)
        if market_reference is not None:
            worksheet.cell(
                row=row, column=columns[MARKET_REFERENCE_HEADER]
            ).alignment = Alignment(wrap_text=True)

        self._save_atomically(workbook)

    def _load_or_create(self) -> OpenpyxlWorkbook:
        if self.path.exists():
            try:
                return load_workbook(self.path)
            except (OSError, ValueError) as exc:
                raise ExcelOutputError("unable to load Research workbook") from exc
        workbook = Workbook()
        workbook.active.title = DEFAULT_SHEET_TITLE
        return workbook

    def _ensure_schema(self, workbook: OpenpyxlWorkbook) -> dict[str, int]:
        worksheet = workbook.active
        blank = (
            worksheet.max_row == 1
            and worksheet.max_column == 1
            and worksheet.cell(row=1, column=1).value is None
        )
        if blank:
            for index, header in enumerate(
                (*VISIBLE_HEADERS, INQUIRY_ID_HEADER), start=1
            ):
                worksheet.cell(row=1, column=index, value=header)

        columns: dict[str, int] = {}
        for header in (*VISIBLE_HEADERS, INQUIRY_ID_HEADER):
            column = self._find_unique_header(worksheet, header)
            if column is None:
                column = worksheet.max_column + 1
                worksheet.cell(row=1, column=column, value=header)
            columns[header] = column
        worksheet.column_dimensions[
            worksheet.cell(row=1, column=columns[INQUIRY_ID_HEADER]).column_letter
        ].hidden = True
        return columns

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
        except (OSError, ValueError) as exc:
            try:
                temp_path.unlink(missing_ok=True)
            finally:
                raise ExcelWriteError("unable to save Research workbook") from exc
        finally:
            workbook.close()
