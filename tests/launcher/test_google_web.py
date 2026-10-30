"""Native UI range contract against a synthetic Sheets surface; no network/CDP."""
import csv
import io
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from src.launcher.browser_bootstrap import BrowserHandle
from src.launcher.google_web import (
    GoogleSheetsWebService,
    _source_values,
    build_google_web_service,
)
from src.sheets import WorksheetIdentity
from src.sheets.google_reader import GoogleSheetsRowReader
from src.sheets.google_writer import GoogleSheetsBrandWriter, GoogleSheetsWriteError
from src.sheets.quotation_input import (
    GoogleQuotationInput,
    QuotationInputLocation,
    QuotationInputUnavailable,
)
from src.workflow.v12_faults import V12Fault
from tests.launcher.test_google_quote_update import Browser, Page

TITLES = {'2026': 0, 'SHAHAB': 17, '报价输入': 29}
HEADERS = {
    '2026': [['STATUS', 'WHAT', 'CLASS', 'WHO', 'MPN', 'MFR', 'Qty']],
    'SHAHAB': [[], ['DATE', 'STATUS', 'Item', 'Part Number', 'Brand', 'QTY', 'UM']],
    '报价输入': [],
}


class Download:
    def __init__(self, page):
        self.page = page
        self.file = page.tmp / f'export-{len(page.downloads)}.tsv'
        buffer = io.StringIO()
        csv.writer(buffer, delimiter='\t', lineterminator='\n').writerows(page.rows[page.title])
        self.file.write_text(buffer.getvalue(), encoding='utf-8')
        page.downloads.append(self)

    def failure(self):
        return None

    def path(self):
        return str(self.file)

    def delete(self):
        self.file.unlink()


class GridLocator:
    def __init__(self, page, kind, name=None):
        self.page, self.kind, self.name = page, kind, name

    def filter(self, *, has):
        return GridLocator(self.page, 'tab', has.name)

    def count(self):
        return int(self.name in TITLES) if self.kind == 'tab' else 1

    def wait_for(self, **_):
        return None

    def click(self, **_):
        if self.kind == 'editor':
            self.page.editor_active = True
        elif self.kind == 'tab':
            self.page.title = self.name
            self.page.url = self.page.url.split('#')[0] + f'#gid={TITLES[self.name]}'
        elif self.name not in ('文件',):
            pattern = getattr(self.name, 'pattern', '')
            if 'tsv' in pattern:
                self.page.pending.value = Download(self.page)

    def fill(self, value):
        if self.kind == 'box':
            self.page.selection = value
        else:
            assert self.kind == 'editor'
            self.page.typed.append(value)
            self.page.edit = value

    def press(self, key):
        if key in ('Control+A', 'Backspace'):
            assert self.kind == 'editor' and self.page.editor_active
            if key == 'Backspace':
                self.page.edit = ''
            return
        assert key == 'Enter'
        if self.kind == 'editor':
            if not self.page.native_edit:
                return  # DOM fill alone is ignored by the real Sheets model.
            cell = self.page.selection
            col, row = ord(cell[0])-65, int(cell[1:])-1
            rows = self.page.rows[self.page.title]
            while len(rows) <= row:
                rows.append([])
            while len(rows[row]) <= col:
                rows[row].append('')
            text = self.page.edit
            rows[row][col] = text.removeprefix("'")
            self.page.editor_active = self.page.native_edit = False

    def input_value(self):
        return self.page.selection

    def evaluate(self, script):
        assert self.kind == 'box' and 'document.activeElement' in script
        return False


class GridPage(Page):
    def __init__(self, context, rows, tmp):
        super().__init__(context)
        self.rows, self.tmp, self.title = rows, tmp, '2026'
        self.typed, self.downloads = [], []
        self.save_fails = False
        self.editor_active = self.native_edit = False
        self.keyboard = SimpleNamespace(press=self.keypress, type=self.type_text)

    def keypress(self, key):
        if key == "'":
            self.editor_active = True
        else:
            assert key == 'Enter'
            GridLocator(self, 'editor').press(key)

    def type_text(self, text, **kwargs):
        self.editor_active = True
        self.typed.append(text)
        self.edit, self.native_edit = text, True

    def locator(self, selector):
        kind = {'#t-name-box': 'box', '.docs-sheet-tab': 'tabs',
                '#t-formula-bar-input [contenteditable="true"]': 'editor'}.get(selector)
        return GridLocator(self, kind) if kind else super().locator(selector)

    def get_by_text(self, text, **kwargs):
        return GridLocator(self, 'label', text) if text in TITLES else super().get_by_text(text, **kwargs)

    def get_by_role(self, role, *, name=None, exact=None):
        if role == 'menuitem':
            return GridLocator(self, 'menu', name)
        return super().get_by_role(role, name=name, exact=exact)

    def wait_for_function(self, script, **kwargs):
        if 'docs-sheet-active-tab' in script:
            assert self.title == kwargs['arg']['title']
        elif 'docs-save-indicator-badge' in script:
            if self.save_fails:
                raise TimeoutError('synthetic unsaved edit')
        else:
            return super().wait_for_function(script, **kwargs)

    def evaluate(self, script, arg=None):
        if 'docs-sheet-active-tab' in script:
            return {'title':self.title, 'fragment':self.url.split('#')[-1]}
        return super().evaluate(script,arg)

    def expect_download(self, **kwargs):
        self.pending = SimpleNamespace(value=None)
        return nullcontext(self.pending)


@pytest.fixture
def web(tmp_path):
    browser = Browser()
    context = browser.contexts[0]
    original = context.pages[0]
    rows = {title: [list(row) for row in header] for title, header in HEADERS.items()}
    rows['2026'].append(['发给采购', '', 'B', 'TEST-CUSTOMER', '000123', 'OLD', '1,200'])
    rows['SHAHAB'].append(['', '已报价给客户', '1', 'TEST-XYZ', 'OLD', '2', 'PCS'])

    def new_page():
        page = GridPage(context, rows, tmp_path)
        context.pages.append(page)
        return page

    context.new_page = new_page
    handle = BrowserHandle(owned=False, browser=browser)
    return GoogleSheetsWebService(lambda: nullcontext(handle)), browser, rows, original


@pytest.mark.parametrize('title,row,model,qty', [('2026', 2, '000123', 1200), ('SHAHAB', 3, 'TEST-XYZ', 2)])
def test_source_reader_reuses_schema_and_preserves_numeric_identity(web, title, row, model, qty):
    service, browser, _, original = web
    actual = GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', title))[row-1]
    assert actual.cells['E' if title == '2026' else 'D'] == model
    assert actual.cells['G' if title == '2026' else 'F'] == qty
    assert browser.connected and not original.closed
    page = browser.contexts[0].pages[-1]
    assert page.closed and all(not d.file.exists() for d in page.downloads)


@pytest.mark.parametrize('title,row,col', [('2026', 2, 'F'), ('SHAHAB', 3, 'E')])
def test_existing_single_cell_writer_uses_literal_ui_and_server_readback(web, title, row, col):
    service, browser, rows, original = web
    old = [list(r) for r in rows[title]]
    brand = '=TEST("do not evaluate")'
    GoogleSheetsBrandWriter(service).write_brand(WorksheetIdentity('test', title), row, brand)
    old[row-1][ord(col)-65] = brand
    assert rows[title] == old
    page = browser.contexts[0].pages[-1]
    assert page.typed == ["'" + brand] and page.closed and not original.closed
    assert all(not d.file.exists() for d in page.downloads)


def test_existing_raw14_adapter_keeps_exact_strings_without_formula_execution(web):
    from src.inso.quotation_read import QUOTATION_COLUMNS
    service, browser, _, original = web
    location = QuotationInputLocation(WorksheetIdentity('test', '报价输入'), 1, 1, '29')
    adapter = GoogleQuotationInput(service, location, expected_columns=QUOTATION_COLUMNS)
    raw = ('2026-01-01', 'TEST-X', 'BRAND', '0002', 'RMB', '', '01.00', '001.00',
           '0000', '2026+', '现货', ' 备注\n第二行\t ', '=TEST()', "'literal")
    adapter.write_payload(raw)
    assert adapter.read_payload() == raw
    assert all(p.closed for p in browser.contexts[0].pages[1:])
    assert not original.closed and browser.connected
    assert all(not d.file.exists() for p in browser.contexts[0].pages[1:] for d in p.downloads)


