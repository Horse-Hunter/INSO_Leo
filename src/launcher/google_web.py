"""Missing web range transport; existing Sheets domain adapters remain canonical.

The API-shaped methods below are LOCAL compatibility calls, not Google API calls.
All I/O uses native Sheets UI through the existing protected Chrome session:
select sheet, File/Download TSV for reads, name box + formula editor for writes.
No OAuth, HTTP export endpoint, clipboard, private Sheets model, or new login.
"""
import csv
import io
import logging
import re
import threading
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from src.research.cdp_pages import shared_playwright_factory
from src.sheets.quotation_input import QuotationInputBusy, QuotationInputUnavailable
from src.sheets.worksheet_schema import worksheet_schema
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_quote_update import UpdateAttemptUnconfirmed

from .browser_bootstrap import BrowserHandle
from .diagnostics import log_step
from .google_quote_update import GoogleQuotationUpdateActions, google_operation_scope

_GOOGLE_GRID_LOCK = threading.RLock()
_TITLES = ("2026", "SHAHAB", "报价输入")


def _temporary_web_read_failure(exc):
    """Unwrap only known read wrappers; unknown/auth/write faults stay closed."""
    visited, temporary = set(), False
    while exc is not None and id(exc) not in visited:
        visited.add(id(exc))
        if isinstance(exc, V12Fault):
            return False
        if type(exc).__module__.startswith("playwright"):
            if type(exc).__name__ == "TimeoutError":
                temporary = True
            else:
                codes = re.findall(r"net::(ERR_[A-Z_]+)", str(exc))
                if not codes or any(code not in {
                    "ERR_TIMED_OUT", "ERR_CONNECTION_TIMED_OUT", "ERR_CONNECTION_RESET",
                    "ERR_CONNECTION_CLOSED", "ERR_CONNECTION_REFUSED", "ERR_EMPTY_RESPONSE",
                    "ERR_NAME_NOT_RESOLVED", "ERR_NETWORK_CHANGED", "ERR_INTERNET_DISCONNECTED",
                    "ERR_PROXY_CONNECTION_FAILED", "ERR_TUNNEL_CONNECTION_FAILED",
                } for code in codes):
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
    quantity = worksheet_schema(title).quantity_column if title != "报价输入" else None
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


