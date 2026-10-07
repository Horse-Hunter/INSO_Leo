"""Launcher-owned access to the unique authenticated INSO shell page.

This module also owns the only place an INSO login is established. Owner finding
(2026-10-01): the session died while a run was in flight, every later ERP step
then failed as a missing control, and the operator saw the purchase leg report
``采购录单异常`` -- indistinguishable from a genuinely broken selector -- until
they noticed and logged in by hand.

The INSO login does not survive between workflow steps: it was observed dead
within minutes while all 122 cookies were still present and unexpired on the
clock. Two cheaper ways of proving a session were measured against the live site
and both are wrong, in opposite directions:

* A pre-existing document. An ERP page keeps rendering after the session behind
  it is gone. That "fossil" grid is how 登录态完好 was once misread.
* A raw ``context.request`` GET. It answers **200 with the list page's own URL**
  while the body is the ERP's 2.7 kB ``.winbox`` expiry stub, so status, path and
  the absence of a password field all agree -- and all lie.

Owner rule (2026-10-01) therefore: **every INSO entry reopens the page and
re-establishes the login.** :class:`InsoSessionGuard` uses login.aspx?t=islogin,
then the authenticated home's native 业务询价 menu. It never navigates directly
to List.aspx: the parent home is required for native purchase dialogs.

Everything fails closed. A CAPTCHA, OTP or device-verification challenge is never
answered programmatically, and a failure that is not a session failure is handed
back unchanged.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from time import monotonic, sleep
from typing import Any
from urllib.parse import urlsplit

_log = logging.getLogger("inso.inso_session")

from src.inso.session import (
    BrowserIdentity,
    BrowserOwnership,
    ContextIdentity,
    InsoOperationAccess,
    InsoSessionLease,
    PageIdentity,
    SecurityViolation,
)

_INSO_ORIGIN = "https://yingsuo.alperp.cn"
_INSO_HOSTNAME = "yingsuo.alperp.cn"
_LIST_PATH = "/innerenquiry/yewuxj/list.aspx"
_LOGIN_PATH = "/login.aspx"
_LOGIN_URL = f"{_INSO_ORIGIN}{_LOGIN_PATH}?t=islogin"

#: Where the ERP sends a browser that no longer holds a session. Measured on the
#: live site (2026-10-01): a navigation answers with the ERP's transit page
#: ``/skins/etaoerp/home/checking.aspx?gourl=...`` and then
#: ``/login.aspx?t=islogin``.
_CHECKING_PATH = "/skins/etaoerp/home/checking.aspx"

#: The ERP's own submit control (``onClick="login()"``), which is what posts the
#: page's ``_xsrf`` token. The exact text is kept as a fallback so a cosmetic
#: class change cannot silently disable login.
_LOGIN_BUTTON_SELECTOR = "button.sign-button.submit:visible"
_LOGIN_BUTTON_TEXT = "登录"
_SMS_CHALLENGE_SELECTOR = "#YZM"

#: The authenticated inquiry list as the ERP itself renders it. These three
#: controls together are the only accepted proof of a live session. ``.winbox``
#: is the ERP's *expired* stub -- the dialog that answers 200 on the list page's
#: own URL -- so its absence is checked explicitly.
_APP_MARKERS_JS = """() => {
  const drawn = (node) => !!node
    && !!(node.offsetWidth || node.offsetHeight || node.getClientRects().length);
  return {
    grid: document.querySelectorAll("#_id_dg").length,
    detail: document.querySelectorAll("#DetailFieldValue").length,
    select: document.querySelectorAll("button#select_btns").length,
    stub: document.querySelectorAll(".winbox").length,
    detailDrawn: drawn(document.querySelector("#DetailFieldValue")) ? 1 : 0,
    selectDrawn: drawn(document.querySelector("button#select_btns")) ? 1 : 0,
  };
}"""

_LOGIN_FORM_TIMEOUT_MS = 20_000
_NAVIGATION_TIMEOUT_MS = 20_000
_LOGIN_WAIT_SECONDS = 20.0
_LIST_RENDER_SECONDS = 20.0
_RENDER_POLL_SECONDS = 0.25

_MANUAL_VERIFICATION_MARKERS = (
    "captcha",
    "otp",
    "verification code",
    "device verification",
    "验证码",
    "动态口令",
    "设备验证",
    "安全验证",
)


class InsoAuthenticationError(SecurityViolation):
    """A sanitized, fail-closed ordinary-login result."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class _BrowserHandle:
    def __init__(self, browser: Any, disconnect_and_close: Any) -> None:
        self.browser = browser
        self._disconnect_and_close = disconnect_and_close

    def is_connected(self) -> bool:
        return self.browser.is_connected()

    def close(self) -> None:
        self._disconnect_and_close()


