from datetime import UTC, datetime
from decimal import Decimal
from typing import Self

from src.research.fx import UsdRmbQuote
from src.research.inso_history import (
    INSO_SITE_ID,
    InsoBrowserConfig,
    InsoCredentialedClient,
    InsoHistoryAdapter,
    InsoHistoryCapture,
    InsoHistoryRecord,
    InsoLogin,
    InsoReadError,
    PlaywrightInsoReadOnlyBrowser,
    parse_inso_history_rows,
)
from src.research.source_contracts import SourceOutcome, format_source_result

NOW = datetime(2026, 9, 30, 10, tzinfo=UTC)


class Client:
    def __init__(self, records: tuple[InsoHistoryRecord, ...]) -> None:
        self.records = records

    def fetch_history(self, mpn: str) -> InsoHistoryCapture:
        return InsoHistoryCapture(self.records, "https://inso.example/history", NOW)


class Fx:
    def get_quote(self) -> UsdRmbQuote:
        return UsdRmbQuote(Decimal(7), NOW, "synthetic-test-only")


def test_inso_uses_positive_supplier_untaxed_usd_and_first_nonempty_window() -> None:
    records = (
        InsoHistoryRecord(Decimal(0), datetime(2026, 9, 29, tzinfo=UTC)),
        InsoHistoryRecord(Decimal(2), datetime(2026, 8, 29, tzinfo=UTC)),
        InsoHistoryRecord(Decimal(1), datetime(2026, 7, 29, tzinfo=UTC)),
    )

    result = InsoHistoryAdapter(Client(records), Fx(), clock=lambda: NOW).search(
        "QUERY-MPN", 999
    )

    assert result.outcome is SourceOutcome.SUCCESS
    assert result.price_candidate is not None
    assert result.price_candidate.raw_price == Decimal(2)
    assert result.price_candidate.normalized_rmb_price == Decimal(14)
    assert result.price_candidate.age_months == 2
    assert format_source_result(result) == "14（两个月）"


def test_inso_three_month_window_and_no_mpn_filtering() -> None:
    records = (
        InsoHistoryRecord(Decimal(3), datetime(2026, 7, 1, tzinfo=UTC)),
    )
    result = InsoHistoryAdapter(Client(records), Fx(), clock=lambda: NOW).search(
        "ANY-MPN", 1
    )
    assert result.price_candidate is not None
    assert result.price_candidate.age_months == 3
    assert format_source_result(result) == "21（三个月）"


def test_zero_or_older_than_three_months_is_no_result() -> None:
    records = (
        InsoHistoryRecord(Decimal(0), datetime(2026, 9, 1, tzinfo=UTC)),
        InsoHistoryRecord(Decimal(1), datetime(2026, 6, 29, tzinfo=UTC)),
    )
    result = InsoHistoryAdapter(Client(records), Fx(), clock=lambda: NOW).search(
        "ABC", 1
    )
    assert result.outcome is SourceOutcome.NO_VALID_PRICE
    assert format_source_result(result) == "无结果"


def test_credentialed_client_has_only_read_history_capability_and_hides_secrets() -> None:
    assert "secret" not in repr(InsoLogin("user-secret", "password-secret"))
    assert "123.45" not in repr(InsoHistoryRecord(Decimal("123.45"), NOW))

    class Credentials:
        site_id: str | None = None

        def get_login(self, site_id: str) -> InsoLogin | None:
            self.site_id = site_id
            return InsoLogin("user-secret", "password-secret")

    class Browser:
        query: str | None = None

        def fetch_procurement_temporary_inquiry_history(
            self, mpn: str, login: InsoLogin
        ) -> InsoHistoryCapture:
            self.query = mpn
            return InsoHistoryCapture((), "https://inso.example/history", NOW)

    credentials = Credentials()
    browser = Browser()
    client = InsoCredentialedClient(credentials, browser)
    capture = client.fetch_history("ABC")
    assert credentials.site_id == INSO_SITE_ID
    assert browser.query == "ABC"
    assert capture.records == ()
    assert not hasattr(client, "submit")
    assert not hasattr(client, "create_order")


def test_missing_credentials_and_fx_failure_are_technical_failures() -> None:
    class MissingCredentials:
        def get_login(self, site_id: str) -> InsoLogin | None:
            return None

    class Browser:
        def fetch_procurement_temporary_inquiry_history(
            self, mpn: str, login: InsoLogin
        ) -> InsoHistoryCapture:
            raise AssertionError("must not be called")

    try:
        InsoCredentialedClient(MissingCredentials(), Browser()).fetch_history("ABC")
    except InsoReadError as exc:
        assert exc.code == "CREDENTIALS_UNAVAILABLE"
    else:
        raise AssertionError("missing credentials must fail")

    class BrokenFx:
        def get_quote(self) -> UsdRmbQuote:
            raise RuntimeError("synthetic")

    result = InsoHistoryAdapter(
        Client((InsoHistoryRecord(Decimal(1), NOW),)),
        BrokenFx(),
        clock=lambda: NOW,
    ).search("ABC", 1)
    assert result.outcome is SourceOutcome.SOURCE_UNAVAILABLE


