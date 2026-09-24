import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Self

from src.research.fx import UsdRmbQuote
from src.research.lcsc import (
    LcscAdapter,
    LcscBrowserClient,
    LcscPage,
    parse_lcsc_product,
    parse_lcsc_search_product,
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
    assert format_source_result(result) == "7（无库存）"


def test_stocked_suffix_and_rmb_prices_are_supported() -> None:
    suffix = LcscAdapter(
        Client(_html("ABC-1-T", preorder=False, stock=5)), Fx()
    ).search("ABC-1", 50)
    rmb = LcscAdapter(
        Client(_html(currency="CNY", preorder=False, stock=5)), Fx()
    ).search("ABC-1", 50)

    assert suffix.price_candidate is not None
    assert suffix.price_candidate.normalized_rmb_price == Decimal("7.0000")
    assert format_source_result(suffix) == "7（ABC-1-T）"
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


def _next(payload: dict[str, object]) -> str:
    return '<script id="__NEXT_DATA__">' + json.dumps(payload) + "</script>"


def _cn_search_html() -> str:
    records = [
        {
            "productVO": {
                "productId": "99",
                "productModel": "UNRELATED",
                "stockNumber": 999,
                "productPriceList": [
                    {"startPurchasedNumber": 1, "productPrice": "0.01"}
                ],
            }
        },
        {
            "productVO": {
                "productId": "531509",
                "productModel": "ADXL355BEZ-RL7",
                "stockNumber": 1102,
                "productPriceList": [
                    {"startPurchasedNumber": 1, "productPrice": "366.02"},
                    {"startPurchasedNumber": 30, "productPrice": "350.12"},
                ],
            },
            "priceDiscount": {
                "priceList": [
                    {"spNumber": 1, "price": "366.02"},
                    {"spNumber": 30, "price": "343.1176"},
                ]
            },
        },
    ]
    return _next(
        {
            "props": {
                "pageProps": {
                    "soData": {"searchResult": {"productRecordList": records}}
                }
            }
        }
    )


def _cn_product_html() -> str:
    return _next(
        {
            "props": {
                "pageProps": {
                    "webData": {
                        "productRecord": {
                            "productId": "531509",
                            "productModel": "ADXL355BEZ-RL7",
                            "stockNumber": 1102,
                        }
                    },
                    "price": "350.12",
                }
            }
        }
    )


def test_chinese_search_parser_is_scoped_and_uses_displayed_discount_tiers() -> None:
    product, product_id = parse_lcsc_search_product(
        _cn_search_html(), "ADXL355BEZ-RL7"
    )

    assert product_id == "531509"
    assert product.mpn == "ADXL355BEZ-RL7"
    assert min(tier.unit_price for tier in product.tiers) == Decimal("343.1176")


class FakePage:
    def __init__(self) -> None:
        self.url = "about:blank"
        self.goto_calls: list[str] = []

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        assert wait_until == "domcontentloaded"
        assert timeout > 0
        self.goto_calls.append(url)
        self.url = url

    def wait_for_timeout(self, timeout: int) -> None:
        assert timeout >= 0

    def content(self) -> str:
        if self.url.startswith("https://so.szlcsc.com/"):
            return _cn_search_html()
        return _cn_product_html()


class FakeBrowser:
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.closed = False

    def new_page(self) -> FakePage:
        return self.page

    def close(self) -> None:
        self.closed = True


class FakeChromium:
    def __init__(self, browser: FakeBrowser) -> None:
        self.browser = browser
        self.launch_calls: list[tuple[str, bool]] = []

    def launch(self, *, channel: str, headless: bool) -> FakeBrowser:
        self.launch_calls.append((channel, headless))
        return self.browser


class FakePlaywright:
    def __init__(self, chromium: FakeChromium) -> None:
        self.chromium = chromium

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_browser_client_uses_chinese_search_then_verified_product_page() -> None:
    page = FakePage()
    browser = FakeBrowser(page)
    chromium = FakeChromium(browser)
    client = LcscBrowserClient(
        settle_ms=0,
        playwright_factory=lambda: FakePlaywright(chromium),
    )

    capture = client.fetch_product_page("ADXL355BEZ-RL7")

    assert page.goto_calls == [
        "https://so.szlcsc.com/global.html?k=ADXL355BEZ-RL7",
        "https://item.szlcsc.com/531509.html",
    ]
    assert capture.product is not None
    assert capture.product.mpn == "ADXL355BEZ-RL7"
    assert browser.closed
