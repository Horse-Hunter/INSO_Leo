"""Narrow Google quotation UI role/text contract on the existing protected CDP.

Named button or Owner-verified sole visible drawing. Configured geometry/gid is mandatory;
this module never discovers credentials, launches a browser, or calls Script URLs.
"""
import re
from urllib.parse import urlsplit

from src.inso.quotation_read import QUOTATION_COLUMNS
from src.sheets.quotation_input import GoogleQuotationInput, QuotationInputLocation
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_quote_update import (
    UpdateAttemptUnconfirmed,
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
    latch.observer = new MutationObserver(sample);
    latch.observer.observe(document.body, {
        subtree: true, childList: true, characterData: true, attributes: true
    });
    button.addEventListener('click', () => { latch.confirmed = true; sample(); },
        {capture: true, once: true});
    window.__insoQuoteSettlement = latch;
}"""


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
        if self._script_pending:
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED")
        if self._protected:
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_AUTHENTICATION_REQUIRED")
        if self._page is not None:
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_OPERATION_NOT_CLOSED")
        browser = self._handle.browser
        if browser is None or not browser.is_connected() or len(browser.contexts) != 1:
            raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE")
        try:
            self._page = browser.contexts[0].new_page()
        except Exception:  # noqa: BLE001 - shared context cannot create the owned operation
            raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE") from None
        self._attempt(lambda: self._page.goto(self._location.url, wait_until="domcontentloaded", timeout=self._timeout))
        self._guard()
        self._ready_control()  # Prove readiness/uniqueness before any input write.

    def _ready_control(self):
        # Real Sheets exposes the drawing shell before onOpen/menu initialization.
        # Wait for observed script readiness, not a fixed sleep or a shell-only click.
        menu = self._page.get_by_text("报价工具", exact=True)
        self._attempt(lambda: menu.wait_for(state="visible", timeout=self._ready_timeout))
        if menu.count() != 1:
            raise UpdateAttemptUnconfirmed("UPDATE_CONTROL_UNCONFIRMED")
        self._guard()
        return self._update_control()

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
        self._script_pending = False

    def _attempt(self, operation):
        try:
            return operation()
        except V12Fault:
            raise
        except Exception:  # noqa: BLE001 - diagnose shared/auth failure before safe UI retry
            self._guard()
            raise UpdateAttemptUnconfirmed("UPDATE_RESULT_UNCONFIRMED") from None

    def close(self):
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
                blank = context.new_page()
                if blank is self._page or blank.is_closed() or blank.url != "about:blank":
                    raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_OPERATION_NOT_CLOSED")
            self._page.close()
            if not self._page.is_closed():
                raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_OPERATION_NOT_CLOSED")
        except Exception:  # noqa: BLE001 - inability to end the owned surface is shared safety failure
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_OPERATION_NOT_CLOSED") from None
        self._page = None


def build_v13_quotation_updater(*, service, source_reader, store, browser_handle,
                                location: QuotationInputLocation, wait, stop_requested=lambda: False):
    """Service supplied by existing cached write-grant/OAuth builder, never replaced.

    RFQ-006 owns production scheduling/wiring. This factory performs no I/O.
    """
    return V13QuotationUpdater(
        source=WorkflowQuotationSource(reader=source_reader, store=store),
        quotation_input=GoogleQuotationInput(service, location, expected_columns=QUOTATION_COLUMNS),
        actions=GoogleQuotationUpdateActions(browser_handle=browser_handle, location=location),
        wait=wait, stop_requested=stop_requested,
    )
