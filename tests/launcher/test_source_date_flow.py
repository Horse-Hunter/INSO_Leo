"""Actual native download -> reader -> original coordinator -> fake writer."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.sheets import WorksheetIdentity
from src.sheets.google_reader import GoogleSheetsReadError, GoogleSheetsRowReader
from src.workflow.v12_contracts import BusinessState, PurchaseOutcome
from src.workflow.v12_flow import ResearchBusinessFacts, V12WorkflowCoordinator
from tests.launcher.test_google_web import web as web  # noqa: PLC0414
from tests.workflow.test_v12_flow import _make_flow

NOW=datetime(2026,11,4,12,tzinfo=timezone.utc)
WS=WorksheetIdentity('synthetic-sheet','2026')


def dated_source(web,day='2026-11-04'):
    service,_browser,rows,_human=web
    rows['2026'][0]+=['']*16
    rows['2026'][0][22]='quote_date'
    rows['2026'][1]=['未发','','C','SYNTHETIC','Mpn-1','Brand-X',7]+['']*15+[day]
    return service,GoogleSheetsRowReader(service,retry_wait=lambda _:False)


def original_flow(tmp_path,reader):
    flow,*rest=_make_flow(tmp_path,facts=ResearchBusinessFacts('货足',Decimal(60001),Decimal('2.00')))
    flow._record_admitted=V12WorkflowCoordinator._record_admitted.__get__(flow)
    flow._brief_snapshot=lambda _:()
    flow._clock=lambda:NOW
    return flow,rest


def test_new_dated_source_researches_and_prepares_original_draft_once_and_persists_date(web,tmp_path):
    service,reader=dated_source(web)
    flow,rest=original_flow(tmp_path,reader)
    queue,_ledger,research,_checker,_provider,writer,_worker=rest
    with service.poll_scope():
        results=flow.poll_and_process(reader,WS,now=NOW)
    assert len(results)==1 and len(research.inputs)==1 and len(writer.commands)==1
    assert results[0].business_state is BusinessState.PURCHASE_DRAFTING
    assert results[0].purchase_outcome is PurchaseOutcome.AI_RECOGNIZED
    item=queue.all_items()[0]
    assert item.source_order_date=='2026-11-04' and item.created_at==NOW
    with service.poll_scope():
        flow.poll_and_process(reader,WS,now=NOW)
    assert len(writer.commands)==1
    assert not web[3].closed and web[1].connected


@pytest.mark.parametrize('day',['2026-10-01','2026-11-05','bad-date',''])
def test_native_old_future_bad_undated_rows_never_create_queue_or_external_calls(web,tmp_path,day):
    service,reader=dated_source(web,day)
    flow,rest=original_flow(tmp_path,reader)
    queue,_ledger,research,checker,_provider,writer,_worker=rest
    with service.poll_scope():
        assert flow.poll_and_process(reader,WS,now=NOW)==()
    assert not queue.all_items() and not research.inputs and not checker.calls and not writer.commands


def test_discovery_cache_retains_bound_date_and_caller_mutation_cannot_change_it(web):
    service,reader=dated_source(web)
    with service.poll_scope():
        first=service.get_discovery(spreadsheetId=WS.spreadsheet,range="'2026'!A1:G").execute()
        first['source_order_dates']['rows'][0][4]='2030-01-01'
        observed=reader.read_discovery_rows(WS)
    assert observed[1].source_order_date=='2026-11-04'


@pytest.mark.parametrize('problem',['wrong-row','model','brand','quantity','header','duplicate'])
def test_reader_rejects_date_proof_with_wrong_identity_or_header(problem):
    from types import SimpleNamespace
    base=['未发','','C','SYNTHETIC','Mpn-1','Brand-X',7]
    proof=[2,'Mpn-1','Brand-X',7,'2026-11-04']
    evidence={'column':'W','header':'quote_date','rows':[proof]}
    if problem=='wrong-row':proof[0]=2;base[4]='Other-Mpn'
    elif problem=='model':proof[1]='Other-Mpn'
    elif problem=='brand':proof[2]='Other-Brand'
    elif problem=='quantity':proof[3]=70
    elif problem=='header':evidence['header']='other_date'
    else:evidence['rows']+=[list(proof)]
    response={'values':[['STATUS','','CLASS','WHO','MPN','MFR','Qty'],base],'source_order_dates':evidence}
    request=SimpleNamespace(execute=lambda:response)
    service=SimpleNamespace(spreadsheets=lambda:SimpleNamespace(values=lambda:SimpleNamespace(get=lambda **_:request)))
    with pytest.raises(GoogleSheetsReadError):GoogleSheetsRowReader(service).read_rows(WS)


def test_source_date_changes_before_submit_prevent_external_write(web,tmp_path):
    service,reader=dated_source(web)
    flow,rest=original_flow(tmp_path,reader)
    _queue,_ledger,research,_checker,_provider,writer,_worker=rest
    original=research.execute
    def changed(item):
        value=original(item)
        web[2]['2026'][1][22]='2026-08-01'
        return value
    research.execute=changed
    with service.poll_scope():flow.poll_and_process(reader,WS,now=NOW)
    assert research.inputs and not writer.commands
