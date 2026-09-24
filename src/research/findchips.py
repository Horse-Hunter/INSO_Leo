"""Read-only Findchips price adapter and server-rendered HTML parser."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from .fx import UsdRmbProvider, UsdRmbQuote
from .source_contracts import (
    EvidenceField,
    MpnMatchKind,
    PriceCandidate,
    ResearchSource,
    SourceEvidence,
    SourceOutcome,
    SourceResult,
    calendar_month_cutoff,
    price_source_mpn_match,
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
    observed_at: datetime | None = None


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


class CdpFindchipsClient:
    """Read the rendered result in the Owner's ordinary Chrome session."""

    def __init__(self, *, cdp_url: str = "http://127.0.0.1:9222", timeout_ms: int = 45_000) -> None:
        parsed = urlsplit(cdp_url)
        if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Findchips CDP endpoint must be loopback")
        self._cdp_url = cdp_url
        self._timeout_ms = timeout_ms

    def fetch_first_page(self, mpn: str) -> FindchipsPage:
        target_url = build_findchips_search_url(mpn)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise FindchipsPageUnavailable("PLAYWRIGHT_NOT_INSTALLED") from error
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.connect_over_cdp(
                    self._cdp_url, timeout=self._timeout_ms
                )
                context = browser.contexts[0]
                pages = [page for page in context.pages if _is_findchips_response_url(page.url)]
                page = pages[0] if pages else context.new_page()
                page.goto(target_url, wait_until="domcontentloaded", timeout=self._timeout_ms)
                page.wait_for_timeout(4_000)
                if not _is_findchips_response_url(page.url):
                    raise FindchipsPageUnavailable("UNEXPECTED_RESPONSE_HOST", page.url)
                html = page.content()
                if not html.strip():
                    raise FindchipsPageUnavailable("EMPTY_RESPONSE", page.url)
                return FindchipsPage(html, page.url, datetime.now(UTC))
        except FindchipsPageUnavailable:
            raise
        except Exception as error:
            raise FindchipsPageUnavailable("BROWSER_FAILURE", target_url) from error


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
        if "," in raw_price and not re.fullmatch(
            r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", raw_price
        ):
            raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE")
        try:
            unit_price = Decimal(raw_price.replace(",", ""))
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


_CHINA_TZ = timezone(timedelta(hours=8))


def _parse_optional_date(value: str | None) -> datetime | None:
    if value is None or not value.strip():
        return None
    raw = value.strip()
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, pattern).replace(
                tzinfo=_CHINA_TZ
            ).astimezone(UTC)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise FindchipsParseError("QUOTE_DATE_UNPARSEABLE") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_CHINA_TZ)
    return parsed.astimezone(UTC)


class _FindchipsParser(HTMLParser):
    def __init__(self, target_mpn: str | None = None) -> None:
        super().__init__(convert_charrefs=True)
        self.target_mpn = target_mpn
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
        if self.target_mpn is not None and price_source_mpn_match(
            self.target_mpn, values["data-mfrpartnumber"] or ""
        ) is None:
            return
        self.offers.append(
            FindchipsOffer(
                mpn=values["data-mfrpartnumber"] or "",
                stock_positive=_parse_stock_presence(values.get("data-instock")),
                tiers=_parse_tiers(values.get("data-price")),
                observed_at=_parse_optional_date(
                    values.get("data-quotedate")
                    or values.get("data-quote-date")
                    or values.get("data-date")
                ),
            )
        )


def parse_findchips_offers(
    html: str, target_mpn: str | None = None
) -> tuple[FindchipsOffer, ...]:
    """Parse safe offer facts without retaining stock quantities or raw HTML."""

    parser = _FindchipsParser(target_mpn)
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
    """Select the lowest displayed supported unit price; quantity is irrelevant."""

    del customer_quantity
    eligible = [tier for tier in tiers if tier.currency in {"USD", "HKD"}]
    return (
        min(eligible, key=lambda tier: (tier.unit_price, tier.break_quantity))
        if eligible
        else None
    )