class _ContextHandle:
    def __init__(self, browser: Any, context: Any) -> None:
        self.browser = browser
        self.context = context

    def is_closed(self) -> bool:
        return not self.browser.is_connected() or self.context not in self.browser.contexts


class _IdentityProbe:
    def __init__(self, endpoint: str, browser: Any, context: Any) -> None:
        self.endpoint = endpoint
        self.browser = browser
        self.context = context

    def endpoint_id(self, _browser: _BrowserHandle) -> str:
        return self.endpoint

    def browser_id(self, _browser: _BrowserHandle) -> str:
        return str(id(self.browser))

    def context_id(self, context: _ContextHandle) -> str:
        return str(id(context.context))

    def page_identity(self, page: Any) -> PageIdentity | None:
        if (
            page.is_closed()
            or page.context is not self.context
            or page not in self.context.pages
        ):
            return None
        return PageIdentity(str(id(self.context)), str(id(page)))


@dataclass(slots=True)
class InsoResearchSession:
    """One verified context and its already-open authenticated shell page."""

    lease: InsoSessionLease
    _playwright: Any
    _browser_handle: Any
    _ownership: BrowserOwnership

    def operation_access(self) -> InsoOperationAccess:
        return self.lease.adapter_access("research-inso-history")

    @property
    def owns_operation_page(self) -> bool:
        return self.lease.owns_operation_page

    def close_owned_operation_tab(self) -> None:
        InsoOperationAccess(self.lease, "launcher-cleanup").close_owned_operation_tab()

    def close_after_drain(self) -> None:
        self.lease.close_after_drain()
        if self._ownership is BrowserOwnership.REUSED:
            if hasattr(self._browser_handle, "disconnect"):
                self._browser_handle.disconnect()
            else:
                self._playwright.stop()


def _verified_shell_frame(page: Any, context: Any) -> Any | None:
    """Return the one authenticated list frame; never choose a first match."""

    try:
        if page.is_closed() or page.context is not context or page not in context.pages:
            return None
        main_url = urlsplit(page.main_frame.url)
        if (
            main_url.scheme != "https"
            or main_url.hostname != _INSO_HOSTNAME
            or main_url.path.casefold().endswith(_LOGIN_PATH)
        ):
            return None
        frames = [
            frame
            for frame in page.frames
            if (url := urlsplit(frame.url)).scheme == "https"
            and url.hostname == _INSO_HOSTNAME
            and url.path.casefold().endswith(_LIST_PATH)
        ]
        if len(frames) != 1:
            return None
        frame = frames[0]
        # The two confirmed controls must be unique and visible: together they
        # prove this frame is the authenticated inquiry list, never a login or
        # landing page.
        for selector in ("#DetailFieldValue", "button#select_btns"):
            locator = frame.locator(selector)
            if locator.count() != 1:
                return None
            if not locator.is_visible():
                return None
        # The result grid must be present exactly once, but it is deliberately
        # not required to be visible. A read-only exact duplicate query that
        # matches nothing -- or any query whose set layui renders compactly --
        # collapses the grid to zero size while leaving the authenticated list
        # shell fully usable. Requiring a visible grid made the shell
        # unverifiable after the very first duplicate check, which broke the next
        # poll cycle's attach. Presence (not size) is the identity signal here.
        if frame.locator("#_id_dg").count() != 1:
            return None
        return frame
    except Exception:  # noqa: BLE001 - any ambiguity fails closed
        return None


