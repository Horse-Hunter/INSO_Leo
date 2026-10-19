from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Self

import pytest

from src.research.findchips import (
    FindchipsAdapter,
    FindchipsHttpClient,
    FindchipsOffer,
    FindchipsPage,
    FindchipsPageUnavailable,
    FindchipsParseError,
    FindchipsPriceTier,
    build_findchips_search_url,
    parse_findchips_offers,
    select_applicable_tier,
    select_lowest_valid_price,
)
from src.research.fx import UsdRmbQuote
from src.research.source_contracts import SourceOutcome, format_source_result

NOW = datetime(2026, 9, 22, 9, tzinfo=UTC)
FIXTURE = Path(__file__).parent / "fixtures" / "findchips_results_minimal.html"


class Client:
    def __init__(self, html: str) -> None:
        self.html = html

    def fetch_first_page(self, mpn: str) -> FindchipsPage:
        return FindchipsPage(self.html, build_findchips_search_url(mpn), NOW)


class Fx:
    def get_quote(self) -> UsdRmbQuote:
        return UsdRmbQuote(Decimal("7.10"), NOW, "synthetic-test-only")

    def get_hkd_rmb_rate(self) -> Decimal:
        return Decimal("0.91")


def _tier(quantity: int, price: str, currency: str = "USD") -> FindchipsPriceTier:
    return FindchipsPriceTier(quantity, Decimal(price), currency)


def _page(*rows: str) -> str:
    return (
        '<section class="distributor-results"><table>'
        + "".join(rows)
        + "</table></section>"
    )


def _row(
    mpn: str, stock: str | None, tiers: str, date: str | None = None
) -> str:
    stock_attr = "" if stock is None else f' data-instock="{stock}"'
    date_attr = "" if date is None else f' data-quotedate="{date}"'
    return (
        f'<tr data-mfrpartnumber="{mpn}"{stock_attr}{date_attr} '
        f"data-price='{tiers}'></tr>"
    )


def test_url_and_http_response_host_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    assert build_findchips_search_url("  Ab c-1  ").endswith("/AB")

    class Headers:
        def get_content_type(self) -> str:
            return "text/html"

        def get_content_charset(self) -> str:
            return "utf-8"

    class Response:
        status = 200
        headers = Headers()

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def geturl(self) -> str:
            return "https://evil.example/result"

        def read(self) -> bytes:
            return b"<html></html>"

    monkeypatch.setattr("src.research.findchips.urlopen", lambda *args, **kwargs: Response())
    result = FindchipsAdapter(FindchipsHttpClient(), Fx()).search("ABC", 1)
    assert result.outcome is SourceOutcome.SOURCE_UNAVAILABLE
    assert result.evidence.source_url == "https://evil.example/result"


def test_parser_retains_only_safe_offer_facts_and_fails_closed() -> None:
    offers = parse_findchips_offers(FIXTURE.read_text(encoding="utf-8"))
    assert len(offers) == 8
    assert offers[0].stock_positive is True
    assert offers[3].stock_positive is False
    assert not hasattr(offers[0], "stock_quantity")
    assert not hasattr(offers[0], "moq")
    with pytest.raises(FindchipsParseError, match="RESULT_CONTAINER_MISSING"):
        parse_findchips_offers("<html></html>")
    with pytest.raises(FindchipsPageUnavailable, match="LOGIN_REQUIRED"):
        parse_findchips_offers('<form>Login<input type="password"></form>')


def test_explicit_target_empty_result_without_offer_table_is_normal() -> None:
    html = '<p class="alert alert-info no-results">No results were found for TESTM.</p>'
    assert parse_findchips_offers(html, "TEST-MPN") == ()
    result = FindchipsAdapter(Client(html), Fx()).search("TEST-MPN", 40)
    assert result.outcome is SourceOutcome.NO_STRICT_MPN_MATCH


