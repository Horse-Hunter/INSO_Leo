import json
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Self

import pytest

from src.research.fx import UsdRmbQuote
from src.research.lcsc import (
    CdpLcscClient,
    LcscAdapter,
    LcscBrowserClient,
    LcscLogin,
    LcscPage,
    LcscPageUnavailable,
    parse_lcsc_cooperation_card,
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


def test_cooperation_inventory_card_price_and_date() -> None:
    product = parse_lcsc_cooperation_card(
        "FDA801B-VYT\n更新时间\n2026年09月24日\n含税\n1+\n￥747.019462"
        "\n10+\n￥622.516219\n库存\n208",
        "FDA801B-VYT",
    )
    assert product is not None
    assert product.stock_quantity == 208
    assert product.observed_at is not None
    assert product.observed_at.date().isoformat() == "2026-09-23"
    assert select_lcsc_tier(product.tiers, 10_000).unit_price == Decimal("622.516219")


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
    mismatch = LcscAdapter(Client(_html("ABC-1ABCDEFG")), Fx()).search("ABC-1", 1)
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


def test_live_style_cooperation_card_without_update_date_is_a_price_result() -> None:
    card = """URAM3T21
品牌
Vicor Corporation
1+
￥1870.683574
8-14个工作日
库存
2
增量
1"""
    product = parse_lcsc_cooperation_card(card, "uRAM-3T21")
    assert product is not None
    assert product.mpn == "URAM3T21"
    assert product.observed_at is None
    assert product.stock_quantity == 2
    assert product.tiers[0].unit_price == Decimal("1870.683574")


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
            return _cn_search_html() + "<script>安全验证</script>"
        return _cn_product_html()

    def locator(self, selector: str) -> "FakePage":
        assert selector == "body"
        return self

    def inner_text(self) -> str:
        return "Search and product details"


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


class _CdpLocator:
    """A selector result that can only report how many matches it has."""

    def __init__(self, text: str = "", count: int = 0) -> None:
        self._text = text
        self._count = count

    def inner_text(self) -> str:
        return self._text

    def count(self) -> int:
        return self._count

    def all(self) -> list[object]:
        return []

    def nth(self, _index: int) -> "_CdpLocator":
        raise AssertionError("a selector with no match has no nth element")


class _LoginControl(_CdpLocator):
    """One login control, with the surface the shared login actually uses.

    ``count``/``nth``/``is_visible`` prove the control is the only visible
    match; ``fill``/``click`` then act on that same handle. ``count`` and
    ``visible`` are parameters so a test can pose the failures the real page
    poses: a missing field, or a selector that also matches something else.
    """

    def __init__(
        self,
        page: "_CdpPage",
        selector: str,
        *,
        count: int = 1,
        visible: bool = True,
        on_click: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(count=count)
        self._page = page
        self._selector = selector
        self._visible = visible
        self._on_click = on_click

    def nth(self, _index: int) -> "_LoginControl":
        return self

    def is_visible(self) -> bool:
        return self._visible

    def fill(self, value: str, *, timeout: int) -> None:
        assert timeout > 0
        self._page.fills.append((self._selector, value))

    def click(self, *, timeout: int) -> None:
        assert timeout > 0
        self._page.clicks.append(self._selector)
        if self._on_click is not None:
            self._on_click()


class _CdpPage:
    def __init__(self) -> None:
        self.url = "about:blank"
        self.goto_calls: list[str] = []
        self.closed = False
        self.fills: list[tuple[str, str]] = []
        self.clicks: list[str] = []

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        assert wait_until == "domcontentloaded"
        assert timeout > 0
        self.goto_calls.append(url)
        self.url = url

    def wait_for_timeout(self, timeout: int) -> None:
        assert timeout >= 0

    def fill(self, selector: str, value: str, *, timeout: int) -> None:
        assert timeout > 0
        self.fills.append((selector, value))

    def click(self, selector: str, *, timeout: int) -> None:
        assert timeout > 0
        self.clicks.append(selector)

    def locator(self, selector: str) -> _CdpLocator:
        if selector == "body":
            return _CdpLocator("search page")
        return _CdpLocator()

    def get_by_text(self, _text: str, *, exact: bool) -> _CdpLocator:
        assert exact
        return _CdpLocator()

    def content(self) -> str:
        return _cn_search_html()

    def close(self) -> None:
        self.closed = True


class _ExpiredSessionCdpPage(_CdpPage):
    """JLC's SSO shell: the account form only exists once its tab is opened."""

    def __init__(self) -> None:
        super().__init__()
        self.url = "https://passport.jlc.com/login"
        self.logged_in = False

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        assert wait_until == "domcontentloaded"
        assert timeout > 0
        self.goto_calls.append(url)
        self.url = (
            url
            if self.logged_in
            else "https://passport.jlc.com/login?redirectUrl=search"
        )

    def click(self, selector: str, *, timeout: int) -> None:
        raise AssertionError(
            f"page-level click({selector!r}) can land on the wrong element"
        )

    def fill(self, selector: str, value: str, *, timeout: int) -> None:
        raise AssertionError(
            f"page-level fill({selector!r}) can land on the wrong element"
        )

    def _sign_in(self) -> None:
        self.logged_in = True
        self.url = "https://so.szlcsc.com/"

    def locator(self, selector: str):
        if selector == 'input[type="text"]:visible, input[type="tel"]:visible':
            return _LoginControl(self, selector)
        if selector == 'input[type="password"]:visible':
            return _LoginControl(self, selector)
        if selector == "button.submit":
            return _LoginControl(self, selector, on_click=self._sign_in)
        return super().locator(selector)

    def get_by_text(self, text: str, *, exact: bool):
        assert exact
        if text == "账号登录":
            return _LoginControl(self, text)
        return _CdpLocator()


class _SameHostExpiredCdpPage(_ExpiredSessionCdpPage):
    """A login shell served from the search host after session expiry."""

    def __init__(self) -> None:
        super().__init__()
        self.url = "https://so.szlcsc.com/global.html?k=OLD"

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        assert wait_until == "domcontentloaded"
        assert timeout > 0
        self.goto_calls.append(url)
        self.url = url

    def content(self) -> str:
        return _cn_search_html() if self.logged_in else "<html>login shell</html>"


class _LcscLoginProvider:
    def get_login(self, site_id: str) -> LcscLogin | None:
        assert site_id == "szlcsc.com"
        return LcscLogin("synthetic-user", "synthetic-password")


class _CdpContext:
    def __init__(self, page: _CdpPage) -> None:
        self.pages = [page]


class _CdpBrowser:
    def __init__(self, context: _CdpContext) -> None:
        self.contexts = [context]


class _CdpChromium:
    def __init__(self, browser: _CdpBrowser) -> None:
        self.browser = browser

    def connect_over_cdp(self, _url: str, *, timeout: int) -> _CdpBrowser:
        assert timeout > 0
        return self.browser


class _CdpPlaywright:
    def __init__(self, chromium: _CdpChromium) -> None:
        self.chromium = chromium

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_cdp_client_initializes_lcsc_sso_before_background_search(
    monkeypatch,
) -> None:
    page = _CdpPage()
    chromium = _CdpChromium(_CdpBrowser(_CdpContext(page)))
    monkeypatch.setattr(
        "src.research.lcsc.new_background_page",
        lambda _browser, _context, **_kwargs: page,
    )
    client = CdpLcscClient(
        timeout_ms=1234,
        playwright_factory=lambda: _CdpPlaywright(chromium),
    )

    capture = client.fetch_product_page("ADXL355BEZ-RL7")

    assert page.goto_calls == [
        "https://www.szlcsc.com/",
        "https://so.szlcsc.com/global.html?k=ADXL355BEZ-RL7",
    ]
    assert capture.product is not None
    assert page.closed


def _owned_cdp_page(
    monkeypatch,
    stale: _CdpPage,
    fresh: _CdpPage,
    *,
    login_provider=None,
):
    """Wire the fake CDP context so the call's own tab is *fresh*."""

    chromium = _CdpChromium(_CdpBrowser(_CdpContext(stale)))
    monkeypatch.setattr(
        "src.research.lcsc.new_background_page",
        lambda _browser, _context, **_kwargs: fresh,
    )
    return CdpLcscClient(
        timeout_ms=1234,
        login_provider=login_provider,
        playwright_factory=lambda: _CdpPlaywright(chromium),
    )


SEARCH_URL = "https://so.szlcsc.com/global.html?k=ADXL355BEZ-RL7"


def test_cdp_client_opens_its_own_tab_and_closes_it(monkeypatch) -> None:
    """Owner rule: every call opens a tab, uses it, and gives it back."""

    stale = _CdpPage()
    stale.url = "https://so.szlcsc.com/global.html?k=OTHER"
    fresh = _CdpPage()
    client = _owned_cdp_page(monkeypatch, stale, fresh)

    capture = client.fetch_product_page("ADXL355BEZ-RL7")

    assert stale.goto_calls == [], "an earlier tab must not be reused"
    assert fresh.goto_calls == ["https://www.szlcsc.com/", SEARCH_URL]
    assert capture.product is not None
    assert fresh.closed


def test_cdp_client_recovers_expired_jlc_session_and_retries_search_once(
    monkeypatch,
) -> None:
    stale = _CdpPage()
    page = _ExpiredSessionCdpPage()
    client = _owned_cdp_page(
        monkeypatch, stale, page, login_provider=_LcscLoginProvider()
    )

    capture = client.fetch_product_page("ADXL355BEZ-RL7")

    assert page.goto_calls == ["https://www.szlcsc.com/", SEARCH_URL, SEARCH_URL]
    assert (
        'input[type="text"]:visible, input[type="tel"]:visible',
        "synthetic-user",
    ) in page.fills
    assert ('input[type="password"]:visible', "synthetic-password") in page.fills
    assert page.clicks == ["账号登录", "button.submit"]
    assert capture.product is not None
    assert page.closed


def test_cdp_client_reports_login_required_when_jlc_vault_is_absent(
    monkeypatch,
) -> None:
    stale = _CdpPage()
    page = _ExpiredSessionCdpPage()
    client = _owned_cdp_page(monkeypatch, stale, page)

    with pytest.raises(LcscPageUnavailable, match="LOGIN_REQUIRED"):
        client.fetch_product_page("ADXL355BEZ-RL7")

    assert page.closed


def test_cdp_client_recovers_when_same_host_login_shell_breaks_parser(
    monkeypatch,
) -> None:
    stale = _CdpPage()
    page = _SameHostExpiredCdpPage()
    client = _owned_cdp_page(
        monkeypatch, stale, page, login_provider=_LcscLoginProvider()
    )

    capture = client.fetch_product_page("ADXL355BEZ-RL7")

    assert page.goto_calls == ["https://www.szlcsc.com/", SEARCH_URL, SEARCH_URL]
    assert capture.product is not None
    assert page.closed


# ---------------------------------------------------------------------------
# The slider JLC raises when it distrusts the login
#
# Measured live 2026-10-01: the challenge is raised *after* the submit and says
# "安全验证 / 为了您的账号安全，请完成验证 / 请按住滑块，拖动到最右边". Its widget is
# injected lazily, so its markup is in no eagerly-loaded bundle -- hence the
# selector list plus a geometric fallback. The company rule is that the slider
# is dragged by us, not left for the Owner.
# ---------------------------------------------------------------------------


class _Clock:
    """A clock and a sleep that only advance when the code under test sleeps."""

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds

    def monotonic(self) -> float:
        return self.now


class _ChallengeBody:
    def __init__(self, page: "_SliderChallengeCdpPage") -> None:
        self._page = page

    def inner_text(self) -> str:
        if self._page.challenging:
            return (
                "登录\n安全验证\n为了您的账号安全，请完成验证\n请按住滑块，拖动到最右边"
            )
        return "search page"

    def count(self) -> int:
        return 1

    def all(self) -> list[object]:
        return []

    def nth(self, _index: int) -> object:
        raise AssertionError("the body has exactly one match")


class _ChallengeMouse:
    def __init__(self, page: "_SliderChallengeCdpPage") -> None:
        self._page = page
        self.events: list[tuple] = []

    def move(self, x: float, y: float) -> None:
        self.events.append(("move", x, y))

    def down(self) -> None:
        self.events.append(("down",))

    def up(self) -> None:
        self.events.append(("up",))
        self._page.gestures += 1
        if self._page.clears:
            self._page.challenging = False
            self._page.logged_in = True
            self._page.url = "https://so.szlcsc.com/"

    @property
    def xs(self) -> list[float]:
        return [event[1] for event in self.events if event[0] == "move"]


class _SliderHandle:
    """The handle the widget draws, plus the geometry a drag has to read."""

    def is_visible(self) -> bool:
        return True

    def evaluate(self, _script: str) -> dict:
        return {
            "handle": [100.0, 200.0, 40.0, 40.0],
            "track": [100.0, 200.0, 300.0, 40.0],
        }


class _SliderLocator:
    def __init__(self, handle: _SliderHandle) -> None:
        self._handle = handle

    def count(self) -> int:
        return 1

    def nth(self, _index: int) -> _SliderHandle:
        return self._handle

    @property
    def first(self) -> _SliderHandle:
        return self._handle

    def inner_text(self) -> str:
        return ""


class _SliderChallengeCdpPage(_ExpiredSessionCdpPage):
    """JLC's risk answer: the submit raises a slider instead of signing in."""

    def __init__(self, *, clears: bool = True) -> None:
        super().__init__()
        self.clears = clears
        self.challenging = False
        self.gestures = 0
        self.mouse = _ChallengeMouse(self)
        self.handle = _SliderHandle()

    def _sign_in(self) -> None:
        self.challenging = True

    def locator(self, selector: str):
        if selector == "body":
            return _ChallengeBody(self)
        if selector == "#nc_1_n1z":
            return _SliderLocator(self.handle)
        return super().locator(selector)


def _frozen_login_clock(monkeypatch) -> _Clock:
    clock = _Clock()
    monkeypatch.setattr("src.research.lcsc.sleep", clock.sleep)
    monkeypatch.setattr("src.research.lcsc.monotonic", clock.monotonic)
    return clock


def test_cdp_client_leaves_slider_verification_to_the_operator(
    monkeypatch,
) -> None:
    _frozen_login_clock(monkeypatch)
    stale = _CdpPage()
    page = _SliderChallengeCdpPage()
    client = _owned_cdp_page(
        monkeypatch, stale, page, login_provider=_LcscLoginProvider()
    )

    with pytest.raises(LcscPageUnavailable, match="MANUAL_VERIFICATION_REQUIRED"):
        client.fetch_product_page("ADXL355BEZ-RL7")
    assert page.challenging is True
    assert page.gestures == 0
    assert page.closed


def test_cdp_client_keeps_the_manual_verdict_when_the_slider_will_not_clear(
    monkeypatch,
) -> None:
    """A drag we cannot confirm is not a solved challenge."""

    _frozen_login_clock(monkeypatch)
    stale = _CdpPage()
    page = _SliderChallengeCdpPage(clears=False)
    client = _owned_cdp_page(
        monkeypatch, stale, page, login_provider=_LcscLoginProvider()
    )

    with pytest.raises(LcscPageUnavailable, match="MANUAL_VERIFICATION_REQUIRED"):
        client.fetch_product_page("ADXL355BEZ-RL7")

    assert page.gestures == 0, "verification is manual, never retried by dragging"
    assert page.closed
