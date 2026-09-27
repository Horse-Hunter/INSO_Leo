from __future__ import annotations

from pathlib import Path

import pytest

from src.inso.session import (
    BrowserIdentity,
    BrowserOwnership,
    ContextIdentity,
    InsoSessionLease,
    LeaseState,
    PageIdentity,
    SecurityViolation,
)


class FakePage:
    def __init__(self, context_id: str, target_id: str, *, valid: bool = True) -> None:
        self.context_id = context_id
        self.target_id = target_id
        self.closed = False
        self.valid = valid

    def is_closed(self) -> bool:
        return self.closed

    def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self) -> None:
        self.connected = True
        self.close_count = 0

    def is_connected(self) -> bool:
        return self.connected

    def close(self) -> None:
        self.close_count += 1
        self.connected = False


class FakeContext:
    def __init__(self, browser_id: str, context_id: str) -> None:
        self.browser_id = browser_id
        self.context_id = context_id
        self.closed = False
        self.pages = [
            FakePage(context_id, "verified-shell"),
            FakePage(context_id, "unrelated-tab", valid=False),
        ]

    def is_closed(self) -> bool:
        return self.closed


class FakeIdentityProbe:
    def __init__(self, *, context_id: str | None = None, browser_id: str = "browser-a") -> None:
        self.expected_browser_id = browser_id
        self.expected_context_id = context_id

    def endpoint_id(self, _browser: FakeBrowser) -> str | None:
        return "loopback-cdp-1"

    def browser_id(self, _browser: FakeBrowser) -> str | None:
        return self.expected_browser_id

    def context_id(self, context: FakeContext) -> str | None:
        return self.expected_context_id or context.context_id

    def page_identity(self, page: FakePage) -> PageIdentity | None:
        return PageIdentity(page.context_id, page.target_id)


def make_lease(
    owner: BrowserOwnership,
    *,
    context_id: str = "context-a",
    cycle_drained=lambda _cycle_id: True,
    shell_valid=lambda page: page.valid,
):
    browser = FakeBrowser()
    context = FakeContext("browser-a", context_id)
    shell = context.pages[0]
    lease = InsoSessionLease(
        ownership=owner,
        browser=browser,
        context=context,
        operation_page=shell,
        operation_frame=object(),
        browser_identity=BrowserIdentity("loopback-cdp-1", "browser-a"),
        context_identity=ContextIdentity("browser-a", context_id),
        operation_page_identity=PageIdentity(context_id, "verified-shell"),
        identity_probe=FakeIdentityProbe(),
        operation_page_is_valid=shell_valid,
        cycle_id="cycle-1",
        cycle_is_drained=cycle_drained,
    )
    return lease, browser, context, shell


def test_reused_lease_uses_existing_shell_and_never_closes_any_page() -> None:
    lease, browser, context, shell = make_lease(BrowserOwnership.REUSED)
    unrelated = context.pages[1]
    original_page_count = len(context.pages)

    with lease.adapter_access("duplicate-read").operation_page() as operation:
        assert operation.page is shell
        assert operation.identity == PageIdentity("context-a", "verified-shell")
        assert operation.shell_frame is not None
    lease.close_after_drain()

    assert len(context.pages) == original_page_count
    assert not shell.is_closed()
    assert not unrelated.is_closed()
    assert browser.close_count == 0
    assert lease.state is LeaseState.RELEASED


def test_app_owned_browser_closes_only_after_cycle_drain_and_keeps_shell_page() -> None:
    drained = False
    lease, browser, context, shell = make_lease(
        BrowserOwnership.APP_OWNED, cycle_drained=lambda _cycle: drained
    )
    unrelated = context.pages[1]

    with pytest.raises(SecurityViolation):
        lease.close_after_drain()
    assert browser.close_count == 0

    drained = True
    lease.close_after_drain()
    assert browser.close_count == 1
    assert shell.is_closed() is False
    assert unrelated.is_closed() is False


def test_wrong_context_identity_fails_closed() -> None:
    browser = FakeBrowser()
    context = FakeContext("browser-a", "context-a")
    shell = context.pages[0]
    with pytest.raises(SecurityViolation):
        InsoSessionLease(
            ownership=BrowserOwnership.REUSED,
            browser=browser,
            context=context,
            operation_page=shell,
            operation_frame=object(),
            browser_identity=BrowserIdentity("endpoint", "browser-a"),
            context_identity=ContextIdentity("browser-a", "context-expected"),
            operation_page_identity=PageIdentity("context-a", "verified-shell"),
            identity_probe=FakeIdentityProbe(context_id="context-other"),
            operation_page_is_valid=lambda _page: True,
            cycle_id="cycle-1",
            cycle_is_drained=lambda _cycle_id: True,
        )
    assert browser.close_count == 0


def test_wrong_endpoint_identity_fails_closed() -> None:
    browser = FakeBrowser()
    context = FakeContext("browser-a", "context-a")
    shell = context.pages[0]
    with pytest.raises(SecurityViolation):
        InsoSessionLease(
            ownership=BrowserOwnership.REUSED,
            browser=browser,
            context=context,
            operation_page=shell,
            operation_frame=object(),
            browser_identity=BrowserIdentity("unexpected-endpoint", "browser-a"),
            context_identity=ContextIdentity("browser-a", "context-a"),
            operation_page_identity=PageIdentity("context-a", "verified-shell"),
            identity_probe=FakeIdentityProbe(),
            operation_page_is_valid=lambda _page: True,
            cycle_id="cycle-1",
            cycle_is_drained=lambda _cycle_id: True,
        )
    assert browser.close_count == 0


def test_wrong_shell_identity_invalidates_access() -> None:
    lease, _browser, _context, shell = make_lease(BrowserOwnership.REUSED)
    operation = lease.adapter_access("research").operation_page()
    shell.valid = False

    with pytest.raises(SecurityViolation):
        _ = operation.page
    assert lease.state is LeaseState.INVALIDATED


def test_stale_page_and_stale_browser_invalidate_lease() -> None:
    lease, _browser, _context, shell = make_lease(BrowserOwnership.REUSED)
    operation = lease.adapter_access("research").operation_page()
    shell.close()
    with pytest.raises(SecurityViolation):
        _ = operation.page
    assert lease.state is LeaseState.INVALIDATED

    second, browser, _context, _shell = make_lease(BrowserOwnership.REUSED)
    browser.connected = False
    with pytest.raises(SecurityViolation):
        second.adapter_access("purchase").operation_page()
    assert second.state is LeaseState.INVALIDATED


def test_session_types_do_not_create_or_close_operation_pages() -> None:
    source = Path("src/inso/session.py").read_text(encoding="utf-8")
    assert ".new_page(" not in source
    assert "_OwnedChild" not in source
    assert "operation_page.close(" not in source
    assert "self._browser.close()" in source
