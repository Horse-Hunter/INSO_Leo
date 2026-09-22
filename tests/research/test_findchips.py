from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.research.findchips import (
    FindchipsAdapter,
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
from src.research.source_contracts import ResearchSource, SourceOutcome

CAPTURED_AT = datetime(2026, 9, 22, 9, 0, tzinfo=UTC)
FX_CAPTURED_AT = datetime(2026, 9, 22, 8, 30, tzinfo=UTC)
FIXTURE = Path(__file__).parent / "fixtures" / "findchips_results_minimal.html"


class FakeClient:
    def __init__(self, html: str) -> None:
        self.html = html
        self.queries: list[str] = []

    def fetch_first_page(self, mpn: str) -> FindchipsPage:
        self.queries.append(mpn)
        return FindchipsPage(
            html=self.html,
            url=build_findchips_search_url(mpn),
            captured_at=CAPTURED_AT,
        )


class UnavailableClient:
    def fetch_first_page(self, mpn: str) -> FindchipsPage:
        raise FindchipsPageUnavailable(
            "HTTP_REQUEST_FAILED",
            build_findchips_search_url(mpn),
        )


class FixedFxProvider:
    def get_quote(self) -> UsdRmbQuote:
        return UsdRmbQuote(
            rate=Decimal("7.10"),
            captured_at=FX_CAPTURED_AT,
            source_label="synthetic-test-only",
        )


class FailingFxProvider:
    def get_quote(self) -> UsdRmbQuote:
        raise RuntimeError("synthetic provider failure")


class InvalidFxProvider:
    def get_quote(self) -> object:
        return object()


def _fields(result: object) -> dict[str, object]:
    source_result = result
    return {
        field.key: field.value  # type: ignore[attr-defined]
        for field in source_result.evidence.fields  # type: ignore[attr-defined]
    }


def _page_html(*rows: str) -> str:
    return (
        '<html><body><section class="distributor-results"><table>'
        + "".join(rows)
        + "</table></section></body></html>"
    )


def _row_html(
    mpn: str,
    stock: str | None,
    tiers: str,
    *,
    extra: str = "",
) -> str:
    stock_attr = "" if stock is None else f' data-instock="{stock}"'
    return (
        f'<tr data-mfrpartnumber="{mpn}"{stock_attr} '
        f"data-price='{tiers}' {extra}></tr>"
    )


def _tier(quantity: int, price: str, currency: str = "USD") -> FindchipsPriceTier:
    return FindchipsPriceTier(quantity, Decimal(price), currency)


def test_build_search_url_strips_edges_only() -> None:
    assert build_findchips_search_url("  Ab c-1  ") == (
        "https://www.findchips.com/search/Ab%20c-1"
    )


def test_fixture_parser_keeps_only_safe_offer_facts() -> None:
    rows = parse_findchips_offers(FIXTURE.read_text(encoding="utf-8"))

    assert len(rows) == 8
    assert rows[0].mpn == "ABC-123"
    assert rows[0].stock_positive is True
    assert rows[0].tiers[1] == FindchipsPriceTier(
        break_quantity=10,
        unit_price=Decimal("8.00"),
        currency="USD",
    )
    assert rows[3].stock_positive is False
    assert rows[4].stock_positive is None
    assert rows[7].mpn == "ABC-123-T"
    assert not hasattr(rows[0], "stock_quantity")
    assert not hasattr(rows[0], "moq")
    assert "1000" not in repr(rows[0])


def test_parser_fails_closed_on_missing_container_or_bad_tiers() -> None:
    with pytest.raises(FindchipsParseError, match="RESULT_CONTAINER_MISSING"):
        parse_findchips_offers("<html><body></body></html>")

    bad = _page_html(
        _row_html("ABC-123", "1", "not-json"),
    )
    with pytest.raises(FindchipsParseError, match="PRICE_TIERS_UNPARSEABLE"):
        parse_findchips_offers(bad)


@pytest.mark.parametrize(
    ("customer_quantity", "expected_break", "expected_price"),
    [
        (1, 1, Decimal("10.00")),
        (10, 10, Decimal("8.00")),
        (50, 10, Decimal("8.00")),
        (100, 100, Decimal("6.00")),
    ],
)
def test_applicable_tier_uses_greatest_break_not_exceeding_quantity(
    customer_quantity: int,
    expected_break: int,
    expected_price: Decimal,
) -> None:
    tiers = (
        _tier(1, "10.00"),
        _tier(10, "8.00"),
        _tier(100, "6.00"),
    )

    selected = select_applicable_tier(tiers, customer_quantity)

    assert selected is not None
    assert selected.break_quantity == expected_break
    assert selected.unit_price == expected_price


def test_applicable_tier_rejects_higher_break_and_non_usd() -> None:
    assert select_applicable_tier((_tier(3000, "0.01"),), 10) is None
    assert select_applicable_tier((_tier(1, "0.01", "EUR"),), 10) is None


def test_moq_and_price_range_do_not_replace_applicable_tier() -> None:
    offers = parse_findchips_offers(FIXTURE.read_text(encoding="utf-8"))

    selected = select_applicable_tier(offers[0].tiers, 50)

    assert selected is not None
    assert selected.unit_price == Decimal("8.00")
    assert selected.unit_price != Decimal("1.00")
    assert not hasattr(offers[0], "moq")


def test_lowest_price_requires_strict_mpn_and_positive_stock_only() -> None:
    offers = parse_findchips_offers(FIXTURE.read_text(encoding="utf-8"))

    selection = select_lowest_valid_price(offers, " abc-123 ", 50)

    assert selection is not None
    matched_mpn, tier = selection
    assert matched_mpn == "ABC-123"
    assert tier.unit_price == Decimal("7.25")
    assert tier.break_quantity == 1


def test_suffix_offer_never_wins_even_when_cheaper() -> None:
    offers = (
        FindchipsOffer("ABC-123", True, (_tier(1, "5.00"),)),
        FindchipsOffer("ABC-123-T", True, (_tier(1, "0.01"),)),
    )

    selection = select_lowest_valid_price(offers, "ABC-123", 1)

    assert selection is not None
    assert selection[0] == "ABC-123"
    assert selection[1].unit_price == Decimal("5.00")


def test_successful_adapter_builds_decimal_price_candidate_and_safe_evidence() -> None:
    client = FakeClient(FIXTURE.read_text(encoding="utf-8"))
    result = FindchipsAdapter(client, FixedFxProvider()).search(" ABC-123 ", 50)
    fields = _fields(result)

    assert client.queries == [" ABC-123 "]
    assert result.source is ResearchSource.FINDCHIPS
    assert result.outcome is SourceOutcome.SUCCESS
    assert result.price_candidate is not None
    assert result.price_candidate.matched_mpn == "ABC-123"
    assert result.price_candidate.raw_price == Decimal("7.25")
    assert result.price_candidate.raw_currency == "USD"
    assert result.price_candidate.normalized_rmb_price == Decimal("51.4750")
    assert isinstance(result.price_candidate.raw_price, Decimal)
    assert isinstance(result.price_candidate.normalized_rmb_price, Decimal)
    assert result.price_candidate.captured_at == CAPTURED_AT
    assert fields["strict_mpn_offer_count"] == 7
    assert fields["positive_stock_strict_offer_count"] == 5
    assert fields["applicable_usd_price_offer_count"] == 3
    assert fields["selected_tier_break_quantity"] == 1
    assert fields["selected_raw_usd_price"] == Decimal("7.25")
    assert fields["fx_rate"] == Decimal("7.10")
    assert fields["fx_captured_at"] == FX_CAPTURED_AT
    assert fields["fx_source_label"] == "synthetic-test-only"
    assert fields["normalized_rmb_price"] == Decimal("51.4750")
    assert not any(
        "stock_quantity" in key or "moq" in key
        for key in fields
    )


def test_strict_match_without_eligible_price_is_no_valid_price() -> None:
    html = _page_html(
        _row_html("ABC-123", "0", '[[1,"USD","0.01"]]'),
        _row_html("ABC-123", "5", '[[3000,"USD","0.001"]]'),
        _row_html("ABC-123", "5", '[[1,"EUR","0.001"]]'),
    )

    result = FindchipsAdapter(FakeClient(html), FixedFxProvider()).search(
        "ABC-123",
        10,
    )

    assert result.outcome is SourceOutcome.NO_VALID_PRICE
    assert result.price_candidate is None
    assert _fields(result)["strict_mpn_offer_count"] == 3


def test_no_strict_match_is_distinct_from_no_valid_price() -> None:
    html = _page_html(
        _row_html("ABC-123-T", "5", '[[1,"USD","0.001"]]'),
    )

    result = FindchipsAdapter(FakeClient(html), FixedFxProvider()).search(
        "ABC-123",
        10,
    )

    assert result.outcome is SourceOutcome.NO_STRICT_MPN_MATCH
    assert result.price_candidate is None
    assert _fields(result)["strict_mpn_offer_count"] == 0


@pytest.mark.parametrize(
    ("client", "failure_code"),
    [
        (UnavailableClient(), "HTTP_REQUEST_FAILED"),
        (FakeClient("<html><body>blocked</body></html>"), "RESULT_CONTAINER_MISSING"),
    ],
)
def test_technical_failure_is_source_unavailable(
    client: object,
    failure_code: str,
) -> None:
    result = FindchipsAdapter(
        client,  # type: ignore[arg-type]
        FixedFxProvider(),
    ).search("ABC-123", 10)

    assert result.outcome is SourceOutcome.SOURCE_UNAVAILABLE
    assert result.price_candidate is None
    assert _fields(result)["failure_code"] == failure_code


@pytest.mark.parametrize(
    "provider",
    [FailingFxProvider(), InvalidFxProvider()],
)
def test_fx_provider_failure_or_invalid_quote_is_source_unavailable(
    provider: object,
) -> None:
    result = FindchipsAdapter(
        FakeClient(FIXTURE.read_text(encoding="utf-8")),
        provider,  # type: ignore[arg-type]
    ).search("ABC-123", 50)

    assert result.outcome is SourceOutcome.SOURCE_UNAVAILABLE
    assert result.price_candidate is None
    assert _fields(result)["failure_code"] == "FX_QUOTE_UNAVAILABLE"
