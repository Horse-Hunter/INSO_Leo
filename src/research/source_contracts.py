"""Website-agnostic source and evidence contracts owned by Research."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class ResearchSource(str, Enum):
    """Stable identifiers for the confirmed V1 Research sources."""

    IC_NET = "ic.net"
    FINDCHIPS = "findchips"
    HQEW = "hqew"
    LCSC = "lcsc"
    BOM_AI = "bom.ai"


PRICE_SOURCES: tuple[ResearchSource, ...] = (
    ResearchSource.FINDCHIPS,
    ResearchSource.HQEW,
    ResearchSource.LCSC,
    ResearchSource.BOM_AI,
)


class SourceOutcome(str, Enum):
    """Outcome of processing one source, before multi-source aggregation."""

    SUCCESS = "SUCCESS"
    NO_STRICT_MPN_MATCH = "NO_STRICT_MPN_MATCH"
    NO_VALID_PRICE = "NO_VALID_PRICE"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


def is_strict_mpn_match(target_mpn: str, observed_mpn: str) -> bool:
    """Compare MPNs after trimming edges and ignoring letter case only."""

    return target_mpn.strip().lower() == observed_mpn.strip().lower()


EvidenceValue = str | int | bool | Decimal | date | datetime | None


@dataclass(frozen=True, slots=True)
class EvidenceField:
    """One typed, source-specific observation captured as evidence."""

    key: str
    value: EvidenceValue


@dataclass(frozen=True, slots=True)
class PriceCandidate:
    """One adapter-selected price normalized for later aggregation."""

    source: ResearchSource
    matched_mpn: str
    raw_price: Decimal
    raw_currency: str
    normalized_rmb_price: Decimal
    captured_at: datetime
    source_url: str | None = None

    def __post_init__(self) -> None:
        if self.source not in PRICE_SOURCES:
            raise ValueError("only confirmed price sources may produce PriceCandidate")
        if not isinstance(self.raw_price, Decimal):
            raise TypeError("raw_price must be Decimal")
        if not isinstance(self.normalized_rmb_price, Decimal):
            raise TypeError("normalized_rmb_price must be Decimal")


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    """Structured provenance for one source-processing result."""

    source: ResearchSource
    query_mpn: str
    matched_mpn: str | None
    outcome: SourceOutcome
    captured_at: datetime
    source_url: str | None = None
    fields: tuple[EvidenceField, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceResult:
    """Result of one source, without mapping to a final ResearchStatus."""

    source: ResearchSource
    outcome: SourceOutcome
    evidence: SourceEvidence
    price_candidate: PriceCandidate | None = None

    def __post_init__(self) -> None:
        if self.evidence.source is not self.source:
            raise ValueError("evidence source must match result source")
        if self.evidence.outcome is not self.outcome:
            raise ValueError("evidence outcome must match result outcome")
        if self.price_candidate is None:
            return
        if self.outcome is not SourceOutcome.SUCCESS:
            raise ValueError(
                "only a successful source result may carry a price candidate"
            )
        if self.source not in PRICE_SOURCES:
            raise ValueError("only confirmed price sources may carry a price candidate")
        if self.price_candidate.source is not self.source:
            raise ValueError("price candidate source must match result source")
