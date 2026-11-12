"""Original Backend/Combined paths: optional metrics cannot veto valid orders."""
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from src.sheets import WorksheetIdentity, WorksheetRow
from src.sheets.google_reader import GoogleSheetsReadUnavailable
from src.workflow.v13_integration import CombinedCycle
from tests.launcher.test_google_web import web as web  # noqa: PLC0414
from tests.launcher.test_v16_backend import prepared

SHEETS=tuple(WorksheetIdentity("synthetic",title) for title in ("2026","SHAHAB"))


@pytest.mark.parametrize("failed",["counts","2026","SHAHAB"])
def test_actual_backend_keeps_healthy_sheet_processing_when_optional_or_one_sheet_read_fails(tmp_path,monkeypatch,failed):
    backend,runtime,_=prepared(tmp_path,monkeypatch)
    processed=[]
    class Reader:
        discovery_scope=staticmethod(nullcontext)
        def read_rows(self,worksheet):
            if worksheet.worksheet==failed:
                raise GoogleSheetsReadUnavailable("synthetic source read unavailable")
            return (WorksheetRow(2,{"A":"未发","C":"C","E":"SYNTH-NEW","F":"SYNTH","G":1}),)
        def read_discovery_rows(self,worksheet):
            if failed=="counts":raise GoogleSheetsReadUnavailable("synthetic optional count read unavailable")
            return self.read_rows(worksheet)
    reader=Reader()
    def process(reader,worksheet,**kwargs):
        reader.read_rows(worksheet);processed.append(worksheet.worksheet)
    flow=SimpleNamespace(begin_poll_cycle=lambda:None,poll_and_process=process)
    backend._combined=CombinedCycle(flow,lambda _:None,on_pause=lambda _:None)
    backend._tp=SimpleNamespace(run=lambda *a,**k:None,issues={})
    backend._purchase_completion=SimpleNamespace(retry_saved_statuses=lambda **k:None)
    for name in ("_check_site_recovery","_idle_login_tick"):
        monkeypatch.setattr(backend,name,lambda *a,**k:None)
    monkeypatch.setattr(backend,"_wait_between_polls",lambda _:backend._stop.set() or True)
    try:
        backend._run_independent_poll(runtime,{"spreadsheet_id":"synthetic"},None,
            SimpleNamespace(poll_scope=nullcontext),reader,SHEETS,None)
        assert processed==[s.worksheet for s in SHEETS if s.worksheet!=failed]
        assert backend._combined.v12_paused is False
        if failed=="counts":assert backend._dashboard_counts is None
    finally:backend.shutdown()


@pytest.mark.parametrize("reason",["GOOGLE_AUTHENTICATION_REQUIRED","SHEETS_SCHEMA_UNAVAILABLE",
    "GOOGLE_SPREADSHEET_UNAVAILABLE", "GOOGLE_TAB_IDENTITY_UNCONFIRMED","GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED","WORKFLOW_LEDGER_UNAVAILABLE"])
def test_shared_safety_cause_never_becomes_an_isolated_sheet_failure(reason):
    from src.workflow.v12_faults import FaultScope, V12Fault
    from src.workflow.v13_integration import is_isolated_source_read_error
    error=GoogleSheetsReadUnavailable("synthetic wrapper")
    error.__cause__=V12Fault(FaultScope.GLOBAL_STOP,reason)
    assert not is_isolated_source_read_error(error)


def test_unclassified_or_security_read_failure_does_not_get_silently_skipped():
    import sqlite3

    from src.sheets.google_reader import GoogleSheetsReadError
    from src.workflow.v13_integration import is_isolated_source_read_error
    for cause in (sqlite3.DatabaseError("synthetic"),ValueError("synthetic malformed response")):
        error=GoogleSheetsReadUnavailable("synthetic wrapper");error.__cause__=cause
        assert not is_isolated_source_read_error(error)
    assert not is_isolated_source_read_error(GoogleSheetsReadError("unverified"))


