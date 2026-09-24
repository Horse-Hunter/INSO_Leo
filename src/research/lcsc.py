"""Read-only LCSC product-page adapter."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
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


class LcscNoMatchingProduct(LcscError):
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
    observed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class LcscPage:
    html: str = field(repr=False)
    url: str
    captured_at: datetime
    product: LcscProduct | None = field(default=None, repr=False)


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


class LcscBrowserClient:
    """Resolve a Chinese LCSC search result and verify its official product page."""

    def __init__(
        self,
        *,
        timeout_ms: int = 45_000,
        settle_ms: int = 4_000,
        browser_channel: str = "chrome",
        headless: bool = False,
        playwright_factory: Callable[[], object] | None = None,
    ) -> None:
        self._timeout_ms = timeout_ms
        self._settle_ms = settle_ms
        self._browser_channel = browser_channel
        self._headless = headless
        self._playwright_factory = playwright_factory

    def fetch_product_page(self, mpn: str) -> LcscPage:
        query = mpn.strip()
        search_url = "https://so.szlcsc.com/global.html?" + urlencode({"k": query})
        factory = self._playwright_factory
        timeout_error: type[Exception] = TimeoutError
        if factory is None:
            try:
                from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
                from playwright.sync_api import sync_playwright
            except ImportError as exc:
                raise LcscPageUnavailable("PLAYWRIGHT_NOT_INSTALLED") from exc
            factory = sync_playwright
            timeout_error = PlaywrightTimeoutError

        current_url: str | None = search_url
        browser = None
        try:
            with factory() as playwright:  # type: ignore[attr-defined]
                browser = playwright.chromium.launch(
                    channel=self._browser_channel,
                    headless=self._headless,
                )
                page = browser.new_page()
                page.goto(
                    search_url,
                    wait_until="domcontentloaded",
                    timeout=self._timeout_ms,
                )
                page.wait_for_timeout(self._settle_ms)
                current_url = page.url
                if urlsplit(current_url).hostname != "so.szlcsc.com":
                    raise LcscPageUnavailable("SEARCH_NAVIGATION_FAILED", current_url)
                search_html = page.content()
                _reject_lcsc_challenge(page.locator("body").inner_text(), current_url)
                product, product_id = parse_lcsc_search_product(search_html, query)

                product_url = f"https://item.szlcsc.com/{product_id}.html"
                page.goto(
                    product_url,
                    wait_until="domcontentloaded",
                    timeout=self._timeout_ms,
                )
                page.wait_for_timeout(self._settle_ms)
                current_url = page.url
                parsed = urlsplit(current_url)
                if (
                    parsed.hostname != "item.szlcsc.com"
                    or parsed.path != f"/{product_id}.html"
                ):
                    raise LcscPageUnavailable(
                        "PRODUCT_NAVIGATION_FAILED", current_url
                    )
                product_html = page.content()
                _reject_lcsc_challenge(page.locator("body").inner_text(), current_url)
                page_product, page_product_id = _parse_lcsc_product_page(
                    product_html
                )
                if (
                    page_product_id != product_id
                    or page_product.mpn.casefold() != product.mpn.casefold()
                ):
                    raise LcscParseError("PRODUCT_IDENTITY_MISMATCH", current_url)
                capture = LcscPage(
                    product_html,
                    current_url,
                    datetime.now(UTC),
                    product,
                )
                browser.close()
                browser = None
                return capture
        except LcscError:
            raise
        except timeout_error as exc:
            raise LcscPageUnavailable("BROWSER_TIMEOUT", current_url) from exc
        except Exception as exc:
            raise LcscPageUnavailable("BROWSER_FAILURE", current_url) from exc


def parse_lcsc_cooperation_card(text: str, target_mpn: str) -> LcscProduct | None:
    """Read a displayed cooperation-inventory card, including date and tiers."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or price_source_mpn_match(target_mpn, lines[0]) is None:
        return None
    try:
        date_index = lines.index("更新时间")
        stock_index = lines.index("库存")
        observed_at = datetime.strptime(
            lines[date_index + 1], "%Y年%m月%d日"
        ).replace(tzinfo=_CHINA_TZ).astimezone(UTC)
        stock = int(lines[stock_index + 1].replace(",", ""))
        tiers = tuple(
            LcscPriceTier(int(lines[index][:-1]), Decimal(lines[index + 1].lstrip("¥￥")), "CNY")
            for index in range(len(lines) - 1)
            if re.fullmatch(r"\d+\+", lines[index])
            and re.fullmatch(r"[¥￥]\d+(?:\.\d+)?", lines[index + 1])
        )
    except (ValueError, IndexError, InvalidOperation) as exc:
        raise LcscParseError("COOPERATION_CARD_UNPARSEABLE") from exc
    if not tiers:
        raise LcscParseError("COOPERATION_PRICE_MISSING")
    return LcscProduct(lines[0], False, stock, tiers, observed_at)