class GoogleSheetsWebService:
    """One thread-safe transport injected into existing readers and writers."""
    def __init__(self, session, *, actions_factory=GoogleQuotationUpdateActions):
        self._session, self._actions_factory = session, actions_factory
        self._poll_handle = ContextVar("google_web_poll_handle", default=None)

    @contextmanager
    def poll_scope(self):
        # One client lifetime, same thread as native UI calls. No page crosses polls.
        # Acquire lazily INSIDE the existing reader/writer error/retry boundary.
        with ExitStack() as lifetime, google_operation_scope():
            token = self._poll_handle.set({"handle": None, "lifetime": lifetime})
            try:
                yield
            finally:
                self._poll_handle.reset(token)

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
            yield handle

    def spreadsheets(self):
        return self

    def values(self):
        return self

    def get(self, **kwargs):
        # Existing metadata binding uses the same web sheet-title/gid proof.
        return _Request(lambda: self._execute(kwargs, write=False))

    def update(self, **kwargs):
        return _Request(lambda: self._execute(kwargs, write=True))

    def _execute(self, options, *, write):
        spreadsheet = options.get("spreadsheetId")
        if not isinstance(spreadsheet, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", spreadsheet):
            raise ValueError("GOOGLE_SPREADSHEET_UNCONFIRMED")
        geometry = _range(options["range"]) if "range" in options else None
        if write and (geometry is None or options.get("valueInputOption") != "RAW"):
            raise ValueError("GOOGLE_WRITE_UNCONFIRMED")
        base = f"https://docs.google.com/spreadsheets/d/{spreadsheet}/edit#gid=0"
        with _GOOGLE_GRID_LOCK, self._operation_session() as handle:
            actions = self._actions_factory(browser_handle=handle, location=_Location(base))
            dirty = False
            stage = "google-open-sheet"
            try:
                if write and geometry[0] == "报价输入":
                    actions.ensure_refresh_input_idle()
                page = actions.open_sheet(select_worksheet=True,
                                          worksheet=geometry[0] if geometry else "2026")
                stage = "google-sheet-ready"
                page.locator("#t-name-box").wait_for(state="visible", timeout=30000)
                # Reuse the verified onOpen readiness signal. Selecting SHAHAB
                # before initialization settles can be reset to the initial tab.
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
                if not write:
                    stage = "google-download-read"
                    rows = self._download(page, actions)
                    self._headers(rows, title)
                    return {"values": _source_values(rows, title, first, start, last, end)}
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
                    box.fill(cell)
                    box.press("Enter")
                    if box.input_value() != cell:
                        raise ValueError("GOOGLE_SELECTION_UNCONFIRMED")
                    # Name-box Enter hands focus back to the selected grid cell.
                    # Sheets' formula-bar DOM fill does not commit its data model.
                    if box.evaluate("element => element === document.activeElement"):
                        raise ValueError("GOOGLE_SELECTION_UNCONFIRMED")
                    stage = "google-write-edit"
                    dirty = True
                    if isinstance(value, str):
                        # Sequential native input gives Sheets its key/input
                        # sequence; a bulk DOM/insertText replacement is ignored.
                        # Literal prefix preserves RAW text, not formula evaluation.
                        page.keyboard.type("'" + value, delay=75)
                    else:
                        page.keyboard.type(str(value))
                    page.keyboard.press("Enter")
                # Observed live UI badge; do not close a page with unsynced edits.
                stage = "google-write-save"
                page.wait_for_function(
                    '() => document.querySelector("#docs-save-indicator-badge")?.getAttribute("aria-label") === "文档状态：已保存到云端硬盘。"',
                    timeout=30000)
                stage = "google-write-readback"
                confirmed = _source_values(self._download(page, actions), title, first, start, last, end)
                if confirmed != values:
                    raise ValueError("GOOGLE_WRITE_READBACK_MISMATCH")
                dirty = False
                return {"updatedCells": len(values[0])}
            except Exception as exc:
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
        previous = page.evaluate('''() => ({
            title: document.querySelector('.docs-sheet-active-tab .docs-sheet-tab-name')?.textContent,
            fragment: location.hash})''')
        tab = page.locator(".docs-sheet-tab").filter(has=page.get_by_text(title, exact=True))
        if tab.count() == 0:
            tab.wait_for(state="visible", timeout=10000)
        if tab.count() != 1:
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SHEET_UNCONFIRMED")
        tab.click(timeout=10000)
        page.wait_for_function(
            '''arg => document.querySelector('.docs-sheet-active-tab .docs-sheet-tab-name')?.textContent === arg.title
                && (arg.already || location.hash !== arg.fragment)''',
            arg={"title": title, "already": previous["title"] == title, "fragment": previous["fragment"]},
            timeout=30000)
        gid = parse_qs(urlsplit(page.url).fragment).get("gid", [])
        if len(gid) != 1 or not gid[0].isdecimal():
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SHEET_UNCONFIRMED")
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
    def _download(page, actions):
        actions._guard()
        page.get_by_role("menuitem", name="文件", exact=True).click(timeout=10000)
        page.get_by_role("menuitem", name=re.compile("^下载")).click(timeout=10000)
        with page.expect_download(timeout=30000) as pending:
            page.get_by_role("menuitem", name=re.compile(r"\.tsv\)")).click(timeout=10000)
        download = pending.value
        try:
            failure = download.failure()
            if failure:
                raise TimeoutError("GOOGLE_WEB_READ_UNAVAILABLE")
            try:
                path = Path(download.path())
                if path.stat().st_size > 32 * 1024 * 1024:
                    raise ValueError("GOOGLE_WEB_READ_TOO_LARGE")
                content = path.read_text(encoding="utf-8-sig")
            except FileNotFoundError:
                # Only this owned export artifact is recoverable. A missing
                # configuration/credential or other unknown file still stops.
                raise TimeoutError("GOOGLE_WEB_READ_ARTIFACT_LOST") from None
            rows = list(csv.reader(io.StringIO(content), delimiter="\t"))
            if len(rows) > 100000:
                raise ValueError("GOOGLE_WEB_READ_TOO_LARGE")
            actions._guard()
            return rows
        finally:
            try:
                download.delete()  # Customer data stays temporary, never evidence/logs/Git.
            except FileNotFoundError:
                pass  # Already removed; never mask a completed read/its real failure.


def build_google_web_service(cdp_url="http://127.0.0.1:9222", *, provider=None, browser_handle=None):
    """Reuse the existing shared Playwright provider; attach only, never launch/login."""
    if cdp_url.rstrip("/") != "http://127.0.0.1:9222":
        raise ValueError("CANONICAL_CDP_REQUIRED")

    def shared():
        if browser_handle is not None:
            if getattr(browser_handle, "_owner_thread", threading.get_ident()) != threading.get_ident():
                return None
            return browser_handle.playwright, browser_handle.browser
        return provider() if provider else None

    @contextmanager
    def session():
        with shared_playwright_factory(shared)() as playwright:
            browser = playwright.chromium.connect_over_cdp(cdp_url, timeout=10000)
            if not browser.is_connected() or len(browser.contexts) != 1:
                raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE")
            yield BrowserHandle(owned=False, browser=browser)

    return GoogleSheetsWebService(session)
