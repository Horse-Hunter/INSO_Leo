"""Foreground creation is forbidden at production operation/cleanup boundaries."""
from types import SimpleNamespace

import pytest

from src.launcher import browser_bootstrap, google_quote_update, inso_session
from tests.launcher.test_google_quote_update import Browser, Page, adapter
from tests.launcher.test_inso_session import FakeContext


def forbidden():
    raise AssertionError("foreground new_page must not be called")


def background_spy(monkeypatch, module, browser, context):
    calls = []
    def create(actual_browser, actual_context, *, timeout_ms):
        assert actual_browser is browser and actual_context is context
        assert timeout_ms > 0
        calls.append("background")
        page = Page(context)
        context.pages.append(page)
        return page
    monkeypatch.setattr(module, "new_background_page", create)
    monkeypatch.setattr(context, "new_page", forbidden)
    return calls


def test_quote_open_and_last_tab_cleanup_never_use_foreground_creation(monkeypatch):
    actions, browser = adapter()
    context = browser.contexts[0]
    calls = background_spy(monkeypatch, google_quote_update, browser, context)
    actions.open_quote_input()
    context.pages[0].close()
    actions.close()
    assert calls == ["background", "background"]
    assert actions._page is None
    assert any(page.url == "about:blank" and not page.is_closed() for page in context.pages)


def test_dedicated_park_creates_background_blank_before_closing_tabs(monkeypatch):
    browser = Browser()
    context = browser.contexts[0]
    context.pages[0].url = "https://synthetic.invalid/"
    original = context.pages[0]
    monkeypatch.setattr(original, "evaluate", lambda script: "")  # unowned tab marker
    calls = background_spy(monkeypatch, browser_bootstrap, browser, context)
    browser_bootstrap.park_shared_cdp(browser)
    assert calls == ["background"] and original.closed


@pytest.mark.parametrize("fresh", [False, True])
def test_login_guard_creates_its_owned_tab_in_background(monkeypatch, fresh):
    context = FakeContext(shell_pages=0)
    context.pages = []
    calls = []
    def create(browser, actual_context, *, timeout_ms):
        assert browser is context.browser and actual_context is context
        calls.append("background")
        raise TimeoutError("synthetic creation failure")
    monkeypatch.setattr(inso_session, "new_background_page", create)
    monkeypatch.setattr(context, "new_page", forbidden)
    login = SimpleNamespace(username="synthetic", password="synthetic")
    guard = inso_session.InsoSessionGuard(login=login, context=lambda: context, fresh_page=fresh)
    result = guard.ensure_authenticated()
    assert calls == ["background"]
    assert result.outcome is inso_session.InsoSessionOutcome.DEAD
    assert guard.opened_page is None
