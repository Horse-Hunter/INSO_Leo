"""Actual Backend/completion/original outbox + fake SMTP; no real endpoints."""
from types import SimpleNamespace

import pytest

from src.launcher.backend import ProductionBackend
from src.launcher.purchase_completion import PurchaseCompletionActions
from src.research import ResearchReasonCode, ResearchResult, ResearchStatus
from src.workflow.v12_notifications import V12NotificationWorker
from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
from tests.workflow.test_v12_flow import NOW, SHEET, FakeSheetsReader, _make_flow
from tests.workflow.test_v12_smtp_transport import FakeCredentials, ScriptedSMTP, login


@pytest.fixture
def scene(tmp_path,request):
    flow,queue,ledger,research,*_=_make_flow(tmp_path)
    reader=FakeSheetsReader(tier=getattr(request,"param","C"))
    research.execute=lambda item:ResearchResult(item.inquiry_id,ResearchStatus.EXCEPTION,reason_code=ResearchReasonCode.NO_MATCHING_PRODUCT)
    result,=flow.poll_and_process(reader,SHEET,now=NOW)
    backend=ProductionBackend(root=tmp_path)
    backend._store,backend._v12_store=queue,ledger
    backend._mail_brief=SimpleNamespace(cached_lines=lambda _:())
    backend._source_projection.observe(SHEET,(reader.row,),queue.all_items(),at=NOW)
    actions=PurchaseCompletionActions(workflow_store=queue,v12_store=ledger,reader=reader,writer_factory=lambda:None,mail_evidence=backend._fault_evidence,automatic_admission=lambda iid,at:backend._current_mail_source(iid,at,module="inquiry") is not None)
    clients=[]
    def factory(*args,**kwargs):
        client=ScriptedSMTP();clients.append(client);return client
    transport=QQSMTPTransport(config=QQSMTPConfig(sender_address="sender@example.invalid"),credentials=FakeCredentials(login()),smtp_factory=factory,clock=lambda:NOW)
    worker=V12NotificationWorker(ledger,transport,review_current=backend._review_current_mail,prepare_content=backend._prepare_business_mail,scope="business")
    yield backend,actions,worker,clients,queue,ledger,reader,result
    backend.shutdown()


@pytest.mark.parametrize("scene",["A","B","C"],indirect=True)
def test_current_no_quote_sends_original_two_recipient_business_notice_once(scene):
    _backend,actions,worker,clients,_queue,_ledger,_reader,result=scene
    actions.process(result,at=NOW)
    assert worker.run_due(now=NOW)==2
    assert {str(c.message["To"]) for c in clients}=={"linan229@qq.com","shawn@inso-hk.com"}
    for c in clients:
        text=c.message.get_content()
        assert "未取得有效报价" in text and "未发采购" in text
        assert "型号有误" not in text and "Google" not in text
    actions.process(result,at=NOW);worker.run_due(now=NOW)
    assert sum(c.send_attempts for c in clients)==2


import sqlite3
from datetime import timedelta

from src.sheets import WorksheetRow
from src.workflow.v12_contracts import BusinessState, EventType, WorkflowEvent


def test_existing_completion_reconciliation_notifies_without_research_or_purchase_replay(scene):
    _backend,actions,worker,clients,queue,_ledger,_reader,result=scene
    before=queue.get_by_inquiry_id(result.inquiry_id)
    actions.retry_saved_statuses(at=NOW)
    assert worker.run_due(now=NOW)==2 and len(clients)==2
    assert queue.get_by_inquiry_id(result.inquiry_id)==before
    actions.retry_saved_statuses(at=NOW)
    assert worker.run_due(now=NOW)==0


@pytest.mark.parametrize("status",["发给采购","采购已报价","已报价给客户","作废"])
@pytest.mark.parametrize("after_enqueue",[False,True])
def test_closed_or_already_purchased_source_never_emits_no_quote_notice(scene,status,after_enqueue):
    backend,actions,worker,clients,queue,_ledger,reader,result=scene
    if after_enqueue:actions.process(result,at=NOW)
    reader.row=WorksheetRow(reader.row.row_position,{**reader.row.cells,"A":status})
    backend._source_projection.observe(SHEET,(reader.row,),queue.all_items(),at=NOW)
    if not after_enqueue:actions.process(result,at=NOW)
    assert worker.run_due(now=NOW)==0 and not clients


