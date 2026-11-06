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
    "GOOGLE_TAB_IDENTITY_UNCONFIRMED","GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED","WORKFLOW_LEDGER_UNAVAILABLE"])
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
