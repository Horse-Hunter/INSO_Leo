"""Missing web range transport; existing Sheets domain adapters remain canonical.

The API-shaped methods below are LOCAL compatibility calls, not Google API calls.
All I/O uses native Sheets UI through the existing protected Chrome session:
select sheet, File/Download TSV for reads, name box + formula editor for writes.
No OAuth, HTTP export endpoint, clipboard, private Sheets model, or new login.
"""
import asyncio
import csv
import io
import logging
import re
import threading
from collections import OrderedDict
from contextlib import ExitStack, contextmanager, nullcontext
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import monotonic
from urllib.parse import parse_qs, urlsplit

from src.research.cdp_pages import (
    bounded_browser_call,
    page_owner,
    shared_playwright_factory,
)
from src.sheets.google_reader import (
    TEMPORARY_READ_NETWORK_CODES,
    GoogleDownloadReadTimeout,
    GoogleReadArtifactLost,
)
from src.sheets.quotation_input import QuotationInputBusy, QuotationInputUnavailable
from src.sheets.worksheet_schema import worksheet_schema
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_quote_update import UpdateAttemptUnconfirmed

from .browser_bootstrap import BrowserHandle
from .diagnostics import log_step
from .google_quote_update import (
    _UNSAFE_POLL_PAGE,
    GoogleQuotationUpdateActions,
    GoogleReadTargetUnavailable,
    _retained_google_matches,
    _same_read_sheet_selection,
    google_operation_scope,
    google_operations_idle,
)

_GOOGLE_GRID_LOCK = threading.RLock()
_TITLES = ("2026", "SHAHAB", "报价输入")


_GoogleDownloadWaitTimeout = GoogleDownloadReadTimeout


def _download_call(download, operation, *, timeout):
    """Bound artifact waits on the SAME bundled synchronous client/Owner.

    Public Download.failure/path/delete have no timeout argument. Reuse its
    existing dispatcher and implementation coroutine, never another thread,
    event loop, connection or browser. Synthetic transport ports stay unchanged.
    """
    from playwright.sync_api import Download
    if not isinstance(download, Download):
        return getattr(download, operation)()
    async def bounded():
        return await asyncio.wait_for(getattr(download._impl_obj, operation)(), timeout)
    try:
        return download._sync(bounded())
    except TimeoutError as exc:
        log_step("google-download-" + operation + "-timeout", cause=exc)
        raise _GoogleDownloadWaitTimeout("GOOGLE_WEB_READ_DOWNLOAD_TIMEOUT") from None


def _temporary_web_read_failure(exc):
    """Unwrap only known read wrappers; unknown/auth/write faults stay closed."""
    visited, temporary = set(), False
    while exc is not None and id(exc) not in visited:
        visited.add(id(exc))
        if isinstance(exc, GoogleReadTargetUnavailable):
            return True  # Exact read-only boundary; no write or identity adoption.
        if isinstance(exc, V12Fault):
            return False
        if isinstance(exc, _GoogleDownloadWaitTimeout):
            return True  # Exact owned-read timeout; never an auth/identity failure.
        if type(exc).__module__.startswith("playwright"):
            if type(exc).__name__ == "TimeoutError":
                temporary = True
            else:
                codes = re.findall(r"net::(ERR_[A-Z_]+)", str(exc))
                if not codes or any(code not in TEMPORARY_READ_NETWORK_CODES for code in codes):
                    return False
                temporary = True
        elif isinstance(exc, (TimeoutError, ConnectionError)):
            temporary = True
        elif isinstance(exc, QuotationInputBusy) and str(exc) == "GOOGLE_QUOTATION_INPUT_BUSY":
            temporary = True  # Only the read caller uses this classifier.
        elif isinstance(exc, UpdateAttemptUnconfirmed) and str(exc) in {
            "GOOGLE_OPERATION_SURFACE_UNAVAILABLE", "GOOGLE_OPERATION_SURFACE_UNCONFIRMED",
        }:
            # A read lost its owned page/worksheet position. Reject its data and
            # re-enter on a fresh page; do not loosen any auth/document/gid guard.
            temporary = True
        elif not (isinstance(exc, UpdateAttemptUnconfirmed) and str(exc) in {
            "UPDATE_RESULT_UNCONFIRMED", "GOOGLE_NAVIGATION_FAILED",
        }):
            return False
        exc = exc.__cause__ or exc.__context__
    return temporary and exc is None


@dataclass(frozen=True)
class _Location:
    url: str


@dataclass
class _Request:
    operation: object

    def execute(self):
        return self.operation()


def _range(value):
    match = re.fullmatch(r"'((?:[^']|'')+)'!([A-Z]+)([1-9]\d*)(?::([A-Z]+)([1-9]\d*)?)?", value)
    if match is None:
        raise ValueError("GOOGLE_RANGE_UNCONFIRMED")
    title, first_col, first_row, last_col, last_row = match.groups()
    title = title.replace("''", "'")
    if title not in _TITLES:
        raise ValueError("GOOGLE_SHEET_UNCONFIRMED")
    def number(text):
        result = 0
        for char in text:
            result = result * 26 + ord(char) - 64
        return result
    first, last = number(first_col), number(last_col or first_col)
    start = int(first_row)
    end = int(last_row) if last_row else (None if last_col else start)
    if not 1 <= first <= last <= 26 or (end is not None and not start <= end <= 100000):
        raise ValueError("GOOGLE_RANGE_UNCONFIRMED")
    if end is None and (first_col != "A" or last_col != "G"):
        raise ValueError("GOOGLE_RANGE_UNCONFIRMED")
    return title, first, start, last, end


