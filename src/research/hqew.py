"""Read-only HQEW cloud-price adapter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from ipaddress import ip_address
from typing import Protocol
from urllib.parse import quote, urlsplit

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

HQEW_RESULT_URL = "https://p.hqew.com/yunquote/"


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
    observed_at: datetime | None = None

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


def _is_loopback_hostname(hostname: str) -> bool:
    if hostname.casefold() == "localhost":
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


def _is_expected_result_url(url: str, mpn: str) -> bool:
    parsed = urlsplit(url)
    encoded_mpn = quote(mpn.strip(), safe="")
    expected_path = f"/yunquote/{encoded_mpn}.html"
    return _is_hqew_url(url) and parsed.path.casefold() == expected_path.casefold()


class CdpHqewClient:
    """Read HQEW through an Owner-authenticated ordinary Chrome session."""

    def __init__(
        self,
        *,
        cdp_url: str = "http://127.0.0.1:9222",
        timeout_ms: int = 45_000,
        settle_ms: int = 5_000,
        navigate: bool = True,
        playwright_factory: Callable[[], object] | None = None,
    ) -> None:
        hostname = urlsplit(cdp_url).hostname
        if hostname is None or not _is_loopback_hostname(hostname):
            raise HqewPageUnavailable("CDP_REMOTE_ENDPOINT_FORBIDDEN")
        self._cdp_url = cdp_url
        self._timeout_ms = timeout_ms
        self._settle_ms = settle_ms
        self._navigate = navigate
        self._playwright_factory = playwright_factory

    def fetch_first_page(self, mpn: str) -> HqewPage:
        mpn = mpn.strip()
        factory = self._playwright_factory
        timeout_error: type[Exception] = TimeoutError
        if factory is None:
            try:
                from playwright.sync_api import (
                    TimeoutError as PlaywrightTimeoutError,
                )
                from playwright.sync_api import sync_playwright
            except ImportError as error:
                raise HqewPageUnavailable("PLAYWRIGHT_NOT_INSTALLED") from error
            factory = sync_playwright
            timeout_error = PlaywrightTimeoutError

        target_url = build_hqew_result_url(mpn)
        current_url: str | None = None
        try:
            with factory() as playwright:  # type: ignore[attr-defined]
                browser = playwright.chromium.connect_over_cdp(
                    self._cdp_url,
                    timeout=self._timeout_ms,
                )
                if not browser.contexts:
                    raise HqewPageUnavailable("CDP_CONTEXT_UNAVAILABLE")
                context = browser.contexts[0]
                pages = list(context.pages)
                exact_pages = [
                    page for page in pages if _is_expected_result_url(page.url, mpn)
                ]

                if not self._navigate:
                    if not exact_pages:
                        raise HqewPageUnavailable("CDP_TARGET_PAGE_NOT_OPEN")
                    page = exact_pages[0]
                else:
                    hqew_pages = [page for page in pages if _is_hqew_url(page.url)]
                    if exact_pages:
                        page = exact_pages[0]
                    elif hqew_pages:
                        page = hqew_pages[0]
                    else:
                        page = context.new_page()
                    page.goto(
                        target_url,
                        wait_until="domcontentloaded",
                        timeout=self._timeout_ms,
                    )
                    page.wait_for_load_state("load", timeout=self._timeout_ms)
                    page.wait_for_timeout(self._settle_ms)

                current_url = page.url
                if page.locator("body").count() == 0:
                    raise HqewPageUnavailable("RESULT_PAGE_BLOCKED", current_url)
                html = page.content()
                if "安全验证" in html or "captcha-reset" in html:
                    raise HqewPageUnavailable(
                        "INTERACTIVE_CHALLENGE_REQUIRED", current_url
                    )
                if not _is_expected_result_url(current_url, mpn):
                    raise HqewPageUnavailable(
                        "RESULT_NAVIGATION_FAILED", current_url
                    )
                captured_at = datetime.now(UTC)
                return HqewPage(
                    html, current_url, captured_at
                )
        except HqewPageUnavailable:
            raise
        except timeout_error as error:
            raise HqewPageUnavailable("BROWSER_TIMEOUT", current_url) from error
        except Exception as error:
            raise HqewPageUnavailable("BROWSER_FAILURE", current_url) from error


class _OfferParser(HTMLParser):
    def __init__(self, reference_at: datetime) -> None:
        super().__init__(convert_charrefs=True)
        self.offers: list[HqewOffer] = []
        self._reference_at = reference_at

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "input":
            return
        values = {key.casefold(): value for key, value in attrs}
        classes = (values.get("class") or "").split()
        if "list-data" not in classes:
            return
        mpn = values.get("pmodel")
        raw_price = values.get("quotationprice")
        raw_date = values.get("quotationdate") or values.get("quotedate")
        if not mpn or not raw_price:
            return
        try:
            price = Decimal(raw_price)
        except InvalidOperation as exc:
            raise HqewParseError("PRICE_UNPARSEABLE") from exc
        try:
            observed_at = _parse_optional_date(raw_date, self._reference_at)
            self.offers.append(HqewOffer(mpn, price, observed_at))
        except ValueError as exc:
            raise HqewParseError("PRICE_INVALID") from exc


_CHINA_TZ = timezone(timedelta(hours=8))


def _parse_optional_date(
    value: str | None, reference_at: datetime
) -> datetime | None:
    if value is None or not value.strip():
        return None
    raw = value.strip()
    # Full date/time formats
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return (
                datetime.strptime(raw, pattern)
                .replace(tzinfo=_CHINA_TZ)
                .astimezone(UTC)
            )
        except ValueError:
            continue
    # Natural-language approximations relative to capture time
    lowered = raw.casefold()
    if lowered in {"今天", "今日"}:
        return reference_at.astimezone(_CHINA_TZ).astimezone(UTC)
    if lowered == "昨天":
        approx = reference_at - timedelta(days=1)
        return approx.astimezone(_CHINA_TZ).astimezone(UTC)
    if lowered == "前天":
        approx = reference_at - timedelta(days=2)
        return approx.astimezone(_CHINA_TZ).astimezone(UTC)
    if lowered in {"1周内", "一周内", "7天内", "最近一周"}:
        approx = reference_at - timedelta(days=6)
        return approx.astimezone(_CHINA_TZ).astimezone(UTC)
    # Year-month only: treat as the first day of that month in China time
    try:
        year, month = map(int, raw.split("-"))
        if 1 <= month <= 12:
            return datetime(year, month, 1, tzinfo=_CHINA_TZ).astimezone(UTC)
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HqewParseError("QUOTE_DATE_UNPARSEABLE") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_CHINA_TZ)
    return parsed.astimezone(UTC)


def parse_hqew_offers(
    html: str, *, reference_at: datetime | None = None
) -> tuple[HqewOffer, ...]:
    if "安全验证" in html or "captcha-reset" in html:
        raise HqewPageUnavailable("INTERACTIVE_CHALLENGE_REQUIRED")
    parser = _OfferParser(reference_at or datetime.now(UTC))
    parser.feed(html)
    if not parser.offers:
        # HQEW renders empty-result pages with either a merchant-focused message
        # or a generic "no data" / "no result" block.
        if any(
            marker in html
            for marker in ("暂无商家报价", "暂无数据", "无结果", "抱歉：您搜索的")
        ):
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
        now = self._clock()
        try:
            page = self._client.fetch_first_page(target_mpn)
            offers = parse_hqew_offers(page.html, reference_at=page.captured_at)
        except HqewError as exc:
            return self._failure(target_mpn, exc)
        matched = [
            offer
            for offer in offers
            if price_source_mpn_match(target_mpn, offer.mpn) is not None
        ]
        if not matched:
            outcome = SourceOutcome.NO_STRICT_MPN_MATCH
            candidate = None
            matched_mpn = None
        else:
            cutoff = calendar_month_cutoff(now)
            valid = [
                offer
                for offer in matched
                if offer.observed_at is None or cutoff <= offer.observed_at <= now
            ]
            if not valid:
                outcome = SourceOutcome.NO_VALID_PRICE
                candidate = None
                matched_mpn = matched[0].mpn
            else:
                selected = min(
                    valid,
                    key=lambda offer: (offer.unit_price_rmb, offer.mpn.casefold()),
                )
                match_kind = price_source_mpn_match(target_mpn, selected.mpn)
                outcome = SourceOutcome.SUCCESS
                matched_mpn = selected.mpn
                candidate = PriceCandidate(
                    ResearchSource.HQEW,
                    selected.mpn,
                    selected.unit_price_rmb,
                    "RMB",
                    selected.unit_price_rmb,
                    page.captured_at,
                    page.url,
                    (
                        selected.mpn
                        if match_kind is MpnMatchKind.SUFFIX
                        else None
                    ),
                )
        evidence = SourceEvidence(
            ResearchSource.HQEW,
            target_mpn,
            matched_mpn,
            outcome,
            page.captured_at,
            page.url,
            (
                EvidenceField("offers_inspected", len(offers)),
                EvidenceField("matched_mpn_offers", len(matched)),
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
