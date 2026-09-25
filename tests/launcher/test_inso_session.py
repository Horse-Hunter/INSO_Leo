from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from src.inso.session import SecurityViolation
from src.launcher.inso_session import attach_inso_research_session


class FakePage:
    def __init__(self, context) -> None:
        self.context = context
        self.closed = False

    def is_closed(self) -> bool:
        return self.closed

    def close(self) -> None:
        self.closed = True


class FakeContext:
    def __init__(self) -> None:
        self.pages = [FakePage(self)]

    def new_page(self) -> FakePage:
        page = FakePage(self)
        self.pages.append(page)
        return page


class FakeBrowser:
    def __init__(self, contexts) -> None:
        self.contexts = contexts
        self.connected = True

    def is_connected(self) -> bool:
        return self.connected


@dataclass
class FakeBrowserHandle:
    owned: bool
    close_count: int = 0

    def close(self) -> None:
        self.close_count += 1


class FakePlaywright:
    def __init__(self, browser) -> None:
        self.chromium = SimpleNamespace(connect_over_cdp=lambda _endpoint: browser)
        self.stop_count = 0

    def start(self):
        return self

    def stop(self) -> None:
        self.stop_count += 1


def attach(browser, browser_handle, drained=lambda _cycle: True):
    playwright = FakePlaywright(browser)
    session = attach_inso_research_session(
        "http://127.0.0.1:9222/",
        browser_handle,
        cycle_id="cycle-1",
        cycle_is_drained=drained,
        playwright_factory=lambda: playwright,
    )
    return session, playwright


def test_reused_browser_keeps_unrelated_tab_and_closes_only_operation_page() -> None:
    context = FakeContext()
    browser = FakeBrowser([context])
    browser_handle = FakeBrowserHandle(owned=False)
    session, playwright = attach(browser, browser_handle)
    unrelated_page = context.pages[0]

    with session.operation_access().open_operation_page() as operation_page:
        assert operation_page.page is context.pages[1]
    session.close_after_drain()

    assert unrelated_page.is_closed() is False
    assert context.pages[1].is_closed() is True
    assert browser.connected is True
    assert browser_handle.close_count == 0
    assert playwright.stop_count == 1


def test_ambiguous_context_fails_closed_without_closing_any_browser() -> None:
    browser = FakeBrowser([FakeContext(), FakeContext()])
    browser_handle = FakeBrowserHandle(owned=False)
    playwright = FakePlaywright(browser)

    with pytest.raises(SecurityViolation):
        attach_inso_research_session(
            "http://127.0.0.1:9222",
            browser_handle,
            cycle_id="cycle-1",
            cycle_is_drained=lambda _cycle: True,
            playwright_factory=lambda: playwright,
        )

    assert playwright.stop_count == 1
    assert browser_handle.close_count == 0
    assert all(not page.is_closed() for context in browser.contexts for page in context.pages)


def test_app_owned_browser_closes_only_after_cycle_drain() -> None:
    browser = FakeBrowser([FakeContext()])
    browser_handle = FakeBrowserHandle(owned=True)
    drained = False
    session, playwright = attach(browser, browser_handle, lambda _cycle: drained)

    with pytest.raises(SecurityViolation):
        session.close_after_drain()
    assert browser_handle.close_count == 0

    drained = True
    session.close_after_drain()
    assert browser_handle.close_count == 1
    assert playwright.stop_count == 1
