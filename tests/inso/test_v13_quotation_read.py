from contextlib import nullcontext
from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from src.inso.duplicate_history import (
    InsoDuplicateHistoryError,
    PlaywrightProcurementHistoryPage,
)
from src.inso.quotation_read import (
    QUOTATION_COLUMNS,
    InsoQuotationReader,
    V13QuotationRow,
    capture_quotation_page,
    select_recent_lowest,
)
from tests.inso.test_procurement_duplicate_history import LowerFrame, row

NOW = datetime(2026, 10, 7, 0, 5, tzinfo=ZoneInfo("Asia/Shanghai"))


def quote(at=NOW, model="MPN", **kwargs):
    payload = (at.strftime("%Y-%m-%d %H:%M:%S"), model, "different brand", "", "RMB", "",
               "0001.2300", "0001.2300", "0000", "", "", "  原样\n备注  ", "备注2\t", "")
    return V13QuotationRow(at, kwargs.get("payload", payload))


@pytest.mark.parametrize("age,accepted", [
    (timedelta(hours=71, minutes=59), True), (timedelta(hours=72), True),
    (timedelta(hours=72, microseconds=1), False), (timedelta(microseconds=-1), False),
])
def test_inclusive_72h_boundaries_and_future(age, accepted):
    record = quote(NOW-age)
    assert (select_recent_lowest([record], queried_mpn="MPN", now=NOW) is record) is accepted


@pytest.mark.parametrize("now", [
    datetime(2026, 10, 7, 0, 5, tzinfo=ZoneInfo("Asia/Shanghai")),
    datetime(2026, 10, 1, 0, 5, tzinfo=ZoneInfo("Asia/Shanghai")),
    datetime(2027, 1, 1, 0, 5, tzinfo=ZoneInfo("Asia/Shanghai")),
])
def test_midnight_month_and_year_transitions(now):
    accepted, old = quote(now-timedelta(hours=72)), quote(now-timedelta(hours=72, seconds=1))
    assert select_recent_lowest([old, accepted], queried_mpn="MPN", now=now) is accepted


def test_empty_one_multiple_unsorted_old_and_exact_normalization():
    latest = quote(NOW-timedelta(minutes=1), model=" ｍｐｎ ")
    older = quote(NOW-timedelta(hours=2))
    stale = quote(NOW-timedelta(hours=73))
    fuzzy = quote(NOW, model="XMPN suffix")
    assert select_recent_lowest([], queried_mpn="MPN", now=NOW) is None
    assert select_recent_lowest([older], queried_mpn="MPN", now=NOW) is older
    assert select_recent_lowest([older, latest, stale, fuzzy], queried_mpn="MPN", now=NOW) is latest


def test_aware_clocks_only_and_same_instant_other_zone():
    with pytest.raises(ValueError):
        select_recent_lowest([], queried_mpn="MPN", now=NOW.replace(tzinfo=None))
    with pytest.raises(ValueError):
        quote(NOW.replace(tzinfo=None))
    record = quote(NOW.astimezone(ZoneInfo("UTC")))
    assert select_recent_lowest([record], queried_mpn="MPN", now=NOW) is record


class DisplayFrame(LowerFrame):
    def __init__(self, pages, displays, total):
        super().__init__(pages, total)
        self.displays = displays

    def evaluate(self, expression, arg=None):
        if arg is None:
            return super().evaluate(expression)
        assert arg["columns"] == list(QUOTATION_COLUMNS)
        assert arg["ids"] == [r["id"] for r in self.pages[self.number-1]]
        return self.displays[self.number-1]


def access(frame):
    return SimpleNamespace(operation_page=lambda: nullcontext(SimpleNamespace(shell_frame=frame)))


def test_real_native_pagination_then_raw_reader_latest_across_all_pages():
    old, latest = quote(NOW-timedelta(hours=2)), quote(NOW-timedelta(minutes=1))
    frame = DisplayFrame([[row(1), row(2)], [row(3)]],
                         [[list(old.payload), list(old.payload)], [list(latest.payload)]], 3)
    records = InsoQuotationReader().read(access(frame), " mpn ")
    assert len(records) == 3
    selected = select_recent_lowest(records, queried_mpn="MPN", now=NOW)
    assert selected.payload == latest.payload
    assert frame.number == 2
    assert frame.value == " mpn "
    assert len(selected.payload) == 14
    assert selected.payload[3] == ""
    assert selected.payload[6] == "0001.2300"
    assert selected.payload[11] == "  原样\n备注  "
    assert selected.payload[13] == ""
    assert selected.quote_record_time == latest.quote_record_time
    assert all("Save" not in selector for _, selector in frame.calls)


def test_every_empty_business_cell_is_allowed_and_preserved():
    raw = ("2026/10/07 00:04", "MPN") + ("",)*12
    frame = DisplayFrame([[row(1, quantity="bad")]], [[list(raw)]], 1)
    records = InsoQuotationReader().read(access(frame), "MPN")
    assert records[0].payload == raw
    assert records[0].quote_record_time == NOW-timedelta(minutes=1)