def ensure_inso_authenticated(
    browser: Any,
    login: Any | None,
    *,
    login_url: str = _LOGIN_URL,
    timeout_seconds: float = _LOGIN_WAIT_SECONDS,
    wait: Callable[[float], None] = sleep,
    clock: Callable[[], float] = monotonic,
    fresh_page: bool = False,
) -> Any | None:
    """Reopen the ERP and ensure a *proven* authenticated list page.

    Returns the tab this call opened, or ``None`` when it reused one that was
    already there, so the caller can hand back exactly what it took.

    One implementation, shared with the in-run guard, so the run entry and the
    recovery path can never disagree about what "logged in" means.

    This deliberately owns no credential storage. ``login`` is the already
    resolved Core-backed object and is used only to fill the two confirmed
    ordinary-login fields. CAPTCHA, OTP and device-verification pages are never
    handled programmatically.
    """

    if not bool(getattr(browser, "is_connected", lambda: False)()):
        raise InsoAuthenticationError("AUTHENTICATION_REQUIRED")
    contexts = tuple(getattr(browser, "contexts", ()))
    if len(contexts) != 1:
        raise InsoAuthenticationError("AUTHENTICATION_REQUIRED")
    context = contexts[0]
    if not _valid_login(login):
        raise InsoAuthenticationError("AUTHENTICATION_REQUIRED")

    guard = InsoSessionGuard(
        login=login,
        context=lambda: context,
        login_url=login_url,
        login_timeout_seconds=timeout_seconds,
        wait=wait,
        clock=clock,
        fresh_page=fresh_page,
    )
    status = guard.ensure_authenticated()
    if status.outcome is InsoSessionOutcome.DEAD:
        try:
            if (
                status.reason_code != "MANUAL_VERIFICATION_REQUIRED"
                and guard.opened_page is not None
                and not guard.opened_page.is_closed()
            ):
                guard.opened_page.close()
        except Exception:  # noqa: BLE001 - retain the original authentication failure
            _log.warning("failed to close the new INSO authentication tab")
        raise InsoAuthenticationError(
            status.reason_code or "AUTHENTICATION_REQUIRED"
        )
    return guard.opened_page


def _app_markers(page: Any) -> dict[str, Any] | None:
    """Read the ERP's own controls out of a page, or ``None`` if unreadable."""

    try:
        markers = page.evaluate(_APP_MARKERS_JS)
    except Exception:  # noqa: BLE001 - an unreadable page proves nothing
        return None
    return markers if isinstance(markers, dict) else None


def _list_page_is_authenticated(page: Any) -> bool:
    """True only when *this* page is the rendered inquiry list right now.

    The URL is not enough on its own: the ERP serves its expiry stub -- a small
    ``.winbox`` dialog -- on the list page's own URL, so a 200 at the right path
    can still be a dead session. The ERP's controls must be present, the stub
    must not be, and the page must not be sitting on the login or transit path.

    The controls must also be *drawn*, not merely present in the DOM. The list
    page is navigated with ``wait_until="domcontentloaded"``, which returns
    while layui is still building the toolbar, so a presence-only check declares
    a healthy session ready a moment before the query controls exist as
    anything a user could touch. Downstream read that as a broken page --
    measured live 2026-10-01: the first duplicate check of every GUI session
    (the only one that follows a fresh navigation) failed with
    ``FAILED_STAGE=QUERY_INPUT`` on ``#DetailFieldValue``, while later checks in
    the same session, which reuse the already-settled page, passed. Waiting for
    the drawn state here fixes the cause instead of every symptom. The wait
    remains bounded by ``_open_list_page``'s deadline, so a page that never
    draws is still reported as an unusable session rather than hanging.
    """

    try:
        current = urlsplit(page.main_frame.url)
    except Exception:  # noqa: BLE001 - an unreadable url proves nothing
        return False
    if current.scheme != "https" or current.hostname != _INSO_HOSTNAME:
        return False
    if current.path.casefold().endswith((_LOGIN_PATH, _CHECKING_PATH)):
        return False
    markers = _app_markers(page)
    if markers is None:
        return False
    return (
        bool(markers.get("grid"))
        and bool(markers.get("detail"))
        and bool(markers.get("select"))
        and bool(markers.get("detailDrawn"))
        and bool(markers.get("selectDrawn"))
        and not markers.get("stub")
    )