def test_history_row_parser_reads_only_date_and_supplier_untaxed_price() -> None:
    records = parse_inso_history_rows(
        [
            {
                "observed_at": "2026-09-24 13:14:15",
                "supplier_untaxed_price": "$ 1,234.50",
            },
            {
                "observed_at": "2026-09-23",
                "supplier_untaxed_price": "0",
            },
        ]
    )

    assert [record.supplier_untaxed_price_usd for record in records] == [
        Decimal("1234.50"),
        Decimal(0),
    ]
    assert records[0].observed_at == datetime(2026, 9, 24, 5, 14, 15, tzinfo=UTC)


class FakeLocator:
    def __init__(self, name: str, calls: list[tuple[str, str, str | None]]) -> None:
        self.name = name
        self.calls = calls

    def count(self) -> int:
        return 1

    def fill(self, value: str) -> None:
        self.calls.append(("fill", self.name, value))

    def click(self) -> None:
        self.calls.append(("click", self.name, None))


class FakeInsoPage:
    def __init__(self) -> None:
        self.url = "about:blank"
        self.calls: list[tuple[str, str, str | None]] = []

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        assert wait_until == "domcontentloaded"
        assert timeout > 0
        self.url = url
        self.calls.append(("goto", url, None))

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(selector, self.calls)

    def get_by_text(self, text: str, *, exact: bool) -> FakeLocator:
        assert exact
        return FakeLocator(f"text:{text}", self.calls)

    def wait_for_timeout(self, timeout: int) -> None:
        assert timeout >= 0

    def content(self) -> str:
        return "<html><body>read-only query</body></html>"

    def evaluate(self, script: str, args: object) -> list[dict[str, str]]:
        assert "INSO_HISTORY_TABLE_MISSING" in script
        assert args == {
            "priceHeader": "供方未税价",
            "dateHeaders": ["报价时间"],
        }
        return [
            {
                "observed_at": "2026-09-24 08:00:00",
                "supplier_untaxed_price": "1.25",
            }
        ]


class FakeInsoBrowser:
    def __init__(self, page: FakeInsoPage) -> None:
        self.page = page
        self.closed = False

    def new_page(self) -> FakeInsoPage:
        return self.page

    def close(self) -> None:
        self.closed = True


class FakeChromium:
    def __init__(self, browser: FakeInsoBrowser) -> None:
        self.browser = browser

    def launch(self, *, channel: str, headless: bool) -> FakeInsoBrowser:
        assert channel == "chrome"
        assert not headless
        return self.browser


class FakePlaywright:
    def __init__(self, chromium: FakeChromium) -> None:
        self.chromium = chromium

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_concrete_browser_login_navigation_query_and_scoped_read() -> None:
    config = InsoBrowserConfig(
        "https://inso.example/login",
        "#username",
        "#password",
        "#login",
        "#mpn",
        "#query",
        "#company",
        ("报价时间",),
    )
    page = FakeInsoPage()
    browser = FakeInsoBrowser(page)
    acquisition = PlaywrightInsoReadOnlyBrowser(
        config,
        settle_ms=0,
        playwright_factory=lambda: FakePlaywright(FakeChromium(browser)),
    )

    capture = acquisition.fetch_procurement_temporary_inquiry_history(
        " ABC-1 ", InsoLogin("synthetic-user", "synthetic-password", "Synthetic Co")
    )

    assert ("click", "text:1.业务询价", None) in page.calls
    assert ("click", "text:采购临时询价", None) in page.calls
    assert ("fill", "#mpn", "ABC-1") in page.calls
    assert ("click", "#query", None) in page.calls
    assert capture.records[0].supplier_untaxed_price_usd == Decimal("1.25")
    assert not hasattr(acquisition, "submit")
    assert not hasattr(acquisition, "create_order")
    assert browser.closed


def test_browser_config_and_navigation_fail_closed() -> None:
    try:
        InsoBrowserConfig("http://inso.example", "u", "p", "l", "m", "q")
    except ValueError:
        pass
    else:
        raise AssertionError("non-HTTPS INSO endpoint must be rejected")

    class RedirectPage(FakeInsoPage):
        def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
            super().goto(url, wait_until=wait_until, timeout=timeout)
            self.url = "https://unexpected.example/login"

    config = InsoBrowserConfig(
        "https://inso.example/login", "u", "p", "l", "m", "q"
    )
    page = RedirectPage()
    acquisition = PlaywrightInsoReadOnlyBrowser(
        config,
        playwright_factory=lambda: FakePlaywright(
            FakeChromium(FakeInsoBrowser(page))
        ),
    )
    try:
        acquisition.fetch_procurement_temporary_inquiry_history(
            "ABC", InsoLogin("u", "p")
        )
    except InsoReadError as exc:
        assert exc.code == "UNEXPECTED_NAVIGATION_HOST"
    else:
        raise AssertionError("cross-host navigation must fail closed")
