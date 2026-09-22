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
from src.research.source_contracts import SourceOutcome

NOW = datetime(2026, 9, 22, tzinfo=UTC)


def _html(
    mpn: str = "ABC-1", *, preorder: bool = True, stock: int = 0, minimum: int = 1
) -> str:
    data = {
        "props": {
            "pageProps": {
                "webData": {
                    "productModel": mpn,
                    "currencyType": "USD",
                    "isPreSale": preorder,
                    "stockNumber": stock,
                    "productPriceList": [
                        {"ladder": minimum, "productPrice": "2.00"},
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
        return LcscPage(self.html, "https://www.lcsc.com/product-detail/C1.html", NOW)


class Fx:
    def get_quote(self) -> UsdRmbQuote:
        return UsdRmbQuote(Decimal("7.00"), NOW, "synthetic-test-only")


def test_quantity_tier_and_preorder_zero_stock_remain_price_eligible() -> None:
    product = parse_lcsc_product(_html())
    assert product.is_preorder is True and product.stock_quantity == 0
    assert select_lcsc_tier(product.tiers, 50).unit_price == Decimal("1.50")  # type: ignore[union-attr]
    result = LcscAdapter(Client(_html()), Fx()).search("ABC-1", 50)
    assert result.outcome is SourceOutcome.SUCCESS
    assert result.price_candidate is not None
    assert result.price_candidate.normalized_rmb_price == Decimal("10.5000")


def test_strict_mpn_and_no_applicable_tier() -> None:
    mismatch = LcscAdapter(Client(_html("ABC-1-T")), Fx()).search("ABC-1", 50)
    no_tier = LcscAdapter(Client(_html(minimum=100)), Fx()).search("ABC-1", 5)
    assert mismatch.outcome is SourceOutcome.NO_STRICT_MPN_MATCH
    assert no_tier.outcome is SourceOutcome.NO_VALID_PRICE