def _open_list_page(
    page: Any,
    *,
    wait: Callable[[float], None],
    clock: Callable[[], float],
    timeout_seconds: float = _LIST_RENDER_SECONDS,
) -> bool:
    """Enter the list through the authenticated home's native menu.

    Direct list navigation lacks the parent's purchase-dialog infrastructure.
    Owner rule: login.aspx?t=islogin, ordinary login, then click 业务询价.
    """
    deadline = clock() + timeout_seconds
    clicks = 0
    last_click = 0.0
    expanded = False
    while True:
        frame = _verified_shell_frame(page, page.context)
        if frame is not None and frame is not page.main_frame:
            return True
        if _is_login_page(page):
            return False
        menu_ready = page.evaluate(
            "() => document.readyState === 'complete' && "
            "typeof window.jQuery?.fn?.BillTab === 'function'"
        ) is True
        retry_menu = clicks == 0 or (
            clicks == 1 and clock() - last_click >= 5.0
            and page.locator("iframe#iframe_YeWuXJ_frame").count() == 0
        )
        if retry_menu and menu_ready:
            entry = page.locator("a#iframe_YeWuXJ_menu")
            if entry.count() > 1:
                return False
            if entry.count() == 1 and not entry.is_visible() and not expanded:
                group = page.locator('a[onclick="expandable(this, 8)"]')
                if group.count() == 1 and group.is_visible() and group.is_enabled():
                    group.click(timeout=_NAVIGATION_TIMEOUT_MS)
                    expanded = True
            if entry.count() == 1 and entry.is_visible() and entry.is_enabled():
                entry.click(timeout=_NAVIGATION_TIMEOUT_MS)
                # Native tab creation can swallow an early click during home
                # initialization. Retry that read-navigation once, only if it
                # created NO iframe; never duplicate a pending/list tab.
                clicks += 1
                last_click = clock()
        if clock() >= deadline:
            return False
        _wait_page_events(page, wait, min(_RENDER_POLL_SECONDS, max(0.0, deadline - clock())))


def _wait_page_events(page: Any, wait: Callable[[float], None], seconds: float) -> None:
    """Pump the existing synchronous client's navigation/frame events."""
    if wait is sleep:
        page.wait_for_timeout(seconds * 1000)
    else:
        wait(seconds)


class InsoSessionOutcome(StrEnum):
    """What an entry into the ERP established about the INSO session."""

    #: The reopened page already rendered the list; nothing was touched.
    AUTHENTICATED = "AUTHENTICATED"
    #: The reopen did not render the list, and the ordinary login fixed it.
    RESTORED = "RESTORED"
    #: Still not the list. ``reason_code`` says why; the ERP was never reached.
    DEAD = "DEAD"


@dataclass(frozen=True, slots=True)
class InsoSessionStatus:
    """Result of :meth:`InsoSessionGuard.ensure_authenticated`."""

    outcome: InsoSessionOutcome
    reason_code: str | None = None

    @property
    def reauthenticated(self) -> bool:
        """True only when this call performed the login that restored the session."""

        return self.outcome is InsoSessionOutcome.RESTORED


