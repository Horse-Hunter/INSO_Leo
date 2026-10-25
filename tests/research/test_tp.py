import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.research.bom_ai import (
    BomAiCapture,
    BomAiPriceRecord,
    parse_bom_ai_price_records,
)
from src.research.findchips import FindchipsPage
from src.research.fx import UsdRmbQuote
from src.research.hqew import HqewPage
from src.research.inso_history import InsoHistoryCapture, InsoHistoryRecord
from src.research.lcsc import LcscPage, LcscPriceTier, LcscProduct
from src.research.source_contracts import ResearchSource as S
from src.research.source_contracts import calendar_month_cutoff
from src.research.tp import TpFx, TpOffer, collect_tp, distinct_two, select_tp_offers
from tests.research.test_findchips import _page, _row
from tests.research.test_hqew import _row as hqew_row

NOW = datetime(2026, 10, 25, 12, tzinfo=UTC)


class Fx:
    def get_quote(self):
        return UsdRmbQuote(Decimal(7), NOW, "synthetic-ECB")
    def get_hkd_rmb_rate(self):
        return Decimal("0.9")


def offer(price="5", *, when=NOW, current=False, stocked=True, source=S.INSO, currency="RMB"):
    return TpOffer(source, "TEST-ABC", Decimal(price), currency, when, current, stocked)


@pytest.mark.parametrize("months", range(1, 13))
def test_tp_inclusive_calendar_boundary_and_no_future(months):
    cutoff = calendar_month_cutoff(NOW, months)
    result = select_tp_offers(S.INSO, [offer(when=cutoff), offer("7", when=cutoff),
         offer("0.1", when=calendar_month_cutoff(NOW, 12)-timedelta(microseconds=1)),
         offer("0.2", when=NOW+timedelta(microseconds=1))],
         query="TEST-ABC", now=NOW, fx=TpFx(Fx(), NOW))
    assert result.months == months
    assert [q.rmb for q in result.quotes] == [Decimal(5), Decimal(7)]


def test_expand_for_second_distinct_price_not_duplicate_tie():
    result = select_tp_offers(S.INSO, [offer("5"), offer("5"),
        offer("4", when=calendar_month_cutoff(NOW, 8))], query="TEST-ABC", now=NOW, fx=TpFx(Fx(), NOW))
    assert result.months == 8
    assert [q.rmb for q in result.quotes] == [Decimal(4), Decimal(5)]
    single = select_tp_offers(S.INSO, [offer(), offer()], query="TEST-ABC", now=NOW, fx=TpFx(Fx(), NOW))
    assert len(single.quotes) == 1 and single.months == 12
    assert len(distinct_two(single.quotes*2)) == 1


def test_unknown_date_not_replaced_by_capture_and_explicit_current():
    result = select_tp_offers(S.INSO, [offer(when=None), offer(when=NOW.replace(tzinfo=None)),
        offer("6", when=None, current=True)], query="TEST-ABC", now=NOW, fx=TpFx(Fx(), NOW))
    assert len(result.quotes) == 1
    assert result.quotes[0].offer.current and result.quotes[0].offer.quoted_at is None


def test_fx_same_snapshot_currency_and_stale_rejected():
    fx = TpFx(Fx(), NOW)
    assert fx.convert(Decimal(2), "USD") == Decimal(14)
    assert fx.convert(Decimal(2), "RMB") == Decimal(2)
    assert fx.convert(Decimal(2), "HKD") == Decimal("1.8")
    stale = SimpleNamespace(get_quote=lambda: UsdRmbQuote(Decimal(7), NOW-timedelta(days=1), "test"))
    rejected = TpFx(stale, NOW)
    for _ in range(2):
        with pytest.raises(ValueError, match="FX"):
            rejected.convert(Decimal(2), "USD")
    for value in (Decimal(0), Decimal(-1), Decimal("NaN"), Decimal("Infinity")):
        with pytest.raises(ValueError):
            fx.convert(value, "USD")


@pytest.mark.parametrize("source", [S.FINDCHIPS, S.HQEW, S.BOM_AI, S.INSO, S.LCSC])
def test_same_existing_parser_client_two_prices_with_real_dates(source):
    when = calendar_month_cutoff(NOW, 10)
    if source is S.FINDCHIPS:
        html = _page(_row("TEST-ABC", "1", json.dumps([[1,"USD","2"],[10,"USD","3"]]), when.isoformat()))
        client = SimpleNamespace(fetch_first_page=lambda _: FindchipsPage(html, "https://synthetic.invalid", NOW))
    elif source is S.HQEW:
        html = hqew_row("TEST-ABC", "2", when.isoformat()) + hqew_row("TEST-ABC", "3", when.isoformat())
        client = SimpleNamespace(fetch_first_page=lambda _: HqewPage(html, "https://synthetic.invalid", NOW))
    elif source is S.BOM_AI:
        capture = BomAiCapture((BomAiPriceRecord("TEST-ABC", Decimal(2), when),
                                BomAiPriceRecord("TEST-ABC", Decimal(3), when)), "https://synthetic.invalid", NOW)
        client = SimpleNamespace(fetch_price_records=lambda _: capture)
    elif source is S.INSO:
        capture = InsoHistoryCapture((InsoHistoryRecord(Decimal(2), "RMB", when, "TEST-ABC"),
                                     InsoHistoryRecord(Decimal(3), "RMB", when, "TEST-ABC")), "https://synthetic.invalid", NOW)
        client = SimpleNamespace(fetch_history=lambda _: capture)
    else:
        product = LcscProduct("TEST-ABC", False, 100, (LcscPriceTier(1,Decimal(2),"RMB"),
                                                     LcscPriceTier(10,Decimal(3),"RMB")))
        client = SimpleNamespace(fetch_product_page=lambda _: LcscPage("", "https://synthetic.invalid", NOW, product))
    result = collect_tp(SimpleNamespace(_client=client), source, "TEST-ABC", 100, NOW, TpFx(Fx(), NOW))
    assert len(result.quotes) == 2
    assert all(q.offer.quoted_at == (None if source is S.LCSC else when) for q in result.quotes)
    assert result.months == (1 if source is S.LCSC else 10)


