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
    def nth(self, index):
        assert index == 0
        return self
    def is_visible(self):
        return bool(self.count()) and self.name not in getattr(self.page, 'hidden_markers', set())
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
        if "__insoRefreshQuietSince" in script:
            assert 'isRunning' in script and '[role="dialog"]' in script
            if (self.script_running or self.popup
                    or (getattr(self, 'initial_update_pending', False) and not self.settled)):
                raise TimeoutError("synthetic script is still using shared input")
            return
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
    def evaluate(self, script, arg=None):
        if script == "() => !!window.__insoQuoteSettlement":
            return self.armed
        if "window.__insoGoogleReadFailed = true" in script:
            self.read_failed = True
            return
        if "window.__insoGoogleReadFailed === true" in script:
            return getattr(self, 'read_failed', False)
        if "document.querySelectorAll('[role=\"dialog\"]')" in script:
            return bool(self.popup or getattr(self, 'refresh_pending', False)
                        or (self.started and self.script_running))
        if "window.__insoRefreshPending = true" in script:
            self.refresh_pending = True
            self.initial_update_pending = "window.__insoQuoteSettlement.initial = true" in script
        elif "window.__insoRefreshPending = false" in script:
            self.refresh_pending = False
        elif "window.__insoRefreshPending === true" in script:
            return getattr(self, "refresh_pending", False)
        elif "window.name = name" in script:
            self.owner_name = arg
        elif "window.name" in script:
            return getattr(self, "owner_name", "")
        else:
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
    assert page.result_waits == [60000]
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
    with pytest.raises(V12Fault) as blocked:
        actions.open_quote_input()
    assert blocked.value.reason == "GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED"
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


def test_production_factory_keeps_model_difference_callback():
    handle = SimpleNamespace(owned=False)
    notices = []
    notify = lambda result, model: notices.append((result, model))
    updater = build_v13_quotation_updater(service=object(), source_reader=object(), store=object(),
        browser_handle=handle, location=location(), wait=lambda _: False, notify_model_difference=notify)
    assert updater._notify_model_difference is notify


@pytest.mark.parametrize('late_dialog', [False, True])
def test_uncertain_refresh_preserves_running_input_then_later_releases_without_update_click(late_dialog):
    from src.sheets.quotation_input import QuotationInputBusy
    actions,browser=adapter()
    owner=browser.contexts[0].pages[0]
    actions.prepare_price_refresh()
    actions.open_quote_input()
    pending=browser.contexts[0].pages[-1]
    actions.click_update_quote()
    pending.popup=None  # No usable result has arrived yet.
    actions.close()
    assert not pending.closed and pending.refresh_pending
    newer=GoogleQuotationUpdateActions(browser_handle=SimpleNamespace(owned=False,browser=browser),location=location())
    with pytest.raises(QuotationInputBusy):
        newer.open_quote_input()
    assert len(browser.contexts[0].pages)==2  # No second writer while script is running.
    assert pending.clicks==['更新报价'] and not owner.closed
    pending.script_running=False
    if late_dialog:
        pending.popup='更新完成\n成功填入：1行'
    newer.open_quote_input()
    assert pending.closed and not owner.closed and browser.connected
    assert pending.clicks==(['更新报价','确定'] if late_dialog else ['更新报价'])
    newer.close()


def test_refresh_native_click_timeout_is_classified_after_dispatch_only():
    from src.workflow.v13_quote_update import UpdateClickUnconfirmed
    actions,browser=adapter()
    actions.prepare_price_refresh()
    actions.open_quote_input()
    page=browser.contexts[0].pages[-1]
    get=page.get_by_role
    def locate(role,*,name=None,exact=None):
        locator=get(role,name=name,exact=exact)
        if role=='button' and name=='更新报价':
            clicked=locator.click
            def timeout(**kwargs):
                clicked(**kwargs)
                raise TimeoutError('native delivery unknown')
            locator.click=timeout
        return locator
    page.get_by_role=locate
    with pytest.raises(UpdateClickUnconfirmed):
        actions.click_update_quote()
    assert page.clicks==['更新报价'] and page.refresh_pending
    actions.close()
    assert not page.closed


def test_preclick_refresh_failure_does_not_mark_dispatch_or_retain_input():
    actions,browser=adapter()
    actions.prepare_price_refresh()
    actions.open_quote_input()
    page=browser.contexts[0].pages[-1]
    page.menu_failure=True
    with pytest.raises(UpdateAttemptUnconfirmed):
        actions.click_update_quote()
    assert not getattr(page,'refresh_pending',False) and not page.clicks
    actions.close()
    assert page.closed



def test_initial_update_click_timeout_is_preserved_and_never_reclicked(monkeypatch):
    from playwright.sync_api import TimeoutError as PageTimeout

    from src.sheets.quotation_input import QuotationInputBusy
    from src.workflow.v13_quote_update import UpdateClickUnconfirmed
    actions, browser = adapter()
    actions.open_quote_input()
    page = actions._page
    click = Locator.click
    def timeout(locator, **kwargs):
        if locator.name == '更新报价':
            page.clicks.append(locator.name)
            raise PageTimeout('synthetic delivered click with missing acknowledgement')
        return click(locator, **kwargs)
    monkeypatch.setattr(Locator, 'click', timeout)
    with pytest.raises(UpdateClickUnconfirmed):
        actions.click_update_quote()
    assert page.refresh_pending and actions._script_pending
    page.popup = None
    page.script_running = False  # Quiet DOM alone cannot settle an unconfirmed initial dispatch.
    actions.close()
    other = GoogleQuotationUpdateActions(browser_handle=SimpleNamespace(owned=False, browser=browser), location=location())
    with pytest.raises(QuotationInputBusy):
        other.open_quote_input()
    assert not page.closed and page.clicks == ['更新报价']



