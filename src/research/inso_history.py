"""Read-only INSO procurement-quote-history source.

The ``Stock_VenQuote`` endpoint exposes supplier quote history for an MPN
through the Owner-authorised ordinary Chrome session. The history records
carry ``CreateTime``, ``InPrice`` (supplier untaxed price) and ``CurrencyID``
(``RMB`` / ``USD``); price values in ``RMB`` are normalised to ``USD`` using
the shared FX quote before ``InsoHistoryAdapter`` emits the ``PriceCandidate``.
"""

from __future__ import annotations

import json
from ipaddress import ip_address
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol
from urllib.parse import urlsplit

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

INSO_SITE_ID = "yingsuo.alperp.cn"


@dataclass(frozen=True, slots=True)
class InsoLogin:
    username: str = field(repr=False)
    password: str = field(repr=False)
    company: str | None = field(default=None, repr=False)


class InsoCredentialProvider(Protocol):
    def get_login(self, site_id: str) -> InsoLogin | None: ...


@dataclass(frozen=True, slots=True)
class InsoHistoryRecord:
    price: Decimal = field(repr=False)
    currency: str = field(repr=False)  # "RMB" or "USD"
    observed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.price, Decimal) or not self.price.is_finite():
            raise ValueError("price must be a finite Decimal")
        if self.price < 0:
            raise ValueError("price must be nonnegative")
        if self.currency not in {"RMB", "USD"}:
            raise ValueError("currency must be RMB or USD")
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
    """Only the approved Stock_VenQuote read is exposed; no write operation."""

    def fetch_procurement_temporary_inquiry_history(
        self, mpn: str, login: InsoLogin
    ) -> InsoHistoryCapture:
        """Read Stock_VenQuote history for ``mpn`` via the CDP-attached session."""


