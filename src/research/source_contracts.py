"""Website-agnostic source and evidence contracts owned by Research."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum


class ResearchSource(str, Enum):
    """Stable identifiers for the confirmed V1 Research sources."""

    IC_NET = "ic.net"
    FINDCHIPS = "findchips"
    HQEW = "hqew"
    LCSC = "lcsc"
    BOM_AI = "bom.ai"
    INSO = "inso"


PRICE_SOURCES: tuple[ResearchSource, ...] = (
    ResearchSource.FINDCHIPS,
    ResearchSource.HQEW,
    ResearchSource.LCSC,
    ResearchSource.BOM_AI,
    ResearchSource.INSO,
)


class SourceOutcome(str, Enum):
    """Business/technical outcome for one completed source attempt."""

    SUCCESS = "SUCCESS"
    NO_STRICT_MPN_MATCH = "NO_STRICT_MPN_MATCH"
    NO_VALID_PRICE = "NO_VALID_PRICE"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


class MpnMatchKind(str, Enum):
    EXACT = "EXACT"
    SUFFIX = "SUFFIX"


def is_strict_mpn_match(target_mpn: str, observed_mpn: str) -> bool:
    """IC.net match: trim edges and ignore case, with no suffix allowance."""

    return target_mpn.strip().casefold() == observed_mpn.strip().casefold()


def price_source_mpn_match(
    target_mpn: str, observed_mpn: str
) -> MpnMatchKind | None:
    """Match an exact MPN or the full MPN plus a <=5 character tail suffix."""

    target = target_mpn.strip()
    observed = observed_mpn.strip()
    folded_target = target.casefold()
    folded_observed = observed.casefold()
    if folded_observed == folded_target:
        return MpnMatchKind.EXACT
    if not folded_observed.startswith(folded_target):
        return None
    suffix_length = len(observed) - len(target)
    return MpnMatchKind.SUFFIX if 1 <= suffix_length <= 5 else None


def calendar_month_cutoff(now: datetime, months: int = 1) -> datetime:
    """Return the same wall-clock time N calendar months earlier, clamped."""

    if months < 1:
        raise ValueError("months must be positive")
    absolute_month = now.year * 12 + now.month - 1 - months
    year, zero_based_month = divmod(absolute_month, 12)
    month = zero_based_month + 1
    day = min(now.day, monthrange(year, month)[1])
    return now.replace(year=year, month=month, day=day)


EvidenceValue = str | int | bool | Decimal | date | datetime | None


@dataclass(frozen=True, slots=True)
class EvidenceField:
    key: str
    value: EvidenceValue


@dataclass(frozen=True, slots=True)
class PriceCandidate:
    """One adapter-selected price normalized to RMB for aggregation."""

    source: ResearchSource
    matched_mpn: str
    raw_price: Decimal
    raw_currency: str
    normalized_rmb_price: Decimal
    captured_at: datetime
    source_url: str | None = None
    display_mpn: str | None = None
    age_months: int = 1

    def __post_init__(self) -> None:
        if self.source not in PRICE_SOURCES:
            raise ValueError("only confirmed price sources may produce PriceCandidate")
        for name, value in (
            ("raw_price", self.raw_price),
            ("normalized_rmb_price", self.normalized_rmb_price),
        ):
            if not isinstance(value, Decimal):
                raise TypeError(f"{name} must be Decimal")
            if not value.is_finite() or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if self.age_months not in {1, 2, 3}:
            raise ValueError("age_months must be 1, 2, or 3")


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    source: ResearchSource
    query_mpn: str
    matched_mpn: str | None
    outcome: SourceOutcome
    captured_at: datetime
    source_url: str | None = None
    fields: tuple[EvidenceField, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceResult:
    """Result of one source, separating normal and out-of-stock candidates."""

    source: ResearchSource
    outcome: SourceOutcome
    evidence: SourceEvidence
    price_candidate: PriceCandidate | None = None
    out_of_stock_candidate: PriceCandidate | None = None

    def __post_init__(self) -> None:
        if self.evidence.source is not self.source:
            raise ValueError("evidence source must match result source")
        if self.evidence.outcome is not self.outcome:
            raise ValueError("evidence outcome must match result outcome")
        candidates = tuple(
            candidate
            for candidate in (self.price_candidate, self.out_of_stock_candidate)
            if candidate is not None
        )
        if candidates and self.outcome is not SourceOutcome.SUCCESS:
            raise ValueError("only a successful source result may carry price candidates")
        for candidate in candidates:
            if candidate.source is not self.source:
                raise ValueError("price candidate source must match result source")
        if self.out_of_stock_candidate is not None and self.source not in {
            ResearchSource.FINDCHIPS,
            ResearchSource.LCSC,
        }:
            raise ValueError("only Findchips and LCSC may carry out-of-stock prices")


def money_text(value: Decimal) -> str:
    """Render a price for human-readable display: max 4 decimals, strip trailing zeros."""
    capped = value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    text = format(capped, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text if text else "0"


def format_source_result(result: SourceResult) -> str:
    """Render business-only source cell content for the Excel snapshot."""

    lines: list[str] = []
    if result.price_candidate is not None:
        candidate = result.price_candidate
        text = money_text(candidate.normalized_rmb_price)
        notes: list[str] = []
        if candidate.source is ResearchSource.INSO and candidate.age_months > 1:
            notes.append("两个月" if candidate.age_months == 2 else "三个月")
        elif candidate.display_mpn:
            notes.append(candidate.display_mpn)
        if notes:
            text += f"（{'，'.join(notes)}）"
        lines.append(text)
    if result.out_of_stock_candidate is not None:
        candidate = result.out_of_stock_candidate
        notes = ["无库存"]
        if candidate.display_mpn:
            notes.append(candidate.display_mpn)
        lines.append(
            f"{money_text(candidate.normalized_rmb_price)}（{'，'.join(notes)}）"
        )
    return "\n".join(lines) if lines else "无结果"
