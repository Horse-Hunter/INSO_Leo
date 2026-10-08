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
        if self.role == "text" and self.name == "正在运行脚本":
            return int(self.page.script_running)
        if self.role == "text":
            return int(self.page.menu_ready) if self.name == "报价工具" else int(self.name in self.page.login_markers)
        if self.role == "drawing":
            return self.page.drawings
        if self.role == "button" and self.name == "更新报价":
            return self.page.update_buttons
        if self.role == "dialog":
            return int(bool(self.page.popup) and (not hasattr(self, "pattern") or bool(self.pattern.search(self.page.popup))))
        return 1
    def filter(self, *, has_text):
        self.pattern = has_text
        return self
    def evaluate(self, script, **kwargs):
        assert "MutationObserver" in script and "addEventListener('click'" in script
        self.page.armed = True
    def click(self, **kwargs):
        if self.name == "确定":
            assert self.page.armed
            self.page.confirmed = True
        self.page.clicks.append(self.name)
        if self.name == "更新报价":
            self.page.popup = "报价更新完成\n成功填入：1行"
        else:
            self.page.popup = None
    def wait_for(self, **kwargs):
        if self.role == "text" and self.name == "正在运行脚本":
            self.page.script_waits.append(kwargs)
            if self.page.script_stuck:
                raise TimeoutError("script still running")
            self.page.script_running = False
            return
        if self.role == "dialog":
            self.page.result_waits.append(kwargs["timeout"])
        if self.role == "text" and self.name == "报价工具":
            self.page.ready_waits.append(kwargs["timeout"])
            if self.page.menu_failure:
                raise TimeoutError("script menu not ready")
            self.page.menu_ready = True
            return
        if self.role == "drawing" and self.page.drawings == 1:
            return
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
        self.update_buttons, self.drawings = 1, 0
        self.menu_ready, self.menu_failure, self.ready_waits = True, False, []
        self.result_waits = []
        self.script_running, self.script_stuck, self.script_waits = True, False, []
        self.armed = self.confirmed = self.started = self.settled = False
        self.script_never_starts = False
    def wait_for_function(self, script, **kwargs):
        state = "settled" if ".settled" in script else "started"
        self.script_waits.append({"state": state, **kwargs})
        assert self.armed and self.confirmed
        if state == "started":
            if self.script_never_starts:
                raise TimeoutError("never started")
            self.script_running = self.started = True
        else:
            assert self.started
            if self.script_stuck:
                raise TimeoutError("never settled")
            self.script_running = False
            self.settled = True
    def evaluate(self, script):
        assert self.started and self.settled
    def goto(self, url, **kwargs):
        self.url = url
    def get_by_role(self, role, *, name=None, exact=None):
        assert role in {"button", "dialog"}
        return Locator(self, role, name)
    def locator(self, selector):
        assert selector == 'div.waffle-borderless-embedded-object-overlay[aria-label="绘图："]:visible'
        return Locator(self, "drawing", "更新报价")
    def get_by_text(self, text, *, exact):
        assert exact or text == "正在运行脚本"
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
        from tests.research.background_targets import attach_background_protocol
        attach_background_protocol(self.contexts[0], self)
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


@pytest.mark.parametrize("visible_count", [0, 1, 2])
def test_verified_drawing_requires_exactly_one_visible_target_before_write(visible_count):
    actions, browser = adapter()
    context = browser.contexts[0]
    def fresh():
        page = Page(context)
        page.update_buttons, page.drawings = 0, visible_count
        context.pages.append(page)
        return page
    context.new_page = fresh
    if visible_count != 1:
        with pytest.raises(UpdateAttemptUnconfirmed):
            actions.open_quote_input()
        assert context.pages[-1].clicks == []
    else:
        actions.open_quote_input()
        actions.click_update_quote()
        assert context.pages[-1].clicks == ["更新报价"]
        assert actions.read_update_result().startswith("报价更新完成")
    actions.close()


