"""Targeted Google Sheets API adapter for Brand column F writes."""

from collections.abc import Mapping
from typing import Any, Protocol

from .brand_write import SheetsWriteError, TargetedBrandWriter
from .pending import WorksheetIdentity


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
    """Update exactly one Brand cell in column F using RAW input."""

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
        try:
            (
                self._service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=worksheet.spreadsheet,
                    range=_brand_cell_range(worksheet.worksheet, row_position),
                    valueInputOption="RAW",
                    body={
                        "majorDimension": "ROWS",
                        "values": [[brand]],
                    },
                )
                .execute()
            )
        except Exception as exc:
            raise GoogleSheetsWriteError("Unable to update Brand column F") from exc


def _brand_cell_range(worksheet_title: str, row_position: int) -> str:
    escaped_title = worksheet_title.replace("'", "''")
    return f"'{escaped_title}'!F{row_position}"
