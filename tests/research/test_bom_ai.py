from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src import research
from src.research.bom_ai import (
    BomAiAdapter,
    BomAiCapture,
    BomAiCredentialedClient,
    BomAiLogin,
    BomAiPriceRecord,
    BomAiRawPage,
    parse_bom_ai_price_records,
)
from src.research.fx import UsdRmbQuote
from src.research.source_contracts import (
    SourceOutcome,
    calendar_month_cutoff,
    format_source_result,
)

NOW = datetime(2026, 9, 22, 12, tzinfo=UTC)


class Client:
    def __init__(self, records: tuple[BomAiPriceRecord, ...]) -> None:
        self.records = records

    def fetch_price_records(self, mpn: str) -> BomAiCapture:
        return BomAiCapture(self.records, "https://www.bom.ai/search", NOW)


class Fx:
    def get_quote(self) -> UsdRmbQuote:
        return UsdRmbQuote(Decimal(7), NOW, "synthetic-test-only")


def test_one_natural_month_minimum_has_no_seven_day_preference() -> None:
    records = (
        BomAiPriceRecord("ABC", Decimal(8), NOW - timedelta(days=2)),
        BomAiPriceRecord("ABC", Decimal(7), NOW - timedelta(days=6)),
        BomAiPriceRecord("ABC", Decimal(1), NOW - timedelta(days=20)),
    )
    result = BomAiAdapter(Client(records), clock=lambda: NOW).search("ABC", 1)
    assert result.price_candidate is not None
    assert result.price_candidate.raw_price == Decimal(1)


def test_suffix_match_expiry_and_overlong_suffix() -> None:
    suffix = BomAiAdapter(
        Client((BomAiPriceRecord("ABC-T", Decimal(2), NOW),)),
        clock=lambda: NOW,
    ).search("ABC", 1)
    expired = BomAiAdapter(
        Client((BomAiPriceRecord("ABC", Decimal(1), NOW - timedelta(days=40)),)),
        clock=lambda: NOW,
    ).search("ABC", 1)
    mismatch = BomAiAdapter(
        Client((BomAiPriceRecord("ABC-ABCDEF", Decimal(1), NOW),)),
        clock=lambda: NOW,
    ).search("ABC", 1)
    assert suffix.price_candidate is not None
    assert format_source_result(suffix) == "2（ABC-T）"
    assert expired.outcome is SourceOutcome.NO_VALID_PRICE
    assert mismatch.outcome is SourceOutcome.NO_STRICT_MPN_MATCH


@pytest.mark.parametrize(
    ("now", "months", "expected"),
    [
        (
            datetime(2026, 3, 31, 9, 15, tzinfo=UTC),
            1,
            datetime(2026, 2, 28, 9, 15, tzinfo=UTC),
        ),
        (
            datetime(2024, 3, 31, 9, 15, tzinfo=UTC),
            1,
            datetime(2024, 2, 29, 9, 15, tzinfo=UTC),
        ),
        (
            datetime(2026, 3, 31, 9, 15, tzinfo=UTC),
            2,
            datetime(2026, 1, 31, 9, 15, tzinfo=UTC),
        ),
    ],
)
def test_calendar_month_cutoff_clamps_month_ends(
    now: datetime, months: int, expected: datetime
) -> None:
    assert calendar_month_cutoff(now, months) == expected


def test_parser_binds_quotes_to_matching_model_section_and_detects_currency() -> None:
    html = """
    <div><data><quotePrice>0.01</quotePrice><quoteDate>2026/9/22 08:00:00</quoteDate></data></div>
    <h3>OTHER</h3>
    <data><quotePrice>0.02</quotePrice><quoteDate>2026/9/22 08:00:00</quoteDate></data>
    <h3>ABC-1-T</h3>
    <data><quotePrice>$1.25</quotePrice><quoteDate>2026/9/21 14:30:40</quoteDate></data>
    <data><quotePrice>¥8.50</quotePrice><quoteDate>2026/9/20 14:30:40</quoteDate></data>
    <h3>AFTER</h3>
    <data><quotePrice>0.03</quotePrice><quoteDate>2026/9/22 08:00:00</quoteDate></data>
    """
    records = parse_bom_ai_price_records(html, "ABC-1")
    assert [(record.mpn, record.raw_price, record.currency) for record in records] == [
        ("ABC-1-T", Decimal("1.25"), "USD"),
        ("ABC-1-T", Decimal("8.50"), "RMB"),
    ]

    result = BomAiAdapter(
        Client(records), fx_provider=Fx(), clock=lambda: NOW
    ).search("ABC-1", 1)
    assert result.price_candidate is not None
    assert result.price_candidate.normalized_rmb_price == Decimal("8.50")
    assert result.price_candidate.raw_currency == "RMB"


def test_parser_reads_target_model_from_real_cloud_row_shape() -> None:
    html = """
    <div class="bom_cloud_block">
      <aside class="stock-view"><div class="model" title="OTHER"></div>
        <script><data><quotePrice>0.01</quotePrice>
        <quoteDate>2026/9/24 9:08:04</quoteDate></data></script></aside>
      <aside class="stock-view"><div class="model znl_quote_model-cell"
        title="STM32F103C8T6"></div><script class="metadata">
        <data><quotePrice>5.495575</quotePrice>
        <quoteDate>2026/9/24 9:08:04</quoteDate></data></script></aside>
    </div>
    """
    records = parse_bom_ai_price_records(html, "STM32F103C8T6")
    assert len(records) == 1
    assert records[0].raw_price == Decimal("5.495575")


def test_login_repr_hides_secret_and_client_only_exposes_read_capture() -> None:
    rendered = repr(BomAiLogin("user-secret", "password-secret", "company-secret"))
    assert "secret" not in rendered

    class Credentials:
        seen_site_id: str | None = None

        def get_login(self, site_id: str) -> BomAiLogin | None:
            self.seen_site_id = site_id
            return BomAiLogin("user-secret", "password-secret")

    class Browser:
        def fetch_price_page(self, mpn: str, login: BomAiLogin) -> BomAiRawPage:
            return BomAiRawPage(
                f"<h3>{mpn}</h3><data><quotePrice>1.25</quotePrice>"
                "<quoteDate>2026/9/22 08:00:00</quoteDate></data>",
                f"https://www.bom.ai/components-storage/{mpn}.html",
                NOW,
            )

    credentials = Credentials()
    capture = BomAiCredentialedClient(credentials, Browser()).fetch_price_records(
        "ABC"
    )
    assert credentials.seen_site_id == "bom.ai"
    assert capture.records[0].unit_price_rmb == Decimal("1.25")


def test_raw_currency_selector_is_not_a_package_public_api() -> None:
    assert not hasattr(research, "select_bom_ai_price")