class CdpLcscClient:
    """Read LCSC search results in an authenticated Owner Chrome session."""

    def __init__(self, *, cdp_url: str = "http://127.0.0.1:9222", timeout_ms: int = 45_000) -> None:
        if urlsplit(cdp_url).hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("LCSC CDP endpoint must be loopback")
        self._cdp_url = cdp_url
        self._timeout_ms = timeout_ms

    def fetch_product_page(self, mpn: str) -> LcscPage:
        search_url = "https://so.szlcsc.com/global.html?" + urlencode({"k": mpn.strip()})
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise LcscPageUnavailable("PLAYWRIGHT_NOT_INSTALLED") from exc
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.connect_over_cdp(
                    self._cdp_url, timeout=self._timeout_ms
                )
                context = browser.contexts[0]
                pages = [page for page in context.pages if urlsplit(page.url).hostname == "so.szlcsc.com"]
                page = next((item for item in pages if item.locator("#login:visible").count() == 0), None)
                if page is None:
                    raise LcscPageUnavailable("AUTHENTICATED_SESSION_REQUIRED", search_url)
                page.goto(search_url, wait_until="domcontentloaded", timeout=self._timeout_ms)
                page.wait_for_timeout(3_000)
                if urlsplit(page.url).hostname != "so.szlcsc.com":
                    raise LcscPageUnavailable("SEARCH_NAVIGATION_FAILED", page.url)
                if page.locator("#login:visible").count():
                    raise LcscPageUnavailable("AUTHENTICATED_SESSION_REQUIRED", page.url)
                cards = page.locator('section[class*="OverseasCard"]')
                for _ in range(10):
                    if cards.count():
                        break
                    page.wait_for_timeout(1_000)
                for card in cards.all():
                    product = parse_lcsc_cooperation_card(card.inner_text(), mpn)
                    if product is not None:
                        return LcscPage("", page.url, datetime.now(UTC), product)
                product, _product_id = parse_lcsc_search_product(page.content(), mpn)
                return LcscPage("", page.url, datetime.now(UTC), product)
        except LcscError:
            raise
        except Exception as exc:
            raise LcscPageUnavailable("BROWSER_FAILURE", search_url) from exc


_NEXT_DATA = re.compile(
    r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def parse_lcsc_product(html: str) -> LcscProduct:
    product, _product_id = _parse_lcsc_product_page(html)
    return product


def _next_data(html: str) -> dict[str, object]:
    match = _NEXT_DATA.search(html)
    if not match:
        raise LcscParseError("NEXT_DATA_MISSING")
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise LcscParseError("PRODUCT_DATA_UNPARSEABLE") from exc
    if not isinstance(payload, dict):
        raise LcscParseError("PRODUCT_DATA_UNPARSEABLE")
    return payload


def _parse_lcsc_product_page(html: str) -> tuple[LcscProduct, str | None]:
    payload = _next_data(html)
    try:
        page_props = payload["props"]["pageProps"]  # type: ignore[index]
        data = page_props["webData"]
        if "productRecord" in data:
            record = data["productRecord"]
            mpn = record["productModel"]
            stock = record.get("stockNumber")
            product_id = str(record["productId"])
            raw_price = page_props.get("price")
            raw_tiers = (
                []
                if raw_price is None
                else [{"ladder": 1, "productPrice": raw_price}]
            )
            currency = "CNY"
            is_preorder = bool(record.get("isPreSale", False))
        else:
            record = data
            mpn = data["productModel"]
            stock = data.get("stockNumber")
            product_id = None
            raw_tiers = data["productPriceList"]
            currency = data["currencyType"]
            is_preorder = bool(data.get("isPreSale", False))
    except (KeyError, TypeError) as exc:
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
    if stock is not None and (isinstance(stock, bool) or not isinstance(stock, int)):
        raise LcscParseError("STOCK_UNPARSEABLE")
    observed_at = _parse_optional_date(
        record.get("quoteDate")
        or record.get("updateTime")
        or record.get("updatedAt")
    )
    return LcscProduct(
        mpn,
        is_preorder,
        stock,
        tuple(tiers),
        observed_at,
    ), product_id


def parse_lcsc_search_product(
    html: str, target_mpn: str
) -> tuple[LcscProduct, str]:
    payload = _next_data(html)
    try:
        records = payload["props"]["pageProps"]["soData"]["searchResult"][  # type: ignore[index]
            "productRecordList"
        ]
    except (KeyError, TypeError) as exc:
        raise LcscParseError("SEARCH_DATA_UNPARSEABLE") from exc
    if not isinstance(records, list):
        raise LcscParseError("SEARCH_DATA_UNPARSEABLE")

    matches: list[tuple[int, int, LcscProduct, str]] = []
    for item in records:
        try:
            vo = item["productVO"]
            mpn = vo["productModel"]
            product_id = str(vo["productId"])
            stock = vo.get("stockNumber")
        except (KeyError, TypeError):
            continue
        if not isinstance(mpn, str) or not product_id.isdecimal():
            continue
        match_kind = price_source_mpn_match(target_mpn, mpn)
        if match_kind is None:
            continue
        discount = item.get("priceDiscount")
        if isinstance(discount, dict) and discount.get("priceList"):
            raw_tiers = discount["priceList"]
            price_key, quantity_key = "price", "spNumber"
        else:
            raw_tiers = vo.get("productPriceList")
            price_key, quantity_key = "productPrice", "startPurchasedNumber"
        if not isinstance(raw_tiers, list):
            raise LcscParseError("PRICE_TIERS_UNPARSEABLE")
        try:
            tiers = tuple(
                LcscPriceTier(
                    int(tier[quantity_key]),
                    Decimal(str(tier[price_key])),
                    "CNY",
                )
                for tier in raw_tiers
            )
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            raise LcscParseError("PRICE_TIERS_UNPARSEABLE") from exc
        if stock is not None and (isinstance(stock, bool) or not isinstance(stock, int)):
            raise LcscParseError("STOCK_UNPARSEABLE")
        suffix_length = len(mpn.strip()) - len(target_mpn.strip())
        product = LcscProduct(
            mpn,
            bool(vo.get("isPreSale", False)),
            stock,
            tiers,
        )
        matches.append(
            (
                0 if match_kind is MpnMatchKind.EXACT else 1,
                suffix_length,
                product,
                product_id,
            )
        )
    if not matches:
        raise LcscNoMatchingProduct("NO_MATCHING_PRODUCT")
    _rank, _suffix, product, product_id = min(
        matches, key=lambda value: (value[0], value[1], int(value[3]))
    )
    return product, product_id


def _reject_lcsc_challenge(visible_text: str, url: str) -> None:
    folded = visible_text.casefold()
    if any(
        marker in folded
        for marker in ("access denied", "captcha", "安全验证", "访问过于频繁")
    ):
        raise LcscPageUnavailable("INTERACTIVE_CHALLENGE_REQUIRED", url)


_CHINA_TZ = timezone(timedelta(hours=8))


def _parse_optional_date(value: object) -> datetime | None:
    if value is None or not isinstance(value, str) or not value.strip():
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
        raise LcscParseError("QUOTE_DATE_UNPARSEABLE") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_CHINA_TZ)
    return parsed.astimezone(UTC)


