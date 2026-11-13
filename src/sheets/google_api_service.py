"""Service-Account Google Sheets transport behind the existing duck-typed service.

The repository already has one Google read/write abstraction: the adapters in
``google_reader``/``google_writer``/``quotation_input``/``tp_brief`` consume an
API-shaped service object. ``launcher.google_web`` provides that shape over the
native Sheets UI (CDP). This module provides the *same* shape over the official
Sheets API using the verified Service Account credential, so no business
adapter, ledger, scheduler or browser manager is duplicated.

Only the container-bound "更新报价" button stays on CDP; it is a Sheets script
that the API cannot trigger.
"""

import json
import re
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from time import monotonic
from typing import Any

from src.core.protected_local_store import unprotect_bytes

from .google_oauth import (
    READ_ONLY_SCOPE,
    READ_WRITE_SCOPE,
    GoogleSheetsAuthorizationError,
    GoogleSheetsDependencyError,
)
from .worksheet_schema import worksheet_schema

SOURCE_ORDER_COLUMN = "W"
SOURCE_ORDER_HEADER = "quote_date"
QUOTE_DATE_INDEX = 22  # Column W is the 23rd column of the 2026 source sheet.
_IDENTITY_WORKSHEETS = frozenset({"2026", "SHAHAB"})
SNAPSHOT_TTL_SECONDS = 60.0
DEFAULT_HTTP_TIMEOUT_SECONDS = 30

# Only the exact source read that carries the Owner-visible quote date is widened
# from A:G to A:W. Nothing else may read beyond column G.
_SOURCE_RANGE = re.compile(r"^'((?:[^']|'')+)'!A(\d+):G$")
_FIXED_RANGE = re.compile(r"^'((?:[^']|'')+)'!([A-Z]{1,2})(\d*)(?::([A-Z]{1,2})(\d*))?$")
_BRIEF_RANGE = "RFQ_BRIEF!A1:Q"
_BRIEF_WIDTH = 17


class GoogleSheetsWriteUnconfirmed(RuntimeError):
    """The API answered but did not confirm the written range."""


@dataclass(frozen=True)
class _Request:
    operation: Any

    def execute(self):
        return self.operation()


def _column_number(letters: str) -> int:
    number = 0
    for char in letters:
        number = number * 26 + ord(char) - 64
    return number


def _pad(row: list, width: int) -> list:
    """A1 responses trim trailing empties; the CDP transport never did."""
    return list(row) + [""] * (width - len(row)) if len(row) < width else list(row[:width])


def load_service_account_info(source: str | Path) -> dict:
    """Read one repository-external key file, plain JSON or DPAPI-protected."""
    path = Path(source)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        # A missing/inaccessible key is a credential condition, never a crash at
        # the first business read.
        raise GoogleSheetsAuthorizationError(
            "Google service account key is unreadable"
        ) from exc
    try:
        info = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        from src.core.protected_local_store import ProtectedStoreError

        try:
            info = json.loads(unprotect_bytes(raw).decode("utf-8"))
        except (ProtectedStoreError, UnicodeDecodeError, ValueError) as exc:
            raise GoogleSheetsAuthorizationError(
                "Google service account key is unreadable"
            ) from exc
    if not isinstance(info, dict) or not {'client_email', 'private_key', 'token_uri'} <= set(info):
        raise GoogleSheetsAuthorizationError("Google service account key is incomplete")
    return info


def build_service_account_sheets_service(
    service_account_file: str | Path,
    *,
    scope: str = READ_WRITE_SCOPE,
    timeout: int = DEFAULT_HTTP_TIMEOUT_SECONDS,
    on_read_success=lambda: None,
    timer=monotonic,
) -> "GoogleApiSheetsService":
    """Build the API transport once; no OAuth consent, no refresh token."""
    if scope not in {READ_ONLY_SCOPE, READ_WRITE_SCOPE}:
        raise ValueError("GOOGLE_API_SCOPE_UNSUPPORTED")
    try:
        import google_auth_httplib2
        import httplib2
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GoogleSheetsDependencyError(
            "Install google-api-python-client, google-auth and google-auth-httplib2"
        ) from exc

    info = load_service_account_info(service_account_file)
    try:
        # The key material stays in memory only; nothing is cached to disk.
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=[scope]
        )
        http = google_auth_httplib2.AuthorizedHttp(
            credentials, http=httplib2.Http(timeout=timeout)
        )
        service = build("sheets", "v4", http=http, cache_discovery=False)
    except GoogleSheetsAuthorizationError:
        raise
    except Exception:  # noqa: BLE001 - sanitize credential/client construction
        raise GoogleSheetsAuthorizationError(
            "Unable to authorize read/write Google Sheets access"
        ) from None
    return GoogleApiSheetsService(service, timer=timer, on_read_success=on_read_success)


