from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.research.icnet import (
    BrandResolution,
    IcNetAdapter,
    IcNetLogin,
    IcNetPage,
    IcNetPageUnavailable,
    IcNetParseError,
    IcNetRow,
    classify_stock,
    extract_manufacturer_display,
    parse_icnet_rows,
    select_brand_by_frequency,
    sum_certified_stock,
)
from src.research.source_contracts import ResearchSource, SourceOutcome

CAPTURED_AT = datetime(2026, 9, 22, 8, 0, tzinfo=UTC)
FIXTURE = Path(__file__).parent / "fixtures" / "icnet_results_minimal.html"


class FakeClient:
    def __init__(self, html: str) -> None:
        self.html = html
        self.queries: list[str] = []

    def fetch_first_page(self, mpn: str) -> IcNetPage:
        self.queries.append(mpn)
        return IcNetPage(
            html=self.html,
            url=f"https://www.ic.net.cn/search/{mpn}.html?isExact=1",
            captured_at=CAPTURED_AT,
        )


class UnavailableClient:
    def fetch_first_page(self, mpn: str) -> IcNetPage:
        raise IcNetPageUnavailable("RESULT_PAGE_BLOCKED")


def _fields(result: object) -> dict[str, object]:
    source_result = result.source_result  # type: ignore[attr-defined]
    return {field.key: field.value for field in source_result.evidence.fields}


def _row_html(
    mpn: str,
    manufacturer: str,
    quantity: str = "1",
    certification: str = "",
) -> str:
    cert_html = f'<a class="{certification.lower()}"></a>' if certification else ""
    return f"""
      <li class="stair_tr">
        <div class="result_id">
          <span class="product_number"><a>{mpn}</a></span>
        </div>
        <div class="result_factory">{manufacturer}</div>
        <div class="result_totalNumber">{quantity}</div>
        <div class="result_supply"><p class="result_icons">{cert_html}</p></div>
      </li>
    """


def _page_html(*rows: str) -> str:
    return f'<html><body><div class="right_results"><ul>{"".join(rows)}</ul></div></body></html>'


def test_sanitized_fixture_parses_only_displayed_values() -> None:
    rows = parse_icnet_rows(FIXTURE.read_text(encoding="utf-8"))

    assert len(rows) == 4
    assert rows[0] == IcNetRow(
        mpn="ABC-123",
        manufacturer="Acme/艾克米",
        quantity=20,
        certifications=frozenset({"SSCP"}),
    )
    assert rows[1].quantity == 10
    assert rows[1].certifications == frozenset({"SSCP", "ICCP"})
    assert rows[2].quantity == 5
    assert rows[2].certifications == frozenset({"ICCP"})
    assert rows[3].mpn == "ABC-123-T"
    assert rows[3].quantity == 9999


@pytest.mark.parametrize(
    ("displayed", "expected"),
    [
        ("Analog Devices", "Analog Devices"),
        ("华芯", "华芯"),
        ("Telit/泰利特", "Telit"),
        ("德州仪器（TI）", "TI"),
        ("  NXP / 恩智浦  ", "NXP"),
        ("Alpha/Beta/阿尔法", None),
        ("", None),
        (None, None),
    ],
)
def test_manufacturer_display_extraction(
    displayed: str | None, expected: str | None
) -> None:
    assert extract_manufacturer_display(displayed) == expected


def test_brand_frequency_and_confirmed_tie_rules() -> None:
    assert select_brand_by_frequency(["Acme/艾克米", "Acme", "华芯"]).brand == "Acme"

    english_preferred = select_brand_by_frequency(["华芯", "VeryLongBrand"])
    assert english_preferred.brand == "VeryLongBrand"

    shorter_english = select_brand_by_frequency(["LongBrand", "TI"])
    assert shorter_english.brand == "TI"

    unresolved = select_brand_by_frequency(["AB", "CD"])
    assert unresolved == BrandResolution(
        brand=None,
        counts=(("AB", 1), ("CD", 1)),
        ambiguous_candidates=("AB", "CD"),
    )


def test_certified_stock_strict_match_and_both_certifications_count_once() -> None:
    rows = list(parse_icnet_rows(FIXTURE.read_text(encoding="utf-8")))

    assert sum_certified_stock(rows, " abc-123 ") == (35, 3)