@pytest.mark.parametrize("display", [None, [], [["missing"]], [[None]*14]])
def test_missing_structure_is_query_failure_not_empty(display):
    frame = DisplayFrame([[row(1)]], [display], 1)
    with pytest.raises(InsoDuplicateHistoryError):
        InsoQuotationReader().read(access(frame), "MPN")


def test_native_failure_does_not_return_empty_and_fuzzy_result_does_not_compete():
    frame = DisplayFrame([[row(1)]], [[list(quote().payload)]], 3)
    with pytest.raises(InsoDuplicateHistoryError):
        InsoQuotationReader().read(access(frame), "MPN")
    fuzzy = row(1)
    fuzzy["PartNo"] = "XMPN suffix"
    frame = DisplayFrame([[fuzzy]], [[list(quote(model="XMPN suffix").payload)]], 1)
    assert InsoQuotationReader().read(access(frame), "MPN") == ()


def test_invalid_exact_date_is_failure_not_no_recent_quote():
    raw = ("date unavailable", "MPN") + ("",)*12
    frame = DisplayFrame([[row(1)]], [[list(raw)]], 1)
    with pytest.raises(InsoDuplicateHistoryError):
        InsoQuotationReader().read(access(frame), "MPN")


def test_native_empty_query_is_successfully_captured():
    frame = DisplayFrame([[]], [[]], 0)
    assert InsoQuotationReader().read(access(frame), "MPN") == ()


def test_same_timestamp_selects_one_latest_without_content_tiebreaking():
    first, second = quote(), quote(model="mpn")
    assert select_recent_lowest([first, second], queried_mpn="MPN", now=NOW) is first


def test_raw_capture_rejects_wrong_model_and_preserves_headers_contract():
    class Frame:
        def evaluate(self, expression, arg):
            assert "data-field" in expression
            assert "labels[start + i]" in expression
            assert "textContent" in expression
            return [list(quote(model="different").payload)]
    with pytest.raises(InsoDuplicateHistoryError):
        capture_quotation_page(Frame(), [row(1)])


def test_capture_hook_does_not_change_default_v12_native_payload():
    frame = LowerFrame([[row(1)]], total=1)
    assert PlaywrightProcurementHistoryPage(frame).query_exact_response("MPN") == {"rows": [row(1)]}


@pytest.mark.parametrize("tax_display", ["", "0", "13.0000", " 13\n "])
def test_owner_verified_live_tax_header_in_sixth_position_preserves_raw_text(tax_display):
    # Independent observed lower-history header fixture, 2026-10-07.
    actual_headers = ("日期", "型号", "品牌", "数量", "币种", "供方税点", "报价", "供方未税价",
                      "平台数量", "批号", "货期", "备注", "备注2", "制单人")
    raw = list(quote().payload)
    raw[5] = tax_display
    class LiveHeaderFixture:
        def evaluate(self, expression, arg):
            return [raw] if tuple(arg["columns"]) == actual_headers else None
    captured = capture_quotation_page(LiveHeaderFixture(), [row(1)])
    assert captured[0]["quotation_display"] == tuple(raw)
    assert captured[0]["quotation_display"][5] == tax_display


def priced(at, price, currency="RMB"):
    from dataclasses import replace
    record = quote(at)
    payload = list(record.payload)
    payload[4], payload[7] = currency, price
    return replace(record, payload=tuple(payload))


def test_lowest_price_beats_latest_and_preserves_exact_payload():
    older = priced(NOW-timedelta(hours=70), "0001.2000")
    newest = priced(NOW-timedelta(minutes=1), "9.000")
    stale = priced(NOW-timedelta(hours=73), "0")
    future = priced(NOW+timedelta(seconds=1), "0")
    selected = select_recent_lowest([newest, stale, future, older], queried_mpn="MPN", now=NOW)
    assert selected is older and selected.payload[7] == "0001.2000"


def test_currency_conversion_ranks_rmb_not_raw_numbers_and_calls_each_rate_once():
    from decimal import Decimal
    usd = priced(NOW, "1", "USD")
    rmb = priced(NOW-timedelta(hours=1), "6.0000", "人民币")
    hkd = priced(NOW-timedelta(hours=2), "5.00", "HKD")
    calls = []
    def rate(currency):
        calls.append(currency)
        return {"USD": Decimal(7), "HKD": Decimal("0.9")}[currency]
    selected = select_recent_lowest([usd, usd, rmb, hkd], queried_mpn="MPN", now=NOW, currency_rate=rate)
    assert selected is hkd and selected.payload[4] == "HKD" and selected.payload[7] == "5.00"
    assert calls == ["USD", "HKD"]


