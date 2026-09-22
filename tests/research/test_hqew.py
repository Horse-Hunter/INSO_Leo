from datetime import UTC, datetime
from decimal import Decimal

from src.research.hqew import (
    HqewAdapter,
    HqewPage,
    HqewPageUnavailable,
    parse_hqew_offers,
)
from src.research.source_contracts import SourceOutcome

NOW = datetime(2026, 9, 22, tzinfo=UTC)


def _row(mpn: str, price: str) -> str:
    return f'<input class="list-data" pmodel="{mpn}" quotationPrice="{price}">'


class Client:
    def __init__(self, html: str) -> None:
        self.html = html

    def fetch_first_page(self, mpn: str) -> HqewPage:
        return HqewPage(self.html, f"https://p.hqew.com/yunquote/{mpn}.html?y4=1", NOW)


class Blocked:
    def fetch_first_page(self, mpn: str) -> HqewPage:
        raise HqewPageUnavailable("INTERACTIVE_CHALLENGE_REQUIRED")


def test_parser_and_adapter_use_strict_lowest_rmb_offer() -> None:
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
    assert result.price_candidate.raw_price == Decimal("2.10")
    assert result.price_candidate.normalized_rmb_price == Decimal("2.10")


def test_challenge_fails_closed() -> None:
    result = HqewAdapter(Blocked()).search("ABC", 1)
    assert result.outcome is SourceOutcome.SOURCE_UNAVAILABLE
    assert result.price_candidate is None
