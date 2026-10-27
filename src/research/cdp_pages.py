"""Create CDP tabs without raising the Owner's Chrome window."""

from __future__ import annotations

import logging
import re
import threading
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


class PageTargetCreationUncertain(PageTargetCleanupError):
    """Chrome may have created a target but returned no usable target ID."""

    reason = "CDP_PAGE_CREATION_UNCONFIRMED"


class PageTargetOwnershipError(PageTargetCleanupError):
    reason = "CDP_PAGE_OWNERSHIP_UNCONFIRMED"


class PageResourceAdmission:
    """One injected, fail-closed admission shared by attached clients.

    Contains sanitized fault metadata only; never Playwright objects. A reconnect
    cannot clear uncertainty. Reconciliation requires a new reviewed lifecycle.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._failure = None

    def invalidate(self, error):
        with self._lock:
            if self._failure is None:
                self._failure = type(error), error.failure_classes

    def require_open(self):
        with self._lock:
            failure = self._failure
        if failure is not None:
            kind, classes = failure
            error = kind(())
            error.failure_classes = classes
            raise error


def bind_page_admission(browser, admission):
    """All clients of one runtime must bind the same admission before use."""
    old = getattr(browser, "_inso_page_admission", None)
    if old is not None and old is not admission:
        error = PageTargetOwnershipError((ValueError("CDP_ADMISSION_REBIND_REFUSED"),))
        admission.invalidate(error)
        if isinstance(old, PageResourceAdmission):
            old.invalidate(error)
        browser._inso_page_resource_failed = True
        raise error
    browser._inso_page_admission = admission
    if getattr(browser, "_inso_page_resource_failed", False) is True:
        admission.invalidate(PageTargetCleanupError(()))
    admission.require_open()


def _invalidate_page_resource(browser, error):
    browser._inso_page_resource_failed = True
    admission = getattr(browser, "_inso_page_admission", None)
    if isinstance(admission, PageResourceAdmission):
        admission.invalidate(error)


def _native_page_owner(page, lease):
    target_id, owner, context, browser = lease
    admission = getattr(browser, "_inso_page_admission", None)
    if isinstance(admission, PageResourceAdmission):
        admission.require_open()
    session = None
    try:
        session = context.new_cdp_session(page)
        actual = session.send("Target.getTargetInfo")["targetInfo"]["targetId"]
        if actual != target_id:
            raise ValueError("TAB_TARGET_ID_MISMATCH")
    except Exception as failure:
        error = PageTargetOwnershipError((failure,))
        _invalidate_page_resource(browser, error)
        raise error from failure
    finally:
        if session is not None:
            try:
                session.detach()
            except Exception as failure:
                error = PageTargetCleanupError((failure,))
                _invalidate_page_resource(browser, error)
                raise error from failure
    if isinstance(admission, PageResourceAdmission):
        admission.require_open()
    return owner


def native_page_owner(page: Any) -> str | None:
    """Verify this client's factory-created target without evaluating its document.

    Explicit read-only actor capability. Does not replace legacy write-surface
    marker checks: clearing a Google/INSO marker must still quarantine that page.
    """
    if page.is_closed():
        return None
    lease = getattr(page, "_inso_native_page_owner", None)
    if lease is None:
        raise PageTargetOwnershipError((ValueError("NATIVE_PAGE_LEASE_MISSING"),))
    return _native_page_owner(page, lease)


def page_owner(page: Any) -> str | None:
    """Read the legacy review/write-surface ownership marker, fail as before."""
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

    def __init__(self, browser: Any, admission=None, delegate=None) -> None:
        self._browser, self._admission, self._delegate = browser, admission, delegate

    def connect_over_cdp(self, _url: str, **_kwargs: Any) -> Any:
        if self._admission is not None:
            self._admission.require_open()
        browser = (self._browser if self._browser is not None else
                   self._delegate.connect_over_cdp(_url, **_kwargs))
        if self._admission is not None:
            bind_page_admission(browser, self._admission)
        return browser


class _SharedPlaywright:
    """Playwright-shaped facade around an existing CDP attachment.

    Playwright's synchronous API cannot be started twice in one thread, so a
    launcher that already holds a CDP Playwright instance must let the
    browser-backed research sources share it. This facade makes each client's
    existing ``playwright.chromium.connect_over_cdp(url)`` call return the shared
    browser instead of opening a second connection, and never stops the shared
    instance on exit.
    """

    def __init__(self, browser: Any, admission=None, owned_factory=None) -> None:
        self._browser, self._admission, self._owned_factory = browser, admission, owned_factory
        self.chromium = _SharedChromium(browser, admission)

    def __enter__(self) -> Self:
        if self._admission is not None:
            self._admission.require_open()
        if self._owned_factory is not None:
            playwright = self._owned_factory.__enter__()
            self.chromium = _SharedChromium(None, self._admission, playwright.chromium)
        return self

    def __exit__(self, *_exc: object) -> bool:
        if self._owned_factory is not None:
            return self._owned_factory.__exit__(*_exc)
        return False


def shared_playwright_factory(
    provider: Callable[[], tuple[Any, Any] | None] | None,
    *, admission: PageResourceAdmission | None = None,
) -> Callable[[], object]:
    """Build a ``playwright_factory`` that reuses a shared CDP attachment.

    ``provider`` is resolved on each call because the launcher may become ready
    only after the research service has been composed. It returns the live
    ``(playwright, browser)`` pair, or ``None`` when there is nothing to reuse --
    in which case the client falls back to its own connection, which is the
    correct behaviour outside the launcher.
    """

    def factory() -> object:
        if admission is not None:
            admission.require_open()
        shared = provider() if callable(provider) else provider
        if shared is not None:
            playwright, browser = shared
            if playwright is not None and browser is not None:
                try:
                    if browser.is_connected():
                        return _SharedPlaywright(browser, admission)
                except Exception as exc:  # noqa: BLE001 - a failed attach is retried, not fatal
                    _LOG.debug(
                        "shared CDP browser is not reusable (%s)", type(exc).__name__
                    )
        from playwright.sync_api import sync_playwright

        if admission is not None:
            return _SharedPlaywright(None, admission, sync_playwright())
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

    admission = getattr(browser, "_inso_page_admission", None)
    if isinstance(admission, PageResourceAdmission):
        admission.require_open()
    if getattr(browser, "_inso_page_resource_failed", False) is True:
        raise PageTargetCleanupError(())
    if owner is not None and not re.fullmatch(r"[a-z][a-z0-9-]{1,40}", owner):
        raise ValueError("INVALID_TAB_OWNER")
    # A task/site owner is not unique per creation. Match a random creation URL
    # first, then prove the Page's native targetId before touching its document.
    initial_url = "about:blank#INSO_CREATE:" + uuid4().hex
    session = browser.new_browser_cdp_session()
    target_id: str | None = None
    creation_attempted = False
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
            creation_attempted = True
            target_id = session.send("Target.createTarget", params)["targetId"]
            if not isinstance(target_id, str) or not target_id:
                target_id = None
                raise ValueError("CDP_TARGET_ID_MISSING")
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
        # guards. Native identity below survives document/context transitions;
        # window.name remains only a compatibility/review-page marker.
        page.evaluate("() => history.replaceState(null, '', 'about:blank')")
        if isinstance(admission, PageResourceAdmission):
            admission.require_open()
        if owner is not None:
            page._inso_native_page_owner = (target_id, owner, context, browser)
        return page
    except BaseException as exc:
        failure = exc
        if creation_attempted and target_id is None:
            error = PageTargetCreationUncertain((exc,))
            _invalidate_page_resource(browser, error)
            raise error from exc
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
            error = PageTargetCleanupError(cleanup_failures)
            _invalidate_page_resource(browser, error)
            raise error from (failure or cleanup_failures[0])