def test_shifted_headers_stop_before_any_source_write(web):
    service, browser, rows, _ = web
    rows['SHAHAB'][1][3] = 'WRONG'
    with pytest.raises(GoogleSheetsWriteError):
        GoogleSheetsBrandWriter(service).write_brand(WorksheetIdentity('test','SHAHAB'),3,'NEW')
    assert not browser.contexts[0].pages[-1].typed


def test_unsaved_write_preserves_only_owned_operation_page(web):
    service, browser, _, original = web
    create = browser.contexts[0].new_page
    def unsaved():
        page = create()
        page.save_fails = True
        return page
    browser.contexts[0].new_page = unsaved
    with pytest.raises(QuotationInputUnavailable):
        service.values().update(spreadsheetId='test', range="'SHAHAB'!E3",
            valueInputOption='RAW', body={'values': [['NEW']]}).execute()
    assert not browser.contexts[0].pages[-1].closed and not original.closed and browser.connected


def test_wrong_gid_binding_and_noncanonical_cdp_are_closed_failures(web):
    from src.inso.quotation_read import QUOTATION_COLUMNS
    service, _, _, _ = web
    adapter = GoogleQuotationInput(service,
        QuotationInputLocation(WorksheetIdentity('test','报价输入'),1,1,'99'), expected_columns=QUOTATION_COLUMNS)
    with pytest.raises(QuotationInputUnavailable, match='BINDING'):
        adapter.validate_schema()
    with pytest.raises(ValueError, match='CANONICAL'):
        build_google_web_service('http://127.0.0.1:9333')


def test_quantity_types_and_other_text_never_share_coercion():
    row = [['', '', '', '', '00012', '00034', '1,200.00']]
    assert _source_values(row,'2026',1,1,7,1)[0][-3:] == ['00012','00034',1200]


def test_authentication_page_is_not_retried_or_closed(web):
    service, browser, _, original = web
    create = browser.contexts[0].new_page
    def auth():
        page = create()
        page.login_markers.add('登录')
        return page
    browser.contexts[0].new_page = auth
    with pytest.raises(V12Fault, match='AUTHENTICATION'):
        service.values().get(spreadsheetId='test', range="'2026'!A1:G").execute()
    assert len(browser.contexts[0].pages) == 2
    assert not browser.contexts[0].pages[-1].closed and not original.closed


def test_poll_reuses_three_worksheet_pages_then_closes_all(web):
    service, browser, _, original = web
    with service.poll_scope():
        for title in ('2026', 'SHAHAB', '2026'):
            service.get(spreadsheetId='test', range=f"'{title}'!A1:G").execute()
        service.update(spreadsheetId='test', range="'报价输入'!A1:N1",
                       valueInputOption='RAW', body={'values': [['TEST'] * 14]}).execute()
        pages = browser.contexts[0].pages[1:]
        assert len(pages) == 3
        assert [page.title for page in pages] == ['2026', 'SHAHAB', '报价输入']
        assert all(not page.closed for page in pages)
        for title in ('SHAHAB', '2026', '报价输入', 'SHAHAB'):
            service.get(spreadsheetId='test', range=f"'{title}'!A1:G").execute()
        assert browser.contexts[0].pages[1:] == pages
    assert all(page.closed for page in pages) and not original.closed
    with service.poll_scope():
        service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
    assert len(browser.contexts[0].pages) == 5 and browser.contexts[0].pages[-1].closed


@pytest.mark.parametrize('problem', ['wrong_document', 'auth', 'pending', 'dialog', 'ownership'])
def test_unsafe_old_sheet_is_quarantined_next_stage_uses_fresh_page(web, problem):
    service, browser, _, original = web
    with service.poll_scope():
        service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
        old = browser.contexts[0].pages[-1]
        if problem == 'wrong_document':
            old.url = 'https://docs.google.com/spreadsheets/d/other/edit#gid=0'
        elif problem == 'auth':
            old.login_markers.add('登录')
        elif problem == 'pending':
            old.refresh_pending = True
        elif problem == 'dialog':
            old.popup = 'Unexpected dialog'
        else:
            old.owner_name = ''
        service.get(spreadsheetId='test', range="'SHAHAB'!A1:G").execute()
        new = browser.contexts[0].pages[-1]
        assert new is not old and new.title == 'SHAHAB'
        assert not old.closed and not new.closed
    assert new.closed and not old.closed and not original.closed


def test_dirty_write_page_is_never_reused_or_closed_by_next_stage(web):
    service, browser, _, original = web
    with service.poll_scope():
        create = browser.contexts[0].new_page
        def dirty():
            page = create()
            page.save_fails = True
            return page
        browser.contexts[0].new_page = dirty
        with pytest.raises(QuotationInputUnavailable):
            service.update(spreadsheetId='test', range="'2026'!F2", valueInputOption='RAW',
                           body={'values': [['NEW']]}).execute()
        old = browser.contexts[0].pages[-1]
        browser.contexts[0].new_page = create
        service.get(spreadsheetId='test', range="'SHAHAB'!A1:G").execute()
        new = browser.contexts[0].pages[-1]
    assert new.closed and not old.closed and not original.closed


def test_poll_cleanup_on_error_does_not_leave_normal_page_open(web):
    service, browser, _, original = web
    with pytest.raises(RuntimeError, match='synthetic stage failure'), service.poll_scope():
        service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
        raise RuntimeError('synthetic stage failure')
    assert browser.contexts[0].pages[-1].closed and not original.closed


def test_updater_and_web_transport_share_input_slot_with_separate_source_pages(web):
    from src.launcher.google_quote_update import GoogleQuotationUpdateActions
    service, browser, _, original = web
    location = QuotationInputLocation(WorksheetIdentity('test', '报价输入'), 1, 1, '29')
    with service.poll_scope():
        actions = GoogleQuotationUpdateActions(browser_handle=BrowserHandle(owned=False, browser=browser),
                                               location=location)
        actions.open_quote_input()
        input_page = actions._page
        for title in ('2026', 'SHAHAB'):
            service.get(spreadsheetId='test', range=f"'{title}'!A1:G").execute()
        service.update(spreadsheetId='test', range="'报价输入'!A1:N1", valueInputOption='RAW',
                       body={'values': [['TEST'] * 14]}).execute()
        assert actions._page is input_page and input_page.title == '报价输入'
        actions.click_update_quote()
        assert '成功填入' in actions.read_update_result()
        actions.dismiss_result()
        # Source status checks after script completion may select the source tab.
        service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
        actions.close()
        assert len(browser.contexts[0].pages) == 4
    assert all(page.closed for page in browser.contexts[0].pages[1:]) and not original.closed


def test_new_stage_auth_failure_still_stops_once_and_preserves_both_pages(web):
    service, browser, _, original = web
    with service.poll_scope():
        service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
        old = browser.contexts[0].pages[-1]
        old.popup = 'Previous stage error'
        create = browser.contexts[0].new_page
        def auth():
            page = create()
            page.login_markers.add('登录')
            return page
        browser.contexts[0].new_page = auth
        with pytest.raises(V12Fault, match='GOOGLE_AUTHENTICATION_REQUIRED'):
            service.get(spreadsheetId='test', range="'SHAHAB'!A1:G").execute()
        new = browser.contexts[0].pages[-1]
        assert len(browser.contexts[0].pages) == 3
    assert not old.closed and not new.closed and not original.closed


def test_poll_session_is_lazy_reused_and_failed_acquisition_can_retry(web):
    from contextlib import contextmanager
    service, _, _, _ = web
    original_session = service._session
    entered, exited = [], []
    @contextmanager
    def session():
        entered.append(True)
        if len(entered) == 1:
            raise TimeoutError('synthetic pre-acquisition failure')
        with original_session() as handle:
            try:
                yield handle
            finally:
                exited.append(True)
    service._session = session
    with service.poll_scope():
        assert not entered
        with pytest.raises(TimeoutError):
            service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
        for title in ('2026', 'SHAHAB'):
            service.get(spreadsheetId='test', range=f"'{title}'!A1:G").execute()
        assert len(entered) == 2 and not exited
    assert len(exited) == 1


