from datetime import UTC, datetime
from decimal import Decimal
from typing import Self

import pytest

from src.research.hqew import (
    CdpHqewClient,
    HqewAdapter,
    HqewPage,
    HqewPageUnavailable,
    parse_hqew_offers,
)
from src.research.source_contracts import SourceOutcome

NOW = datetime(2026, 9, 22, tzinfo=UTC)


def _row(mpn: str, price: str, date: str | None = None) -> str:
    date_attr = "" if date is None else f' quotationDate="{date}"'
    return (
        f'<input class="list-data" pmodel="{mpn}" '
        f'quotationPrice="{price}"{date_attr}>'
    )


class Client:
    def __init__(self, html: str) -> None:
        self.html = html

    def fetch_first_page(self, mpn: str) -> HqewPage:
        return HqewPage(self.html, f"https://p.hqew.com/yunquote/{mpn}.html?y4=1", NOW)


class Blocked:
    def fetch_first_page(self, mpn: str) -> HqewPage:
        raise HqewPageUnavailable("INTERACTIVE_CHALLENGE_REQUIRED")


class FakeLocator:
    def __init__(self, count: int) -> None:
        self._count = count

    def count(self) -> int:
        return self._count


class FakeCdpPage:
    def __init__(self, url: str, html: str, *, has_body: bool = True) -> None:
        self.url = url
        self.html = html
        self.has_body = has_body
        self.goto_calls: list[tuple[str, str, int]] = []

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        self.goto_calls.append((url, wait_until, timeout))
        self.url = url

    def wait_for_load_state(self, state: str, *, timeout: int) -> None:
        assert state == "load"
        assert timeout > 0

    def wait_for_timeout(self, timeout: int) -> None:
        assert timeout >= 0

    def locator(self, selector: str) -> FakeLocator:
        assert selector == "body"
        return FakeLocator(int(self.has_body))

    def content(self) -> str:
        return self.html


class FakeCdpContext:
    def __init__(self, pages: list[FakeCdpPage]) -> None:
        self.pages = pages

    def new_page(self) -> FakeCdpPage:
        page = FakeCdpPage("about:blank", "<html><body></body></html>")
        self.pages.append(page)
        return page


class FakeCdpBrowser:
    def __init__(self, context: FakeCdpContext) -> None:
        self.contexts = [context]


class FakeChromium:
    def __init__(self, browser: FakeCdpBrowser) -> None:
        self.browser = browser

    def connect_over_cdp(self, url: str, *, timeout: int) -> FakeCdpBrowser:
        return self.browser


class FakePlaywright:
    def __init__(self, chromium: FakeChromium) -> None:
        self.chromium = chromium

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _cdp_client(
    pages: list[FakeCdpPage],
    *,
    navigate: bool,
    cdp_url: str = "http://127.0.0.1:9333",
) -> tuple[CdpHqewClient, FakeChromium]:
    context = FakeCdpContext(pages)
    chromium = FakeChromium(FakeCdpBrowser(context))
    client = CdpHqewClient(
        cdp_url=cdp_url,
        timeout_ms=1234,
        settle_ms=0,
        navigate=navigate,
        playwright_factory=lambda: FakePlaywright(chromium),
    )
    return client, chromium


def test_parser_and_adapter_use_suffix_lowest_rmb_offer() -> None:
    html = (
        "<table>"
        + _row("ABC-1", "3.20")
        + _row("abc-1", "2.10")
        + _row("ABC-1-T", "0.01")
        + "</table>"
    )
    assert len(parse_hqew_offers(html)) == 3
    result = HqewAdapter(Client(html)).search(" ABC-1 ", 50)
    assert result.outcome is SourceOutcome.SUCCESS
    assert result.price_candidate is not None
    assert result.price_candidate.raw_price == Decimal("0.01")
    assert result.price_candidate.normalized_rmb_price == Decimal("0.01")
    assert result.price_candidate.display_mpn == "ABC-1-T"


def test_dated_history_is_limited_to_one_calendar_month_but_undated_is_allowed() -> None:
    html = (
        _row("ABC", "0.01", "2026-08-21 23:59:59")
        + _row("ABC", "2.00", "2026-08-22 00:00:00")
        + _row("ABC", "1.50")
    )
    adapter = HqewAdapter(Client(html), clock=lambda: NOW)

    result = adapter.search("ABC", 1)

    assert result.price_candidate is not None
    assert result.price_candidate.raw_price == Decimal("1.50")


