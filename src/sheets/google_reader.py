"""Read-only Google Sheets API adapter for worksheet rows."""

import socket
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from types import MappingProxyType
from typing import Any, Protocol

from .pending import WorksheetIdentity, WorksheetRow


class GoogleSheetsReadError(RuntimeError):
    """A Google Sheets read failed or returned an invalid response."""


class GoogleSheetsReadUnavailable(GoogleSheetsReadError):
    """A transient read exhausted its bounded attempts; next poll may resume."""


def _temporary_read_failure(exc: Exception) -> bool:
    status = getattr(getattr(exc, "resp", None), "status", None)
    if isinstance(status, int):
        return status == 429 or 500 <= status < 600
    return isinstance(exc, (TimeoutError, ConnectionError, socket.gaierror)) or type(exc).__name__ in {
        "ServerNotFoundError", "TransportError", "ConnectTimeout", "ReadTimeout",
    }


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
        retry_wait=None,
    ) -> None:
        if first_row < 1:
            raise ValueError("first_row must be a positive Google Sheet row number")
        self._service = service
        self._first_row = first_row
        self._retry_wait = retry_wait or (lambda _seconds: False)
        self._discovery = ContextVar("google_source_discovery", default=None)

    @contextmanager
    def discovery_scope(self):
        """Only discovery opts in; ordinary read_rows ALWAYS re-reads the source."""
        token = self._discovery.set({})
        try:
            yield
        finally:
            self._discovery.reset(token)

    def clear_discovery_snapshot(self):
        """Quotation must see inquiry writes; never carry a snapshot across stages."""
        if self._discovery.get() is not None:
            self._discovery.set({})

    def read_discovery_rows(self, worksheet):
        cache = self._discovery.get()
        if cache is None:
            return self.read_rows(worksheet)
        if worksheet not in cache:
            self.read_rows(worksheet)
        return cache[worksheet]

    def read_rows(
        self,
        worksheet: WorksheetIdentity,
    ) -> tuple[WorksheetRow, ...]:
        read_range = _a1_range(worksheet.worksheet, self._first_row)
        try:
            for attempt in range(5):
                try:
                    response = (
                        self._service.spreadsheets().values().get(
                            spreadsheetId=worksheet.spreadsheet,
                            range=read_range, majorDimension="ROWS",
                            valueRenderOption="UNFORMATTED_VALUE",
                        ).execute()
                    )
                    break
                except Exception as exc:
                    if not _temporary_read_failure(exc):
                        raise
                    if attempt == 4 or self._retry_wait(2 * (attempt + 1)):
                        raise GoogleSheetsReadUnavailable("Google read retry exhausted") from exc
            values = response.get("values", [])
            rows = _to_worksheet_rows(values, first_row=self._first_row)
            cache = self._discovery.get()
            if cache is not None:
                # A mandatory live check also refreshes later discovery, but a
                # discovery snapshot never substitutes for that live check.
                cache[worksheet] = tuple(
                    WorksheetRow(row.row_position, MappingProxyType(dict(row.cells))) for row in rows
                )
            return rows
        except GoogleSheetsReadError:
            self._invalidate_discovery(worksheet)
            raise
        except Exception as exc:
            self._invalidate_discovery(worksheet)
            raise GoogleSheetsReadError(
                f"Unable to read worksheet {worksheet.worksheet!r}"
            ) from exc

    def _invalidate_discovery(self, worksheet):
        cache = self._discovery.get()
        if cache is not None:
            cache.pop(worksheet, None)


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
