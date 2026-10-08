"""Create CDP tabs without raising the Owner's Chrome window."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Self

_LOG = logging.getLogger(__name__)


class _SharedChromium:
    """Chromium-shaped facade that hands back the already-attached browser."""

    def __init__(self, browser: Any) -> None:
        self._browser = browser

    def connect_over_cdp(self, _url: str, **_kwargs: Any) -> Any:
        return self._browser


class _SharedPlaywright:
    """Playwright-shaped facade around an existing CDP attachment.

    Playwright's synchronous API cannot be started twice in one thread, so a
    launcher that already holds a CDP Playwright instance must let the
    browser-backed research sources share it. This facade makes each client's
    existing ``playwright.chromium.connect_over_cdp(url)`` call return the shared
    browser instead of opening a second connection, and never stops the shared
    instance on exit.
    """

    def __init__(self, browser: Any) -> None:
        self._browser = browser
        self.chromium = _SharedChromium(browser)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False


def shared_playwright_factory(
    provider: Callable[[], tuple[Any, Any] | None] | None,
) -> Callable[[], object]:
    """Build a ``playwright_factory`` that reuses a shared CDP attachment.

    ``provider`` is resolved on each call because the launcher may become ready
    only after the research service has been composed. It returns the live
    ``(playwright, browser)`` pair, or ``None`` when there is nothing to reuse --
    in which case the client falls back to its own connection, which is the
    correct behaviour outside the launcher.
    """

    def factory() -> object:
        shared = provider() if callable(provider) else provider
        if shared is not None:
            playwright, browser = shared
            if playwright is not None and browser is not None:
                try:
                    if browser.is_connected():
                        return _SharedPlaywright(browser)
                except Exception as exc:  # noqa: BLE001 - a failed attach is retried, not fatal
                    _LOG.debug(
                        "shared CDP browser is not reusable (%s)", type(exc).__name__
                    )
        from playwright.sync_api import sync_playwright

        return sync_playwright()

    return factory


def new_background_page(
    browser: Any,
    context: Any,
    *,
    timeout_ms: int,
    browser_context_id: str | None = None,
) -> Any:
    """Return a tab in the attached context without foreground activation.

    Playwright ``context.new_page`` focuses Chrome and can restore a minimized
    dedicated window. CDP's background target preserves its window state.
    """

    session = browser.new_browser_cdp_session()
    target_id: str | None = None
    try:
        with context.expect_page(timeout=timeout_ms) as pending:
            params = {"url": "about:blank", "background": True}
            # A windowless bootstrap has no existing tab/window to reuse.
            # Ask Chrome to create that first window minimized, rather than
            # creating a normal window and hiding it after a visible flash.
            if not context.pages:
                params.update(newWindow=True, windowState="minimized")
            if browser_context_id is not None:
                params["browserContextId"] = browser_context_id
            target_id = session.send("Target.createTarget", params)["targetId"]
        return pending.value
    except Exception:
        if target_id is not None:
            session.send("Target.closeTarget", {"targetId": target_id})
        raise
    finally:
        session.detach()