@pytest.mark.parametrize("field,value",[("E","SYNTH-OTHER"),("F","SYNTH-OTHER"),("G",70)])
def test_changed_order_identity_never_sends(scene,field,value):
    backend,actions,worker,clients,queue,_ledger,reader,result=scene
    actions.process(result,at=NOW)
    reader.row=WorksheetRow(reader.row.row_position,{**reader.row.cells,field:value})
    backend._source_projection.observe(SHEET,(reader.row,),queue.all_items(),at=NOW)
    assert worker.run_due(now=NOW)==0 and not clients


def test_transient_source_unavailable_defers_then_verified_source_allows_notice(scene):
    backend,actions,worker,clients,queue,_ledger,reader,result=scene
    actions.process(result,at=NOW)
    backend._source_projection.rows.clear()
    assert worker.run_due(now=NOW)==0 and not clients
    backend._source_projection.observe(SHEET,(reader.row,),queue.all_items(),at=NOW+timedelta(minutes=1))
    worker._transport._clock=lambda:NOW+timedelta(minutes=1)
    assert worker.run_due(now=NOW+timedelta(minutes=1))==2
    assert sum(c.send_attempts for c in clients)==2


@pytest.mark.parametrize("after_enqueue",[False,True])
def test_expired_order_has_zero_smtp_even_if_previously_enqueued(scene,after_enqueue):
    _backend,actions,worker,clients,_queue,_ledger,_reader,result=scene
    if after_enqueue:actions.process(result,at=NOW)
    later=NOW+timedelta(days=9)
    if not after_enqueue:actions.process(result,at=later)
    assert worker.run_due(now=later)==0 and not clients


@pytest.mark.parametrize("change",["success","technical","missing_event","old_event"])
def test_unproven_or_recovered_research_is_not_a_no_quote_business_fact(scene,change,monkeypatch):
    _backend,actions,worker,clients,queue,ledger,_reader,result=scene
    actions.process(result,at=NOW)
    if change=="success":
        ledger.set_business_state(result.inquiry_id,BusinessState.HUMAN_COMPLETED,WorkflowEvent("synthetic-recovered",result.inquiry_id,EventType.HUMAN_RESOLUTION_RECORDED,NOW,"workflow"))
    with sqlite3.connect(queue.database_path) as db:
        if change=="technical":db.execute("UPDATE workflow_items SET research_status='RETRYABLE_FAILURE',last_error='SOURCE_UNAVAILABLE'")
    # Simulate a missing/stale read through the accessor; never mutate append-only events.
    original=ledger.event_history
    if change=="missing_event":monkeypatch.setattr(ledger,"event_history",lambda iid:tuple(e for e in original(iid) if e.event_type is not EventType.RESEARCH_FAILED))
    if change=="old_event":
        from dataclasses import replace
        monkeypatch.setattr(ledger,"event_history",lambda iid:tuple(replace(e,occurred_at=NOW-timedelta(days=20)) if e.event_type is EventType.RESEARCH_FAILED else e for e in original(iid)))
    assert worker.run_due(now=NOW)==0 and not clients


@pytest.mark.parametrize("unknown",[False,True])
def test_smtp_sent_unknown_remains_terminal_across_worker_restart(scene,monkeypatch,unknown):
    backend,actions,worker,clients,_queue,ledger,_reader,result=scene
    if unknown:
        def uncertain(self,message):
            self.send_attempts+=1;self.message=message;raise TimeoutError()
        monkeypatch.setattr(ScriptedSMTP,"send_message",uncertain)
    actions.process(result,at=NOW)
    assert worker.run_due(now=NOW)==2 and len(clients)==2
    ledger.recover_abandoned_notification_attempts(at=NOW+timedelta(minutes=1))
    from src.workflow.v12_store import V12Store
    restarted=V12NotificationWorker(V12Store(ledger.database_path),worker._transport,review_current=backend._review_current_mail,prepare_content=backend._prepare_business_mail,scope="business")
    actions.retry_saved_statuses(at=NOW+timedelta(minutes=1))
    assert restarted.run_due(now=NOW+timedelta(minutes=1))==0 and len(clients)==2


