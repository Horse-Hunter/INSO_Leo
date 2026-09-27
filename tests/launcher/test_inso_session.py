from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from src.inso.session import SecurityViolation
from src.launcher.inso_session import attach_inso_research_session


class FakeLocator:
    def __init__(self, count: int = 1, visible: bool = True) -> None:
        self._count = count
        self._visible = visible

    def count(self) -> int:
        return self._count

    def is_visible(self) -> bool:
        return self._visible


class FakeFrame:
    def __init__(self, url: str, *, shell: bool = False) -> None:
        self.url = url
        self.name = "main" if shell else ""
        self._shell = shell

    def locator(self, _selector: str) -> FakeLocator:
        return FakeLocator(1 if self._shell else 0)


class FakePage:
    def __init__(self, context, *, shell: bool = False) -> None:
        self.context = context
        self.closed = False
        self.main_frame = FakeFrame("https://yingsuo.alperp.cn/", shell=shell)
        self.frames = [self.main_frame]
        if shell:
            self.shell_frame = FakeFrame(
                "https://yingsuo.alperp.cn/skins/etaoerp/InnerEnquiry/YeWuXJ/List.aspx",
                shell=True,
            )
            self.frames.append(self.shell_frame)

    def is_closed(self) -> bool:
        return self.closed


class FakeContext:
    def __init__(self, *, shell_pages: int = 1) -> None:
        self.pages = [FakePage(self, shell=False)]
        self.pages.extend(FakePage(self, shell=True) for _ in range(shell_pages))


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
    disconnect_count: int = 0

    def close(self) -> None:
        self.close_count += 1

    def disconnect(self) -> None:
        self.disconnect_count += 1


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


def test_reused_session_uses_verified_shell_and_leaves_all_pages_open() -> None:
    context = FakeContext()
    browser = FakeBrowser([context])
    browser_handle = FakeBrowserHandle(owned=False)
    unrelated_page, shell_page = context.pages
    session, playwright = attach(browser, browser_handle)

    with session.operation_access().operation_page() as operation:
        assert operation.page is shell_page
        assert operation.shell_frame is shell_page.shell_frame
    session.close_after_drain()

    assert all(not page.is_closed() for page in context.pages)
    assert browser.connected is True
    assert browser_handle.close_count == 0
    assert browser_handle.disconnect_count == 1
    assert playwright.stop_count == 0
    assert unrelated_page.is_closed() is False


def test_login_redirect_and_wrong_origin_are_not_shell_candidates() -> None:
    for invalid in ("https://yingsuo.alperp.cn/login.aspx", "https://example.invalid/"):
        context = FakeContext()
        context.pages[1].main_frame.url = invalid
        browser = FakeBrowser([context])
        with pytest.raises(SecurityViolation):
            attach(browser, FakeBrowserHandle(owned=False))
        assert all(not page.is_closed() for page in context.pages)


def test_pinned_page_removed_from_context_fails_closed() -> None:
    context = FakeContext()
    browser = FakeBrowser([context])
    session, _ = attach(browser, FakeBrowserHandle(owned=False))
    operation = session.operation_access().operation_page()
    context.pages.remove(context.pages[1])

    with pytest.raises(SecurityViolation):
        _ = operation.page


def test_ambiguous_context_fails_closed_without_closing_any_page() -> None:
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


def test_missing_or_multiple_verified_shells_fail_closed() -> None:
    for context in (FakeContext(shell_pages=0), FakeContext(shell_pages=2)):
        browser = FakeBrowser([context])
        with pytest.raises(SecurityViolation):
            attach(browser, FakeBrowserHandle(owned=False))
        assert all(not page.is_closed() for page in context.pages)


def test_shell_identity_change_fails_closed_before_next_operation() -> None:
    context = FakeContext()
    browser = FakeBrowser([context])
    session, _ = attach(browser, FakeBrowserHandle(owned=False))
    operation = session.operation_access().operation_page()
    shell_page = context.pages[1]
    shell_page.frames = [shell_page.main_frame]

    with pytest.raises(SecurityViolation):
        _ = operation.page


def test_app_owned_browser_closes_only_after_cycle_drain() -> None:
    browser = FakeBrowser([FakeContext()])
    browser_handle = FakeBrowserHandle(owned=True)
    drained = False
    session, _playwright = attach(browser, browser_handle, lambda _cycle: drained)
    pages = tuple(browser.contexts[0].pages)

    with pytest.raises(SecurityViolation):
        session.close_after_drain()
    assert browser_handle.close_count == 0

    drained = True
    session.close_after_drain()
    assert browser_handle.close_count == 1
    assert all(not page.is_closed() for page in pages)
