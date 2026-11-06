"""Transient Research failures retain original durable retry budget."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from src.research import ResearchResult, ResearchStatus
from src.research.contracts import ResearchReasonCode
from src.workflow.v12_contracts import BusinessState
from tests.workflow.test_v12_flow import (
    NOW,
    SHEET,
    FakeSheetsReader,
    ResearchBusinessFacts,
    _make_flow,
)


@pytest.mark.parametrize("restart",[False,True])
def test_temporary_source_failure_is_retried_without_manual_rerun_or_duplicate_purchase(tmp_path,restart):
    flow,queue,ledger,research,_checker,_facts,writer,_worker=_make_flow(tmp_path,
        facts=ResearchBusinessFacts("货足",Decimal(2),Decimal(2)))
    original=research.execute
    research.execute=lambda item:ResearchResult(item.inquiry_id,ResearchStatus.RETRYABLE_FAILURE,
        reason_code=ResearchReasonCode.SOURCE_UNAVAILABLE)
    reader=FakeSheetsReader(tier="C")
    reader.row=replace(reader.row,source_order_date=NOW.date().isoformat())
    from src.workflow.v12_flow import V12WorkflowCoordinator
    flow._record_admitted=V12WorkflowCoordinator._record_admitted.__get__(flow)
    flow._brief_snapshot=lambda _:()
    first,=flow.poll_and_process(reader,SHEET,now=NOW)
    item=queue.get_by_inquiry_id(first.inquiry_id)
    assert item.status.value=="RETRY_WAIT"
    assert item.attempt_count==1 and item.created_at==NOW and item.next_attempt_at==NOW+timedelta(minutes=15)
    assert ledger.business_state(item.inquiry_id) is BusinessState.RESEARCH_RETRY_WAIT
    assert not writer.commands
    if restart:flow.initialize_run_state(now=NOW+timedelta(minutes=1))
    research.execute=original
    second,=flow.poll_and_process(reader,SHEET,now=NOW+timedelta(minutes=16))
    current=queue.get_by_inquiry_id(second.inquiry_id)
    assert current.status.value=="COMPLETED" and current.created_at==NOW
    assert len(queue.all_items())==1 and len(writer.commands)==1
    flow.poll_and_process(reader,SHEET,now=NOW+timedelta(minutes=32))
    assert len(writer.commands)==1


def test_current_legacy_premature_failure_recovers_remaining_budget_on_fresh_normal_poll(tmp_path):
    flow,queue,_ledger,research,_checker,_facts,writer,_worker=_make_flow(tmp_path,
        facts=ResearchBusinessFacts("货足",Decimal(2),Decimal(2)))
    reader=FakeSheetsReader(tier="C")
    reader.row=replace(reader.row,source_order_date=NOW.date().isoformat())
    from src.workflow.v12_flow import V12WorkflowCoordinator
    flow._record_admitted=V12WorkflowCoordinator._record_admitted.__get__(flow)
    flow._brief_snapshot=lambda _:()
    original=research.execute
    research.execute=lambda item:ResearchResult(item.inquiry_id,ResearchStatus.RETRYABLE_FAILURE,
        reason_code=ResearchReasonCode.SOURCE_UNAVAILABLE)
    first,=flow.poll_and_process(reader,SHEET,now=NOW)
    item=queue.get_by_inquiry_id(first.inquiry_id)
    # Synthetic old-version terminal state only; never a live-record repair.
    queue.finish_row_failure(item.id,"SOURCE_UNAVAILABLE",now=NOW)
    from src.workflow.v12_contracts import EventType
    flow._set_state(item.inquiry_id,BusinessState.RESEARCH_FAILED,EventType.RESEARCH_FAILED,NOW)
    research.execute=original
    result,=flow.poll_and_process(reader,SHEET,now=NOW+timedelta(minutes=16))
    current=queue.get_by_inquiry_id(result.inquiry_id)
    assert current.status.value=="COMPLETED" and current.attempt_count==2
    assert current.created_at==NOW and current.source_order_date==NOW.date().isoformat()
    assert len(writer.commands)==1


@pytest.mark.parametrize("block",["old","future_intake","old_source","no_source_date","budget_exhausted",
    "unknown_reason","purchase_unknown","quote_unknown","unbound_quote_unknown","owner_completed"])
def test_legacy_source_retry_never_bypasses_age_budget_current_status_or_external_unknown(tmp_path,block):
    import json
    import sqlite3

    from src.workflow.v12_contracts import EventType, PurchaseOutcome
    from src.workflow.v12_flow import V12WorkflowCoordinator
    flow,queue,ledger,research,_checker,_facts,writer,_worker=_make_flow(tmp_path,
        facts=ResearchBusinessFacts("货足",Decimal(2),Decimal(2)))
    reader=FakeSheetsReader(tier="C");reader.row=replace(reader.row,source_order_date=NOW.date().isoformat())
    flow._record_admitted=V12WorkflowCoordinator._record_admitted.__get__(flow);flow._brief_snapshot=lambda _:()
    research.execute=lambda item:ResearchResult(item.inquiry_id,ResearchStatus.RETRYABLE_FAILURE,reason_code=ResearchReasonCode.SOURCE_UNAVAILABLE)
    first,=flow.poll_and_process(reader,SHEET,now=NOW);item=queue.get_by_inquiry_id(first.inquiry_id)
    queue.finish_row_failure(item.id,"SOURCE_UNAVAILABLE",now=NOW)
    flow._set_state(item.inquiry_id,BusinessState.RESEARCH_FAILED,EventType.RESEARCH_FAILED,NOW)
    now=NOW+timedelta(minutes=16);holds=None;held_before=None;purchase_before=None
    if block=="old":now=NOW+timedelta(days=9)
    if block=="future_intake":
        with sqlite3.connect(queue.database_path) as db:db.execute("UPDATE workflow_items SET created_at=?",((NOW+timedelta(days=1)).isoformat(),))
    if block=="old_source":reader.row=replace(reader.row,source_order_date=(NOW-timedelta(days=9)).date().isoformat())
    if block=="no_source_date":
        reader.row=replace(reader.row,source_order_date=None)
        with sqlite3.connect(queue.database_path) as db:
            payload=json.loads(db.execute("SELECT record_identity_json FROM workflow_items").fetchone()[0]);payload.pop("source_order_date",None)
            db.execute("UPDATE workflow_items SET record_identity_json=?",(json.dumps(payload),))
    if block=="budget_exhausted":
        with sqlite3.connect(queue.database_path) as db:db.execute("UPDATE workflow_items SET attempt_count=4")
    if block=="unknown_reason":
        with sqlite3.connect(queue.database_path) as db:db.execute("UPDATE workflow_items SET last_error='SYNTHETIC_UNKNOWN'")
    if block=="owner_completed":reader.row=replace(reader.row,cells={**reader.row.cells,"A":"已报价给客户"})
    if block=="purchase_unknown":
        ledger.set_purchase_state(item.inquiry_id,"synthetic-draft",PurchaseOutcome.PRE_SAVE_READY,at=NOW)
        ledger.set_purchase_state(item.inquiry_id,"synthetic-draft",PurchaseOutcome.AI_RECOGNIZED,at=NOW)
        ledger.begin_save_dispatch(item.inquiry_id,at=NOW);purchase_before=ledger.purchase_state(item.inquiry_id)
    if block in {"quote_unknown","unbound_quote_unknown"}:
        from src.workflow.v13_integration import V13HoldStore
        from src.workflow.v13_quotation import (
            QuotationOutcome,
            RowErrorReason,
            V13QuotationResult,
        )
        holds=V13HoldStore(queue.database_path);holds.migrate()
        holds.hold(V13QuotationResult(item.inquiry_id if block=="quote_unknown" else None,item.record_identity,
            item.mpn,QuotationOutcome.ROW_FAILED,None,RowErrorReason.UPDATE_RESULT_UNCONFIRMED,SHEET,item.record_identity.row_position),item.record_identity)
        held_before=holds.active()
    attempts=queue.get_by_inquiry_id(item.inquiry_id).attempt_count
    flow.poll_and_process(reader,SHEET,now=now)
    assert not writer.commands and queue.get_by_inquiry_id(item.inquiry_id).attempt_count==attempts
    if holds is not None:assert holds.active()==held_before
    if purchase_before is not None:assert ledger.purchase_state(item.inquiry_id)==purchase_before


def test_source_retry_budget_remains_bounded_across_poll_cycles(tmp_path):
    from src.workflow.v12_flow import V12WorkflowCoordinator
    flow,queue,ledger,research,_checker,_facts,writer,_worker=_make_flow(tmp_path)
    reader=FakeSheetsReader(tier="C");reader.row=replace(reader.row,source_order_date=NOW.date().isoformat())
    flow._record_admitted=V12WorkflowCoordinator._record_admitted.__get__(flow);flow._brief_snapshot=lambda _:()
    calls=[]
    def unavailable(item):
        calls.append(item.inquiry_id)
        return ResearchResult(item.inquiry_id,ResearchStatus.RETRYABLE_FAILURE,reason_code=ResearchReasonCode.SOURCE_UNAVAILABLE)
    research.execute=unavailable
    for minutes in (0,15,45,105):flow.poll_and_process(reader,SHEET,now=NOW+timedelta(minutes=minutes))
    item=queue.all_items()[0]
    assert item.status.value=="FAILED" and item.attempt_count==4
    assert ledger.business_state(item.inquiry_id) is BusinessState.RESEARCH_FAILED
    flow.poll_and_process(reader,SHEET,now=NOW+timedelta(minutes=400))
    assert len(calls)==4 and not writer.commands



def test_legacy_retry_recovery_is_atomic_if_event_commit_fails(tmp_path,monkeypatch):
    from src.workflow import v12_store as persistence
    from src.workflow.v12_contracts import EventType
    from src.workflow.v12_flow import V12WorkflowCoordinator
    flow,queue,ledger,research,_checker,_facts,_writer,_worker=_make_flow(tmp_path)
    reader=FakeSheetsReader(tier="C");reader.row=replace(reader.row,source_order_date=NOW.date().isoformat())
    flow._record_admitted=V12WorkflowCoordinator._record_admitted.__get__(flow);flow._brief_snapshot=lambda _:()
    research.execute=lambda item:ResearchResult(item.inquiry_id,ResearchStatus.RETRYABLE_FAILURE,reason_code=ResearchReasonCode.SOURCE_UNAVAILABLE)
    first,=flow.poll_and_process(reader,SHEET,now=NOW);item=queue.get_by_inquiry_id(first.inquiry_id)
    queue.finish_row_failure(item.id,"SOURCE_UNAVAILABLE",now=NOW)
    flow._set_state(item.inquiry_id,BusinessState.RESEARCH_FAILED,EventType.RESEARCH_FAILED,NOW)
    before=queue.get_by_inquiry_id(item.inquiry_id);events=ledger.event_history(item.inquiry_id)
    def fail(*args):raise RuntimeError("synthetic event commit failure")
    monkeypatch.setattr(persistence,"_insert_event",fail)
    with pytest.raises(RuntimeError,match="synthetic"):
        ledger.resume_premature_source_retry(item.inquiry_id,item.record_identity,at=NOW+timedelta(minutes=16))
    assert queue.get_by_inquiry_id(item.inquiry_id)==before
    assert ledger.business_state(item.inquiry_id) is BusinessState.RESEARCH_FAILED
    assert ledger.event_history(item.inquiry_id)==events


@pytest.mark.parametrize("recovery",["restart","legacy"])
def test_shahab_explicit_date_survives_retry_and_legacy_recovery(tmp_path,recovery):
    from src.sheets import WorksheetIdentity, WorksheetRow
    from src.workflow.v12_contracts import EventType
    from src.workflow.v12_flow import V12WorkflowCoordinator
    flow,queue,_ledger,research,_,_,writer,_=_make_flow(tmp_path,
        facts=ResearchBusinessFacts("货足",Decimal(2),Decimal(2)))
    flow._record_admitted=V12WorkflowCoordinator._record_admitted.__get__(flow)
    flow._brief_snapshot=lambda _:()
    reader=type("Reader",(),{"read_rows":lambda self,w:(WorksheetRow(3,
        {"A":NOW.date().isoformat(),"B":"未发","C":1,"D":"Mpn-1","E":"Brand-X","F":7,"G":"PCS"}),)})()
    sheet=WorksheetIdentity("synthetic-sheet","SHAHAB")
    original=research.execute
    research.execute=lambda item:ResearchResult(item.inquiry_id,ResearchStatus.RETRYABLE_FAILURE,
        reason_code=ResearchReasonCode.SOURCE_UNAVAILABLE)
    first,=flow.poll_and_process(reader,sheet,now=NOW)
    item=queue.get_by_inquiry_id(first.inquiry_id)
    if recovery=="restart":
        assert item.source_order_date==NOW.date().isoformat()
        flow.initialize_run_state(now=NOW+timedelta(minutes=1))
    else:
        import json
        import sqlite3
        queue.finish_row_failure(item.id,"SOURCE_UNAVAILABLE",now=NOW)
        flow._set_state(item.inquiry_id,BusinessState.RESEARCH_FAILED,EventType.RESEARCH_FAILED,NOW)
        with sqlite3.connect(queue.database_path) as db:
            payload=json.loads(db.execute("SELECT record_identity_json FROM workflow_items").fetchone()[0])
            payload.pop("source_order_date",None)
            db.execute("UPDATE workflow_items SET record_identity_json=?",(json.dumps(payload),))
    research.execute=original
    flow.poll_and_process(reader,sheet,now=NOW+timedelta(minutes=16))
    current=queue.get_by_inquiry_id(item.inquiry_id)
    assert current.attempt_count==2 and len(writer.commands)==1
    assert current.created_at==NOW and current.source_order_date==NOW.date().isoformat()


@pytest.mark.parametrize("restart",[False,True])
@pytest.mark.parametrize("second_failure",[False,True])
def test_fresh_read_failure_after_completed_research_resumes_routing_without_reresearch(tmp_path,restart,second_failure):
    from src.sheets.google_reader import GoogleSheetsReadUnavailable
    from src.workflow.v12_flow import V12WorkflowCoordinator
    flow,queue,ledger,research,_,_,writer,_=_make_flow(tmp_path,
        facts=ResearchBusinessFacts("货足",Decimal(2),Decimal(2)))
    flow._record_admitted=V12WorkflowCoordinator._record_admitted.__get__(flow)
    flow._brief_snapshot=lambda _:()
    reader=FakeSheetsReader(tier="C");reader.row=replace(reader.row,source_order_date=NOW.date().isoformat())
    original=reader.read_rows;failed=[]
    def read(w):
        items=queue.all_items()
        if items and items[0].status.value=="COMPLETED" and not failed:
            failed.append(True);raise GoogleSheetsReadUnavailable("synthetic source read")
        if (second_failure and items and failed==[True]
                and ledger.business_state(items[0].inquiry_id) is BusinessState.ROUTING):
            failed.append(True);raise GoogleSheetsReadUnavailable("synthetic second read")
        return original(w)
    reader.read_rows=read
    with pytest.raises(GoogleSheetsReadUnavailable):flow.poll_and_process(reader,SHEET,now=NOW)
    if restart:flow.initialize_run_state(now=NOW+timedelta(minutes=1))
    if second_failure:
        with pytest.raises(GoogleSheetsReadUnavailable):
            flow.poll_and_process(reader,SHEET,now=NOW+timedelta(minutes=16))
    else:flow.poll_and_process(reader,SHEET,now=NOW+timedelta(minutes=16))
    flow.poll_and_process(reader,SHEET,now=NOW+timedelta(minutes=32))
    assert len(research.inputs)==1 and len(writer.commands)==1



@pytest.mark.parametrize("protection",[None,"unknown_release","exhausted_budget","unknown_purchase"])
def test_released_unprepared_source_retry_keeps_remaining_budget_across_restart(tmp_path,protection):
    from src.workflow import ResearchPreparationError
    from src.workflow.v12_flow import V12WorkflowCoordinator
    flow,queue,_ledger,research,_,_,writer,_=_make_flow(tmp_path,
        facts=ResearchBusinessFacts("货足",Decimal(2),Decimal(2)))
    flow._record_admitted=V12WorkflowCoordinator._record_admitted.__get__(flow)
    flow._brief_snapshot=lambda _:()
    reader=FakeSheetsReader(tier="C");reader.row=replace(reader.row,source_order_date=NOW.date().isoformat())
    execute=research.execute
    research.execute=lambda item:ResearchResult(item.inquiry_id,ResearchStatus.RETRYABLE_FAILURE,
        reason_code=ResearchReasonCode.SOURCE_UNAVAILABLE)
    first,=flow.poll_and_process(reader,SHEET,now=NOW)
    def unavailable(item):raise ResearchPreparationError("synthetic prepare unavailable")
    research.execute=unavailable
    with pytest.raises(ResearchPreparationError):
        flow.poll_and_process(reader,SHEET,now=NOW+timedelta(minutes=16))
    item=queue.get_by_inquiry_id(first.inquiry_id)
    assert item.status.value=="QUEUED" and item.attempt_count==1 and not writer.commands
    if protection in {"unknown_release","exhausted_budget"}:
        import sqlite3
        with sqlite3.connect(queue.database_path) as db:
            if protection=="unknown_release":db.execute("UPDATE workflow_items SET last_error='synthetic other release'")
            else:db.execute("UPDATE workflow_items SET attempt_count=4")
    elif protection=="unknown_purchase":
        from src.workflow.v12_contracts import PurchaseOutcome
        _ledger.set_purchase_state(item.inquiry_id,"synthetic-draft",PurchaseOutcome.PRE_SAVE_READY,at=NOW)
        _ledger.set_purchase_state(item.inquiry_id,"synthetic-draft",PurchaseOutcome.AI_RECOGNIZED,at=NOW)
        _ledger.begin_save_dispatch(item.inquiry_id,at=NOW)
    flow.initialize_run_state(now=NOW+timedelta(minutes=17))
    if protection:
        assert queue.get_by_inquiry_id(item.inquiry_id).status.value=="MANUAL_REVIEW"
        assert not writer.commands
        return
    assert queue.get_by_inquiry_id(item.inquiry_id).status.value=="QUEUED"
    research.execute=execute
    flow.poll_and_process(reader,SHEET,now=NOW+timedelta(minutes=18))
    current=queue.get_by_inquiry_id(item.inquiry_id)
    assert current.status.value=="COMPLETED" and current.attempt_count==2
    assert current.created_at==NOW and len(writer.commands)==1
