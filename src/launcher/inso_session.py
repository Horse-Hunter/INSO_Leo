"""Launcher-owned, explicit Research access to the authenticated INSO session."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.inso.session import (
    BrowserIdentity,
    BrowserOwnership,
    ContextIdentity,
    InsoOperationAccess,
    InsoSessionLease,
    PageIdentity,
    SecurityViolation,
)


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

    def new_page(self) -> Any:
        return self.context.new_page()

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
        if page.is_closed() or page.context is not self.context:
            return None
        return PageIdentity(str(id(self.context)), str(id(page)))


@dataclass(slots=True)
class InsoResearchSession:
    """One verified default context; only lease-created child pages are used."""

    lease: InsoSessionLease
    _playwright: Any
    _ownership: BrowserOwnership

    def operation_access(self) -> InsoOperationAccess:
        return self.lease.adapter_access("research-inso-history")

    def close_after_drain(self) -> None:
        self.lease.close_after_drain()
        if self._ownership is BrowserOwnership.REUSED:
            # Stop Playwright's CDP connection; this does not close the remote browser.
            self._playwright.stop()


def attach_inso_research_session(
    endpoint: str,
    browser_handle: Any,
    *,
    cycle_id: str,
    cycle_is_drained: Any,
    playwright_factory: Callable[[], Any] | None = None,
) -> InsoResearchSession:
    """Attach only when CDP exposes one unambiguous context; never select a tab."""

    if playwright_factory is None:
        from playwright.sync_api import sync_playwright

        playwright_factory = sync_playwright

    playwright = playwright_factory().start()
    try:
        browser = playwright.chromium.connect_over_cdp(endpoint)
        contexts = tuple(browser.contexts)
        if not browser.is_connected() or len(contexts) != 1:
            raise SecurityViolation("INSO authenticated context is not unique")
        context = contexts[0]
        ownership = (
            BrowserOwnership.APP_OWNED
            if browser_handle.owned
            else BrowserOwnership.REUSED
        )
        normalized_endpoint = endpoint.rstrip("/")

        def disconnect_and_close() -> None:
            try:
                playwright.stop()
            finally:
                browser_handle.close()

        leased_browser = _BrowserHandle(browser, disconnect_and_close)
        leased_context = _ContextHandle(browser, context)
        probe = _IdentityProbe(normalized_endpoint, browser, context)
        lease = InsoSessionLease(
            ownership=ownership,
            browser=leased_browser,
            context=leased_context,
            browser_identity=BrowserIdentity(
                normalized_endpoint, str(id(browser))
            ),
            context_identity=ContextIdentity(str(id(browser)), str(id(context))),
            identity_probe=probe,
            cycle_id=cycle_id,
            cycle_is_drained=cycle_is_drained,
        )
        return InsoResearchSession(lease, playwright, ownership)
    except Exception:
        playwright.stop()
        raise