@pytest.mark.parametrize("price", ["", "unknown", "NaN", "Infinity", "-1"])
def test_unusable_prices_do_not_win_or_change_captured_payload(price):
    bad = priced(NOW, price)
    valid = priced(NOW-timedelta(hours=1), "2")
    assert select_recent_lowest([bad, valid], queried_mpn="MPN", now=NOW) is valid
    assert select_recent_lowest([bad], queried_mpn="MPN", now=NOW) is None


def test_equal_price_chooses_newer_but_equal_time_retains_first():
    first = priced(NOW, "1.00")
    same = priced(NOW, "1")
    older = priced(NOW-timedelta(hours=1), "1.000")
    assert select_recent_lowest([older, first, same], queried_mpn="MPN", now=NOW) is first


def test_unknown_currency_and_unavailable_fx_fail_closed():
    from src.inso.quotation_read import QuotationPriceUnavailable
    with pytest.raises(QuotationPriceUnavailable, match="QUOTE_CURRENCY_UNSUPPORTED"):
        select_recent_lowest([priced(NOW, "1", "UNKNOWN")], queried_mpn="MPN", now=NOW)
    with pytest.raises(QuotationPriceUnavailable, match="QUOTE_FX_REQUIRED"):
        select_recent_lowest([priced(NOW, "1", "USD")], queried_mpn="MPN", now=NOW)


def test_supplier_net_price_is_used_even_when_quote_column_would_choose_opposite():
    from dataclasses import replace
    lower_net = priced(NOW-timedelta(hours=1), "2.0000")
    lower_quote = priced(NOW, "8.00")
    a, b = list(lower_net.payload), list(lower_quote.payload)
    a[6], b[6] = "100", "0"
    lower_net, lower_quote = replace(lower_net, payload=tuple(a)), replace(lower_quote, payload=tuple(b))
    chosen = select_recent_lowest([lower_quote, lower_net], queried_mpn="MPN", now=NOW)
    assert chosen is lower_net and chosen.payload[6:8] == ("100", "2.0000")


def test_positive_net_price_preferred_to_zero_and_zero_only_falls_back_unchanged():
    zero = priced(NOW, "000.0000")
    positive = priced(NOW-timedelta(hours=1), "2.0000")
    assert select_recent_lowest([zero, positive], queried_mpn="MPN", now=NOW) is positive
    older_zero = priced(NOW-timedelta(hours=2), "-0")
    selected = select_recent_lowest([older_zero, zero], queried_mpn="MPN", now=NOW)
    assert selected is zero and selected.payload[7] == "000.0000"


def test_zero_fallback_ignores_stale_fuzzy_and_future_rows_and_needs_no_fx():
    zero = priced(NOW, "0", "USD")
    stale = priced(NOW-timedelta(hours=73), "0")
    future = priced(NOW+timedelta(seconds=1), "0")
    assert select_recent_lowest([stale, future], queried_mpn="MPN", now=NOW) is None
    assert select_recent_lowest([zero], queried_mpn="MPN", now=NOW) is zero


def test_owner_suffix_reader_and_lowest_price_across_pages_preserve_raw14():
    from dataclasses import replace
    original = quote(model="WGI210IT S LJXS")
    cheap = list(original.payload)
    cheap[7] = "0000.7500"
    suffixed = replace(original, payload=tuple(cheap))
    other = quote(model="WGI211IT")
    first, second, third = row(1), row(2), row(3)
    first["PartNo"], second["PartNo"], third["PartNo"] = "WGI210IT", original.payload[1], other.payload[1]
    exact = quote(model="WGI210IT")
    frame = DisplayFrame([[first, second], [third]],
                         [[list(exact.payload), list(suffixed.payload)], [list(other.payload)]], 3)
    records = InsoQuotationReader().read(access(frame), "WGI210IT")
    assert frame.value == "WGI210IT"
    assert len(records) == 2
    selected = select_recent_lowest(records, queried_mpn="WGI210IT", now=NOW)
    assert selected.payload == suffixed.payload
    assert selected.payload[1] == "WGI210IT S LJXS"
    assert selected.payload[7] == "0000.7500"


def test_separated_model_no_stock_quote_is_retrieved_and_selected_without_fx():
    original = quote(model="RM342-059-581-7200")
    values = list(original.payload)
    values[4], values[7], values[11] = "USD", "0", "无货"
    matched, other = row(1), row(2)
    matched["PartNo"], other["PartNo"] = original.payload[1], "RM342-999-581-7200"
    other_quote = quote(model=other["PartNo"])
    frame = DisplayFrame([[matched, other]], [[values, list(other_quote.payload)]], 2)
    records = InsoQuotationReader().read(access(frame), original.payload[1])
    assert frame.value == "RM342-059-581-7200"
    assert len(records) == 1
    selected = select_recent_lowest(records, queried_mpn=original.payload[1], now=NOW,
        currency_rate=lambda _: pytest.fail("zero quote must not fetch FX"))
    assert selected.payload == tuple(values)
