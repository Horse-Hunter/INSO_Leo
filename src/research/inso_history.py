"""Read-only INSO procurement-temporary-inquiry history price source."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from .fx import UsdRmbProvider, UsdRmbQuote
from .source_contracts import (
    EvidenceField,
    PriceCandidate,
    ResearchSource,
    SourceEvidence,
    SourceOutcome,
    SourceResult,
    calendar_month_cutoff,
)

INSO_SITE_ID = "inso"


@dataclass(frozen=True, slots=True)
class InsoLogin:
    username: str = field(repr=False)
    password: str = field(repr=False)
    company: str | None = field(default=None, repr=False)


class InsoCredentialProvider(Protocol):
    def get_login(self, site_id: str) -> InsoLogin | None: ...


@dataclass(frozen=True, slots=True)
class InsoHistoryRecord:
    supplier_untaxed_price_usd: Decimal = field(repr=False)
    observed_at: datetime

    def __post_init__(self) -> None:
        value = self.supplier_untaxed_price_usd
        if not isinstance(value, Decimal):
            raise TypeError("supplier_untaxed_price_usd must be Decimal")
        if not value.is_finite() or value < 0:
            raise ValueError("supplier_untaxed_price_usd must be finite and nonnegative")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class InsoHistoryCapture:
    records: tuple[InsoHistoryRecord, ...]
    url: str
    captured_at: datetime


class InsoReadError(RuntimeError):
    def __init__(self, code: str, source_url: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.source_url = source_url


class InsoReadOnlyBrowser(Protocol):
    """Only the approved inquiry-history query is exposed; no write operation."""

    def fetch_procurement_temporary_inquiry_history(
        self, mpn: str, login: InsoLogin
    ) -> InsoHistoryCapture:
        """Read 业务询价 → 采购临时询价 → query → history results."""


class InsoHistoryClient(Protocol):
    def fetch_history(self, mpn: str) -> InsoHistoryCapture: ...


class InsoCredentialedClient:
    """Acquire an authenticated, read-only history capture without logging secrets."""

    def __init__(
        self,
        credential_provider: InsoCredentialProvider,
        browser: InsoReadOnlyBrowser,
    ) -> None:
        self._credential_provider = credential_provider
        self._browser = browser

    def fetch_history(self, mpn: str) -> InsoHistoryCapture:
        login = self._credential_provider.get_login(INSO_SITE_ID)
        if login is None:
            raise InsoReadError("CREDENTIALS_UNAVAILABLE")
        try:
            return self._browser.fetch_procurement_temporary_inquiry_history(
                mpn, login
            )
        except InsoReadError:
            raise
        except (OSError, RuntimeError, TimeoutError) as exc:
            raise InsoReadError("AUTHENTICATED_READ_UNAVAILABLE") from exc


class InsoHistoryAdapter:
    def __init__(
        self,
        client: InsoHistoryClient,
        fx_provider: UsdRmbProvider,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client
        self._fx = fx_provider
        self._clock = clock or (lambda: datetime.now(UTC))

    def search(self, target_mpn: str, customer_quantity: int) -> SourceResult:
        del customer_quantity
        now = self._clock()
        try:
            capture = self._client.fetch_history(target_mpn)
        except InsoReadError as exc:
            return self._failure(target_mpn, now, exc.code, exc.source_url)

        positive = tuple(
            record
            for record in capture.records
            if record.supplier_untaxed_price_usd > 0 and record.observed_at <= now
        )
        selected: InsoHistoryRecord | None = None
        selected_months = 1
        for months in (1, 2, 3):
            cutoff = calendar_month_cutoff(now, months)
            pool = [record for record in positive if record.observed_at >= cutoff]
            if pool:
                selected = min(
                    pool,
                    key=lambda record: (
                        record.supplier_untaxed_price_usd,
                        record.observed_at,
                    ),
                )
                selected_months = months
                break
        if selected is None:
            evidence = SourceEvidence(
                ResearchSource.INSO,
                target_mpn,
                None,
                SourceOutcome.NO_VALID_PRICE,
                capture.captured_at,
                capture.url,
                (
                    EvidenceField("records_inspected", len(capture.records)),
                    EvidenceField("positive_records", len(positive)),
                ),
            )
            return SourceResult(
                ResearchSource.INSO, SourceOutcome.NO_VALID_PRICE, evidence
            )

        try:
            quote = self._fx.get_quote()
            if not isinstance(quote, UsdRmbQuote):
                raise TypeError
        except (RuntimeError, TypeError, ValueError):
            return self._failure(
                target_mpn, capture.captured_at, "FX_QUOTE_UNAVAILABLE", capture.url
            )
        normalized = selected.supplier_untaxed_price_usd * quote.rate
        candidate = PriceCandidate(
            ResearchSource.INSO,
            target_mpn.strip(),
            selected.supplier_untaxed_price_usd,
            "USD",
            normalized,
            capture.captured_at,
            capture.url,
            None,
            selected_months,
        )
        evidence = SourceEvidence(
            ResearchSource.INSO,
            target_mpn,
            None,
            SourceOutcome.SUCCESS,
            capture.captured_at,
            capture.url,
            (
                EvidenceField("records_inspected", len(capture.records)),
                EvidenceField("positive_records", len(positive)),
                EvidenceField("selected_window_months", selected_months),
                EvidenceField("fx_rate", quote.rate),
            ),
        )
        return SourceResult(
            ResearchSource.INSO, SourceOutcome.SUCCESS, evidence, candidate
        )

    @staticmethod
    def _failure(
        query: str, captured_at: datetime, code: str, url: str | None
    ) -> SourceResult:
        evidence = SourceEvidence(
            ResearchSource.INSO,
            query,
            None,
            SourceOutcome.SOURCE_UNAVAILABLE,
            captured_at,
            url,
            (EvidenceField("failure_code", code),),
        )
        return SourceResult(
            ResearchSource.INSO, SourceOutcome.SOURCE_UNAVAILABLE, evidence
        )
