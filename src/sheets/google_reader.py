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


def execute_google_read(operation, *, retry_wait):
    """One bounded retry contract for source rows and read-only sheet metadata."""
    for attempt in range(5):
        try:
            return operation()
        except Exception as exc:
            if not _temporary_read_failure(exc):
                raise
            if attempt == 4 or retry_wait(2 * (attempt + 1)):
                raise GoogleSheetsReadUnavailable("Google read retry exhausted") from exc


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
        on_observation=lambda worksheet, rows, failed: None,
    ) -> None:
        if first_row < 1:
            raise ValueError("first_row must be a positive Google Sheet row number")
        self._on_observation = on_observation
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

    @property
    def live_read_revision(self):
        value = getattr(self._service, "live_read_revision", None)
        return value if type(value) is int else None

    def read_discovery_rows(self, worksheet):
        # The shared transport owns TTL and invalidation across cycles/modules.
        # Never let the legacy per-cycle snapshot outlive that verified cache.
        if callable(getattr(self._service, "get_discovery", None)):
            return self._read_rows(worksheet, discovery=True)
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
        return self._read_rows(worksheet, discovery=False)

    def _read_rows(self, worksheet, *, discovery):
        read_range = _a1_range(worksheet.worksheet, self._first_row)
        try:
            resource = self._service.spreadsheets().values()
            get = resource.get_discovery if discovery else resource.get
            response = execute_google_read(
                lambda: get(
                    spreadsheetId=worksheet.spreadsheet,
                    range=read_range, majorDimension="ROWS",
                    valueRenderOption="UNFORMATTED_VALUE",
                ).execute(), retry_wait=self._retry_wait)
            values = response.get("values", [])
            rows = _to_worksheet_rows(values, first_row=self._first_row)
            cache = self._discovery.get()
            if cache is not None:
                # A mandatory live check also refreshes later discovery, but a
                # discovery snapshot never substitutes for that live check.
                cache[worksheet] = tuple(
                    WorksheetRow(row.row_position, MappingProxyType(dict(row.cells))) for row in rows
                )
            self._on_observation(worksheet, rows, False)
            return rows
        except GoogleSheetsReadError:
            self._on_observation(worksheet, (), True)
            self._invalidate_discovery(worksheet)
            raise
        except Exception as exc:
            self._on_observation(worksheet, (), True)
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