def select_lcsc_tier(
    tiers: tuple[LcscPriceTier, ...], quantity: int
) -> LcscPriceTier | None:
    del quantity
    applicable = [tier for tier in tiers if tier.currency in {"USD", "RMB", "CNY"}]
    return (
        min(applicable, key=lambda tier: (tier.unit_price, tier.break_quantity))
        if applicable
        else None
    )


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
            product = page.product or parse_lcsc_product(page.html)
        except LcscNoMatchingProduct as exc:
            return self._no_result(target_mpn, exc)
        except LcscError as exc:
            return self._failure(target_mpn, exc)
        match = price_source_mpn_match(target_mpn, product.mpn)
        if match is None:
            return self._result(
                target_mpn,
                page,
                product,
                SourceOutcome.NO_STRICT_MPN_MATCH,
                None,
                None,
                None,
            )
        now = self._clock()
        if product.observed_at is not None and not (
            calendar_month_cutoff(now) <= product.observed_at <= now
        ):
            return self._result(
                target_mpn,
                page,
                product,
                SourceOutcome.NO_VALID_PRICE,
                None,
                None,
                None,
            )
        tier = select_lcsc_tier(product.tiers, customer_quantity)
        if tier is None or tier.currency not in {"USD", "RMB", "CNY"}:
            return self._result(
                target_mpn,
                page,
                product,
                SourceOutcome.NO_VALID_PRICE,
                None,
                None,
                None,
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
            product.mpn if match is MpnMatchKind.SUFFIX else None,
        )
        stocked = (
            product.stock_quantity is not None
            and product.stock_quantity > 0
            and not product.is_preorder
        )
        return self._result(
            target_mpn,
            page,
            product,
            SourceOutcome.SUCCESS,
            candidate if stocked else None,
            candidate if not stocked else None,
            quote,
            tier,
        )

    def _result(
        self,
        query: str,
        page: LcscPage,
        product: LcscProduct,
        outcome: SourceOutcome,
        candidate: PriceCandidate | None,
        out_of_stock_candidate: PriceCandidate | None,
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
                (
                    candidate.normalized_rmb_price
                    if candidate
                    else out_of_stock_candidate.normalized_rmb_price
                    if out_of_stock_candidate
                    else None
                ),
            ),
        )
        evidence = SourceEvidence(
            ResearchSource.LCSC,
            query,
            product.mpn if price_source_mpn_match(query, product.mpn) else None,
            outcome,
            page.captured_at,
            page.url,
            fields,
        )
        return SourceResult(
            ResearchSource.LCSC,
            outcome,
            evidence,
            candidate,
            out_of_stock_candidate,
        )

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

    def _no_result(self, query: str, exc: LcscError) -> SourceResult:
        evidence = SourceEvidence(
            ResearchSource.LCSC,
            query,
            None,
            SourceOutcome.NO_VALID_PRICE,
            self._clock(),
            exc.source_url,
            (EvidenceField("records_inspected", 0),),
        )
        return SourceResult(
            ResearchSource.LCSC, SourceOutcome.NO_VALID_PRICE, evidence
        )
