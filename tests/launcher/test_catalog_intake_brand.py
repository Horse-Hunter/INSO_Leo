"""Production-shaped original UNKNOWN/resolved brand, no live data or external I/O."""
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace

import pytest

from src.launcher.backend import ProductionBackend
from src.sheets.pending import query_pending_records
from tests.workflow.test_v12_flow import NOW, SHEET, FakeSheetsReader, _make_flow


@pytest.mark.parametrize("status",["NOT_CONFIGURED","FAILED","CONFLICT",None])
def test_unwritten_resolved_brand_does_not_erase_bound_intake_date(tmp_path,status):
    _,queue,*_=_make_flow(tmp_path)
    reader=FakeSheetsReader(brand="UNKNOWN",quantity=300)
    record,=query_pending_records(reader,SHEET)
    queue.enqueue(record,now=NOW-timedelta(days=20))
    item=replace(queue.all_items()[0],resolved_brand="TI",brand_update_status=status)
    backend=ProductionBackend(root=tmp_path)
    backend._mail_brief=SimpleNamespace(cached_lines=lambda _:())
    backend._research_catalog.configure_sources((SHEET,))
    backend._catalog_source(SHEET,(reader.row,),(item,),observed_at=NOW)
    order=backend._research_catalog.match(record.model,now=NOW)
    assert order is not None and order.quantity==300 and order.customer=="Synthetic Customer"
    assert order.date_source=="本地订单日期（近似）" and order.rfq_date.startswith("2026-09-06")
    assert queue.get_by_inquiry_id(item.inquiry_id).created_at==item.created_at
    backend.shutdown()


@pytest.mark.parametrize("change",["brand","model","quantity","row","duplicate","no_intake"])
def test_intake_approximation_never_crosses_unverified_identity_or_ambiguous_binding(tmp_path,change):
    from src.sheets import WorksheetRow
    _,queue,*_=_make_flow(tmp_path)
    reader=FakeSheetsReader(brand="UNKNOWN",quantity=300)
    record,=query_pending_records(reader,SHEET)
    queue.enqueue(record,now=NOW-timedelta(days=20))
    item=replace(queue.all_items()[0],resolved_brand="TI",brand_update_status="NOT_CONFIGURED")
    items=(item,)
    cells=dict(reader.row.cells);rowpos=reader.row.row_position
    if change=="brand":cells["F"]="OTHER"
    if change=="model":cells["E"]="OTHER-MODEL"
    if change=="quantity":cells["G"]=301
    if change=="row":rowpos+=1
    if change=="duplicate":items=(item,replace(item,id=item.id+1,inquiry_id="other-synthetic"))
    if change=="no_intake":items=(replace(item,created_at=None),)
    backend=ProductionBackend(root=tmp_path)
    backend._research_catalog.configure_sources((SHEET,))
    backend._catalog_source(SHEET,(WorksheetRow(rowpos,cells),),items,observed_at=NOW,brief_lines=())
    assert backend._research_catalog.match(cells["E"],now=NOW) is None
    backend.shutdown()


def test_confirmed_brand_write_uses_verified_updated_brand(tmp_path):
    from src.sheets import WorksheetRow
    _,queue,*_=_make_flow(tmp_path)
    reader=FakeSheetsReader(brand="UNKNOWN",quantity=300)
    record,=query_pending_records(reader,SHEET)
    queue.enqueue(record,now=NOW-timedelta(days=20))
    item=replace(queue.all_items()[0],resolved_brand="TI",brand_update_status="UPDATED")
    backend=ProductionBackend(root=tmp_path);backend._research_catalog.configure_sources((SHEET,))
    backend._catalog_source(SHEET,(WorksheetRow(reader.row.row_position,{**reader.row.cells,"F":"TI"}),),(item,),observed_at=NOW,brief_lines=())
    order=backend._research_catalog.match(record.model,now=NOW)
    assert order is not None and order.brand=="TI" and order.quantity==300
    backend.shutdown()


@pytest.mark.parametrize("rfq_date,conflict,allowed",[("",False,True),("invalid",False,False),("2026-09-07",False,True),("",True,False)])
def test_blank_optional_date_uses_only_exact_immutable_intake_not_invalid_or_conflicting_date(tmp_path,rfq_date,conflict,allowed):
    from src.sheets.tp_brief import BRIEF_HEADERS, BriefLine
    _,queue,*_=_make_flow(tmp_path);reader=FakeSheetsReader(brand="UNKNOWN",quantity=300)
    record,=query_pending_records(reader,SHEET);queue.enqueue(record,now=NOW-timedelta(days=20))
    item=replace(queue.all_items()[0],resolved_brand="TI",brand_update_status="NOT_CONFIGURED")
    values={"sheet":"2026","sheet_row":str(record.row_position),"mpn":record.model,"mfr":"UNKNOWN","qty":"301" if conflict else "300","rfq_date":rfq_date}
    line=BriefLine(2,tuple(values.get(k,"") for k in BRIEF_HEADERS))
    backend=ProductionBackend(root=tmp_path);backend._research_catalog.configure_sources((SHEET,))
    backend._catalog_source(SHEET,(reader.row,),(item,),observed_at=NOW,brief_lines=(line,))
    order=backend._research_catalog.match(record.model,now=NOW)
    assert (order is not None)==allowed
    if order and not rfq_date:assert order.date_source=="本地订单日期（近似）"
    if order and rfq_date:assert order.date_source is None and order.rfq_date==rfq_date
    backend.shutdown()
