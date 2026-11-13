"""Service-Account Google Sheets transport behind the existing duck-typed service.

The repository already has one Google read/write abstraction: the adapters in
``google_reader``/``google_writer``/``quotation_input``/``tp_brief`` consume an
API-shaped service object. ``launcher.google_web`` provides that shape over the
native Sheets UI (CDP). This module provides the *same* shape over the official
Sheets API using the verified Service Account credential, so no business
adapter, ledger, scheduler or browser manager is duplicated.

Only the container-bound "更新报价" button stays on CDP; it is a Sheets script
that the API cannot trigger.

The native transport returned TSV display text and a numeric quantity. This one
reproduces that typing explicitly per column (``FORMATTED_VALUE`` + a fixed
per-column contract) instead of leaking raw JSON numbers, so dates never arrive
as serial numbers and identifiers never lose their leading zeros.
"""

import json
import re
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
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
SOURCE_TITLES = frozenset({"2026", "SHAHAB"})
QUOTE_INPUT_TITLE = "报价输入"
READ_TITLES = SOURCE_TITLES | {QUOTE_INPUT_TITLE}
SOURCE_WIDTH = 7
QUOTE_INPUT_WIDTH = 14
SNAPSHOT_TTL_SECONDS = 60.0
DEFAULT_HTTP_TIMEOUT_SECONDS = 30

# Only the exact source read that carries the Owner-visible quote date is widened
# from A:G to A:W. Nothing else may read beyond column G.
_SOURCE_RANGE = re.compile(r"^'((?:[^']|'')+)'!A(\d+):G$")
_FIXED_RANGE = re.compile(r"^'((?:[^']|'')+)'!([A-Z]{1,2})(\d*)(?::([A-Z]{1,2})(\d*))?$")
_RECEIPT_RANGE = re.compile(
    r"^(?:'((?:[^']|'')+)'|([^!']+))!([A-Z]{1,2})(\d+)(?::([A-Z]{1,2})(\d+))?$")