@dataclass(frozen=True, slots=True)
class InsoBrowserConfig:
    """Runtime config for the INSO read-only Stock_VenQuote client."""

    login_url: str
    cdp_url: str = "http://127.0.0.1:9222"
    pagesize: int = 30

    def __post_init__(self) -> None:
        parsed = urlsplit(self.login_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("INSO login_url must be HTTPS")
        cdp_parsed = urlsplit(self.cdp_url)
        if cdp_parsed.scheme not in {"http", "https"} or not cdp_parsed.hostname:
            raise ValueError("INSO cdp_url must be a loopback http(s) URL")
        if not _is_loopback_host(cdp_parsed.hostname):
            raise ValueError("INSO cdp_url must point to a loopback address")
        if cdp_parsed.port is None:
            raise ValueError("INSO cdp_url must include an explicit port")
        if self.pagesize <= 0:
            raise ValueError("INSO pagesize must be positive")


# Form body captured from the live UI. The server ignores empty fields and
# rejects the request when ``BillDateType`` / ``leftlike`` / ``CompanyType`` /
# ``OwnerType`` are missing, so the body must be sent verbatim.
_INSO_STOCK_VENQUOTE_FORM = (
    "searchData[MainVendorID]=0"
    "&searchData[DetailField]=PartNo"
    "&searchData[DetailField_text]=%E5%9E%8B%E5%8F%B7"
    "&searchData[VendorID2]="
    "&searchData[CompanyName2]="
    "&searchData[DetailFieldValue]={MPN}"
    "&searchData[BillDateType]=all"
    "&searchData[BillDateType_text]=%E6%89%80%E6%9C%89%E6%97%A5%E6%9C%9F"
    "&searchData[VendorID]="
    "&searchData[CompanyName]="
    "&searchData[ImpValueF]="
    "&searchData[PENO]="
    "&searchData[StartBillDate]="
    "&searchData[EndBillDate]="
    "&searchData[leftlike]=on"
    "&searchData[CompanyType]=CompanyID"
    "&searchData[CompanyType_text]=%E6%8C%89%E5%85%AC%E5%8F%B8"
    "&searchData[CompanyTypeValue]="
    "&searchData[CompanyTypeValue_text]="
    "&searchData[OwnerType]=OwnerID"
    "&searchData[OwnerType_text]=%E6%8B%A5%E6%9C%89%E4%BA%BA"
    "&searchData[OwnerTypeValue]="
    "&searchData[OwnerTypeValue_text]="
    "&searchData[BuysOwnerID]="
    "&searchData[BuysOwnerID_text]="
    "&searchData[GroupID]="
    "&searchData[GroupID_text]="
    "&searchData[VenContact]="
    "&searchData[CusVenType]="
    "&searchData[StartAmount]="
    "&searchData[EndAmount]="
    "&searchData_More[VendorID2]="
    "&searchData_More[CompanyName2]="
    "&searchData_More[OwnerTypeValue2]="
    "&searchData_More[OwnerTypeValue2_text]="
    "&searchData_More[CompanyTypeValue2]="
    "&searchData_More[CompanyTypeValue2_text]="
    "&formData="
)


def _is_loopback_host(hostname: str) -> bool:
    if hostname.casefold() == "localhost":
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


def build_inso_stock_venquote_form(mpn: str) -> str:
    return _INSO_STOCK_VENQUOTE_FORM.replace("{MPN}", mpn)


def parse_inso_history_rows(rows: object) -> tuple[InsoHistoryRecord, ...]:
    """Parse the ``rows`` array from a ``Stock_VenQuote`` JSON response.

    Required fields per row: ``CreateTime`` (Asia/Shanghai string), ``InPrice``
    (string Decimal), ``CurrencyID`` (``RMB`` / ``USD``). Rows whose
    ``InPrice`` does not parse to a finite non-negative Decimal are skipped
    (an empty price means the supplier did not actually quote).
    """
    if not isinstance(rows, list):
        raise InsoReadError("HISTORY_ROWS_UNPARSEABLE")
    records: list[InsoHistoryRecord] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_date = row.get("CreateTime")
        raw_price = row.get("InPrice")
        raw_currency = row.get("CurrencyID")
        if not isinstance(raw_date, str) or not isinstance(raw_price, str):
            continue
        if raw_currency not in {"RMB", "USD"}:
            continue
        try:
            price = Decimal(raw_price.strip().replace(",", ""))
        except InvalidOperation:
            continue
        # InPrice == 0 means the supplier did not actually quote a price.
        if not price.is_finite() or price <= 0:
            continue
        try:
            observed = _parse_inso_datetime(raw_date)
        except InsoReadError:
            continue
        records.append(InsoHistoryRecord(price, raw_currency, observed))
    return tuple(records)


def _parse_inso_datetime(value: str) -> datetime:
    raw = value.strip()
    for pattern in (
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            parsed = datetime.strptime(raw, pattern).replace(
                tzinfo=timezone(timedelta(hours=8))
            )
            return parsed.astimezone(UTC)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise InsoReadError("HISTORY_DATE_UNPARSEABLE") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone(timedelta(hours=8)))
    return parsed.astimezone(UTC)


class PlaywrightInsoReadOnlyBrowser:
    """Concrete CDP-attached acquisition of Stock_VenQuote history."""

    def __init__(
        self,
        config: InsoBrowserConfig,
        *,
        timeout_ms: int = 45_000,
        settle_ms: int = 2_000,
        playwright_factory: Callable[[], object] | None = None,
    ) -> None:
        self._config = config
        self._timeout_ms = timeout_ms
        self._settle_ms = settle_ms
        self._playwright_factory = playwright_factory

    def fetch_procurement_temporary_inquiry_history(
        self, mpn: str, login: InsoLogin
    ) -> InsoHistoryCapture:
        del login  # CDP session is already authenticated by the Owner
        factory = self._playwright_factory
        timeout_error: type[Exception] = TimeoutError
        if factory is None:
            try:
                from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
                from playwright.sync_api import sync_playwright
            except ImportError as exc:
                raise InsoReadError("PLAYWRIGHT_NOT_INSTALLED") from exc
            factory = sync_playwright
            timeout_error = PlaywrightTimeoutError

        mpn_clean = mpn.strip()
        url = (
            f"{self._config.login_url.rstrip('/')}"
            "/services/stock/select.ashx"
            "?action=Stock_VenQuote"
            f"&para={mpn_clean}"
            "&DetailField=PartNo"
            "&BillPage=Stock_VenQuote"
            f"&pageindex=1&pagesize={self._config.pagesize}"
        )
        body = build_inso_stock_venquote_form(mpn_clean)

        try:
            with factory() as playwright:  # type: ignore[attr-defined]
                browser = playwright.chromium.connect_over_cdp(
                    self._config.cdp_url,
                    timeout=self._timeout_ms,
                )
                try:
                    pages: list[Any] = []
                    for ctx in browser.contexts:
                        pages.extend(ctx.pages)
                    page = next((p for p in pages if not p.is_closed()), None)
                    if page is None:
                        raise InsoReadError("CDP_NO_AVAILABLE_PAGE", url)
                    response = page.request.post(
                        url,
                        headers={
                            "Content-Type": (
                                "application/x-www-form-urlencoded; "
                                "charset=UTF-8"
                            ),
                            "X-Requested-With": "XMLHttpRequest",
                            "Referer": (
                                f"{self._config.login_url.rstrip('/')}"
                                "/skins/etaoerp//InnerEnquiry/YeWuXJ/List.aspx"
                            ),
                            "Accept": "application/json, text/javascript, */*; q=0.01",
                        },
                        data=body,
                        timeout=self._timeout_ms,
                    )
                    text = response.text()
                    if not text or text.strip() in {"{}", ""}:
                        raise InsoReadError("AUTHENTICATED_READ_EMPTY", url)
                    try:
                        payload = json.loads(text)
                    except json.JSONDecodeError as exc:
                        raise InsoReadError("RESPONSE_NOT_JSON", url) from exc
                    rows = payload.get("rows") if isinstance(payload, dict) else None
                    if rows is None:
                        raise InsoReadError("RESPONSE_ROWS_MISSING", url)
                    records = parse_inso_history_rows(rows)
                finally:
                    try:
                        browser.close()
                    except Exception:
                        pass
        except InsoReadError:
            raise
        except timeout_error as exc:
            raise InsoReadError("CDP_TIMEOUT", url) from exc
        except Exception as exc:
            raise InsoReadError("CDP_FAILURE", url) from exc

        return InsoHistoryCapture(records, url, datetime.now(UTC))


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

        try:
            quote = self._fx.get_quote()
            if not isinstance(quote, UsdRmbQuote):
                raise TypeError
        except (RuntimeError, TypeError, ValueError):
            return self._failure(
                target_mpn, capture.captured_at, "FX_QUOTE_UNAVAILABLE", capture.url
            )

        positive = tuple(
            record
            for record in capture.records
            if record.price > 0 and record.observed_at <= now
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
                        self._to_normalized_rmb(record, quote),
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

        normalized = self._to_normalized_rmb(selected, quote)
        candidate = PriceCandidate(
            ResearchSource.INSO,
            target_mpn.strip(),
            selected.price,
            selected.currency,
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
                EvidenceField("selected_native_price", str(selected.price)),
                EvidenceField("selected_currency", selected.currency),
                EvidenceField("fx_rate", quote.rate),
            ),
        )
        return SourceResult(
            ResearchSource.INSO, SourceOutcome.SUCCESS, evidence, candidate
        )

    @staticmethod
    def _to_normalized_rmb(record: InsoHistoryRecord, quote: UsdRmbQuote) -> Decimal:
        if record.currency == "RMB":
            return record.price
        # USD: multiply by RMB-per-USD rate
        return record.price * quote.rate

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