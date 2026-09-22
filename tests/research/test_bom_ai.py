from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.research.bom_ai import (
    BomAiAdapter,
    BomAiCapture,
    BomAiCredentialedClient,
    BomAiLogin,
    BomAiPriceRecord,
    BomAiRawPage,
    calendar_month_cutoff,
    parse_bom_ai_price_records,
)
from src.research.source_contracts import SourceOutcome

NOW = datetime(2026, 9, 22, 12, tzinfo=UTC)


class Client:
    def __init__(self, records: tuple[BomAiPriceRecord, ...]) -> None:
        self.records = records

    def fetch_price_records(self, mpn: str) -> BomAiCapture:
        return BomAiCapture(self.records, "https://www.bom.ai/search", NOW)


def cutoff(now: datetime) -> datetime:
    return now - timedelta(days=31)


def test_seven_day_window_wins_over_cheaper_month_price() -> None:
    records = (
        BomAiPriceRecord("ABC", Decimal(8), NOW - timedelta(days=2)),
        BomAiPriceRecord("ABC", Decimal(7), NOW - timedelta(days=6)),
        BomAiPriceRecord("ABC", Decimal(1), NOW - timedelta(days=20)),
    )
    result = BomAiAdapter(Client(records), cutoff, clock=lambda: NOW).search("ABC", 1)
    assert result.price_candidate is not None
    assert result.price_candidate.raw_price == Decimal(7)


def test_month_fallback_expiry_and_strict_no_match() -> None:
    month = BomAiAdapter(
        Client((BomAiPriceRecord("ABC", Decimal(2), NOW - timedelta(days=20)),)),
        cutoff,
        clock=lambda: NOW,
    ).search("ABC", 1)
    expired = BomAiAdapter(
        Client((BomAiPriceRecord("ABC", Decimal(1), NOW - timedelta(days=40)),)),
        cutoff,
        clock=lambda: NOW,
    ).search("ABC", 1)
    mismatch = BomAiAdapter(
        Client((BomAiPriceRecord("ABC-T", Decimal(1), NOW),)), cutoff, clock=lambda: NOW
    ).search("ABC", 1)
    assert (
        month.price_candidate is not None
        and month.price_candidate.raw_price == Decimal(2)
    )
    assert expired.outcome is SourceOutcome.NO_VALID_PRICE
    assert mismatch.outcome is SourceOutcome.NO_STRICT_MPN_MATCH


def test_login_repr_hides_secret() -> None:
    rendered = repr(BomAiLogin("user-secret", "password-secret", "company-secret"))
    assert "user-secret" not in rendered
    assert "password-secret" not in rendered
    assert "company-secret" not in rendered


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (
            datetime(2026, 3, 31, 9, 15, tzinfo=UTC),
            datetime(2026, 2, 28, 9, 15, tzinfo=UTC),
        ),
        (
            datetime(2024, 3, 31, 9, 15, tzinfo=UTC),
            datetime(2024, 2, 29, 9, 15, tzinfo=UTC),
        ),
        (
            datetime(2026, 1, 30, 9, 15, tzinfo=UTC),
            datetime(2025, 12, 30, 9, 15, tzinfo=UTC),
        ),
    ],
)
def test_calendar_month_cutoff_clamps_month_ends(
    now: datetime, expected: datetime
) -> None:
    assert calendar_month_cutoff(now) == expected


def test_authenticated_html_parser_uses_strict_page_identity_and_absolute_dates() -> (
    None
):
    html = """
    <h3>ABC-1</h3>
    <data><quotePrice>2.50</quotePrice><quoteDate>2026/9/21 14:30:40</quoteDate></data>
    <data><quotePrice>{{stock.Price}}</quotePrice><quoteDate>{{stock.Date}}</quoteDate></data>
    """

    records = parse_bom_ai_price_records(html, "abc-1")

    assert records == (
        BomAiPriceRecord(
            "abc-1",
            Decimal("2.50"),
            datetime(2026, 9, 21, 6, 30, 40, tzinfo=UTC),
        ),
    )
    assert parse_bom_ai_price_records(html, "ABC-1-T") == ()


def test_credentialed_client_uses_site_id_and_keeps_browser_injected() -> None:
    class Credentials:
        seen_site_id: str | None = None

        def get_login(self, site_id: str) -> BomAiLogin | None:
            self.seen_site_id = site_id
            return BomAiLogin("user-secret", "password-secret")

    class Browser:
        seen_login: BomAiLogin | None = None

        def fetch_price_page(self, mpn: str, login: BomAiLogin) -> BomAiRawPage:
            self.seen_login = login
            return BomAiRawPage(
                f"<h3>{mpn}</h3><data><quotePrice>1.25</quotePrice>"
                "<quoteDate>2026/9/22 08:00:00</quoteDate></data>",
                f"https://www.bom.ai/components-storage/{mpn}.html",
                NOW,
            )

    credentials = Credentials()
    browser = Browser()
    capture = BomAiCredentialedClient(credentials, browser).fetch_price_records("ABC")

    assert credentials.seen_site_id == "bom.ai"
    assert browser.seen_login is not None
    assert capture.records[0].unit_price_rmb == Decimal("1.25")
