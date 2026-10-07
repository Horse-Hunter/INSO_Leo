from types import SimpleNamespace

import pytest

from src.launcher.google_quote_update import (
    GoogleQuotationUpdateActions,
    build_v13_quotation_updater,
)
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_quote_update import UpdateAttemptUnconfirmed
from tests.sheets.test_quotation_input import location


class Locator:
    def __init__(self, page, role, name):
        self.page, self.role, self.name = page, role, name
    def count(self):
        if self.role == "text":
            return int(self.name in self.page.login_markers)
        if self.role == "dialog":
            return int(bool(self.page.popup))
        return 1
    def click(self, **kwargs):
        self.page.clicks.append(self.name)
        if self.name == "更新报价":
            self.page.popup = "报价更新完成\n成功填入：1行"
        else:
            self.page.popup = None
    def wait_for(self, **kwargs):
        if not self.page.popup:
            raise TimeoutError("missing popup")
    def inner_text(self, **kwargs):
        return self.page.popup
    def get_by_role(self, role, *, name, exact):
        return Locator(self.page, role, name)


class Page:
    def __init__(self, context):
        self.context, self.closed = context, False
        self.url, self.popup = "about:blank", None
        self.login_markers, self.clicks = set(), []
    def goto(self, url, **kwargs):
        self.url = url
    def get_by_role(self, role, *, name, exact):
        assert exact and role in {"button", "dialog"}
        return Locator(self, role, name)
    def get_by_text(self, text, *, exact):
        assert exact
        return Locator(self, "text", text)
    def is_closed(self):
        return self.closed
    def close(self):
        self.closed = True


class Context:
    def __init__(self):
        self.pages = [Page(self)]
    def new_page(self):
        page = Page(self)
        self.pages.append(page)
        return page


class Browser:
    def __init__(self):
        self.contexts, self.connected = [Context()], True
    def is_connected(self):
        return self.connected


def adapter():
    browser = Browser()
    handle = SimpleNamespace(owned=False, browser=browser)
    return GoogleQuotationUpdateActions(browser_handle=handle, location=location()), browser


def test_fresh_google_surface_submit_exact_roles_popup_dismiss_only_owned_tab():
    actions, browser = adapter()
    owner_page = browser.contexts[0].pages[0]
    actions.open_quote_input()
    first = browser.contexts[0].pages[-1]
    assert first.url == location().url
    actions.click_update_quote()
    assert actions.read_update_result().startswith("报价更新完成")
    actions.dismiss_result()
    assert first.clicks == ["更新报价", "确定"]
    actions.close()
    assert first.closed and not owner_page.closed and browser.connected
    actions.open_quote_input()
    second = browser.contexts[0].pages[-1]
    assert first is not second
    actions.close()
    assert second.closed and not owner_page.closed


@pytest.mark.parametrize("auth", ["accounts", "登录", "Verify it's you", "请求访问权限"])
def test_login_or_manual_challenge_retained_through_close(auth):
    actions, browser = adapter()
    actions.open_quote_input()
    page = browser.contexts[0].pages[-1]
    if auth == "accounts":
        page.url = "https://accounts.google.com/signin"
    else:
        page.login_markers.add(auth)
    with pytest.raises(V12Fault) as raised:
        actions.click_update_quote()
    assert raised.value.scope is FaultScope.GLOBAL_STOP
    actions.close()
    assert not page.closed and browser.connected
    assert page.clicks == []
    with pytest.raises(V12Fault):
        actions.open_quote_input()


def test_challenge_appearing_during_api_work_is_not_closed_by_final_cleanup():
    actions, browser = adapter()
    actions.open_quote_input()
    page = browser.contexts[0].pages[-1]
    page.url = "https://accounts.google.com/signin"
    actions.close()
    assert not page.closed and browser.connected


def test_old_popup_is_never_accepted_as_new_submission():
    actions, browser = adapter()
    actions.open_quote_input()
    page = browser.contexts[0].pages[-1]
    page.popup = "报价更新完成 成功填入：1行"
    with pytest.raises(UpdateAttemptUnconfirmed):
        actions.click_update_quote()
    assert page.clicks == []
    actions.close()
    assert page.closed


def test_no_popup_is_recoverable_but_disconnected_cdp_is_shared_fault():
    actions, browser = adapter()
    actions.open_quote_input()
    with pytest.raises(UpdateAttemptUnconfirmed):
        actions.read_update_result()
    browser.connected = False
    with pytest.raises(V12Fault) as raised:
        actions.click_update_quote()
    assert raised.value.scope is FaultScope.GLOBAL_STOP


def test_factory_reuses_supplied_capabilities_without_accessing_service_or_browser():
    handle = SimpleNamespace(owned=False)
    updater = build_v13_quotation_updater(service=object(), source_reader=object(), store=object(),
        browser_handle=handle, location=location(), wait=lambda _: False)
    assert updater._input.location == location()
    assert updater._input._columns[0] == "日期" and updater._input._columns[-1] == "制单人"
    assert not hasattr(updater, "quarantine")


def test_real_ui_adapter_authentication_fault_through_updater_retains_human_tab():
    from src.workflow.v13_quote_update import V13QuotationUpdater
    from tests.workflow.test_v13_quote_update import Input, Source, found
    actions, browser = adapter()
    context = browser.contexts[0]
    new_page = context.new_page
    def challenged_page():
        page = new_page()
        page.goto = lambda *args, **kwargs: setattr(page, "url", "https://accounts.google.com/signin")
        return page
    context.new_page = challenged_page
    io = Input()
    updater = V13QuotationUpdater(source=Source(), quotation_input=io, actions=actions, wait=lambda _: False)
    with pytest.raises(V12Fault) as raised:
        updater.update_one(found())
    assert raised.value.scope is FaultScope.GLOBAL_STOP
    assert raised.value.reason == "GOOGLE_AUTHENTICATION_REQUIRED"
    assert io.writes == []
    assert len(context.pages) == 2 and all(not page.closed for page in context.pages)
    assert browser.connected


def test_last_owned_tab_cleanup_retains_blank_before_closing():
    actions, browser = adapter()
    actions.open_quote_input()
    context = browser.contexts[0]
    owned = context.pages[-1]
    context.pages[0].close()
    actions.close()
    live = [page for page in context.pages if not page.closed]
    assert owned.closed and len(live) == 1 and live[0].url == "about:blank" and browser.connected


def test_initial_navigation_hang_is_safe_retry_not_shared_auth_fault():
    actions, browser = adapter()
    context = browser.contexts[0]
    new_page = context.new_page
    def hung_page():
        page = new_page()
        def timeout(*args, **kwargs):
            raise TimeoutError("navigation did not settle")
        page.goto = timeout
        return page
    context.new_page = hung_page
    with pytest.raises(UpdateAttemptUnconfirmed):
        actions.open_quote_input()
    actions.close()
    assert context.pages[-1].closed and not context.pages[0].closed and browser.connected