@pytest.mark.parametrize('branch', ['protected', 'unsafe'])
def test_busy_branch_observation_preserves_original_rejection_and_owned_pages(branch, caplog):
    from src.launcher.google_quote_update import (
        _POLL_GOOGLE_PAGES,
        google_operation_scope,
    )
    from src.sheets.quotation_input import QuotationInputBusy
    actions, browser = adapter()
    human = browser.contexts[0].pages[0]
    with google_operation_scope():
        page = actions.open_sheet(select_worksheet=True, worksheet='2026')
        actions.close()
        pool, _ = _POLL_GOOGLE_PAGES.get()
        entry = next(iter(pool.values()))
        if branch == 'protected':
            entry['protected'] = True
            expected = 'google-busy-protected-entry'
        elif branch == 'unsafe':
            page.popup = 'synthetic pending dialog'
            expected = 'google-busy-pooled-unsafe'
        before = tuple(browser.contexts[0].pages)
        second = GoogleQuotationUpdateActions(browser_handle=actions._handle, location=location())
        with pytest.raises(QuotationInputBusy, match='GOOGLE_QUOTATION_INPUT_BUSY'):
            second.open_sheet(select_worksheet=True, worksheet='2026')
        assert expected in [getattr(record, 'inso_step', None) for record in caplog.records]
        assert tuple(browser.contexts[0].pages) == before
        assert not human.closed
        # No page/URL/dialog content is carried in the diagnostic extras.
        assert all(getattr(record, 'inso_cause', None) is None for record in caplog.records
                   if getattr(record, 'inso_step', None) == expected)



def test_failed_owned_read_does_not_block_next_attempt_in_same_scope():
    from src.launcher.google_quote_update import google_operation_scope
    actions, browser = adapter()
    human = browser.contexts[0].pages[0]
    with google_operation_scope(retained={}):
        actions._read_only = True
        failed = actions.open_sheet(select_worksheet=True, worksheet="2026")
        actions.retire_failed_page(read_only=True)
        actions.close()
        next_read = GoogleQuotationUpdateActions(browser_handle=actions._handle, location=location())
        next_read._read_only = True
        recovered = next_read.open_sheet(select_worksheet=True, worksheet="2026")
        assert recovered is not failed and failed.closed and not human.closed
        next_read.close()


def test_failed_owned_read_navigated_to_error_page_recovers_in_same_scope():
    from src.launcher.google_quote_update import google_operation_scope
    actions, browser = adapter()
    human = browser.contexts[0].pages[0]
    with google_operation_scope(retained={}):
        actions._read_only = True
        failed = actions.open_sheet(select_worksheet=True, worksheet="2026")
        actions.close()
        assert not failed.closed
        failed.url = "chrome-error://chromewebdata/"
        next_read = GoogleQuotationUpdateActions(browser_handle=actions._handle, location=location())
        next_read._read_only = True
        recovered = next_read.open_sheet(select_worksheet=True, worksheet="2026")
        assert recovered is not failed and not failed.closed and not human.closed
        next_read.close()
        # The old unverified surface must not grant permission to write.
        from src.sheets.quotation_input import QuotationInputBusy
        from src.workflow.v13_quote_update import UpdateAttemptUnconfirmed
        writer = GoogleQuotationUpdateActions(browser_handle=actions._handle, location=location())
        with pytest.raises((V12Fault, QuotationInputBusy, UpdateAttemptUnconfirmed)):
            writer.open_sheet(select_worksheet=True, worksheet="2026")


def test_nested_task_scopes_may_exceed_three_and_close_only_their_own_pages():
    from contextlib import ExitStack

    from src.launcher.google_quote_update import google_operation_scope
    root, browser = adapter()
    human = browser.contexts[0].pages[0]
    opened = []
    with ExitStack() as scopes:
        for _module in range(7):
            scopes.enter_context(google_operation_scope())
            current = GoogleQuotationUpdateActions(browser_handle=root._handle, location=location())
            page = current.open_sheet(select_worksheet=True, worksheet='2026')
            opened.append(page)
            current.close()  # The active task scope still owns this page.
            assert all(not p.closed for p in opened) and not human.closed
    assert all(p.closed for p in opened) and not human.closed


def test_repeated_nested_scope_completion_does_not_accumulate_pages():
    from src.launcher.google_quote_update import google_operation_scope
    root, browser = adapter()
    human = browser.contexts[0].pages[0]
    with google_operation_scope():
        outer = root.open_sheet(select_worksheet=True, worksheet='2026')
        root.close()
        for _cycle in range(30):
            with google_operation_scope():
                inner = GoogleQuotationUpdateActions(browser_handle=root._handle, location=location())
                child = inner.open_sheet(select_worksheet=True, worksheet='2026')
                inner.close()
                assert not outer.closed and not child.closed
            assert child.closed and not outer.closed
            assert sum(not p.closed for p in browser.contexts[0].pages) == 2
    assert outer.closed and not human.closed


