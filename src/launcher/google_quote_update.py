"""Narrow Google quotation UI role/text contract on the existing protected CDP.

Named button or Owner-verified sole visible drawing. Configured geometry/gid is mandatory;
this module never discovers credentials, launches a browser, or calls Script URLs.
"""
import re
import threading
from contextlib import ExitStack, contextmanager, nullcontext
from contextvars import ContextVar
from types import SimpleNamespace
from urllib.parse import parse_qsl, urlsplit

from src.inso.quotation_read import QUOTATION_COLUMNS
from src.research.cdp_pages import (
    DocumentWriteBusy,
    DocumentWriteHeld,
    PageResourceAdmission,
    PageTargetOwnershipError,
    bounded_browser_call,
    google_document_key,
    native_page_owner,
    new_background_page,
    page_owner,
)
from src.sheets.quotation_input import (
    GoogleQuotationInput,
    QuotationInputBusy,
    QuotationInputLocation,
)
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_quote_update import (
    UpdateAttemptUnconfirmed,
    UpdateClickUnconfirmed,
    UpdateResultTimeout,
    V13QuotationUpdater,
    WorkflowQuotationSource,
)

from .diagnostics import log_step

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
    if (!window.__insoQuoteSettlement) return false;
    const busy = [...document.querySelectorAll('[role="dialog"]')].some(visible) ||
        window.__insoQuoteSettlement?.isRunning() ||
        (window.__insoQuoteSettlement?.initial && !window.__insoQuoteSettlement.settled);
    if (busy) { window.__insoRefreshQuietSince = null; return false; }
    window.__insoRefreshQuietSince ??= performance.now();
    return performance.now() - window.__insoRefreshQuietSince >= 1000;
}"""


_POLL_GOOGLE_PAGES = ContextVar("poll_google_pages", default=None)
_ACTIVE_QUOTE_TARGETS = {}
_ACTIVE_QUOTE_LOCK = threading.Lock()
_UNSAFE_POLL_PAGE = """() => window.__insoRefreshPending === true ||
    [...document.querySelectorAll('[role="dialog"]')].some(e => e.getClientRects().length &&
        getComputedStyle(e).visibility !== 'hidden' && getComputedStyle(e).display !== 'none') ||
    document.body.innerText.includes('正在运行脚本') ||
    (() => { const label = document.querySelector('#docs-save-indicator-badge')?.getAttribute('aria-label');
        return !!label && label !== '文档状态：已保存到云端硬盘。'; })()"""


@contextmanager
def google_operation_scope(*, retained=None, lock=None):
    """Borrow current-client pages; optional retained registry holds IDs only."""
    pages = {}
    token = _POLL_GOOGLE_PAGES.set((pages, retained))
    try:
        yield
    finally:
        _POLL_GOOGLE_PAGES.reset(token)
        with (lock if lock is not None else nullcontext()), ExitStack() as closing:
            for key, entry in pages.items():
                if retained is not None:
                    if entry["page"].is_closed():
                        previous = retained.get(key)
                        mismatch = previous is not None and previous[0] != entry.get("target_id")
                        pure_read = (len(key) == 4 and previous is not None and not mismatch
                                     and len(previous) >= 4 and previous[3] is True
                                     and entry.get("read_only") is True
                                     and not entry["actions"]._script_pending)
                        if mismatch or (entry["protected"] and not entry.get("reopenable", False)
                                        and not pure_read):
                            if previous is not None:
                                retained[key] = (previous[0], True, False, False)
                        else:
                            retained.pop(key, None)
                        continue
                    cleanup = entry["actions"]
                    cleanup._page, cleanup._poll_entry = entry["page"], entry
                    cleanup.close()  # Recheck settlement; never close retained tabs.
                    _retain_google_entry(key, entry, retained)
                    continue
                if not entry["protected"]:
                    cleanup = entry["actions"]
                    cleanup._page = entry["page"]
                    cleanup._poll_entry = entry
                    cleanup.close()  # Recheck changes since this slot was last borrowed.
                    if entry["protected"]:
                        continue
                    cleanup._page = entry["page"]
                    cleanup._poll_entry = None
                    cleanup._location = SimpleNamespace(url=entry["page"].url)
                    closing.callback(cleanup.close)


def google_operations_idle():
    """Re-prove existing retained surfaces at a same-Owner lending boundary.

    Does not create/close a managed page or change admission/settlement policy.
    Existing close rechecks unsafe DOM; a quarantined surface never certifies idle.
    """
    scope = _POLL_GOOGLE_PAGES.get()
    if scope is None or scope[1] is None:
        return False
    pages, retained = scope
    if any(value[1] for key, value in retained.items()
           if not (len(key) >= 5 and key[4] == "quarantine" and len(value) >= 4 and value[3])):
        return False
    for key, entry in tuple(pages.items()):
        if len(key) >= 5 and key[4] == "quarantine" and entry.get("read_only") is True:
            continue
        page, actions = entry['page'], entry['actions']
        if entry['protected'] or page.is_closed():
            return False
        expected = retained.get(key)
        actions._page, actions._poll_entry = page, entry
        try:
            actions._guard()  # Authentication failure propagates, not idle=False.
            if (expected is None or _google_target_id(page) != expected[0]
                    or page_owner(page) != 'google-operation'):
                raise PageTargetOwnershipError((ValueError('GOOGLE_TAB_IDENTITY_UNCONFIRMED'),))
        finally:
            actions.close()  # Canonical ownership/unsafe-DOM guard, retain four pages.
        if entry['protected']:
            return False
    return True


class GoogleReadTargetUnavailable(TimeoutError):
    """No read/write may proceed; retry the original read on its next attempt."""


def _google_target_id(page):
    """Prove native identity; factory leases use explicit browser target queries.

    The factory already binds this exact Page to a native target. Re-attaching
    another per-page CDP session is unnecessary and can race a document/process
    transition. Browser-scoped Target.getTargetInfo with that exact ID keeps
    proof independent of the transient page session; document/owner/write
    settlement guards remain mandatory at their original callers.
    """
    session = None
    step = "google-target-session"
    attaching, proving = None, False
    try:
        if page.is_closed():
            raise ValueError("GOOGLE_TARGET_CLOSED")
        lease = getattr(page, "_inso_native_page_owner", None)
        if lease is not None:
            expected, _owner, context, browser = lease
            if context is not page.context or not isinstance(expected, str) or not expected:
                raise ValueError("GOOGLE_NATIVE_LEASE_INVALID")
            attaching = "native"
            session = bounded_browser_call(browser, "new_browser_cdp_session")
            attaching = None
            step = "google-target-explicit-proof"
            proving = True
            response = bounded_browser_call(session, "send", "Target.getTargetInfo", {"targetId": expected})
            proving = False
            info = response["targetInfo"]
            target = info["targetId"]
            if target != expected or info.get("type") != "page":
                raise ValueError("GOOGLE_NATIVE_TARGET_MISMATCH")
        else:
            attaching = "page"
            session = bounded_browser_call(page.context, "new_cdp_session", page)
            attaching = None
            step = "google-target-page-proof"
            proving = True
            response = bounded_browser_call(session, "send", "Target.getTargetInfo")
            proving = False
            target = response["targetInfo"]["targetId"]
        if not isinstance(target, str) or not target:
            raise ValueError("MISSING_TARGET_ID")
        return target
    except Exception as exc:
        log_step(step, cause=exc)
        failure = V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED")
        failure._google_probe_attach_failed = attaching == "page" and session is None
        failure._google_native_transport_failed = attaching == "native" or proving
        raise failure from exc
    finally:
        if session is not None:
            try:
                bounded_browser_call(session, "detach")
            except Exception as exc:
                log_step("google-target-proof-detach", cause=exc)
                raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED") from exc



def _retained_google_matches(pages, target_id, *, read_only=False):
    """Require positive exact proof; an unrelated failed probe is not our fault.

    Reattached clients enumerate Owner/manual/extension pages as well as ours.
    Never adopt an unproved page or interpret a failed probe as disappearance.
    """
    matches, failure = [], None
    for page in pages:
        if page.is_closed():
            continue
        try:
            actual = _google_target_id(page)
        except V12Fault as error:
            # Detach/cleanup failures remain globally unsafe even if another
            # target can be proved. Only a failed attachment to an unleased
            # candidate may be irrelevant to the positively identified page.
            foreign_attach = (getattr(page, "_inso_native_page_owner", None) is None
                              and getattr(error, "_google_probe_attach_failed", False) is True)
            read_transport = read_only and getattr(error, "_google_native_transport_failed", False) is True
            if error.reason != "GOOGLE_TAB_IDENTITY_UNCONFIRMED" or not (foreign_attach or read_transport):
                raise
            failure = error
            continue
        if actual == target_id:
            matches.append(page)
    if failure is not None and not matches:
        if read_only:
            raise GoogleReadTargetUnavailable("GOOGLE_READ_TARGET_UNAVAILABLE")
        raise failure  # Missing target cannot be inferred from an unreadable page.
    return matches


def _retain_google_entry(key, entry, retained):
    read_unavailable = False
    try:
        target_id = _google_target_id(entry["page"])
    except V12Fault as error:
        if (not entry.get("read_only") or (entry["protected"] and not entry.get("reopenable", False))
                or not getattr(error, "_google_native_transport_failed", False)):
            raise
        read_unavailable = True
    if read_unavailable:
        # Factory leases were positively bound at creation. Retain only that
        # identity for a later fresh proof, not permission to use this Page.
        lease = getattr(entry["page"], "_inso_native_page_owner", None)
        if key not in retained and lease is not None:
            retained[key] = (lease[0], False, False, False)
        raise GoogleReadTargetUnavailable("GOOGLE_READ_TARGET_UNAVAILABLE")
    previous = retained.get(key)
    if previous and previous[0] != target_id:
        # Preserve the old target as a hard hold before reporting mismatch.
        retained[key] = (previous[0], True, False, False)
        raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED")
    entry["target_id"] = target_id
    protected = entry["protected"] or bool(previous and previous[0] == target_id and previous[1])
    # Missing or mismatched history cannot establish that this target was only read.
    prior_read_only = (previous is None or previous[0] != target_id
                       or len(previous) >= 4 and previous[3] is True)
    read_only = entry.get("read_only") is True and prior_read_only
    prior_hard_hold = bool(previous and previous[0] == target_id and previous[1] and not previous[2])
    reopenable = entry.get("reopenable", False) and read_only and not prior_hard_hold
    record = (target_id, protected, reopenable, read_only)
    if entry.get("recoverable_read") is True and read_only and protected:
        record += (True, entry.get("failed_url"))
    retained[key] = record


def _same_read_sheet_selection(actual, expected):
    """Only a valid cell selection may vary; never a document or worksheet ID."""
    def parts(fragment):
        try:
            pairs = parse_qsl(fragment, keep_blank_values=True, strict_parsing=True)
        except ValueError:
            return None
        values = dict(pairs)
        if len(values) != len(pairs) or set(values) not in ({"gid"}, {"gid", "range"}):
            return None
        if not re.fullmatch(r"[0-9]+", values.get("gid", "")):
            return None
        if "range" in values and not re.fullmatch(
                r"\$?[A-Za-z]{1,3}\$?[1-9][0-9]{0,6}(?::\$?[A-Za-z]{1,3}\$?[1-9][0-9]{0,6})?",
                values["range"]):
            return None
        return values["gid"]
    gid = parts(expected)
    return gid is not None and parts(actual) == gid


class GoogleQuotationUpdateActions:
    def __init__(self, *, browser_handle, location: QuotationInputLocation,
                 timeout_ms: int = 10000, readiness_timeout_ms: int = 30000,
                 result_timeout_ms: int = 30000, popup_timeout_ms: int = 60000,
                 page_role="google-operation"):
        if page_role not in {"google-operation", "google-mail-read"}:
            raise ValueError("GOOGLE_PAGE_ROLE_INVALID")
        self._page_role = page_role
        if browser_handle.owned:
            raise ValueError("quotation UI must reuse the protected shared CDP handle")
        self._handle, self._location, self._timeout = browser_handle, location, timeout_ms
        self._ready_timeout = readiness_timeout_ms
        self._result_timeout = result_timeout_ms
        self._popup_timeout = popup_timeout_ms
        self._page, self._protected = None, False
        self._script_pending = False
        self._price_refresh = False
        self._poll_entry = None
        self._read_only = False
        self._active_quote_target = None
        self._document_write_owner = None

    def _document_key(self):
        return google_document_key(self._location.url)

    def _shared_admission(self):
        browser = getattr(self._handle, "browser", None)
        admission = getattr(browser, "_inso_page_admission", None)
        return admission if isinstance(admission, PageResourceAdmission) else None

    def _require_write_admission(self):
        """Every write surface must share the runtime's page admission."""
        if self._read_only:
            return None
        admission = self._shared_admission()
        if admission is None:
            # A write path with no shared admission cannot prove that another
            # client/effect is not already unresolved; fail before page creation.
            raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_PAGE_ADMISSION_UNCONFIRMED")
        admission.require_open()
        document = self._document_key()
        try:
            admission.require_document_writable(document)
        except DocumentWriteHeld as exc:
            raise QuotationInputBusy("GOOGLE_QUOTATION_INPUT_BUSY") from exc
        return admission

    def _hold_document(self, reason):
        """Publish an unresolved write on the one shared admission root."""
        admission = self._shared_admission()
        if admission is None:
            return
        try:
            document = self._document_key()
        except ValueError:
            return
        admission.hold_document(document, self, reason, page=self._page)
        if self._page is not None:
            self._page._inso_document_hold_owner = self
            self._page._inso_document_hold_protected = (
                bool(getattr(self._page, "_inso_document_hold_protected", False))
                or self._protected)
            if self._protected:
                self._page._inso_protected_surface = True

    def _release_page_document_hold(self, page=None, *, allow_closed=False):
        """Release only the owner recorded on this exact page after settlement.

        ``allow_closed`` is used only by the successful settlement+close path,
        where the page is already gone and ownership was proved immediately
        before close. Page closure alone never calls this method.
        """
        admission = self._shared_admission()
        page = page if page is not None else self._page
        owner = getattr(page, "_inso_document_hold_owner", None)
        if admission is None or owner is None:
            return
        if (getattr(page, "_inso_document_hold_protected", False) is True
                or getattr(page, "_inso_protected_surface", False) is True):
            # Protected identity/auth/ownership uncertainty is never released
            # by an ordinary refresh-settlement probe.
            return
        try:
            owned = page_owner(page) == self._page_role
        except Exception:  # noqa: BLE001 - unprovable ownership cannot release
            owned = False
        if not owned and not (allow_closed and page.is_closed()):
            # A page adopted/moved to another owner is never treated as this
            # controller's settled surface.
            return
        try:
            document = self._document_key()
        except ValueError:
            return
        admission.release_document(document, owner)
        page._inso_document_hold_owner = None

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
                actual = urlsplit(page.url)
                if page.is_closed() or (actual.hostname, actual.path) != (expected.hostname, expected.path):
                    continue
                lease = getattr(page, "_inso_native_page_owner", None)
                owner = page_owner(page)
                if owner != self._page_role:
                    if lease is not None and native_page_owner(page) == self._page_role:
                        raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED")
                    continue
                if not bounded_browser_call(page, "evaluate", "() => window.__insoRefreshPending === true"):
                    continue
                if getattr(page, "_inso_active_quote_action", None) is not None:
                    raise QuotationInputBusy("GOOGLE_QUOTATION_INPUT_BUSY")
                def require_owner(page=page):
                    if (getattr(page, "_inso_native_page_owner", None) is None
                            or native_page_owner(page) != self._page_role or page_owner(page) != self._page_role):
                        raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED")
                require_owner()
                if getattr(page, "_inso_protected_surface", False) is True:
                    # An explicitly protected/uncertain surface is never
                    # settled by an ordinary refresh probe.
                    raise QuotationInputBusy("GOOGLE_QUOTATION_INPUT_BUSY")
                if not bounded_browser_call(page, "evaluate", "() => !!window.__insoQuoteSettlement"):
                    raise QuotationInputBusy("GOOGLE_QUOTATION_INPUT_BUSY")
                recovery = GoogleQuotationUpdateActions(browser_handle=self._handle,
                    location=SimpleNamespace(url=page.url), result_timeout_ms=self._result_timeout, page_role=self._page_role)
                recovery._page, recovery._script_pending = page, True
                recovery._price_refresh = True
                recovery._guard()  # Authentication/CDP failures retain their existing boundaries.
                try:
                    if bounded_browser_call(recovery._result_dialog(), "count") == 1:
                        require_owner()
                        recovery.dismiss_result()  # Confirm result dialog only, never re-click update.
                    else:
                        bounded_browser_call(page, "wait_for_function", _REFRESH_INPUT_IDLE, timeout=self._result_timeout, timeout_ms=(self._result_timeout)+1000)
                        recovery._guard()
                        require_owner()
                        bounded_browser_call(page, "evaluate", "() => { window.__insoRefreshPending = false; }")
                        recovery._script_pending = False
                        # The hold is released only by the subsequent
                        # recovery.close() proving this exact page closed, or
                        # by an explicit protected-page resolution. Releasing
                        # here would precede the close-time Owner-adoption
                        # check and could bypass it.
                except V12Fault:
                    raise  # Shared identity or settlement uncertainty is never a local busy read.
                except Exception:  # noqa: BLE001 - unknown local wait remains protected
                    recovery._guard()
                    log_step("google-busy-refresh-uncertain")
                    raise QuotationInputBusy("GOOGLE_QUOTATION_INPUT_BUSY") from None
                require_owner()
                recovery.close()
                if page.is_closed():
                    # Only the successful settlement + close path above may
                    # release the owner's page-level hold.
                    recovery._release_page_document_hold(page, allow_closed=True)
                else:
                    require_owner()  # The Owner may have adopted the page during close.

    def _require_owned_page(self):
        try:
            owned = (self._page is not None and native_page_owner(self._page) == self._page_role
                     and page_owner(self._page) == self._page_role)
        except BaseException:
            self._protected = True
            raise
        if not owned:
            self._protected = True
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED")

    def _guard(self, *, read_selection=False):
        browser = self._handle.browser
        if browser is None or not browser.is_connected():
            raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE")
        if self._page is None or self._page.is_closed():
            raise UpdateAttemptUnconfirmed("GOOGLE_OPERATION_SURFACE_UNAVAILABLE")
        parsed = urlsplit(self._page.url)
        # Text/role contract only; no automated Google login/verification bypass.
        login = parsed.hostname == "accounts.google.com"
        for text in ("登录", "Sign in", "Verify it's you", "验证您的身份", "请求访问权限"):
            markers = self._page.get_by_text(text, exact=True)
            login |= any(bounded_browser_call(markers.nth(i), "is_visible")
                         for i in range(bounded_browser_call(markers, "count")))
        if login:
            self._protected = True
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_AUTHENTICATION_REQUIRED")
        if self._page.url == "about:blank":
            raise UpdateAttemptUnconfirmed("GOOGLE_OPERATION_SURFACE_UNCONFIRMED")
        expected = urlsplit(self._location.url)
        if parsed.scheme != "https" or parsed.hostname != expected.hostname or parsed.path != expected.path:
            error_page = self._page.url == "chrome-error://chromewebdata/"
            step = ("google-navigation-error-page" if error_page
                    else "google-document-host-mismatch" if parsed.scheme != "https" or parsed.hostname != expected.hostname
                    else "google-document-path-mismatch")
            log_step(step)
            if error_page and self._read_only and not self._protected:
                # Chrome's own error page has no document to prove and no Owner
                # state to preserve; only this owned pure-read attempt failed.
                # A write, an uncertain ownership or a protected surface keeps
                # the established global stop below.
                raise GoogleReadTargetUnavailable("GOOGLE_READ_TARGET_UNAVAILABLE")
            reason = ("GOOGLE_SPREADSHEET_UNAVAILABLE" if error_page
                      else "GOOGLE_TAB_IDENTITY_UNCONFIRMED")
            raise V12Fault(FaultScope.GLOBAL_STOP, reason)
        if parsed.fragment != expected.fragment and not (
                read_selection and _same_read_sheet_selection(parsed.fragment, expected.fragment)):
            log_step("google-read-fragment-drift" if read_selection
                     else "google-write-fragment-drift")
            raise UpdateAttemptUnconfirmed("GOOGLE_OPERATION_SURFACE_UNCONFIRMED")

    def open_quote_input(self):
        self.ensure_refresh_input_idle()
        self.open_sheet()
        self._ready_control()

    def refresh_after_external_write(self):
        """Reload this owned input page so the bound script sees an API-written row.

        Only the container-bound script (and its menu) still needs the browser;
        when the input row was written through the Sheets API the page's client
        model is stale. Reloading the exact already-proved URL keeps the same
        document/gid, and re-proves ownership before and after the reload. No
        cell value is compared here: the cancelled 14-cell readback stays gone.
        """
        self._require_write_admission()
        if self._script_pending:
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED")
        self._guard()
        if self._page is None or self._page.is_closed():
            raise UpdateAttemptUnconfirmed("GOOGLE_OPERATION_SURFACE_UNAVAILABLE")
        self._attempt(lambda: bounded_browser_call(
            self._page, "reload", wait_until="domcontentloaded",
            timeout=self._timeout, timeout_ms=(self._timeout) + 1000))
        self._guard()
        self._require_owned_page()
        self.wait_for_script_menu()

    def open_sheet(self, *, select_worksheet=False, worksheet="报价输入"):
        return self._open_sheet(select_worksheet=select_worksheet, worksheet=worksheet)

    def _open_sheet(self, *, select_worksheet=False, worksheet="报价输入"):
        if self._script_pending:
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED")
        if self._protected:
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_AUTHENTICATION_REQUIRED")
        self._require_write_admission()
        if self._page is not None:
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_OPERATION_NOT_CLOSED")
        browser = self._handle.browser
        if browser is None or not browser.is_connected() or len(browser.contexts) != 1:
            raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE")
        if not self._read_only:
            target = urlsplit(self._location.url)
            for existing in tuple(browser.contexts[0].pages):
                actual = urlsplit(existing.url)
                if (existing.is_closed() or (actual.scheme, actual.hostname, actual.path) !=
                        (target.scheme, target.hostname, target.path)):
                    continue
                if getattr(existing, "_inso_active_quote_action", None) is not None:
                    raise QuotationInputBusy("GOOGLE_QUOTATION_INPUT_BUSY")
                try:
                    pending = bounded_browser_call(existing, "evaluate", "() => window.__insoRefreshPending === true")
                except Exception:  # noqa: BLE001 - optional probe cannot classify unrelated read failure
                    with _ACTIVE_QUOTE_LOCK:
                        active_same_document = any(
                            (urlsplit(action._location.url).scheme, urlsplit(action._location.url).hostname,
                             urlsplit(action._location.url).path) == (target.scheme, target.hostname, target.path)
                            for action in _ACTIVE_QUOTE_TARGETS.values())
                    if active_same_document:
                        raise QuotationInputBusy("GOOGLE_QUOTATION_INPUT_BUSY") from None
                    log_step("google-optional-refresh-probe")
                    continue
                if pending:
                    try:
                        native_target = _google_target_id(existing)
                    except V12Fault:
                        native_target = None
                    with _ACTIVE_QUOTE_LOCK:
                        active = native_target is not None and native_target in _ACTIVE_QUOTE_TARGETS
                        if native_target is None:
                            active = any(
                                (urlsplit(action._location.url).scheme, urlsplit(action._location.url).hostname,
                                 urlsplit(action._location.url).path) == (target.scheme, target.hostname, target.path)
                                for action in _ACTIVE_QUOTE_TARGETS.values())
                    if active:
                        raise QuotationInputBusy("GOOGLE_QUOTATION_INPUT_BUSY")
                    if getattr(existing, "_inso_native_page_owner", None) is None:
                        # A pending script survived the client that started it.
                        # Do not replay it or adopt its page without ownership proof.
                        raise QuotationInputBusy("GOOGLE_QUOTATION_INPUT_BUSY")
                    self.ensure_refresh_input_idle()
                    break
        # A document marker alone cannot carry permission across clients. Only
        # this scope's exact, safely retired read entry is eligible for cleanup.
        scope = _POLL_GOOGLE_PAGES.get()
        pool, retained = scope if scope is not None else (None, None)
        if retained is not None:
            for old_key, record in tuple(retained.items()):
                if not (len(old_key) >= 5 and old_key[4] == "quarantine"
                        and len(record) >= 4 and record[3] is True):
                    continue
                try:
                    matches = _retained_google_matches(browser.contexts[0].pages, record[0], read_only=True)
                except (GoogleReadTargetUnavailable, V12Fault):
                    continue  # Optional cleanup never turns an uncertain probe into a stop.
                if not matches:
                    retained.pop(old_key, None)
        expected_document = urlsplit(self._location.url)
        for old in tuple(browser.contexts[0].pages):
            actual = urlsplit(old.url)
            if old.is_closed() or ((actual.scheme, actual.hostname, actual.path) != (
                    expected_document.scheme, expected_document.hostname, expected_document.path
            ) and actual.hostname != "accounts.google.com"):
                continue  # Do not evaluate unrelated manual/INSO/other-document pages.
            # A stale document marker or native lease cannot override a
            # protected entry or prove the Owner did not move to another tab.
            if (actual.hostname == "accounts.google.com"
                    and getattr(old, "_inso_native_page_owner", None) is not None
                    and native_page_owner(old) == self._page_role and page_owner(old) == self._page_role):
                # Preserve the owned login surface and avoid opening a new tab
                # on each poll; inspection does not transfer ownership.
                recovery = GoogleQuotationUpdateActions(browser_handle=self._handle,
                    location=SimpleNamespace(url=old.url), page_role=self._page_role)
                recovery._page = old
                recovery._guard()
            entries = [(key, entry) for key, entry in (pool or {}).items()
                       if entry.get("page") is old and entry.get("read_only") is True
                       and entry.get("reopenable") is True
                       and entry.get("failed_url") == old.url]
            if len(entries) != 1 or getattr(old, "_inso_native_page_owner", None) is None:
                continue
            key, entry = entries[0]
            if native_page_owner(old) != self._page_role or page_owner(old) != self._page_role:
                continue
            native = _google_target_id(old)
            prior = retained.get(key) if retained is not None else None
            if retained is not None and (prior is None or prior[0] != native or prior[1] and not prior[2]):
                continue
            if not bounded_browser_call(old, "evaluate", "() => window.__insoGoogleReadFailed === true"):
                continue
            recovery = GoogleQuotationUpdateActions(browser_handle=self._handle,
                location=SimpleNamespace(url=old.url), page_role=self._page_role)
            recovery._page = old
            recovery._guard()
            if not bounded_browser_call(old, "evaluate", _UNSAFE_POLL_PAGE):
                recovery.close()
        target = urlsplit(self._location.url)
        document_key = (target.scheme, target.hostname, target.path)
        if worksheet not in {"2026", "SHAHAB", "RFQ_BRIEF", "报价输入"}:
            raise ValueError("GOOGLE_SHEET_UNCONFIRMED")
        key = (*document_key, worksheet)
        quarantine_key = (*key, "quarantine")
        entry = pool.get(key) if pool is not None else None
        if entry is None and retained is not None and key in retained:
            retained_entry = retained[key]
            target_id, protected, reopenable = retained_entry[:3]
            retained_read_only = len(retained_entry) >= 4 and retained_entry[3] is True
            matches = _retained_google_matches(browser.contexts[0].pages, target_id,
                read_only=self._read_only and not (protected and not reopenable))
            if len(matches) > 1:
                raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED")
            if matches:
                entry = {"page": matches[0], "actions": self, "protected": protected,
                         "reopenable": reopenable, "target_id": target_id,
                         "read_only": retained_read_only,
                         "recoverable_read": len(retained_entry) >= 6 and retained_entry[4] is True,
                         "failed_url": retained_entry[5] if len(retained_entry) >= 6 else None}
                pool[key] = entry
            else:
                # An exactly known target disappeared (Owner closed it). Reopen
                # only this sheet on demand; never adopt another visible page.
                if protected and not reopenable and not retained_read_only:
                    raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED")
                # Exact native target absence plus retained read-only history
                # cannot represent a program-dispatched write.
                del retained[key]
        if entry is not None and entry["page"].is_closed():
            if retained is not None and entry["protected"]:
                prior = retained.get(key)
                exact_read = (entry.get("read_only") is True and prior is not None
                              and prior[0] == entry.get("target_id") and len(prior) >= 4
                              and prior[3] is True and not entry["actions"]._script_pending)
                if not exact_read:
                    raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED")
                # The exact same known read-only page was safely retired; only
                # now can a replacement get a new registry identity.
                del retained[key]
            elif retained is not None and key in retained:
                prior = retained[key]
                if prior[0] != entry.get("target_id") or prior[1]:
                    raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED")
                del retained[key]
            del pool[key]
            entry = None
        if (entry is not None and not entry["protected"] and self._read_only
                and entry.get("read_only") is True
                and entry["page"].url == "chrome-error://chromewebdata/"
                and native_page_owner(entry["page"]) == self._page_role):
            # Preserve the failed target. A browser error page cannot prove
            # the previous document state and must never be closed or reused.
            native = _google_target_id(entry["page"])
            prior = retained.get(key) if retained is not None else None
            if retained is None or (prior is not None and prior[0] == native
                                    and len(prior) >= 4 and prior[3] is True):
                entry.update(protected=True, recoverable_read=True,
                             failed_url=entry["page"].url, error_page=True)
                if retained is not None:
                    _retain_google_entry(key, entry, retained)
        if entry is not None and entry["protected"]:
            # A busy READ must not conceal authentication/document failure.
            previous = entry["actions"]
            borrowed_page, borrowed_location = previous._page, previous._location
            try:
                previous._page = entry["page"]
                if not (entry.get("error_page") is True and self._read_only
                        and entry["page"].url == "chrome-error://chromewebdata/"):
                    failed_url = entry.get("failed_url")
                    failed = urlsplit(failed_url) if isinstance(failed_url, str) else None
                    if (entry.get("recoverable_read") is True and failed_url == entry["page"].url
                            and failed is not None
                            and (failed.scheme, failed.hostname, failed.path) == document_key):
                        previous._location = SimpleNamespace(url=failed_url)
                    previous._guard()
            finally:
                previous._location = borrowed_location
                # This is inspection only. In particular, a reattached entry
                # can use self as its inspector; never hand its protected page
                # to the caller's failure cleanup as a newly owned surface.
                previous._page = borrowed_page
            # Only a failed, provably read-only operation in this same scope
            # can use one independent recovery surface. Keep the old surface
            # quarantined; its owner may have adopted it without changing URL.
            can_isolate = (entry.get("recoverable_read") is True
                           and entry.get("read_only") is True and pool is not None
                           and entry.get("failed_url") == entry["page"].url)
            if not can_isolate:
                log_step("google-busy-protected-entry")
                raise QuotationInputBusy("GOOGLE_QUOTATION_INPUT_BUSY")
            old = retained.get(key) if retained is not None else None
            if retained is not None and (old is None or len(old) < 4
                    or old[0] != _google_target_id(entry["page"]) or not old[1] or not old[3]):
                raise QuotationInputBusy("GOOGLE_QUOTATION_INPUT_BUSY")
            quarantined_target = _google_target_id(entry["page"])
            entry["target_id"] = quarantined_target
            quarantine_key = (*key, "quarantine", quarantined_target)
            if retained is not None:
                retained[quarantine_key] = old
                del retained[key]
            # The quarantined and replacement slots must not share mutable
            # controller state when scope cleanup revisits both entries.
            quarantined = GoogleQuotationUpdateActions(browser_handle=self._handle,
                location=SimpleNamespace(url=entry["page"].url), page_role=self._page_role)
            quarantined._read_only = True
            quarantined._protected = True
            entry["actions"] = quarantined
            pool[quarantine_key] = entry
            del pool[key]
            entry = None
        if entry is not None and not entry["protected"]:
            entry["read_only"] = entry.get("read_only", False) and self._read_only
            if retained is not None and not entry["read_only"]:
                # Publish loss of read-only provenance before any write can start.
                _retain_google_entry(key, entry, retained)
            self._page, self._poll_entry = entry["page"], entry
            # Prove the current document/authentication BEFORE navigating away.
            expected = self._location
            self._location = SimpleNamespace(url=self._page.url)
            actual = urlsplit(self._page.url)
            try:
                self._guard()
                if (actual.scheme, actual.hostname, actual.path) != document_key or page_owner(self._page) != self._page_role:
                    log_step("google-pooled-document-mismatch" if
                             (actual.scheme, actual.hostname, actual.path) != document_key
                             else "google-tab-ownership-lost")
                    raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED")
                if bounded_browser_call(self._page, "evaluate", _UNSAFE_POLL_PAGE):
                    log_step("google-busy-pooled-unsafe")
                    raise QuotationInputBusy("GOOGLE_QUOTATION_INPUT_BUSY")
            except Exception as failure:
                # Preserve genuine unfinished work without repeatedly adding tabs.
                # A pure-read page that only lost its document (Chrome's error
                # page) carries no work to preserve, so leave it recoverable and
                # let the reviewed error-page isolation path above replace it.
                entry["protected"] = not (self._read_only and isinstance(failure, GoogleReadTargetUnavailable))
                self._page, self._poll_entry, self._protected = None, None, False
                raise
            finally:
                self._location = expected
            if self._page is not None:
                if select_worksheet:
                    # Native range transport selects/proves its worksheet next;
                    # do not reload default gid=0 on every range operation.
                    self._location = SimpleNamespace(url=self._page.url)
                elif self._page.url != expected.url:
                    self._attempt(lambda: bounded_browser_call(self._page, "goto", expected.url, wait_until="domcontentloaded", timeout=self._timeout, timeout_ms=(self._timeout)+1000))
                self._guard()
                return self._page
        # Page count is not transaction safety. Independent/nested task scopes
        # may coexist; exact ownership/protected-entry/settlement gates above
        # still apply, and each originating scope retires only its own pages.
        try:
            self._page = new_background_page(browser, browser.contexts[0], timeout_ms=self._timeout,
                                             owner=self._page_role)
        except Exception:  # noqa: BLE001 - shared context cannot create the owned operation
            raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE") from None
        # Record the exact native target before navigation can fail. Otherwise
        # an uncertain initial page can be leaked and replaced on every poll.
        if pool is not None:
            self._poll_entry = {"page": self._page, "actions": self, "protected": False,
                                "read_only": self._read_only}
            pool[key] = self._poll_entry
            if retained is not None:
                _retain_google_entry(key, self._poll_entry, retained)
        self._attempt(lambda: bounded_browser_call(self._page, "goto", self._location.url, wait_until="domcontentloaded", timeout=self._timeout, timeout_ms=(self._timeout)+1000))
        self._guard()
        # Navigation may have handed the surface to the Owner. Never repair an
        # ownership marker by overwriting it after control has been yielded.
        self._require_owned_page()
        return self._page

    def _ready_control(self):
        self.wait_for_script_menu()
        return self._update_control()

    def wait_for_script_menu(self):
        # Real Sheets exposes the drawing shell before onOpen/menu initialization.
        # Wait for observed script readiness, not a fixed sleep or a shell-only click.
        menu = self._page.get_by_text("报价工具", exact=True)
        self._attempt(lambda: bounded_browser_call(menu, "wait_for", state="visible", timeout=self._ready_timeout, timeout_ms=(self._ready_timeout)+1000))
        if bounded_browser_call(menu, "count") != 1:
            raise UpdateAttemptUnconfirmed("UPDATE_CONTROL_UNCONFIRMED")
        self._guard()

    def _result_dialog(self):
        # Live dialog has an observed title in its body; accessible name can be absent.
        return self._page.get_by_role("dialog").filter(
            has_text=re.compile(r"^(?:报价更新完成|更新完成)"))

    def _update_control(self):
        button = self._page.get_by_role("button", name="更新报价", exact=True)
        if bounded_browser_call(button, "count") == 1:
            return button
        if bounded_browser_call(button, "count") > 1:
            raise UpdateAttemptUnconfirmed("UPDATE_CONTROL_UNCONFIRMED")
        # Verified on the exact metadata-bound quote-input sheet, 2026-10-07:
        # two DOM overlays, only one visible; Owner screenshot identifies it.
        drawing = self._page.locator(
            'div.waffle-borderless-embedded-object-overlay[aria-label="绘图："]:visible'
        )
        if bounded_browser_call(drawing, "count") == 0:
            self._attempt(lambda: bounded_browser_call(drawing, "wait_for", state="visible", timeout=self._timeout, timeout_ms=(self._timeout)+1000))
        if bounded_browser_call(drawing, "count") != 1:
            raise UpdateAttemptUnconfirmed("UPDATE_CONTROL_UNCONFIRMED")
        return drawing

    def click_update_quote(self):
        if self._script_pending:
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED")
        self._guard()
        button = self._ready_control()
        # Stale result dialogs cannot be mistaken for this attempt's result.
        if bounded_browser_call(self._result_dialog(), "count"):
            raise UpdateAttemptUnconfirmed("UPDATE_RESULT_STALE")
        self._acquire_write_owner()
        if self._price_refresh:
            # Arm before native dispatch; a click timeout may mean it DID execute.
            bounded_browser_call(button, "evaluate", _SCRIPT_SETTLEMENT_LATCH, timeout=self._timeout)
            bounded_browser_call(self._page, "evaluate", "() => { window.__insoRefreshPending = true; }")
            self._script_pending = True
            self._page._inso_active_quote_action = self
            lease = getattr(self._page, "_inso_native_page_owner", None)
            if lease is not None and isinstance(lease[0], str):
                self._active_quote_target = lease[0]
                with _ACTIVE_QUOTE_LOCK:
                    _ACTIVE_QUOTE_TARGETS[self._active_quote_target] = self
            try:
                bounded_browser_call(button, "click", timeout=self._timeout, timeout_ms=(self._timeout)+1000)
            except Exception:  # noqa: BLE001 - do not retry a possibly delivered refresh click
                self._hold_document("GOOGLE_QUOTE_CLICK_UNCONFIRMED")
                raise UpdateClickUnconfirmed("UPDATE_RESULT_UNCONFIRMED") from None
        else:
            self._attempt(lambda: bounded_browser_call(button, "evaluate", _SCRIPT_SETTLEMENT_LATCH, timeout=self._timeout))
            self._attempt(lambda: bounded_browser_call(self._page, "evaluate", "() => { window.__insoQuoteSettlement.initial = true; window.__insoRefreshPending = true; }"))
            self._script_pending = True
            self._page._inso_active_quote_action = self
            lease = getattr(self._page, "_inso_native_page_owner", None)
            if lease is not None and isinstance(lease[0], str):
                self._active_quote_target = lease[0]
                with _ACTIVE_QUOTE_LOCK:
                    _ACTIVE_QUOTE_TARGETS[self._active_quote_target] = self
            try:
                bounded_browser_call(button, "click", timeout=self._timeout, timeout_ms=(self._timeout)+1000)
            except Exception:  # noqa: BLE001 - native click may already have executed
                self._hold_document("GOOGLE_QUOTE_CLICK_UNCONFIRMED")
                raise UpdateClickUnconfirmed("UPDATE_RESULT_UNCONFIRMED") from None

    def read_update_result(self):
        self._guard()
        dialog = self._result_dialog()
        try:
            bounded_browser_call(dialog, "wait_for", state="visible", timeout=self._popup_timeout, timeout_ms=(self._popup_timeout)+1000)
        except Exception as exc:
            if isinstance(exc, TimeoutError) or (type(exc).__name__ == "TimeoutError"
                    and type(exc).__module__.startswith("playwright")):
                # The click already happened. Report the actual timeout immediately;
                # the page and the order remain unresolved and are not reused here.
                self._hold_document("GOOGLE_QUOTE_RESULT_UNCONFIRMED")
                raise UpdateResultTimeout("UPDATE_RESULT_POPUP_TIMEOUT") from exc
            self._guard()
            self._hold_document("GOOGLE_QUOTE_RESULT_UNCONFIRMED")
            raise UpdateAttemptUnconfirmed("UPDATE_RESULT_UNCONFIRMED") from exc
        if bounded_browser_call(dialog, "count") != 1:
            self._hold_document("GOOGLE_QUOTE_RESULT_UNCONFIRMED")
            raise UpdateAttemptUnconfirmed("UPDATE_RESULT_UNCONFIRMED")
        return self._attempt(lambda: bounded_browser_call(dialog, "inner_text", timeout=self._timeout, timeout_ms=(self._timeout)+1000))

    def dismiss_result(self):
        self._guard()
        dialog = self._result_dialog()
        if bounded_browser_call(dialog, "count") != 1:
            raise UpdateAttemptUnconfirmed("UPDATE_RESULT_UNCONFIRMED")
        button = dialog.get_by_role("button", name="确定", exact=True)
        if bounded_browser_call(button, "count") != 1:
            raise UpdateAttemptUnconfirmed("UPDATE_DISMISS_UNCONFIRMED")
        # Script clears input after UI confirmation. Do not write the next row until
        # this observed execution ends; never clear the shared input ourselves.
        self._script_pending = True
        try:
            self._require_owned_page()
            bounded_browser_call(button, "evaluate", _SCRIPT_SETTLEMENT_LATCH, timeout=self._timeout)
            self._guard()
            self._require_owned_page()
            bounded_browser_call(button, "click", timeout=self._timeout, timeout_ms=(self._timeout)+1000)
            bounded_browser_call(self._page, "wait_for_function",
                "() => window.__insoQuoteSettlement?.confirmed && window.__insoQuoteSettlement.started",
                timeout=self._result_timeout, timeout_ms=(self._result_timeout)+1000)
            bounded_browser_call(self._page, "wait_for_function",
                "() => window.__insoQuoteSettlement?.started && window.__insoQuoteSettlement.settled",
                timeout=self._result_timeout, timeout_ms=(self._result_timeout)+1000)
            self._guard()
            self._require_owned_page()
            bounded_browser_call(self._page, "evaluate", "() => window.__insoQuoteSettlement.observer.disconnect()")
            self._guard()
            self._require_owned_page()
            bounded_browser_call(self._page, "evaluate", "() => { window.__insoRefreshPending = false; }")
        except Exception:  # noqa: BLE001 - any settlement uncertainty preserves the operation page
            self._hold_document("GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED")
            raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED") from None
        self._script_pending = False
        self._release_page_document_hold()
        self._release_write_owner()

    def _attempt(self, operation):
        try:
            return operation()
        except V12Fault:
            raise
        except Exception as exc:
            if self._page is not None and self._page.url == "chrome-error://chromewebdata/":
                # The URL cannot identify the transport failure (including TLS).
                # Only the read caller may classify the original exception.
                raise UpdateAttemptUnconfirmed("GOOGLE_NAVIGATION_FAILED") from exc
            self._guard()
            raise UpdateAttemptUnconfirmed("UPDATE_RESULT_UNCONFIRMED") from None

    def close_temporary_failed_read(self):
        """Close only this client's proven read-only failed page, never a write surface."""
        page = self._page
        entry = self._poll_entry
        if (not self._read_only or self._script_pending or self._protected or page is None
                or page.is_closed() or (entry is not None and entry.get("read_only") is not True)):
            return False
        try:
            if page.url == "chrome-error://chromewebdata/":
                # Chrome's error page exposes no document, so the ordinary
                # window.name/document proof cannot run there. Native target
                # identity is the same proof the write path accepts, and this
                # client created the target: release only that exact pure-read
                # page instead of leaving an unusable tab behind.
                lease = getattr(page, "_inso_native_page_owner", None)
                if lease is None or native_page_owner(page) != self._page_role:
                    return False
                if entry is not None and entry.get("target_id") not in (None, lease[0]):
                    return False
                if self._handle.browser is None or not self._handle.browser.is_connected():
                    return False
            else:
                self._require_owned_page()
                self._guard(read_selection=True)
                target_id = _google_target_id(page)
                if entry is not None and entry.get("target_id") not in (None, target_id):
                    return False
            if not any(other is not page and not other.is_closed() for other in page.context.pages):
                return False  # Do not close the browser's last page.
            bounded_browser_call(page, "close")
            return page.is_closed()
        except Exception:  # noqa: BLE001 - retain anything whose ownership cannot be proved
            return False

    def retire_failed_page(self, *, read_only=False):
        """Never pass a failed phase's page to another phase/retry."""
        # Pure read failures use retained-page isolation only; they are not a
        # dispatched-write unknown and must not freeze unrelated writes.
        if self._page is not None and not read_only:
            self._hold_document("GOOGLE_WRITE_UNCONFIRMED")
        if read_only and self._page is not None and not self._page.is_closed():
            try:
                # Never restore or overwrite a marker after ownership changed:
                # the Owner may have adopted this exact native page.
                if (getattr(self._page, "_inso_native_page_owner", None) is None
                        or native_page_owner(self._page) != self._page_role
                        or page_owner(self._page) != self._page_role):
                    self._protected = True
                else:
                    bounded_browser_call(self._page, "evaluate", "() => { window.__insoGoogleReadFailed = true; }")
            except Exception:  # noqa: BLE001 - inability to prove ownership stays protected
                self._protected = True
        if self._poll_entry is None:
            return
        recoverable_read = (read_only and self._poll_entry.get("read_only") is True
                            and not self._protected and not self._script_pending)
        self._poll_entry["protected"] = True
        self._poll_entry["actions"] = self
        failed_entry = self._poll_entry
        self._poll_entry = None
        try:
            # Ordinary read failures can be closed; unresolved work stays visible.
            self._protected |= bool(bounded_browser_call(self._page, "evaluate", _UNSAFE_POLL_PAGE))
        except Exception:  # noqa: BLE001 - uncertain old surface is retained
            self._protected = True
        # A later read cannot erase this slot's prior write history.
        failed_entry["reopenable"] = (read_only and failed_entry.get("read_only") is True
                                      and not self._protected and not self._script_pending)
        if read_only and not failed_entry["reopenable"]:
            self._protected = True  # The subsequent close must preserve the quarantined page.
        failed_entry["recoverable_read"] = recoverable_read
        failed_entry["failed_url"] = self._page.url if recoverable_read else None
        scope = _POLL_GOOGLE_PAGES.get()
        if scope is not None and scope[1] is not None and not failed_entry["page"].is_closed():
            for key, entry in scope[0].items():
                if entry is failed_entry:
                    _retain_google_entry(key, entry, scope[1])
                    break

    def _acquire_write_owner(self):
        """Atomically claim the in-flight write lease immediately before dispatch."""
        if self._document_write_owner is not None:
            return
        admission = self._require_write_admission()
        document = self._document_key()
        owner = object()
        try:
            admission.begin_document_write(document, owner)
        except DocumentWriteHeld as exc:
            raise QuotationInputBusy("GOOGLE_QUOTATION_INPUT_BUSY") from exc
        except DocumentWriteBusy as exc:
            raise QuotationInputBusy("GOOGLE_QUOTATION_INPUT_BUSY") from exc
        self._document_write_owner = owner

    def _release_write_owner(self):
        owner = self._document_write_owner
        if owner is None:
            return
        self._document_write_owner = None
        admission = self._shared_admission()
        if admission is None:
            return
        try:
            document = self._document_key()
        except ValueError:
            return
        admission.end_document_write(document, owner)

    def close(self):
        try:
            self._close_impl()
        finally:
            self._release_write_owner()

    def _close_impl(self):
        if (self._page is not None and not self._read_only
                and (self._script_pending or self._protected)):
            # Close cannot settle an unresolved write; publish a durable-to-restart
            # shared hold before any later client can open the same document.
            self._hold_document("GOOGLE_WRITE_UNCONFIRMED")
        if self._active_quote_target is not None:
            with _ACTIVE_QUOTE_LOCK:
                if _ACTIVE_QUOTE_TARGETS.get(self._active_quote_target) is self:
                    del _ACTIVE_QUOTE_TARGETS[self._active_quote_target]
            self._active_quote_target = None
        if (self._page is not None and
                getattr(self._page, "_inso_active_quote_action", None) is self):
            self._page._inso_active_quote_action = None
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
                        or page_owner(self._page) != self._page_role
                        or bool(bounded_browser_call(self._page, "evaluate", _UNSAFE_POLL_PAGE)))
                except Exception:  # noqa: BLE001 - unknown surfaces are quarantined, never reused
                    entry["protected"] = True
                finally:
                    self._location = expected
            entry["actions"] = self
            self._protected |= entry["protected"]
            if not self._read_only and self._protected:
                self._hold_document("GOOGLE_WRITE_UNCONFIRMED")
            scope = _POLL_GOOGLE_PAGES.get()
            if scope is not None and scope[1] is not None and not entry["page"].is_closed():
                for key, candidate in scope[0].items():
                    if candidate is entry:
                        _retain_google_entry(key, entry, scope[1])
                        break
            self._page = None
            return
        if self._price_refresh and self._script_pending:
            # The browser-visible marker, not this disposable controller, owns
            # recovery. Preserve the tab and allow a later attempt to re-check it.
            self._page, self._script_pending, self._price_refresh = None, False, False
            return
        if self._protected or self._script_pending or self._page is None:
            return
        # Earlier ownership cannot authorize closing a surface Owner moved/adopted.
        special = self._page.url in {"about:blank", "chrome-error://chromewebdata/"}
        try:
            actual, expected = urlsplit(self._page.url), urlsplit(self._location.url)
            owner = native_page_owner(self._page) if special else page_owner(self._page)
            if (owner != self._page_role or not special and
                    (actual.scheme, actual.hostname, actual.path) != (expected.scheme, expected.hostname, expected.path)):
                self._protected = True
                return
        except Exception:
            self._protected = True
            raise
        try:
            self._guard()
        except V12Fault:
            if self._protected:
                return
        except (UpdateAttemptUnconfirmed, GoogleReadTargetUnavailable):
            # An unprovable surface or a pure-read page that only lost its
            # document cannot certify its contents; both still close below
            # under the native-owner proof taken immediately above.
            pass
        try:
            # Keep the protected browser alive if this has become its last tab.
            context = self._page.context
            if not any(page is not self._page and not page.is_closed() for page in context.pages):
                blank = new_background_page(self._handle.browser, context, timeout_ms=self._timeout)
                if blank is self._page or blank.is_closed() or blank.url != "about:blank":
                    raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_OPERATION_NOT_CLOSED")
            bounded_browser_call(self._page, "close")
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
                                notify_refresh_uncertain=lambda _r, _old, _new: None, persist_uncertain=None):
    """Domain input contract supplied by the canonical Google web transport.

    RFQ-006 owns production scheduling/wiring. This factory performs no I/O.
    """
    return V13QuotationUpdater(
        source=WorkflowQuotationSource(reader=source_reader, store=store),
        quotation_input=GoogleQuotationInput(service, location, expected_columns=QUOTATION_COLUMNS, retry_wait=wait),
        actions=GoogleQuotationUpdateActions(browser_handle=browser_handle, location=location),
        wait=wait, stop_requested=stop_requested,
        notify_model_difference=notify_model_difference,
        price_store=price_store, currency_rate=currency_rate,
        notify_refresh_uncertain=notify_refresh_uncertain, persist_uncertain=persist_uncertain,
    )