def test_bom_current_marker_retained_without_fabricated_date():
    html = '<h3>TEST-ABC</h3><data><quotePrice>2</quotePrice>当前报价</data>'
    records = parse_bom_ai_price_records(html, "TEST-ABC", captured_at=NOW)
    assert records and records[0].is_current
    old = replace(records[0], is_current=False)
    assert old.observed_at == NOW  # V1.4 legacy projection remains compatible.


def test_real_service_six_sources_actual_minimum_not_inso_preference_and_no_excel(tmp_path):
    from src.research import tp
    from src.research.icnet import IcNetResult
    from src.research.service import ResearchService
    from src.research.source_contracts import (
        PriceCandidate,
        SourceEvidence,
        SourceOutcome,
        SourceResult,
    )
    from src.research.tp import TpOffer
    from src.sheets.tp_brief import bind_tp_order
    from tests.sheets.test_tp_brief import brief, source
    native = SourceResult(S.IC_NET, SourceOutcome.SUCCESS,
        SourceEvidence(S.IC_NET, "TEST-ABC", "TEST-ABC", SourceOutcome.SUCCESS, NOW),
        PriceCandidate(S.IC_NET, "TEST-ABC", Decimal(1), "RMB", Decimal(1), NOW))
    service = ResearchService(icnet=SimpleNamespace(search=lambda *args: IcNetResult(native, None, "货多")),
        findchips=object(), hqew=object(), lcsc=object(), bom_ai=object(), inso=object(),
        output=SimpleNamespace(write=lambda *args: pytest.fail("TP must not write ordinary Excel")), fx_provider=Fx())
    calls = []
    original = tp.collect_tp
    def collect(adapter, site, mpn, quantity, now, fx):
        calls.append(site)
        return select_tp_offers(site, [TpOffer(site, mpn, Decimal("1.1") if site is S.INSO else Decimal(2),
            "RMB", NOW, False)], query=mpn, now=now, fx=fx)
    tp.collect_tp = collect
    try:
        result = service.execute_tp("tp_synthetic", bind_tp_order(brief(), "synthetic", [source()]), now=NOW)
    finally:
        tp.collect_tp = original
    assert len(calls) == 5 and len(result.sources) == 6
    assert result.lowest.offer.source is S.IC_NET and result.lowest.rmb == Decimal(1)
    assert result.second.offer.source is S.INSO and result.second.rmb == Decimal("1.1")
    assert result.lowest.offer.quoted_at is None and result.stock_label == "货多"
    assert result.estimated_total == Decimal(100)


def test_calendar_leap_day_clamp_invalid_prices_and_mismatch():
    leap = NOW.replace(year=2024, month=2, day=29)
    assert calendar_month_cutoff(leap, 12).day == 28
    result = select_tp_offers(S.INSO, [offer("0"), offer("-1"), offer("NaN"),
                                     offer("Infinity")], query="TEST-ABC", now=NOW, fx=TpFx(Fx(), NOW))
    assert not result.quotes
    mismatch = select_tp_offers(S.INSO, [offer()], query="DIFFERENT", now=NOW, fx=TpFx(Fx(), NOW))
    assert mismatch.outcome.value == "NO_STRICT_MPN_MATCH"


@pytest.mark.parametrize("unavailable", [False, True])
def test_global_stock_fallback_requires_no_technical_uncertainty(monkeypatch, unavailable):
    from src.research import tp
    from src.research.icnet import IcNetResult
    from src.research.service import ResearchService
    from src.research.source_contracts import (
        PRICE_SOURCES,
        SourceEvidence,
        SourceOutcome,
        SourceResult,
    )
    from src.sheets.tp_brief import bind_tp_order
    from tests.sheets.test_tp_brief import brief, source
    ic = SourceResult(S.IC_NET, SourceOutcome.NO_VALID_PRICE,
        SourceEvidence(S.IC_NET, "TEST-ABC", None, SourceOutcome.NO_VALID_PRICE, NOW))
    def collect(adapter, site, mpn, quantity, now, fx):
        result = select_tp_offers(site, [offer(source=site, stocked=False)],
                                  query=mpn, now=now, fx=fx)
        if unavailable and site is S.HQEW:
            return replace(result, outcome=SourceOutcome.SOURCE_UNAVAILABLE, quotes=())
        return result
    monkeypatch.setattr(tp, "collect_tp", collect)
    service = ResearchService(icnet=SimpleNamespace(search=lambda *a: IcNetResult(ic)),
        findchips=object(), hqew=object(), lcsc=object(), bom_ai=object(), inso=object(),
        output=None, fx_provider=Fx())
    result = service.execute_tp("tp_synthetic", bind_tp_order(brief(), "synthetic", [source()]), now=NOW)
    assert len(result.sources) == len(PRICE_SOURCES)
    assert result.fallback is not unavailable
    assert (result.lowest is None) is unavailable
    monkeypatch.setattr(tp, "collect_tp", lambda adapter, site, mpn, quantity, now, fx:
        select_tp_offers(site, [], query=mpn, now=now, fx=fx))
    empty = service.execute_tp("tp_synthetic", bind_tp_order(brief(), "synthetic", [source()]), now=NOW)
    assert empty.lowest is None and not empty.fallback