def test_unleased_same_document_page_with_stale_markers_is_never_closed():
    actions, browser = adapter()
    human = browser.contexts[0].pages[0]
    human.url = location().url
    human.owner_name = "INSO_OWNER_TAB:google-operation"
    human.read_failed = True
    actions._read_only = True
    page = actions.open_sheet(select_worksheet=True, worksheet="2026")
    assert page is not human and not human.closed
    actions.close()
    assert not human.closed


def test_protected_failed_page_is_not_closed_after_dialog_clears_and_tab_moves():
    from src.launcher.google_quote_update import google_operation_scope
    from src.sheets.quotation_input import QuotationInputBusy
    from src.workflow.v13_quote_update import UpdateAttemptUnconfirmed

    actions, browser = adapter()
    with google_operation_scope(retained={}):
        actions._read_only = True
        page = actions.open_sheet(select_worksheet=True, worksheet="2026")
        page.popup = "synthetic unresolved work"
        actions.retire_failed_page(read_only=True)
        actions.close()
        page.popup = None
        page.url = page.url.split("#")[0]+"#gid=999"
        next_read = GoogleQuotationUpdateActions(browser_handle=actions._handle, location=location())
        next_read._read_only = True
        with pytest.raises((V12Fault, QuotationInputBusy, UpdateAttemptUnconfirmed)):
            next_read.open_sheet(select_worksheet=True, worksheet="2026")
        assert not page.closed and not browser.contexts[0].pages[0].closed


def test_failed_busy_read_with_unchanged_markers_does_not_prove_owner_abandoned_it():
    from src.launcher.google_quote_update import google_operation_scope
    from src.sheets.quotation_input import QuotationInputBusy

    actions, browser = adapter()
    with google_operation_scope(retained={}):
        actions._read_only = True
        page = actions.open_sheet(select_worksheet=True, worksheet="2026")
        page.popup = "synthetic unresolved work"
        actions.retire_failed_page(read_only=True)
        actions.close()
        # A person may take over this same tab without changing its URL or name.
        page.popup = None
        another = GoogleQuotationUpdateActions(browser_handle=actions._handle, location=location())
        another._read_only = True
        recovered = another.open_sheet(select_worksheet=True, worksheet="2026")
        assert recovered is not page and not page.closed and not browser.contexts[0].pages[0].closed
        another.close()
        writer = GoogleQuotationUpdateActions(browser_handle=actions._handle, location=location())
        with pytest.raises(QuotationInputBusy):
            writer.open_sheet(select_worksheet=True, worksheet="2026")


def test_recovery_waits_for_inflight_writer_and_then_blocks_new_writers():
    from src.launcher.google_quote_update import google_operation_scope
    from src.sheets.quotation_input import QuotationInputBusy

    writer, browser = adapter()
    with google_operation_scope(retained={}):
        write_page = writer.open_sheet(select_worksheet=True, worksheet="2026")
        with google_operation_scope(retained={}):
            reader = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
            reader._read_only = True
            old = reader.open_sheet(select_worksheet=True, worksheet="2026")
            old.popup = "synthetic dialog"
            reader.retire_failed_page(read_only=True)
            reader.close()
            old.popup = None
            other = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
            other._read_only = True
            with pytest.raises(QuotationInputBusy):
                other.open_sheet(select_worksheet=True, worksheet="2026")
            assert not old.closed and not write_page.closed
            writer.close()
            replacement = other.open_sheet(select_worksheet=True, worksheet="2026")
            assert replacement is not old and not old.closed
            other.close()
            blocked = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
            with pytest.raises(QuotationInputBusy):
                blocked.open_sheet(select_worksheet=True, worksheet="2026")
    assert not browser.contexts[0].pages[0].closed


@pytest.mark.parametrize("uncertain", ["script", "protected"])
def test_unconfirmed_write_keeps_cross_service_barrier_after_close(uncertain):
    from src.sheets.quotation_input import QuotationInputBusy

    writer, browser = adapter()
    page = writer.open_sheet(select_worksheet=True, worksheet="2026")
    if uncertain == "script":
        writer._script_pending = True
    else:
        writer._protected = True
    writer.close()
    assert not page.closed
    other = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
    with pytest.raises(QuotationInputBusy):
        other.open_sheet(select_worksheet=True, worksheet="2026")
    assert not browser.contexts[0].pages[0].closed


def test_pending_quote_update_blocks_only_new_writes_until_owner_finishes():
    from src.sheets.quotation_input import QuotationInputBusy

    writer, browser = adapter()
    writer.prepare_price_refresh()
    writer.open_quote_input()
    page = browser.contexts[0].pages[-1]
    writer.click_update_quote()
    other = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
    with pytest.raises(QuotationInputBusy):
        other.open_sheet(select_worksheet=True, worksheet="2026")
    assert page.refresh_pending and not page.closed
    page.popup = None
    page.script_running = False
    writer.close()
    other.open_sheet(select_worksheet=True, worksheet="2026")
    other.close()
    assert not browser.contexts[0].pages[0].closed


