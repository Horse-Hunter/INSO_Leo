"""Every restored legitimate producer traverses the original queue/fake SMTP."""
from datetime import UTC, datetime

from src.gui.contracts import RunState
from src.launcher import sales_header
from src.order_mail.contracts import OrderError
from src.workflow.order_notifications import OrderExceptionNotifications
from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
from tests.workflow.test_rfq016_regressions import production_scene, real_fake_smtp
from tests.workflow.test_v12_flow import NOW
from tests.workflow.test_v12_smtp_transport import FakeCredentials, ScriptedSMTP, login


def test_confirmed_manual_auth_before_order_binding_still_notifies_owner_once(tmp_path):
    backend,*_=production_scene(tmp_path)
    from src.workflow.v13_integration import V13HoldStore
    V13HoldStore(backend._v12_store.database_path).migrate()
    backend._v13_ledger_ready=True
    try:
        backend._active_inso_inquiry=None
        backend._source_projection.rows.clear()
        backend._run_id="synthetic-running-session"
        backend._state=RunState.RUNNING
        backend._site_manual_wait.add("INSO")
        backend._notify_runtime_fault("synthetic-challenge","INSO_AUTHENTICATION_REQUIRED",at=NOW)
        worker,smtp=real_fake_smtp(backend._v12_store,now=NOW,review_current=backend._review_current_mail)
        assert worker.run_due(now=NOW)==1 and smtp.send_attempts==1
        backend._notify_runtime_fault("another-poll","INSO_AUTHENTICATION_REQUIRED",at=NOW)
        assert worker.run_due(now=NOW)==0 and smtp.send_attempts==1
    finally:backend.shutdown()


def test_actual_owner_manual_order_failure_has_verified_notice_not_blanket_suppression(tmp_path,monkeypatch):
    client=ScriptedSMTP()
    transport=QQSMTPTransport(config=QQSMTPConfig(sender_address="sender@example.invalid"),credentials=FakeCredentials(login()),smtp_factory=lambda *a,**k:client,clock=lambda:datetime.now(UTC))
    service=OrderExceptionNotifications(tmp_path,transport=transport,background=False)
    def unsupported(*args):raise OrderError("LEAD_TIME")
    monkeypatch.setattr(sales_header,"sales_config",unsupported)
    try:
        stage,_=sales_header.run_sales_header_check(config_path="synthetic",production_path="synthetic",root=tmp_path,notify=service.notify)
        assert stage=="STOPPED" and client.send_attempts==1
        assert client.message["To"]=="linan229@qq.com"
        assert "交期" in client.message.get_content()
    finally:service.close()


def test_durable_unsubmitted_purchase_validation_failure_notifies_owner(tmp_path):
    from decimal import Decimal
    from types import SimpleNamespace

    from src.launcher.backend import ProductionBackend
    from src.launcher.purchase_completion import PurchaseCompletionActions
    from tests.workflow.test_v12_flow import (
        SHEET,
        FakeSheetsReader,
        ResearchBusinessFacts,
        _make_flow,
    )
    flow,queue,ledger,_research,_checker,_provider,writer,_worker=_make_flow(tmp_path,facts=ResearchBusinessFacts("货足",Decimal(10),Decimal(2)))
    writer._recognized=("SYNTH-OTHER","Brand-X",7)
    reader=FakeSheetsReader(tier="C")
    result,=flow.poll_and_process(reader,SHEET,now=NOW)
    backend=ProductionBackend(root=tmp_path)
    backend._store,backend._v12_store=queue,ledger
    backend._mail_brief=SimpleNamespace(cached_lines=lambda _:())
    backend._source_projection.observe(SHEET,(reader.row,),queue.all_items(),at=NOW)
    try:
        actions=PurchaseCompletionActions(workflow_store=queue,v12_store=ledger,reader=reader,writer_factory=lambda:None,mail_evidence=backend._fault_evidence)
        actions.process(result,at=NOW)
        worker,smtp=real_fake_smtp(ledger,now=NOW,review_current=backend._review_current_mail)
        assert worker.run_due(now=NOW)==1 and smtp.send_attempts==1
        assert "未发采购" in smtp.message.get_content()
    finally:backend.shutdown()


