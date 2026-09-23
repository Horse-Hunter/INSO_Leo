from datetime import UTC, datetime
from decimal import Decimal

from src.research.fx import UsdRmbQuote
from src.research.inso_history import (
    InsoCredentialedClient,
    InsoHistoryAdapter,
    InsoHistoryCapture,
    InsoHistoryRecord,
    InsoLogin,
    InsoReadError,
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
    assert credentials.site_id == "inso"
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
