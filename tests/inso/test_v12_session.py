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
    def __init__(self, context_id: str, target_id: str) -> None:
        self.context_id = context_id
        self.target_id = target_id
        self.closed = False

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
        self.pages = [FakePage(context_id, "unrelated-original-tab")]
        self._next = 0

    def is_closed(self) -> bool:
        return self.closed

    def new_page(self) -> FakePage:
        self._next += 1
        page = FakePage(self.context_id, f"operation-child-{self._next}")
        self.pages.append(page)
        return page


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
    cycle_drained: bool = True,
):
    browser = FakeBrowser()
    context = FakeContext("browser-a", context_id)
    lease = InsoSessionLease(
        ownership=owner,
        browser=browser,
        context=context,
        browser_identity=BrowserIdentity("loopback-cdp-1", "browser-a"),
        context_identity=ContextIdentity("browser-a", context_id),
        identity_probe=FakeIdentityProbe(),
        cycle_id="cycle-1",
        cycle_is_drained=lambda _cycle_id: cycle_drained,
    )
    return lease, browser, context


def test_reused_browser_and_unrelated_tab_stay_open_child_page_is_operation_owned() -> None:
    lease, browser, context = make_lease(BrowserOwnership.REUSED)
    unrelated = context.pages[0]
    access = lease.adapter_access("duplicate-read")

    with access.open_operation_page() as owned:
        child = owned.page
        assert owned.identity.context_id == "context-a"
        assert child is not unrelated
        assert not child.is_closed()
    assert child.is_closed()
    assert not unrelated.is_closed()

    lease.close_after_drain()
    assert browser.close_count == 0
    assert not unrelated.is_closed()
    assert lease.state is LeaseState.RELEASED


def test_app_owned_browser_closes_only_after_child_pages_drain() -> None:
    lease, browser, context = make_lease(BrowserOwnership.APP_OWNED)
    unrelated = context.pages[0]
    child = lease.adapter_access("research").open_operation_page()

    with pytest.raises(SecurityViolation):
        lease.close_after_drain()
    assert browser.close_count == 0

    child.close()
    lease.close_after_drain()
    assert browser.close_count == 1
    assert not unrelated.is_closed()


def test_app_owned_browser_requires_composition_root_cycle_drain() -> None:
    lease, browser, _ = make_lease(BrowserOwnership.APP_OWNED, cycle_drained=False)
    with pytest.raises(SecurityViolation):
        lease.close_after_drain()
    assert browser.close_count == 0
    assert lease.state is LeaseState.ACTIVE


def test_wrong_context_identity_fails_closed() -> None:
    browser = FakeBrowser()
    context = FakeContext("browser-a", "context-a")
    with pytest.raises(SecurityViolation):
        InsoSessionLease(
            ownership=BrowserOwnership.REUSED,
            browser=browser,
            context=context,
            browser_identity=BrowserIdentity("endpoint", "browser-a"),
            context_identity=ContextIdentity("browser-a", "context-expected"),
            identity_probe=FakeIdentityProbe(context_id="context-other"),
            cycle_id="cycle-1",
            cycle_is_drained=lambda _cycle_id: True,
        )
    assert browser.close_count == 0


def test_wrong_endpoint_identity_fails_closed() -> None:
    browser = FakeBrowser()
    context = FakeContext("browser-a", "context-a")
    with pytest.raises(SecurityViolation):
        InsoSessionLease(
            ownership=BrowserOwnership.REUSED,
            browser=browser,
            context=context,
            browser_identity=BrowserIdentity("unexpected-endpoint", "browser-a"),
            context_identity=ContextIdentity("browser-a", "context-a"),
            identity_probe=FakeIdentityProbe(),
            cycle_id="cycle-1",
            cycle_is_drained=lambda _cycle_id: True,
        )
    assert browser.close_count == 0


def test_stale_page_and_stale_browser_invalidate_lease() -> None:
    lease, _browser, _context = make_lease(BrowserOwnership.REUSED)
    operation = lease.adapter_access("research").open_operation_page()
    page = operation.page
    page.close()

    with pytest.raises(SecurityViolation):
        _ = operation.page
    assert lease.state is LeaseState.INVALIDATED

    second, browser, _ = make_lease(BrowserOwnership.REUSED)
    browser.connected = False
    with pytest.raises(SecurityViolation):
        second.adapter_access("purchase").open_operation_page()
    assert second.state is LeaseState.INVALIDATED


def test_already_closed_owned_child_drains_only_its_own_lease_entry() -> None:
    lease, browser, context = make_lease(BrowserOwnership.APP_OWNED)
    unrelated = context.pages[0]
    operation = lease.adapter_access("research").open_operation_page()
    child = operation.page
    child.close()
    operation.close()
    lease.close_after_drain()
    assert browser.close_count == 1
    assert unrelated.is_closed() is False


def test_session_types_never_discover_first_or_global_pages() -> None:
    source = Path("src/research/inso_history.py").read_text(encoding="utf-8")
    assert "connect_over_cdp" not in source
    assert "browser.close(" not in source
    assert "next((p for p in pages" not in source
    assert "for ctx in browser.contexts" not in source