@pytest.mark.parametrize("failed",[None,"2026","SHAHAB"])
def test_both_real_native_readers_reach_original_queue_and_fake_purchase_independently(web,tmp_path,monkeypatch,failed):
    from decimal import Decimal

    from playwright.sync_api import TimeoutError as PageTimeout

    from src.sheets.google_reader import GoogleSheetsRowReader
    from src.workflow.v12_flow import ResearchBusinessFacts, V12WorkflowCoordinator
    from tests.launcher.test_source_date_flow import NOW
    from tests.workflow.test_v12_flow import _make_flow
    monkeypatch.setattr("src.launcher.backend.utc_now",lambda:NOW)
    service,browser,rows,human=web
    rows["2026"][0]+=[""]*16;rows["2026"][0][22]="quote_date"
    rows["2026"][1]=["未发","","C","SYNTH","SYNTH-2026","Brand-X",7]+[""]*15+[NOW.date().isoformat()]
    rows["SHAHAB"]=[rows["SHAHAB"][0],rows["SHAHAB"][1],
        [NOW.date().isoformat(),"未发",1,"SYNTH-SHAHAB","Brand-X",7,"PCS"]]
    native_select=service._select
    def select(page,actions,title):
        if title==failed:raise PageTimeout("synthetic native sheet read timeout")
        return native_select(page,actions,title)
    monkeypatch.setattr(service,"_select",select)
    flow,queue,ledger,_research,_checker,_facts,writer,_worker=_make_flow(tmp_path,
        facts=ResearchBusinessFacts("货足",Decimal(2),Decimal(2)))
    from src.workflow.v12_contracts import DuplicateCheckResult, DuplicateOutcome
    _checker.check=lambda iid,mpn,quantity,at:DuplicateCheckResult(iid,DuplicateOutcome.CONFIRMED,str(mpn),at,repeated=False)
    flow._record_admitted=V12WorkflowCoordinator._record_admitted.__get__(flow)
    flow._brief_snapshot=lambda _:();flow._clock=lambda:NOW
    backend,runtime,_=prepared(tmp_path,monkeypatch)
    backend._store=queue;backend._v12_store=ledger
    backend._combined=CombinedCycle(flow,lambda _:None,on_pause=lambda _:None)
    backend._tp=SimpleNamespace(run=lambda *a,**k:None,issues={})
    backend._purchase_completion=SimpleNamespace(retry_saved_statuses=lambda **k:None)
    for name in ("_check_site_recovery","_idle_login_tick"):
        monkeypatch.setattr(backend,name,lambda *a,**k:None)
    monkeypatch.setattr(backend,"_wait_between_polls",lambda _:backend._stop.set() or True)
    sheets=tuple(WorksheetIdentity("synthetic-sheet",name) for name in ("2026","SHAHAB"))
    reader=GoogleSheetsRowReader(service,retry_wait=lambda _:False)
    try:
        backend._run_independent_poll(runtime,{"spreadsheet_id":"synthetic-sheet"},None,
            service,reader,sheets,None)
        assert {x.record_identity.worksheet.worksheet for x in queue.all_items()}=={x.worksheet for x in sheets if x.worksheet!=failed}
        assert len(writer.commands)==(2 if failed is None else 1), [(x.record_identity.worksheet.worksheet,x.status.value,x.last_error,ledger.business_state(x.inquiry_id).value,flow.admission_skips.get(x.inquiry_id)) for x in queue.all_items()]
        assert not human.closed and browser.connected
        assert backend._combined.v12_paused is False
    finally:backend.shutdown()


@pytest.mark.parametrize("url",["https://yingsuo.alperp.cn/","https://docs.google.com/spreadsheets/d/other/edit#gid=0"])
def test_google_read_does_not_probe_unrelated_manual_page_ownership(web,monkeypatch,url):
    from src.sheets.google_reader import GoogleSheetsRowReader
    service,browser,_rows,human=web
    human.url=url
    def forbidden(*args,**kwargs):raise AssertionError("Unrelated manual page must not be evaluated")
    monkeypatch.setattr(human,"evaluate",forbidden)
    with service.poll_scope():assert GoogleSheetsRowReader(service).read_rows(WorksheetIdentity("test","2026"))
    assert not human.closed and browser.connected


