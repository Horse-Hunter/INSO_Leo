import json
from datetime import UTC, datetime
from decimal import Decimal

from src.research.fx import UsdRmbQuote
from src.research.lcsc import (
    LcscAdapter,
    LcscPage,
    parse_lcsc_product,
    select_lcsc_tier,
)
from src.research.source_contracts import SourceOutcome, format_source_result

NOW = datetime(2026, 9, 22, tzinfo=UTC)


def _html(
    mpn: str = "ABC-1",
    *,
    preorder: bool = True,
    stock: int = 0,
    currency: str = "USD",
    quote_date: str | None = None,
) -> str:
    data = {
        "props": {
            "pageProps": {
                "webData": {
                    "productModel": mpn,
                    "currencyType": currency,
                    "isPreSale": preorder,
                    "stockNumber": stock,
                    "quoteDate": quote_date,
                    "productPriceList": [
                        {"ladder": 1, "productPrice": "2.00"},
                        {"ladder": 10, "productPrice": "1.50"},
                        {"ladder": 100, "productPrice": "1.00"},
                    ],
                }
            }
        }
    }
    return '<script id="__NEXT_DATA__">' + json.dumps(data) + "</script>"


class Client:
    def __init__(self, html: str) -> None:
        self.html = html

    def fetch_product_page(self, mpn: str) -> LcscPage:
        return LcscPage(
            self.html, "https://www.lcsc.com/product-detail/C1.html", NOW
        )


class Fx:
    def get_quote(self) -> UsdRmbQuote:
        return UsdRmbQuote(Decimal("7.00"), NOW, "synthetic-test-only")


def test_quantity_does_not_select_tier_and_preorder_is_out_of_stock() -> None:
    product = parse_lcsc_product(_html())
    assert select_lcsc_tier(product.tiers, 1).unit_price == Decimal("1.00")  # type: ignore[union-attr]
    assert select_lcsc_tier(product.tiers, 10_000).unit_price == Decimal("1.00")  # type: ignore[union-attr]

    result = LcscAdapter(Client(_html()), Fx()).search("ABC-1", 1)

    assert result.outcome is SourceOutcome.SUCCESS
    assert result.price_candidate is None
    assert result.out_of_stock_candidate is not None
    assert result.out_of_stock_candidate.normalized_rmb_price == Decimal("7.0000")
    assert format_source_result(result) == "7.0000（无库存）"


def test_stocked_suffix_and_rmb_prices_are_supported() -> None:
    suffix = LcscAdapter(
        Client(_html("ABC-1-T", preorder=False, stock=5)), Fx()
    ).search("ABC-1", 50)
    rmb = LcscAdapter(
        Client(_html(currency="CNY", preorder=False, stock=5)), Fx()
    ).search("ABC-1", 50)

    assert suffix.price_candidate is not None
    assert suffix.price_candidate.normalized_rmb_price == Decimal("7.0000")
    assert format_source_result(suffix) == "7.0000（ABC-1-T）"
    assert rmb.price_candidate is not None
    assert rmb.price_candidate.normalized_rmb_price == Decimal("1.00")


def test_overlong_suffix_and_unsupported_currency_have_no_candidate() -> None:
    mismatch = LcscAdapter(Client(_html("ABC-1ABCDEF")), Fx()).search("ABC-1", 1)
    unsupported = LcscAdapter(Client(_html(currency="EUR")), Fx()).search(
        "ABC-1", 1
    )
    assert mismatch.outcome is SourceOutcome.NO_STRICT_MPN_MATCH
    assert unsupported.outcome is SourceOutcome.NO_VALID_PRICE


def test_present_date_is_filtered_by_natural_month() -> None:
    result = LcscAdapter(
        Client(
            _html(
                preorder=False,
                stock=5,
                quote_date="2026-08-21 23:59:59",
            )
        ),
        Fx(),
        clock=lambda: NOW,
    ).search("ABC-1", 1)
    assert result.outcome is SourceOutcome.NO_VALID_PRICE