def test_other_thread_cannot_borrow_or_close_poll_page(web):
    from threading import Thread
    service, browser, _, _ = web
    with service.poll_scope():
        service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
        poll_page = browser.contexts[0].pages[-1]
        results = []
        worker = Thread(target=lambda: results.append(service.get(
            spreadsheetId='test', range="'SHAHAB'!A1:G").execute()))
        worker.start()
        worker.join(timeout=2)
        assert not worker.is_alive() and results
        assert len(browser.contexts[0].pages) == 3
        assert browser.contexts[0].pages[-1].closed and not poll_page.closed
    assert poll_page.closed


def test_pending_refresh_page_kept_while_other_source_reads_continue(web):
    from src.launcher.google_quote_update import GoogleQuotationUpdateActions
    service, browser, _, _ = web
    location = QuotationInputLocation(WorksheetIdentity('test', '报价输入'), 1, 1, '29')
    with service.poll_scope():
        actions = GoogleQuotationUpdateActions(browser_handle=BrowserHandle(owned=False, browser=browser),
                                               location=location)
        actions.prepare_price_refresh()
        actions.open_quote_input()
        old = actions._page
        actions.click_update_quote()
        actions.close()  # Uncertain result, no repeat click or destructive navigation.
        service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
        new = browser.contexts[0].pages[-1]
        assert new is not old and old.refresh_pending and old.clicks == ['更新报价']
    assert new.closed and not old.closed


def test_wrapped_menu_timeout_retries_once_then_recovers_in_reader(web, monkeypatch):
    from playwright.sync_api import TimeoutError as PageTimeout

    from tests.launcher.test_google_quote_update import Locator
    service, browser, _, _ = web
    calls = []
    original = Locator.wait_for
    def wait(locator, **kwargs):
        if locator.name == '报价工具':
            calls.append(True)
            if len(calls) == 1:
                raise PageTimeout('synthetic menu loading timeout')
        return original(locator, **kwargs)
    monkeypatch.setattr(Locator, 'wait_for', wait)
    with service.poll_scope():
        rows = GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', '2026'))
    assert rows and len(calls) == 2
    assert len(browser.contexts[0].pages) == 3  # Failed phase closed; retry gets a new tab.
    assert all(page.closed for page in browser.contexts[0].pages[1:])


@pytest.mark.parametrize('code', ['ERR_TIMED_OUT', 'ERR_CONNECTION_RESET', 'ERR_NETWORK_CHANGED',
                                 'ERR_PROXY_CONNECTION_FAILED', 'ERR_NAME_NOT_RESOLVED'])
def test_wrapped_navigation_network_failure_is_transient(web, monkeypatch, code):
    from playwright.sync_api import Error as PageError

    from src.sheets.google_reader import GoogleSheetsReadUnavailable
    service, browser, _, _ = web
    create = browser.contexts[0].new_page
    calls = []
    def new_page():
        page = create()
        def goto(url, **kwargs):
            calls.append(True)
            raise PageError(f'Page.goto: net::{code} at private-url-not-for-logs')
        page.goto = goto
        return page
    browser.contexts[0].new_page = new_page
    with service.poll_scope(), pytest.raises(GoogleSheetsReadUnavailable):
        GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', '2026'))
    assert len(calls) == 5


@pytest.mark.parametrize('failure', ['unknown', 'cert', 'auth', 'schema', 'wrapper_without_cause', 'missing_runtime'])
def test_unknown_and_security_failures_do_not_become_temporary(web, monkeypatch, failure):
    from playwright.sync_api import Error as PageError

    from src.sheets.google_reader import (
        GoogleSheetsReadError,
        GoogleSheetsReadUnavailable,
    )
    from src.workflow.v12_faults import FaultScope
    from src.workflow.v13_quote_update import UpdateAttemptUnconfirmed
    from tests.launcher.test_google_quote_update import Locator
    service, _, _, _ = web
    errors = {
        'unknown': RuntimeError('private unexpected DOM'),
        'cert': PageError('net::ERR_CERT_AUTHORITY_INVALID'),
        'auth': V12Fault(FaultScope.GLOBAL_STOP, 'GOOGLE_AUTHENTICATION_REQUIRED'),
        'schema': V12Fault(FaultScope.GLOBAL_STOP, 'SHEETS_SCHEMA_UNAVAILABLE'),
        'wrapper_without_cause': UpdateAttemptUnconfirmed('UPDATE_RESULT_UNCONFIRMED'),
        'missing_runtime': FileNotFoundError('synthetic unrelated missing runtime'),
    }
    calls = []
    original = Locator.wait_for
    def wait(locator, **kwargs):
        if locator.name == '报价工具':
            calls.append(True)
            raise errors[failure]
        return original(locator, **kwargs)
    monkeypatch.setattr(Locator, 'wait_for', wait)
    with service.poll_scope(), pytest.raises(GoogleSheetsReadError) as caught:
        GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', '2026'))
    assert not isinstance(caught.value, GoogleSheetsReadUnavailable) and len(calls) == 1


@pytest.mark.parametrize('failure_mode', ['menu_timeout', 'read_gid_drift', 'read_page_closed',
                                        'artifact_lost', 'timeout_then_busy', 'navigation_error_page', 'session_attach', 'metadata_timeout'])