@pytest.mark.parametrize("html", [
    '<p class="alert alert-info no-results">No results were found for OTHER.</p>',
    '<script>No results were found for TESTM.</script>',
    '<p>No results were found for TESTM.</p>',
    '<p class="alert alert-info no-results">Temporarily unavailable</p>',
])
def test_empty_result_requires_authoritative_marker_and_matching_query(html):
    with pytest.raises(FindchipsParseError, match="RESULT_CONTAINER_MISSING"):
        parse_findchips_offers(html, "TEST-MPN")


def test_target_parse_ignores_unrelated_malformed_tiers() -> None:
    html = _page(
        _row("UNRELATED", "1", "not-json"),
        _row("TARGET", "1", '[[1,"USD","2.50"]]'),
    )
    offers = parse_findchips_offers(html, "TARGET")
    assert len(offers) == 1
    assert offers[0].mpn == "TARGET"
    with pytest.raises(FindchipsParseError, match="PRICE_TIERS_UNPARSEABLE"):
        parse_findchips_offers(_page(_row("TARGET", "1", "not-json")), "TARGET")


def test_hkd_offer_preserves_currency_and_converts_from_hkd() -> None:
    result = FindchipsAdapter(
        Client(_page(_row("FDA801B-VYT", "0", '[[1000,"HKD","94.7456"]]'))),
        Fx(),
    ).search("FDA801B-VYT", 10_000)
    assert result.outcome is SourceOutcome.SUCCESS
    assert result.out_of_stock_candidate is not None
    assert result.out_of_stock_candidate.raw_currency == "HKD"
    assert result.out_of_stock_candidate.normalized_rmb_price == Decimal("86.218496")


def test_uram3t21_keeps_stock_and_converts_each_visible_currency() -> None:
    html = _page(
        _row("URAM3T21", "8", '[[1,"HKD","1,855.5900"]]'),
        _row("URAM3T21", "0", '[[1,"USD","227.5800"],[10,"USD","225.7000"]]'),
    )
    result = FindchipsAdapter(Client(html), Fx()).search("uRAM3T21", 20)
    assert result.price_candidate is not None
    assert result.out_of_stock_candidate is not None
    assert (result.price_candidate.raw_price, result.price_candidate.raw_currency) == (
        Decimal("1855.5900"), "HKD"
    )
    assert result.price_candidate.normalized_rmb_price == Decimal("1688.586900")
    assert (result.out_of_stock_candidate.raw_price, result.out_of_stock_candidate.raw_currency) == (
        Decimal("225.7000"), "USD"
    )
    assert result.out_of_stock_candidate.normalized_rmb_price == Decimal("1602.470000")


def test_visible_hkd_tiers_override_stale_usd_attribute() -> None:
    html = _page(
        '<tr data-mfrpartnumber="URAM3T21" data-instock="8" '
        'data-price=\'[[1,"USD","227.5800"]]\'>'
        '<ul class="price-list"><li><span class="label">1</span>'
        '<span class="value" data-basecurrency="USD">HK$1,855.5900</span>'
        '</li></ul></tr>'
    )
    result = FindchipsAdapter(Client(html), Fx()).search("URAM3T21", 1)
    assert result.price_candidate is not None
    assert result.price_candidate.raw_currency == "HKD"
    assert result.price_candidate.raw_price == Decimal("1855.5900")
    assert result.price_candidate.normalized_rmb_price == Decimal("1688.586900")


def test_mixed_currency_tiers_are_compared_after_rmb_conversion() -> None:
    html = _page(_row("ABC", "8", '[[1,"USD","20"],[10,"HKD","100"]]'))
    result = FindchipsAdapter(Client(html), Fx()).search("ABC", 1)
    assert result.price_candidate is not None
    assert result.price_candidate.raw_currency == "HKD"
    assert result.price_candidate.normalized_rmb_price == Decimal("91.00")


def test_displayed_thousands_separator_is_parsed_as_price() -> None:
    offers = parse_findchips_offers(
        _page(_row("BCM957504-N425G", "0", '[[1,"HKD","6,361.7100"]]')),
        "BCM957504-N425G",
    )
    assert offers[0].tiers[0].unit_price == Decimal("6361.7100")