@pytest.mark.parametrize("probe_fails", [False, True])
def test_pending_quote_is_detected_through_reattached_page(monkeypatch, probe_fails):
    from src.launcher import google_quote_update as module
    from src.sheets.quotation_input import QuotationInputBusy

    writer, browser = adapter()
    writer.prepare_price_refresh()
    writer.open_quote_input()
    page = browser.contexts[0].pages[-1]
    writer.click_update_quote()
    lease, active = page._inso_native_page_owner, page._inso_active_quote_action
    target = lease[0]
    page._inso_native_page_owner = None
    page._inso_active_quote_action = None
    original_target = module._google_target_id
    def target_id(candidate):
        if candidate is page:
            if probe_fails:
                raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED")
            return target
        return original_target(candidate)
    monkeypatch.setattr(module, "_google_target_id", target_id)
    try:
        other = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
        with pytest.raises(QuotationInputBusy):
            other.open_sheet(select_worksheet=True, worksheet="2026")
        assert page.refresh_pending and not page.closed
    finally:
        page._inso_native_page_owner, page._inso_active_quote_action = lease, active
        writer.close()


def test_active_quote_blocks_overlap_if_reattached_page_is_temporarily_unresponsive(monkeypatch):
    from src.sheets.quotation_input import QuotationInputBusy

    writer, browser = adapter()
    writer.prepare_price_refresh()
    writer.open_quote_input()
    page = browser.contexts[0].pages[-1]
    writer.click_update_quote()
    lease, active = page._inso_native_page_owner, page._inso_active_quote_action
    page._inso_native_page_owner = None
    page._inso_active_quote_action = None
    evaluate = Page.evaluate
    def unresponsive(candidate, script, *args, **kwargs):
        if candidate is page and "window.__insoRefreshPending === true" in script:
            raise TimeoutError("synthetic temporary page failure")
        return evaluate(candidate, script, *args, **kwargs)
    monkeypatch.setattr(Page, "evaluate", unresponsive)
    try:
        other = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
        with pytest.raises(QuotationInputBusy):
            other.open_sheet(select_worksheet=True, worksheet="2026")
        assert not page.closed and page.clicks == ["更新报价"]
    finally:
        page._inso_native_page_owner, page._inso_active_quote_action = lease, active
        writer.close()


def test_pending_quote_left_by_previous_client_is_not_replayed():
    from src.sheets.quotation_input import QuotationInputBusy

    writer, browser = adapter()
    writer.prepare_price_refresh()
    writer.open_quote_input()
    page = browser.contexts[0].pages[-1]
    writer.click_update_quote()
    writer.close()
    page._inso_native_page_owner = None  # Reattached client cannot prove prior lease.
    other = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
    with pytest.raises(QuotationInputBusy):
        other.open_sheet(select_worksheet=True, worksheet="2026")
    assert page.refresh_pending and not page.closed and page.clicks == ["更新报价"]
    reader = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
    reader._read_only = True
    assert reader.open_sheet(select_worksheet=True, worksheet="2026") is not page
    reader.close()
    page.closed = True  # Owner resolves and closes the earlier quotation page.
    other.open_sheet(select_worksheet=True, worksheet="2026")
    other.close()
    assert not browser.contexts[0].pages[0].closed


def test_unrelated_read_probe_failure_does_not_block_new_writer(monkeypatch):
    from src.launcher.google_quote_update import google_operation_scope

    reader, browser = adapter()
    with google_operation_scope(retained={}):
        reader._read_only = True
        old = reader.open_sheet(select_worksheet=True, worksheet="2026")
        reader.close()
        evaluate = Page.evaluate
        def optional_probe_fails(page, script, *args, **kwargs):
            if page is old and "window.__insoRefreshPending === true" in script:
                raise TimeoutError("synthetic read page probe failure")
            return evaluate(page, script, *args, **kwargs)
        monkeypatch.setattr(Page, "evaluate", optional_probe_fails)
        writer = GoogleQuotationUpdateActions(browser_handle=reader._handle, location=location())
        assert writer.open_sheet(select_worksheet=True, worksheet="SHAHAB") is not old
        writer.close()
        assert not browser.contexts[0].pages[0].closed


def test_recovery_cannot_touch_page_while_original_writer_is_active():
    from src.sheets.quotation_input import QuotationInputBusy

    writer, browser = adapter()
    writer.prepare_price_refresh()
    writer.open_quote_input()
    page = browser.contexts[0].pages[-1]
    writer.click_update_quote()
    page.popup = None
    page.script_running = False
    other = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
    with pytest.raises(QuotationInputBusy):
        other.ensure_refresh_input_idle()
    assert page.refresh_pending and not page.closed
    writer.close()
    other.ensure_refresh_input_idle()
    assert not page.refresh_pending and page.closed
    assert not browser.contexts[0].pages[0].closed


def test_recovery_lease_excludes_all_writers_until_recovery_finishes():
    import threading

    from src.launcher.google_quote_update import _GoogleDocumentBarrier
    from src.sheets.quotation_input import QuotationInputBusy

    barrier = _GoogleDocumentBarrier()
    document = ("https", "docs.google.com", "/spreadsheets/d/test/edit")
    barrier.begin_reconcile(document)
    with pytest.raises(QuotationInputBusy):
        barrier.begin_write(document)
    with pytest.raises(QuotationInputBusy):
        barrier.quarantine(document)
    result = []
    def competing_writer():
        try:
            barrier.begin_write(document)
        except QuotationInputBusy:
            result.append("busy")
        else:
            result.append("admitted")
            barrier.end_write(document)
    thread = threading.Thread(target=competing_writer)
    thread.start()
    thread.join(2)
    assert not thread.is_alive() and result == ["busy"]
    barrier.end_reconcile(document)
    barrier.begin_write(document)
    barrier.end_write(document)