def test_relative_and_year_month_dates_are_parsed_relative_to_capture() -> None:
    html = (
        _row("ABC", "3.00", "今天")
        + _row("ABC", "8.00", "昨天")
        + _row("ABC", "7.00", "前天")
        + _row("ABC", "6.00", "1周内")
        + _row("ABC", "5.00", "2026-08")
        + _row("ABC", "4.00", "2026-07-01")
    )
    adapter = HqewAdapter(Client(html), clock=lambda: NOW)
    result = adapter.search("ABC", 1)

    assert result.outcome is SourceOutcome.SUCCESS
    assert result.price_candidate is not None
    assert result.price_candidate.raw_price == Decimal("3.00")
    assert result.price_candidate.age_months == 1
    # all six rows parse (relative + YYYY-MM + explicit dates)
    assert result.evidence.fields[0].value == 6


def test_challenge_fails_closed() -> None:
    result = HqewAdapter(Blocked()).search("ABC", 1)
    assert result.outcome is SourceOutcome.SOURCE_UNAVAILABLE
    assert result.price_candidate is None


@pytest.mark.parametrize(
    "empty_marker",
    [
        '抱歉：您搜索的<span title="ABC">ABC</span>无结果',
        '<div class="list-none-text">暂无数据</div>',
        "暂无商家报价",
    ],
)
def test_empty_result_page_returns_no_offers(empty_marker: str) -> None:
    html = f"<html><body>{empty_marker}</body></html>"
    assert parse_hqew_offers(html, reference_at=NOW) == ()


@pytest.mark.parametrize(
    "cdp_url",
    [
        "http://localhost:9222",
        "http://127.0.0.1:9222",
        "http://[::1]:9222",
    ],
)
def test_cdp_client_accepts_loopback_endpoints(cdp_url: str) -> None:
    client, _ = _cdp_client([], navigate=True, cdp_url=cdp_url)
    assert client is not None


def test_cdp_client_rejects_remote_endpoint() -> None:
    with pytest.raises(HqewPageUnavailable, match="CDP_REMOTE_ENDPOINT_FORBIDDEN"):
        _cdp_client(
            [], navigate=True, cdp_url="http://192.0.2.10:9222"
        )


def test_cdp_client_reuses_authenticated_hqew_page_for_navigation() -> None:
    page = FakeCdpPage("https://www.hqew.com/", _row("ABC", "1.25"))
    client, _ = _cdp_client([page], navigate=True)

    captured = client.fetch_first_page(" ABC ")

    target = "https://p.hqew.com/yunquote/ABC.html?y4=1"
    assert captured.url == target
    assert page.goto_calls == [(target, "domcontentloaded", 1234)]


def test_cdp_client_does_not_reuse_unrelated_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.research.hqew.new_background_page",
        lambda _browser, context, **_kwargs: context.new_page(),
    )
    unrelated = FakeCdpPage("https://evil.example/", _row("ABC", "1.25"))
    client, chromium = _cdp_client([unrelated], navigate=True)

    captured = client.fetch_first_page("ABC")

    context = chromium.browser.contexts[0]
    assert captured.url == "https://p.hqew.com/yunquote/ABC.html?y4=1"
    assert unrelated.goto_calls == []
    assert len(context.pages) == 2


def test_cdp_client_attach_only_requires_exact_result_page() -> None:
    page = FakeCdpPage("https://www.hqew.com/", _row("ABC", "1.25"))
    client, _ = _cdp_client([page], navigate=False)

    with pytest.raises(HqewPageUnavailable, match="CDP_TARGET_PAGE_NOT_OPEN"):
        client.fetch_first_page("ABC")


def test_cdp_client_challenge_fails_closed_after_authenticated_navigation() -> None:
    html = '<html><body>安全验证</body></html>'
    page = FakeCdpPage("https://p.hqew.com/yunquote/ABC.html?y4=1", html)
    client, _ = _cdp_client([page], navigate=False)

    with pytest.raises(HqewPageUnavailable, match="INTERACTIVE_CHALLENGE_REQUIRED"):
        client.fetch_first_page("ABC")


def test_package_api_prefers_authenticated_browser_client() -> None:
    import src.research.hqew as hqew_module

    assert hqew_module.HqewAdapter is HqewAdapter
    assert hqew_module.CdpHqewClient is CdpHqewClient
