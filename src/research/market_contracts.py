"""Read-only Research message payloads; no sessions, providers or authority."""
from dataclasses import dataclass, field, fields
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from math import isfinite

from .icnet import IcNetResult
from .source_contracts import (
    EvidenceField,
    PriceCandidate,
    ResearchSource,
    SourceEvidence,
    SourceOutcome,
    SourceResult,
)
from .tp import TpOffer


class MarketReadMode(str, Enum):
    ORDINARY = "ordinary"
    TP_OFFERS = "tp_offers"


@dataclass(frozen=True, slots=True)
class MarketReadQuery:
    source: ResearchSource
    mode: MarketReadMode
    mpn: str = field(repr=False)
    quantity: int | float
    reference_at: datetime
    brand: str | None = field(default=None, repr=False)

    def __post_init__(self):
        if (not isinstance(self.source, ResearchSource) or self.source is ResearchSource.INSO
                or not isinstance(self.mode, MarketReadMode)):
            raise ValueError("MARKET_QUERY_SOURCE_OR_MODE_INVALID")
        if (not isinstance(self.mpn, str) or not self.mpn.strip() or len(self.mpn) > 256
                or self.brand is not None and (not isinstance(self.brand, str) or len(self.brand) > 256)
                or isinstance(self.quantity, bool) or not isinstance(self.quantity, (int, float))
                or not isfinite(self.quantity) or self.quantity <= 0
                or not isinstance(self.reference_at, datetime) or self.reference_at.utcoffset() is None):
            raise ValueError("MARKET_QUERY_PARAMETERS_INVALID")


def _immutable_payload(value, depth=0):
    # Exact canonical frozen types only. Never admit arbitrary dataclasses,
    # mutable evidence values, exceptions, callbacks, or Playwright proxies.
    if depth > 12:
        raise ValueError("MARKET_PAYLOAD_TOO_DEEP")
    if value is None or type(value) in {bool, int, str, date, datetime, Decimal, float}:
        if isinstance(value, str) and len(value) > 8192:
            raise ValueError("MARKET_PAYLOAD_TOO_LARGE")
        if isinstance(value, (float, Decimal)) and not isfinite(value):
            raise ValueError("MARKET_PAYLOAD_NONFINITE")
        return
    if type(value) in {ResearchSource, SourceOutcome}:
        return
    if type(value) is tuple and len(value) <= 128:
        for child in value:
            _immutable_payload(child, depth + 1)
        return
    if type(value) in {IcNetResult, SourceResult, SourceEvidence, EvidenceField, PriceCandidate, TpOffer}:
        for entry in fields(value):
            _immutable_payload(getattr(value, entry.name), depth + 1)
        return
    raise ValueError("MARKET_PAYLOAD_NOT_CANONICAL_IMMUTABLE")


@dataclass(frozen=True, slots=True)
class MarketReadResult:
    source: ResearchSource
    mode: MarketReadMode
    ordinary: SourceResult | IcNetResult | None = field(default=None, repr=False)
    offers: tuple[TpOffer, ...] | None = field(default=None, repr=False)
    icnet_context: IcNetResult | None = field(default=None, repr=False)

    def __post_init__(self):
        if (not isinstance(self.source, ResearchSource) or self.source is ResearchSource.INSO
                or not isinstance(self.mode, MarketReadMode)):
            raise ValueError("MARKET_RESULT_SOURCE_OR_MODE_INVALID")
        if self.mode is MarketReadMode.ORDINARY:
            expected = IcNetResult if self.source is ResearchSource.IC_NET else SourceResult
            if type(self.ordinary) is not expected or self.offers is not None or self.icnet_context is not None:
                raise ValueError("MARKET_RESULT_SHAPE_INVALID")
            result = self.ordinary.source_result if expected is IcNetResult else self.ordinary
            if result.source is not self.source:
                raise ValueError("MARKET_RESULT_SOURCE_MISMATCH")
        elif (self.ordinary is not None or type(self.offers) is not tuple
              or any(type(offer) is not TpOffer or offer.source is not self.source for offer in self.offers)):
            raise ValueError("MARKET_RESULT_SHAPE_INVALID")
        if self.icnet_context is not None and (
                self.mode is not MarketReadMode.TP_OFFERS or self.source is not ResearchSource.IC_NET
                or type(self.icnet_context) is not IcNetResult
                or self.icnet_context.source_result.source is not self.source):
            raise ValueError("MARKET_RESULT_ICNET_CONTEXT_INVALID")
        _immutable_payload(self.icnet_context)
        _immutable_payload(self.ordinary)
        _immutable_payload(self.offers)