def _column(number):
    return chr(64 + number)  # Only the verified A:Z contract above.


def _source_values(rows, title, first, start, last, end):
    """Only quantity becomes numeric; never coerce MPN/brand or raw14 strings."""
    quantity = worksheet_schema(title).quantity_column if title not in {"报价输入", "RFQ_BRIEF"} else None
    answer = []
    for row in rows[start - 1:end]:
        values = []
        for index in range(first - 1, last):
            value = row[index] if index < len(row) else ""
            if quantity is not None:
                if not value:
                    value = None
                elif _column(index + 1) == quantity and re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", value):
                    number = Decimal(value.replace(",", ""))
                    value = int(number) if number == number.to_integral_value() else float(number)
            values.append(value)
        answer.append(values)
    return answer


def _readback_mismatch_code(confirmed, expected, first):
    """Only fixed column letters may leave the process; never include cell values."""
    if len(confirmed) != 1 or len(expected) != 1:
        return "GOOGLE_READBACK_ROW_UNCONFIRMED"
    actual, wanted = confirmed[0], expected[0]
    if len(actual) != len(wanted):
        return "GOOGLE_READBACK_SHAPE_UNCONFIRMED"
    columns = [_column(first + i) for i, (left, right) in enumerate(zip(actual, wanted, strict=True))
               if left != right]
    return "GOOGLE_READBACK_DIFF_" + "_".join(columns) if columns else "GOOGLE_READBACK_SHAPE_UNCONFIRMED"


def _no_read_guard():
    return None


