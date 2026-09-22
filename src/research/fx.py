"""Research-owned USD/RMB foreign-exchange boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True)
class UsdRmbQuote:
    """One quote oriented as 1 USD equals the rate in RMB/CNY."""

    rate: Decimal
    captured_at: datetime
    source_label: str
    base_currency: str = "USD"
    quote_currency: str = "RMB"

    def __post_init__(self) -> None:
        if not isinstance(self.rate, Decimal):
            raise TypeError("rate must be Decimal")
        if self.rate <= 0:
            raise ValueError("rate must be greater than zero")
        if self.base_currency != "USD":
            raise ValueError("base_currency must be USD")
        if self.quote_currency not in {"RMB", "CNY"}:
            raise ValueError("quote_currency must be RMB or CNY")
        if not self.source_label.strip():
            raise ValueError("source_label must not be blank")


class UsdRmbProvider(Protocol):
    """Supply one approved quote without defining a live FX source."""

    def get_quote(self) -> UsdRmbQuote:
        """Return a positive Decimal quote oriented from USD to RMB/CNY."""