def test_owner_adoption_at_refresh_close_retains_shared_hold(monkeypatch):
    from src.sheets.quotation_input import QuotationInputBusy

    writer, browser = adapter()
    writer.prepare_price_refresh()
    writer.open_quote_input()
    page = browser.contexts[0].pages[-1]
    writer.click_update_quote()
    page.popup = None
    writer.close()
    page.script_running = False
    close = GoogleQuotationUpdateActions.close
    def adopt_before_close(actions):
        if actions._page is page:
            page.owner_name = "OWNER_ADOPTED"
        return close(actions)
    monkeypatch.setattr(GoogleQuotationUpdateActions, "close", adopt_before_close)
    other = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
    with pytest.raises(V12Fault, match="GOOGLE_TAB_IDENTITY_UNCONFIRMED"):
        other.open_quote_input()
    assert not page.closed and not browser.contexts[0].pages[0].closed
    with pytest.raises(QuotationInputBusy):
        GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location()).open_sheet()


def test_refresh_adoption_during_close_is_detected(monkeypatch):
    actions, browser = adapter()
    actions.prepare_price_refresh()
    actions.open_quote_input()
    page = actions._page
    actions.click_update_quote()
    page.popup = None
    actions.close()
    page.script_running = False
    close = GoogleQuotationUpdateActions.close
    def adopt_before_close(current):
        if current._page is page:
            page.owner_name = "OWNER_ADOPTED"
        return close(current)
    monkeypatch.setattr(GoogleQuotationUpdateActions, "close", adopt_before_close)
    another = GoogleQuotationUpdateActions(browser_handle=actions._handle, location=location())
    with pytest.raises(V12Fault, match="GOOGLE_TAB_IDENTITY_UNCONFIRMED"):
        another.open_quote_input()
    assert not page.closed and not browser.contexts[0].pages[0].closed


def test_refresh_settlement_does_not_clear_separate_identity_uncertainty():
    from src.sheets.quotation_input import QuotationInputBusy

    writer, browser = adapter()
    writer.prepare_price_refresh()
    writer.open_quote_input()
    page = browser.contexts[0].pages[-1]
    writer.click_update_quote()
    page.popup = None
    writer._protected = True
    writer.close()
    page.script_running = False
    other = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
    with pytest.raises(QuotationInputBusy):
        other.open_quote_input()
    assert page.refresh_pending and not page.closed
    assert not browser.contexts[0].pages[0].closed


def test_write_surface_becoming_busy_during_close_blocks_another_client():
    from src.launcher.google_quote_update import google_operation_scope
    from src.sheets.quotation_input import QuotationInputBusy

    writer, browser = adapter()
    with google_operation_scope(retained={}):
        page = writer.open_sheet(select_worksheet=True, worksheet="2026")
        page.popup = "synthetic unresolved work"
        writer.close()
        assert not page.closed
        with google_operation_scope(retained={}):
            other = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
            with pytest.raises(QuotationInputBusy):
                other.open_sheet(select_worksheet=True, worksheet="SHAHAB")
    assert not browser.contexts[0].pages[0].closed


def test_confirming_refresh_never_releases_other_unknown_or_read_hold():
    from src.launcher.google_quote_update import _GoogleDocumentBarrier
    from src.sheets.quotation_input import QuotationInputBusy

    barrier = _GoogleDocumentBarrier()
    document = ("https", "docs.google.com", "/spreadsheets/d/test/edit")
    barrier.begin_write(document)
    barrier.end_write(document, hold=("refresh", "synthetic-target"))
    barrier.settle_refresh(document, "different-target")
    with pytest.raises(QuotationInputBusy):
        barrier.begin_write(document)
    barrier.quarantine(document)
    barrier.settle_refresh(document, "synthetic-target")
    with pytest.raises(QuotationInputBusy):
        barrier.begin_write(document)


def test_document_write_admission_serializes_threads_but_allows_same_owner_nesting():
    import threading

    from src.launcher.google_quote_update import _GoogleDocumentBarrier
    from src.sheets.quotation_input import QuotationInputBusy

    barrier = _GoogleDocumentBarrier()
    document = ("https", "docs.google.com", "/spreadsheets/d/test/edit")
    barrier.begin_write(document)
    barrier.begin_write(document)
    outcomes = []
    def competing_writer():
        try:
            barrier.begin_write(document)
        except QuotationInputBusy:
            outcomes.append("busy")
        else:
            outcomes.append("admitted")
            barrier.end_write(document)
    thread = threading.Thread(target=competing_writer)
    thread.start()
    thread.join(2)
    assert not thread.is_alive() and outcomes == ["busy"]
    barrier.end_write(document)
    barrier.end_write(document)
    barrier.begin_write(document)
    barrier.end_write(document)


