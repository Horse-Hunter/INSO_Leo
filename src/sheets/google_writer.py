"""Targeted Google Sheets API adapter for Brand column F writes."""

from collections.abc import Mapping
from typing import Any, Protocol

from .brand_write import SheetsWriteError, TargetedBrandWriter
from .pending import WorksheetIdentity
from .worksheet_schema import worksheet_schema


class GoogleSheetsWriteError(SheetsWriteError):
    """A targeted Google Sheets Brand write failed."""


class GoogleSheetsWriteRequest(Protocol):
    def execute(self) -> Mapping[str, Any]: ...


class GoogleSheetsWritableValuesResource(Protocol):
    def update(self, **kwargs: Any) -> GoogleSheetsWriteRequest: ...


class GoogleSheetsWritableSpreadsheetsResource(Protocol):
    def values(self) -> GoogleSheetsWritableValuesResource: ...


class GoogleSheetsWritableService(Protocol):
    def spreadsheets(self) -> GoogleSheetsWritableSpreadsheetsResource: ...


class GoogleSheetsBrandWriter(TargetedBrandWriter):
    """Update exactly one worksheet-specific Brand cell using RAW input."""

    def __init__(self, service: GoogleSheetsWritableService) -> None:
        self._service = service

    def write_brand(
        self,
        worksheet: WorksheetIdentity,
        row_position: int,
        brand: str,
    ) -> None:
        if row_position < 1:
            raise ValueError("row_position must be a positive Google Sheet row number")
        brand_column = worksheet_schema(worksheet.worksheet).brand_column
        self._write_cell(worksheet, row_position, brand_column, brand)

    def write_order_field(self, worksheet, row_position, field, value):
        """Owner-initiated whitelist; reuse the canonical single-cell RAW writer."""
        if row_position < 1 or field not in {"model", "brand", "quantity", "importance"}:
            raise ValueError("invalid editable field or row")
        schema = worksheet_schema(worksheet.worksheet)
        column = getattr(schema, {"model": "model_column", "brand": "brand_column",
                                 "quantity": "quantity_column", "importance": "importance_column"}[field])
        if column is None:
            raise ValueError("此工作表的重要程度固定为A，没有可编辑列。")
        self._write_cell(worksheet, row_position, column, value)

    def _write_cell(self, worksheet, row_position, column, value) -> None:
        try:
            (
                self._service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=worksheet.spreadsheet,
                    range=_brand_cell_range(
                        worksheet.worksheet,
                        column,
                        row_position,
                    ),
                    valueInputOption="RAW",
                    body={
                        "majorDimension": "ROWS",
                        "values": [[value]],
                    },
                )
                .execute()
            )
        except Exception as exc:
            raise GoogleSheetsWriteError(
                f"Unable to update column {column}"
            ) from exc


class GoogleSheetsPurchaseStatusWriter(GoogleSheetsBrandWriter):
    """Only the Owner-approved status value; no arbitrary status argument."""

    def write_purchase_status(self, worksheet: WorksheetIdentity, row_position: int) -> None:
        if row_position < 1:
            raise ValueError("row_position must be positive")
        column = worksheet_schema(worksheet.worksheet).status_column
        self._write_cell(worksheet, row_position, column, "发给采购")


def _brand_cell_range(
    worksheet_title: str,
    brand_column: str,
    row_position: int,
) -> str:
    escaped_title = worksheet_title.replace("'", "''")
    return f"'{escaped_title}'!{brand_column}{row_position}"
