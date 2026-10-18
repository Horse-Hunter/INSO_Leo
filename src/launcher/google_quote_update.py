"""Narrow Google quotation UI role/text contract on the existing protected CDP.

Named button or Owner-verified sole visible drawing. Configured geometry/gid is mandatory;
this module never discovers credentials, launches a browser, or calls Script URLs.
"""
import re
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from types import SimpleNamespace
from urllib.parse import urlsplit

from src.inso.quotation_read import QUOTATION_COLUMNS
from src.research.cdp_pages import new_background_page, page_owner
from src.sheets.quotation_input import (
    GoogleQuotationInput,
    QuotationInputBusy,
    QuotationInputLocation,
)
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_quote_update import (
    UpdateAttemptUnconfirmed,
    UpdateClickUnconfirmed,
    V13QuotationUpdater,
    WorkflowQuotationSource,
)

_SCRIPT_SETTLEMENT_LATCH = """button => {
    const previous = window.__insoQuoteSettlement;
    if (previous) previous.observer.disconnect();
    const latch = {confirmed: false, started: false, settled: false};
    const visibleRunning = () => {
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
            if (!node.textContent.includes('正在运行脚本')) continue;
            const element = node.parentElement;
            if (!element || !element.getClientRects().length) continue;
            const style = getComputedStyle(element);
            if (style.visibility !== 'hidden' && style.display !== 'none') return true;
        }
        return false;
    };
    const sample = () => {
        if (!latch.confirmed) return;
        const running = visibleRunning();
        if (running) { latch.started = true; latch.settled = false; }
        else if (latch.started) latch.settled = true;
    };
    latch.isRunning = visibleRunning;
    latch.observer = new MutationObserver(sample);
    latch.observer.observe(document.body, {
        subtree: true, childList: true, characterData: true, attributes: true
    });
    button.addEventListener('click', () => { latch.confirmed = true; sample(); },
        {capture: true, once: true});
    window.__insoQuoteSettlement = latch;
}"""

_REFRESH_INPUT_IDLE = """() => {
    const visible = e => e.getClientRects().length &&
        getComputedStyle(e).visibility !== 'hidden' && getComputedStyle(e).display !== 'none';
    const busy = [...document.querySelectorAll('[role="dialog"]')].some(visible) ||
        window.__insoQuoteSettlement?.isRunning();
    if (busy) { window.__insoRefreshQuietSince = null; return false; }
    window.__insoRefreshQuietSince ??= performance.now();
    return performance.now() - window.__insoRefreshQuietSince >= 1000;
}"""


_POLL_GOOGLE_PAGES = ContextVar("poll_google_pages", default=None)
_UNSAFE_POLL_PAGE = """() => window.__insoRefreshPending === true ||
    [...document.querySelectorAll('[role="dialog"]')].some(e => e.getClientRects().length) ||
    document.body.innerText.includes('正在运行脚本') ||
    (() => { const label = document.querySelector('#docs-save-indicator-badge')?.getAttribute('aria-label');
        return !!label && label !== '文档状态：已保存到云端硬盘。'; })()"""


@contextmanager
def google_operation_scope():
    """Retain only this thread's owned surfaces until this poll exits."""
    pages = {}
    token = _POLL_GOOGLE_PAGES.set(pages)
    try:
        yield
    finally:
        _POLL_GOOGLE_PAGES.reset(token)
        with ExitStack() as closing:
            for entry in pages.values():
                if not entry["protected"]:
                    cleanup = entry["actions"]
                    cleanup._page = entry["page"]
                    cleanup._poll_entry = None
                    cleanup._location = SimpleNamespace(url=entry["page"].url)
                    closing.callback(cleanup.close)


