from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.research.fx import UsdRmbQuote

CAPTURED_AT = datetime(2026, 9, 22, 9, 0, tzinfo=UTC)


def test_usd_rmb_quote_is_positive_decimal_and_immutable() -> None:
    quote = UsdRmbQuote(
        rate=Decimal("7.10"),
        captured_at=CAPTURED_AT,
        source_label="synthetic-test-only",
    )

    assert quote.base_currency == "USD"
    assert quote.quote_currency == "RMB"
    assert quote.rate == Decimal("7.10")
    with pytest.raises(FrozenInstanceError):
        quote.rate = Decimal("7.20")  # type: ignore[misc]


@pytest.mark.parametrize("rate", [Decimal("0"), Decimal("-1")])
def test_usd_rmb_quote_rejects_non_positive_rate(rate: Decimal) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        UsdRmbQuote(rate, CAPTURED_AT, "synthetic-test-only")


def test_usd_rmb_quote_rejects_float_rate() -> None:
    with pytest.raises(TypeError, match="Decimal"):
        UsdRmbQuote(7.1, CAPTURED_AT, "synthetic-test-only")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("base_currency", "EUR", "base_currency"),
        ("quote_currency", "EUR", "quote_currency"),
        ("source_label", "  ", "source_label"),
    ],
)
def test_usd_rmb_quote_validates_orientation_and_provenance(
    field: str,
    value: str,
    message: str,
) -> None:
    values = {
        "rate": Decimal("7.10"),
        "captured_at": CAPTURED_AT,
        "source_label": "synthetic-test-only",
        "base_currency": "USD",
        "quote_currency": "RMB",
    }
    values[field] = value

    with pytest.raises(ValueError, match=message):
        UsdRmbQuote(**values)  # type: ignore[arg-type]