@pytest.mark.parametrize("title",["2026","SHAHAB"])
def test_plain_native_read_does_not_require_quotation_script_menu(web,title):
    from src.sheets.google_reader import GoogleSheetsRowReader
    service,browser,_,human=web
    create=browser.contexts[0].new_page
    def new_page():
        page=create();page.menu_failure=True;return page
    browser.contexts[0].new_page=new_page
    with service.poll_scope():
        assert GoogleSheetsRowReader(service,retry_wait=lambda _:False).read_rows(WorksheetIdentity("test",title))
    assert not human.closed


@pytest.mark.parametrize("quotation_wrapper",[False,True])
def test_wrapped_safe_navigation_read_keeps_polling_after_three_hours(tmp_path,monkeypatch,quotation_wrapper):
    from src.workflow.v12_faults import FaultScope, V12Fault
    backend,runtime,_clock=prepared(tmp_path,monkeypatch)
    error=GoogleSheetsReadUnavailable("synthetic read")
    error.__cause__=TimeoutError("synthetic verified temporary read")
    if quotation_wrapper:
        outer=V12Fault(FaultScope.GLOBAL_STOP,"SHEETS_READ_UNAVAILABLE");outer.__cause__=error;error=outer
    backend._module_execute=lambda _:(_ for _ in ()).throw(error)
    monkeypatch.setattr(backend,"_defer_website_poll",lambda *a,**k:True)
    backend._site_outages["Google Sheets"]=-20000
    try:
        assert runtime.claim_due_module()=="inquiry"
        backend._run_independent_job("inquiry")
        assert runtime.module_plans()["inquiry"][0]==900
        assert runtime.module_plans()["inquiry"][2] is False
        assert backend._module_failures["inquiry"][1] == "表格读取未完成，等待下一轮重试"
    finally:backend.shutdown()


@pytest.mark.parametrize("phase",["before","after"])
@pytest.mark.parametrize("persistent",[False,True])
def test_native_sheet_title_drift_rejects_wrong_export_and_retries_locally(web,monkeypatch,phase,persistent):
    from src.sheets.google_reader import (
        GoogleSheetsReadUnavailable,
        GoogleSheetsRowReader,
    )
    service,_browser,_,human=web
    calls=[]
    original=service._download
    def download(page,actions):
        drift=persistent or not calls;calls.append(True)
        if drift and phase=="before":page.title="2026"
        if drift and phase=="after":
            from tests.launcher.test_google_web import Download
            failure=Download.failure
            def altered(artifact):
                page.title="2026";return failure(artifact)
            monkeypatch.setattr(Download,"failure",altered)
        else:
            from tests.launcher.test_google_web import Download
            monkeypatch.setattr(Download,"failure",lambda _:None)
        return original(page,actions)
    monkeypatch.setattr(service,"_download",download)
    with service.poll_scope():
        reader=GoogleSheetsRowReader(service,retry_wait=lambda _:False)
        if persistent:
            with pytest.raises(GoogleSheetsReadUnavailable) as caught:
                reader.read_rows(WorksheetIdentity("test","SHAHAB"))
            from src.workflow.v13_integration import is_isolated_source_read_error
            assert is_isolated_source_read_error(caught.value)
            assert len(calls)==5
        else:
            assert reader.read_rows(WorksheetIdentity("test","SHAHAB")) and len(calls)==2
    assert not human.closed



def test_native_selection_does_not_bind_lagging_sdk_url_cache(web,monkeypatch):
    from src.sheets.google_reader import GoogleSheetsRowReader
    from tests.launcher.test_google_web import GridLocator, GridPage
    service,browser,_,human=web
    click=GridLocator.click;evaluate=GridPage.evaluate
    waits=[]
    def select(control,**kwargs):
        previous=control.page.url;result=click(control,**kwargs)
        if control.kind=="tab":
            control.page.live_url=control.page.url;control.page.url=previous
        return result
    def observe(page,script,arg=None):
        if 'docs-sheet-active-tab' in script:
            return {"title":page.title,"fragment":getattr(page,"live_url",page.url).split('#')[-1]}
        return evaluate(page,script,arg)
    def wait_url(page,predicate,**kwargs):
        assert kwargs['timeout']<=30000 and kwargs['wait_until']=='domcontentloaded' and predicate(page.live_url)
        waits.append(True);page.url=page.live_url
    original=service._download
    def download(page,actions):
        page.url=page.live_url  # The SDK cache catches up before the export.
        return original(page,actions)
    monkeypatch.setattr(GridLocator,"click",select)
    monkeypatch.setattr(GridPage,"evaluate",observe)
    monkeypatch.setattr(GridPage,"wait_for_url",wait_url,raising=False)
    monkeypatch.setattr(service,"_download",download)
    with service.poll_scope():
        assert GoogleSheetsRowReader(service,retry_wait=lambda _:False).read_rows(WorksheetIdentity("test","SHAHAB"))
    assert len(waits)==1 and len(browser.contexts[0].pages)==2
    assert not human.closed


