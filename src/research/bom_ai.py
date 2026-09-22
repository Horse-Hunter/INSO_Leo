"""Bom.Ai price selection behind an authenticated read-client boundary."""

from __future__ import annotations

import re
from calendar import monthrange
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Protocol
from urllib.parse import urlsplit

from .source_contracts import (
    EvidenceField,
    PriceCandidate,
    ResearchSource,
    SourceEvidence,
    SourceOutcome,
    SourceResult,
    is_strict_mpn_match,
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
    unit_price_rmb: Decimal
    observed_at: datetime

    def __post_init__(self) -> None:
        if not self.unit_price_rmb.is_finite() or self.unit_price_rmb <= 0:
            raise ValueError("unit_price_rmb must be finite and positive")


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
    """Authenticated read client; credentials remain inside its bounded session."""

    def fetch_price_records(self, mpn: str) -> BomAiCapture: ...


class BomAiAuthenticatedBrowser(Protocol):
    """Browser boundary that owns the bounded authenticated session."""

    def fetch_price_page(self, mpn: str, login: BomAiLogin) -> BomAiRawPage: ...


_H3 = re.compile(r"<h3[^>]*>(.*?)</h3>", re.IGNORECASE | re.DOTALL)
_DATA = re.compile(r"<data>(.*?)</data>", re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_CHINA_TZ = timezone(timedelta(hours=8))


def _child_text(block: str, tag: str) -> str | None:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", block, re.IGNORECASE | re.DOTALL)
    return None if match is None else _TAG.sub("", match.group(1)).strip()


def parse_bom_ai_price_records(
    html: str, target_mpn: str
) -> tuple[BomAiPriceRecord, ...]:
    """Parse authenticated server-rendered historical quote records."""

    headings = [_TAG.sub("", value).strip() for value in _H3.findall(html)]
    if not headings:
        raise BomAiClientError("RESULT_IDENTITY_MISSING")
    if not any(is_strict_mpn_match(target_mpn, value) for value in headings):
        return ()

    records: list[BomAiPriceRecord] = []
    for block in _DATA.findall(html):
        raw_price = _child_text(block, "quotePrice")
        raw_date = _child_text(block, "quoteDate")
        if raw_price is None and raw_date is None:
            continue
        if not raw_price or not raw_date or "{{" in raw_price or "{{" in raw_date:
            continue
        try:
            price = Decimal(raw_price)
            observed = datetime.strptime(raw_date, "%Y/%m/%d %H:%M:%S").replace(
                tzinfo=_CHINA_TZ
            )
        except (InvalidOperation, ValueError) as exc:
            raise BomAiClientError("PRICE_RECORD_UNPARSEABLE") from exc
        records.append(
            BomAiPriceRecord(
                target_mpn.strip(),
                price,
                observed.astimezone(UTC),
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
        records = parse_bom_ai_price_records(page.html, mpn)
        return BomAiCapture(records, page.url, page.captured_at)


class BomAiMonthCutoff(Protocol):
    """Owner-selected one-month cutoff policy."""

    def __call__(self, now: datetime) -> datetime: ...


def calendar_month_cutoff(now: datetime) -> datetime:
    """Return the same wall-clock time one calendar month earlier.

    When the previous month has fewer days, clamp to its final day. For
    example, March 31 maps to February 28 (or 29 in a leap year).
    """

    if now.month == 1:
        year, month = now.year - 1, 12
    else:
        year, month = now.year, now.month - 1
    day = min(now.day, monthrange(year, month)[1])
    return now.replace(year=year, month=month, day=day)


def select_bom_ai_price(
    records: tuple[BomAiPriceRecord, ...],
    target_mpn: str,
    *,
    now: datetime,
    month_cutoff: datetime,
) -> BomAiPriceRecord | None:
    strict = [
        record for record in records if is_strict_mpn_match(target_mpn, record.mpn)
    ]
    valid = [record for record in strict if month_cutoff <= record.observed_at <= now]
    recent = [
        record for record in valid if record.observed_at >= now - timedelta(days=7)
    ]
    pool = recent or valid
    return min(pool, key=lambda record: record.unit_price_rmb) if pool else None


class BomAiAdapter:
    def __init__(
        self,
        client: BomAiAuthenticatedClient,
        month_cutoff: BomAiMonthCutoff = calendar_month_cutoff,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client
        self._month_cutoff = month_cutoff
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

        strict = [
            record
            for record in capture.records
            if is_strict_mpn_match(target_mpn, record.mpn)
        ]
        if not strict:
            outcome = SourceOutcome.NO_STRICT_MPN_MATCH
            selected = None
        else:
            selected = select_bom_ai_price(
                capture.records, target_mpn, now=now, month_cutoff=cutoff
            )
            outcome = (
                SourceOutcome.SUCCESS if selected else SourceOutcome.NO_VALID_PRICE
            )
        candidate = (
            None
            if selected is None
            else PriceCandidate(
                ResearchSource.BOM_AI,
                selected.mpn,
                selected.unit_price_rmb,
                "RMB",
                selected.unit_price_rmb,
                capture.captured_at,
                capture.url,
            )
        )
        evidence = SourceEvidence(
            ResearchSource.BOM_AI,
            target_mpn,
            strict[0].mpn if strict else None,
            outcome,
            capture.captured_at,
            capture.url,
            (
                EvidenceField("strict_mpn_records", len(strict)),
                EvidenceField(
                    "selected_observed_at", selected.observed_at if selected else None
                ),
                EvidenceField(
                    "selected_rmb_price", selected.unit_price_rmb if selected else None
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
