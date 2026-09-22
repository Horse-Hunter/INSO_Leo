"""Read-only LCSC product-page adapter."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
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

LCSC_USER_AGENT = "INSO-Leo-Research/1.0 (read-only LCSC adapter)"


class LcscError(RuntimeError):
    def __init__(self, code: str, source_url: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.source_url = source_url


class LcscPageUnavailable(LcscError):
    pass


class LcscParseError(LcscError):
    pass


@dataclass(frozen=True, slots=True)
class LcscPriceTier:
    break_quantity: int
    unit_price: Decimal
    currency: str

    def __post_init__(self) -> None:
        if (
            self.break_quantity <= 0
            or not self.unit_price.is_finite()
            or self.unit_price <= 0
        ):
            raise ValueError("LCSC tier must have positive finite values")


@dataclass(frozen=True, slots=True)
class LcscProduct:
    mpn: str
    is_preorder: bool
    stock_quantity: int | None
    tiers: tuple[LcscPriceTier, ...]


@dataclass(frozen=True, slots=True)
class LcscPage:
    html: str = field(repr=False)
    url: str
    captured_at: datetime


class LcscPageClient(Protocol):
    def fetch_product_page(self, mpn: str) -> LcscPage: ...


class LcscHttpClient:
    """HTTP acquisition using an injected normal public product-URL resolver."""

    def __init__(
        self,
        product_url_resolver: Callable[[str], str],
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._resolver = product_url_resolver
        self._timeout_seconds = timeout_seconds

    def fetch_product_page(self, mpn: str) -> LcscPage:
        url = self._resolver(mpn.strip())
        host = urlsplit(url).hostname
        if not host or not (
            host.casefold() == "lcsc.com" or host.casefold().endswith(".lcsc.com")
        ):
            raise LcscPageUnavailable("PRODUCT_URL_HOST_FORBIDDEN", url)
        try:
            with urlopen(
                Request(url, headers={"User-Agent": LCSC_USER_AGENT}),
                timeout=self._timeout_seconds,
            ) as response:
                final_url = response.geturl()
                final_host = urlsplit(final_url).hostname
                if not final_host or not (
                    final_host.casefold() == "lcsc.com"
                    or final_host.casefold().endswith(".lcsc.com")
                ):
                    raise LcscPageUnavailable("UNEXPECTED_RESPONSE_HOST", final_url)
                html = response.read().decode(
                    response.headers.get_content_charset() or "utf-8", errors="replace"
                )
                if response.status != 200 or not html.strip():
                    raise LcscPageUnavailable("HTTP_RESPONSE_UNUSABLE", final_url)
                return LcscPage(html, final_url, datetime.now(UTC))
        except LcscPageUnavailable:
            raise
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise LcscPageUnavailable("HTTP_REQUEST_FAILED", url) from exc


_NEXT_DATA = re.compile(
    r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def parse_lcsc_product(html: str) -> LcscProduct:
    match = _NEXT_DATA.search(html)
    if not match:
        raise LcscParseError("NEXT_DATA_MISSING")
    try:
        payload = json.loads(match.group(1))
        data = payload["props"]["pageProps"]["webData"]
        mpn = data["productModel"]
        currency = data["currencyType"]
        raw_tiers = data["productPriceList"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise LcscParseError("PRODUCT_DATA_UNPARSEABLE") from exc
    if (
        not isinstance(mpn, str)
        or not isinstance(currency, str)
        or not isinstance(raw_tiers, list)
    ):
        raise LcscParseError("PRODUCT_DATA_UNPARSEABLE")
    tiers: list[LcscPriceTier] = []
    try:
        for item in raw_tiers:
            tiers.append(
                LcscPriceTier(
                    int(item["ladder"]),
                    Decimal(str(item["productPrice"])),
                    currency.upper(),
                )
            )
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise LcscParseError("PRICE_TIERS_UNPARSEABLE") from exc
    stock = data.get("stockNumber")
    if stock is not None and (isinstance(stock, bool) or not isinstance(stock, int)):
        raise LcscParseError("STOCK_UNPARSEABLE")
    return LcscProduct(mpn, bool(data.get("isPreSale", False)), stock, tuple(tiers))


def select_lcsc_tier(
    tiers: tuple[LcscPriceTier, ...], quantity: int
) -> LcscPriceTier | None:
    applicable = [tier for tier in tiers if tier.break_quantity <= quantity]
    return max(applicable, key=lambda tier: tier.break_quantity) if applicable else None


class LcscAdapter:
    def __init__(
        self,
        client: LcscPageClient,
        fx_provider: UsdRmbProvider,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client
        self._fx = fx_provider
        self._clock = clock or (lambda: datetime.now(UTC))

    def search(self, target_mpn: str, customer_quantity: int) -> SourceResult:
        try:
            page = self._client.fetch_product_page(target_mpn)
            product = parse_lcsc_product(page.html)
        except LcscError as exc:
            return self._failure(target_mpn, exc)
        if not is_strict_mpn_match(target_mpn, product.mpn):
            return self._result(
                target_mpn, page, product, SourceOutcome.NO_STRICT_MPN_MATCH, None, None
            )
        tier = select_lcsc_tier(product.tiers, customer_quantity)
        if tier is None or tier.currency not in {"USD", "RMB", "CNY"}:
            return self._result(
                target_mpn, page, product, SourceOutcome.NO_VALID_PRICE, None, None
            )
        quote: UsdRmbQuote | None = None
        if tier.currency == "USD":
            try:
                quote = self._fx.get_quote()
                if not isinstance(quote, UsdRmbQuote):
                    raise TypeError
            except (RuntimeError, TypeError, ValueError):
                return self._failure(
                    target_mpn, LcscPageUnavailable("FX_QUOTE_UNAVAILABLE", page.url)
                )
            normalized = tier.unit_price * quote.rate
        else:
            normalized = tier.unit_price
        candidate = PriceCandidate(
            ResearchSource.LCSC,
            product.mpn,
            tier.unit_price,
            tier.currency,
            normalized,
            page.captured_at,
            page.url,
        )
        return self._result(
            target_mpn, page, product, SourceOutcome.SUCCESS, candidate, quote, tier
        )

    def _result(
        self,
        query: str,
        page: LcscPage,
        product: LcscProduct,
        outcome: SourceOutcome,
        candidate: PriceCandidate | None,
        quote: UsdRmbQuote | None,
        tier: LcscPriceTier | None = None,
    ) -> SourceResult:
        fields = (
            EvidenceField("is_preorder", product.is_preorder),
            EvidenceField(
                "stock_present",
                product.stock_quantity is not None and product.stock_quantity > 0,
            ),
            EvidenceField(
                "selected_tier_break_quantity", tier.break_quantity if tier else None
            ),
            EvidenceField("selected_raw_price", tier.unit_price if tier else None),
            EvidenceField("raw_currency", tier.currency if tier else None),
            EvidenceField("fx_rate", quote.rate if quote else None),
            EvidenceField(
                "normalized_rmb_price",
                candidate.normalized_rmb_price if candidate else None,
            ),
        )
        evidence = SourceEvidence(
            ResearchSource.LCSC,
            query,
            product.mpn if is_strict_mpn_match(query, product.mpn) else None,
            outcome,
            page.captured_at,
            page.url,
            fields,
        )
        return SourceResult(ResearchSource.LCSC, outcome, evidence, candidate)

    def _failure(self, query: str, exc: LcscError) -> SourceResult:
        evidence = SourceEvidence(
            ResearchSource.LCSC,
            query,
            None,
            SourceOutcome.SOURCE_UNAVAILABLE,
            self._clock(),
            exc.source_url,
            (EvidenceField("failure_code", exc.code),),
        )
        return SourceResult(
            ResearchSource.LCSC, SourceOutcome.SOURCE_UNAVAILABLE, evidence
        )