@pytest.mark.parametrize("quantity", [1, 10, 50, 100, 10_000])
def test_quantity_never_changes_lowest_displayed_tier(quantity: int) -> None:
    selected = select_applicable_tier(
        (_tier(1, "10"), _tier(10, "8"), _tier(100, "6")), quantity
    )
    assert selected == _tier(100, "6")


def test_lowest_selection_accepts_suffix_and_ignores_quantity() -> None:
    offers = (
        FindchipsOffer("ABC-123", True, (_tier(1, "5"),)),
        FindchipsOffer("ABC-123-T", True, (_tier(3000, "0.01"),)),
        FindchipsOffer("XABC-123", True, (_tier(1, "0.001"),)),
    )
    selected = select_lowest_valid_price(offers, "ABC-123", 1)
    assert selected is not None
    assert selected[0] == "ABC-123-T"
    assert selected[1].unit_price == Decimal("0.01")


def test_adapter_keeps_stocked_and_out_of_stock_minima_with_suffix_display() -> None:
    result = FindchipsAdapter(
        Client(FIXTURE.read_text(encoding="utf-8")), Fx()
    ).search("ABC-123", 50)

    assert result.outcome is SourceOutcome.SUCCESS
    assert result.price_candidate is not None
    assert result.price_candidate.matched_mpn == "ABC-123-T"
    assert result.price_candidate.raw_price == Decimal("0.001")
    assert result.price_candidate.normalized_rmb_price == Decimal("0.00710")
    assert result.out_of_stock_candidate is not None
    assert result.out_of_stock_candidate.raw_price == Decimal("0.02")
    assert format_source_result(result) == "0.01（ABC-123-T）\n0.14（无库存）"


def test_only_out_of_stock_is_successful_query_without_normal_candidate() -> None:
    html = _page(_row("ABC-1", "0", '[[1,"USD","1.00"]]'))
    result = FindchipsAdapter(Client(html), Fx()).search("ABC-1", 999)
    assert result.outcome is SourceOutcome.SUCCESS
    assert result.price_candidate is None
    assert result.out_of_stock_candidate is not None
    assert format_source_result(result) == "7.1（无库存）"


def test_dated_quotes_use_one_natural_month_and_undated_quotes_remain_valid() -> None:
    html = _page(
        _row("ABC", "1", '[[1,"USD","0.01"]]', "2026-08-21 16:59:59"),
        _row("ABC", "1", '[[1,"USD","2.00"]]'),
    )
    result = FindchipsAdapter(Client(html), Fx(), clock=lambda: NOW).search(
        "ABC", 1
    )
    assert result.price_candidate is not None
    assert result.price_candidate.raw_price == Decimal("2.00")


def test_suffix_over_ten_or_prefix_mutation_does_not_match() -> None:
    html = _page(
        _row("ABC-1ABCDEFGHI", "1", '[[1,"USD","0.01"]]'),
        _row("AXX-1", "1", '[[1,"USD","0.01"]]'),
    )
    result = FindchipsAdapter(Client(html), Fx()).search("ABC-1", 1)
    assert result.outcome is SourceOutcome.NO_STRICT_MPN_MATCH


def test_fx_or_acquisition_failure_is_technical_failure() -> None:
    class BrokenClient:
        def fetch_first_page(self, mpn: str) -> FindchipsPage:
            raise FindchipsPageUnavailable("HTTP_REQUEST_FAILED")

    class BrokenFx:
        def get_quote(self) -> UsdRmbQuote:
            raise RuntimeError("synthetic")

    unavailable = FindchipsAdapter(BrokenClient(), Fx()).search("ABC", 1)
    fx_failed = FindchipsAdapter(
        Client(_page(_row("ABC", "1", '[[1,"USD","1"]]'))), BrokenFx()
    ).search("ABC", 1)
    assert unavailable.outcome is SourceOutcome.SOURCE_UNAVAILABLE
    assert fx_failed.outcome is SourceOutcome.SOURCE_UNAVAILABLE