def test_safe_quote_timeout_then_three_new_shahab_orders_enter_original_flow_once(web,tmp_path,monkeypatch):
    from decimal import Decimal

    from src.sheets.google_reader import GoogleSheetsRowReader
    from src.workflow.inso_query import run_inso_query
    from src.workflow.v12_contracts import DuplicateCheckResult, DuplicateOutcome
    from src.workflow.v12_flow import ResearchBusinessFacts, V12WorkflowCoordinator
    from tests.launcher.test_source_date_flow import NOW
    from tests.workflow.test_v12_flow import _make_flow
    service,browser,rows,human=web
    flow,queue,ledger,_research,checker,_facts,writer,_worker=_make_flow(tmp_path,facts=ResearchBusinessFacts('货足',Decimal(2),Decimal(2)))
    checker.check=lambda iid,mpn,quantity,at:DuplicateCheckResult(iid,DuplicateOutcome.CONFIRMED,str(mpn),at,repeated=False)
    flow._record_admitted=V12WorkflowCoordinator._record_admitted.__get__(flow)
    flow._brief_snapshot=lambda _:();flow._clock=lambda:NOW
    backend,runtime,clock=prepared(tmp_path,monkeypatch)
    service._timer=lambda:clock.tick
    monkeypatch.setattr('src.launcher.backend.utc_now',lambda:NOW)
    backend._store=queue;backend._v12_store=ledger
    quote_calls=[];resets=[];retry_waits=[];tp_calls=[]
    def quote(_):
        quote_calls.append(clock.tick)
        if len(quote_calls)==1:
            def wait(seconds):retry_waits.append(seconds);clock.tick+=seconds;return False
            run_inso_query(lambda:False,succeeded=bool,reset=lambda:resets.append(True),wait=wait)
    backend._combined=CombinedCycle(flow,quote,on_pause=lambda _:None)
    backend._tp=SimpleNamespace(run=lambda *a,**kw:tp_calls.append(clock.tick),issues={})
    backend._purchase_completion=SimpleNamespace(retry_saved_statuses=lambda **kw:None)
    for name in ('_check_site_recovery','_idle_login_tick'):
        monkeypatch.setattr(backend,name,lambda *a,**kw:None)
    injected=[False]
    def next_poll(seconds):
        if clock.tick>=1800:backend._stop.set();return True
        clock.tick+=seconds
        if not injected[0]:
            rows['SHAHAB'].extend([[NOW.date().isoformat(),'未发',n,'SYNTH-NEW-'+str(n),'Brand-X',7,'PCS'] for n in range(1,4)])
            injected[0]=True
        return False
    monkeypatch.setattr(backend,'_wait_between_polls',next_poll)
    sheets=tuple(WorksheetIdentity('synthetic-sheet',name) for name in ('2026','SHAHAB'))
    reader=GoogleSheetsRowReader(service,retry_wait=lambda _:False)
    try:
        backend._run_independent_poll(runtime,{'spreadsheet_id':'synthetic-sheet'},None,service,reader,sheets,None)
        items=queue.all_items()
        assert len(items)==len(writer.commands)==3
        assert {str(i.mpn) for i in items}=={'SYNTH-NEW-1','SYNTH-NEW-2','SYNTH-NEW-3'}
        assert all(i.record_identity.worksheet.worksheet=='SHAHAB' and i.source_order_date==NOW.date().isoformat() for i in items)
        assert all(i.created_at==NOW for i in items)
        assert len(resets)==4 and retry_waits==[120]*3 and tp_calls
        assert len(quote_calls)>=2 and clock.tick>=1800
        assert not human.closed and browser.connected
    finally:backend.shutdown()


