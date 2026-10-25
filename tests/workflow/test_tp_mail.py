"""Concise mail facts and HTML use synthetic orders only."""
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.research.source_contracts import (
    PRICE_SOURCES,
    ResearchSource,
    SourceEvidence,
    SourceOutcome,
)
from src.research.tp import TpOffer, TpQuote, TpResearchResult, TpSourceResult
from src.sheets.tp_brief import bind_tp_order
from src.workflow.tp_research import tp_mail
from tests.research.test_tp import NOW
from tests.sheets.test_tp_brief import brief, source


def example():
    order = bind_tp_order(brief(price="2 USD"), "synthetic", [source()])
    when = datetime(2026, 10, 24, 20, 30, tzinfo=UTC)  # Oct25 in the source's China calendar
    first = TpQuote(TpOffer(ResearchSource.BOM_AI, "TEST-ABC", Decimal(2), "USD", when, False), Decimal(14))
    second = TpQuote(TpOffer(ResearchSource.INSO, "TEST-ABC", Decimal(18), "RMB", when, False), Decimal(18))
    current = TpQuote(TpOffer(ResearchSource.FINDCHIPS, "TEST-ABC", Decimal(4), "USD", None, True), Decimal(28))
    pool = {ResearchSource.BOM_AI: (first,), ResearchSource.INSO: (second,), ResearchSource.FINDCHIPS: (current,)}
    sources = tuple(TpSourceResult(s, SourceOutcome.SUCCESS if s in pool else SourceOutcome.SOURCE_UNAVAILABLE,
        SourceEvidence(s, "TEST-ABC", None, SourceOutcome.SUCCESS, NOW), pool.get(s, ())) for s in PRICE_SOURCES)
    return order, TpResearchResult(sources, first, second, "货少", Decimal(14), Decimal(1400), Decimal(7))


@pytest.mark.parametrize("target,opening", [(15, "请人工加急跟进：最低价低于 TP。"),
    (14, "最低价等于 TP。"), (13, "最低价高于 TP。")])
def test_opening_explains_price_comparison_in_rmb(target, opening):
    order, result = example()
    mail = tp_mail(order, replace(result, target_rmb=Decimal(target)), "synthetic:0", NOW)
    assert mail.text_body.startswith(opening + "\n\n")
    assert opening in mail.html_body


def test_dates_only_valid_sites_only_clear_names_and_no_debug_noise():
    order, result = example()
    mail = tp_mail(order, result, "synthetic:0", NOW)
    body = mail.text_body
    assert "正能量：2 USD ≈ 14 RMB · 2026-10-25" in body
    assert "INSO：18 RMB · 2026-10-25" in body
    assert "Findchips：4 USD ≈ 28 RMB · 现价" in body
    assert "\n\n各来源报价\n" in body
    for noise in ("立创", "华强", "IC.net", "无有效报价", "不足两档", "窗口", "来源暂不可用",
                  "报价日期未提供", "价格排名", "T20:", "+00:00", "20:30", "2026-10-24", "RMB /", "bom.ai"):
        assert noise not in body
    assert mail.html_body.count("</tr>") == 4  # header + three valid sources
    assert "<table" in mail.html_body and "<br>" in mail.html_body
    assert '>次低</th>' not in mail.html_body  # all sites only supplied one valid price


def test_second_column_only_appears_when_a_source_has_a_real_second_quote():
    order, result = example()
    second = replace(result.lowest, offer=replace(result.lowest.offer, price=Decimal(3)), rmb=Decimal(21))
    result = replace(result, sources=tuple(replace(s, quotes=s.quotes+(second,))
                     if s.source is ResearchSource.BOM_AI else s for s in result.sources))
    mail = tp_mail(order, result, "synthetic:0", NOW)
    assert '>次低</th>' in mail.html_body
    assert "次低 3 USD ≈ 21 RMB" in mail.text_body


def test_missing_second_is_omitted_and_invalid_site_prices_do_not_leak():
    order, result = example()
    bad = replace(result.lowest, rmb=Decimal("NaN"))
    sources = tuple(replace(s, quotes=(bad,)) if s.source is ResearchSource.HQEW else s for s in result.sources)
    result = replace(result, second=None, sources=sources)
    mail = tp_mail(order, result, "synthetic:0", NOW)
    assert "次低" not in mail.text_body
    assert "华强" not in mail.text_body
    assert "NaN" not in mail.text_body + mail.html_body
    assert "不足" not in mail.text_body


def test_html_escapes_order_values_and_preserves_plain_text_alternative():
    order, result = example()
    order = replace(order, customer="Test <Buyer> & Co", mpn='TEST<img src="x">')
    mail = tp_mail(order, result, "synthetic:0", NOW)
    assert "<Buyer>" in mail.text_body
    assert "<Buyer>" not in mail.html_body and "&lt;Buyer&gt; &amp; Co" in mail.html_body
    assert '<img src="x">' not in mail.html_body and "&lt;img" in mail.html_body