def select_lowest_valid_price(
    offers: tuple[FindchipsOffer, ...],
    target_mpn: str,
    customer_quantity: int,
) -> tuple[str, FindchipsPriceTier] | None:
    """Select the lowest displayed USD price from matched stocked offers."""

    applicable: list[tuple[str, FindchipsPriceTier]] = []
    for offer in offers:
        if price_source_mpn_match(target_mpn, offer.mpn) is None:
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
            offers = parse_findchips_offers(page.html, target_mpn)
        except FindchipsError as error:
            return self._unavailable(
                target_mpn,
                error.code,
                captured_at=page.captured_at,
                source_url=page.url,
            )

        now = self._clock()
        cutoff = calendar_month_cutoff(now)
        mpn_matched_offers = [
            offer
            for offer in offers
            if price_source_mpn_match(target_mpn, offer.mpn) is not None
        ]
        matched_offers = [
            offer
            for offer in mpn_matched_offers
            if (
                offer.observed_at is None
                or cutoff <= offer.observed_at <= now
            )
        ]
        if not mpn_matched_offers:
            evidence = SourceEvidence(
                source=ResearchSource.FINDCHIPS,
                query_mpn=target_mpn,
                matched_mpn=None,
                outcome=SourceOutcome.NO_STRICT_MPN_MATCH,
                captured_at=page.captured_at,
                source_url=page.url,
                fields=(
                    EvidenceField("inspected_offer_count", len(offers)),
                    EvidenceField("matched_mpn_offer_count", 0),
                ),
            )
            return SourceResult(
                source=ResearchSource.FINDCHIPS,
                outcome=SourceOutcome.NO_STRICT_MPN_MATCH,
                evidence=evidence,
            )
        if not matched_offers:
            evidence = SourceEvidence(
                source=ResearchSource.FINDCHIPS,
                query_mpn=target_mpn,
                matched_mpn=mpn_matched_offers[0].mpn,
                outcome=SourceOutcome.NO_VALID_PRICE,
                captured_at=page.captured_at,
                source_url=page.url,
                fields=(
                    EvidenceField("inspected_offer_count", len(offers)),
                    EvidenceField(
                        "matched_mpn_offer_count", len(mpn_matched_offers)
                    ),
                ),
            )
            return SourceResult(
                source=ResearchSource.FINDCHIPS,
                outcome=SourceOutcome.NO_VALID_PRICE,
                evidence=evidence,
            )

        priced = [
            (offer, tier)
            for offer in matched_offers
            if (tier := select_applicable_tier(offer.tiers, customer_quantity))
            is not None
        ]
        stocked = [(offer, tier) for offer, tier in priced if offer.stock_positive is True]
        out_of_stock = [
            (offer, tier) for offer, tier in priced if offer.stock_positive is False
        ]
        count_fields = (
            EvidenceField("inspected_offer_count", len(offers)),
            EvidenceField("matched_mpn_offer_count", len(matched_offers)),
            EvidenceField("stocked_price_offer_count", len(stocked)),
            EvidenceField("out_of_stock_price_offer_count", len(out_of_stock)),
        )
        if not stocked and not out_of_stock:
            evidence = SourceEvidence(
                source=ResearchSource.FINDCHIPS,
                query_mpn=target_mpn,
                matched_mpn=matched_offers[0].mpn,
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

        try:
            fx_quote = self._fx_provider.get_quote()
            if not isinstance(fx_quote, UsdRmbQuote):
                raise TypeError("FX provider returned an invalid quote")
            rates = {"USD": fx_quote.rate}
            if any(tier.currency == "HKD" for _, tier in stocked + out_of_stock):
                hkd_rate = self._fx_provider.get_hkd_rmb_rate()
                if not isinstance(hkd_rate, Decimal) or not hkd_rate.is_finite() or hkd_rate <= 0:
                    raise ValueError("Invalid HKD/RMB rate")
                rates["HKD"] = hkd_rate
        except Exception:  # noqa: BLE001 - external provider boundary
            return self._unavailable(
                target_mpn,
                "FX_QUOTE_UNAVAILABLE",
                captured_at=page.captured_at,
                source_url=page.url,
                fields=count_fields,
            )

        def lowest(
            selections: list[tuple[FindchipsOffer, FindchipsPriceTier]],
        ) -> tuple[FindchipsOffer, FindchipsPriceTier] | None:
            return (
                min(
                    selections,
                    key=lambda item: (
                        item[1].unit_price * rates[item[1].currency],
                        item[0].mpn.casefold(),
                        item[1].break_quantity,
                    ),
                )
                if selections
                else None
            )

        stocked_selection = lowest(stocked)
        out_of_stock_selection = lowest(out_of_stock)

        def candidate(selection: tuple[FindchipsOffer, FindchipsPriceTier] | None):
            if selection is None:
                return None
            offer, tier = selection
            match = price_source_mpn_match(target_mpn, offer.mpn)
            return PriceCandidate(
                source=ResearchSource.FINDCHIPS,
                matched_mpn=offer.mpn,
                raw_price=tier.unit_price,
                raw_currency=tier.currency,
                normalized_rmb_price=tier.unit_price * rates[tier.currency],
                captured_at=page.captured_at,
                source_url=page.url,
                display_mpn=(
                    offer.mpn if match is MpnMatchKind.SUFFIX else None
                ),
            )

        stocked_candidate = candidate(stocked_selection)
        out_of_stock_candidate = candidate(out_of_stock_selection)
        evidence_match = (
            stocked_selection or out_of_stock_selection
        )
        assert evidence_match is not None
        matched_mpn = evidence_match[0].mpn
        evidence = SourceEvidence(
            source=ResearchSource.FINDCHIPS,
            query_mpn=target_mpn,
            matched_mpn=matched_mpn,
            outcome=SourceOutcome.SUCCESS,
            captured_at=page.captured_at,
            source_url=page.url,
            fields=(
                *count_fields,
                EvidenceField("fx_base_currency", fx_quote.base_currency),
                EvidenceField("fx_quote_currency", fx_quote.quote_currency),
                EvidenceField("fx_rate", fx_quote.rate),
                EvidenceField("hkd_rmb_rate", rates.get("HKD")),
                EvidenceField("fx_captured_at", fx_quote.captured_at),
                EvidenceField("fx_source_label", fx_quote.source_label),
                EvidenceField(
                    "stocked_rmb_price",
                    stocked_candidate.normalized_rmb_price
                    if stocked_candidate
                    else None,
                ),
                EvidenceField(
                    "out_of_stock_rmb_price",
                    out_of_stock_candidate.normalized_rmb_price
                    if out_of_stock_candidate
                    else None,
                ),
            ),
        )
        return SourceResult(
            source=ResearchSource.FINDCHIPS,
            outcome=SourceOutcome.SUCCESS,
            evidence=evidence,
            price_candidate=stocked_candidate,
            out_of_stock_candidate=out_of_stock_candidate,
        )
