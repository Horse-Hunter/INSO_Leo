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
        try:
            (
                self._service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=worksheet.spreadsheet,
                    range=_brand_cell_range(
                        worksheet.worksheet,
                        brand_column,
                        row_position,
                    ),
                    valueInputOption="RAW",
                    body={
                        "majorDimension": "ROWS",
                        "values": [[brand]],
                    },
                )
                .execute()
            )
        except Exception as exc:
            raise GoogleSheetsWriteError(
                f"Unable to update Brand column {brand_column}"
            ) from exc


def _brand_cell_range(
    worksheet_title: str,
    brand_column: str,
    row_position: int,
) -> str:
    escaped_title = worksheet_title.replace("'", "''")
    return f"'{escaped_title}'!{brand_column}{row_position}"
