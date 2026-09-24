"""Bom.Ai read-only historical-price adapter and section-scoped parser."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Protocol
from urllib.parse import urlsplit

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

BOM_AI_SITE_ID = "bom.ai"


@dataclass(frozen=True, slots=True)
class BomAiLogin:
    username: str = field(repr=False)
    password: str = field(repr=False)
    company: str | None = field(default=None, repr=False)


class BomAiCredentialProvider(Protocol):
    def get_login(self, site_id: str) -> BomAiLogin | None: ...


@dataclass(frozen=True, slots=True)
class BomAiPriceRecord:
    mpn: str
    raw_price: Decimal
    observed_at: datetime
    currency: str = "RMB"

    def __post_init__(self) -> None:
        if not self.raw_price.is_finite() or self.raw_price <= 0:
            raise ValueError("raw_price must be finite and positive")
        if self.currency not in {"RMB", "CNY", "USD"}:
            raise ValueError("currency must be RMB, CNY, or USD")

    @property
    def unit_price_rmb(self) -> Decimal:
        """Compatibility accessor for RMB-only records."""

        if self.currency not in {"RMB", "CNY"}:
            raise ValueError("USD record is not normalized yet")
        return self.raw_price


@dataclass(frozen=True, slots=True)
class BomAiCapture:
    records: tuple[BomAiPriceRecord, ...]
    url: str
    captured_at: datetime


@dataclass(frozen=True, slots=True)
class BomAiRawPage:
    html: str = field(repr=False)
    url: str
    captured_at: datetime


class BomAiClientError(RuntimeError):
    def __init__(self, code: str, source_url: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.source_url = source_url


class BomAiAuthenticatedClient(Protocol):
    def fetch_price_records(self, mpn: str) -> BomAiCapture: ...


class BomAiAuthenticatedBrowser(Protocol):
    def fetch_price_page(self, mpn: str, login: BomAiLogin) -> BomAiRawPage: ...


_H3 = re.compile(r"<h3[^>]*>(.*?)</h3>", re.IGNORECASE | re.DOTALL)
_DATA = re.compile(r"<data(?:\s[^>]*)?>(.*?)</data>", re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_CHINA_TZ = timezone(timedelta(hours=8))


def _child_text(block: str, tag: str) -> str | None:
    match = re.search(
        rf"<{tag}(?:\s[^>]*)?>(.*?)</{tag}>",
        block,
        re.IGNORECASE | re.DOTALL,
    )
    return None if match is None else _TAG.sub("", match.group(1)).strip()


def _parse_price(value: str) -> tuple[Decimal, str]:
    compact = value.strip()
    upper = compact.upper()
    currency = "USD" if "$" in compact or "USD" in upper else "RMB"
    numeric = re.sub(r"(?i)USD|RMB|CNY|US\$|[$¥￥,\s]", "", compact)
    try:
        price = Decimal(numeric)
    except InvalidOperation as exc:
        raise BomAiClientError("PRICE_RECORD_UNPARSEABLE") from exc
    if not price.is_finite() or price <= 0:
        raise BomAiClientError("PRICE_RECORD_UNPARSEABLE")
    return price, currency


def parse_bom_ai_price_records(
    html: str, target_mpn: str
) -> tuple[BomAiPriceRecord, ...]:
    """Parse only quote blocks belonging to matching lower-page MPN sections."""

    headings = list(_H3.finditer(html))
    if not headings:
        raise BomAiClientError("RESULT_IDENTITY_MISSING")
    records: list[BomAiPriceRecord] = []
    for index, heading in enumerate(headings):
        section_mpn = _TAG.sub("", heading.group(1)).strip()
        if price_source_mpn_match(target_mpn, section_mpn) is None:
            continue
        section_end = (
            headings[index + 1].start() if index + 1 < len(headings) else len(html)
        )
        section = html[heading.end() : section_end]
        for block in _DATA.findall(section):
            raw_price = _child_text(block, "quotePrice")
            raw_date = _child_text(block, "quoteDate")
            if raw_price is None and raw_date is None:
                continue
            if (
                not raw_price
                or not raw_date
                or "{{" in raw_price
                or "{{" in raw_date
            ):
                continue
            price, currency = _parse_price(raw_price)
            try:
                observed = datetime.strptime(
                    raw_date, "%Y/%m/%d %H:%M:%S"
                ).replace(tzinfo=_CHINA_TZ)
            except ValueError as exc:
                raise BomAiClientError("PRICE_RECORD_UNPARSEABLE") from exc
            records.append(
                BomAiPriceRecord(
                    section_mpn,
                    price,
                    observed.astimezone(UTC),
                    currency,
                )
            )
    return tuple(records)


class BomAiCredentialedClient:
    """Join injected credential and browser capabilities without persisting secrets."""

    def __init__(
        self,
        credential_provider: BomAiCredentialProvider,
        browser: BomAiAuthenticatedBrowser,
    ) -> None:
        self._credential_provider = credential_provider
        self._browser = browser

    def fetch_price_records(self, mpn: str) -> BomAiCapture:
        login = self._credential_provider.get_login(BOM_AI_SITE_ID)
        if login is None:
            raise BomAiClientError("CREDENTIALS_UNAVAILABLE")
        page = self._browser.fetch_price_page(mpn, login)
        parsed = urlsplit(page.url)
        if (
            parsed.scheme != "https"
            or parsed.hostname is None
            or not (
                parsed.hostname.casefold() == "bom.ai"
                or parsed.hostname.casefold().endswith(".bom.ai")
            )
        ):
            raise BomAiClientError("UNEXPECTED_RESPONSE_HOST", page.url)
        return BomAiCapture(
            parse_bom_ai_price_records(page.html, mpn),
            page.url,
            page.captured_at,
        )


class BomAiMonthCutoff(Protocol):
    def __call__(self, now: datetime) -> datetime: ...


class BomAiAdapter:
    def __init__(
        self,
        client: BomAiAuthenticatedClient,
        month_cutoff: BomAiMonthCutoff = calendar_month_cutoff,
        *,
        fx_provider: UsdRmbProvider | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client
        self._month_cutoff = month_cutoff
        self._fx = fx_provider
        self._clock = clock or (lambda: datetime.now(UTC))

    def search(self, target_mpn: str, customer_quantity: int) -> SourceResult:
        del customer_quantity
        now = self._clock()
        try:
            capture = self._client.fetch_price_records(target_mpn)
            cutoff = self._month_cutoff(now)
        except BomAiClientError as exc:
            return self._failure(target_mpn, now, exc.code, exc.source_url)
        except (RuntimeError, TypeError, ValueError):
            return self._failure(
                target_mpn, now, "AUTHENTICATED_READ_UNAVAILABLE", None
            )

        matched = [
            record
            for record in capture.records
            if price_source_mpn_match(target_mpn, record.mpn) is not None
        ]
        valid = [
            record
            for record in matched
            if cutoff <= record.observed_at <= now
        ]
        if not matched:
            return self._result(target_mpn, capture, SourceOutcome.NO_STRICT_MPN_MATCH)
        if not valid:
            return self._result(target_mpn, capture, SourceOutcome.NO_VALID_PRICE)

        quote: UsdRmbQuote | None = None
        if any(record.currency == "USD" for record in valid):
            try:
                if self._fx is None:
                    raise RuntimeError
                quote = self._fx.get_quote()
                if not isinstance(quote, UsdRmbQuote):
                    raise TypeError
            except (RuntimeError, TypeError, ValueError):
                return self._failure(
                    target_mpn, now, "FX_QUOTE_UNAVAILABLE", capture.url
                )

        normalized = [
            (
                record,
                record.raw_price * quote.rate
                if record.currency == "USD" and quote is not None
                else record.raw_price,
            )
            for record in valid
        ]
        selected, rmb_price = min(
            normalized,
            key=lambda item: (item[1], item[0].observed_at, item[0].mpn.casefold()),
        )
        match = price_source_mpn_match(target_mpn, selected.mpn)
        candidate = PriceCandidate(
            ResearchSource.BOM_AI,
            selected.mpn,
            selected.raw_price,
            selected.currency,
            rmb_price,
            capture.captured_at,
            capture.url,
            selected.mpn if match is MpnMatchKind.SUFFIX else None,
        )
        return self._result(
            target_mpn, capture, SourceOutcome.SUCCESS, candidate
        )

    @staticmethod
    def _result(
        query: str,
        capture: BomAiCapture,
        outcome: SourceOutcome,
        candidate: PriceCandidate | None = None,
    ) -> SourceResult:
        evidence = SourceEvidence(
            ResearchSource.BOM_AI,
            query,
            candidate.matched_mpn if candidate else None,
            outcome,
            capture.captured_at,
            capture.url,
            (
                EvidenceField("records_inspected", len(capture.records)),
                EvidenceField(
                    "selected_observed_at",
                    next(
                        (
                            record.observed_at
                            for record in capture.records
                            if candidate is not None
                            and record.mpn == candidate.matched_mpn
                            and record.raw_price == candidate.raw_price
                        ),
                        None,
                    ),
                ),
                EvidenceField(
                    "selected_rmb_price",
                    candidate.normalized_rmb_price if candidate else None,
                ),
            ),
        )
        return SourceResult(ResearchSource.BOM_AI, outcome, evidence, candidate)

    @staticmethod
    def _failure(
        query: str, captured_at: datetime, code: str, url: str | None
    ) -> SourceResult:
        evidence = SourceEvidence(
            ResearchSource.BOM_AI,
            query,
            None,
            SourceOutcome.SOURCE_UNAVAILABLE,
            captured_at,
            url,
            (EvidenceField("failure_code", code),),
        )
        return SourceResult(
            ResearchSource.BOM_AI, SourceOutcome.SOURCE_UNAVAILABLE, evidence
        )