def test_nested_clients_share_document_barrier():
    from src.launcher.google_quote_update import _document_barrier
    from src.research.cdp_pages import PageResourceAdmission
    from src.sheets.quotation_input import QuotationInputBusy

    root = PageResourceAdmission()
    child = PageResourceAdmission(parent=root)
    browser_one = SimpleNamespace(_inso_page_admission=root)
    browser_two = SimpleNamespace(_inso_page_admission=child)
    first, second = _document_barrier(browser_one), _document_barrier(browser_two)
    document = ("https", "docs.google.com", "/spreadsheets/d/test/edit")
    assert first is second
    first.begin_write(document)
    with pytest.raises(QuotationInputBusy):
        second.quarantine(document)
    first.end_write(document)
    second.quarantine(document)
    with pytest.raises(QuotationInputBusy):
        first.begin_write(document)


def test_failed_read_does_not_overwrite_owner_adoption_marker():
    from src.launcher.google_quote_update import google_operation_scope

    actions, browser = adapter()
    with google_operation_scope(retained={}):
        actions._read_only = True
        page = actions.open_sheet(select_worksheet=True, worksheet="2026")
        page.owner_name = "OWNER_ADOPTED"
        actions.retire_failed_page(read_only=True)
        actions.close()
        assert page.owner_name == "OWNER_ADOPTED"
        assert not page.closed and not browser.contexts[0].pages[0].closed


@pytest.mark.parametrize("marker", ["OWNER_ADOPTED", ""])
def test_navigation_does_not_overwrite_owner_adoption_marker(monkeypatch, marker):
    actions, browser = adapter()
    original_goto = Page.goto
    def adopt(page, url, **kwargs):
        original_goto(page, url, **kwargs)
        page.owner_name = marker
    monkeypatch.setattr(Page, "goto", adopt)
    actions._read_only = True
    with pytest.raises(V12Fault, match="GOOGLE_TAB_IDENTITY_UNCONFIRMED"):
        actions.open_sheet(select_worksheet=True, worksheet="2026")
    page = browser.contexts[0].pages[-1]
    actions.retire_failed_page(read_only=True)
    actions.close()
    assert page.owner_name == marker
    assert not page.closed and not browser.contexts[0].pages[0].closed


def test_native_identity_probe_failure_preserves_page(monkeypatch):
    import src.launcher.google_quote_update as module
    from src.research.cdp_pages import PageTargetOwnershipError

    actions, browser = adapter()
    def fail(_):
        raise PageTargetOwnershipError((ValueError("synthetic identity failure"),))
    monkeypatch.setattr(module, "native_page_owner", fail)
    with pytest.raises(PageTargetOwnershipError):
        actions.open_sheet(select_worksheet=True, worksheet="2026")
    page = browser.contexts[0].pages[-1]
    actions.close()
    assert not page.closed and not browser.contexts[0].pages[0].closed


def test_unleased_refresh_marker_is_never_cleared_or_closed():
    actions, browser = adapter()
    human = browser.contexts[0].pages[0]
    human.url = location().url
    human.owner_name = "INSO_OWNER_TAB:google-operation"
    human.refresh_pending = True
    human.armed = True
    with pytest.raises(V12Fault, match="GOOGLE_TAB_IDENTITY_UNCONFIRMED"):
        actions.ensure_refresh_input_idle()
    assert human.refresh_pending and not human.closed


def test_refresh_pending_without_settlement_latch_is_not_released():
    from src.sheets.quotation_input import QuotationInputBusy

    actions, browser = adapter()
    actions.open_quote_input()
    page = actions._page
    page.refresh_pending = True
    page.armed = False
    actions._page = None
    with pytest.raises(QuotationInputBusy):
        actions.ensure_refresh_input_idle()
    assert page.refresh_pending and not page.closed and not browser.contexts[0].pages[0].closed


def test_refresh_owner_adoption_during_wait_keeps_pending_and_page(monkeypatch):
    actions, browser = adapter()
    actions.prepare_price_refresh()
    actions.open_quote_input()
    page = actions._page
    actions.click_update_quote()
    page.popup = None
    page.script_running = False
    actions.close()
    original_wait = page.wait_for_function
    def adopt_after_wait(script, **kwargs):
        result = original_wait(script, **kwargs)
        page.owner_name = "OWNER_ADOPTED"
        return result
    monkeypatch.setattr(page, "wait_for_function", adopt_after_wait)
    next_actions = GoogleQuotationUpdateActions(browser_handle=actions._handle, location=location())
    with pytest.raises(V12Fault, match="GOOGLE_TAB_IDENTITY_UNCONFIRMED"):
        next_actions.ensure_refresh_input_idle()
    assert page.refresh_pending and not page.closed and not browser.contexts[0].pages[0].closed


def test_refresh_result_wait_adoption_does_not_clear_pending_or_close(monkeypatch):
    actions, browser = adapter()
    actions.prepare_price_refresh()
    actions.open_quote_input()
    page = actions._page
    actions.click_update_quote()
    actions.close()
    original_wait = page.wait_for_function
    def adopt_after_settlement(script, **kwargs):
        result = original_wait(script, **kwargs)
        if ".settled" in script:
            page.owner_name = "OWNER_ADOPTED"
        return result
    monkeypatch.setattr(page, "wait_for_function", adopt_after_settlement)
    next_actions = GoogleQuotationUpdateActions(browser_handle=actions._handle, location=location())
    with pytest.raises(V12Fault, match="GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED"):
        next_actions.ensure_refresh_input_idle()
    assert page.refresh_pending and page.owner_name == "OWNER_ADOPTED"
    assert not page.closed and not browser.contexts[0].pages[0].closed