class GoogleApiSheetsService:
    """The API-shaped transport the existing adapters already expect."""

    external_write = True  # A writer outside the browser page: reload before the script.

    def __init__(self, service, *, timer=monotonic, on_read_success=lambda: None) -> None:
        self._service = service
        self._timer = timer
        self._on_read_success = on_read_success
        self._lock = RLock()
        self._snapshots = OrderedDict()
        self._brief_revisions = {}
        self._live_read_revision = 0

    # --- transport shape -------------------------------------------------
    def spreadsheets(self):
        return self

    def values(self):
        return self

    @property
    def live_read_revision(self):
        return self._live_read_revision

    def get(self, **kwargs):
        def read():
            if "range" in kwargs:
                return self._read_range(kwargs)
            return self._call(lambda: self._service.spreadsheets().get(**kwargs).execute())

        return _Request(read)

    def update(self, **kwargs):
        return _Request(lambda: self._write_range(kwargs))

    # --- browser-only lifecycle ports (no pages are owned here) ----------
    @contextmanager
    def poll_scope(self):
        yield

    @contextmanager
    def suspend_idle_poll(self):
        yield

    def operations_idle(self):
        return True

    def release_retained_pages(self, **_kwargs):
        return None

    def close(self):
        return None

    # --- RFQ_BRIEF --------------------------------------------------------
    def read_brief(self, spreadsheet: str):
        with self._lock:
            response = self._call(lambda: self._service.spreadsheets().values().get(
                spreadsheetId=spreadsheet, range=_BRIEF_RANGE,
                majorDimension="ROWS", valueRenderOption="UNFORMATTED_VALUE",
            ).execute())
            rows = tuple(tuple(_pad(row, _BRIEF_WIDTH)) for row in response.get("values", []) or ())
            self._remember(spreadsheet, rows)
            return {"values": [list(row) for row in rows]}

    def read_brief_discovery(self, spreadsheet: str):
        entry = self._unexpired(spreadsheet)
        if entry is not None:
            return {"values": [list(row) for row in entry[1]]}
        return self.read_brief(spreadsheet)

    def peek_brief_snapshot(self, spreadsheet: str):
        entry = self._unexpired(spreadsheet)
        return None if entry is None else {"values": [list(row) for row in entry[1]]}

    def peek_brief_token(self, spreadsheet: str):
        return self._brief_revisions.get(spreadsheet, 0), self._unexpired(spreadsheet)

    # --- internals --------------------------------------------------------
    def _call(self, operation):
        # One serialized client: the discovery/http pair is not re-entrant and the
        # existing reader/writer boundaries already classify what comes back.
        with self._lock:
            return operation()

    def _read_range(self, options):
        spreadsheet = options.get("spreadsheetId")
        range_name = options.get("range")
        if not isinstance(spreadsheet, str) or not isinstance(range_name, str):
            raise ValueError("GOOGLE_RANGE_UNCONFIRMED")  # noqa: TRY004 - transport contract
        title, first_column, last_column = _parse_range(range_name)
        width = last_column - first_column + 1
        requested = range_name
        match = _SOURCE_RANGE.fullmatch(range_name)
        widen = match is not None and match.group(1).replace("''", "'") == "2026"
        if widen:
            # The native transport always downloaded from A1 (A:G) and sliced the
            # requested rows afterwards, so the quote-date column comes from the
            # same complete read. Keep that exact geometry here.
            requested = f"'2026'!A1:{SOURCE_ORDER_COLUMN}"
        response = self._call(lambda: self._service.spreadsheets().values().get(
            spreadsheetId=spreadsheet, range=requested,
            majorDimension=options.get("majorDimension", "ROWS"),
            valueRenderOption=options.get("valueRenderOption", "UNFORMATTED_VALUE"),
        ).execute())
        if not isinstance(response, dict):
            raise ValueError("GOOGLE_RESPONSE_UNCONFIRMED")  # noqa: TRY004 - transport contract
        rows = response.get("values", []) or ()
        start = int(match.group(2)) if widen else 1
        values = [_pad(list(row), width) for row in rows[start - 1:]]
        _normalise_model_column(values, title, first_column, last_column)
        answer = {"range": range_name, "majorDimension": "ROWS", "values": values}
        if widen:
            evidence = self._order_date_evidence(rows, 1)
            if evidence is not None:
                answer["source_order_dates"] = evidence
        with self._lock:
            self._live_read_revision += 1
        self._on_read_success()
        return answer

    @staticmethod
    def _order_date_evidence(rows, first_row):
        """Exactly the CDP proof: unique quote_date header plus per-row identity."""
        if not rows:
            return None
        header = list(rows[0])
        if len(header) > QUOTE_DATE_INDEX and header[QUOTE_DATE_INDEX] == SOURCE_ORDER_HEADER:
            pass
        elif SOURCE_ORDER_HEADER in header:
            raise ValueError("GOOGLE_ORDER_DATE_HEADER_AMBIGUOUS")
        else:
            return None
        proofs = []
        for offset, raw in enumerate(rows):
            row = list(raw)
            if offset == 0 or len(row) <= 4 or not row[4]:
                continue
            proofs.append((first_row + offset, row[4], row[5] if len(row) > 5 else "",
                           row[6] if len(row) > 6 else "",
                           row[QUOTE_DATE_INDEX] if len(row) > QUOTE_DATE_INDEX else ""))
        return {"column": SOURCE_ORDER_COLUMN, "header": SOURCE_ORDER_HEADER, "rows": proofs}

    def _write_range(self, options):
        spreadsheet = options.get("spreadsheetId")
        range_name = options.get("range")
        body = options.get("body")
        values = body.get("values") if isinstance(body, dict) else None
        if (not isinstance(spreadsheet, str) or not isinstance(range_name, str)
                or options.get("valueInputOption") != "RAW"
                or not isinstance(values, list) or len(values) != 1
                or not isinstance(values[0], list) or not values[0]
                or any(isinstance(value, bool) or not isinstance(value, (str, int, float))
                       for value in values[0])
                or len(values[0]) != _range_width(range_name)):
            raise ValueError("GOOGLE_WRITE_UNCONFIRMED")
        # A write changes whatever snapshot this transport may still hold.
        self._clear_snapshots()
        response = self._call(lambda: self._service.spreadsheets().values().update(
            spreadsheetId=spreadsheet, range=range_name, valueInputOption="RAW",
            body={"majorDimension": "ROWS", "values": values},
        ).execute())
        if (not isinstance(response, dict) or not isinstance(response.get("updatedRange"), str)
                or not isinstance(response.get("updatedCells"), int)):
            raise GoogleSheetsWriteUnconfirmed("GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED")
        return response

    def _unexpired(self, spreadsheet):
        with self._lock:
            entry = self._snapshots.get((spreadsheet, "RFQ_BRIEF"))
            if entry is None or not 0 <= self._timer() - entry[0] < SNAPSHOT_TTL_SECONDS:
                return None
            return entry

    def _remember(self, spreadsheet, rows):
        with self._lock:
            return self._remember_locked(spreadsheet, rows)

    def _remember_locked(self, spreadsheet, rows):
        key = (spreadsheet, "RFQ_BRIEF")
        entry = (self._timer(), tuple(tuple(row) for row in rows),
                 None, datetime.now(UTC))
        self._brief_revisions[spreadsheet] = self._brief_revisions.get(spreadsheet, 0) + 1
        self._snapshots[key] = entry
        self._snapshots.move_to_end(key)
        while len(self._snapshots) > 6:
            self._snapshots.popitem(last=False)
        return entry

    def _clear_snapshots(self):
        with self._lock:
            self._clear_snapshots_locked()

    def _clear_snapshots_locked(self):
        for spreadsheet, _ in self._snapshots:
            self._brief_revisions[spreadsheet] = self._brief_revisions.get(spreadsheet, 0) + 1
        self._snapshots.clear()