def test_verified_icnet_manual_challenge_is_not_lost_in_generic_read_defer(tmp_path,monkeypatch):
    import pytest

    from src.research.source_contracts import (
        EvidenceField,
        ResearchSource,
        SourceEvidence,
        SourceOutcome,
        SourceResult,
    )
    from src.workflow.v12_faults import V12Fault
    from src.workflow.v13_integration import V13HoldStore
    backend,*rest=production_scene(tmp_path)
    V13HoldStore(backend._v12_store.database_path).migrate()
    backend._v13_ledger_ready=True;backend._run_id="synthetic-ic-challenge";backend._state=RunState.RUNNING
    monkeypatch.setattr("src.launcher.backend.utc_now",lambda:NOW)
    source=SourceResult(ResearchSource.IC_NET,SourceOutcome.SOURCE_UNAVAILABLE,SourceEvidence(ResearchSource.IC_NET,"SYNTH",None,SourceOutcome.SOURCE_UNAVAILABLE,NOW,fields=(EvidenceField("failure_code","MANUAL_VERIFICATION_REQUIRED"),)))
    try:
        with pytest.raises(V12Fault):backend._observe_source_failure(rest[-1],source)
        worker,smtp=real_fake_smtp(backend._v12_store,now=NOW,review_current=backend._review_current_mail)
        assert worker.run_due(now=NOW)==1 and smtp.send_attempts==1
    finally:backend.shutdown()


import json
import sqlite3
from dataclasses import replace

import pytest


def runtime_scene(tmp_path):
    from src.workflow.v13_integration import V13HoldStore
    backend,*rest=production_scene(tmp_path)
    V13HoldStore(backend._v12_store.database_path).migrate()
    backend._v13_ledger_ready=True;backend._run_id="synthetic-runtime";backend._state=RunState.RUNNING
    return backend,rest


@pytest.mark.parametrize("closed",["recovered","owner_stop","new_run_without_fresh_proof"])
def test_runtime_manual_notice_is_rechecked_before_actual_smtp(tmp_path,closed):
    backend,_=runtime_scene(tmp_path)
    try:
        backend._active_inso_inquiry=None;backend._source_projection.rows.clear();backend._site_manual_wait.add("INSO")
        backend._notify_runtime_fault("synthetic","INSO_AUTHENTICATION_REQUIRED",at=NOW)
        if closed=="recovered":backend._site_manual_wait.clear()
        if closed=="owner_stop":backend._owner_stop_requested=True
        if closed=="new_run_without_fresh_proof":backend._run_id="different-runtime"
        worker,smtp=real_fake_smtp(backend._v12_store,now=NOW,review_current=backend._review_current_mail)
        assert worker.run_due(now=NOW)==0 and smtp.send_attempts==0
    finally:backend.shutdown()


def test_one_shared_manual_challenge_notifies_once_when_later_bound_to_order(tmp_path):
    backend,rest=runtime_scene(tmp_path)
    try:
        reader=rest[-3];iid=rest[-1]
        backend._active_inso_inquiry=None;backend._source_projection.rows.clear();backend._site_manual_wait.add("INSO")
        backend._notify_runtime_fault("before-order","INSO_AUTHENTICATION_REQUIRED",at=NOW)
        worker,smtp=real_fake_smtp(backend._v12_store,now=NOW,review_current=backend._review_current_mail)
        assert worker.run_due(now=NOW)==1 and smtp.send_attempts==1
        from tests.workflow.test_v12_flow import SHEET
        backend._source_projection.observe(SHEET,(reader.row,),backend._store.all_items(),at=NOW)
        backend._active_inso_inquiry=iid
        backend._notify_runtime_fault("after-order","INSO_AUTHENTICATION_REQUIRED",at=NOW)
        assert worker.run_due(now=NOW)==0 and smtp.send_attempts==1
    finally:backend.shutdown()


@pytest.mark.parametrize("code,expected",[("MANUAL_VERIFICATION_REQUIRED",1),("CAPTCHA_REQUIRED",1),("CREDENTIAL_REJECTED",1),("CREDENTIALS_UNAVAILABLE",1),("BROWSER_TIMEOUT",0),("LOGIN_NOT_CONFIRMED",0),("SOURCE_UNAVAILABLE",0),("CDP_TIMEOUT",0)])
def test_icnet_manual_evidence_uses_exact_codes_not_login_word_guess(tmp_path,monkeypatch,code,expected):
    from src.research.source_contracts import (
        EvidenceField,
        ResearchSource,
        SourceEvidence,
        SourceOutcome,
        SourceResult,
    )
    from src.workflow.v12_faults import V12Fault
    backend,rest=runtime_scene(tmp_path)
    monkeypatch.setattr("src.launcher.backend.utc_now",lambda:NOW)
    source=SourceResult(ResearchSource.IC_NET,SourceOutcome.SOURCE_UNAVAILABLE,SourceEvidence(ResearchSource.IC_NET,"SYNTH",None,SourceOutcome.SOURCE_UNAVAILABLE,NOW,fields=(EvidenceField("failure_code",code),)))
    try:
        with pytest.raises(V12Fault):backend._observe_source_failure(rest[-1],source)
        worker,smtp=real_fake_smtp(backend._v12_store,now=NOW,review_current=backend._review_current_mail)
        assert worker.run_due(now=NOW)==expected and smtp.send_attempts==expected
        if expected:
            assert "IC.net" in smtp.message.get_content()
            assert "INSO登录" not in smtp.message.get_content()
    finally:backend.shutdown()