@pytest.mark.parametrize("message, code", [
    ("Bad captcha", "MANUAL_VERIFICATION_REQUIRED"),
    ("Invalid login", "LOGIN_REJECTED"),
])
def test_findchips_explicit_login_error_stops_wait_with_safe_reason(message, code):
    from types import SimpleNamespace
    from urllib.parse import quote

    from src.research.findchips import _findchips_login_pending
    from src.research.site_login import SiteLoginError

    page = SimpleNamespace(url="https://www.findchips.com/signin?login_error=" + quote(message))
    with pytest.raises(SiteLoginError) as error:
        _findchips_login_pending(page)
    assert error.value.reason_code == code
    assert message not in str(error.value)


@pytest.mark.parametrize("url, pending", [
    ("https://www.findchips.com/signin", True),
    ("https://www.findchips.com/signin?login_error=false", True),
    ("https://www.findchips.com/search/DRV8833PWR?login_error=Bad+captcha", False),
    ("https://untrusted.example/signin?login_error=Bad+captcha", True),
])
def test_findchips_only_own_signin_refusal_is_interpreted(url, pending):
    from types import SimpleNamespace

    from src.research.findchips import _findchips_login_pending
    assert _findchips_login_pending(SimpleNamespace(url=url)) is pending


@pytest.mark.parametrize("verdict, expected_clicks, error_code", [
    ("success", 1, None), ("silent_then_success", 2, None),
    ("silent", 2, "LOGIN_NOT_CONFIRMED"),
    ("request_pending", 1, "LOGIN_NOT_CONFIRMED"),
    ("page_changed", 1, "LOGIN_NOT_CONFIRMED"),
    ("button_busy", 1, "LOGIN_NOT_CONFIRMED"),
    ("delayed_success", 1, None),
    ("Bad captcha", 1, "MANUAL_VERIFICATION_REQUIRED"),
    ("Invalid login", 1, "LOGIN_REJECTED"),
])
def test_findchips_checks_options_waits_and_only_reclicks_if_silent(
    monkeypatch, verdict, expected_clicks, error_code,
):
    from types import SimpleNamespace
    from urllib.parse import quote

    from src.research import findchips as module
    from src.research.site_login import SiteLoginError

    events, listeners = [], {}
    now = [0.0]
    page = SimpleNamespace(url=module.FINDCHIPS_LOGIN_URL, html="login form")
    page.goto = lambda *a, **k: pytest.fail("reuse the opened login form")
    page.wait_for_load_state = lambda *a, **k: None
    page.evaluate = lambda _: True
    page.content = lambda: page.html
    page.on = lambda name, callback: listeners.__setitem__(name, callback)
    page.remove_listener = lambda name, callback: listeners.pop(name)

    class Control:
        def __init__(self, name, *, checked=False, visible=True, enabled=True):
            self.name, self.checked = name, checked
            self.visible, self.enabled = visible, enabled

        def is_visible(self):
            return self.visible

        def is_enabled(self):
            return self.enabled

        def is_checked(self):
            return self.checked

        def fill(self, value, *, timeout):
            events.append((self.name, value))

        def check(self, *, timeout):
            assert not self.checked, "already checked must never be clicked"
            self.checked = True
            events.append((self.name, now[0]))

        def click(self, *, timeout):
            events.append(("submit", now[0]))
            clicks = sum(name == "submit" for name, _ in events)
            if verdict == "success" or (verdict == "silent_then_success" and clicks == 2):
                page.url = "https://www.findchips.com/account"
            elif verdict in {"request_pending", "delayed_success"}:
                listeners["request"](SimpleNamespace(resource_type="xhr"))
            elif verdict == "page_changed":
                page.html = "login form with site response"
            elif verdict == "button_busy":
                self.enabled = False
            elif verdict in {"Bad captcha", "Invalid login"}:
                page.url += "?login_error=" + quote(verdict)

    options = [Control("option-1"), Control("option-2"),
               Control("already-checked", checked=True),
               Control("hidden", visible=False), Control("disabled", enabled=False)]
    controls = {
        module.FINDCHIPS_LOGIN_FORM.username: [Control("username")],
        module.FINDCHIPS_LOGIN_FORM.password: [Control("password")],
        module.FINDCHIPS_LOGIN_FORM.submit: [Control("submit")],
        'input[type="checkbox"]': options,
    }

    def locator(selector):
        matches = controls.get(selector, [])
        return SimpleNamespace(count=lambda: len(matches), nth=lambda i: matches[i])

    page.locator = locator
    monkeypatch.setattr(module, "challenge_present", lambda *a: False)
    monkeypatch.setattr("src.research.site_login.challenge_present", lambda *a: False)
    monkeypatch.setattr("src.research.site_login.rejection_present", lambda *a: False)

    def wait(seconds):
        events.append(("wait", seconds))
        now[0] += seconds
        if verdict == "delayed_success" and now[0] >= 7.5:
            page.url = "https://www.findchips.com/account"

    def run():
        module.ensure_findchips_signed_in(
            page, login=module.FindchipsLogin("synthetic-user", "synthetic-password"),
            timeout_ms=4_000, wait=wait, clock=lambda: now[0],
        )

    if error_code is None:
        run()
    else:
        with pytest.raises(SiteLoginError, match=error_code):
            run()
    assert events[:5] == [
        ("username", "synthetic-user"), ("password", "synthetic-password"),
        ("option-1", 0.0), ("option-2", 0.0), ("wait", 5.0),
    ]
    assert all(option.checked for option in options[:3])
    assert not options[3].checked and not options[4].checked
    submits = [value for name, value in events if name == "submit"]
    assert submits == ([5.0, 7.0] if expected_clicks == 2 else [5.0])
    assert listeners == {}