class GoogleSheetsWebService:
    """One thread-safe transport injected into existing readers and writers."""
    def __init__(self, session, *, actions_factory=GoogleQuotationUpdateActions, on_read_success=lambda: None,
                 timer=monotonic, read_guard=_no_read_guard, stop_requested=lambda: False,
                 retain_pages=False, retire_session=None, isolated_read=False):
        self._session, self._actions_factory = session, actions_factory
        self._isolated_read = isolated_read
        self._grid_lock = threading.RLock() if isolated_read else _GOOGLE_GRID_LOCK
        if isolated_read:
            from functools import partial
            self._actions_factory = partial(actions_factory, page_role="google-mail-read")
        self._retire_session = retire_session or session
        self._on_read_success = on_read_success
        self._timer, self._read_guard, self._stop_requested = timer, read_guard, stop_requested
        # One bounded process-service cache; no pages, files or caller-mutable rows.
        self._snapshots = OrderedDict()
        self._brief_revisions = {}
        self._live_read_revision = 0
        self._retained_pages = {} if retain_pages else None
        self._poll_handle = ContextVar("google_web_poll_handle", default=None)

    def release_retained_pages(self, *, browser_handle=None):
        """Final drained-Owner cleanup only; never adopt previous-run pages.

        Registry IDs are the sole candidates. Unknown/protected/manual pages
        survive, including a known page whose worksheet was changed by Owner.
        Stop does not suppress cleanup; shared safety admission still does.
        """
        with self._grid_lock:
            if not self._retained_pages:
                return
            if self._poll_handle.get() is not None:
                raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_OPERATION_NOT_CLOSED")
            self._read_guard()
            if browser_handle is not None and (
                    browser_handle.owned or browser_handle._owner_thread != threading.get_ident()):
                raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED")
            session = (nullcontext(browser_handle) if browser_handle is not None
                       else self._retire_session())
            with session as handle:
                browser = handle.browser
                if handle.owned or browser is None or not browser.is_connected() or len(browser.contexts) != 1:
                    raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE")
                pages = tuple(browser.contexts[0].pages)
                for key, retained_entry in tuple(self._retained_pages.items()):
                    native, protected, _reopenable = retained_entry[:3]
                    if protected:
                        continue
                    self._read_guard()
                    matches = _retained_google_matches(pages, native)
                    if not matches:
                        self._retained_pages.pop(key, None)  # Gone, never reopen at shutdown.
                        continue
                    if len(matches) != 1:
                        raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED")
                    page = matches[0]
                    actual = urlsplit(page.url)
                    actions = self._actions_factory(browser_handle=handle, location=_Location(page.url))
                    actions._page = page
                    try:
                        actions._guard()
                        if ((actual.scheme, actual.hostname, actual.path) != key[:3]
                                or page_owner(page) != "google-operation"):
                            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED")
                        state = bounded_browser_call(page, "evaluate", """() => ({title: document.querySelector(
                            '.docs-sheet-active-tab .docs-sheet-tab-name')?.textContent})""")
                        if state.get("title") != key[3] or bounded_browser_call(page, "evaluate", _UNSAFE_POLL_PAGE):
                            self._retained_pages[key] = (native, True, False, False)
                            continue
                        actions.close()  # Original native close and last-tab protection.
                        if not page.is_closed():
                            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_OPERATION_NOT_CLOSED")
                    except BaseException:
                        self._retained_pages[key] = (native, True, False, False)
                        raise
                    self._retained_pages.pop(key, None)

    @contextmanager
    def poll_scope(self):
        # One client lifetime, same thread as native UI calls. Only target IDs
        # cross polls; attached Page objects are always resolved on this client.
        # Acquire lazily INSIDE the existing reader/writer error/retry boundary.
        if self._poll_handle.get() is not None:
            # Same original Owner, nested module: borrow the same per-title pool
            # rather than duplicate tabs/clients. Each native operation remains
            # serialized by _GOOGLE_GRID_LOCK and re-proves its protected surface.
            yield
            return
        with ExitStack() as lifetime, ExitStack() as pages:
            pages.enter_context(google_operation_scope(
                retained=self._retained_pages, lock=self._grid_lock))
            token = self._poll_handle.set({"handle": None, "lifetime": lifetime, "pages": pages})
            try:
                yield
            finally:
                self._poll_handle.reset(token)

    @contextmanager
    def suspend_idle_poll(self):
        """End proven-settled Page borrows before a nested module can replace CDP.

        Keep only the existing retained native IDs. The nested module receives
        its own normal scope; resumed quotation lazily resolves those exact IDs
        on the current original Owner client. No unsafe surface is discarded.
        """
        state = self._poll_handle.get()
        if state is None or not self.operations_idle():
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_OPERATION_NOT_CLOSED")
        state["pages"].close()  # Re-prove ownership/settlement while client is live.
        state["lifetime"].close()
        state["handle"] = None
        token = self._poll_handle.set(None)
        try:
            yield
        finally:
            self._poll_handle.reset(token)
            state["pages"].enter_context(google_operation_scope(
                retained=self._retained_pages, lock=self._grid_lock))

    @contextmanager
    def _operation_session(self):
        state = self._poll_handle.get()
        with ExitStack() as lifetime:
            try:
                if state is not None:
                    if state["handle"] is None:
                        state["handle"] = state["lifetime"].enter_context(self._session())
                    handle = state["handle"]
                else:
                    handle = lifetime.enter_context(self._session())
            except Exception as exc:
                # Only attachment failed; no UI operation/write has begun.
                if _temporary_web_read_failure(exc):
                    raise TimeoutError("GOOGLE_WEB_SESSION_UNAVAILABLE") from exc
                raise
            if state is None and self._retained_pages is not None:
                lifetime.enter_context(google_operation_scope(
                    retained=self._retained_pages, lock=self._grid_lock))
            yield handle

    def operations_idle(self):
        """Optional original-Owner checkpoint under the unchanged global lock."""
        with self._grid_lock:
            self._read_guard()
            if self._stop_requested() or self._poll_handle.get() is None:
                return False
            return google_operations_idle()

    def spreadsheets(self):
        return self

    def values(self):
        return self

    def get(self, **kwargs):
        # Existing metadata binding uses the same web sheet-title/gid proof.
        def read():
            result = self._execute(kwargs, write=False)
            self._on_read_success()
            return result
        return _Request(read)

    @property
    def live_read_revision(self):
        return self._live_read_revision

    def get_discovery(self, **kwargs):
        """Explicit ordinary discovery only; get() remains mandatory live I/O."""
        return _Request(lambda: self._execute(kwargs, write=False, discovery=True))

    def get_discovery_observed(self, **kwargs):
        """Discovery response with its actual source acquisition time."""
        return _Request(lambda: self._execute(kwargs, write=False, discovery=True, include_observation=True))

    def peek_brief_token(self, spreadsheet):
        """Nonblocking identity token for the existing unexpired immutable snapshot."""
        if not self._grid_lock.acquire(blocking=False):
            raise TimeoutError("GOOGLE_BRIEF_SNAPSHOT_BUSY")
        try:
            if self._stop_requested():
                raise TimeoutError("GOOGLE_BRIEF_SNAPSHOT_STOPPED")
            owner = getattr(self._read_guard, "__self__", None)
            check = getattr(owner, "is_open_nonblocking", None)
            if not (self._read_guard is _no_read_guard or callable(check) and check()):
                raise TimeoutError("GOOGLE_BRIEF_ADMISSION_UNCONFIRMED")
            entry = self._snapshots.get((spreadsheet, "RFQ_BRIEF"))
            live = entry if entry is not None and 0 <= self._timer()-entry[0] < 60.0 else None
            return self._brief_revisions.get(spreadsheet, 0), live
        finally:
            self._grid_lock.release()

    def peek_brief_snapshot(self, spreadsheet):
        """Optional ordinary-read hint only. Never attaches, refreshes or downloads."""
        with self._grid_lock:
            self._read_guard()
            if self._stop_requested():
                from src.workflow.v13_quotation import V13Stopped
                raise V13Stopped()
            entry = self._snapshots.get((spreadsheet, "RFQ_BRIEF"))
            if entry is None or not 0 <= self._timer() - entry[0] < 60.0:
                return None
            return {"values": [list(row) for row in entry[1]]}

    def read_brief_discovery(self, spreadsheet):
        return self._execute({"spreadsheetId": spreadsheet}, write=False,
                             brief_read=True, discovery=True)

    def update(self, **kwargs):
        return _Request(lambda: self._execute(kwargs, write=True))

    def read_brief(self, spreadsheet):
        """Dedicated exact-sheet read. No range/get/update whitelist is extended."""
        return self._execute({"spreadsheetId": spreadsheet}, write=False, brief_read=True)

    def _execute(self, options, *, write, brief_read=False, discovery=False, include_observation=False):
        if write and self._isolated_read:
            raise ValueError("GOOGLE_MAIL_READ_ONLY")
        # Reuse the canonical UI lock for hit/miss/write invalidation and single
        # flight. No UI objects cross threads and no TTL sleep/timer is introduced.
        with self._grid_lock:
            try:
                self._read_guard()
                if self._stop_requested():
                    from src.workflow.v13_quotation import V13Stopped
                    raise V13Stopped()
                spreadsheet = options.get("spreadsheetId")
                if not isinstance(spreadsheet, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", spreadsheet):
                    raise ValueError("GOOGLE_SPREADSHEET_UNCONFIRMED")
                geometry = (("RFQ_BRIEF", 1, 1, 17, None) if brief_read else
                            _range(options["range"]) if "range" in options else None)
                key = (spreadsheet, geometry[0]) if geometry else None
                if write and key:
                    self._forget_snapshot(key)  # Before ANY attempted effect.
                if not discovery:
                    # A mandatory live check must invalidate old discoveries even
                    # when it fails. It never consumes or certifies cached data.
                    if key:
                        self._forget_snapshot(key)
                    # Mandatory checks still perform native I/O. Their complete
                    # verified download may seed ordinary discovery afterwards.
                    seed = (not write and geometry is not None and
                            geometry[0] in {"2026", "SHAHAB", "RFQ_BRIEF"} and (brief_read or geometry[3] <= 7))
                    request = dict(options)
                    if seed and not brief_read:
                        request["range"] = f"'{geometry[0]}'!A1:G"
                    read_started = datetime.now(UTC)
                    result = self._execute_live(request, write=write, brief_read=brief_read)
                    if not write:
                        self._read_guard()
                        if self._stop_requested():
                            from src.workflow.v13_quotation import V13Stopped
                            raise V13Stopped()
                        self._live_read_revision += 1
                    if seed:
                        self._remember(key, result["values"], result.get("source_order_dates"), observed_at=read_started)
                        _, first, start, last, end = geometry
                        return self._source_response(result["values"], first, start, last, end, result.get("source_order_dates"))
                    return result
                if (write or geometry is None or geometry[0] not in {"2026", "SHAHAB", "RFQ_BRIEF"}
                        or (not brief_read and geometry[3] > 7)):
                    raise ValueError("GOOGLE_DISCOVERY_UNCONFIRMED")
                entry = self._snapshots.get(key)
                cache_hit = entry is not None and 0 <= self._timer() - entry[0] < 60.0
                if not cache_hit:
                    self._forget_snapshot(key)
                    request = dict(options)
                    if not brief_read:
                        request["range"] = f"'{geometry[0]}'!A1:G"
                    read_started = datetime.now(UTC)
                    result = self._execute_live(request, write=False, brief_read=brief_read)
                    self._read_guard()
                    if self._stop_requested():
                        from src.workflow.v13_quotation import V13Stopped
                        raise V13Stopped()
                    # Native download and header/worksheet/gid validation have
                    # completed; TTL starts now, never at navigation start.
                    values = tuple(tuple(row) for row in result["values"])
                    entry = self._remember(key, values, result.get("source_order_dates"), observed_at=read_started)
                    self._live_read_revision += 1
                    self._on_read_success()  # Real acquisition ONLY, never a hit.
                self._snapshots.move_to_end(key)
                _, first, start, last, end = geometry
                response = self._source_response(entry[1], first, start, last, end, entry[2] if len(entry) > 2 else None)
                if include_observation:
                    response["_inso_source_observed_at"] = entry[3].isoformat()
                    response["_inso_source_cache_hit"] = cache_hit
                return response
            except BaseException:
                # Includes Stop/cancellation, metadata/auth/Busy/schema failures.
                # A session fault cannot be hidden behind another sheet's cache.
                self._clear_snapshots()
                raise

    @staticmethod
    def _source_response(rows, first, start, last, end, evidence=None):
        result = {"values": [list(row[first-1:last]) for row in rows[start-1:end]]}
        if evidence is not None:
            result["source_order_dates"] = {"column": evidence.get("column"), "header": evidence.get("header"),
                "rows": [list(row) for row in evidence["rows"]]}
        return result

    def _mark_brief_change(self, key):
        if key is not None and key[1] == "RFQ_BRIEF":
            self._brief_revisions[key[0]] = self._brief_revisions.get(key[0], 0)+1

    def _forget_snapshot(self, key):
        if key in self._snapshots:
            self._mark_brief_change(key)
        self._snapshots.pop(key, None)

    def _clear_snapshots(self):
        for key in self._snapshots:
            self._mark_brief_change(key)
        self._snapshots.clear()

    def _remember(self, key, rows, evidence=None, *, observed_at=None):
        frozen = None if evidence is None else {"column": evidence.get("column"), "header": evidence.get("header"),
                                               "rows": tuple(tuple(row) for row in evidence["rows"])}
        entry = (self._timer(), tuple(tuple(row) for row in rows), frozen, observed_at or datetime.now(UTC))
        self._mark_brief_change(key)
        self._snapshots[key] = entry
        self._snapshots.move_to_end(key)
        if len(self._snapshots) > 6:
            evicted, _ = self._snapshots.popitem(last=False)
            self._mark_brief_change(evicted)
        return entry

    def _execute_live(self, options, *, write, brief_read=False):
        if brief_read and write:
            raise ValueError("GOOGLE_WRITE_UNCONFIRMED")
        spreadsheet = options.get("spreadsheetId")
        if not isinstance(spreadsheet, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", spreadsheet):
            raise ValueError("GOOGLE_SPREADSHEET_UNCONFIRMED")
        geometry = _range(options["range"]) if "range" in options else None
        if brief_read:
            geometry = ("RFQ_BRIEF", 1, 1, 17, None)
        if write and (geometry is None or options.get("valueInputOption") != "RAW"):
            raise ValueError("GOOGLE_WRITE_UNCONFIRMED")
        base = f"https://docs.google.com/spreadsheets/d/{spreadsheet}/edit#gid=0"
        with self._grid_lock, self._operation_session() as handle:
            actions = self._actions_factory(browser_handle=handle, location=_Location(base))
            actions._read_only = not write
            dirty = False
            stage = "google-open-sheet"
            try:
                if write and geometry[0] == "报价输入":
                    actions.ensure_refresh_input_idle()
                page = actions.open_sheet(select_worksheet=True,
                                          worksheet=geometry[0] if geometry else "2026")
                stage = "google-sheet-ready"
                bounded_browser_call(page.locator("#t-name-box"), "wait_for", state="visible", timeout=30000, timeout_ms=(30000)+1000)
                # Native READ does not depend on the quotation Apps Script.
                # Selection is proved before and after export; writes retain
                # the existing script-readiness requirement.
                if write:
                    actions.wait_for_script_menu()
                if geometry is None:
                    stage = "google-select-sheet"
                    sheets = []
                    for title in _TITLES:
                        gid = self._select(page, actions, title)
                        sheets.append({"properties": {"title": title, "sheetId": gid}})
                    return {"sheets": sheets}
                title, first, start, last, end = geometry
                stage = "google-select-sheet"
                self._select(page, actions, title)
                # Use native title and gid for both read and write readbacks;
                # a cached browser URL can lag the actual selected worksheet.
                actions._native_read_title = title
                if not write:
                    stage = "google-download-read"
                    rows = self._download(page, actions)
                    self._headers(rows, title)
                    result = {"values": _source_values(rows, title, first, start, last, end)}
                    # One native download contains the original W date as well
                    # as A:G. Carry only a uniquely headed, exact-row proof;
                    # never widen business input fields or read twice per row.
                    if title == "2026" and rows and "quote_date" in rows[0]:
                        if len(rows[0]) < 23 or rows[0][22] != "quote_date" or rows[0].count("quote_date") != 1:
                            raise ValueError("GOOGLE_ORDER_DATE_HEADER_AMBIGUOUS")
                        basic = _source_values(rows, title, 1, 1, 7, None)
                        result["source_order_dates"] = {"column": "W", "header": "quote_date", "rows": [
                            (n, basic[n-1][4], basic[n-1][5], basic[n-1][6], raw[22] if len(raw)>22 else "")
                            for n,raw in enumerate(rows,1) if n>1 and len(raw)>4 and raw[4]]}
                    return result
                values = options.get("body", {}).get("values")
                if (not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], list)
                        or end != start or len(values[0]) != last - first + 1
                        or (title == "报价输入" and last - first + 1 != 14)
                        or (title != "报价输入" and first != last)):
                    raise ValueError("GOOGLE_WRITE_UNCONFIRMED")
                if title != "报价输入":
                    schema = worksheet_schema(title)
                    columns = {schema.status_column, schema.model_column, schema.brand_column,
                               schema.quantity_column, schema.importance_column}
                    if _column(first) not in columns:
                        raise ValueError("GOOGLE_WRITE_UNCONFIRMED")
                    self._headers(self._download(page, actions), title)
                for offset, value in enumerate(values[0]):
                    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                        raise TypeError("GOOGLE_VALUE_UNCONFIRMED")
                    actions._guard()
                    stage = "google-write-select-cell"
                    cell = f"{_column(first + offset)}{start}"
                    box = page.locator("#t-name-box")
                    bounded_browser_call(box, "fill", cell, timeout_ms=31000)
                    bounded_browser_call(box, "press", "Enter", timeout_ms=31000)
                    bounded_browser_call(page, "wait_for_function", """cell => {
                        const box = document.querySelector('#t-name-box');
                        return !!box && box.value === cell && document.activeElement !== box;
                    }""", arg=cell, timeout=10000, timeout_ms=(10000)+1000)
                    if bounded_browser_call(box, "input_value") != cell:
                        raise ValueError("GOOGLE_SELECTION_UNCONFIRMED")
                    # Name-box Enter hands focus back to the selected grid cell.
                    # Sheets' formula-bar DOM fill does not commit its data model.
                    if bounded_browser_call(box, "evaluate", "element => element === document.activeElement"):
                        raise ValueError("GOOGLE_SELECTION_UNCONFIRMED")
                    actions._guard()
                    self._prove_active_sheet(page, actions, title, "write")
                    if page_owner(page) != actions._page_role:
                        actions._protected = True
                        raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED")
                    stage = "google-write-edit"
                    dirty = True
                    if isinstance(value, str):
                        # Sequential native input gives Sheets its key/input
                        # sequence; a bulk DOM/insertText replacement is ignored.
                        # Literal prefix preserves RAW text, not formula evaluation.
                        bounded_browser_call(page.keyboard, "type", "'" + value, delay=75, timeout_ms=max(10000, (len(value)+1)*75+10000))
                    else:
                        bounded_browser_call(page.keyboard, "type", str(value))
                    bounded_browser_call(page.keyboard, "press", "Enter")
                # Observed live UI badge; do not close a page with unsynced edits.
                stage = "google-write-save"
                bounded_browser_call(page, "wait_for_function",
                    '() => document.querySelector("#docs-save-indicator-badge")?.getAttribute("aria-label") === "文档状态：已保存到云端硬盘。"',
                    timeout=30000, timeout_ms=(30000)+1000)
                if title != "报价输入":
                    stage = "google-write-readback"
                    confirmed = _source_values(self._download(page, actions), title, first, start, last, end)
                    if confirmed != values:
                        logging.getLogger("inso.diagnostics").warning("Google readback differs", extra={
                            "runtime_reason": _readback_mismatch_code(confirmed, values, first),
                            "runtime_cause": "ReadbackMismatch",
                        })
                        raise ValueError("GOOGLE_WRITE_READBACK_MISMATCH")
                dirty = False
                return {"updatedCells": len(values[0])}
            except Exception as exc:
                closed_read = (not write and _temporary_web_read_failure(exc)
                               and actions.close_temporary_failed_read())
                if not closed_read:
                    actions.retire_failed_page(read_only=not write)
                if write:
                    log_step(stage, cause=exc)
                    reason = str(exc) if str(exc) in {
                        "GOOGLE_SELECTION_UNCONFIRMED", "GOOGLE_WRITE_READBACK_MISMATCH",
                        "GOOGLE_VALUE_UNCONFIRMED", "GOOGLE_WEB_READ_ARTIFACT_LOST",
                    } else "GOOGLE_WEB_WRITE_UNCLASSIFIED"
                    logging.getLogger("inso.diagnostics").warning("Google write classification", extra={
                        "runtime_reason": reason, "runtime_cause": type(exc).__name__})
                if dirty:
                    actions._protected = True
                    raise QuotationInputUnavailable("GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED") from None
                # Same bounded retry/next-15-minute policy as existing transient reads.
                # Never turn auth, unknown errors or write ambiguity into a retry.
                if not write:
                    temporary = _temporary_web_read_failure(exc)
                    log_step(stage, cause=exc)
                    reason = ("GOOGLE_WEB_READ_UNAVAILABLE" if temporary else
                              getattr(exc, "reason", "GOOGLE_WEB_READ_UNCLASSIFIED"))
                    if isinstance(exc, UpdateAttemptUnconfirmed) and str(exc) in {
                        "GOOGLE_OPERATION_SURFACE_UNAVAILABLE", "GOOGLE_OPERATION_SURFACE_UNCONFIRMED",
                    }:
                        reason = str(exc)  # Safe exact guard code; never page text/URLs.
                    elif isinstance(exc, _GoogleDownloadWaitTimeout):
                        reason = "GOOGLE_WEB_READ_DOWNLOAD_TIMEOUT"
                    elif isinstance(exc, TimeoutError) and str(exc) == "GOOGLE_WEB_READ_ARTIFACT_LOST":
                        reason = "GOOGLE_WEB_READ_ARTIFACT_LOST"
                    elif isinstance(exc, QuotationInputBusy):
                        reason = "GOOGLE_WEB_READ_BUSY"
                    logging.getLogger("inso.diagnostics").warning("Google read classification", extra={
                        "runtime_reason": reason, "runtime_cause": type(exc).__name__})
                    if temporary:
                        try:
                            actions._guard()
                        except Exception as guard:
                            # A failed navigation can still leave a blank/closed page.
                            navigation_failure = (
                                stage == "google-open-sheet"
                                and isinstance(exc, UpdateAttemptUnconfirmed)
                                and str(exc) == "GOOGLE_NAVIGATION_FAILED"
                                and isinstance(guard, V12Fault)
                                and guard.reason == "GOOGLE_SPREADSHEET_UNAVAILABLE"
                                and actions._page is not None
                                and actions._page.url == "chrome-error://chromewebdata/")
                            if not navigation_failure and (not isinstance(guard, UpdateAttemptUnconfirmed) or str(guard) not in {
                                "GOOGLE_OPERATION_SURFACE_UNAVAILABLE", "GOOGLE_OPERATION_SURFACE_UNCONFIRMED",
                            }):
                                raise
                        raise TimeoutError("GOOGLE_WEB_READ_UNAVAILABLE") from None
                raise
            finally:
                actions.close()  # Own tab only; reuse existing auth/script protection.

    @staticmethod
    def _headers(rows, title):
        if title == "RFQ_BRIEF":
            from src.sheets.tp_brief import BRIEF_HEADERS, TpLocalError
            if not rows or tuple(rows[0]) != BRIEF_HEADERS or any(len(r) > 17 for r in rows):
                raise TpLocalError("TP_BRIEF_SCHEMA_UNAVAILABLE")
            return
        contracts = {
            "2026": (0, {0: "STATUS", 2: "CLASS", 4: "MPN", 5: "MFR", 6: "Qty"}),
            "SHAHAB": (1, {1: "STATUS", 3: "Part Number", 4: "Brand", 5: "QTY"}),
        }
        if title not in contracts:
            return  # Existing quotation input is intentionally headerless.
        position, expected = contracts[title]
        if position >= len(rows) or any(index >= len(rows[position]) or rows[position][index] != label
                                        for index, label in expected.items()):
            raise V12Fault(FaultScope.GLOBAL_STOP, "SHEETS_SCHEMA_UNAVAILABLE")

    @staticmethod
    def _select(page, actions, title):
        previous = bounded_browser_call(page, "evaluate", '''() => ({
            title: document.querySelector('.docs-sheet-active-tab .docs-sheet-tab-name')?.textContent,
            fragment: location.hash})''')
        tab = page.locator(".docs-sheet-tab").filter(has=page.get_by_text(title, exact=True))
        if bounded_browser_call(tab, "count") == 0:
            bounded_browser_call(tab, "wait_for", state="visible", timeout=10000, timeout_ms=(10000)+1000)
        if bounded_browser_call(tab, "count") != 1:
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SHEET_UNCONFIRMED")
        bounded_browser_call(tab, "click", timeout=10000, timeout_ms=(10000)+1000)
        bounded_browser_call(page, "wait_for_function",
            '''arg => document.querySelector('.docs-sheet-active-tab .docs-sheet-tab-name')?.textContent === arg.title
                && (arg.already || location.hash !== arg.fragment)''',
            arg={"title": title, "already": previous["title"] == title, "fragment": previous["fragment"]},
            timeout=30000, timeout_ms=(30000)+1000)
        # History/active-tab state can precede the SDK frame-URL event. Bind
        # the native selected sheet, never the previous cached Page.url.
        selected = bounded_browser_call(page, "evaluate", """() => ({
            title: document.querySelector('.docs-sheet-active-tab .docs-sheet-tab-name')?.textContent,
            fragment: location.hash})""")
        if not isinstance(selected, dict) or selected.get("title") != title:
            log_step("google-select-title-drift")
            raise UpdateAttemptUnconfirmed("GOOGLE_OPERATION_SURFACE_UNCONFIRMED")
        fragment = selected.get("fragment", "").removeprefix("#")
        gid = parse_qs(fragment).get("gid", [])
        if (len(gid) != 1 or not gid[0].isdecimal()
                or not _same_read_sheet_selection(fragment, "gid="+gid[0])):
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SHEET_UNCONFIRMED")
        document = urlsplit(actions._location.url)
        def selected_url(url):
            actual = urlsplit(url)
            return ((actual.scheme, actual.hostname, actual.path) ==
                    (document.scheme, document.hostname, document.path) and actual.fragment == fragment)
        if not selected_url(page.url):
            log_step("google-select-url-sync")
            bounded_browser_call(page, "wait_for_url", selected_url, timeout=10000, wait_until="domcontentloaded", timeout_ms=(10000)+1000)
        if not selected_url(page.url):
            raise UpdateAttemptUnconfirmed("GOOGLE_OPERATION_SURFACE_UNCONFIRMED")
        # Rebind only after a unique visible tab and its active title are confirmed.
        expected = urlsplit(actions._location.url)
        actual = urlsplit(page.url)
        if (actual.scheme, actual.hostname, actual.path) != (expected.scheme, expected.hostname, expected.path):
            actions._guard()
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SPREADSHEET_UNAVAILABLE")
        actions._location = _Location(page.url)
        actions._guard()
        return int(gid[0])

    @staticmethod
    def _prove_active_sheet(page, actions, title, phase):
        try:
            actions._guard(read_selection=True)
        except UpdateAttemptUnconfirmed:
            log_step("google-"+phase+"-guard")
            raise
        observed = bounded_browser_call(page, "evaluate", """() => ({
            title: document.querySelector('.docs-sheet-active-tab .docs-sheet-tab-name')?.textContent,
            fragment: location.hash})""")
        if not isinstance(observed, dict) or observed.get("title") != title:
            log_step("google-"+phase+"-title")
            raise UpdateAttemptUnconfirmed("GOOGLE_OPERATION_SURFACE_UNCONFIRMED")
        fragment = observed.get("fragment")
        expected = urlsplit(actions._location.url).fragment
        if (not isinstance(fragment, str)
                or not _same_read_sheet_selection(fragment.removeprefix("#"), expected)):
            log_step("google-"+phase+"-fragment")
            raise UpdateAttemptUnconfirmed("GOOGLE_OPERATION_SURFACE_UNCONFIRMED")

    @staticmethod
    def _download(page, actions):
        def prove_selection(phase):
            expected = getattr(actions, "_native_read_title", None)
            if expected is None:
                actions._guard(read_selection=True)
            else:
                GoogleSheetsWebService._prove_active_sheet(page, actions, expected, "read-"+phase)
        prove_selection("pre")
        bounded_browser_call(page.get_by_role("menuitem", name="文件", exact=True), "click", timeout=10000, timeout_ms=(10000)+1000)
        bounded_browser_call(page.get_by_role("menuitem", name=re.compile("^下载")), "click", timeout=10000, timeout_ms=(10000)+1000)
        with page.expect_download(timeout=30000) as pending:
            bounded_browser_call(page.get_by_role("menuitem", name=re.compile(r"\.tsv\)")), "click", timeout=10000, timeout_ms=(10000)+1000)
        download = pending.value
        try:
            failure = _download_call(download, "failure", timeout=60)
            if failure:
                matched = re.fullmatch(r"(?:net::)?(ERR_[A-Z_]+)", failure.strip()) if isinstance(failure, str) else None
                if matched is None or matched.group(1) not in TEMPORARY_READ_NETWORK_CODES:
                    raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_DOWNLOAD_FAILURE_UNCLASSIFIED")
                raise TimeoutError("GOOGLE_WEB_READ_UNAVAILABLE")
            try:
                path = Path(_download_call(download, "path", timeout=10))
                if path.stat().st_size > 32 * 1024 * 1024:
                    raise ValueError("GOOGLE_WEB_READ_TOO_LARGE")
                content = path.read_text(encoding="utf-8-sig")
            except FileNotFoundError:
                # Only this owned export artifact is recoverable. A missing
                # configuration/credential or other unknown file still stops.
                raise GoogleReadArtifactLost("GOOGLE_WEB_READ_ARTIFACT_LOST") from None
            rows = list(csv.reader(io.StringIO(content), delimiter="\t"))
            if len(rows) > 100000:
                raise ValueError("GOOGLE_WEB_READ_TOO_LARGE")
            prove_selection("post")
            return rows
        except _GoogleDownloadWaitTimeout:
            try:
                _download_call(download, "cancel", timeout=10)
            except Exception as exc:  # noqa: BLE001 - preserve the original read timeout
                logging.getLogger("inso.diagnostics").warning(
                    "Google read export cancellation failed", extra={"runtime_cause": type(exc).__name__})
            raise
        finally:
            try:
                _download_call(download, "delete", timeout=10)
            except FileNotFoundError:
                pass  # Already removed; never mask a completed read/its real failure.
            except Exception as exc:  # noqa: BLE001 - cleanup cannot invalidate a completed read
                logging.getLogger("inso.diagnostics").warning(
                    "Google read export cleanup failed", extra={"runtime_cause": type(exc).__name__})