def test_certified_stock_does_not_filter_by_brand() -> None:
    rows = [
        IcNetRow("ABC", "BrandA", 10, frozenset({"SSCP"})),
        IcNetRow("ABC", "BrandB", 20, frozenset({"ICCP"})),
    ]

    assert sum_certified_stock(rows, "abc") == (30, 2)


def test_qualified_unparseable_quantity_fails_closed() -> None:
    rows = [IcNetRow("ABC", "BrandA", None, frozenset({"SSCP"}))]

    with pytest.raises(IcNetParseError, match="QUALIFIED_QUANTITY_UNPARSEABLE"):
        sum_certified_stock(rows, "ABC")


def test_stock_label_includes_equality_in_low_stock() -> None:
    assert classify_stock(30, 10) == "货少"
    assert classify_stock(31, 10) == "货多"


def test_successful_adapter_result_has_evidence_and_no_price_candidate() -> None:
    client = FakeClient(FIXTURE.read_text(encoding="utf-8"))
    result = IcNetAdapter(client).search("ABC-123", None, 10)
    fields = _fields(result)

    assert client.queries == ["ABC-123"]
    assert result.source_result.source is ResearchSource.IC_NET
    assert result.source_result.outcome is SourceOutcome.SUCCESS
    assert result.source_result.price_candidate is None
    assert result.resolved_brand == "Acme"
    assert result.stock_label == "货多"
    assert fields["first_page_rows_inspected"] == 4
    assert fields["strict_mpn_rows"] == 3
    assert fields["brand_frequency_rows_used"] == 3
    assert fields["qualified_certified_rows"] == 3
    assert fields["certified_stock_total"] == 35
    assert fields["customer_quantity"] == 10
    assert fields["stock_threshold"] == 30
    assert fields["stock_label"] == "货多"
    assert fields["brand_source"] == "ic.net"


def test_provided_brand_is_preserved_and_not_frequency_replaced() -> None:
    result = IcNetAdapter(
        FakeClient(FIXTURE.read_text(encoding="utf-8"))
    ).search("ABC-123", "Owner Brand", 100)
    fields = _fields(result)

    assert result.resolved_brand == "Owner Brand"
    assert fields["brand_source"] == "input"
    assert fields["brand_frequency_rows_used"] == 0


def test_brand_frequency_uses_at_most_first_twenty_rows() -> None:
    rows = [
        _row_html("ABC", "LongBrand" if index < 10 else "TI")
        for index in range(20)
    ]
    rows.append(_row_html("ABC", "LongBrand"))
    result = IcNetAdapter(FakeClient(_page_html(*rows))).search("ABC", None, 1)

    assert result.resolved_brand == "TI"
    assert _fields(result)["brand_frequency_rows_used"] == 20


def test_no_strict_match_is_not_source_unavailability() -> None:
    html = _page_html(_row_html("ABC-123-T", "Acme", "99", "SSCP"))
    result = IcNetAdapter(FakeClient(html)).search("ABC-123", None, 10)

    assert result.source_result.outcome is SourceOutcome.NO_STRICT_MPN_MATCH
    assert result.resolved_brand is None
    assert result.stock_label is None
    assert result.source_result.evidence.matched_mpn is None


def test_bad_qualified_quantity_maps_to_source_unavailable() -> None:
    html = _page_html(_row_html("ABC", "Acme", "unknown", "SSCP"))
    result = IcNetAdapter(FakeClient(html)).search("ABC", None, 10)

    assert result.source_result.outcome is SourceOutcome.SOURCE_UNAVAILABLE
    assert _fields(result)["failure_code"] == "QUALIFIED_QUANTITY_UNPARSEABLE"


def test_unexpected_page_shape_and_client_failure_are_source_unavailable() -> None:
    bad_page = IcNetAdapter(FakeClient("<html><body>login</body></html>")).search(
        "ABC", None, 10
    )
    blocked = IcNetAdapter(UnavailableClient()).search("ABC", None, 10)

    assert bad_page.source_result.outcome is SourceOutcome.SOURCE_UNAVAILABLE
    assert _fields(bad_page)["failure_code"] == "RESULT_CONTAINER_MISSING"
    assert blocked.source_result.outcome is SourceOutcome.SOURCE_UNAVAILABLE
    assert _fields(blocked)["failure_code"] == "RESULT_PAGE_BLOCKED"


def test_login_repr_does_not_expose_secret_values() -> None:
    login = IcNetLogin("user-secret", "password-secret")

    rendered = repr(login)
    assert "user-secret" not in rendered
    assert "password-secret" not in rendered