def test_google_web_timeout_exhaustion_notifies_once_and_actual_poller_runs_next_cycle(
        web, tmp_path, monkeypatch, failure_mode):
    import json
    from types import SimpleNamespace

    from playwright.sync_api import TimeoutError as PageTimeout

    from src.launcher import backend as launcher
    from tests.launcher.test_backend import _RecordingTransport, _write_runtime_configs
    from tests.launcher.test_google_quote_update import Locator
    service, browser, rows, original_page = web
    rows['2026'] = [list(row) for row in HEADERS['2026']]
    rows['SHAHAB'] = [list(row) for row in HEADERS['SHAHAB']]
    production, rc, _ = _write_runtime_configs(tmp_path)
    cfg = json.loads(production.read_text(encoding='utf-8'))
    cfg.update(worksheet_titles=['2026', 'SHAHAB'], v13_enabled=True,
               quotation_input={'gid': '29', 'input_row': 1, 'first_column': 1})
    production.write_text(json.dumps(cfg), encoding='utf-8')
    monkeypatch.setattr(launcher, 'build_google_web_service', lambda *a, **kw: service)
    monkeypatch.setattr(launcher, 'GoogleSheetsRowReader', lambda svc, **kw: GoogleSheetsRowReader(svc))
    monkeypatch.setattr(launcher, 'assess_readiness', lambda *a, **kw: SimpleNamespace(ready=True, missing_site_ids=()))
    monkeypatch.setattr(launcher, 'build_research_service', lambda *a, **kw: SimpleNamespace(execute=lambda _: None))
    monkeypatch.setattr(launcher, 'QQSMTPTransport', _RecordingTransport)
    monkeypatch.setattr('src.launcher.v12_composition.QQSMTPTransport', _RecordingTransport)
    _RecordingTransport.sent.clear()
    calls, waits, busy_pages = [], [], []
    original_goto = GridPage.goto
    navigation_calls = []
    def goto(page, url, **kwargs):
        navigation_calls.append(page)
        if failure_mode == 'navigation_error_page' and len(navigation_calls) <= 5:
            from playwright.sync_api import Error as PageError
            calls.append(True)
            page.url = 'chrome-error://chromewebdata/'
            raise PageError('net::ERR_CONNECTION_RESET synthetic navigation failure')
        return original_goto(page, url, **kwargs)
    monkeypatch.setattr(GridPage, 'goto', goto)
    from contextlib import contextmanager

    from src.inso.quotation_read import QUOTATION_COLUMNS
    session = service._session
    @contextmanager
    def attach():
        if failure_mode == 'session_attach' and len(calls) < 5:
            calls.append(True)
            raise PageTimeout('synthetic CDP attach timeout')
        with session() as handle:
            yield handle
    monkeypatch.setattr(service, '_session', attach)
    dashboard = launcher.read_dashboard_counts
    def counts(*args, **kwargs):
        if failure_mode == 'metadata_timeout':
            target = QuotationInputLocation(WorksheetIdentity('test', '报价输入'), 1, 1, '29')
            GoogleQuotationInput(service, target, expected_columns=QUOTATION_COLUMNS).validate_schema()
        return dashboard(*args, **kwargs)
    monkeypatch.setattr(launcher, 'read_dashboard_counts', counts)
    select = service._select
    def select_sheet(*args):
        if failure_mode == 'metadata_timeout' and len(calls) <= 5:
            raise PageTimeout('synthetic metadata timeout')
        return select(*args)
    monkeypatch.setattr(service, '_select', select_sheet)
    original_wait = Locator.wait_for
    def page_wait(locator, **kwargs):
        if locator.name == '报价工具':
            calls.append(True)
            if len(calls) <= 5 and failure_mode == 'menu_timeout':
                raise PageTimeout('synthetic page load/menu timeout')
        return original_wait(locator, **kwargs)
    monkeypatch.setattr(Locator, 'wait_for', page_wait)
    original_download = service._download
    def read(page, actions):
        if failure_mode == 'timeout_then_busy' and not waits:
            busy_pages.append(page)
            page.popup = 'Synthetic temporary read-only dialog'
            raise PageTimeout('synthetic download timeout followed by busy slot')
        if len(calls) <= 5 and failure_mode == 'read_gid_drift':
            page.url = page.url.split('#')[0] + '#gid=999'
        elif len(calls) <= 5 and failure_mode == 'read_page_closed':
            page.closed = True
        return original_download(page, actions)
    monkeypatch.setattr(service, '_download', read)
    original_path = Download.path
    def artifact_path(download):
        if len(calls) <= 5 and failure_mode == 'artifact_lost':
            download.file.unlink()
        return original_path(download)
    monkeypatch.setattr(Download, 'path', artifact_path)
    backend = launcher.ProductionBackend(root=tmp_path, config_path=rc, production_config_path=production)
    def next_poll(seconds):
        waits.append(seconds)
        backend._publish_poll_wait(seconds)
        assert not backend._stop.is_set() and backend.get_status().next_poll_at is not None
        if len(waits) == 1:
            if failure_mode == 'timeout_then_busy':
                assert len(calls) == 1 and len(busy_pages) == 1
                busy_pages[0].popup = ''  # Site is idle by the next poll.
            else:
                assert len(calls) == 5
            backend._v12_composition.coordinator.run_notifications(now=launcher.utc_now())
            return False
        backend._stop.set()
        return True
    monkeypatch.setattr(backend, '_wait_between_polls', next_poll)
    try:
        backend.start()
        backend._thread.join(timeout=10)
        assert not backend._thread.is_alive() and waits == [900, 900]
        assert len(calls) == (5 if failure_mode == 'timeout_then_busy' else
                              10 if failure_mode == 'metadata_timeout' else 9)
        assert backend.get_health().overall == '正常'
        assert len(_RecordingTransport.sent) == 1
        assert _RecordingTransport.sent[0][1].address == 'linan229@qq.com'
        assert '15分钟后重试' in _RecordingTransport.sent[0][2]
        assert backend._store.all_items() == ()
        assert not original_page.closed
        assert all(p.closed for p in browser.contexts[0].pages[1:])
    finally:
        backend.shutdown()


def test_timeout_does_not_hide_authentication_discovered_by_real_guard(web, monkeypatch):
    from playwright.sync_api import TimeoutError as PageTimeout

    from src.sheets.google_reader import (
        GoogleSheetsReadError,
        GoogleSheetsReadUnavailable,
    )
    from tests.launcher.test_google_quote_update import Locator
    service, browser, _, _ = web
    original = Locator.wait_for
    calls = []
    def wait(locator, **kwargs):
        if locator.name == '报价工具':
            calls.append(True)
            locator.page.login_markers.add('登录')
            raise PageTimeout('synthetic expired login after loading')
        return original(locator, **kwargs)
    monkeypatch.setattr(Locator, 'wait_for', wait)
    with service.poll_scope(), pytest.raises(GoogleSheetsReadError) as caught:
        GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', '2026'))
    assert not isinstance(caught.value, GoogleSheetsReadUnavailable)
    assert len(calls) == 1 and not browser.contexts[0].pages[-1].closed


def test_write_timeout_is_not_translated_to_retryable_read(web, monkeypatch):
    from playwright.sync_api import TimeoutError as PageTimeout

    from src.workflow.v13_quote_update import UpdateAttemptUnconfirmed
    from tests.launcher.test_google_quote_update import Locator
    service, _, _, _ = web
    original = Locator.wait_for
    def wait(locator, **kwargs):
        if locator.name == '报价工具':
            raise PageTimeout('synthetic write-stage setup timeout')
        return original(locator, **kwargs)
    monkeypatch.setattr(Locator, 'wait_for', wait)
    with service.poll_scope(), pytest.raises(UpdateAttemptUnconfirmed):
        service.update(spreadsheetId='test', range="'2026'!F2", valueInputOption='RAW',
                       body={'values': [['NEW']]}).execute()


def test_new_read_diagnostics_remain_sanitized(web, monkeypatch, caplog):
    from playwright.sync_api import Error as PageError

    from src.gui.main import _sanitized_line
    from src.sheets.google_reader import GoogleSheetsReadUnavailable
    from tests.launcher.test_google_quote_update import Locator
    service, _, _, _ = web
    original = Locator.wait_for
    def wait(locator, **kwargs):
        if locator.name == '报价工具':
            raise PageError('net::ERR_CONNECTION_RESET private-customer private-url token=synthetic-secret')
        return original(locator, **kwargs)
    monkeypatch.setattr(Locator, 'wait_for', wait)
    with service.poll_scope(), pytest.raises(GoogleSheetsReadUnavailable):
        GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', '2026'))
    lines = [_sanitized_line(record) for record in caplog.records if record.name == 'inso.diagnostics']
    assert any('google-sheet-ready' in line for line in lines)
    assert any('GOOGLE_WEB_READ_UNAVAILABLE' in line for line in lines)
    assert all('private-' not in line and 'synthetic-secret' not in line for line in lines)


@pytest.mark.parametrize('title', ['2026', 'SHAHAB'])
@pytest.mark.parametrize('failure', ['closed', 'gid_before', 'gid_after', 'range_after'])
def test_read_surface_changes_reject_actual_loss_but_keep_valid_selection(web, monkeypatch, title, failure):
    service, _browser, _, original_page = web
    attempts = []
    download = service._download
    download_path = Download.path
    def read(page, actions):
        attempts.append(page)
        if len(attempts) == 1:
            if failure == 'closed':
                page.closed = True
            elif failure == 'gid_before':
                page.url = page.url.split('#')[0] + '#gid=999'
        return download(page, actions)
    def path(attachment):
        if len(attempts) == 1:
            if failure == 'gid_after':
                attachment.page.url = attachment.page.url.split('#')[0] + '#gid=999'
            elif failure == 'range_after':
                attachment.page.url += '&range=A1'
        return download_path(attachment)
    monkeypatch.setattr(service, '_download', read)
    monkeypatch.setattr(Download, 'path', path)
    with service.poll_scope():
        result = GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', title))
    if failure == 'range_after':
        assert len(attempts) == 1  # Same gid, valid A1 selection is not identity loss.
    else:
        assert len(attempts) == 2 and attempts[0] is not attempts[1]
    assert attempts[-1].title == title
    assert result and not original_page.closed
    assert all(p.closed for p in attempts)
    assert all(not d.file.exists() for p in attempts for d in p.downloads)


@pytest.mark.parametrize('failure', ['auth', 'document', 'unknown'])
def test_download_guard_does_not_retry_wrong_document_auth_or_unknown(web, monkeypatch, failure):
    from src.sheets.google_reader import (
        GoogleSheetsReadError,
        GoogleSheetsReadUnavailable,
    )
    from src.workflow.v13_quote_update import UpdateAttemptUnconfirmed
    service, _, _, _ = web
    calls = []
    download = service._download
    def read(page, actions):
        calls.append(True)
        if failure == 'auth':
            page.login_markers.add('登录')
        elif failure == 'document':
            page.url = 'https://docs.google.com/spreadsheets/d/other/edit#gid=0'
        else:
            raise UpdateAttemptUnconfirmed('UPDATE_RESULT_UNCONFIRMED')
        return download(page, actions)
    monkeypatch.setattr(service, '_download', read)
    with service.poll_scope(), pytest.raises(GoogleSheetsReadError) as caught:
        GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', '2026'))
    assert not isinstance(caught.value, GoogleSheetsReadUnavailable) and len(calls) == 1