def _parse_range(range_name: str):
    """Only the fixed range shapes the canonical adapters already build."""
    match = _FIXED_RANGE.fullmatch(range_name)
    if match is None:
        raise ValueError("GOOGLE_RANGE_UNCONFIRMED")
    first = _column_number(match.group(2))
    last = _column_number(match.group(4)) if match.group(4) else first
    if last < first:
        raise ValueError("GOOGLE_RANGE_UNCONFIRMED")
    return match.group(1).replace("''", "'"), first, last


def _range_width(range_name: str) -> int:
    _title, first, last = _parse_range(range_name)
    return last - first + 1


def _identity_text(value):
    """The TSV display of the same cell, never a guessed or re-padded identity.

    A JSON number only round-trips when it is an exact integer in the range the
    native download would have printed without exponent notation. Anything else
    is returned untouched so the existing row-level identity checks reject it
    rather than the transport inventing a model name.
    """
    if isinstance(value, str) or value is None:
        return "" if value is None else value
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    return value


def _normalise_model_column(rows, title, first, last):
    """Only a source worksheet's model column is a business identity here.

    `worksheet_schema` falls back to the standard mapping for any other title,
    so the whitelist must be explicit: the 14-cell quotation input row and
    RFQ_BRIEF are payload text, never an identity to reinterpret.
    """
    if title not in _IDENTITY_WORKSHEETS:
        return
    schema = worksheet_schema(title)
    index = _column_number(schema.model_column) - first
    if not 0 <= index < last - first + 1:
        return
    for row in rows:
        row[index] = _identity_text(row[index])
