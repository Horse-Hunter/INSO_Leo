"""Launcher-owned access to the unique authenticated INSO shell page."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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
            if selector != "#_id_dg" and not locator.is_visible():
                return None
        return frame
    except Exception:  # noqa: BLE001 - any ambiguity fails closed
        return None


def attach_inso_research_session(
    endpoint: str,
    browser_handle: Any,
    *,
    cycle_id: str,
    cycle_is_drained: Callable[[str], bool],
    playwright_factory: Callable[[], Any] | None = None,
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
