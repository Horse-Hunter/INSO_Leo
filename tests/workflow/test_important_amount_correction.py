"""Original producer, Backend final review/outbox and injected QQ SMTP; no network."""
import json
import smtplib
import sqlite3
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.sheets import WorksheetRow
from src.workflow.v12_contracts import NotificationRecipient
from src.workflow.v12_flow import ResearchBusinessFacts
from src.workflow.v12_notifications import (
    V12NotificationWorker,
    enqueue_important_amount_correction,
)
from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
from tests.workflow.test_rfq016_regressions import production_scene
from tests.workflow.test_v12_flow import NOW, SHEET
from tests.workflow.test_v12_smtp_transport import FakeCredentials, ScriptedSMTP, login


def scene(tmp_path, *, legacy=False):
    backend,flow,queue,ledger,reader,_record,iid=production_scene(tmp_path)
    flow._recipients=(NotificationRecipient("owner","linan229@qq.com"),NotificationRecipient("ops","shawn@inso-hk.com"))
    facts=ResearchBusinessFacts("货少",Decimal(21000),Decimal(3000),recorded_at=NOW,price_sources=("Findchips",))
    flow._research_facts.facts=facts
    clock=[NOW];flow._clock=lambda:clock[0]
    execute=flow._research.execute
    def delayed(item):
        clock[0]=NOW+timedelta(seconds=300)
        return execute(item)
    flow._research.execute=delayed
    flow.poll_and_process(reader,SHEET,now=NOW)
    reader.row=WorksheetRow(reader.row.row_position,{**reader.row.cells,"A":"发给采购"})
    observe(backend,queue,reader,clock[0])
    with sqlite3.connect(ledger.database_path) as db:
        command_id=db.execute("SELECT command_id FROM workflow_v12_notification_commands WHERE kind='IMPORTANT_ORDER'").fetchone()[0]
        if legacy:db.execute("UPDATE workflow_v12_notification_commands SET review_json=NULL,payload_version=1 WHERE command_id=?",(command_id,))
    return backend,flow,queue,ledger,reader,iid,command_id,clock


def observe(backend,queue,reader,now):
    backend._source_projection.observe(SHEET,(reader.row,),queue.all_items(),at=now)


def worker(backend,ledger,clock,server):
    return V12NotificationWorker(ledger,QQSMTPTransport(config=QQSMTPConfig(sender_address="sender@example.invalid"),
        credentials=FakeCredentials(login()),smtp_factory=lambda *a,**k:server,clock=lambda:clock[0]),
        review_current=backend._review_current_mail,prepare_content=backend._prepare_business_mail,scope="business")


def original_rows(ledger,cid):
    with sqlite3.connect(ledger.database_path) as db:
        return (db.execute("SELECT * FROM workflow_v12_notification_commands WHERE command_id=?",(cid,)).fetchall(),
            db.execute("SELECT * FROM workflow_v12_notification_recipients WHERE command_id=? ORDER BY recipient_id",(cid,)).fetchall())


def test_slow_research_does_not_preexpire_new_notice_and_fallback_preserves_verified_basis(tmp_path):
    backend,_flow,queue,ledger,reader,_iid,cid,clock=scene(tmp_path)
    requests=[]
    backend._mail_research_service=SimpleNamespace(cached_report=lambda *a:None,
        store=SimpleNamespace(get=lambda _:None,request_business=lambda cmd,order,now:requests.append((cmd.command_id,now))),
        wake=SimpleNamespace(set=lambda:None),stop=lambda **k:None)
    try:
        command=ledger.notification_command(cid)
        assert command.created_at==clock[0]==NOW+timedelta(seconds=300)
        assert backend._prepare_business_mail(command,clock[0]) is None
        assert requests==[(cid,clock[0])]
        clock[0]+=timedelta(seconds=120);observe(backend,queue,reader,clock[0])
        fallback=backend._prepare_business_mail(command,clock[0])
        assert "21,000.00" in fallback.text_body and "Findchips" in fallback.text_body
        assert "非当前市场" in fallback.text_body and "当前价格与库存尚未核实" in fallback.text_body
    finally:
        backend._mail_research_service=None;backend.shutdown()


