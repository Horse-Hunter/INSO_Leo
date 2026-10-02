"""Read-only LCSC product-page adapter."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from time import monotonic, sleep
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from .cdp_pages import new_background_page
from .fx import UsdRmbProvider, UsdRmbQuote
from .site_login import (
    REJECTED_PASSWORD_TEXT,
    LoginForm,
    SiteLoginError,
    await_login_outcome,
    submit_login_form,
)
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
LCSC_HOME_URL = "https://www.szlcsc.com/"
# Core Vault indexes the existing LCSC credential by the commerce site, not
# by JLC's separate SSO redirect host. Keep these identities intentionally
# distinct so session recovery never asks the Owner to duplicate a password.
LCSC_CREDENTIAL_SITE_ID = "szlcsc.com"
LCSC_AUTH_HOST = "passport.jlc.com"
#: JLC's own SSO host. It serves two different pages -- the ordinary account
#: form, and an already-signed-in account that only needs handing over to the
#: commerce site -- which is why callers have to look at the page, not the URL.
LCSC_LOGIN_URL = f"https://{LCSC_AUTH_HOST}/login"

#: JLC's ordinary account form. The page also offers QR and SMS paths; this
#: form is only ever addressed after the "账号登录" tab has been opened.
#: ``submit`` must name the account form's own button
#: (``<button class="el-button base-button w-full submit …">登录</button>``,
#: tracked by JLC as ``spm=login.account.submit``), never the text "登录": that
#: text also matches the page's ``<h2>`` heading, which comes first in DOM
#: order, so a page-level click landed on the heading and the button was never
#: pressed (measured live 2026-10-01).
LCSC_LOGIN_FORM = LoginForm(
    username='input[type="text"]:visible, input[type="tel"]:visible',
    password='input[type="password"]:visible',
    submit="button.submit",
    # Measured live 2026-10-01: JLC answers a login it distrusts with a slider --
    # "安全验证 / 为了您的账号安全，请完成验证 / 请按住滑块，拖动到最右边". Both
    # markers were confirmed *absent* from the rendered page before the submit
    # (body length 212, neither string present), so looking for them here cannot
    # refuse a form that was never tried.
    challenge_text=("安全验证", "请按住滑块"),
    rejection=REJECTED_PASSWORD_TEXT,
    # Measured live 2026-10-01: the challenge widget is injected only when the
    # risk engine fires, and its copy is in no eagerly-loaded bundle, so the
    # markup cannot be read ahead of time. These are the vendor marks JLC's
    # wording ("请按住滑块，拖动到最右边") comes from; if they all miss,
    # ``solve_slider_challenge`` falls back to the one element the page itself
    # marks draggable, and refuses when that is not unique.
    slider=(
        "#nc_1_n1z",
        ".nc_iconfont.btn_slide",
        "#nc_1_n1z span",
        "[class*='slide'] [class*='btn']",
        "[class*='slider'] [class*='btn']",
    ),
)


def lcsc_login_page_open(page: object) -> bool:
    """Settle predicate: has JLC's own script carried us off the SSO host?"""

    return urlsplit(getattr(page, "url", "") or "").hostname == LCSC_AUTH_HOST


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
class LcscLogin:
    """An in-memory JLC ordinary-login supplied by Core Vault."""

    username: str = field(repr=False)
    password: str = field(repr=False)