def test_failed_read_does_not_make_previously_written_slot_reopenable():
    from src.launcher.google_quote_update import google_operation_scope
    from src.sheets.quotation_input import QuotationInputBusy

    writer, browser = adapter()
    with google_operation_scope(retained={}):
        page = writer.open_sheet(select_worksheet=True, worksheet="2026")
        writer.close()
        reader = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
        reader._read_only = True
        assert reader.open_sheet(select_worksheet=True, worksheet="2026") is page
        entry = reader._poll_entry
        assert entry["read_only"] is False
        reader.retire_failed_page(read_only=True)
        reader.close()
        assert entry["protected"] and not entry["reopenable"]
        another = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
        another._read_only = True
        with pytest.raises(QuotationInputBusy):
            another.open_sheet(select_worksheet=True, worksheet="2026")
        assert not page.closed and not browser.contexts[0].pages[0].closed


def test_failed_read_cannot_erase_write_history_across_scopes():
    from src.launcher.google_quote_update import google_operation_scope
    from src.sheets.quotation_input import QuotationInputBusy

    writer, browser = adapter()
    retained = {}
    with google_operation_scope(retained=retained):
        page = writer.open_sheet(select_worksheet=True, worksheet="2026")
        writer.close()
    assert next(iter(retained.values()))[3] is False
    with google_operation_scope(retained=retained):
        reader = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
        reader._read_only = True
        assert reader.open_sheet(select_worksheet=True, worksheet="2026") is page
        entry = reader._poll_entry
        reader.retire_failed_page(read_only=True)
        reader.close()
        assert entry["protected"] and not entry["reopenable"]
        assert not page.closed and not browser.contexts[0].pages[0].closed
        another = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
        another._read_only = True
        with pytest.raises(QuotationInputBusy):
            another.open_sheet(select_worksheet=True, worksheet="2026")
    assert next(iter(retained.values()))[1:] == (True, False, False)


def test_legacy_retained_target_has_no_read_only_proof():
    from src.launcher.google_quote_update import google_operation_scope

    original, _browser = adapter()
    retained = {}
    with google_operation_scope(retained=retained):
        original._read_only = True
        page = original.open_sheet(select_worksheet=True, worksheet="2026")
        original.close()
    key = next(iter(retained))
    retained[key] = retained[key][:3]  # Old registry entries carry no read history.
    with google_operation_scope(retained=retained):
        reader = GoogleQuotationUpdateActions(browser_handle=original._handle, location=location())
        reader._read_only = True
        assert reader.open_sheet(select_worksheet=True, worksheet="2026") is page
        assert reader._poll_entry["read_only"] is False
        reader.retire_failed_page(read_only=True)
        reader.close()
        assert not page.closed
    assert retained[key][1:] == (True, False, False)


def test_write_admission_records_lost_read_only_proof_before_use():
    from src.launcher.google_quote_update import google_operation_scope

    first, _browser = adapter()
    retained = {}
    with google_operation_scope(retained=retained):
        first._read_only = True
        first.open_sheet(select_worksheet=True, worksheet="2026")
        first.close()
    assert next(iter(retained.values()))[3] is True
    with google_operation_scope(retained=retained):
        writer = GoogleQuotationUpdateActions(browser_handle=first._handle, location=location())
        writer.open_sheet(select_worksheet=True, worksheet="2026")
        assert next(iter(retained.values()))[3] is False
        writer.close()


def test_read_only_history_survives_protected_scope_reattachment():
    from src.launcher.google_quote_update import google_operation_scope
    from src.sheets.quotation_input import QuotationInputBusy

    first, _browser = adapter()
    retained = {}
    with google_operation_scope(retained=retained):
        first._read_only = True
        page = first.open_sheet(select_worksheet=True, worksheet="2026")
        page.popup = "Synthetic busy dialog"
        first.retire_failed_page(read_only=True)
        first.close()
    key = next(iter(retained))
    assert retained[key][1:4] == (True, False, True)
    with google_operation_scope(retained=retained):
        reader = GoogleQuotationUpdateActions(browser_handle=first._handle, location=location())
        reader._read_only = True
        with pytest.raises(QuotationInputBusy):
            reader.open_sheet(select_worksheet=True, worksheet="2026")
        assert not page.closed
    assert retained[key][1:4] == (True, False, True)


def test_retained_hard_hold_cannot_be_weakened_by_new_read_entry():
    from src.launcher.google_quote_update import _google_target_id, _retain_google_entry

    actions, _browser = adapter()
    page = actions.open_sheet(select_worksheet=True, worksheet="2026")
    key = ("synthetic",)
    retained = {key: (_google_target_id(page), True, False, True)}
    entry = {"page": page, "protected": True, "reopenable": True, "read_only": True}
    _retain_google_entry(key, entry, retained)
    assert retained[key][1:4] == (True, False, True)


def test_new_target_cannot_replace_a_different_protected_target():
    from src.launcher.google_quote_update import _retain_google_entry

    actions, _browser = adapter()
    page = actions.open_sheet(select_worksheet=True, worksheet="2026")
    key = ("synthetic",)
    original = ("other-protected-target", True, False, False)
    retained = {key: original}
    entry = {"page": page, "protected": False, "reopenable": False, "read_only": True}
    with pytest.raises(V12Fault, match="GOOGLE_TAB_IDENTITY_UNCONFIRMED"):
        _retain_google_entry(key, entry, retained)
    assert retained[key] == (original[0], True, False, False) and not page.closed


