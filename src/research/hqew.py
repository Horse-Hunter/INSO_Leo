"""Read-only HQEW cloud-price adapter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from .source_contracts import (
    EvidenceField,
    PriceCandidate,
    ResearchSource,
    SourceEvidence,
    SourceOutcome,
    SourceResult,
    is_strict_mpn_match,
)

HQEW_RESULT_URL = "https://p.hqew.com/yunquote/"
HQEW_USER_AGENT = "INSO-Leo-Research/1.0 (read-only HQEW adapter)"


class HqewError(RuntimeError):
    def __init__(self, code: str, source_url: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.source_url = source_url


class HqewPageUnavailable(HqewError):
    pass


class HqewParseError(HqewError):
    pass


@dataclass(frozen=True, slots=True)
class HqewOffer:
    mpn: str
    unit_price_rmb: Decimal

    def __post_init__(self) -> None:
        if not self.unit_price_rmb.is_finite() or self.unit_price_rmb <= 0:
            raise ValueError("unit_price_rmb must be finite and positive")


@dataclass(frozen=True, slots=True)
class HqewPage:
    html: str = field(repr=False)
    url: str
    captured_at: datetime


class HqewPageClient(Protocol):
    def fetch_first_page(self, mpn: str) -> HqewPage: ...


def build_hqew_result_url(mpn: str) -> str:
    return f"{HQEW_RESULT_URL}{quote(mpn.strip(), safe='')}.html?y4=1"


def _is_hqew_url(url: str) -> bool:
    host = urlsplit(url).hostname
    return bool(
        host
        and (host.casefold() == "hqew.com" or host.casefold().endswith(".hqew.com"))
    )


class HqewHttpClient:
    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self._timeout_seconds = timeout_seconds

    def fetch_first_page(self, mpn: str) -> HqewPage:
        url = build_hqew_result_url(mpn)
        try:
            with urlopen(
                Request(
                    url, headers={"User-Agent": HQEW_USER_AGENT, "Accept": "text/html"}
                ),
                timeout=self._timeout_seconds,
            ) as response:
                final_url = response.geturl()
                if not _is_hqew_url(final_url):
                    raise HqewPageUnavailable("UNEXPECTED_RESPONSE_HOST", final_url)
                html = response.read().decode(
                    response.headers.get_content_charset() or "utf-8", errors="replace"
                )
                if "安全验证" in html or "captcha-reset" in html:
                    raise HqewPageUnavailable(
                        "INTERACTIVE_CHALLENGE_REQUIRED", final_url
                    )
                if response.status != 200 or not html.strip():
                    raise HqewPageUnavailable("HTTP_RESPONSE_UNUSABLE", final_url)
                return HqewPage(html, final_url, datetime.now(UTC))
        except HqewPageUnavailable:
            raise
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise HqewPageUnavailable("HTTP_REQUEST_FAILED", url) from exc


class _OfferParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.offers: list[HqewOffer] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "input":
            return
        values = {key.casefold(): value for key, value in attrs}
        classes = (values.get("class") or "").split()
        if "list-data" not in classes:
            return
        mpn = values.get("pmodel")
        raw_price = values.get("quotationprice")
        if not mpn or not raw_price:
            return
        try:
            price = Decimal(raw_price)
        except InvalidOperation as exc:
            raise HqewParseError("PRICE_UNPARSEABLE") from exc
        try:
            self.offers.append(HqewOffer(mpn, price))
        except ValueError as exc:
            raise HqewParseError("PRICE_INVALID") from exc


def parse_hqew_offers(html: str) -> tuple[HqewOffer, ...]:
    if "安全验证" in html or "captcha-reset" in html:
        raise HqewPageUnavailable("INTERACTIVE_CHALLENGE_REQUIRED")
    parser = _OfferParser()
    parser.feed(html)
    if not parser.offers:
        if "暂无商家报价" in html:
            return ()
        raise HqewParseError("RESULT_ROWS_MISSING")
    return tuple(parser.offers)


class HqewAdapter:
    def __init__(
        self, client: HqewPageClient, *, clock: Callable[[], datetime] | None = None
    ) -> None:
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))

    def search(self, target_mpn: str, customer_quantity: int) -> SourceResult:
        del customer_quantity
        try:
            page = self._client.fetch_first_page(target_mpn)
            offers = parse_hqew_offers(page.html)
        except HqewError as exc:
            return self._failure(target_mpn, exc)
        strict = [
            offer for offer in offers if is_strict_mpn_match(target_mpn, offer.mpn)
        ]
        if not strict:
            outcome = SourceOutcome.NO_STRICT_MPN_MATCH
            candidate = None
            matched = None
        else:
            selected = min(strict, key=lambda offer: offer.unit_price_rmb)
            outcome = SourceOutcome.SUCCESS
            matched = selected.mpn
            candidate = PriceCandidate(
                ResearchSource.HQEW,
                selected.mpn,
                selected.unit_price_rmb,
                "RMB",
                selected.unit_price_rmb,
                page.captured_at,
                page.url,
            )
        evidence = SourceEvidence(
            ResearchSource.HQEW,
            target_mpn,
            matched,
            outcome,
            page.captured_at,
            page.url,
            (
                EvidenceField("offers_inspected", len(offers)),
                EvidenceField("strict_mpn_offers", len(strict)),
                EvidenceField(
                    "selected_rmb_price", candidate.raw_price if candidate else None
                ),
            ),
        )
        return SourceResult(ResearchSource.HQEW, outcome, evidence, candidate)

    def _failure(self, target_mpn: str, exc: HqewError) -> SourceResult:
        evidence = SourceEvidence(
            ResearchSource.HQEW,
            target_mpn,
            None,
            SourceOutcome.SOURCE_UNAVAILABLE,
            self._clock(),
            exc.source_url,
            (EvidenceField("failure_code", exc.code),),
        )
        return SourceResult(
            ResearchSource.HQEW, SourceOutcome.SOURCE_UNAVAILABLE, evidence
        )
