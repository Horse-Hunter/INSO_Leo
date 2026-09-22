"""Read-only Findchips price adapter and server-rendered HTML parser."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from .fx import UsdRmbProvider, UsdRmbQuote
from .source_contracts import (
    EvidenceField,
    PriceCandidate,
    ResearchSource,
    SourceEvidence,
    SourceOutcome,
    SourceResult,
    is_strict_mpn_match,
)

FINDCHIPS_SEARCH_URL = "https://www.findchips.com/search/"
FINDCHIPS_USER_AGENT = "INSO-Leo-Research/1.0 (read-only Findchips adapter)"


class FindchipsError(RuntimeError):
    """Base class for safe Findchips acquisition and parsing failures."""

    def __init__(self, code: str, source_url: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.source_url = source_url


class FindchipsPageUnavailable(FindchipsError):
    """The approved HTTP path could not return a usable result page."""


class FindchipsParseError(FindchipsError):
    """The server-rendered result document could not be parsed reliably."""


@dataclass(frozen=True, slots=True)
class FindchipsPriceTier:
    """One displayed quantity-break unit-price tier."""

    break_quantity: int
    unit_price: Decimal
    currency: str

    def __post_init__(self) -> None:
        if self.break_quantity <= 0:
            raise ValueError("break_quantity must be greater than zero")
        if not isinstance(self.unit_price, Decimal):
            raise TypeError("unit_price must be Decimal")
        if not self.unit_price.is_finite() or self.unit_price <= 0:
            raise ValueError("unit_price must be finite and greater than zero")
        if not self.currency.strip():
            raise ValueError("currency must not be blank")


@dataclass(frozen=True, slots=True)
class FindchipsOffer:
    """Minimum safe offer data; concrete stock and MOQ are intentionally absent."""

    mpn: str
    stock_positive: bool | None
    tiers: tuple[FindchipsPriceTier, ...] = ()


@dataclass(frozen=True, slots=True)
class FindchipsPage:
    """One in-memory Findchips search result capture."""

    html: str = field(repr=False)
    url: str
    captured_at: datetime


class FindchipsPageClient(Protocol):
    """Acquisition boundary replaced by fixtures in default tests."""

    def fetch_first_page(self, mpn: str) -> FindchipsPage:
        """Return one normal public Findchips search page."""


def build_findchips_search_url(mpn: str) -> str:
    """Build the normal search path after trimming edge whitespace only."""

    return f"{FINDCHIPS_SEARCH_URL}{quote(mpn.strip(), safe='')}"


def _is_findchips_response_url(url: str) -> bool:
    try:
        hostname = urlsplit(url).hostname
    except ValueError:
        return False
    if hostname is None:
        return False
    normalized = hostname.casefold()
    return normalized == "findchips.com" or normalized.endswith(".findchips.com")


class FindchipsHttpClient:
    """Bounded ordinary-HTTP client for one public Findchips search page."""

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self._timeout_seconds = timeout_seconds

    def fetch_first_page(self, mpn: str) -> FindchipsPage:
        target_url = build_findchips_search_url(mpn)
        request = Request(
            target_url,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": FINDCHIPS_USER_AGENT,
            },
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                response_url = response.geturl()
                if not _is_findchips_response_url(response_url):
                    raise FindchipsPageUnavailable(
                        "UNEXPECTED_RESPONSE_HOST",
                        response_url,
                    )
                if response.status != 200:
                    raise FindchipsPageUnavailable(
                        "HTTP_STATUS_UNEXPECTED",
                        response_url,
                    )
                if response.headers.get_content_type() != "text/html":
                    raise FindchipsPageUnavailable(
                        "CONTENT_TYPE_UNEXPECTED",
                        response_url,
                    )
                encoding = response.headers.get_content_charset() or "utf-8"
                html = response.read().decode(encoding, errors="replace")
                if not html.strip():
                    raise FindchipsPageUnavailable(
                        "EMPTY_RESPONSE",
                        response_url,
                    )
                return FindchipsPage(
                    html=html,
                    url=response_url,
                    captured_at=datetime.now(UTC),
                )
        except FindchipsPageUnavailable:
            raise
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise FindchipsPageUnavailable(
                "HTTP_REQUEST_FAILED",
                target_url,
            ) from error


def _parse_stock_presence(value: str | None) -> bool | None:
    if value is None:
        return None
    compact = value.replace(",", "").strip()
    if not compact.isdecimal():
        return None
    return int(compact) > 0


def _parse_tiers(value: str | None) -> tuple[FindchipsPriceTier, ...]:
    if value is None or not value.strip():
        return ()
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE") from error
    if not isinstance(payload, list):
        raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE")

    tiers: list[FindchipsPriceTier] = []
    for item in payload:
        if not isinstance(item, list) or len(item) != 3:
            raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE")
        raw_break, raw_currency, raw_price = item
        if isinstance(raw_break, bool):
            raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE")
        if isinstance(raw_break, int):
            break_quantity = raw_break
        elif isinstance(raw_break, str) and raw_break.isdecimal():
            break_quantity = int(raw_break)
        else:
            raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE")
        if not isinstance(raw_currency, str) or not isinstance(raw_price, str):
            raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE")
        try:
            unit_price = Decimal(raw_price)
        except InvalidOperation as error:
            raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE") from error
        try:
            tier = FindchipsPriceTier(
                break_quantity=break_quantity,
                unit_price=unit_price,
                currency=raw_currency.upper(),
            )
        except (TypeError, ValueError) as error:
            raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE") from error
        tiers.append(tier)
    return tuple(tiers)


class _FindchipsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.result_container_found = False
        self.offers: list[FindchipsOffer] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = dict(attrs)
        classes = frozenset((values.get("class") or "").split())
        if "distributor-results" in classes:
            self.result_container_found = True
        if tag != "tr" or values.get("data-mfrpartnumber") is None:
            return
        self.offers.append(
            FindchipsOffer(
                mpn=values["data-mfrpartnumber"] or "",
                stock_positive=_parse_stock_presence(values.get("data-instock")),
                tiers=_parse_tiers(values.get("data-price")),
            )
        )


def parse_findchips_offers(html: str) -> tuple[FindchipsOffer, ...]:
    """Parse safe offer facts without retaining stock quantities or raw HTML."""

    parser = _FindchipsParser()
    try:
        parser.feed(html)
    except FindchipsError:
        raise
    except Exception as error:
        raise FindchipsParseError("RESULT_DOCUMENT_UNPARSEABLE") from error
    if not parser.result_container_found:
        raise FindchipsParseError("RESULT_CONTAINER_MISSING")
    return tuple(parser.offers)


def select_applicable_tier(
    tiers: tuple[FindchipsPriceTier, ...],
    customer_quantity: int,
) -> FindchipsPriceTier | None:
    """Select the greatest displayed USD break at or below customer quantity."""

    eligible = [
        tier
        for tier in tiers
        if tier.currency == "USD" and tier.break_quantity <= customer_quantity
    ]
    if not eligible:
        return None
    greatest_break = max(tier.break_quantity for tier in eligible)
    return min(
        (tier for tier in eligible if tier.break_quantity == greatest_break),
        key=lambda tier: tier.unit_price,
    )


def select_lowest_valid_price(
    offers: tuple[FindchipsOffer, ...],
    target_mpn: str,
    customer_quantity: int,
) -> tuple[str, FindchipsPriceTier] | None:
    """Select the lowest applicable USD price from strict, stocked offers."""

    applicable: list[tuple[str, FindchipsPriceTier]] = []
    for offer in offers:
        if not is_strict_mpn_match(target_mpn, offer.mpn):
            continue
        if offer.stock_positive is not True:
            continue
        tier = select_applicable_tier(offer.tiers, customer_quantity)
        if tier is not None:
            applicable.append((offer.mpn, tier))
    if not applicable:
        return None
    return min(
        applicable,
        key=lambda selection: (
            selection[1].unit_price,
            selection[1].break_quantity,
            selection[0].casefold(),
        ),
    )


class FindchipsAdapter:
    """Build a Findchips source result using an injected USD/RMB quote."""

    def __init__(
        self,
        client: FindchipsPageClient,
        fx_provider: UsdRmbProvider,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client
        self._fx_provider = fx_provider
        self._clock = clock or (lambda: datetime.now(UTC))

    def _unavailable(
        self,
        target_mpn: str,
        code: str,
        *,
        captured_at: datetime | None = None,
        source_url: str | None = None,
        fields: tuple[EvidenceField, ...] = (),
    ) -> SourceResult:
        evidence = SourceEvidence(
            source=ResearchSource.FINDCHIPS,
            query_mpn=target_mpn,
            matched_mpn=None,
            outcome=SourceOutcome.SOURCE_UNAVAILABLE,
            captured_at=captured_at or self._clock(),
            source_url=source_url,
            fields=(EvidenceField("failure_code", code), *fields),
        )
        return SourceResult(
            source=ResearchSource.FINDCHIPS,
            outcome=SourceOutcome.SOURCE_UNAVAILABLE,
            evidence=evidence,
        )

    def search(self, target_mpn: str, customer_quantity: int) -> SourceResult:
        try:
            page = self._client.fetch_first_page(target_mpn)
        except FindchipsError as error:
            return self._unavailable(
                target_mpn,
                error.code,
                source_url=error.source_url,
            )

        try:
            offers = parse_findchips_offers(page.html)
        except FindchipsError as error:
            return self._unavailable(
                target_mpn,
                error.code,
                captured_at=page.captured_at,
                source_url=page.url,
            )

        strict_offers = [
            offer
            for offer in offers
            if is_strict_mpn_match(target_mpn, offer.mpn)
        ]
        if not strict_offers:
            evidence = SourceEvidence(
                source=ResearchSource.FINDCHIPS,
                query_mpn=target_mpn,
                matched_mpn=None,
                outcome=SourceOutcome.NO_STRICT_MPN_MATCH,
                captured_at=page.captured_at,
                source_url=page.url,
                fields=(
                    EvidenceField("inspected_offer_count", len(offers)),
                    EvidenceField("strict_mpn_offer_count", 0),
                ),
            )
            return SourceResult(
                source=ResearchSource.FINDCHIPS,
                outcome=SourceOutcome.NO_STRICT_MPN_MATCH,
                evidence=evidence,
            )

        positive_stock = [
            offer for offer in strict_offers if offer.stock_positive is True
        ]
        applicable = [
            (offer, tier)
            for offer in positive_stock
            if (tier := select_applicable_tier(offer.tiers, customer_quantity))
            is not None
        ]
        count_fields = (
            EvidenceField("inspected_offer_count", len(offers)),
            EvidenceField("strict_mpn_offer_count", len(strict_offers)),
            EvidenceField(
                "positive_stock_strict_offer_count",
                len(positive_stock),
            ),
            EvidenceField(
                "applicable_usd_price_offer_count",
                len(applicable),
            ),
            EvidenceField("customer_quantity", customer_quantity),
        )
        selection = select_lowest_valid_price(
            offers,
            target_mpn,
            customer_quantity,
        )
        if selection is None:
            evidence = SourceEvidence(
                source=ResearchSource.FINDCHIPS,
                query_mpn=target_mpn,
                matched_mpn=strict_offers[0].mpn,
                outcome=SourceOutcome.NO_VALID_PRICE,
                captured_at=page.captured_at,
                source_url=page.url,
                fields=count_fields,
            )
            return SourceResult(
                source=ResearchSource.FINDCHIPS,
                outcome=SourceOutcome.NO_VALID_PRICE,
                evidence=evidence,
            )

        matched_mpn, selected_tier = selection
        try:
            fx_quote = self._fx_provider.get_quote()
            if not isinstance(fx_quote, UsdRmbQuote):
                raise TypeError("FX provider returned an invalid quote")
        except Exception:  # noqa: BLE001 - external provider boundary
            return self._unavailable(
                target_mpn,
                "FX_QUOTE_UNAVAILABLE",
                captured_at=page.captured_at,
                source_url=page.url,
                fields=count_fields,
            )

        normalized_price = selected_tier.unit_price * fx_quote.rate
        evidence = SourceEvidence(
            source=ResearchSource.FINDCHIPS,
            query_mpn=target_mpn,
            matched_mpn=matched_mpn,
            outcome=SourceOutcome.SUCCESS,
            captured_at=page.captured_at,
            source_url=page.url,
            fields=(
                *count_fields,
                EvidenceField(
                    "selected_tier_break_quantity",
                    selected_tier.break_quantity,
                ),
                EvidenceField(
                    "selected_raw_usd_price",
                    selected_tier.unit_price,
                ),
                EvidenceField("fx_base_currency", fx_quote.base_currency),
                EvidenceField("fx_quote_currency", fx_quote.quote_currency),
                EvidenceField("fx_rate", fx_quote.rate),
                EvidenceField("fx_captured_at", fx_quote.captured_at),
                EvidenceField("fx_source_label", fx_quote.source_label),
                EvidenceField("normalized_rmb_price", normalized_price),
            ),
        )
        candidate = PriceCandidate(
            source=ResearchSource.FINDCHIPS,
            matched_mpn=matched_mpn,
            raw_price=selected_tier.unit_price,
            raw_currency="USD",
            normalized_rmb_price=normalized_price,
            captured_at=page.captured_at,
            source_url=page.url,
        )
        return SourceResult(
            source=ResearchSource.FINDCHIPS,
            outcome=SourceOutcome.SUCCESS,
            evidence=evidence,
            price_candidate=candidate,
        )