def build_google_web_service(cdp_url="http://127.0.0.1:9222", *, provider=None, browser_handle=None,
                             on_read_success=lambda: None, read_guard=_no_read_guard,
                             stop_requested=lambda: False, isolated_read=False, page_admission=None):
    """Reuse the existing shared Playwright provider; attach only, never launch/login."""
    if cdp_url.rstrip("/") != "http://127.0.0.1:9222":
        raise ValueError("CANONICAL_CDP_REQUIRED")

    if page_admission is None and browser_handle is not None:
        page_admission = getattr(browser_handle.browser, "_inso_page_admission", None)

    def shared():
        if browser_handle is not None:
            if getattr(browser_handle, "_owner_thread", threading.get_ident()) != threading.get_ident():
                return None
            return browser_handle.playwright, browser_handle.browser
        return provider() if provider else None

    @contextmanager
    def session(*, retire=False):
        # Final cleanup must never bootstrap Chrome through the business provider.
        with shared_playwright_factory(None if retire else shared, admission=page_admission)() as playwright:
            browser = playwright.chromium.connect_over_cdp(cdp_url, timeout=10000)
            if not browser.is_connected() or len(browser.contexts) != 1:
                raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE")
            yield BrowserHandle(owned=False, browser=browser)

    return GoogleSheetsWebService(session, on_read_success=on_read_success,
                                  read_guard=read_guard, stop_requested=stop_requested, retain_pages=not isolated_read, isolated_read=isolated_read,
                                  retire_session=lambda: session(retire=True))
