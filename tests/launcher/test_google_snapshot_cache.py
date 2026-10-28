"""Shared60s ordinary snapshots; native guard/effect paths remain live. Synthetic UI only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

import pytest

from src.launcher.backend import ProductionBackend
from src.research.cdp_pages import PageResourceAdmission, PageTargetOwnershipError
from src.sheets import WorksheetIdentity
from src.sheets.google_reader import GoogleSheetsReadError, GoogleSheetsRowReader
from src.sheets.tp_brief import BRIEF_HEADERS, BriefReader
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_quotation import V13Stopped
from tests.launcher.test_google_web import TITLES, web  # noqa: F401
from tests.research.test_tp import NOW
from tests.sheets.test_tp_brief import brief
from tests.workflow.test_tp_research import build


def downloads(browser):
    return sum(len(p.downloads) for p in browser.contexts[0].pages[1:])


@pytest.fixture
def cached(request, monkeypatch):
    service, browser, rows, _original = request.getfixturevalue("web")
    monkeypatch.setitem(TITLES, 'RFQ_BRIEF', 31)
    rows['RFQ_BRIEF'] = [list(BRIEF_HEADERS)]
    clock = SimpleNamespace(now=0.0)
    service._timer = lambda: clock.now
    return service, browser, rows, clock


@pytest.mark.parametrize('title', ['2026', 'SHAHAB', 'RFQ_BRIEF'])
def test_expiry_exact_boundary_cross_reader_and_cycle_mutation_isolation(cached, title):
    service, browser, _rows, clock = cached
    def read():
        if title == 'RFQ_BRIEF':
            return service.read_brief_discovery('test')
        return service.get_discovery(spreadsheetId='test', range=f"'{title}'!A1:G").execute()
    first = read()
    first['values'][0][0] = 'poison'
    clock.now = 59.999
    assert read()['values'][0][0] != 'poison'
    assert downloads(browser) == 1
    clock.now = 60.0
    assert read()['values'][0][0] != 'poison'
    assert downloads(browser) == 2
    if title != 'RFQ_BRIEF':
        for _ in range(3):
            reader = GoogleSheetsRowReader(service)
            with service.poll_scope(), reader.discovery_scope():
                reader.read_discovery_rows(WorksheetIdentity('test', title))
        assert downloads(browser) == 2


def test_independent_expiry_document_keys_and_bounded_storage(cached):
    service, browser, _rows, clock = cached
    def read(doc, title):
        return service.get_discovery(spreadsheetId=doc, range=f"'{title}'!A1:G").execute()
    read('test', '2026')
    clock.now = 20
    read('test', 'SHAHAB')
    clock.now = 40
    service.read_brief_discovery('test')
    clock.now = 60
    read('test', '2026')
    read('test', 'SHAHAB')
    service.read_brief_discovery('test')
    assert downloads(browser) == 4  # Only2026 expired.
    read('other', '2026')
    assert downloads(browser) == 5
    for n in range(9):
        read(f'doc-{n}', '2026')
    assert len(service._snapshots) == 6


def test_single_flight_concurrent_discovery_and_completion_based_ttl(cached, monkeypatch):
    service, browser, _rows, clock = cached
    native = service._download
    def slow_download(*args):
        answer = native(*args)
        clock.now = 17  # Successful acquisition, not request start, starts TTL.
        return answer
    monkeypatch.setattr(service, '_download', slow_download)
    barrier = Barrier(4)
    def read(_):
        barrier.wait(timeout=5)
        return GoogleSheetsRowReader(service).read_discovery_rows(WorksheetIdentity('test', '2026'))
    with ThreadPoolExecutor(max_workers=4) as pool:
        answers = tuple(pool.map(read, range(4)))
    assert downloads(browser) == 1 and len(answers) == 4
    clock.now = 76.999
    read_response = service.get_discovery(spreadsheetId='test', range="'2026'!A2:G").execute()
    assert read_response['values'][0][4] == '000123' and downloads(browser) == 1
    clock.now = 77
    service.get_discovery(spreadsheetId='test', range="'2026'!A1:G").execute()
    assert downloads(browser) == 2


@pytest.mark.parametrize('failure', ['busy', 'auth', 'gid', 'schema', 'missing', 'oversize', 'cancel'])
def test_failures_evict_all_sheets_and_never_fallback_to_stale(cached, monkeypatch, failure):
    from src.sheets.quotation_input import QuotationInputBusy
    from tests.launcher.test_google_web import Download
    service, _browser, rows, clock = cached
    reader = GoogleSheetsRowReader(service, retry_wait=lambda _: True)
    ws = WorksheetIdentity('test', '2026')
    reader.read_discovery_rows(ws)
    reader.read_discovery_rows(WorksheetIdentity('test', 'SHAHAB'))
    clock.now = 60
    if failure == 'schema':
        rows['2026'][0][4] = 'wrong header'
    elif failure in {'missing', 'oversize'}:
        native = Download.path
        def invalid_path(download):
            if failure == 'missing':
                download.file.unlink()
            else:
                with download.file.open('r+b') as stream:
                    stream.truncate(32 * 1024 * 1024 + 1)
            return native(download)
        monkeypatch.setattr(Download, 'path', invalid_path)
    else:
        def fail(*args, **kwargs):
            if failure == 'busy':
                raise QuotationInputBusy('GOOGLE_QUOTATION_INPUT_BUSY')
            if failure == 'cancel':
                raise V13Stopped()
            raise V12Fault(FaultScope.GLOBAL_STOP,
                           'GOOGLE_SHEET_UNCONFIRMED' if failure == 'gid' else 'SESSION_IDENTITY_UNVERIFIED')
        monkeypatch.setattr(service, '_download', fail)
    with pytest.raises((GoogleSheetsReadError, V13Stopped)):
        reader.read_discovery_rows(ws)
    assert not service._snapshots
    with pytest.raises((GoogleSheetsReadError, V13Stopped)):
        reader.read_discovery_rows(ws)
    assert not service._snapshots


def test_hits_respect_shared_admission_stop_and_do_not_clear_existing_outage(cached, tmp_path):
    service, browser, _rows, _clock = cached
    backend = ProductionBackend(root=tmp_path)
    reader = GoogleSheetsRowReader(service)
    ws = WorksheetIdentity('test', '2026')
    backend._store = None
    callbacks = []
    service._on_read_success = lambda: callbacks.append(True)
    backend._refresh_dashboard_counts(reader, (ws,), episodes=None, now=NOW)
    backend._site_outages['Google Sheets'] = 0
    backend._refresh_dashboard_counts(reader, (ws,), episodes=None, now=NOW)
    assert downloads(browser) == 1 and len(callbacks) == 1
    assert 'Google Sheets' in backend._site_outages
    admission = PageResourceAdmission()
    service._read_guard = admission.require_open
    admission.invalidate(PageTargetOwnershipError(()))
    with pytest.raises(GoogleSheetsReadError):
        reader.read_discovery_rows(ws)
    assert not service._snapshots and len(callbacks) == 1
    service._read_guard = lambda: None
    reader.read_discovery_rows(ws)
    service._stop_requested = lambda: True
    with pytest.raises(GoogleSheetsReadError):
        reader.read_discovery_rows(ws)
    assert not service._snapshots and downloads(browser) == 2


@pytest.mark.parametrize('failed_write', [False, True])
def test_native_write_invalidates_and_keeps_prewrite_and_readback_live(cached, failed_write, monkeypatch):
    from tests.launcher.test_google_web import GridPage
    service, browser, _rows, _clock = cached
    reader = GoogleSheetsRowReader(service)
    ws = WorksheetIdentity('test', '2026')
    reader.read_discovery_rows(ws)
    before = downloads(browser)
    if failed_write:
        native = GridPage.wait_for_function
        def failed_save(page, script, **kwargs):
            if 'docs-save-indicator-badge' in script:
                raise TimeoutError('synthetic save uncertain')
            return native(page, script, **kwargs)
        monkeypatch.setattr(GridPage, 'wait_for_function', failed_save)
    request = service.update(spreadsheetId='test', range="'2026'!F2", valueInputOption='RAW',
                             body={'values': [['NEW-BRAND']]})
    if failed_write:
        from src.sheets.quotation_input import QuotationInputUnavailable
        with pytest.raises(QuotationInputUnavailable, match='SETTLEMENT_UNCONFIRMED'):
            request.execute()
        assert downloads(browser) - before == 1  # Prewrite only, no fictitious readback.
        assert not service._snapshots
    else:
        assert request.execute() == {'updatedCells': 1}
        assert downloads(browser) - before == 2  # Mandatory prewrite+postwrite.
        assert not service._snapshots
        assert reader.read_discovery_rows(ws)[1].cells['F'] == 'NEW-BRAND'
        assert downloads(browser) - before == 3  # New ordinary acquisition.


@pytest.mark.parametrize('column,value', [('E', 'CHANGED-MPN'), ('F', 'CHANGED-BRAND'), ('A', '成交'), ('G', '999')])
def test_purchase_fresh_gate_rejects_inside_ttl_changes(cached, column, value):
    from src.sheets.brand_write import SheetRecordConflict
    from src.sheets.pending import query_pending_records
    from src.sheets.purchase_status import current_purchase_status
    service, browser, rows, _clock = cached
    ws = WorksheetIdentity('test', '2026')
    reader = GoogleSheetsRowReader(service)
    rows['2026'][1][0] = '未发'
    record, = query_pending_records(reader, ws, discovery=True)
    rows['2026'][1][ord(column)-65] = value
    assert reader.read_discovery_rows(ws)[1].cells[column] != value
    with pytest.raises(SheetRecordConflict):
        current_purchase_status(reader, record.record_identity)
    assert downloads(browser) == 2  # Ordinary discovery + mandatory fresh check.
    assert not browser.contexts[0].pages[-1].typed


@pytest.mark.parametrize('change', ['brief_tp', 'mpn', 'qty', 'brand', 'row', 'status'])
def test_tp_cached_discovery_but_target_and_source_recheck_live(cached, tmp_path, change):
    service, browser, rows, _clock = cached
    rows['RFQ_BRIEF'].append(list(brief(row='2', mpn='000123', qty='1200', brand='OLD').values))
    cycle, _, _, transport, _ = build(tmp_path)
    cycle.brief, cycle.reader = BriefReader(service), GoogleSheetsRowReader(service)
    # First discovery shared across cycles; no native download per TP order.
    assert len(cycle.read_orders('test')) == 1
    assert len(cycle.read_orders('test')) == 1 and downloads(browser) == 2
    def mutate():
        if change == 'brief_tp':
            rows['RFQ_BRIEF'][1][BRIEF_HEADERS.index('target_price')] = '9 USD'
        elif change == 'row':
            rows['2026'].insert(1, ['未发', '', 'B', '', 'OTHER', 'OLD', '1200'])
        else:
            index = {'mpn': 4, 'qty': 6, 'brand': 5, 'status': 0}[change]
            rows['2026'][1][index] = {'mpn': 'OTHER', 'qty': '99', 'brand': 'OTHER', 'status': '成交'}[change]
    cycle.research.hook = mutate
    if change == 'status':
        # The reviewed E continuation verifies the full original source snapshot;
        # do not invent a new status restriction for the old synchronous TP path.
        order, = cycle.read_orders('test')
        expected = cycle.continuation_source(order)
        key = cycle.store.register(order, NOW)
        command = cycle.store.claim(key, order, NOW)
        result = cycle.research.execute_tp(key, order, now=NOW)
        with pytest.raises(ValueError, match='TP_SOURCE_CHANGED'):
            cycle.complete_order(order, key, command, result, now=NOW, expected_source=expected)
    else:
        cycle.run('test', now=NOW)
        assert cycle.store.rows()[0]['state'] == 'FAILED'
    assert not transport.calls
    assert all(not p.typed for p in browser.contexts[0].pages[1:])


def test_protected_quotation_input_not_cache_member(cached):
    service, browser, _rows, _clock = cached
    with pytest.raises(ValueError, match='GOOGLE_DISCOVERY_UNCONFIRMED'):
        service.get_discovery(spreadsheetId='test', range="'报价输入'!A1:N1").execute()
    assert downloads(browser) == 0


@pytest.mark.parametrize('column,value', [('E', 'OTHER'), ('F', 'OTHER'), ('A', '成交'), ('G', '999')])
def test_quotation_action_rechecks_source_inside_ttl(cached, column, value):
    from types import SimpleNamespace

    from src.sheets import IdentifyingSnapshot, SheetRecordIdentity
    from src.workflow.v13_quotation import (
        QuotationOutcome,
        V13QuotationResult,
        V13SourceRowError,
    )
    from src.workflow.v13_quote_update import WorkflowQuotationSource
    from tests.workflow.test_v13_quotation import Store
    service, browser, rows, _clock = cached
    reader = GoogleSheetsRowReader(service)
    ws = WorksheetIdentity('test', '2026')
    identity = SheetRecordIdentity(ws, 2, IdentifyingSnapshot('发给采购', 'B', '000123', 'OLD', 1200))
    item = SimpleNamespace(inquiry_id='synthetic', record_identity=identity,
                           resolved_brand=None, brand_update_status=None)
    result = V13QuotationResult('synthetic', identity, '000123', QuotationOutcome.QUOTE_FOUND, None)
    gate = WorkflowQuotationSource(reader=reader, store=Store([item]))
    reader.read_discovery_rows(ws)
    rows['2026'][1][ord(column)-65] = value
    with pytest.raises(V13SourceRowError, match='SOURCE_CHANGED'):
        gate.read_state(result)
    assert downloads(browser) == 2
    assert all(not p.typed for p in browser.contexts[0].pages[1:])


def test_actual_busy_fresh_failure_cannot_be_hidden_by_warm_snapshot(cached, monkeypatch):
    from src.launcher.google_quote_update import GoogleQuotationUpdateActions
    from src.sheets.quotation_input import QuotationInputBusy
    service, browser, _rows, _clock = cached
    succeeded = []
    service._on_read_success = lambda: succeeded.append(True)
    reader = GoogleSheetsRowReader(service, retry_wait=lambda _: True)
    ws = WorksheetIdentity('test', '2026')
    reader.read_discovery_rows(ws)
    def busy(*args, **kwargs):
        raise QuotationInputBusy('GOOGLE_QUOTATION_INPUT_BUSY')
    monkeypatch.setattr(GoogleQuotationUpdateActions, 'open_sheet', busy)
    with pytest.raises(GoogleSheetsReadError):
        reader.read_rows(ws)  # Mandatory live gate sees protection despite TTL.
    with pytest.raises(GoogleSheetsReadError):
        reader.read_discovery_rows(ws)  # Evicted; no cached success fallback.
    assert not service._snapshots and downloads(browser) == 1
    assert succeeded == [True]


def test_stop_after_acquisition_does_not_publish_snapshot(cached, monkeypatch):
    service, browser, _rows, _clock = cached
    stopped = []
    native = service._download
    def stop_after(*args):
        result = native(*args)
        stopped.append(True)
        return result
    monkeypatch.setattr(service, '_download', stop_after)
    service._stop_requested = lambda: bool(stopped)
    with pytest.raises(V13Stopped):
        service.get_discovery(spreadsheetId='test', range="'2026'!A1:G").execute()
    assert downloads(browser) == 1 and not service._snapshots
    assert service.live_read_revision == 0



def test_manual_tp_discovery_is_live_even_inside_ttl(cached, tmp_path):
    from decimal import Decimal

    service, browser, rows, _clock = cached
    rows['RFQ_BRIEF'].append(list(brief(row='2', mpn='000123', qty='1200', brand='OLD').values))
    cycle, _, _, _, _ = build(tmp_path)
    cycle.brief, cycle.reader = BriefReader(service), GoogleSheetsRowReader(service)
    order, = cycle.read_orders('test')
    key = cycle.store.register(order, NOW)
    rows['RFQ_BRIEF'][1][BRIEF_HEADERS.index('target_price')] = '9 USD'
    cycle.store.finish(key, 'FAILED', NOW, 'SYNTHETIC_PRIOR_FAILURE')
    manual, = cycle.read_orders('test', manual_key=key)
    assert manual.target_price == Decimal(9) and downloads(browser) == 4



def test_discovery_cannot_widen_verified_column_contract(cached):
    service, browser, _rows, _clock = cached
    with pytest.raises(ValueError, match='GOOGLE_DISCOVERY_UNCONFIRMED'):
        service.get_discovery(spreadsheetId='test', range="'2026'!H1:H2").execute()
    assert not service._snapshots and downloads(browser) == 0



@pytest.mark.parametrize('corruption', ['header', 'wide'])
def test_brief_schema_failure_evicts_verified_snapshot(cached, corruption):
    service, browser, rows, clock = cached
    reader = BriefReader(service)
    assert reader.read_discovery('test') == ()
    clock.now = 60
    if corruption == 'header':
        rows['RFQ_BRIEF'][0][0] = 'WRONG'
    else:
        rows['RFQ_BRIEF'].append(['x'] * 18)
    with pytest.raises(ValueError, match='TP_BRIEF_SCHEMA_UNAVAILABLE'):
        reader.read_discovery('test')
    assert not service._snapshots and downloads(browser) == 2