def test_write_guard_surface_loss_stays_unconfirmed_without_retry(web, monkeypatch):
    from src.workflow.v13_quote_update import UpdateAttemptUnconfirmed
    service, browser, _, _ = web
    calls = []
    download = service._download
    def read(page, actions):
        calls.append(True)
        page.url = page.url.split('#')[0] + '#gid=999'
        return download(page, actions)
    monkeypatch.setattr(service, '_download', read)
    with service.poll_scope(), pytest.raises(UpdateAttemptUnconfirmed):
        service.update(spreadsheetId='test', range="'2026'!F2", valueInputOption='RAW',
                       body={'values': [['NEW']]}).execute()
    assert len(calls) == 1 and not browser.contexts[0].pages[-1].typed


def test_read_guard_code_is_logged_without_exception_or_page_content(web, monkeypatch, caplog):
    from src.gui.main import _sanitized_line
    from src.sheets.google_reader import GoogleSheetsReadUnavailable
    service, _, _, _ = web
    download = service._download
    def read(page, actions):
        page.url = page.url.split('#')[0] + '#gid=999'
        return download(page, actions)
    monkeypatch.setattr(service, '_download', read)
    with service.poll_scope(), pytest.raises(GoogleSheetsReadUnavailable):
        GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', '2026'))
    lines = [_sanitized_line(r) for r in caplog.records if r.name == 'inso.diagnostics']
    assert any('GOOGLE_OPERATION_SURFACE_UNCONFIRMED' in line for line in lines)
    assert all('range=' not in line and 'gid=' not in line for line in lines)


def test_repeated_source_reads_select_target_without_default_sheet_reload(web, monkeypatch):
    service, browser, _, _ = web
    navigations = []
    original = GridPage.goto
    def goto(page, url, **kwargs):
        navigations.append(url)
        return original(page, url, **kwargs)
    monkeypatch.setattr(GridPage, 'goto', goto)
    with service.poll_scope():
        for title in ('SHAHAB', 'SHAHAB', '2026', 'SHAHAB'):
            service.get(spreadsheetId='test', range=f"'{title}'!A1:G").execute()
            assert sum(not page.closed and page.title == title
                       for page in browser.contexts[0].pages[1:]) == 1
    assert len(navigations) == 2


def test_many_query_only_candidates_share_one_export_per_sheet_stage(web):
    from src.sheets import (
        IdentifyingSnapshot,
        SheetRecordIdentity,
        query_pending_records,
    )
    from src.workflow.dashboard_counts import read_dashboard_counts
    from src.workflow.v13_integration import CombinedCycle
    from src.workflow.v13_quotation import V13QuotationCycle
    from tests.inso.test_v13_quotation_read import NOW
    from tests.workflow.test_v13_quotation import Operations, Quotes, Store
    service, browser, rows, _ = web
    reader = GoogleSheetsRowReader(service)
    worksheets = tuple(WorksheetIdentity('test', title) for title in ('2026', 'SHAHAB'))
    items = []
    for ws in worksheets:
        rows[ws.worksheet] = [list(row) for row in HEADERS[ws.worksheet]]
        for index in range(12):
            model = f'TEST-{ws.worksheet}-{index}'
            cells = (['发给采购', '', 'B', '', model, 'BRAND', '2'] if ws.worksheet == '2026'
                     else ['', '发给采购', '1', model, 'BRAND', '2', 'PCS'])
            rows[ws.worksheet].append(cells)
            importance = 'B' if ws.worksheet == '2026' else None
            identity = SheetRecordIdentity(ws, len(rows[ws.worksheet]),
                                          IdentifyingSnapshot('未发', importance, model, 'BRAND', 2))
            items.append(SimpleNamespace(inquiry_id=model, record_identity=identity,
                                         resolved_brand=None, brand_update_status=None))
    store = Store(items)
    results = []
    inquiry = SimpleNamespace(begin_poll_cycle=lambda: None,
        poll_and_process=lambda r, ws, **kw: query_pending_records(r, ws, discovery=True))
    def quotation(ws):
        cycle = V13QuotationCycle(reader=reader, store=store, operations=Operations(),
            clock=lambda: NOW, wait=lambda _: False, quote_reader=Quotes([()] * 12))
        results.extend(cycle.run(ws))
    combined = CombinedCycle(inquiry, quotation, on_pause=lambda _: pytest.fail('unexpected pause'))
    with service.poll_scope(), reader.discovery_scope():
        counts = read_dashboard_counts(reader, worksheets, store=None, episodes=None, now=NOW)
        assert counts.awaiting_quotation == 24
        combined.run(reader, worksheets, now=NOW)
    assert len(results) == 24 and all(r.outcome.value == 'NO_RECENT_QUOTE' for r in results)
    assert sum(len(p.downloads) for p in browser.contexts[0].pages[1:]) == 2  # shared60s snapshot survives stage boundary


@pytest.mark.parametrize('title,position,model,qty,column', [
    ('2026', 2, '000123', 1200, 6), ('SHAHAB', 3, 'TEST-XYZ', 2, 5),
])
def test_live_source_check_rejects_owner_edit_despite_cached_discovery(web, title, position, model, qty, column):
    from src.sheets import IdentifyingSnapshot, SheetRecordIdentity
    from src.workflow.v13_quotation import (
        QuotationOutcome,
        V13QuotationResult,
        V13SourceRowError,
    )
    from src.workflow.v13_quote_update import WorkflowQuotationSource
    from tests.workflow.test_v13_quotation import Store
    service, _, rows, _ = web
    reader = GoogleSheetsRowReader(service)
    ws = WorksheetIdentity('test', title)
    identity = SheetRecordIdentity(ws, position, IdentifyingSnapshot('未发', 'B' if title == '2026' else None,
                                                                   model, 'OLD', qty))
    item = SimpleNamespace(inquiry_id='test', record_identity=identity,
                           resolved_brand=None, brand_update_status=None)
    result = V13QuotationResult('test', identity, model, QuotationOutcome.QUOTE_FOUND, None)
    source = WorkflowQuotationSource(reader=reader, store=Store([item]))
    with service.poll_scope(), reader.discovery_scope():
        reader.read_discovery_rows(ws)
        rows[title][position - 1][column] = '999'
        with pytest.raises(V13SourceRowError, match='SOURCE_CHANGED'):
            source.read_state(result)


def test_quotation_discovery_sees_inquiry_changes_in_both_sheets(web):
    from src.sheets import query_pending_records, query_quotation_candidates
    from src.workflow.dashboard_counts import read_dashboard_counts
    from src.workflow.v13_integration import CombinedCycle
    from tests.inso.test_v13_quotation_read import NOW
    service, _, rows, _ = web
    reader = GoogleSheetsRowReader(service)
    worksheets = tuple(WorksheetIdentity('test', title) for title in ('2026', 'SHAHAB'))
    rows['2026'][1][0] = rows['SHAHAB'][2][1] = '未发'
    def inquiry(r, ws, **_):
        assert len(query_pending_records(r, ws, discovery=True)) == 1
        if ws.worksheet == '2026':
            target = "'2026'!A2"
        else:
            target = "'SHAHAB'!B3"
        # Model the real canonical write, which invalidates the shared snapshot.
        service.update(spreadsheetId='test', range=target, valueInputOption='RAW',
                       body={'values': [['发给采购']]}).execute()
    quotations = []
    combined = CombinedCycle(SimpleNamespace(begin_poll_cycle=lambda: None, poll_and_process=inquiry),
        lambda ws: quotations.extend(query_quotation_candidates(reader, ws, discovery=True)),
        on_pause=lambda _: pytest.fail('unexpected pause'))
    with service.poll_scope(), reader.discovery_scope():
        assert read_dashboard_counts(reader, worksheets, store=None, episodes=None, now=NOW).new_orders == 2
        combined.run(reader, worksheets, now=NOW)
    assert len(quotations) == 2 and all(r.status == '发给采购' for r in quotations)