class InsoSessionGuard:
    """Reopen the ERP, prove the login behind it, and restore it when it is gone.

    Owner rule (2026-10-01): every INSO entry opens the page again and
    re-establishes the session, because the login does not survive between
    workflow steps and no cheaper signal about it can be trusted. The proof is
    therefore always the same shape -- a real navigation, judged by the ERP's
    own authenticated controls.

    The caller decides what to do with the answer, which is what keeps a real
    session failure from being confused with a broken selector:

    ``AUTHENTICATED``
        The reopened page rendered the list. Nothing was touched, so the failure
        that led here was not a session failure and must not be retried.
    ``RESTORED``
        The reopen failed and the ordinary login fixed it. A bounded retry is
        justified because the session really had gone.
    ``DEAD``
        Not usable, with ``reason_code`` saying why. The ERP cannot have been
        reached, so the honest report is ``SESSION_STALE`` -- never a missing
        control.

    ``force_login`` is what a run entry uses: it skips the first proof and logs
    in unconditionally. The diagnosis call made after a failure leaves it off,
    so a healthy session is never re-logged-in and therefore never mistaken for
    a recovered one.

    ``reattach`` is required whenever the caller leases a verified shell: the
    lease is pinned to one page identity, so a login invalidates it even though
    the session is healthy again. ``context`` is the live browsing context; it
    is resolved only when a login is actually needed.
    """

    def __init__(
        self,
        *,
        login: Any | None,
        context: Callable[[], Any],
        reattach: Callable[[], None] | None = None,
        page: Callable[[], Any] | None = None,
        fresh_page: bool = False,
        login_url: str = _LOGIN_URL,
        login_timeout_seconds: float = _LOGIN_WAIT_SECONDS,
        wait: Callable[[float], None] = sleep,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._login = login
        self._context = context
        self._reattach = reattach
        self._page = page
        self._fresh_page = fresh_page
        self.authenticated_page: Any | None = None
        self._login_url = login_url
        self._login_timeout_seconds = login_timeout_seconds
        self._wait = wait
        self._clock = clock
        #: The tab this guard opened itself, or ``None`` when it reused one that
        #: was already open. Only a page we opened may be closed by us again.
        self.opened_page: Any | None = None

    def ensure_authenticated(
        self, *, force_login: bool = False
    ) -> InsoSessionStatus:
        """Reopen the ERP and ensure the login behind it is proven live."""

        if not _valid_login(self._login):
            return InsoSessionStatus(
                InsoSessionOutcome.DEAD, "AUTHENTICATION_REQUIRED"
            )
        try:
            if self._page is not None:
                page, opened_here = self._page(), False
            elif self._fresh_page:
                page, opened_here = self._context().new_page(), True
            else:
                page, opened_here = _existing_or_new_login_page(self._context())
        except Exception:  # noqa: BLE001 - an unusable page becomes a status, not an exception
            _log.warning("no INSO page could be opened to prove", exc_info=True)
            return InsoSessionStatus(
                InsoSessionOutcome.DEAD, "AUTHENTICATION_REQUIRED"
            )
        self.opened_page = page if opened_here else None
        self.authenticated_page = page

        _log.warning("the INSO session is being established by logging in")
        try:
            submitted = self._log_in(page)
        except Exception as exc:  # noqa: BLE001 - any submit failure becomes an explicit status
            return InsoSessionStatus(
                InsoSessionOutcome.DEAD,
                getattr(exc, "reason_code", None) or "AUTHENTICATION_REQUIRED",
            )
        try:
            proven = self._prove(page)
        except Exception:  # noqa: BLE001 - native-menu failure must remain closed
            proven = False
        if not proven:
            return InsoSessionStatus(
                InsoSessionOutcome.DEAD, "AUTHENTICATED_SHELL_UNAVAILABLE"
            )
        if self._reattach is not None:
            try:
                self._reattach()
            except Exception:  # noqa: BLE001 - a failed reattach is reported, not raised
                _log.warning(
                    "the INSO shell could not be re-leased after logging in",
                    exc_info=True,
                )
                return InsoSessionStatus(
                    InsoSessionOutcome.DEAD, "SESSION_IDENTITY_UNVERIFIED"
                )
        return InsoSessionStatus(
            InsoSessionOutcome.RESTORED if submitted else InsoSessionOutcome.AUTHENTICATED
        )

    def _prove(self, page: Any) -> bool:
        return _open_list_page(
            page,
            wait=self._wait,
            clock=self._clock,
            timeout_seconds=self._login_timeout_seconds,
        )

    def _log_in(self, page: Any) -> bool:
        """Open the ordinary login form, submit it once, and let it settle.

        Returns whether an ordinary login was actually submitted. Submitting is
        not enough on its own: the form posts through the ERP's own script,
        which then navigates, so the page is given until the login timeout to
        leave the form. Leaving immediately races that redirect -- the list
        navigation would arrive before the new session exists, be served the
        login page again, and be read as a failed login. Measured live on
        2026-10-01: that race made the guard report a dead session for a login
        that had in fact succeeded.
        """

        if str(getattr(page, "url", "")) != self._login_url:
            try:
                page.goto(
                    self._login_url,
                    wait_until="domcontentloaded",
                    timeout=_LOGIN_FORM_TIMEOUT_MS,
                )
            except Exception:  # noqa: BLE001 - a form we cannot fill means authentication is required
                raise InsoAuthenticationError("AUTHENTICATION_REQUIRED") from None
        if _human_verification_required(page):
            raise InsoAuthenticationError("MANUAL_VERIFICATION_REQUIRED")
        if not _is_login_page(page):
            # The ERP refused to show a form, which means it still considers
            # this session authenticated. Nothing to submit.
            return False
        _submit_ordinary_login(page, self._login)
        self._wait_until_login_settles(page)
        return True

    def _wait_until_login_settles(self, page: Any) -> None:
        """Wait for the ERP to leave the login form, or for the challenge."""

        deadline = self._clock() + self._login_timeout_seconds
        while _is_login_page(page):
            if _human_verification_required(page):
                # The ERP revealed a code field after the submit, so this login
                # is human-only. Stop rather than guess.
                raise InsoAuthenticationError("MANUAL_VERIFICATION_REQUIRED")
            if self._clock() >= deadline:
                # Still on the form. The proof that follows decides what that
                # means; it must not be reported as a restored session.
                return
            _wait_page_events(page, self._wait, min(_RENDER_POLL_SECONDS, max(0.0, deadline - self._clock())))


def _existing_or_new_login_page(context: Any) -> tuple[Any, bool]:
    """Pick the page to log in on, and say whether this call opened it.

    A live context legitimately holds Research tabs (``hqew.com``,
    ``ic.net.cn``) next to the ERP, so "the context has exactly one page" is not
    a usable rule here -- it is precisely the rule that made in-run recovery
    unable to act. Only INSO-origin pages are candidates.

    An open list page wins, then a login page: reusing the page that is already
    the shell keeps it unique, whereas turning an extra page into a second list
    page would make the lease unable to pick one. A leftover login page is
    harmless by comparison -- it is not a shell. The chosen page is navigated by
    :meth:`InsoSessionGuard.ensure_authenticated`.

    The second element is what lets the launcher give back only the tab it
    opened: a tab the Owner already had open is never closed by us.
    """

    candidates = tuple(
        page
        for page in tuple(getattr(context, "pages", ()))
        if _is_inso_origin_page(page)
    )
    for page in candidates:
        if _is_list_page(page):
            return page, False
    for page in candidates:
        if _is_login_page(page):
            return page, False
    if candidates:
        return candidates[0], False
    return context.new_page(), True


def _submit_ordinary_login(page: Any, login: Any | None) -> None:
    """Fill the two confirmed fields and press the page's own login control.

    At most one ordinary login attempt. The controls are resolved before either
    field is written, and each write is read back before the submit, so a
    rejected field can never be followed by a click.
    """

    if not _valid_login(login):
        raise InsoAuthenticationError("AUTHENTICATION_REQUIRED")
    try:
        username = _single_visible_enabled(page, "input#personname:visible")
        password = _single_visible_enabled(page, "input#password:visible")
        button = _login_button(page)
    except Exception:  # noqa: BLE001 - a form we cannot resolve means authentication is required
        raise InsoAuthenticationError("AUTHENTICATION_REQUIRED") from None
    try:
        username.fill(login.username)
        if not _nonempty_readback(username):
            raise ValueError("username read-back is empty")
    except Exception:  # noqa: BLE001 - an unverified read-back must not be submitted
        raise InsoAuthenticationError("AUTHENTICATION_REQUIRED") from None
    try:
        password.fill(login.password)
        if not _nonempty_readback(password):
            raise ValueError("password read-back is empty")
    except Exception:  # noqa: BLE001 - an unverified read-back must not be submitted
        raise InsoAuthenticationError("AUTHENTICATION_REQUIRED") from None
    try:
        button.click()
    except Exception:  # noqa: BLE001 - a click we cannot perform means authentication is required
        raise InsoAuthenticationError("AUTHENTICATION_REQUIRED") from None


def _login_button(page: Any) -> Any:
    """Return the one usable login submit control; never a first match."""

    try:
        confirmed = page.locator(_LOGIN_BUTTON_SELECTOR)
        count = confirmed.count()
        if count > 1:
            raise ValueError("the ERP login control is ambiguous")
        if count == 1:
            if not confirmed.is_visible() or not confirmed.is_enabled():
                raise ValueError("the ERP login control is not usable")
            return confirmed
        fallback = page.get_by_text(_LOGIN_BUTTON_TEXT, exact=True)
        if (
            fallback.count() != 1
            or not fallback.is_visible()
            or not fallback.is_enabled()
        ):
            raise ValueError("login button is not unique and usable")
    except ValueError:
        raise
    except Exception:  # noqa: BLE001 - any non-ValueError becomes an explicit auth failure
        raise ValueError("login button is not resolvable") from None
    return fallback


def _human_verification_required(page: Any) -> bool:
    """True when the login page is asking for a human-only challenge."""

    return _manual_verification_present(page) or _sms_challenge_present(page)


def _sms_challenge_present(page: Any) -> bool:
    """True when the ERP has revealed its mobile-code block.

    The block ships ``display:none`` and the ERP's own JS reveals it when the
    server decides this login needs a code, so a visible one means the ordinary
    username/password path will not complete on its own.
    """

    try:
        locator = page.locator(_SMS_CHALLENGE_SELECTOR)
        count = locator.count()
    except Exception:  # noqa: BLE001 - a challenge we cannot read is treated as absent
        return False
    if count == 0:
        return False
    if count > 1:
        return True
    try:
        return bool(locator.is_visible())
    except Exception:  # noqa: BLE001 - an unreadable challenge is assumed present
        return True


def _valid_login(login: Any | None) -> bool:
    return all(
        isinstance(getattr(login, field, None), str)
        and bool(getattr(login, field).strip())
        for field in ("username", "password")
    )


def _is_login_page(page: Any) -> bool:
    try:
        current = urlsplit(page.main_frame.url)
        return (
            current.scheme == "https"
            and current.hostname == _INSO_HOSTNAME
            and current.path.casefold().endswith(_LOGIN_PATH)
        )
    except Exception:  # noqa: BLE001 - page identity reads fail closed
        return False


def _is_inso_origin_page(page: Any) -> bool:
    try:
        current = urlsplit(page.main_frame.url)
    except Exception:  # noqa: BLE001 - page identity reads fail closed
        return False
    return current.scheme == "https" and current.hostname == _INSO_HOSTNAME


def _is_list_page(page: Any) -> bool:
    """True when the page's own document is (supposed to be) the inquiry list."""

    try:
        current = urlsplit(page.main_frame.url)
    except Exception:  # noqa: BLE001 - an unreadable url proves nothing
        return False
    return (
        current.scheme == "https"
        and current.hostname == _INSO_HOSTNAME
        and current.path.casefold().endswith(_LIST_PATH)
    )


def _single_visible_enabled(page: Any, selector: str) -> Any:
    locator = page.locator(selector)
    # Every caller supplies a ``:visible`` selector. Count is the safety
    # boundary; the native fill/click below then rejects disabled controls.
    if locator.count() != 1 or not locator.is_visible() or not locator.is_enabled():
        raise ValueError("login control is not unique and usable")
    return locator


def _nonempty_readback(locator: Any) -> bool:
    """Confirm a fill without retaining or exposing its value."""

    try:
        return bool(locator.input_value())
    except Exception:  # noqa: BLE001 - an unreadable secret field fails closed
        return False


def _manual_verification_present(page: Any) -> bool:
    try:
        text = page.locator("body").inner_text().casefold()
    except Exception:  # noqa: BLE001 - challenge inspection is best effort
        return False
    return any(marker.casefold() in text for marker in _MANUAL_VERIFICATION_MARKERS)


def attach_inso_research_session(
    endpoint: str,
    browser_handle: Any,
    *,
    cycle_id: str,
    cycle_is_drained: Callable[[str], bool],
    playwright_factory: Callable[[], Any] | None = None,
    login: Any | None = None,
    fresh_page: bool = False,
    operation_page: Any | None = None,
    owns_operation_page: bool = False,
) -> InsoResearchSession:
    """Attach to exactly one existing authenticated shell in the sole context."""

    if playwright_factory is None:
        from playwright.sync_api import sync_playwright

        playwright_factory = sync_playwright

    playwright = getattr(browser_handle, "playwright", None)
    browser = getattr(browser_handle, "browser", None)
    acquired_here = playwright is None or browser is None
    if acquired_here:
        playwright = playwright_factory().start()
    opened_page = None
    try:
        if acquired_here:
            browser = playwright.chromium.connect_over_cdp(endpoint)
        opened_page = (
            ensure_inso_authenticated(browser, login, fresh_page=fresh_page)
            if login is not None else None
        )
        contexts = tuple(browser.contexts)
        if not browser.is_connected() or len(contexts) != 1:
            raise SecurityViolation("INSO authenticated context is not unique")
        context = contexts[0]
        preferred_page = operation_page if operation_page is not None else opened_page
        shells = [
            (page, frame)
            for page in tuple(context.pages)
            if preferred_page is None or page is preferred_page
            if (frame := _verified_shell_frame(page, context)) is not None
        ]
        if len(shells) != 1:
            raise SecurityViolation("verified authenticated INSO shell is not unique")
        page, shell_frame = shells[0]
        main_frame = page.main_frame
        ownership = (
            BrowserOwnership.APP_OWNED
            if browser_handle.owned
            else BrowserOwnership.REUSED
        )
        normalized_endpoint = endpoint.rstrip("/")

        def disconnect_and_close() -> None:
            if hasattr(browser_handle, "disconnect"):
                if ownership is BrowserOwnership.APP_OWNED:
                    browser_handle.close()
                else:
                    browser_handle.disconnect()
            else:
                playwright.stop()
                if ownership is BrowserOwnership.APP_OWNED:
                    browser_handle.close()

        leased_browser = _BrowserHandle(browser, disconnect_and_close)
        leased_context = _ContextHandle(browser, context)
        probe = _IdentityProbe(normalized_endpoint, browser, context)

        def shell_identity_is_valid(candidate: Any) -> bool:
            return (
                candidate is page
                and candidate.main_frame is main_frame
                and _verified_shell_frame(candidate, context) is shell_frame
            )

        lease = InsoSessionLease(
            ownership=ownership,
            browser=leased_browser,
            context=leased_context,
            operation_page=page,
            operation_frame=shell_frame,
            browser_identity=BrowserIdentity(
                normalized_endpoint, str(id(browser))
            ),
            context_identity=ContextIdentity(str(id(browser)), str(id(context))),
            operation_page_identity=PageIdentity(str(id(context)), str(id(page))),
            identity_probe=probe,
            operation_page_is_valid=shell_identity_is_valid,
            # Owner rule (2026-10-01): the launcher gives back the tab it
            # opened. A shell the Owner already had open is left alone.
            owns_operation_page=owns_operation_page or (opened_page is not None and opened_page is page),
            cycle_id=cycle_id,
            cycle_is_drained=cycle_is_drained,
        )
        return InsoResearchSession(lease, playwright, browser_handle, ownership)
    except Exception:
        cleanup_page = opened_page or (operation_page if owns_operation_page else None)
        try:
            if cleanup_page is not None and not cleanup_page.is_closed():
                cleanup_page.close()
        except Exception:  # noqa: BLE001 - cleanup must not mask the lease failure
            _log.warning("failed to close the new INSO operation tab")
        if acquired_here:
            playwright.stop()
        if getattr(browser_handle, "owned", False) and hasattr(
            browser_handle, "close"
        ):
            # Authentication can stop at a real manual verification challenge.
            # This handle was created for the current operation, so leaving it
            # attached would orphan an app-owned Chrome process.
            browser_handle.close()
        elif not acquired_here and hasattr(browser_handle, "disconnect"):
            browser_handle.disconnect()
        raise
