"""Create CDP tabs without raising the Owner's Chrome window."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any, Self
from uuid import uuid4

_LOG = logging.getLogger(__name__)


_OWNER_PREFIX = "INSO_OWNER_TAB:"


class PageTargetCleanupError(RuntimeError):
    """The client cannot safely reuse its page resources after teardown failed."""

    reason = "CDP_PAGE_CLEANUP_UNCONFIRMED"

    def __init__(self, failures):
        super().__init__(self.reason)
        self.failure_classes = tuple(type(exc).__name__ for exc in failures)


def page_owner(page: Any) -> str | None:
    """Browser-visible ownership survives CDP clients/threads and navigation."""
    if page.is_closed():
        return None
    url = str(getattr(page, "url", ""))
    if url.startswith("about:blank#" + _OWNER_PREFIX):
        return url.split("#", 1)[1][len(_OWNER_PREFIX):]
    evaluate = getattr(page, "evaluate", None)
    name = evaluate("() => window.name") if callable(evaluate) else None
    if isinstance(name, str) and name.startswith(_OWNER_PREFIX):
        return name[len(_OWNER_PREFIX):]
    return None


def mark_owned_page(page: Any, owner: str) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,40}", owner):
        raise ValueError("INVALID_TAB_OWNER")
    page.evaluate("name => { window.name = name; }", _OWNER_PREFIX + owner)
    if page_owner(page) != owner:
        raise ValueError("TAB_OWNERSHIP_UNCONFIRMED")


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


def _close_created_target(session, target_id):
    if session.send("Target.closeTarget", {"targetId": target_id}).get("success") is not True:
        raise RuntimeError("CDP_TARGET_CLOSE_UNCONFIRMED")


def new_background_page(
    browser: Any,
    context: Any,
    *,
    timeout_ms: int,
    browser_context_id: str | None = None,
    owner: str | None = None,
) -> Any:
    """Return a tab in the attached context without foreground activation.

    Playwright ``context.new_page`` focuses Chrome and can restore a minimized
    dedicated window. CDP's background target preserves its window state.
    """

    if getattr(browser, "_inso_page_resource_failed", False) is True:
        raise PageTargetCleanupError(())
    if owner is not None and not re.fullmatch(r"[a-z][a-z0-9-]{1,40}", owner):
        raise ValueError("INVALID_TAB_OWNER")
    # A task/site owner is not unique per creation. Match a random creation URL
    # first, then prove the Page's native targetId before touching its document.
    initial_url = "about:blank#INSO_CREATE:" + uuid4().hex
    session = browser.new_browser_cdp_session()
    target_id: str | None = None
    failure = None
    cleanup_failures = []
    try:
        with context.expect_event("page", predicate=lambda page: page.url == initial_url,
                                  timeout=timeout_ms) as pending:
            params = {"url": initial_url, "background": True}
            # A windowless bootstrap has no existing tab/window to reuse.
            # Ask Chrome to create that first window minimized, rather than
            # creating a normal window and hiding it after a visible flash.
            if not context.pages:
                params.update(newWindow=True, windowState="minimized")
            if browser_context_id is not None:
                params["browserContextId"] = browser_context_id
            target_id = session.send("Target.createTarget", params)["targetId"]
        page = pending.value
        proof = context.new_cdp_session(page)
        proof_failure = None
        try:
            actual = proof.send("Target.getTargetInfo")["targetInfo"]["targetId"]
            if actual != target_id:
                raise ValueError("TAB_TARGET_ID_MISMATCH")
        except BaseException as exc:
            proof_failure = exc
            raise
        finally:
            try:
                proof.detach()
            except Exception as cleanup:
                cleanup_failures.append(cleanup)
                if proof_failure is None:
                    raise
        if owner is not None:
            mark_owned_page(page, owner)
        # Keep exact about:blank for existing navigation-failure and last-tab
        # guards. Ownership lives in window.name, not the creation fragment.
        page.evaluate("() => history.replaceState(null, '', 'about:blank')")
        return page
    except BaseException as exc:
        failure = exc
        if target_id is not None:
            try:
                _close_created_target(session, target_id)
            except Exception as cleanup:  # noqa: BLE001 - converted to typed resource fault below
                cleanup_failures.append(cleanup)
        raise
    finally:
        try:
            session.detach()
        except Exception as cleanup:  # noqa: BLE001 - converted to typed resource fault below
            cleanup_failures.append(cleanup)
            if failure is None and target_id is not None:
                # A failed detach on the success path still invalidates return.
                try:
                    _close_created_target(session, target_id)
                except Exception as close:  # noqa: BLE001 - converted to typed resource fault below
                    cleanup_failures.append(close)
        if cleanup_failures:
            browser._inso_page_resource_failed = True
            raise PageTargetCleanupError(cleanup_failures) from (failure or cleanup_failures[0])