class LcscLoginProvider(Protocol):
    def get_login(self, site_id: str) -> LcscLogin | None: ...


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
        stock_index = lines.index("库存")
        observed_at = None
        if "更新时间" in lines:
            date_index = lines.index("更新时间")
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

    def __init__(
        self,
        *,
        cdp_url: str = "http://127.0.0.1:9222",
        timeout_ms: int = 45_000,
        login_provider: LcscLoginProvider | None = None,
        playwright_factory: Callable[[], object] | None = None,
    ) -> None:
        if urlsplit(cdp_url).hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("LCSC CDP endpoint must be loopback")
        self._cdp_url = cdp_url
        self._timeout_ms = timeout_ms
        self._login_provider = login_provider
        self._playwright_factory = playwright_factory

    def fetch_product_page(self, mpn: str) -> LcscPage:
        search_url = "https://so.szlcsc.com/global.html?" + urlencode({"k": mpn.strip()})
        factory = self._playwright_factory
        if factory is None:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError as exc:
                raise LcscPageUnavailable("PLAYWRIGHT_NOT_INSTALLED") from exc
            factory = sync_playwright
        try:
            with factory() as playwright:  # type: ignore[attr-defined]
                browser = playwright.chromium.connect_over_cdp(
                    self._cdp_url, timeout=self._timeout_ms
                )
                context = browser.contexts[0]
                # Owner rule (2026-10-01): every call opens its own tab, makes
                # sure it is signed in, does its work, and gives the tab back.
                page = new_background_page(
                    browser, context, timeout_ms=self._timeout_ms
                )
                try:
                    # A fresh CDP target has no site document yet. Initializing
                    # the ordinary LCSC home page lets its existing SSO
                    # cookies establish before the actual search.
                    page.goto(
                        LCSC_HOME_URL,
                        wait_until="domcontentloaded",
                        timeout=self._timeout_ms,
                    )
                    page.wait_for_timeout(1_000)
                    page.goto(search_url, wait_until="domcontentloaded", timeout=self._timeout_ms)
                    page.wait_for_timeout(3_000)
                    if urlsplit(page.url).hostname == LCSC_AUTH_HOST:
                        if not lcsc_enter_system_if_offered(
                            page, timeout_ms=self._timeout_ms
                        ):
                            self._restore_session(page)
                        # Authentication may return to a landing page. Re-run
                        # the original query exactly once after either SSO handoff
                        # or a Vault-backed ordinary login.
                        page.goto(
                            search_url,
                            wait_until="domcontentloaded",
                            timeout=self._timeout_ms,
                        )
                        page.wait_for_timeout(3_000)
                    if urlsplit(page.url).hostname != "so.szlcsc.com":
                        raise LcscPageUnavailable("SEARCH_NAVIGATION_FAILED", page.url)
                    body = page.locator("body").inner_text()
                    _reject_lcsc_challenge(body, page.url)
                    cards = page.locator('section[class*="OverseasCard"]')
                    for _ in range(10):
                        if cards.count():
                            break
                        page.wait_for_timeout(1_000)
                    for card in cards.all():
                        product = parse_lcsc_cooperation_card(card.inner_text(), mpn)
                        if product is not None:
                            return LcscPage("", page.url, datetime.now(UTC), product)
                    try:
                        product, _product_id = parse_lcsc_search_product(
                            page.content(), mpn
                        )
                    except LcscParseError:
                        # A same-host login shell can look like a changed
                        # search document. Recover only when the actual normal
                        # account form is present, and re-run the query once.
                        if not has_normal_lcsc_login_form(page):
                            raise
                        self._restore_session(page)
                        page.goto(
                            search_url,
                            wait_until="domcontentloaded",
                            timeout=self._timeout_ms,
                        )
                        page.wait_for_timeout(3_000)
                        if urlsplit(page.url).hostname != "so.szlcsc.com":
                            raise LcscPageUnavailable(
                                "SEARCH_NAVIGATION_FAILED", page.url
                            )
                        _reject_lcsc_challenge(
                            page.locator("body").inner_text(), page.url
                        )
                        product, _product_id = parse_lcsc_search_product(
                            page.content(), mpn
                        )
                    return LcscPage("", page.url, datetime.now(UTC), product)
                finally:
                    page.close()
        except LcscError:
            raise
        except Exception as exc:
            raise LcscPageUnavailable("BROWSER_FAILURE", search_url) from exc

    def _restore_session(self, page: object) -> None:
        """Perform one ordinary JLC account login, never a QR/OTP flow.

        The login itself lives in :func:`ensure_lcsc_signed_in` so the sell
        sweep signs in exactly the way a price read does; only the translation
        into this client's own error type belongs here.
        """

        if self._login_provider is None:
            raise LcscPageUnavailable("LOGIN_REQUIRED")
        login = self._login_provider.get_login(LCSC_CREDENTIAL_SITE_ID)
        if login is None:
            raise LcscPageUnavailable("LOGIN_REQUIRED")
        try:
            ensure_lcsc_signed_in(
                page,
                login=login,
                timeout_ms=self._timeout_ms,
            )
        except SiteLoginError as error:
            raise LcscPageUnavailable(
                error.reason_code, page.url  # type: ignore[attr-defined]
            ) from None