@pytest.mark.parametrize('auth_on_fifth', [False, True])
def test_real_web_guard_four_failures_then_fifth_recovers_or_auth_stops(web, monkeypatch, auth_on_fifth):
    from playwright.sync_api import TimeoutError as PageTimeout

    from src.sheets.google_reader import (
        GoogleSheetsReadError,
        GoogleSheetsReadUnavailable,
    )
    from tests.launcher.test_google_quote_update import Locator
    service, browser, _, _ = web
    attempts = []
    original = Locator.wait_for
    def wait(locator, **kwargs):
        if locator.name == '报价工具':
            attempts.append(locator.page)
            if len(attempts) < 5:
                raise PageTimeout('synthetic intermittent load')
            if auth_on_fifth:
                locator.page.login_markers.add('登录')
        return original(locator, **kwargs)
    monkeypatch.setattr(Locator, 'wait_for', wait)
    with service.poll_scope():
        if auth_on_fifth:
            with pytest.raises(GoogleSheetsReadError) as caught:
                GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', 'SHAHAB'))
            assert not isinstance(caught.value, GoogleSheetsReadUnavailable)
        else:
            assert GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', 'SHAHAB'))
    assert len(attempts) == len({id(p) for p in attempts}) == 5
    assert all(p.closed for p in attempts[:4])
    assert attempts[-1].closed is not auth_on_fifth
    assert not browser.contexts[0].pages[0].closed


@pytest.mark.parametrize('title,position', [('2026', 2), ('SHAHAB', 3)])
def test_purchase_status_writer_commits_grid_without_formula_dom_fill(web, monkeypatch, title, position):
    from src.sheets.google_writer import GoogleSheetsPurchaseStatusWriter
    from src.sheets.worksheet_schema import worksheet_schema
    service, _, rows, _ = web
    schema = worksheet_schema(title)
    column = ord(schema.status_column) - 65
    rows[title][position - 1][column] = '未发'
    fill = GridLocator.fill
    def no_formula_fill(locator, value):
        assert locator.kind != 'editor', 'DOM-only edits never commit Sheets data'
        return fill(locator, value)
    monkeypatch.setattr(GridLocator, 'fill', no_formula_fill)
    GoogleSheetsPurchaseStatusWriter(service).write_purchase_status(WorksheetIdentity('test', title), position)
    assert rows[title][position - 1][column] == '发给采购'


def test_grid_write_requires_focus_to_leave_name_box(web, monkeypatch):
    service, browser, rows, _ = web
    monkeypatch.setattr(GridLocator, 'evaluate', lambda *a: True)
    old = [list(row) for row in rows['2026']]
    with pytest.raises(GoogleSheetsWriteError):
        GoogleSheetsBrandWriter(service).write_brand(WorksheetIdentity('test', '2026'), 2, 'NEW')
    assert rows['2026'] == old and not browser.contexts[0].pages[-1].typed


def test_lost_owned_export_retries_fresh_read_without_hiding_other_missing_files(web, monkeypatch, caplog):
    service, browser, _, _ = web
    path = Download.path
    calls = []
    def lose_once(download):
        calls.append(download)
        if len(calls) == 1:
            download.file.unlink()
        return path(download)
    monkeypatch.setattr(Download, 'path', lose_once)
    with service.poll_scope():
        assert GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', 'SHAHAB'))
    assert len(calls) == 2 and calls[0].page is not calls[1].page
    assert all(p.closed for p in browser.contexts[0].pages[1:])
    assert all(not d.file.exists() for d in calls)
    assert any(getattr(r, 'runtime_reason', None) == 'GOOGLE_WEB_READ_ARTIFACT_LOST' for r in caplog.records)


def test_already_deleted_download_cleanup_does_not_fail_a_valid_read(web, monkeypatch):
    service, _, _, _ = web
    def gone(download):
        download.file.unlink()
        raise FileNotFoundError('synthetic already removed export')
    monkeypatch.setattr(Download, 'delete', gone)
    assert GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', '2026'))


def test_lost_export_after_grid_commit_stays_uncertain_and_never_repeats_write(web, monkeypatch):
    service, browser, rows, _ = web
    path = Download.path
    def lose_readback(download):
        if download.page.typed:
            download.file.unlink()
        return path(download)
    monkeypatch.setattr(Download, 'path', lose_readback)
    with pytest.raises(GoogleSheetsWriteError):
        GoogleSheetsBrandWriter(service).write_brand(WorksheetIdentity('test', '2026'), 2, 'NEW')
    page = browser.contexts[0].pages[-1]
    assert rows['2026'][1][5] == 'NEW' and page.typed == ["'NEW"] and not page.closed


def test_write_failure_logs_fixed_stage_and_reason_without_values(web, monkeypatch, caplog):
    from src.gui.main import _sanitized_line
    service, _, _, _ = web
    monkeypatch.setattr(GridLocator, 'evaluate', lambda *a: True)
    with pytest.raises(GoogleSheetsWriteError):
        GoogleSheetsBrandWriter(service).write_brand(WorksheetIdentity('test', '2026'), 2, 'PRIVATE-TEST-VALUE')
    lines = [_sanitized_line(r) for r in caplog.records if r.name == 'inso.diagnostics']
    assert any('google-write-select-cell' in line for line in lines)
    assert any('GOOGLE_SELECTION_UNCONFIRMED' in line for line in lines)
    assert all('PRIVATE-TEST-VALUE' not in line for line in lines)


@pytest.mark.parametrize('failure', ['network', 'timeout', 'certificate', 'unknown', 'wrong_document', 'auth'])
def test_navigation_error_page_preserves_transport_classification(web, monkeypatch, failure):
    from playwright.sync_api import Error as PageError
    from playwright.sync_api import TimeoutError as PageTimeout

    from src.sheets.google_reader import (
        GoogleSheetsReadError,
        GoogleSheetsReadUnavailable,
    )
    service, browser, _, _ = web
    original = GridPage.goto
    attempts = []
    def goto(page, url, **kwargs):
        attempts.append(page)
        if len(attempts) == 1:
            page.url = 'chrome-error://chromewebdata/'
            if failure == 'wrong_document':
                page.url = 'https://docs.google.com/spreadsheets/d/other/edit#gid=0'
            elif failure == 'auth':
                page.url = 'https://accounts.google.com/'
            if failure == 'timeout':
                raise PageTimeout('synthetic navigation timeout')
            codes = {'certificate': 'ERR_CERT_AUTHORITY_INVALID', 'unknown': 'ERR_FAILED'}
            raise PageError('net::' + codes.get(failure, 'ERR_CONNECTION_RESET'))
        return original(page, url, **kwargs)
    monkeypatch.setattr(GridPage, 'goto', goto)
    with service.poll_scope():
        if failure in {'network', 'timeout'}:
            assert GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', '2026'))
            assert len(attempts) == 2 and attempts[0].closed
        else:
            with pytest.raises(GoogleSheetsReadError) as caught:
                GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', '2026'))
            assert not isinstance(caught.value, GoogleSheetsReadUnavailable)
            assert len(attempts) == 1
    assert not browser.contexts[0].pages[0].closed


@pytest.mark.parametrize('title', ['2026', 'SHAHAB'])
def test_late_worksheet_tab_is_awaited_before_document_failure(web, monkeypatch, title):
    service, _, _, _ = web
    pending, awaited = {title}, []
    count, wait = GridLocator.count, GridLocator.wait_for
    def delayed_count(locator):
        if locator.kind == 'tab' and locator.name in pending:
            return 0
        return count(locator)
    def delayed_wait(locator, **kwargs):
        if locator.kind == 'tab' and locator.name in pending:
            assert kwargs == {'state': 'visible', 'timeout': 10000}
            awaited.append(locator.name)
            pending.remove(locator.name)
        return wait(locator, **kwargs)
    monkeypatch.setattr(GridLocator, 'count', delayed_count)
    monkeypatch.setattr(GridLocator, 'wait_for', delayed_wait)
    with service.poll_scope():
        assert GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', title))
    assert awaited == [title]


