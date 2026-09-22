"""Idempotent local Excel persistence for Research V1."""

from __future__ import annotations

import os
import tempfile
from copy import copy
from decimal import Decimal
from pathlib import Path
from typing import Final

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
CANONICAL_HEADERS = (*VISIBLE_HEADERS, INQUIRY_ID_HEADER)
LEGACY_HEADERS = (INQUIRY_ID_HEADER, IMPORTANCE_HEADER, REMARKS_HEADER)


class _UnsetType:
    pass


_UNSET: Final = _UnsetType()


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
        remarks: str | None | _UnsetType = _UNSET,
        mpn: str | None | _UnsetType = _UNSET,
        brand: str | None | _UnsetType = _UNSET,
        quantity: int | None | _UnsetType = _UNSET,
        stock_label: str | None | _UnsetType = _UNSET,
        estimated_total: Decimal | None | _UnsetType = _UNSET,
        market_reference: str | None | _UnsetType = _UNSET,
    ) -> None:
        workbook: OpenpyxlWorkbook | None = None
        try:
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
            worksheet.cell(row=row, column=inquiry_col).value = inquiry_id

            values: dict[str, object | None | _UnsetType] = {
                IMPORTANCE_HEADER: importance_display_value(importance_raw),
                MPN_HEADER: mpn,
                BRAND_HEADER: brand,
                QUANTITY_HEADER: quantity,
                STOCK_HEADER: stock_label,
                ESTIMATED_TOTAL_HEADER: (
                    estimated_total
                    if isinstance(estimated_total, _UnsetType)
                    else _decimal_text(estimated_total)
                ),
                MARKET_REFERENCE_HEADER: market_reference,
                REMARKS_HEADER: remarks,
            }
            for header, value in values.items():
                if isinstance(value, _UnsetType):
                    continue
                worksheet.cell(row=row, column=columns[header]).value = value
            if not isinstance(market_reference, _UnsetType):
                worksheet.cell(
                    row=row, column=columns[MARKET_REFERENCE_HEADER]
                ).alignment = Alignment(wrap_text=True)

            self._save_atomically(workbook)
        except ExcelOutputError:
            raise
        except Exception as exc:
            raise ExcelOutputError("unable to update Research workbook") from exc
        finally:
            if workbook is not None:
                try:
                    workbook.close()
                except Exception as exc:
                    raise ExcelOutputError("unable to close Research workbook") from exc

    def _load_or_create(self) -> OpenpyxlWorkbook:
        if self.path.exists():
            try:
                return load_workbook(self.path)
            except Exception as exc:
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
            for index, header in enumerate(CANONICAL_HEADERS, start=1):
                worksheet.cell(row=1, column=index, value=header)
        else:
            headers = tuple(
                worksheet.cell(row=1, column=column).value
                for column in range(1, worksheet.max_column + 1)
            )
            if len(set(headers)) != len(headers):
                raise ExcelConsistencyError("duplicate Excel header")
            if headers == CANONICAL_HEADERS:
                pass
            elif headers == LEGACY_HEADERS or set(headers) == set(CANONICAL_HEADERS):
                self._normalize_schema(worksheet, headers)
            else:
                raise ExcelConsistencyError("unrecognized Research workbook schema")

        columns = {
            header: index for index, header in enumerate(CANONICAL_HEADERS, start=1)
        }
        for header in VISIBLE_HEADERS:
            worksheet.column_dimensions[
                worksheet.cell(row=1, column=columns[header]).column_letter
            ].hidden = False
        worksheet.column_dimensions[
            worksheet.cell(row=1, column=columns[INQUIRY_ID_HEADER]).column_letter
        ].hidden = True
        return columns

    @staticmethod
    def _normalize_schema(worksheet, headers: tuple[object, ...]) -> None:
        source_columns = {
            header: index for index, header in enumerate(headers, start=1)
        }
        snapshots: dict[tuple[int, object], tuple[object, object, object, object]] = {}
        for row in range(1, worksheet.max_row + 1):
            for header, column in source_columns.items():
                cell = worksheet.cell(row=row, column=column)
                snapshots[(row, header)] = (
                    cell.value,
                    copy(cell._style),
                    copy(cell.hyperlink),
                    copy(cell.comment),
                )

        original_max_column = worksheet.max_column
        for column, header in enumerate(CANONICAL_HEADERS, start=1):
            for row in range(1, worksheet.max_row + 1):
                target = worksheet.cell(row=row, column=column)
                state = snapshots.get((row, header))
                if state is None:
                    target.value = header if row == 1 else None
                    target.hyperlink = None
                    target.comment = None
                    continue
                value, style, hyperlink, comment = state
                target.value = value
                target._style = copy(style)
                target.hyperlink = copy(hyperlink)
                target.comment = copy(comment)

        if original_max_column > len(CANONICAL_HEADERS):
            worksheet.delete_cols(
                len(CANONICAL_HEADERS) + 1,
                original_max_column - len(CANONICAL_HEADERS),
            )

    def _save_atomically(self, workbook: OpenpyxlWorkbook) -> None:
        temp_path: Path | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{self.path.stem}.",
                suffix=self.path.suffix or ".xlsx",
                dir=self.path.parent,
            )
            os.close(fd)
            temp_path = Path(temp_name)
            workbook.save(temp_path)
            os.replace(temp_path, self.path)
        except Exception as exc:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise ExcelWriteError("unable to save Research workbook") from exc
