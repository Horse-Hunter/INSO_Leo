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