def test_closed_former_write_target_cannot_clear_its_protection():
    from src.launcher.google_quote_update import google_operation_scope

    writer, _browser = adapter()
    retained = {}
    with google_operation_scope(retained=retained):
        page = writer.open_sheet(select_worksheet=True, worksheet="2026")
        writer.close()
    with google_operation_scope(retained=retained):
        reader = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
        reader._read_only = True
        assert reader.open_sheet(select_worksheet=True, worksheet="2026") is page
        page.close()
        reader.retire_failed_page(read_only=True)
        reader.close()
        retry = GoogleQuotationUpdateActions(browser_handle=writer._handle, location=location())
        retry._read_only = True
        with pytest.raises(V12Fault, match="GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED"):
            retry.open_sheet(select_worksheet=True, worksheet="2026")
    assert next(iter(retained.values()))[1:] == (True, False, False)


def test_closed_read_cannot_replace_mismatched_retained_identity():
    from src.launcher.google_quote_update import google_operation_scope

    reader, _browser = adapter()
    reader._read_only = True
    retained = {}
    with google_operation_scope(retained=retained):
        page = reader.open_sheet(select_worksheet=True, worksheet="2026")
        key = next(iter(retained))
        retained[key] = ("different-target", False, False, True)
        page.close()
        reader.retire_failed_page(read_only=True)
        reader.close()
        retry = GoogleQuotationUpdateActions(browser_handle=reader._handle, location=location())
        retry._read_only = True
        with pytest.raises(V12Fault, match="GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED"):
            retry.open_sheet(select_worksheet=True, worksheet="2026")
    assert retained[key][0] == "different-target" and retained[key][1] is True


def test_new_target_cannot_replace_another_retained_target_even_when_not_protected():
    from src.launcher.google_quote_update import _retain_google_entry

    actions, _browser = adapter()
    page = actions.open_sheet(select_worksheet=True, worksheet="2026")
    key = ("synthetic",)
    original = ("other-target", False, False, True)
    retained = {key: original}
    entry = {"page": page, "protected": False, "reopenable": False, "read_only": True}
    with pytest.raises(V12Fault, match="GOOGLE_TAB_IDENTITY_UNCONFIRMED"):
        _retain_google_entry(key, entry, retained)
    assert retained[key] == (original[0], True, False, False) and not page.closed


def test_missing_quote_popup_waits_one_minute_without_clicking_again():
    actions, browser = adapter()
    actions.open_quote_input()
    page = browser.contexts[0].pages[-1]
    actions.click_update_quote()
    page.popup = None
    from src.workflow.v13_quote_update import UpdateResultTimeout
    with pytest.raises(UpdateResultTimeout):
        actions.read_update_result()
    assert page.result_waits == [60000]
    assert page.clicks == ["更新报价"]
    actions.close()
    assert not page.closed and not browser.contexts[0].pages[0].closed


def test_popup_timeout_does_not_wait_for_a_second_page_probe(monkeypatch):
    from src.workflow.v13_quote_update import UpdateResultTimeout

    actions, browser = adapter()
    actions.open_quote_input()
    page = browser.contexts[0].pages[-1]
    actions.click_update_quote()
    page.popup = None
    guard = actions._guard
    calls = []
    def first_guard_only(*args, **kwargs):
        calls.append(True)
        if len(calls) > 1:
            raise TimeoutError("synthetic unresponsive page")
        return guard(*args, **kwargs)
    monkeypatch.setattr(actions, "_guard", first_guard_only)
    with pytest.raises(UpdateResultTimeout):
        actions.read_update_result()
    assert page.result_waits == [60000] and len(calls) == 1
    assert page.clicks == ["更新报价"]
    actions.close()
    assert not page.closed


def test_next_order_can_proceed_when_timed_out_script_finishes():
    from src.workflow.v13_quote_update import UpdateResultTimeout

    first, browser = adapter()
    first.open_quote_input()
    old = browser.contexts[0].pages[-1]
    first.click_update_quote()
    old.popup = None
    with pytest.raises(UpdateResultTimeout):
        first.read_update_result()
    first.close()
    old.confirmed = old.started = old.settled = True
    old.script_running = False
    next_order = GoogleQuotationUpdateActions(browser_handle=first._handle, location=location())
    next_order.open_quote_input()
    assert next_order._page is not old and old.closed
    assert old.clicks == ["更新报价"]
    next_order.close()
    assert not browser.contexts[0].pages[0].closed


def test_delayed_result_dialog_within_fifteen_seconds_is_not_closed_or_reclicked(monkeypatch):
    actions, browser = adapter()
    actions.open_quote_input()
    page = browser.contexts[0].pages[-1]
    actions.click_update_quote()
    page.popup = None  # The simulated result has not appeared yet.
    original = Locator.wait_for
    def delayed_dialog(locator, **kwargs):
        if locator.role == "dialog":
            assert kwargs["timeout"] >= 15000
            assert not page.closed and page.clicks == ["更新报价"]
            page.popup = "报价更新完成\n成功填入：1行"
        return original(locator, **kwargs)
    monkeypatch.setattr(Locator, "wait_for", delayed_dialog)

    assert actions.read_update_result() == "报价更新完成\n成功填入：1行"
    assert page.result_waits == [60000] and page.clicks == ["更新报价"]
    assert not page.closed
