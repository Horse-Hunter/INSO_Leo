"""Canonical detailed six-source acquisition, FX and ranking shared by TP and mail."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .fx import UsdRmbQuote
from .source_contracts import (
    EvidenceField,
    ResearchSource,
    SourceEvidence,
    SourceOutcome,
    calendar_month_cutoff,
)


@dataclass(frozen=True)
class TpOffer:
    source: ResearchSource
    mpn: str
    price: Decimal
    currency: str
    quoted_at: datetime | None
    current: bool
    stocked: bool = True


@dataclass(frozen=True)
class TpQuote:
    offer: TpOffer
    rmb: Decimal


@dataclass(frozen=True)
class TpSourceResult:
    source: ResearchSource
    outcome: SourceOutcome
    evidence: SourceEvidence
    quotes: tuple[TpQuote, ...] = ()
    months: int = 1


@dataclass(frozen=True)
class TpResearchResult:
    sources: tuple[TpSourceResult, ...]
    lowest: TpQuote | None
    second: TpQuote | None
    stock_label: str
    target_rmb: Decimal | None
    estimated_total: Decimal | None
    fx_rate: Decimal
    fallback: bool = False


class TpFx:
    """Same authoritative provider, one consistent conversion snapshot per TP run."""
    def __init__(self, provider, now):
        self.provider, self.now, self.quote, self.hkd = provider, now, None, None

    def convert(self, value, currency):
        if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
            raise ValueError("TP_PRICE_INVALID")
        if currency in {"RMB", "CNY"}:
            return value
        if self.quote is None:
            try:
                quote = self.provider.get_quote()
            except Exception:  # noqa: BLE001 - FX boundary; no provider text escapes
                raise ValueError("FX_QUOTE_UNAVAILABLE") from None
            if (not isinstance(quote, UsdRmbQuote) or quote.captured_at.tzinfo is None
                    or quote.captured_at.date() != self.now.date()):
                raise ValueError("FX_QUOTE_UNAVAILABLE")
            self.quote = quote
        if currency == "USD":
            return value * self.quote.rate
        if currency == "HKD":
            if self.hkd is None:
                try:
                    self.hkd = self.provider.get_hkd_rmb_rate()
                except Exception:  # noqa: BLE001 - FX boundary
                    raise ValueError("FX_QUOTE_UNAVAILABLE") from None
            if not isinstance(self.hkd, Decimal) or not self.hkd.is_finite() or self.hkd <= 0:
                raise ValueError("FX_QUOTE_UNAVAILABLE")
            return value * self.hkd
        raise ValueError("TP_CURRENCY_UNSUPPORTED")


def distinct_two(quotes):
    """Second means a distinct RMB unit price. Equal-price offers are ties."""
    selected = {}
    for q in sorted(quotes, key=lambda q: (q.rmb, q.offer.source.value,
                                           q.offer.quoted_at.isoformat() if q.offer.quoted_at else "",
                                           q.offer.mpn)):
        selected.setdefault(q.rmb, q)
    return tuple(selected.values())[:2]


def select_tp_offers(source, offers, *, query, now, fx):
    from .source_contracts import price_source_mpn_match
    valid = []
    matched = False
    for offer in offers:
        if offer.source is not source or price_source_mpn_match(query, offer.mpn) is None:
            continue
        matched = True
        if not isinstance(offer.price, Decimal) or not offer.price.is_finite() or offer.price <= 0:
            continue
        if offer.current:
            if offer.quoted_at is not None:
                raise ValueError("TP_CURRENT_DATE_CONFLICT")
        elif (offer.quoted_at is None or offer.quoted_at.tzinfo is None
              or not calendar_month_cutoff(now, 12) <= offer.quoted_at <= now):
            continue
        valid.append(TpQuote(offer, fx.convert(offer.price, offer.currency)))
    chosen = []
    months = 1
    for stocked in (True, False):
        pool = []
        for window in range(1, 13):
            cutoff = calendar_month_cutoff(now, window)
            pool = distinct_two(q for q in valid if q.offer.stocked is stocked
                                and (q.offer.current or q.offer.quoted_at >= cutoff))
            if len(pool) == 2:
                break
        chosen.extend(pool)
        if pool:
            months = max(months, window)
    outcome = (SourceOutcome.SUCCESS if chosen else SourceOutcome.NO_VALID_PRICE
               if matched else SourceOutcome.NO_STRICT_MPN_MATCH)
    return TpSourceResult(source, outcome, SourceEvidence(source, query, None, outcome, now),
                          tuple(chosen), months)


def collect_tp_offers(adapter, source, mpn, quantity, now):
    """Canonical raw acquisition; keeps projection/FX on the task owner."""
    offers = []
    if source is ResearchSource.FINDCHIPS:
        from .findchips import parse_findchips_offers
        page = adapter._client.fetch_first_page(mpn)
        for row in parse_findchips_offers(page.html, mpn):
            if row.stock_positive is None:
                continue
            for tier in row.tiers:
                if tier.currency in {"USD", "HKD"}:
                    offers.append(TpOffer(source, row.mpn, tier.unit_price, tier.currency,
                                          row.observed_at, row.observed_at is None,
                                          row.stock_positive))
    elif source is ResearchSource.HQEW:
        from .hqew import parse_hqew_offers
        page = adapter._client.fetch_first_page(mpn)
        offers = [TpOffer(source, row.mpn, row.unit_price_rmb, "RMB", row.observed_at,
                          row.observed_at is None)
                  for row in parse_hqew_offers(page.html, reference_at=page.captured_at)]
    elif source is ResearchSource.LCSC:
        from .lcsc import parse_lcsc_product
        page = adapter._client.fetch_product_page(mpn)
        product = page.product or parse_lcsc_product(page.html)
        stocked = bool(product.stock_quantity and product.stock_quantity > 0 and not product.is_preorder)
        offers = [TpOffer(source, product.mpn, tier.unit_price, tier.currency, None, True, stocked)
                  for tier in product.tiers if tier.currency in {"USD", "RMB", "CNY"}]
    elif source is ResearchSource.BOM_AI:
        capture = adapter._client.fetch_price_records(mpn)
        offers = [TpOffer(source, row.mpn, row.raw_price, row.currency,
                          None if row.is_current else row.observed_at, row.is_current)
                  for row in capture.records if row.currency_confirmed]
        if not offers and capture.records:
            return TpSourceResult(source, SourceOutcome.SOURCE_UNAVAILABLE,
                SourceEvidence(source, mpn, None, SourceOutcome.SOURCE_UNAVAILABLE, now,
                    fields=(EvidenceField("failure_code", "PRICE_CURRENCY_UNCONFIRMED"),)))
    elif source is ResearchSource.INSO:
        capture = adapter._client.fetch_history(mpn)
        offers = [TpOffer(source, row.mpn, row.price, row.currency, row.observed_at, False)
                  for row in capture.records if row.price.is_finite() and row.price > 0]
    else:
        raise ValueError("TP_SOURCE_UNSUPPORTED")
    return tuple(offers)


def collect_tp(adapter, source, mpn, quantity, now, fx):
    """Preserve ordinary TP behavior through the same acquisition and selector."""
    offers = collect_tp_offers(adapter, source, mpn, quantity, now)
    if isinstance(offers, TpSourceResult):
        return offers  # Existing typed currency-unconfirmed BOM outcome.
    return select_tp_offers(source, offers, query=mpn, now=now, fx=fx)


def execute_tp(service, task_id, order, now):
    continuation = service.begin_tp(task_id, order, now=now)
    while not continuation.ready:
        continuation.accept_owner(continuation.read_owner())
    return continuation.finish()


def finish_tp(order, icnet, results, *, target_rmb, fx):
    """Same canonical ranking, called once by the original task owner."""
    normal = [q for result in results for q in result.quotes if q.offer.stocked]
    fallback_pool = [q for result in results for q in result.quotes if not q.offer.stocked]
    fallback = bool(not normal and fallback_pool
                    and not any(r.outcome is SourceOutcome.SOURCE_UNAVAILABLE for r in results))
    pool = normal or (fallback_pool if fallback else [])
    ranked = distinct_two(pool)
    lowest, second = (ranked + (None, None))[:2]
    stock = getattr(icnet, "stock_label", None) or "待验证"
    return TpResearchResult(tuple(results), lowest, second, stock, target_rmb,
        lowest.rmb * order.quantity if lowest and order.quantity is not None else None,
        fx.quote.rate if fx.quote else Decimal(1), fallback)


@dataclass(frozen=True)
class DetailedOrder:
    """Report identity only; never an order-write capability. None stays unknown."""
    mpn: str
    brand: str | None = None
    quantity: int | None = None
    customer: str | None = None
    rfq_date: str | None = None
    sheet: str | None = None
    row: int | None = None
    target_price: None = None
    date_source: str | None = None
    spreadsheet: str | None = None


def icnet_detailed_result(result, fx):
    native = result.source_result
    candidate = native.price_candidate
    quotes = () if candidate is None else (TpQuote(TpOffer(native.source, candidate.matched_mpn,
        candidate.raw_price, candidate.raw_currency, None, True),
        fx.convert(candidate.raw_price, candidate.raw_currency)),)
    return TpSourceResult(native.source, native.outcome, native.evidence, quotes)


def dump_source(result):
    """Bounded confirmed quote facts only, no pages/HTML/credentials."""
    return {"source": result.source.value, "outcome": result.outcome.value, "months": result.months,
        "captured_at": result.evidence.captured_at.isoformat(),
        "quotes": [{"source": q.offer.source.value, "mpn": q.offer.mpn,
            "price": str(q.offer.price), "currency": q.offer.currency,
            "quoted_at": q.offer.quoted_at.isoformat() if q.offer.quoted_at else None,
            "current": q.offer.current, "stocked": q.offer.stocked, "rmb": str(q.rmb)} for q in result.quotes]}


def load_source(data, mpn):
    source, outcome = ResearchSource(data["source"]), SourceOutcome(data["outcome"])
    quotes = tuple(TpQuote(TpOffer(ResearchSource(q["source"]), q["mpn"], Decimal(q["price"]), q["currency"],
        datetime.fromisoformat(q["quoted_at"]) if q["quoted_at"] else None, q["current"], q["stocked"]), Decimal(q["rmb"]))
        for q in data["quotes"])
    return TpSourceResult(source, outcome, SourceEvidence(source, mpn, None, outcome,
        datetime.fromisoformat(data["captured_at"])), quotes, data["months"])
