"""Synthetic new-row admission must use real source evidence, never today's guess."""
from datetime import datetime, timezone
from types import SimpleNamespace

from src.sheets import WorksheetIdentity
from src.sheets.pending import query_pending_records
from src.workflow.automatic_admission import admit

NOW=datetime(2026,11,4,12,tzinfo=timezone.utc)
WS=WorksheetIdentity("synthetic","2026")


def source(day="2026-11-04"):
    return SimpleNamespace(row_position=2,cells={"A":"未发","C":"C","D":"SYNTHETIC", "E":"SYNTH-PART","F":"SYNTH-BRAND","G":1},source_order_date=day)


def test_current_source_date_admits_new_unqueued_inquiry_without_minting_intake():
    row=source();record,=query_pending_records(SimpleNamespace(read_rows=lambda _: (row,)),WS)
    result=admit(record.record_identity,row,(),lambda:None,now=NOW,module="inquiry")
    assert result.allowed and result.date_source=="SOURCE_ORDER_DATE"


def test_absent_source_date_still_cannot_admit_undated_history():
    row=source(None);record,=query_pending_records(SimpleNamespace(read_rows=lambda _: (row,)),WS)
    assert not admit(record.record_identity,row,(),lambda:None,now=NOW,module="inquiry").allowed


from datetime import timedelta

import pytest

from src.workflow.store import WorkflowStateStore


@pytest.mark.parametrize("day", [None,"", "2026-10-01", "not-a-date", "2026-11-05"])
def test_missing_expired_malformed_future_dates_never_reach_new_queue(day):
    row=source(day);record,=query_pending_records(SimpleNamespace(read_rows=lambda _: (row,)),WS)
    assert not admit(record.record_identity,row,(),lambda:None,now=NOW,module="inquiry").allowed


def test_recent_sheet_date_never_revives_month_old_durable_item():
    row=source();record,=query_pending_records(SimpleNamespace(read_rows=lambda _: (row,)),WS)
    result=admit(record.record_identity,row,(),lambda:NOW-timedelta(days=31),now=NOW,module="inquiry")
    assert not result.allowed and result.reason=="QUOTE_AGE_EXPIRED"


def test_original_date_survives_restart_reenqueue_and_manual_input_revival(tmp_path):
    row=source();record,=query_pending_records(SimpleNamespace(read_rows=lambda _: (row,)),WS)
    store=WorkflowStateStore(tmp_path/'synthetic.sqlite3')
    assert store.enqueue(record,now=NOW,source_order_date="2026-11-01")
    iid=store.inquiry_id_for(record.record_identity)
    store=WorkflowStateStore(store.database_path)
    assert not store.enqueue(record,now=NOW+timedelta(days=3),source_order_date="2026-11-07")
    item=store.get_by_inquiry_id(iid)
    assert item.created_at==NOW and item.source_order_date=="2026-11-01"
    assert store.revive_item(item.id,record,now=NOW+timedelta(days=3),manual_retry=True)
    item=store.get_by_inquiry_id(iid)
    assert item.created_at==NOW and item.source_order_date=="2026-11-01"
    result=admit(item.record_identity,source("2026-11-10"),(),lambda:item.created_at,
        recorded_source_date=item.source_order_date,now=NOW+timedelta(days=6),module="inquiry")
    assert not result.allowed and result.reason=="QUOTE_AGE_EXPIRED"


@pytest.mark.parametrize("status", ["发给采购","采购已报价","已报价给客户"])
def test_quote_date_alone_cannot_admit_untracked_quoted_history(status):
    row=source();row.cells["A"]=status
    from src.sheets.pending import identify_worksheet_row
    identity=identify_worksheet_row(WS,row)
    assert not admit(identity,row,(),lambda:None,now=NOW,module="quotation").allowed


def test_explicit_owner_manual_age_exemption_still_keeps_current_status():
    row=source("2026-01-01");record,=query_pending_records(SimpleNamespace(read_rows=lambda _: (row,)),WS)
    assert admit(record.record_identity,row,(),lambda:None,now=NOW,module="inquiry",manual=True).allowed
    row.cells['A']='已报价给客户'
    assert not admit(record.record_identity,row,(),lambda:None,now=NOW,module="inquiry",manual=True).allowed


def test_revival_of_missing_item_remains_false(tmp_path):
    row=source();record,=query_pending_records(SimpleNamespace(read_rows=lambda _: (row,)),WS)
    store=WorkflowStateStore(tmp_path/"synthetic.sqlite3")
    assert not store.revive_item(999,record,now=NOW,manual_retry=True)