def manual_service(tmp_path,*,unknown=False):
    client=ScriptedSMTP(send_error=TimeoutError() if unknown else None)
    transport=QQSMTPTransport(config=QQSMTPConfig(sender_address="sender@example.invalid"),credentials=FakeCredentials(login()),smtp_factory=lambda *a,**k:client,clock=lambda:NOW)
    return OrderExceptionNotifications(tmp_path,transport=transport,background=False),client


def manual_command():
    from src.workflow.order_notifications import exception_command
    return exception_command(invocation_id="synthetic-manual",pi_no="SYNTH-PI",situation="合同信息未通过，任务已停止。",treatment="请核对原页面。",at=NOW,event_code="REQUIRED")


def test_manual_notice_recovery_changes_only_mail_proof_not_business_rows(tmp_path):
    service,smtp=manual_service(tmp_path)
    try:
        service.enqueue(manual_command())
        with sqlite3.connect(service.store.database_path) as db:before=db.execute("SELECT * FROM workflow_items").fetchall()
        service.resolve_order("SYNTH-PI",at=NOW)
        assert service.worker.run_due(now=NOW)==0 and smtp.send_attempts==0
        with sqlite3.connect(service.store.database_path) as db:
            assert db.execute("SELECT * FROM workflow_items").fetchall()==before
            assert json.loads(db.execute("SELECT review_json FROM workflow_v12_notification_commands").fetchone()[0])["active"] is False
    finally:service.close()


@pytest.mark.parametrize("unknown",[False,True])
def test_manual_order_sent_unknown_survives_service_restart_without_resend(tmp_path,unknown):
    service,smtp=manual_service(tmp_path,unknown=unknown)
    service.enqueue(manual_command());service.worker.run_due(now=NOW);service.close()
    assert smtp.send_attempts==1
    restarted,another=manual_service(tmp_path)
    try:
        restarted.enqueue(manual_command())
        assert restarted.worker.run_due(now=NOW)==0 and another.send_attempts==0
    finally:restarted.close()


def test_manual_current_pending_survives_restart_and_remains_deliverable(tmp_path):
    service,_=manual_service(tmp_path)
    service.enqueue(manual_command());service.close()
    restarted,smtp=manual_service(tmp_path)
    try:assert restarted.worker.run_due(now=NOW)==1 and smtp.send_attempts==1
    finally:restarted.close()


def test_manual_wrong_recipient_is_never_sent(tmp_path):
    from src.workflow.v12_contracts import NotificationRecipient
    service,smtp=manual_service(tmp_path)
    try:
        command=manual_command()
        service.enqueue(replace(command,recipients=(NotificationRecipient("other","other@example.invalid"),)))
        assert service.worker.run_due(now=NOW)==0 and smtp.send_attempts==0
    finally:service.close()


def test_unknown_manual_error_cannot_claim_successful_queue_submission(tmp_path,monkeypatch):
    service,smtp=manual_service(tmp_path)
    def unclassified(*args):raise OrderError("SYNTH_UNCLASSIFIED")
    monkeypatch.setattr(sales_header,"sales_config",unclassified)
    try:
        stage,message=sales_header.run_sales_header_check(config_path="synthetic",production_path="synthetic",root=tmp_path,notify=service.notify)
        assert stage=="STOPPED" and "通知不可用" in message and smtp.send_attempts==0
    finally:service.close()


def test_quote_without_row_error_is_safely_ignored_not_a_mail_exception():
    from types import SimpleNamespace

    from src.launcher.v13_integration import notify_quotation
    def forbidden(*args,**kwargs):raise AssertionError("normal result cannot enqueue an exception")
    notify_quotation(SimpleNamespace(observe_incident=forbidden),SimpleNamespace(inquiry_id="synthetic",row_error_reason=None),"key","episode",at=NOW)