def lcsc_enter_system_if_offered(page: object, *, timeout_ms: int) -> bool:
    """Take JLC's SSO handoff when the page is offering it, and say whether it did.

    ``passport.jlc.com`` serves two different things under one URL. For an
    account that is already signed in there -- measured live 2026-10-01 -- it
    prints 「已登录账号 … 点击【进入系统】」 and hands the browser to the commerce
    site; for anyone else it shows the ordinary account form. Only the first is
    a handoff, so that is what the page's own wording is used to tell apart.
    """

    try:
        body = page.locator("body").inner_text()  # type: ignore[attr-defined]
        enter = page.get_by_text("进入系统", exact=True)  # type: ignore[attr-defined]
        if "已登录账号" not in body or enter.count() != 1:
            return False
        enter.click(timeout=timeout_ms)
    except Exception:  # noqa: BLE001 - only an auth hint, never a failure
        return False
    return True


def ensure_lcsc_signed_in(
    page: object,
    *,
    login: LcscLogin | None,
    timeout_ms: int,
    wait: Callable[[float], None] = sleep,
    clock: Callable[[], float] = monotonic,
) -> None:
    """Complete one ordinary JLC account login on a page parked on the SSO host.

    Only "open JLC's own account tab" is LCSC-specific; typing, the challenge
    refusal and the settle wait all come from the shared
    implementation so one fix reaches every source. Fails closed with a
    :class:`SiteLoginError`: the caller decides what a given reason code means.
    """

    if login is None:
        raise SiteLoginError("CREDENTIALS_UNAVAILABLE")
    account_tab = page.get_by_text("账号登录", exact=True)  # type: ignore[attr-defined]
    if account_tab.count() != 1:
        raise SiteLoginError("RESULT_CHANGED")
    try:
        account_tab.click(timeout=timeout_ms)
    except Exception as error:
        raise SiteLoginError("LOGIN_FORM_UNAVAILABLE") from error
    # CAPTCHA/slider/OTP belongs to the operator, not automated login.
    submit_login_form(page, form=LCSC_LOGIN_FORM, login=login, timeout_ms=timeout_ms)
    await_login_outcome(
        page, form=LCSC_LOGIN_FORM, is_login_page=lcsc_login_page_open,
        timeout_ms=timeout_ms, wait=wait, clock=clock,
    )
    _reject_lcsc_challenge(
        page.locator("body").inner_text(),  # type: ignore[attr-defined]
        page.url,  # type: ignore[attr-defined]
    )
    if urlsplit(page.url).hostname == LCSC_AUTH_HOST:  # type: ignore[attr-defined]
        raise SiteLoginError("LOGIN_NOT_CONFIRMED")


def has_normal_lcsc_login_form(page: object) -> bool:
    """Recognize the site's ordinary account form without URL guessing.

    Kept next to :func:`ensure_lcsc_signed_in` because it answers the same
    question the login does -- "is this JLC asking for a password?" -- rather
    than the adapter's "is this a result page?".
    """

    try:
        account_tab = page.get_by_text("账号登录", exact=True)  # type: ignore[attr-defined]
        password = page.locator('input[type="password"]:visible')  # type: ignore[attr-defined]
        return account_tab.count() == 1 and password.count() == 1
    except Exception:  # noqa: BLE001 - only an auth hint, never a failure
        return False


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
        suffix_length = len(re.sub(r"[\s-]", "", mpn)) - len(
            re.sub(r"[\s-]", "", target_mpn)
        )
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