@pytest.mark.parametrize("outcome",["SENT","UNKNOWN"])
def test_legacy_owner_only_terminal_notice_cannot_be_sent_again(scene,outcome):
    backend,actions,worker,clients,_queue,ledger,_reader,result=scene
    from src.workflow.v12_contracts import (
        NotificationCommand,
        NotificationKind,
        NotificationRecipient,
    )
    cid=f"purchase-exception:{result.inquiry_id}:RESEARCH:NO_MATCHING_PRODUCT"
    proof=backend._fault_evidence(result.inquiry_id,"NO_MATCHING_PRODUCT",at=NOW,event=cid,module="inquiry")
    import json
    ledger.enqueue_notification(NotificationCommand(cid,result.inquiry_id,NotificationKind.PURCHASE_EXCEPTION,(NotificationRecipient("owner","linan229@qq.com"),),"synthetic legacy","synthetic legacy",None,NOW,2,json.dumps(proof)))
    # Historical delivery receipt in this synthetic DB, not a production mutation.
    with sqlite3.connect(ledger.database_path) as db:db.execute("UPDATE workflow_v12_notification_recipients SET outcome=? WHERE command_id=?",(outcome,cid))
    actions.process(result,at=NOW)
    assert worker.run_due(now=NOW)==0 and not clients


def test_unconfirmed_derived_brand_does_not_hide_valid_original_row(scene):
    _backend,actions,worker,clients,queue,_ledger,_reader,result=scene
    with sqlite3.connect(queue.database_path) as db:db.execute("UPDATE workflow_items SET resolved_brand='SYNTH-DERIVED',brand_update_status='FAILED'")
    actions.process(result,at=NOW)
    assert worker.run_due(now=NOW)==2 and len(clients)==2


def test_unknown_purchase_uses_owner_only_unknown_notice_not_no_quote_claim(scene):
    _backend,actions,worker,clients,_queue,ledger,_reader,result=scene
    from src.workflow.v12_contracts import PurchaseOutcome
    ledger.set_purchase_state(result.inquiry_id,"cmd_synthetic",PurchaseOutcome.PRE_SAVE_READY,at=NOW)
    ledger.set_purchase_state(result.inquiry_id,"cmd_synthetic",PurchaseOutcome.AI_RECOGNIZED,at=NOW)
    ledger.begin_save_dispatch(result.inquiry_id,at=NOW)
    actions.process(result,at=NOW)
    assert worker.run_due(now=NOW)==1 and len(clients)==1
    assert clients[0].message["To"]=="linan229@qq.com"
    assert "待人工核实" in clients[0].message.get_content()
    assert "六来源未取得有效报价" not in clients[0].message["Subject"]


def test_one_recipient_transient_retry_does_not_resend_the_successful_recipient(scene):
    _backend,actions,worker,clients,_queue,_ledger,_reader,result=scene
    calls=[0]
    def factory(*args,**kwargs):
        calls[0]+=1
        c=ScriptedSMTP(login_error=TimeoutError("synthetic pre-send timeout") if calls[0]==2 else None)
        clients.append(c);return c
    worker._transport._smtp_factory=factory
    actions.process(result,at=NOW)
    assert worker.run_due(now=NOW)==2
    later=NOW+timedelta(minutes=5)
    worker._transport._clock=lambda:later
    assert worker.run_due(now=later)==1
    assert sum(c.send_attempts for c in clients)==2
    assert {str(c.message["To"]) for c in clients if c.message}=={"linan229@qq.com","shawn@inso-hk.com"}
