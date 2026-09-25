from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Self

import pytest

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
    build_inso_stock_venquote_form,
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


def _rec(price: str | Decimal, currency: str, observed: datetime) -> InsoHistoryRecord:
    return InsoHistoryRecord(Decimal(price), currency, observed)


def test_inso_uses_lowest_rmb_normalized_price_and_first_nonempty_window() -> None:
    # RMB 14 is cheaper than USD 4 (which normalizes to RMB 28 at rate 7)
    records = (
        _rec("0", "USD", datetime(2026, 9, 29, tzinfo=UTC)),
        _rec("14", "RMB", datetime(2026, 8, 29, tzinfo=UTC)),
        _rec("4", "USD", datetime(2026, 7, 29, tzinfo=UTC)),  # normalizes to 28 RMB
    )

    result = InsoHistoryAdapter(Client(records), Fx(), clock=lambda: NOW).search(
        "QUERY-MPN", 999
    )

    assert result.outcome is SourceOutcome.SUCCESS
    assert result.price_candidate is not None
    assert result.price_candidate.raw_price == Decimal(14)
    assert result.price_candidate.raw_currency == "RMB"
    assert result.price_candidate.normalized_rmb_price == Decimal(14)
    assert result.price_candidate.age_months == 2
    assert format_source_result(result) == "14（两个月）"


def test_inso_three_month_window() -> None:
    # within last 3 months only
    records = (
        _rec("3", "USD", datetime(2026, 7, 1, tzinfo=UTC)),
    )
    result = InsoHistoryAdapter(Client(records), Fx(), clock=lambda: NOW).search(
        "ANY-MPN", 1
    )
    assert result.price_candidate is not None
    assert result.price_candidate.age_months == 3
    assert format_source_result(result) == "21（三个月）"


def test_zero_or_older_than_three_months_is_no_result() -> None:
    records = (
        _rec("0", "USD", datetime(2026, 9, 1, tzinfo=UTC)),
        _rec("1", "USD", datetime(2026, 6, 29, tzinfo=UTC)),
    )
    result = InsoHistoryAdapter(Client(records), Fx(), clock=lambda: NOW).search(
        "ABC", 1
    )
    assert result.outcome is SourceOutcome.NO_VALID_PRICE
    assert format_source_result(result) == "无结果"


def test_credentialed_client_has_only_read_history_capability_and_hides_secrets() -> None:
    assert "secret" not in repr(InsoLogin("user-secret", "password-secret"))
    assert "123.45" not in repr(_rec("123.45", "USD", NOW))

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
        Client((_rec("1", "USD", NOW),)),
        BrokenFx(),
        clock=lambda: NOW,
    ).search("ABC", 1)
    assert result.outcome is SourceOutcome.SOURCE_UNAVAILABLE


def test_history_row_parser_reads_create_time_rpc_inprice_and_currencyid() -> None:
    records = parse_inso_history_rows(
        [
            {
                "CreateTime": "2026-09-24 13:14:15",
                "InPrice": "5.398230",
                "CurrencyID": "RMB",
            },
            {
                "CreateTime": "2026-09-23 11:00:00",
                "InPrice": "0",
                "CurrencyID": "USD",
            },
            {
                "CreateTime": "bad-date",
                "InPrice": "1.00",
                "CurrencyID": "USD",
            },
            {
                "CreateTime": "2026-09-22 09:00:00",
                "InPrice": "junk",
                "CurrencyID": "USD",
            },
            {
                "CreateTime": "2026-09-21 09:00:00",
                "InPrice": "2.50",
                "CurrencyID": "EUR",
            },
        ]
    )

    assert [r.price for r in records] == [Decimal("5.398230")]
    assert records[0].currency == "RMB"
    assert records[0].observed_at == datetime(2026, 9, 24, 5, 14, 15, tzinfo=UTC)


def test_build_inso_form_encodes_mpn_and_required_keys() -> None:
    body = build_inso_stock_venquote_form("STM32F103C8T6")
    # brackets are sent literal here; the HTTP transport URL-encodes them
    assert "searchData[DetailFieldValue]=STM32F103C8T6" in body
    assert "searchData[BillDateType]=all" in body
    assert "searchData[leftlike]=on" in body
    assert "searchData[CompanyType]=CompanyID" in body
    assert "searchData[OwnerType]=OwnerID" in body


class FakeResponse:
    def __init__(self, text: str) -> None:
        self._text = text

    def text(self) -> str:
        return self._text


class FakeRequest:
    def __init__(self, response_text: str, captured: dict) -> None:
        self._response_text = response_text
        self.captured = captured

    def post(self, url: str, *, headers: dict, data: str, timeout: int) -> FakeResponse:
        self.captured["url"] = url
        self.captured["headers"] = headers
        self.captured["data"] = data
        self.captured["timeout"] = timeout
        return FakeResponse(self._response_text)


