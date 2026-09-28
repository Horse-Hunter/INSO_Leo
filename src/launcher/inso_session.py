"""Launcher-owned access to the unique authenticated INSO shell page."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic, sleep
from typing import Any
from urllib.parse import urlsplit

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
_LIST_PATH = "/innerenquiry/yewuxj/list.aspx"
_LOGIN_PATH = "/login.aspx"
_LOGIN_URL = f"{_INSO_ORIGIN}{_LOGIN_PATH}"
_LIST_URL = f"{_INSO_ORIGIN}/skins/etaoerp//InnerEnquiry/YeWuXJ/List.aspx"
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
            or main_url.hostname != "yingsuo.alperp.cn"
            or main_url.path.casefold().endswith("/login.aspx")
        ):
            return None
        frames = [
            frame
            for frame in page.frames
            if (url := urlsplit(frame.url)).scheme == "https"
            and url.hostname == "yingsuo.alperp.cn"
            and url.path.casefold().endswith(_LIST_PATH)
        ]
        if len(frames) != 1:
            return None
        frame = frames[0]
        for selector in ("#DetailFieldValue", "button#select_btns", "#_id_dg"):
            locator = frame.locator(selector)
            if locator.count() != 1:
                return None
            if not locator.is_visible():
                return None
        return frame
    except Exception:  # noqa: BLE001 - any ambiguity fails closed
        return None


def ensure_inso_authenticated(
    browser: Any,
    login: Any | None,
    *,
    login_url: str = _LOGIN_URL,
    timeout_seconds: float = 20.0,
    wait: Callable[[float], None] = sleep,
    clock: Callable[[], float] = monotonic,
) -> None:
    """Ensure one verified INSO shell using at most one ordinary login attempt.

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
    shells = _verified_shells(context)
    if len(shells) == 1:
        return
    if len(shells) > 1:
        raise InsoAuthenticationError("AUTHENTICATION_REQUIRED")
    needs_login = True
    if not _valid_login(login):
        raise InsoAuthenticationError("AUTHENTICATION_REQUIRED")

    pages = tuple(getattr(context, "pages", ()))
    if not pages:
        try:
            page = context.new_page()
            page.goto(login_url, wait_until="domcontentloaded", timeout=20_000)
        except Exception:  # noqa: BLE001 - never leak provider/page text
            raise InsoAuthenticationError("AUTHENTICATION_REQUIRED") from None
    elif len(pages) == 1 and _is_login_page(pages[0]):
        page = pages[0]
    elif len(pages) == 1 and _is_authenticated_inso_page(pages[0]):
        page = pages[0]
        needs_login = False
    else:
        raise InsoAuthenticationError("AUTHENTICATION_REQUIRED")

    if _manual_verification_present(page):
        raise InsoAuthenticationError("MANUAL_VERIFICATION_REQUIRED")
    if needs_login:
        try:
            username = _single_visible_enabled(page, "input#personname:visible")
            password = _single_visible_enabled(page, "input#password:visible")
            button = page.get_by_text("登录", exact=True)
            if (
                button.count() != 1
                or not button.is_visible()
                or not button.is_enabled()
            ):
                raise ValueError("login button is not unique")
            username.fill(login.username)
            if not _nonempty_readback(username):
                raise ValueError("username read-back is empty")
        except Exception:  # noqa: BLE001 - control failures fail closed
            raise InsoAuthenticationError("AUTHENTICATION_REQUIRED") from None
        try:
            password.fill(login.password)
            if not _nonempty_readback(password):
                raise ValueError("password read-back is empty")
        except Exception:  # noqa: BLE001 - control failures fail closed
            raise InsoAuthenticationError("AUTHENTICATION_REQUIRED") from None
        try:
            button.click()
        except Exception:  # noqa: BLE001 - control failures fail closed
            raise InsoAuthenticationError("AUTHENTICATION_REQUIRED") from None

    deadline = clock() + timeout_seconds
    list_navigation_attempted = False
    while clock() < deadline:
        if _manual_verification_present(page):
            raise InsoAuthenticationError("MANUAL_VERIFICATION_REQUIRED")
        shells = _verified_shells(context)
        if len(shells) == 1:
            return
        if len(shells) > 1:
            break
        if not list_navigation_attempted and _is_authenticated_inso_page(page):
            try:
                page.goto(_LIST_URL, wait_until="domcontentloaded", timeout=20_000)
                list_navigation_attempted = True
                continue
            except Exception:  # noqa: BLE001 - one read-only navigation only
                break
        wait(min(0.2, max(0.0, deadline - clock())))
    raise InsoAuthenticationError("AUTHENTICATED_SHELL_UNAVAILABLE")


def _verified_shells(context: Any) -> tuple[tuple[Any, Any], ...]:
    return tuple(
        (page, frame)
        for page in tuple(getattr(context, "pages", ()))
        if (frame := _verified_shell_frame(page, context)) is not None
    )


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
            and current.hostname == "yingsuo.alperp.cn"
            and current.path.casefold().endswith(_LOGIN_PATH)
        )
    except Exception:  # noqa: BLE001 - page identity reads fail closed
        return False


def _is_authenticated_inso_page(page: Any) -> bool:
    try:
        current = urlsplit(page.main_frame.url)
        return (
            current.scheme == "https"
            and current.hostname == "yingsuo.alperp.cn"
            and not current.path.casefold().endswith(_LOGIN_PATH)
        )
    except Exception:  # noqa: BLE001 - page identity reads fail closed
        return False


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
    try:
        if acquired_here:
            browser = playwright.chromium.connect_over_cdp(endpoint)
        if login is not None:
            ensure_inso_authenticated(browser, login)
        contexts = tuple(browser.contexts)
        if not browser.is_connected() or len(contexts) != 1:
            raise SecurityViolation("INSO authenticated context is not unique")
        context = contexts[0]
        shells = [
            (page, frame)
            for page in tuple(context.pages)
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
            cycle_id=cycle_id,
            cycle_is_drained=cycle_is_drained,
        )
        return InsoResearchSession(lease, playwright, browser_handle, ownership)
    except Exception:
        if acquired_here:
            playwright.stop()
        elif hasattr(browser_handle, "disconnect"):
            browser_handle.disconnect()
        raise
