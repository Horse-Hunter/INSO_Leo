"""Read-only INSO procurement-temporary-inquiry history price source."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Protocol
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


@dataclass(frozen=True, slots=True)
class InsoBrowserConfig:
    """Runtime selectors for the approved read-only INSO query screen."""

    login_url: str
    username_selector: str
    password_selector: str
    login_button_selector: str
    mpn_selector: str
    query_button_selector: str
    company_selector: str | None = None
    date_headers: tuple[str, ...] = (
        "询价时间",
        "报价时间",
        "更新时间",
        "创建时间",
        "日期",
    )

    def __post_init__(self) -> None:
        parsed = urlsplit(self.login_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("INSO login_url must be HTTPS")
        required = (
            self.username_selector,
            self.password_selector,
            self.login_button_selector,
            self.mpn_selector,
            self.query_button_selector,
        )
        if any(not value.strip() for value in required):
            raise ValueError("INSO selectors must not be blank")


class PlaywrightInsoReadOnlyBrowser:
    """Concrete login/navigation/query acquisition with no write capability."""

    def __init__(
        self,
        config: InsoBrowserConfig,
        *,
        timeout_ms: int = 45_000,
        settle_ms: int = 2_000,
        browser_channel: str = "chrome",
        headless: bool = False,
        playwright_factory: Callable[[], object] | None = None,
    ) -> None:
        self._config = config
        self._timeout_ms = timeout_ms
        self._settle_ms = settle_ms
        self._browser_channel = browser_channel
        self._headless = headless
        self._playwright_factory = playwright_factory

    def fetch_procurement_temporary_inquiry_history(
        self, mpn: str, login: InsoLogin
    ) -> InsoHistoryCapture:
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

        browser = None
        current_url: str | None = self._config.login_url
        expected_host = urlsplit(self._config.login_url).hostname
        try:
            with factory() as playwright:  # type: ignore[attr-defined]
                browser = playwright.chromium.launch(
                    channel=self._browser_channel,
                    headless=self._headless,
                )
                page = browser.new_page()
                page.goto(
                    self._config.login_url,
                    wait_until="domcontentloaded",
                    timeout=self._timeout_ms,
                )
                current_url = page.url
                self._require_expected_host(current_url, expected_host)
                self._reject_challenge(page.content(), current_url)

                username = page.locator(self._config.username_selector)
                if username.count() > 0:
                    username.fill(login.username)
                    page.locator(self._config.password_selector).fill(login.password)
                    if self._config.company_selector is not None:
                        company = page.locator(self._config.company_selector)
                        if company.count() > 0:
                            if login.company is None:
                                raise InsoReadError(
                                    "COMPANY_CREDENTIAL_UNAVAILABLE", current_url
                                )
                            company.fill(login.company)
                    page.locator(self._config.login_button_selector).click()
                    page.wait_for_timeout(self._settle_ms)
                    current_url = page.url
                    self._require_expected_host(current_url, expected_host)
                    self._reject_challenge(page.content(), current_url)

                page.get_by_text("1.业务询价", exact=True).click()
                page.get_by_text("采购临时询价", exact=True).click()
                page.locator(self._config.mpn_selector).fill(mpn.strip())
                page.locator(self._config.query_button_selector).click()
                page.wait_for_timeout(self._settle_ms)
                current_url = page.url
                self._require_expected_host(current_url, expected_host)
                self._reject_challenge(page.content(), current_url)
                rows = page.evaluate(
                    _INSO_TABLE_READER,
                    {
                        "priceHeader": "供方未税价",
                        "dateHeaders": list(self._config.date_headers),
                    },
                )
                records = parse_inso_history_rows(rows)
                capture = InsoHistoryCapture(
                    records, current_url, datetime.now(UTC)
                )
                browser.close()
                browser = None
                return capture
        except InsoReadError:
            raise
        except timeout_error as exc:
            raise InsoReadError("BROWSER_TIMEOUT", current_url) from exc
        except Exception as exc:
            raise InsoReadError("BROWSER_FAILURE", current_url) from exc

    @staticmethod
    def _require_expected_host(url: str, expected_host: str | None) -> None:
        if urlsplit(url).hostname != expected_host:
            raise InsoReadError("UNEXPECTED_NAVIGATION_HOST", url)

    @staticmethod
    def _reject_challenge(html: str, url: str) -> None:
        folded = html.casefold()
        if any(
            marker in folded
            for marker in ("captcha", "验证码", "安全验证", "一次性密码", "otp")
        ):
            raise InsoReadError("INTERACTIVE_CHALLENGE_REQUIRED", url)


_INSO_TABLE_READER = """
({priceHeader, dateHeaders}) => {
  const clean = (value) => (value || '').replace(/\\s+/g, ' ').trim();
  for (const table of document.querySelectorAll('table')) {
    const headers = Array.from(table.querySelectorAll('thead th')).map(
      (cell) => clean(cell.innerText)
    );
    const priceIndex = headers.indexOf(priceHeader);
    const dateIndex = headers.findIndex((header) => dateHeaders.includes(header));
    if (priceIndex < 0) continue;
    if (dateIndex < 0) throw new Error('INSO_DATE_COLUMN_MISSING');
    return Array.from(table.querySelectorAll('tbody tr')).map((row) => {
      const cells = Array.from(row.querySelectorAll('td'));
      return {
        observed_at: clean(cells[dateIndex]?.innerText),
        supplier_untaxed_price: clean(cells[priceIndex]?.innerText),
      };
    });
  }
  throw new Error('INSO_HISTORY_TABLE_MISSING');
}
"""


def parse_inso_history_rows(rows: object) -> tuple[InsoHistoryRecord, ...]:
    """Parse only date and 供方未税价 from an already-scoped result table."""

    if not isinstance(rows, list):
        raise InsoReadError("HISTORY_ROWS_UNPARSEABLE")
    records: list[InsoHistoryRecord] = []
    for row in rows:
        if not isinstance(row, dict):
            raise InsoReadError("HISTORY_ROWS_UNPARSEABLE")
        raw_date = row.get("observed_at")
        raw_price = row.get("supplier_untaxed_price")
        if not isinstance(raw_date, str) or not isinstance(raw_price, str):
            raise InsoReadError("HISTORY_ROWS_UNPARSEABLE")
        try:
            price = Decimal(
                raw_price.strip().replace(",", "").removeprefix("$").strip()
            )
        except InvalidOperation as exc:
            raise InsoReadError("SUPPLIER_UNTAXED_PRICE_UNPARSEABLE") from exc
        observed_at = _parse_inso_datetime(raw_date)
        records.append(InsoHistoryRecord(price, observed_at))
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