# Same worksheet-identity proof the retired TSV transport applied to its download.
SOURCE_HEADERS = {
    "2026": (0, {0: "STATUS", 2: "CLASS", 4: "MPN", 5: "MFR", 6: "Qty"}),
    "SHAHAB": (1, {1: "STATUS", 3: "Part Number", 4: "Brand", 5: "QTY"}),
}
_BRIEF_RANGE = "RFQ_BRIEF!A1:Q"
_BRIEF_TITLE = "RFQ_BRIEF"
_BRIEF_WIDTH = 17
_QUANTITY_NUMBER = re.compile(r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?")


class GoogleSheetsWriteUnconfirmed(RuntimeError):
    """The API may have applied an external write; never retried blindly."""


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


def _text_cell(value):
    """The display text of the same cell, never a guessed or re-padded identity.

    A JSON number only round-trips when it is an exact integer the native
    download would have printed without exponent notation. Anything else is
    returned untouched so the existing row-level identity checks reject it
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


def _display_text(value):
    """The cell's display text for every non-identity column (price, date, note)."""
    if isinstance(value, str) or value is None:
        return "" if value is None else value
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() and abs(value) < 1e15 else repr(value)
    return value


def _quantity_cell(value):
    """Exactly the old TSV quantity rule: blank → None, number → int/float."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and _QUANTITY_NUMBER.fullmatch(value):
        number = Decimal(value.replace(",", ""))
        return int(number) if number == number.to_integral_value() else float(number)
    return value


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
                majorDimension="ROWS", valueRenderOption="FORMATTED_VALUE",
            ).execute())
            rows = tuple(
                tuple(_text_cell(value) for value in _pad(list(row), _BRIEF_WIDTH))
                for row in response.get("values", []) or ()
            )
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
        title, first_column, first_row, last_column = _parse_range(range_name)
        _require_read_target(title, first_column, last_column)
        # The native transport always downloaded from A1 (A:G) and sliced the
        # requested rows afterwards, so the quote-date column comes from the
        # same complete read. Keep that exact geometry here.
        widen = title == "2026" and first_column == 1 and last_column == SOURCE_WIDTH
        # Source sheets are always read from row 1, exactly like the native
        # download, so the header proof and the requested slice share one read.
        source_read = title in SOURCE_TITLES
        requested = (f"'2026'!A1:{SOURCE_ORDER_COLUMN}" if widen
                     else f"'{_escaped(title)}'!A1:G" if source_read else range_name)
        response = self._call(lambda: self._service.spreadsheets().values().get(
            spreadsheetId=spreadsheet, range=requested,
            majorDimension=options.get("majorDimension", "ROWS"),
            # Display parity with the TSV download: dates are never raw serials.
            valueRenderOption="FORMATTED_VALUE",
        ).execute())
        if not isinstance(response, dict):
            raise ValueError("GOOGLE_RESPONSE_UNCONFIRMED")  # noqa: TRY004 - transport contract
        rows = response.get("values", []) or ()
        if source_read:
            # One contract over A..W keeps the header proof, the W evidence and
            # the A:G identity cells literally the same values.
            full = _apply_contract(rows, title, 1,
                                   QUOTE_DATE_INDEX + 1 if widen else SOURCE_WIDTH)
            _require_source_header(full, title)
            values = [row[:SOURCE_WIDTH] for row in full[first_row - 1:]]
            evidence = _order_date_evidence(full) if widen else None
        else:
            values = _apply_contract(rows[first_row - 1:], title, first_column, last_column)
            evidence = None
        answer = {"range": range_name, "majorDimension": "ROWS", "values": values}
        if evidence is not None:
            answer["source_order_dates"] = evidence
        with self._lock:
            self._live_read_revision += 1
        self._on_read_success()
        return answer

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
                       for value in values[0])):
            raise ValueError("GOOGLE_WRITE_UNCONFIRMED")
        title, first_column, first_row, last_column = _parse_range(range_name)
        _require_write_target(title, first_column, first_row, last_column, len(values[0]))
        # A write changes whatever snapshot this transport may still hold.
        self._clear_snapshots()
        response = self._call(lambda: self._service.spreadsheets().values().update(
            spreadsheetId=spreadsheet, range=range_name, valueInputOption="RAW",
            body={"majorDimension": "ROWS", "values": values},
        ).execute())
        _verify_write_receipt(response, spreadsheet, title, first_column, first_row, last_column)
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
    first_row = int(match.group(3)) if match.group(3) else 1
    if last < first:
        raise ValueError("GOOGLE_RANGE_UNCONFIRMED")
    return match.group(1).replace("''", "'"), first, first_row, last


def _require_read_target(title, first_column, last_column):
    """The old read whitelist: known titles, source A:G, 14-cell input row."""
    if title not in READ_TITLES:
        raise ValueError("GOOGLE_SHEET_UNCONFIRMED")
    if title in SOURCE_TITLES:
        if (first_column, last_column) != (1, SOURCE_WIDTH):
            raise ValueError("GOOGLE_RANGE_UNCONFIRMED")
        return
    if last_column - first_column + 1 != QUOTE_INPUT_WIDTH:
        raise ValueError("GOOGLE_RANGE_UNCONFIRMED")


def _require_write_target(title, first_column, first_row, last_column, width):
    """The old write whitelist: one raw14 row, else one schema-approved cell."""
    if title not in READ_TITLES:
        raise ValueError("GOOGLE_SHEET_UNCONFIRMED")
    if width != last_column - first_column + 1:
        raise ValueError("GOOGLE_WRITE_UNCONFIRMED")
    if title == QUOTE_INPUT_TITLE:
        if width != QUOTE_INPUT_WIDTH:
            raise ValueError("GOOGLE_WRITE_UNCONFIRMED")
        return
    schema = worksheet_schema(title)
    allowed = {schema.status_column, schema.model_column, schema.brand_column,
               schema.quantity_column, schema.importance_column}
    if first_column != last_column or width != 1:
        raise ValueError("GOOGLE_WRITE_UNCONFIRMED")
    if _column_letter(first_column) not in allowed:
        raise ValueError("GOOGLE_WRITE_UNCONFIRMED")
    if first_row < 1:
        raise ValueError("GOOGLE_WRITE_UNCONFIRMED")


def _column_letter(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _apply_contract(rows, title, first_column, last_column):
    """FORMATTED_VALUE rows plus the exact CDP-era per-column typing.

    Source sheets keep one numeric column (quantity) and text everywhere else;
    the 14-cell quotation row and RFQ_BRIEF are text only.
    """
    width = last_column - first_column + 1
    padded = [_pad(list(row), width) for row in rows]
    quantity_index = model_index = None
    if title in SOURCE_TITLES:
        schema = worksheet_schema(title)
        quantity_index = _column_number(schema.quantity_column) - first_column
        model_index = _column_number(schema.model_column) - first_column
    for row in padded:
        for index in range(width):
            if index == quantity_index:
                row[index] = _quantity_cell(row[index])
            elif index == model_index:
                # An identifier is never re-padded or guessed.
                row[index] = _text_cell(row[index])
            else:
                row[index] = _display_text(row[index])
    return padded


def _escaped(title: str) -> str:
    return title.replace("'", "''")


def _require_source_header(rows, title):
    """The exact worksheet identity the retired TSV download required."""
    position, expected = SOURCE_HEADERS[title]
    if position >= len(rows) or any(
            index >= len(rows[position]) or rows[position][index] != label
            for index, label in expected.items()):
        # Same fault type/reason the CDP transport raised; imported lazily so this
        # transport stays importable without the workflow package.
        from src.workflow.v12_faults import FaultScope, V12Fault

        raise V12Fault(FaultScope.GLOBAL_STOP, "SHEETS_SCHEMA_UNAVAILABLE")


def _order_date_evidence(rows):
    """Exactly the CDP proof: unique W header plus per-row E/F/G identity."""
    if not rows:
        return None
    header = list(rows[0])
    if SOURCE_ORDER_HEADER not in header:
        return None
    if (len(header) <= QUOTE_DATE_INDEX or header[QUOTE_DATE_INDEX] != SOURCE_ORDER_HEADER
            or header.count(SOURCE_ORDER_HEADER) != 1):
        raise ValueError("GOOGLE_ORDER_DATE_HEADER_AMBIGUOUS")
    proofs = []
    for offset, row in enumerate(rows):
        if offset == 0 or len(row) <= 4 or not row[4]:
            continue
        proofs.append((offset + 1, row[4],
                       row[5] if len(row) > 5 else "",
                       row[6] if len(row) > 6 else "",
                       row[QUOTE_DATE_INDEX] if len(row) > QUOTE_DATE_INDEX else ""))
    return {"column": SOURCE_ORDER_COLUMN, "header": SOURCE_ORDER_HEADER, "rows": proofs}


def _verify_write_receipt(response, spreadsheet, title, first_column, first_row, last_column):
    """Require the server to confirm exactly the requested target and cell count."""
    if not isinstance(response, dict):
        raise GoogleSheetsWriteUnconfirmed("GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED")
    reported = response.get("spreadsheetId")
    if isinstance(reported, str) and reported != spreadsheet:
        raise GoogleSheetsWriteUnconfirmed("GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED")
    updated_range = response.get("updatedRange")
    updated_cells = response.get("updatedCells")
    if not isinstance(updated_cells, int) or isinstance(updated_cells, bool):
        raise GoogleSheetsWriteUnconfirmed("GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED")
    expected_cells = last_column - first_column + 1
    if updated_cells != expected_cells:
        raise GoogleSheetsWriteUnconfirmed("GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED")
    if not isinstance(updated_range, str):
        raise GoogleSheetsWriteUnconfirmed("GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED")
    match = _RECEIPT_RANGE.fullmatch(updated_range)
    if match is None:
        raise GoogleSheetsWriteUnconfirmed("GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED")
    receipt_title = (match.group(1) or match.group(2) or "").replace("''", "'")
    receipt_first = _column_number(match.group(3))
    receipt_row = int(match.group(4))
    receipt_last = _column_number(match.group(5)) if match.group(5) else receipt_first
    receipt_last_row = int(match.group(6)) if match.group(6) else receipt_row
    if (receipt_title.casefold() != title.casefold()
            or receipt_first != first_column or receipt_last != last_column
            or receipt_row != first_row or receipt_last_row != first_row):
        raise GoogleSheetsWriteUnconfirmed("GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED")