def test_wrapped_google_identity_fault_is_not_reported_as_website_outage():
    from src.launcher.backend import _website_failure
    from src.sheets.google_reader import GoogleSheetsReadError
    from src.workflow.v12_faults import FaultScope, V12Fault

    error = GoogleSheetsReadError("synthetic read")
    error.__cause__ = V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED")
    assert _website_failure(error) is None


@pytest.mark.parametrize("code,isolated", [("ERR_CONNECTION_RESET", True), ("ERR_CERT_AUTHORITY_INVALID", False)])
def test_native_navigation_cause_chain_preserves_safe_retry_and_certificate_stop(web, monkeypatch, code, isolated):
    from playwright.sync_api import Error as PageError

    from src.sheets.google_reader import GoogleSheetsReadError, GoogleSheetsRowReader
    from src.workflow.v13_integration import is_isolated_source_read_error
    from tests.launcher.test_google_web import GridPage

    service, browser, _, human = web
    def goto(page, url, **kwargs):
        page.url = "chrome-error://chromewebdata/"
        raise PageError("net::"+code+" synthetic failure")
    monkeypatch.setattr(GridPage, "goto", goto)
    with service.poll_scope(), pytest.raises(GoogleSheetsReadError) as caught:
        GoogleSheetsRowReader(service, retry_wait=lambda _: False).read_rows(WorksheetIdentity("test", "2026"))
    assert is_isolated_source_read_error(caught.value) is isolated
    from src.launcher.backend import _website_failure
    assert _website_failure(caught.value) == ("Google Sheets" if isolated else None)
    assert not human.closed and browser.is_connected()


@pytest.mark.parametrize("cancel_fails", [False, True])
def test_native_async_download_timeout_requires_successful_cancel_and_cleanup(web, monkeypatch, cancel_fails):
    import asyncio

    import src.launcher.google_web as google
    from src.sheets.google_reader import (
        GoogleDownloadReadTimeout,
        GoogleSheetsReadError,
        GoogleSheetsRowReader,
    )
    from src.workflow.v13_integration import is_isolated_source_read_error

    service, _, _, human = web
    original = google._download_call
    operations = []
    def call(download, operation, *, timeout):
        operations.append(operation)
        if operation == "failure":
            async def expire():
                await asyncio.wait_for(asyncio.sleep(1), timeout=0.001)
            try:
                asyncio.run(expire())
            except TimeoutError:
                raise GoogleDownloadReadTimeout("GOOGLE_WEB_READ_DOWNLOAD_TIMEOUT") from None
        if operation == "cancel":
            if cancel_fails:
                raise RuntimeError("synthetic cancellation failure")
            return None
        return original(download, operation, timeout=timeout)
    monkeypatch.setattr(google, "_download_call", call)
    with service.poll_scope(), pytest.raises(GoogleSheetsReadError) as caught:
        GoogleSheetsRowReader(service, retry_wait=lambda _: False).read_rows(WorksheetIdentity("test", "2026"))
    assert is_isolated_source_read_error(caught.value)
    assert "cancel" in operations and "delete" in operations
    assert not human.closed


def test_unrelated_async_cancellation_is_not_a_safe_read_failure():
    from asyncio import CancelledError

    from src.workflow.v13_integration import is_isolated_source_read_error
    error = GoogleSheetsReadUnavailable("synthetic")
    error.__cause__ = CancelledError()
    assert not is_isolated_source_read_error(error)


def test_artifact_loss_message_alone_does_not_authorize_retry():
    from src.workflow.v13_integration import is_isolated_source_read_error

    error = GoogleSheetsReadUnavailable("synthetic")
    timeout = TimeoutError("GOOGLE_WEB_READ_ARTIFACT_LOST")
    timeout.__cause__ = FileNotFoundError("unverified file")
    error.__cause__ = timeout
    assert not is_isolated_source_read_error(error)


