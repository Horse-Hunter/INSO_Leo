"""Synthetic Brief/source identity contracts. No live business data."""
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.sheets.pending import WorksheetRow
from src.sheets.tp_brief import (
    BRIEF_HEADERS,
    BriefLine,
    BriefReader,
    bind_tp_order,
    parse_target_price,
    quantity_value,
)


def brief(*, sheet="2026", row="10", brand="", price="2 USD", mpn="TEST-ABC", qty="100"):
    values = {"rfq_line_id": "synthetic-line", "sheet": sheet, "sheet_row": row,
              "mpn": mpn, "mfr": brand, "qty": qty, "target_price": price,
              "rfq_date": "2026-10-20"}
    return BriefLine(2, tuple(values.get(h, "") for h in BRIEF_HEADERS))


def source(*, sheet="2026", position=10, brand="", mpn="TEST-ABC", qty=100):
    return WorksheetRow(position, {"A": "未发", "C": "A", "D": "TEST-CUSTOMER",
                                  "E": mpn, "F": brand, "G": qty} if sheet == "2026" else
                        {"A": "2026/10/20", "B": "已报价给客户", "D": mpn,
                         "E": brand, "F": qty})


@pytest.mark.parametrize("value,expected", [("1.25 USD", (Decimal("1.25"), "USD")),
    ("USD 1.25", (Decimal("1.25"), "USD")), ("2 RMB", (Decimal(2), "RMB")),
    ("￥1,200.50", (Decimal("1200.50"), "RMB")), ("", None)])
def test_price_explicit_currency(value, expected):
    assert parse_target_price(value) == expected


@pytest.mark.parametrize("value", ["0 USD", "-1 RMB", "NaN USD", "1", "1 EUR", "=1 USD", "1,00 USD"])
def test_invalid_target(value):
    with pytest.raises(ValueError):
        parse_target_price(value)


@pytest.mark.parametrize("value", [None, True, "", "1k", "-1", "0", "1.5", "1,00"])
def test_invalid_quantity(value):
    with pytest.raises((ValueError, TypeError)):
        quantity_value(value)


def test_four_tp_synthetic_states_no_legacy_inquiry_required():
    # Four TP aliases, missing/known brand and old/no-old-ledger scenarios.
    # Legacy inquiry availability is deliberately not an input to binding.
    for i, (brand, price) in enumerate((("", "1 USD"), ("", "2 RMB"),
                                      ("TEST-MFR", "3 USD"), ("TEST-MFR", "4 USD")), 10):
        line = brief(row=str(i), brand=brand, price=price)
        order = bind_tp_order(line, "synthetic", [source(position=i, brand=brand)])
        assert order.row == i and order.customer == "TEST-CUSTOMER"
    with pytest.raises(ValueError, match="BRAND_CONFLICT"):
        bind_tp_order(brief(brand="TEST-MFR"), "synthetic", [source(brand="DIFFERENT")])
    with pytest.raises(ValueError, match="AMBIGUOUS"):
        bind_tp_order(brief(), "synthetic", [source(), source()])


def test_duplicate_business_keys_resolve_only_explicit_correlated_anchor():
    rows = [source(position=10), source(position=12)]
    assert bind_tp_order(brief(row="12"), "synthetic", rows).row == 12
    with pytest.raises(ValueError, match="UNMATCHED"):
        bind_tp_order(brief(row="11"), "synthetic", rows)
    with pytest.raises(ValueError, match="MODEL_CONFLICT"):
        bind_tp_order(brief(), "synthetic", [source(mpn="TEST-OTHER")])
    with pytest.raises(ValueError, match="QUANTITY_CONFLICT"):
        bind_tp_order(brief(), "synthetic", [source(qty=101)])


def test_shahab_date_and_status_change():
    line = brief(sheet="SHAHAB")
    row = source(sheet="SHAHAB")
    assert bind_tp_order(line, "synthetic", [row]).customer == "SHAHAB"
    assert bind_tp_order(line, "synthetic", [replace(row, cells={**row.cells, "B": "成交"})])
    with pytest.raises(ValueError, match="DATE_CONFLICT"):
        bind_tp_order(line, "synthetic", [replace(row, cells={**row.cells, "A": "2026/10/19"})])


def test_exact_header_and_rows_preserved():
    line = brief()
    service = SimpleNamespace(read_brief=lambda _: {"values": [BRIEF_HEADERS, [], line.values]})
    assert BriefReader(service).read("synthetic")[0].brief_row == 3
    service.read_brief = lambda _: {"values": [list(reversed(BRIEF_HEADERS))]}
    with pytest.raises(ValueError, match="SCHEMA"):
        BriefReader(service).read("synthetic")


@pytest.mark.parametrize("response", [None, {"values": None}, {"values": [None]},
                                    {"values": [BRIEF_HEADERS, None]},
                                    {"values": [BRIEF_HEADERS, [123]]}])
def test_malformed_brief_response_is_explicitly_tp_local(response):
    from src.sheets.tp_brief import TpLocalError
    with pytest.raises(TpLocalError, match="TP_BRIEF_SCHEMA_UNAVAILABLE"):
        BriefReader(SimpleNamespace(read_brief=lambda _: response)).read("synthetic")