@pytest.mark.parametrize("fails", [False, True])
def test_drawing_shell_cannot_click_before_script_menu_ready(fails):
    actions, browser = adapter()
    context = browser.contexts[0]
    def fresh():
        page = Page(context)
        page.update_buttons, page.drawings = 0, 1
        page.menu_ready, page.menu_failure = False, fails
        context.pages.append(page)
        return page
    context.new_page = fresh
    if fails:
        with pytest.raises(UpdateAttemptUnconfirmed):
            actions.open_quote_input()
        assert context.pages[-1].clicks == []
    else:
        actions.open_quote_input()
        page = context.pages[-1]
        assert page.menu_ready and page.ready_waits == [30000]
        actions.click_update_quote()
        assert page.clicks == ["更新报价"]
    actions.close()


def test_live_unnamed_dialog_is_read_dismissed_and_rejected_if_stale():
    actions, browser = adapter()
    actions.open_quote_input()
    page = browser.contexts[0].pages[-1]
    page.popup = "更新完成\n成功填入：0 行\n已有价跳过：1 行\n确定"
    with pytest.raises(UpdateAttemptUnconfirmed, match="UPDATE_RESULT_STALE"):
        actions.click_update_quote()
    assert page.clicks == []
    assert actions.read_update_result() == page.popup
    assert page.result_waits == [30000]
    actions.dismiss_result()
    assert page.popup is None and page.clicks == ["确定"]
    assert page.script_waits == [{"state": "started", "timeout": 30000},
                                 {"state": "settled", "timeout": 30000}]
    assert not page.script_running
    actions.close()


def test_script_settlement_timeout_preserves_surface_and_prevents_next_row():
    actions, browser = adapter()
    actions.open_quote_input()
    page = browser.contexts[0].pages[-1]
    page.popup = "更新完成 成功填入：0行 已有价跳过：1行"
    page.script_stuck = True
    with pytest.raises(V12Fault) as fault:
        actions.dismiss_result()
    assert fault.value.scope is FaultScope.GLOBAL_STOP
    assert fault.value.reason == "GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED"
    actions.close()
    assert not page.closed and browser.connected
    with pytest.raises(V12Fault, match="GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED"):
        actions.open_quote_input()
    assert page.clicks == ["确定"]


@pytest.mark.parametrize("initial_running", [True, False])
def test_settlement_proves_start_then_end_even_if_initially_absent(initial_running):
    actions, browser = adapter()
    actions.open_quote_input()
    page = browser.contexts[0].pages[-1]
    page.popup = "更新完成 成功填入：0行 已有价跳过：1行"
    page.script_running = initial_running
    actions.dismiss_result()
    assert page.started and page.settled and not actions._script_pending
    actions.close()
    actions.open_quote_input()
    assert page.closed and browser.contexts[0].pages[-1] is not page


def test_never_observed_start_is_not_settlement_and_blocks_next_surface():
    actions, browser = adapter()
    actions.open_quote_input()
    page = browser.contexts[0].pages[-1]
    page.popup = "更新完成 成功填入：0行 已有价跳过：1行"
    page.script_running = False
    page.script_never_starts = True
    with pytest.raises(V12Fault, match="GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED"):
        actions.dismiss_result()
    assert actions._script_pending and not page.started
    actions.close()
    with pytest.raises(V12Fault, match="GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED"):
        actions.open_quote_input()
    with pytest.raises(V12Fault, match="GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED"):
        actions.click_update_quote()
    assert not page.closed and page.clicks == ["确定"]


def test_cdp_error_during_settlement_maps_to_settlement_stop_and_preserves_page():
    actions, browser = adapter()
    actions.open_quote_input()
    page = browser.contexts[0].pages[-1]
    page.popup = "更新完成 成功填入：1行"
    def failed(*a, **kw):
        raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE")
    page.wait_for_function = failed
    with pytest.raises(V12Fault, match="GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED"):
        actions.dismiss_result()
    actions.close()
    assert actions._script_pending and not page.closed
