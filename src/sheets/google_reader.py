"""Read-only Google Sheets API adapter for worksheet rows."""

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from .pending import WorksheetIdentity, WorksheetRow


class GoogleSheetsReadError(RuntimeError):
    """A Google Sheets read failed or returned an invalid response."""


class GoogleSheetsRequest(Protocol):
    def execute(self) -> Mapping[str, Any]: ...


class GoogleSheetsValuesResource(Protocol):
    def get(self, **kwargs: Any) -> GoogleSheetsRequest: ...


class GoogleSheetsSpreadsheetsResource(Protocol):
    def values(self) -> GoogleSheetsValuesResource: ...


class GoogleSheetsService(Protocol):
    def spreadsheets(self) -> GoogleSheetsSpreadsheetsResource: ...


class GoogleSheetsRowReader:
    """Convert one read-only Google Sheets values response into worksheet rows."""

    def __init__(
        self,
        service: GoogleSheetsService,
        *,
        first_row: int = 1,
    ) -> None:
        if first_row < 1:
            raise ValueError("first_row must be a positive Google Sheet row number")
        self._service = service
        self._first_row = first_row

    def read_rows(
        self,
        worksheet: WorksheetIdentity,
    ) -> tuple[WorksheetRow, ...]:
        read_range = _a1_range(worksheet.worksheet, self._first_row)
        try:
            response = (
                self._service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=worksheet.spreadsheet,
                    range=read_range,
                    majorDimension="ROWS",
                    valueRenderOption="UNFORMATTED_VALUE",
                )
                .execute()
            )
            values = response.get("values", [])
            return _to_worksheet_rows(values, first_row=self._first_row)
        except GoogleSheetsReadError:
            raise
        except Exception as exc:
            raise GoogleSheetsReadError(
                f"Unable to read worksheet {worksheet.worksheet!r}"
            ) from exc


def _a1_range(worksheet_title: str, first_row: int) -> str:
    escaped_title = worksheet_title.replace("'", "''")
    return f"'{escaped_title}'!A{first_row}:G"


def _to_worksheet_rows(
    values: object,
    *,
    first_row: int,
) -> tuple[WorksheetRow, ...]:
    if values is None:
        raise GoogleSheetsReadError("Google Sheets values response is null")
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise GoogleSheetsReadError("Google Sheets values response is not a row sequence")

    rows: list[WorksheetRow] = []
    for offset, raw_row in enumerate(values):
        if not isinstance(raw_row, Sequence) or isinstance(raw_row, (str, bytes)):
            raise GoogleSheetsReadError(
                "Google Sheets values response contains an invalid row"
            )
        cells = {
            column: raw_row[index] if index < len(raw_row) else None
            for index, column in enumerate("ABCDEFG")
        }
        rows.append(
            WorksheetRow(
                row_position=first_row + offset,
                cells=cells,
            )
        )
    return tuple(rows)