def test_current_model_difference_is_deliverable_to_original_pair_without_false_write_claim(tmp_path):
    from types import SimpleNamespace

    from src.sheets import WorksheetRow
    from tests.workflow.test_v12_flow import SHEET
    backend,rest=runtime_scene(tmp_path)
    try:
        reader=rest[-3];record=rest[-2];iid=rest[-1]
        reader.row=WorksheetRow(record.row_position,{**reader.row.cells,"A":"发给采购"})
        backend._source_projection.observe(SHEET,(reader.row,),backend._store.all_items(),at=NOW)
        result=SimpleNamespace(inquiry_id=iid,quotation=SimpleNamespace(payload=("synthetic-date","SYNTH-ACTUAL")),source_worksheet=SHEET,source_row_position=record.row_position)
        backend._notify_model_difference(result,"Mpn-1",at=NOW)
        worker,smtp=real_fake_smtp(backend._v12_store,now=NOW,review_current=backend._review_current_mail)
        assert worker.run_due(now=NOW)==2 and smtp.send_attempts==2
        assert "型号与原表不同" in smtp.message.get_content()
        assert "不作为报价写入成功或失败的凭据" in smtp.message.get_content()
    finally:backend.shutdown()


def test_unrelated_malformed_legacy_proof_cannot_crash_verified_login_dispatch(tmp_path):
    backend,_=runtime_scene(tmp_path)
    try:
        backend._active_inso_inquiry=None;backend._source_projection.rows.clear();backend._site_manual_wait.add("INSO")
        backend._notify_runtime_fault("synthetic","INSO_AUTHENTICATION_REQUIRED",at=NOW)
        with sqlite3.connect(backend._v12_store.database_path) as db:
            db.execute("INSERT INTO workflow_v12_notification_commands(command_id,inquiry_id,kind,subject,text_body,created_at,review_json,payload_version) VALUES ('synthetic-legacy',NULL,'PURCHASE_EXCEPTION','synthetic','synthetic',?,'null',2)",(NOW.isoformat(),))
            db.execute("INSERT INTO workflow_v12_notification_recipients(command_id,recipient_id,address,outcome,attempt_count) VALUES ('synthetic-legacy','owner','linan229@qq.com','SENT',1)")
        worker,smtp=real_fake_smtp(backend._v12_store,now=NOW,review_current=backend._review_current_mail)
        assert worker.run_due(now=NOW)==1 and smtp.send_attempts==1
    finally:backend.shutdown()


@pytest.mark.parametrize("reason", ["SESSION_STALE", "CONTROL_NOT_FOUND", None])
def test_non_ai_purchase_failure_does_not_emit_false_ai_mismatch_mail(tmp_path, reason):
    from decimal import Decimal
    from types import SimpleNamespace

    from src.launcher.backend import ProductionBackend
    from src.launcher.purchase_completion import PurchaseCompletionActions
    from src.workflow.v12_contracts import (
        PurchaseDraftResult,
        PurchaseOutcome,
        ReasonCode,
    )
    from tests.workflow.test_v12_flow import (
        SHEET,
        FakeSheetsReader,
        ResearchBusinessFacts,
        _make_flow,
    )

    flow, queue, ledger, _research, _checker, _provider, writer, _worker = _make_flow(
        tmp_path, facts=ResearchBusinessFacts("synthetic", Decimal(10), Decimal(2)))
    writer.prepare = lambda command: PurchaseDraftResult(command.command_id,
        PurchaseOutcome.VALIDATION_FAILED, NOW, reason_code=ReasonCode(reason) if reason else None)
    reader = FakeSheetsReader(tier="C")
    result, = flow.poll_and_process(reader, SHEET, now=NOW)
    backend = ProductionBackend(root=tmp_path)
    backend._store, backend._v12_store = queue, ledger
    backend._mail_brief = SimpleNamespace(cached_lines=lambda _: ())
    backend._source_projection.observe(SHEET, (reader.row,), queue.all_items(), at=NOW)
    try:
        actions = PurchaseCompletionActions(workflow_store=queue, v12_store=ledger, reader=reader,
            writer_factory=lambda: None, mail_evidence=backend._fault_evidence)
        actions.process(result, at=NOW)
        worker, smtp = real_fake_smtp(ledger, now=NOW, review_current=backend._review_current_mail)
        assert worker.run_due(now=NOW) == 0 and smtp.send_attempts == 0
    finally:
        backend.shutdown()