def test_hidden_login_text_does_not_stop_verified_document_read(web, monkeypatch):
    service, _, _, _ = web
    goto = GridPage.goto
    def hidden_login(page, url, **kwargs):
        result = goto(page, url, **kwargs)
        page.login_markers.add('登录')
        page.hidden_markers = {'登录'}
        return result
    monkeypatch.setattr(GridPage, 'goto', hidden_login)
    with service.poll_scope():
        assert GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', '2026'))


def test_metadata_exhaustion_reaches_updater_without_opening_or_writing_input(web, monkeypatch):
    from playwright.sync_api import TimeoutError as PageTimeout

    from src.inso.quotation_read import QUOTATION_COLUMNS
    from src.sheets.google_reader import GoogleSheetsReadUnavailable
    from src.workflow.v13_quote_update import V13QuotationUpdater
    from tests.workflow.test_v13_quote_update import Actions, Source, found
    service, browser, _, _ = web
    original = service._select
    selected, waits = [], []
    def select(page, actions, title):
        selected.append(title)
        raise PageTimeout('synthetic metadata selection timeout')
    monkeypatch.setattr(service, '_select', select)
    location = QuotationInputLocation(WorksheetIdentity('fake-sheet', '报价输入'), 1, 1, '29')
    adapter = GoogleQuotationInput(service, location, expected_columns=QUOTATION_COLUMNS,
                                  retry_wait=lambda seconds: waits.append(seconds) or False)
    source = Source()
    actions = Actions(source)
    updater = V13QuotationUpdater(source=source, quotation_input=adapter, actions=actions, wait=lambda _: False)
    with service.poll_scope(), pytest.raises(GoogleSheetsReadUnavailable):
        updater.update_one(found())
    assert len(selected) == 5 and waits == [2, 4, 6, 8]
    assert actions.opened == actions.clicks == 0
    assert all(not p.typed for p in browser.contexts[0].pages[1:])
    monkeypatch.setattr(service, '_select', original)
    with service.poll_scope():
        adapter.validate_schema()
    assert all(p.closed for p in browser.contexts[0].pages[1:])


@pytest.mark.parametrize('failure', ['certificate', 'unknown'])
def test_metadata_permanent_failure_is_not_retried(web, monkeypatch, failure):
    from playwright.sync_api import Error as PageError

    from src.inso.quotation_read import QUOTATION_COLUMNS
    service, _, _, _ = web
    attempts = []
    def select(*args):
        attempts.append(True)
        raise PageError('net::' + ('ERR_CERT_AUTHORITY_INVALID' if failure == 'certificate' else 'ERR_FAILED'))
    monkeypatch.setattr(service, '_select', select)
    location = QuotationInputLocation(WorksheetIdentity('test', '报价输入'), 1, 1, '29')
    adapter = GoogleQuotationInput(service, location, expected_columns=QUOTATION_COLUMNS)
    with service.poll_scope(), pytest.raises(QuotationInputUnavailable):
        adapter.validate_schema()
    assert len(attempts) == 1


@pytest.mark.parametrize('write', [False, True])
def test_navigation_network_error_does_not_replay_writes(web, monkeypatch, write):
    from playwright.sync_api import Error as PageError

    from src.workflow.v13_quote_update import UpdateAttemptUnconfirmed
    service, browser, _, _ = web
    attempts = []
    def goto(page, url, **kwargs):
        attempts.append(page)
        page.url = 'chrome-error://chromewebdata/'
        raise PageError('net::ERR_CONNECTION_RESET synthetic private-url')
    monkeypatch.setattr(GridPage, 'goto', goto)
    with service.poll_scope():
        if write:
            with pytest.raises(UpdateAttemptUnconfirmed, match='GOOGLE_NAVIGATION_FAILED'):
                service.update(spreadsheetId='test', range="'2026'!F2", valueInputOption='RAW',
                               body={'values': [['NEW']]}).execute()
        else:
            with pytest.raises(TimeoutError, match='GOOGLE_WEB_READ_UNAVAILABLE'):
                service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
    assert len(attempts) == 1 and not attempts[0].typed
    assert attempts[0].closed and not browser.contexts[0].pages[0].closed


def test_navigation_guard_diagnostics_distinguish_causes_without_urls(web, monkeypatch, caplog):
    from src.gui.main import _sanitized_line
    from src.launcher.google_quote_update import GoogleQuotationUpdateActions
    service, _, _, _ = web
    original = GoogleQuotationUpdateActions._guard
    def wrong_document(actions):
        if actions._page and actions._page.url.startswith('https://docs.google.com/'):
            actions._page.url = 'https://docs.google.com/spreadsheets/d/private-id/edit#gid=0'
        return original(actions)
    monkeypatch.setattr(GoogleQuotationUpdateActions, '_guard', wrong_document)
    with service.poll_scope(), pytest.raises(V12Fault):
        service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
    lines = [_sanitized_line(r) for r in caplog.records if r.name == 'inso.diagnostics']
    assert any('google-document-path-mismatch' in line for line in lines)
    assert all('private-id' not in line and 'https://' not in line for line in lines)



def test_repeated_auth_polls_reuse_preserved_page_instead_of_opening_more(web, monkeypatch):
    service, browser, _, _ = web
    goto = GridPage.goto
    def auth(page, url, **kwargs):
        result = goto(page, url, **kwargs)
        page.url = 'https://accounts.google.com/'
        return result
    monkeypatch.setattr(GridPage, 'goto', auth)
    for _ in range(4):
        with service.poll_scope(), pytest.raises(V12Fault, match='GOOGLE_AUTHENTICATION_REQUIRED'):
            service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
    assert len(browser.contexts[0].pages) == 2
    retained = browser.contexts[0].pages[-1]
    assert not retained.closed and retained.read_failed
    retained.url = 'https://docs.google.com/spreadsheets/d/test/edit#gid=0'
    monkeypatch.setattr(GridPage, 'goto', goto)
    with service.poll_scope():
        assert service.get(spreadsheetId='test', range="'2026'!A1:G").execute()['values']
    assert retained.closed


def test_only_successful_reads_signal_site_recovery_not_failed_reads_or_writes(web, monkeypatch):
    from playwright.sync_api import TimeoutError as PageTimeout
    service, _, _, _ = web
    recovered = []
    service._on_read_success = lambda: recovered.append(True)
    service.update(spreadsheetId='test', range="'2026'!F2", valueInputOption='RAW', body={'values': [['NEW']]}).execute()
    assert not recovered
    download = service._download
    monkeypatch.setattr(service, '_download', lambda *a: (_ for _ in ()).throw(PageTimeout('synthetic failed read')))
    with pytest.raises(TimeoutError):
        service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
    assert not recovered
    monkeypatch.setattr(service, '_download', download)
    assert service.get(spreadsheetId='test', range="'2026'!A1:G").execute()['values']
    assert recovered == [True]



def test_native_nested_module_scope_can_read_with_three_live_parent_surfaces(web):
    service, browser, _rows, human = web
    reader = GoogleSheetsRowReader(service, retry_wait=lambda _: True)
    with service.poll_scope(), reader.discovery_scope():
        for title in ('2026', 'SHAHAB'):
            reader.read_discovery_rows(WorksheetIdentity('test', title))
        service.get(spreadsheetId='test', range="'报价输入'!A1:N1").execute()
        parents = tuple(p for p in browser.contexts[0].pages if p is not human and not p.closed)
        assert len(parents) == 3
        with service.poll_scope(), reader.discovery_scope():
            fresh = reader.read_rows(WorksheetIdentity('test', '2026'))
            assert fresh[1].cells['E'] == '000123'  # Native live check, not cache.
            children = [p for p in browser.contexts[0].pages if p not in parents and p is not human]
            assert children == []  # Borrow the already verified2026 slot.
        assert all(not p.closed for p in parents)
    assert all(p.closed for p in parents) and not human.closed



