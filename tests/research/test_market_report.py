"""Report facts retain provenance and Shanghai calendar dates."""
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from src.research.detailed import (
    DetailedOrder,
    TpFx,
    TpOffer,
    TpQuote,
    TpSourceResult,
    finish_tp,
)
from src.research.report import render_market_report
from src.research.source_contracts import PRICE_SOURCES, SourceEvidence, SourceOutcome


def test_local_intake_approximation_uses_shanghai_calendar_day():
    now = datetime(2026, 10, 31, 8, tzinfo=UTC)
    order = DetailedOrder("MPN", quantity=10, rfq_date="2026-10-30T20:30:00+00:00", date_source="本地订单日期（近似）")
    sources = tuple(TpSourceResult(source, SourceOutcome.SUCCESS,
        SourceEvidence(source, "MPN", "MPN", SourceOutcome.SUCCESS, now),
        (TpQuote(TpOffer(source, "MPN", Decimal(2), "RMB", None, True), Decimal(2)),)) for source in PRICE_SOURCES)
    result = finish_tp(order, SimpleNamespace(stock_label="货多"), sources, target_rmb=None, fx=TpFx(None, now))
    text, _ = render_market_report(order, result, target=False)
    assert "本地订单日期（近似）：2026-10-31" in text
    assert "原询价日期" not in text



def test_target_free_report_shows_all_retained_stock_buckets_and_single_quote_reason():
    now=datetime(2026,11,1,8,tzinfo=UTC)
    order=DetailedOrder("TEST123")
    sources=[]
    for index,source in enumerate(PRICE_SOURCES):
        values=[(2,True),(3,True),(1,False),(4,False)] if index==1 else [(9,True)]
        quotes=tuple(TpQuote(TpOffer(source,order.mpn,Decimal(price),"RMB",None,True,stocked),Decimal(price)) for price,stocked in values)
        sources.append(TpSourceResult(source,SourceOutcome.SUCCESS,SourceEvidence(source,order.mpn,order.mpn,SourceOutcome.SUCCESS,now),quotes))
    result=finish_tp(order,SimpleNamespace(stock_label="货多"),tuple(sources),target_rmb=None,fx=TpFx(None,now))
    text,html=render_market_report(order,result,target=False)
    assert "1 RMB" in html and "4 RMB" in html and "报价4" in text
    assert "本次仅取得1条有效报价" in text
    assert "有库存" in text and "无库存" in text
    assert "已保留报价" in html and ">次低</th>" not in html