class FakePage:
    context_id = "ctx-verified"

    def __init__(self, response_text: str, captured: dict) -> None:
        self.target_id = "target-operation-child"
        self.request = FakeRequest(response_text, captured)
        self.closed = False

    def is_closed(self) -> bool:
        return self.closed

    def close(self) -> None:
        self.closed = True


class FakeOperationPage:
    def __init__(self, page: FakePage) -> None:
        self.page = page

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        self.page.close()


class FakeOperationAccess:
    def __init__(self, page: FakePage) -> None:
        self.page = page

    def open_operation_page(self) -> FakeOperationPage:
        return FakeOperationPage(self.page)


def test_concrete_browser_uses_cdp_and_posts_stock_venquote() -> None:
    payload = {
        "total": -1,
        "rows": [
            {
                "CreateTime": "2026-09-24 08:00:00",
                "InPrice": "1.25",
                "CurrencyID": "USD",
                "PartNo": "ABC-1",
            }
        ],
    }
    import json as _json

    captured: dict = {}
    page = FakePage(_json.dumps(payload), captured)
    acquisition = PlaywrightInsoReadOnlyBrowser(
        InsoBrowserConfig(
            login_url="https://inso.example/",
            cdp_url="http://127.0.0.1:9222",
        ),
        settle_ms=0,
        operation_access=FakeOperationAccess(page),
    )

    capture = acquisition.fetch_procurement_temporary_inquiry_history(
        " ABC-1 ", InsoLogin("u", "p")
    )

    assert "ABC-1" in captured["data"]
    assert captured["headers"]["Content-Type"].startswith(
        "application/x-www-form-urlencoded"
    )
    assert "action=Stock_VenQuote" in captured["url"]
    assert "DetailField=PartNo" in captured["url"]
    assert capture.records[0].price == Decimal("1.25")
    assert capture.records[0].currency == "USD"
    assert page.closed
    assert not hasattr(acquisition, "close_browser")
    assert not hasattr(acquisition, "submit")
    assert not hasattr(acquisition, "create_order")


def test_concrete_browser_empty_response_is_fail_closed() -> None:
    captured: dict = {}
    page = FakePage("{}", captured)
    acquisition = PlaywrightInsoReadOnlyBrowser(
        InsoBrowserConfig(login_url="https://inso.example/"),
        settle_ms=0,
        operation_access=FakeOperationAccess(page),
    )

    try:
        acquisition.fetch_procurement_temporary_inquiry_history(
            "ABC", InsoLogin("u", "p")
        )
    except InsoReadError as exc:
        assert exc.code == "AUTHENTICATED_READ_EMPTY"
    else:
        raise AssertionError("empty response must fail closed")


def test_concrete_browser_expired_session_is_identified_without_rows() -> None:
    captured: dict = {}
    page = FakePage('{"isLogin":"false"}', captured)
    acquisition = PlaywrightInsoReadOnlyBrowser(
        InsoBrowserConfig(login_url="https://inso.example/"),
        settle_ms=0,
        operation_access=FakeOperationAccess(page),
    )

    with pytest.raises(InsoReadError) as caught:
        acquisition.fetch_procurement_temporary_inquiry_history(
            "ABC", InsoLogin("u", "p")
        )
    assert caught.value.code == "AUTHENTICATED_SESSION_REQUIRED"
    assert page.closed


def test_concrete_browser_without_explicit_lease_fails_closed() -> None:
    acquisition = PlaywrightInsoReadOnlyBrowser(
        InsoBrowserConfig(login_url="https://inso.example/"),
        settle_ms=0,
    )

    with pytest.raises(InsoReadError) as caught:
        acquisition.fetch_procurement_temporary_inquiry_history(
            "ABC", InsoLogin("u", "p")
        )
    assert caught.value.code == "VERIFIED_SESSION_LEASE_REQUIRED"


def test_browser_config_validates_https_and_loopback_cdp() -> None:
    try:
        InsoBrowserConfig("http://inso.example", cdp_url="http://127.0.0.1:9222")
    except ValueError:
        pass
    else:
        raise AssertionError("non-HTTPS INSO endpoint must be rejected")

    try:
        InsoBrowserConfig(
            "https://inso.example/",
            cdp_url="https://attacker.example/remote",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("non-loopback CDP must be rejected")

    try:
        InsoBrowserConfig("https://inso.example/", cdp_url="http://127.0.0.1:9222", pagesize=0)
    except ValueError:
        pass
    else:
        raise AssertionError("non-positive pagesize must be rejected")