def test_four_exact_sheet_slots_reused_across_nested_modules(web, monkeypatch):
    from src.sheets.tp_brief import BRIEF_HEADERS, BriefReader
    service, browser, rows, human = web
    monkeypatch.setitem(TITLES, 'RFQ_BRIEF', 31)
    rows['RFQ_BRIEF'] = [list(BRIEF_HEADERS)]
    reader = GoogleSheetsRowReader(service)
    brief = BriefReader(service)
    def read_all_live():
        reader.read_rows(WorksheetIdentity('test', '2026'))
        reader.read_rows(WorksheetIdentity('test', 'SHAHAB'))
        brief.read('test')
        service.get(spreadsheetId='test', range="'报价输入'!A1:N1").execute()
    with service.poll_scope():
        read_all_live()
        slots = tuple(p for p in browser.contexts[0].pages if p is not human)
        assert len(slots) == 4
        for _module in range(3):
            with service.poll_scope():
                read_all_live()
            assert tuple(p for p in browser.contexts[0].pages if p is not human) == slots
            assert all(not p.closed for p in slots)
    assert all(p.closed for p in slots) and not human.closed


def test_four_sheets_real_transport_reads_queue_under_original_grid_lock(web, monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from src.sheets.tp_brief import BRIEF_HEADERS
    service, browser, rows, _human = web
    monkeypatch.setitem(TITLES, 'RFQ_BRIEF', 31)
    rows['RFQ_BRIEF'] = [list(BRIEF_HEADERS)]
    barrier = threading.Barrier(4)
    entered = threading.Event()
    release = threading.Event()
    counter_lock = threading.Lock()
    active, peak = [0], [0]
    native = service._download
    def observed_download(*args):
        with counter_lock:
            active[0] += 1
            peak[0] = max(peak[0], active[0])
            is_first = not entered.is_set()
            if is_first:
                entered.set()
        try:
            if is_first:
                assert release.wait(5)
            return native(*args)
        finally:
            with counter_lock:
                active[0] -= 1
    monkeypatch.setattr(service, '_download', observed_download)
    def read(title):
        barrier.wait(timeout=5)
        if title == 'RFQ_BRIEF':
            return service.read_brief('test')
        return service.get(spreadsheetId='test', range=f"'{title}'!A1:G1").execute()
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(read, title) for title in ('2026', 'SHAHAB', 'RFQ_BRIEF', '报价输入')]
        assert entered.wait(5)
        assert peak[0] == 1
        release.set()
        assert all(isinstance(f.result(timeout=10), dict) for f in futures)
    assert peak[0] == 1 and active[0] == 0
    assert all(page.closed for page in browser.contexts[0].pages[1:])


@pytest.mark.parametrize('scoped', [False, True])
def test_retained_four_tabs_survive_polls_and_reopen_only_closed_target(web, monkeypatch, scoped):
    from src.sheets.tp_brief import BRIEF_HEADERS
    service, browser, rows, original = web
    service._retained_pages = {}
    monkeypatch.setitem(TITLES, 'RFQ_BRIEF', 31)
    rows['RFQ_BRIEF'] = [list(BRIEF_HEADERS)]

    def read_all():
        with service.poll_scope() if scoped else nullcontext():
            for title in ('2026', 'SHAHAB', 'RFQ_BRIEF', '报价输入'):
                if title == 'RFQ_BRIEF':
                    service.read_brief('test')
                else:
                    service.get(spreadsheetId='test', range=f"'{title}'!A1:G1").execute()

    read_all()
    pages = browser.contexts[0].pages[1:]
    assert len(pages) == 4 and all(not p.closed for p in pages)
    assert all(isinstance(target, str) and isinstance(protected, bool)
               for target, protected, _ in service._retained_pages.values())
    for _ in range(4):
        read_all()
    assert browser.contexts[0].pages[1:] == pages
    pages[1].close()  # Owner accidentally closes exactly SHAHAB.
    read_all()
    assert len(browser.contexts[0].pages) == 6
    assert browser.contexts[0].pages[-1].title == 'SHAHAB'
    assert all(not p.closed for p in (pages[0], pages[2], pages[3], original))
    assert sum(not p.closed for p in browser.contexts[0].pages[1:]) == 4


@pytest.mark.parametrize('problem', ['auth', 'document', 'ownership', 'pending'])
def test_retained_target_revalidated_without_replacing_protected_page(web, problem):
    service, browser, _, original = web
    from src.sheets.quotation_input import QuotationInputBusy
    service._retained_pages = {}
    with service.poll_scope():
        service.get(spreadsheetId='test', range="'2026'!A1:G1").execute()
    page = browser.contexts[0].pages[-1]
    if problem == 'auth':
        page.login_markers.add('登录')
    elif problem == 'document':
        page.url = 'https://docs.google.com/spreadsheets/d/other/edit#gid=0'
    elif problem == 'ownership':
        page.owner_name = ''
    else:
        page.refresh_pending = True
    with service.poll_scope(), pytest.raises((V12Fault, QuotationInputBusy, TimeoutError)):

        service.get(spreadsheetId='test', range="'2026'!A1:G1").execute()
    assert not page.closed and not original.closed
    assert len(browser.contexts[0].pages) == 2  # No blind replacement or takeover.


def test_retained_unknown_write_closed_target_never_reopens_or_replays(web):
    service, browser, _, original = web
    service._retained_pages = {}
    with service.poll_scope():
        service.get(spreadsheetId='test', range="'2026'!A1:G1").execute()
        page = browser.contexts[0].pages[-1]
        page.save_fails = True
        with pytest.raises(QuotationInputUnavailable):
            service.update(spreadsheetId='test', range="'2026'!F2",
                           valueInputOption='RAW', body={'values': [['TEST']]}).execute()
        page.close()
    assert next(iter(service._retained_pages.values()))[1] is True
    with service.poll_scope(), pytest.raises(V12Fault, match='SETTLEMENT_UNCONFIRMED'):
        service.get(spreadsheetId='test', range="'2026'!A1:G1").execute()
    assert len(browser.contexts[0].pages) == 2 and not original.closed


def test_retained_safe_failed_read_recovers_without_accumulating_tabs(web):
    service, browser, _, _ = web
    service._retained_pages = {}
    create = browser.contexts[0].new_page
    first = []
    def once():
        page = create()
        if not first:
            page.menu_failure = True
            first.append(page)
        return page
    browser.contexts[0].new_page = once
    with service.poll_scope():
        result = GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', '2026'))
    assert result and first[0].closed
    assert sum(not p.closed for p in browser.contexts[0].pages[1:]) == 1


def test_retained_cache_hit_does_not_reopen_closed_page_until_live_read_due(web):
    service, browser, _, _ = web
    service._retained_pages = {}
    now = [0.0]
    service._timer = lambda: now[0]
    with service.poll_scope():
        expected = service.get_discovery(spreadsheetId='test', range="'2026'!A1:G").execute()
    page = browser.contexts[0].pages[-1]
    page.close()
    now[0] = 59.99
    with service.poll_scope():
        assert service.get_discovery(spreadsheetId='test', range="'2026'!A1:G").execute() == expected
    assert len(browser.contexts[0].pages) == 2
    now[0] = 60.0
    with service.poll_scope():
        assert service.get_discovery(spreadsheetId='test', range="'2026'!A1:G").execute() == expected
    assert len(browser.contexts[0].pages) == 3 and not browser.contexts[0].pages[-1].closed


def test_retained_stop_blocks_reopening_and_native_identity_failure_stops(web):
    service, browser, _, _ = web
    service._retained_pages = {}
    with service.poll_scope():
        service.get(spreadsheetId='test', range="'2026'!A1:G1").execute()
    page = browser.contexts[0].pages[-1]
    page.close()
    service._stop_requested = lambda: True
    from src.workflow.v13_quotation import V13Stopped
    with service.poll_scope(), pytest.raises(V13Stopped):
        service.get(spreadsheetId='test', range="'2026'!A1:G1").execute()
    assert len(browser.contexts[0].pages) == 2
    service._stop_requested = lambda: False
    browser.contexts[0].new_cdp_session = lambda p: (_ for _ in ()).throw(RuntimeError('synthetic proof loss'))
    with service.poll_scope(), pytest.raises(V12Fault, match='IDENTITY_UNCONFIRMED'):
        service.get(spreadsheetId='test', range="'2026'!A1:G1").execute()
    assert len(browser.contexts[0].pages) == 2