@pytest.mark.parametrize("legacy",[False,True])
@pytest.mark.parametrize("unknown",[False,True])
def test_explicit_amount_correction_sends_once_and_never_reopens_original_or_procurement(tmp_path,legacy,unknown):
    backend,flow,queue,ledger,reader,_iid,cid,clock=scene(tmp_path,legacy=legacy)
    backend._mail_research_service=None
    try:
        clock[0]+=timedelta(seconds=120);observe(backend,queue,reader,clock[0])
        first=ScriptedSMTP();assert worker(backend,ledger,clock,first).run_due(now=clock[0])==2
        before=original_rows(ledger,cid);items=queue.all_items();purchases=len(flow._purchase_writer.commands)
        original=ledger.notification_command(cid)
        basis={"quantity":7,"reference_unit_rmb":"3000","estimated_total_rmb":"21000","recorded_at":NOW.isoformat()}
        clock[0]+=timedelta(seconds=1)
        correction=enqueue_important_amount_correction(ledger,queue,flow._research_facts,cid,
            now=clock[0],owner_authorized=True,expected_basis=basis)
        assert enqueue_important_amount_correction(ledger,queue,flow._research_facts,cid,
            now=clock[0]+timedelta(seconds=1),owner_authorized=True,expected_basis=basis)==correction
        assert set(ledger.notification_command(correction).recipients)==set(original.recipients)
        clock[0]+=timedelta(seconds=120);observe(backend,queue,reader,clock[0])
        smtp=ScriptedSMTP(send_error=smtplib.SMTPServerDisconnected("synthetic uncertainty") if unknown else None)
        sender=worker(backend,ledger,clock,smtp)
        assert sender.run_due(now=clock[0])==2 and smtp.send_attempts==2
        if not unknown:
            body=smtp.message.get_body(preferencelist=("plain",)).get_content()
            assert "21,000.00" in body and "Findchips" in body and "非当前市场" in body
        ledger.recover_abandoned_notification_attempts(at=clock[0]+timedelta(minutes=1),scope="business")
        restarted=worker(backend,ledger,clock,smtp)
        assert restarted.run_due(now=clock[0]+timedelta(minutes=2))==0 and smtp.send_attempts==2
        assert original_rows(ledger,cid)==before and queue.all_items()==items
        assert len(flow._purchase_writer.commands)==purchases==1
    finally:backend.shutdown()


@pytest.mark.parametrize("block",["authorization","changed_basis","completed","changed_quantity","expired","future_snapshot"])
def test_correction_never_bypasses_authority_original_basis_or_final_source_review(tmp_path,block):
    backend,flow,queue,ledger,reader,_iid,cid,clock=scene(tmp_path)
    backend._mail_research_service=None
    try:
        clock[0]+=timedelta(seconds=120);observe(backend,queue,reader,clock[0])
        assert worker(backend,ledger,clock,ScriptedSMTP()).run_due(now=clock[0])==2
        original=original_rows(ledger,cid)
        if block=="changed_basis":flow._research_facts.facts=replace(flow._research_facts.facts,estimated_total=Decimal(22000))
        if block in {"authorization","changed_basis"}:
            with pytest.raises(ValueError):enqueue_important_amount_correction(ledger,queue,flow._research_facts,cid,
                now=clock[0],owner_authorized=block!="authorization")
        else:
            correction=enqueue_important_amount_correction(ledger,queue,flow._research_facts,cid,now=clock[0],owner_authorized=True)
            clock[0]+=timedelta(seconds=120)
            if block=="completed":reader.row=replace(reader.row,cells={**reader.row.cells,"A":"已报价给客户"})
            if block=="changed_quantity":reader.row=replace(reader.row,cells={**reader.row.cells,"G":8})
            if block=="expired":clock[0]+=timedelta(days=9)
            if block=="future_snapshot":
                command=ledger.notification_command(correction);proof=json.loads(command.review)
                proof['business_decision']['decision_at']=(command.created_at+timedelta(days=1)).isoformat()
                with sqlite3.connect(ledger.database_path) as db:db.execute("UPDATE workflow_v12_notification_commands SET review_json=? WHERE command_id=?",(json.dumps(proof),correction))
            observe(backend,queue,reader,clock[0]);smtp=ScriptedSMTP()
            worker(backend,ledger,clock,smtp).run_due(now=clock[0])
            assert smtp.send_attempts==0
        assert original_rows(ledger,cid)==original and len(flow._purchase_writer.commands)==1
    finally:backend.shutdown()


def test_unsent_original_notice_cannot_create_competing_correction(tmp_path):
    backend,flow,queue,ledger,_reader,_iid,cid,clock=scene(tmp_path)
    try:
        with pytest.raises(ValueError,match='CORRECTION_ORIGINAL_DELIVERY_UNSETTLED'):
            enqueue_important_amount_correction(ledger,queue,flow._research_facts,cid,
                now=clock[0],owner_authorized=True)
        assert ledger.notification_delivery_states(cid)==('PENDING','PENDING')
        assert len(flow._purchase_writer.commands)==1
    finally:backend.shutdown()


def test_legacy_correction_requires_explicit_verified_original_basis(tmp_path):
    backend,flow,queue,ledger,reader,_iid,cid,clock=scene(tmp_path,legacy=True)
    backend._mail_research_service=None
    try:
        clock[0]+=timedelta(seconds=120);observe(backend,queue,reader,clock[0])
        assert worker(backend,ledger,clock,ScriptedSMTP()).run_due(now=clock[0])==2
        with pytest.raises(TypeError,match='CORRECTION_ORIGINAL_BASIS_REQUIRED'):
            enqueue_important_amount_correction(ledger,queue,flow._research_facts,cid,
                now=clock[0],owner_authorized=True)
        assert len(flow._purchase_writer.commands)==1
    finally:backend.shutdown()