def test_findchips_existing_session_does_not_submit_again(monkeypatch):
    from types import SimpleNamespace

    from src.research import findchips as module
    page = SimpleNamespace(url="https://www.findchips.com/dashboard", goto=lambda *a, **k: None)
    monkeypatch.setattr(module, "unique_visible_control", lambda *a: pytest.fail("already signed in"))
    module.ensure_findchips_signed_in(page, login=object(), timeout_ms=1000)


@pytest.mark.parametrize("becomes_ready", [True, False])
def test_findchips_waits_for_passive_verification_before_click(monkeypatch, becomes_ready):
    from types import SimpleNamespace

    from src.research import findchips as module
    from src.research.site_login import SiteLoginError
    time = [0.0]
    waits = []
    def wait(seconds):
        waits.append(seconds)
        time[0] += seconds
    page = SimpleNamespace(wait_for_load_state=lambda *a, **k: None,
                           evaluate=lambda _: becomes_ready and time[0] >= .5)
    monkeypatch.setattr(module, "challenge_present", lambda *a: False)
    monkeypatch.setattr(module, "unique_visible_control", lambda *a: SimpleNamespace(is_enabled=lambda: True))
    if becomes_ready:
        module._wait_findchips_submit_ready(page, timeout_ms=1000, wait=wait, clock=lambda: time[0])
        assert time[0] == .5
    else:
        with pytest.raises(SiteLoginError, match="LOGIN_NOT_READY"):
            module._wait_findchips_submit_ready(page, timeout_ms=1000, wait=wait, clock=lambda: time[0])
        assert time[0] == 1.0
    assert waits


def test_owner_wgi_suffix_price_is_compared_and_wrong_prefix_excluded():
    html = _page(_row("WGI210IT S LJXS", "1", '[[1,"USD","1.25"]]'),
                 _row("WGI211IT", "1", '[[1,"USD","0.01"]]'))
    result = FindchipsAdapter(Client(html), Fx()).search("WGI210IT", 1)
    assert result.price_candidate.matched_mpn == "WGI210IT S LJXS"
    assert result.price_candidate.raw_price == Decimal("1.25")
