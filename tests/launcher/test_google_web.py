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
        if self.kind == 'tab':
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
        assert key == 'Enter'
        if self.kind == 'editor':
            cell = self.page.selection
            col, row = ord(cell[0])-65, int(cell[1:])-1
            rows = self.page.rows[self.page.title]
            while len(rows) <= row:
                rows.append([])
            while len(rows[row]) <= col:
                rows[row].append('')
            text = self.page.edit
            rows[row][col] = text.removeprefix("'")

    def input_value(self):
        return self.page.selection


class GridPage(Page):
    def __init__(self, context, rows, tmp):
        super().__init__(context)
        self.rows, self.tmp, self.title = rows, tmp, '2026'
        self.typed, self.downloads = [], []
        self.save_fails = False

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


def test_poll_reuses_one_page_across_both_sources_and_raw14_then_closes(web):
    service, browser, _, original = web
    with service.poll_scope():
        for title in ('2026', 'SHAHAB', '2026'):
            service.get(spreadsheetId='test', range=f"'{title}'!A1:G").execute()
        service.update(spreadsheetId='test', range="'报价输入'!A1:N1",
                       valueInputOption='RAW', body={'values': [['TEST'] * 14]}).execute()
        assert len(browser.contexts[0].pages) == 2
        assert not browser.contexts[0].pages[-1].closed
    assert browser.contexts[0].pages[-1].closed and not original.closed
    with service.poll_scope():
        service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
    assert len(browser.contexts[0].pages) == 3 and browser.contexts[0].pages[-1].closed


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


def test_updater_and_web_transport_share_one_page_despite_interleaved_source_reads(web):
    from src.launcher.google_quote_update import GoogleQuotationUpdateActions
    service, browser, _, original = web
    location = QuotationInputLocation(WorksheetIdentity('test', '报价输入'), 1, 1, '29')
    with service.poll_scope():
        actions = GoogleQuotationUpdateActions(browser_handle=BrowserHandle(owned=False, browser=browser),
                                               location=location)
        actions.open_quote_input()
        for title in ('2026', 'SHAHAB'):
            service.get(spreadsheetId='test', range=f"'{title}'!A1:G").execute()
        service.update(spreadsheetId='test', range="'报价输入'!A1:N1", valueInputOption='RAW',
                       body={'values': [['TEST'] * 14]}).execute()
        actions.click_update_quote()
        assert '成功填入' in actions.read_update_result()
        actions.dismiss_result()
        # Source status checks after script completion may select the source tab.
        service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
        actions.close()
        assert len(browser.contexts[0].pages) == 2
    assert browser.contexts[0].pages[-1].closed and not original.closed


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
    assert len(calls) == 2


@pytest.mark.parametrize('failure', ['unknown', 'cert', 'auth', 'schema', 'wrapper_without_cause'])
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


def test_google_web_timeout_exhaustion_notifies_once_and_actual_poller_runs_next_cycle(web, tmp_path, monkeypatch):
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
    monkeypatch.setattr(launcher, 'assess_readiness', lambda *a, **kw: SimpleNamespace(ready=True, missing_site_ids=()))
    monkeypatch.setattr(launcher, 'build_research_service', lambda *a, **kw: SimpleNamespace(execute=lambda _: None))
    monkeypatch.setattr(launcher, 'QQSMTPTransport', _RecordingTransport)
    monkeypatch.setattr('src.launcher.v12_composition.QQSMTPTransport', _RecordingTransport)
    _RecordingTransport.sent.clear()
    calls, waits = [], []
    original_wait = Locator.wait_for
    def page_wait(locator, **kwargs):
        if locator.name == '报价工具':
            calls.append(True)
            if len(calls) <= 2:
                raise PageTimeout('synthetic page load/menu timeout')
        return original_wait(locator, **kwargs)
    monkeypatch.setattr(Locator, 'wait_for', page_wait)
    backend = launcher.ProductionBackend(root=tmp_path, config_path=rc, production_config_path=production)
    def next_poll(seconds):
        waits.append(seconds)
        assert not backend._stop.is_set() and backend.get_status().next_poll_at is not None
        if len(waits) == 1:
            assert len(calls) == 2
            backend._v12_composition.coordinator.run_notifications(now=launcher.utc_now())
            return False
        backend._stop.set()
        return True
    monkeypatch.setattr(backend, '_wait_between_polls', next_poll)
    try:
        backend.start()
        backend._thread.join(timeout=10)
        assert not backend._thread.is_alive() and waits == [900, 900]
        assert len(calls) > 2 and backend.get_health().overall == '正常'
        assert len(_RecordingTransport.sent) == 1
        assert _RecordingTransport.sent[0][1].address == 'linan229@qq.com'
        assert '15分钟后重试' in _RecordingTransport.sent[0][2]
        assert backend._store.all_items() == ()
        assert not original_page.closed and all(p.closed for p in browser.contexts[0].pages[1:])
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