@pytest.mark.parametrize("failure", [ConnectionError, RuntimeError])
def test_failed_owned_download_cleanup_preserves_successful_read(web, monkeypatch, failure):
    import src.launcher.google_web as google
    from src.sheets.google_reader import GoogleSheetsRowReader

    service, _, _, human = web
    original = google._download_call
    operations = []
    def call(download, operation, *, timeout):
        operations.append(operation)
        if operation == "delete":
            raise failure("synthetic cleanup failure")
        return original(download, operation, timeout=timeout)
    monkeypatch.setattr(google, "_download_call", call)
    with service.poll_scope():
        rows = GoogleSheetsRowReader(service, retry_wait=lambda _: False).read_rows(WorksheetIdentity("test", "2026"))
    assert rows and "delete" in operations and not human.closed


def test_cleanup_failure_does_not_mask_download_timeout(web, monkeypatch):
    import src.launcher.google_web as google
    from src.sheets.google_reader import GoogleDownloadReadTimeout

    service, _, _, human = web
    original = google._download_call
    def call(download, operation, *, timeout):
        if operation == "failure":
            raise GoogleDownloadReadTimeout("GOOGLE_WEB_READ_DOWNLOAD_TIMEOUT")
        if operation == "delete":
            raise RuntimeError("synthetic cleanup failure")
        if operation == "cancel":
            return None
        return original(download, operation, timeout=timeout)
    monkeypatch.setattr(google, "_download_call", call)
    with service.poll_scope(), pytest.raises(TimeoutError):
        service.get(spreadsheetId="test", range="'2026'!A1:G").execute()
    assert not human.closed


def test_certificate_failure_inside_generic_google_fault_never_becomes_outage():
    from playwright.sync_api import Error as PageError

    from src.launcher.backend import _website_failure
    from src.sheets.google_reader import GoogleSheetsReadError
    from src.workflow.v12_faults import FaultScope, V12Fault

    error = GoogleSheetsReadError("synthetic read")
    fault = V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SPREADSHEET_UNAVAILABLE")
    fault.__cause__ = PageError("net::ERR_CERT_AUTHORITY_INVALID synthetic")
    error.__cause__ = fault
    assert _website_failure(error) is None


@pytest.mark.parametrize("failure,isolated", [
    ("net::ERR_CONNECTION_RESET", True),
    ("net::ERR_CERT_AUTHORITY_INVALID", False),
    ("unrecognized private failure", False),
    ("net::ERR_CONNECTION_RESET plus unknown", False),
])
def test_native_download_failure_requires_explicit_transient_code(web, monkeypatch, failure, isolated):
    from src.launcher.backend import _website_failure
    from src.sheets.google_reader import GoogleSheetsReadError, GoogleSheetsRowReader
    from src.workflow.v13_integration import is_isolated_source_read_error
    from tests.launcher.test_google_web import Download

    service, _, _, human = web
    deletes = []
    original_delete = Download.delete
    monkeypatch.setattr(Download, "failure", lambda _: failure)
    def delete(download):
        deletes.append(True)
        return original_delete(download)
    monkeypatch.setattr(Download, "delete", delete)
    with service.poll_scope(), pytest.raises(GoogleSheetsReadError) as caught:
        GoogleSheetsRowReader(service, retry_wait=lambda _: False).read_rows(WorksheetIdentity("test", "2026"))
    assert is_isolated_source_read_error(caught.value) is isolated
    assert _website_failure(caught.value) == ("Google Sheets" if isolated else None)
    assert len(deletes) == (5 if isolated else 1)
    assert not human.closed


def test_nested_tls_failure_has_priority_over_generic_google_fault():
    from ssl import SSLError

    from src.launcher.backend import _website_failure
    from src.sheets.google_reader import GoogleSheetsReadError
    from src.workflow.v12_faults import FaultScope, V12Fault

    error = GoogleSheetsReadError("synthetic")
    fault = V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SPREADSHEET_UNAVAILABLE")
    fault.__cause__ = SSLError("synthetic")
    error.__cause__ = fault
    assert _website_failure(error) is None