class GoogleQuotationUpdateActions:
    def __init__(self, *, browser_handle, location: QuotationInputLocation,
                 timeout_ms: int = 10000, readiness_timeout_ms: int = 30000,
                 result_timeout_ms: int = 30000):
        if browser_handle.owned:
            raise ValueError("quotation UI must reuse the protected shared CDP handle")
        self._handle, self._location, self._timeout = browser_handle, location, timeout_ms
        self._ready_timeout = readiness_timeout_ms
        self._result_timeout = result_timeout_ms
        self._page, self._protected = None, False
        self._script_pending = False
        self._price_refresh = False
        self._poll_entry = None

    def prepare_price_refresh(self):
        self._price_refresh = True

    def ensure_refresh_input_idle(self):
        """Recheck only our unfinished refresh pages; no durable barrier/global stop."""
        browser = self._handle.browser
        if browser is None or not browser.is_connected():
            raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE")
        expected = urlsplit(self._location.url)
        for context in browser.contexts:
            for page in tuple(context.pages):
                if page.is_closed() or page_owner(page) != "google-operation":
                    continue
                actual = urlsplit(page.url)
                if (actual.hostname, actual.path) != (expected.hostname, expected.path):
                    continue
                if not page.evaluate("() => window.__insoRefreshPending === true"):
                    continue
                recovery = GoogleQuotationUpdateActions(browser_handle=self._handle,
                    location=SimpleNamespace(url=page.url), result_timeout_ms=self._result_timeout)
                recovery._page, recovery._script_pending = page, True
                recovery._price_refresh = True
                recovery._guard()  # Authentication/CDP failures retain their existing boundaries.
                try:
                    if recovery._result_dialog().count() == 1:
                        recovery.dismiss_result()  # Confirm result dialog only, never re-click update.
                    else:
                        page.wait_for_function(_REFRESH_INPUT_IDLE, timeout=self._result_timeout)
                        recovery._guard()
                        page.evaluate("() => { window.__insoRefreshPending = false; }")
                        recovery._script_pending = False
                except Exception:  # noqa: BLE001 - occupied/uncertain input defers only this attempt
                    recovery._guard()
                    raise QuotationInputBusy("GOOGLE_QUOTATION_INPUT_BUSY") from None
                recovery.close()

    def _guard(self):
        browser = self._handle.browser
        if browser is None or not browser.is_connected():
            raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE")
        if self._page is None or self._page.is_closed():
            raise UpdateAttemptUnconfirmed("GOOGLE_OPERATION_SURFACE_UNAVAILABLE")
        parsed = urlsplit(self._page.url)
        # Text/role contract only; no automated Google login/verification bypass.
        login = parsed.hostname == "accounts.google.com" or any(
            self._page.get_by_text(text, exact=True).count() > 0
            for text in ("登录", "Sign in", "Verify it's you", "验证您的身份", "请求访问权限"))
        if login:
            self._protected = True
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_AUTHENTICATION_REQUIRED")
        if self._page.url == "about:blank":
            raise UpdateAttemptUnconfirmed("GOOGLE_OPERATION_SURFACE_UNCONFIRMED")
        expected = urlsplit(self._location.url)
        if parsed.scheme != "https" or parsed.hostname != expected.hostname or parsed.path != expected.path:
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SPREADSHEET_UNAVAILABLE")
        if parsed.fragment != expected.fragment:
            raise UpdateAttemptUnconfirmed("GOOGLE_OPERATION_SURFACE_UNCONFIRMED")

    def open_quote_input(self):
        self.ensure_refresh_input_idle()
        self.open_sheet()
        self._ready_control()  # Prove readiness/uniqueness before any input write.

    def open_sheet(self):
        """Shared Google navigation/auth/ownership boundary, without running a script."""
        if self._script_pending:
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED")
        if self._protected:
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_AUTHENTICATION_REQUIRED")
        if self._page is not None:
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_OPERATION_NOT_CLOSED")
        browser = self._handle.browser
        if browser is None or not browser.is_connected() or len(browser.contexts) != 1:
            raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE")
        pool = _POLL_GOOGLE_PAGES.get()
        target = urlsplit(self._location.url)
        key = (target.scheme, target.hostname, target.path)
        entry = pool.get(key) if pool is not None else None
        if entry is not None and not entry["protected"]:
            self._page, self._poll_entry = entry["page"], entry
            # Prove the current document/authentication BEFORE navigating away.
            expected = self._location
            self._location = SimpleNamespace(url=self._page.url)
            actual = urlsplit(self._page.url)
            try:
                self._guard()
                if (actual.scheme, actual.hostname, actual.path) != key or page_owner(self._page) != "google-operation":
                    raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SPREADSHEET_UNAVAILABLE")
                if self._page.evaluate(_UNSAFE_POLL_PAGE):
                    raise QuotationInputBusy("GOOGLE_QUOTATION_INPUT_BUSY")
            except Exception:  # noqa: BLE001 - unknown old pages get isolated, never repaired in place
                # Quarantine the old surface. A new stage gets one ordinary new
                # page, whose existing guards/retries decide whether it can run.
                entry["protected"] = True
                self._page, self._poll_entry, self._protected = None, None, False
            finally:
                self._location = expected
            if self._page is not None:
                if self._page.url != expected.url:
                    self._attempt(lambda: self._page.goto(expected.url, wait_until="domcontentloaded", timeout=self._timeout))
                self._guard()
                return self._page
        try:
            self._page = new_background_page(browser, browser.contexts[0], timeout_ms=self._timeout,
                                             owner="google-operation")
        except Exception:  # noqa: BLE001 - shared context cannot create the owned operation
            raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE") from None
        self._attempt(lambda: self._page.goto(self._location.url, wait_until="domcontentloaded", timeout=self._timeout))
        self._guard()
        from src.research.cdp_pages import mark_owned_page
        mark_owned_page(self._page, "google-operation")
        if pool is not None:
            self._poll_entry = {"page": self._page, "actions": self, "protected": False}
            pool[key] = self._poll_entry
        return self._page

    def _ready_control(self):
        self.wait_for_script_menu()
        return self._update_control()

    def wait_for_script_menu(self):
        # Real Sheets exposes the drawing shell before onOpen/menu initialization.
        # Wait for observed script readiness, not a fixed sleep or a shell-only click.
        menu = self._page.get_by_text("报价工具", exact=True)
        self._attempt(lambda: menu.wait_for(state="visible", timeout=self._ready_timeout))
        if menu.count() != 1:
            raise UpdateAttemptUnconfirmed("UPDATE_CONTROL_UNCONFIRMED")
        self._guard()

    def _result_dialog(self):
        # Live dialog has an observed title in its body; accessible name can be absent.
        return self._page.get_by_role("dialog").filter(
            has_text=re.compile(r"^(?:报价更新完成|更新完成)"))

    def _update_control(self):
        button = self._page.get_by_role("button", name="更新报价", exact=True)
        if button.count() == 1:
            return button
        if button.count() > 1:
            raise UpdateAttemptUnconfirmed("UPDATE_CONTROL_UNCONFIRMED")
        # Verified on the exact metadata-bound quote-input sheet, 2026-10-07:
        # two DOM overlays, only one visible; Owner screenshot identifies it.
        drawing = self._page.locator(
            'div.waffle-borderless-embedded-object-overlay[aria-label="绘图："]:visible'
        )
        if drawing.count() == 0:
            self._attempt(lambda: drawing.wait_for(state="visible", timeout=self._timeout))
        if drawing.count() != 1:
            raise UpdateAttemptUnconfirmed("UPDATE_CONTROL_UNCONFIRMED")
        return drawing

    def click_update_quote(self):
        if self._script_pending:
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED")
        self._guard()
        button = self._ready_control()
        # Stale result dialogs cannot be mistaken for this attempt's result.
        if self._result_dialog().count():
            raise UpdateAttemptUnconfirmed("UPDATE_RESULT_STALE")
        if self._price_refresh:
            # Arm before native dispatch; a click timeout may mean it DID execute.
            button.evaluate(_SCRIPT_SETTLEMENT_LATCH, timeout=self._timeout)
            self._page.evaluate("() => { window.__insoRefreshPending = true; }")
            self._script_pending = True
            try:
                button.click(timeout=self._timeout)
            except Exception:  # noqa: BLE001 - do not retry a possibly delivered refresh click
                raise UpdateClickUnconfirmed("UPDATE_RESULT_UNCONFIRMED") from None
        else:
            self._attempt(lambda: button.click(timeout=self._timeout))

    def read_update_result(self):
        self._guard()
        dialog = self._result_dialog()
        self._attempt(lambda: dialog.wait_for(state="visible", timeout=self._result_timeout))
        if dialog.count() != 1:
            raise UpdateAttemptUnconfirmed("UPDATE_RESULT_UNCONFIRMED")
        return self._attempt(lambda: dialog.inner_text(timeout=self._timeout))

    def dismiss_result(self):
        self._guard()
        dialog = self._result_dialog()
        if dialog.count() != 1:
            raise UpdateAttemptUnconfirmed("UPDATE_RESULT_UNCONFIRMED")
        button = dialog.get_by_role("button", name="确定", exact=True)
        if button.count() != 1:
            raise UpdateAttemptUnconfirmed("UPDATE_DISMISS_UNCONFIRMED")
        # Script clears input after UI confirmation. Do not write the next row until
        # this observed execution ends; never clear the shared input ourselves.
        self._script_pending = True
        try:
            button.evaluate(_SCRIPT_SETTLEMENT_LATCH, timeout=self._timeout)
            button.click(timeout=self._timeout)
            self._page.wait_for_function(
                "() => window.__insoQuoteSettlement?.confirmed && window.__insoQuoteSettlement.started",
                timeout=self._result_timeout)
            self._page.wait_for_function(
                "() => window.__insoQuoteSettlement?.started && window.__insoQuoteSettlement.settled",
                timeout=self._result_timeout)
            self._guard()
            self._page.evaluate("() => window.__insoQuoteSettlement.observer.disconnect()")
        except Exception:  # noqa: BLE001 - any settlement uncertainty preserves the operation page
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED") from None
        if self._price_refresh:
            self._page.evaluate("() => { window.__insoRefreshPending = false; }")
        self._script_pending = False

    def _attempt(self, operation):
        try:
            return operation()
        except V12Fault:
            raise
        except Exception:  # noqa: BLE001 - diagnose shared/auth failure before safe UI retry
            self._guard()
            raise UpdateAttemptUnconfirmed("UPDATE_RESULT_UNCONFIRMED") from None

    def retire_failed_page(self):
        """Never pass a failed phase's page to another phase/retry."""
        if self._poll_entry is None:
            return
        self._poll_entry["protected"] = True
        self._poll_entry = None
        try:
            # Ordinary read failures can be closed; unresolved work stays visible.
            self._protected |= bool(self._page.evaluate(_UNSAFE_POLL_PAGE))
        except Exception:  # noqa: BLE001 - uncertain old surface is retained
            self._protected = True

    def close(self):
        if self._poll_entry is not None:
            entry, self._poll_entry = self._poll_entry, None
            entry["protected"] |= self._protected or self._script_pending
            if not entry["protected"] and self._page is not None and not self._page.is_closed():
                expected = self._location
                actual = urlsplit(self._page.url)
                target = urlsplit(expected.url)
                try:
                    # Other nested calls may legitimately have selected another gid.
                    # Authentication/document ownership and settlement must still hold.
                    self._location = SimpleNamespace(url=self._page.url)
                    self._guard()
                    entry["protected"] |= (
                        (actual.scheme, actual.hostname, actual.path) !=
                        (target.scheme, target.hostname, target.path)
                        or page_owner(self._page) != "google-operation"
                        or bool(self._page.evaluate(_UNSAFE_POLL_PAGE)))
                except Exception:  # noqa: BLE001 - unknown surfaces are quarantined, never reused
                    entry["protected"] = True
                finally:
                    self._location = expected
            entry["actions"] = self
            self._page = None
            return
        if self._price_refresh and self._script_pending:
            # The browser-visible marker, not this disposable controller, owns
            # recovery. Preserve the tab and allow a later attempt to re-check it.
            self._page, self._script_pending, self._price_refresh = None, False, False
            return
        if self._protected or self._script_pending or self._page is None:
            return
        try:
            self._guard()
        except V12Fault:
            if self._protected:
                return
        except UpdateAttemptUnconfirmed:
            pass
        try:
            # Keep the protected browser alive if this has become its last tab.
            context = self._page.context
            if not any(page is not self._page and not page.is_closed() for page in context.pages):
                blank = new_background_page(self._handle.browser, context, timeout_ms=self._timeout)
                if blank is self._page or blank.is_closed() or blank.url != "about:blank":
                    raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_OPERATION_NOT_CLOSED")
            self._page.close()
            if not self._page.is_closed():
                raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_OPERATION_NOT_CLOSED")
        except Exception:  # noqa: BLE001 - inability to end the owned surface is shared safety failure
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_OPERATION_NOT_CLOSED") from None
        self._page = None
        self._price_refresh = False


def build_v13_quotation_updater(*, service, source_reader, store, browser_handle,
                                location: QuotationInputLocation, wait, stop_requested=lambda: False,
                                notify_model_difference=lambda _r, _m: None,
                                price_store=None, currency_rate=None,
                                notify_refresh_uncertain=lambda _r, _old, _new: None):
    """Domain input contract supplied by the canonical Google web transport.

    RFQ-006 owns production scheduling/wiring. This factory performs no I/O.
    """
    return V13QuotationUpdater(
        source=WorkflowQuotationSource(reader=source_reader, store=store),
        quotation_input=GoogleQuotationInput(service, location, expected_columns=QUOTATION_COLUMNS),
        actions=GoogleQuotationUpdateActions(browser_handle=browser_handle, location=location),
        wait=wait, stop_requested=stop_requested,
        notify_model_difference=notify_model_difference,
        price_store=price_store, currency_rate=currency_rate,
        notify_refresh_uncertain=notify_refresh_uncertain,
    )
