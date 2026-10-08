"""Read-only Findchips price adapter and server-rendered HTML parser."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from time import monotonic, sleep
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlsplit
from urllib.request import Request, urlopen

from src.core.mpn import lookup_mpn_prefix

from .cdp_pages import new_background_page
from .fx import UsdRmbProvider, UsdRmbQuote
from .site_login import (
    REJECTED_PASSWORD_TEXT,
    LoginForm,
    SiteLoginError,
    await_login_outcome,
    challenge_present,
    submit_login_form,
    unique_visible_control,
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

FINDCHIPS_SEARCH_URL = "https://www.findchips.com/search/"
FINDCHIPS_USER_AGENT = "INSO-Leo-Research/1.0 (read-only Findchips adapter)"
#: Canonical credential site id; matches the entry in the Core vault.
FINDCHIPS_SITE_ID = "findchips.com"
FINDCHIPS_LOGIN_URL = "https://www.findchips.com/signin"

#: Findchips' ordinary sign-in form. It asks for nothing else -- no captcha and
#: no company field -- but any future gate is declared as a challenge so the
#: shared submit refuses to run blind.
FINDCHIPS_LOGIN_FORM = LoginForm(
    username="#email-address",
    password="#password",
    submit="#j-signin button.signin",
    # English wording on top of the shared set: this site is the only one whose
    # refusal is not in Chinese.
    rejection=(*REJECTED_PASSWORD_TEXT, "incorrect password", "invalid password"),
)


class FindchipsError(RuntimeError):
    """Base class for safe Findchips acquisition and parsing failures."""

    def __init__(self, code: str, source_url: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.source_url = source_url


class FindchipsPageUnavailable(FindchipsError):
    """The approved HTTP path could not return a usable result page."""


class FindchipsParseError(FindchipsError):
    """The server-rendered result document could not be parsed reliably."""


@dataclass(frozen=True, slots=True)
class FindchipsPriceTier:
    """One displayed quantity-break unit-price tier."""

    break_quantity: int
    unit_price: Decimal
    currency: str

    def __post_init__(self) -> None:
        if self.break_quantity <= 0:
            raise ValueError("break_quantity must be greater than zero")
        if not isinstance(self.unit_price, Decimal):
            raise TypeError("unit_price must be Decimal")
        if not self.unit_price.is_finite() or self.unit_price <= 0:
            raise ValueError("unit_price must be finite and greater than zero")
        if not self.currency.strip():
            raise ValueError("currency must not be blank")


@dataclass(frozen=True, slots=True)
class FindchipsOffer:
    """Minimum safe offer data; concrete stock and MOQ are intentionally absent."""

    mpn: str
    stock_positive: bool | None
    tiers: tuple[FindchipsPriceTier, ...] = ()
    observed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class FindchipsPage:
    """One in-memory Findchips search result capture."""

    html: str = field(repr=False)
    url: str
    captured_at: datetime


@dataclass(frozen=True, slots=True)
class FindchipsLogin:
    """An in-memory Findchips login supplied by the project Credential Provider."""

    username: str = field(repr=False)
    password: str = field(repr=False)


class FindchipsLoginProvider(Protocol):
    """Research-facing credential capability; storage details stay in Core."""

    def get_login(self, site_id: str) -> FindchipsLogin | None:
        """Return one configured login without logging or persisting it."""


class FindchipsPageClient(Protocol):
    """Acquisition boundary replaced by fixtures in default tests."""

    def fetch_first_page(self, mpn: str) -> FindchipsPage:
        """Return one normal public Findchips search page."""


def build_findchips_search_url(mpn: str) -> str:
    """Build the native prefix search while retaining full targets in adapters."""

    return f"{FINDCHIPS_SEARCH_URL}{quote(lookup_mpn_prefix(mpn), safe='')}"


def _is_findchips_response_url(url: str) -> bool:
    try:
        hostname = urlsplit(url).hostname
    except ValueError:
        return False
    if hostname is None:
        return False
    normalized = hostname.casefold()
    return normalized == "findchips.com" or normalized.endswith(".findchips.com")


def _is_findchips_login_page(html: str) -> bool:
    folded = html.casefold()
    return (
        ("type=\"password\"" in folded or "type='password'" in folded)
        and "login" in folded
    )


def _is_findchips_signin_url(url: str) -> bool:
    """True while the tab is still on Findchips' sign-in path."""

    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    return (parsed.path or "").casefold().startswith("/signin")


def findchips_login_page_open(page: object) -> bool:
    """Settle predicate: has Findchips' own script carried us off the form?"""

    return _is_findchips_signin_url(getattr(page, "url", "") or "")


def _findchips_login_pending(page: object) -> bool:
    """Recognize the site's explicit post-login refusal without leaking its text."""
    parsed = urlsplit(getattr(page, "url", "") or "")
    if _is_findchips_response_url(parsed.geturl()) and _is_findchips_signin_url(parsed.geturl()):
        errors = parse_qs(parsed.query).get("login_error", ())
        errors = [value.casefold() for value in errors
                  if value.strip() and value.casefold() not in {"0", "false"}]
        if errors:
            if any("captcha" in value for value in errors):
                raise SiteLoginError("MANUAL_VERIFICATION_REQUIRED")
            raise SiteLoginError("LOGIN_REJECTED")
    return findchips_login_page_open(page)


class FindchipsHttpClient:
    """Bounded ordinary-HTTP client for one public Findchips search page."""

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self._timeout_seconds = timeout_seconds

    def fetch_first_page(self, mpn: str) -> FindchipsPage:
        target_url = build_findchips_search_url(mpn)
        request = Request(
            target_url,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": FINDCHIPS_USER_AGENT,
            },
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                response_url = response.geturl()
                if not _is_findchips_response_url(response_url):
                    raise FindchipsPageUnavailable(
                        "UNEXPECTED_RESPONSE_HOST",
                        response_url,
                    )
                if response.status != 200:
                    raise FindchipsPageUnavailable(
                        "HTTP_STATUS_UNEXPECTED",
                        response_url,
                    )
                if response.headers.get_content_type() != "text/html":
                    raise FindchipsPageUnavailable(
                        "CONTENT_TYPE_UNEXPECTED",
                        response_url,
                    )
                encoding = response.headers.get_content_charset() or "utf-8"
                html = response.read().decode(encoding, errors="replace")
                if not html.strip():
                    raise FindchipsPageUnavailable(
                        "EMPTY_RESPONSE",
                        response_url,
                    )
                if _is_findchips_login_page(html):
                    raise FindchipsPageUnavailable("LOGIN_REQUIRED", response_url)
                return FindchipsPage(
                    html=html,
                    url=response_url,
                    captured_at=datetime.now(UTC),
                )
        except FindchipsPageUnavailable:
            raise
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise FindchipsPageUnavailable(
                "HTTP_REQUEST_FAILED",
                target_url,
            ) from error


class CdpFindchipsClient:
    """Read a public result in a temporary background tab in approved Chrome."""

    def __init__(
        self,
        *,
        cdp_url: str = "http://127.0.0.1:9222",
        timeout_ms: int = 45_000,
        login_provider: FindchipsLoginProvider | None = None,
        playwright_factory: Callable[[], object] | None = None,
    ) -> None:
        parsed = urlsplit(cdp_url)
        if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Findchips CDP endpoint must be loopback")
        self._cdp_url = cdp_url
        self._timeout_ms = timeout_ms
        self._login_provider = login_provider
        self._playwright_factory = playwright_factory

    def fetch_first_page(self, mpn: str) -> FindchipsPage:
        target_url = build_findchips_search_url(mpn)
        factory = self._playwright_factory
        if factory is None:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError as error:
                raise FindchipsPageUnavailable("PLAYWRIGHT_NOT_INSTALLED") from error
            factory = sync_playwright
        try:
            with factory() as playwright:  # type: ignore[attr-defined]
                browser = playwright.chromium.connect_over_cdp(
                    self._cdp_url, timeout=self._timeout_ms
                )
                if not browser.contexts:
                    raise FindchipsPageUnavailable("CDP_CONTEXT_UNAVAILABLE", target_url)
                context = browser.contexts[0]
                page = new_background_page(
                    browser,
                    context,
                    timeout_ms=self._timeout_ms,
                )
                try:
                    html, current_url = self._load_result(page, target_url)
                    if _is_findchips_login_page(html):
                        # Owner rule (2026-10-01): a login wall is a session
                        # problem to solve, never a business answer. Sign in,
                        # then ask the site for the result again.
                        self._sign_in(page)
                        html, current_url = self._load_result(page, target_url)
                        if _is_findchips_login_page(html):
                            raise FindchipsPageUnavailable(
                                "LOGIN_NOT_CONFIRMED", current_url
                            )
                    return FindchipsPage(html, current_url, datetime.now(UTC))
                finally:
                    page.close()
        except FindchipsPageUnavailable:
            raise
        except Exception as error:
            raise FindchipsPageUnavailable("BROWSER_FAILURE", target_url) from error

    def _load_result(self, page: object, target_url: str) -> tuple[str, str]:
        """Fetch the result page and say plainly whether it is usable.

        A document that turns out to be the sign-in page is returned rather
        than raised: whether it is a problem depends on whether a login can
        still be established, and that is the caller's decision.
        """

        page.goto(  # type: ignore[attr-defined]
            target_url,
            wait_until="domcontentloaded",
            timeout=self._timeout_ms,
        )
        page.wait_for_load_state("load", timeout=self._timeout_ms)  # type: ignore[attr-defined]
        page.wait_for_timeout(4_000)  # type: ignore[attr-defined]
        current_url = page.url  # type: ignore[attr-defined]
        if not _is_findchips_response_url(current_url):
            raise FindchipsPageUnavailable("UNEXPECTED_RESPONSE_HOST", current_url)
        html = page.content()  # type: ignore[attr-defined]
        if not html.strip():
            raise FindchipsPageUnavailable("EMPTY_RESPONSE", current_url)
        return html, current_url

    def _sign_in(self, page: object) -> None:
        """Establish Findchips' own login once, or say why it cannot be done."""

        provider = self._login_provider
        login = provider.get_login(FINDCHIPS_SITE_ID) if provider is not None else None
        if login is None:
            # No configured credential: this stays the old, honest answer.
            raise FindchipsPageUnavailable(
                "LOGIN_REQUIRED", page.url  # type: ignore[attr-defined]
            )
        try:
            ensure_findchips_signed_in(
                page,
                login=login,
                timeout_ms=self._timeout_ms,
            )
        except SiteLoginError as error:
            raise FindchipsPageUnavailable(
                error.reason_code, page.url  # type: ignore[attr-defined]
            ) from None


def ensure_findchips_signed_in(
    page: object,
    *,
    login: FindchipsLogin | None,
    timeout_ms: int,
    wait: Callable[[float], None] = sleep,
    clock: Callable[[], float] = monotonic,
) -> None:
    """Open Findchips' own sign-in page and complete one login there.

    This site navigates itself -- the page it is handed is only a tab -- so the
    whole flow is shared rather than half of it, and the sell sweep signs in
    exactly the way a price read does.
    """

    if login is None:
        raise SiteLoginError("CREDENTIALS_UNAVAILABLE")
    # The sweep already opened this form. Reloading it here discards the
    # passive verification which may have just finished in the current tab.
    if not (_is_findchips_response_url(page.url) and findchips_login_page_open(page)):
        page.goto(  # type: ignore[attr-defined]
            FINDCHIPS_LOGIN_URL,
            wait_until="domcontentloaded",
            timeout=timeout_ms,
        )
    # An existing session redirects /signin to /account or /dashboard.
    if _is_findchips_response_url(page.url) and not findchips_login_page_open(page):
        return
    for attempt in range(2):
        _wait_findchips_submit_ready(page, timeout_ms=timeout_ms, wait=wait, clock=clock)
        submit_login_form(
            page, form=FINDCHIPS_LOGIN_FORM, login=login, timeout_ms=timeout_ms,
        )
        try:
            await_login_outcome(
                page, form=FINDCHIPS_LOGIN_FORM,
                is_login_page=_findchips_login_pending,
                timeout_ms=timeout_ms, wait=wait, clock=clock,
            )
            if not _is_findchips_response_url(page.url):
                raise SiteLoginError("UNEXPECTED_RESPONSE_HOST")
            return
        except SiteLoginError as error:
            # Retry only an ordinary submit with no confirmed site verdict.
            # CAPTCHA/password refusals are not fixed by repeated clicks.
            if error.reason_code != "LOGIN_NOT_CONFIRMED" or attempt:
                raise


def _wait_findchips_submit_ready(
    page: object, *, timeout_ms: int,
    wait: Callable[[float], None], clock: Callable[[], float],
) -> None:
    """Wait for site scripts and passive verification before the normal click."""
    page.wait_for_load_state("load", timeout=timeout_ms)
    deadline = clock() + timeout_ms / 1000.0
    while True:
        if challenge_present(page, FINDCHIPS_LOGIN_FORM):
            raise SiteLoginError("MANUAL_VERIFICATION_REQUIRED")
        button = unique_visible_control(page, FINDCHIPS_LOGIN_FORM.submit)
        ready = page.evaluate("""() => {
            const token = document.querySelector('[name="cf-turnstile-response"]');
            return document.readyState === 'complete' && (!token || !!token.value);
        }""")
        if button is not None and button.is_enabled() and ready:
            return
        if clock() >= deadline:
            raise SiteLoginError("LOGIN_NOT_READY")
        wait(min(0.25, max(0.0, deadline - clock())))



def _parse_stock_presence(value: str | None) -> bool | None:
    if value is None:
        return None
    compact = value.replace(",", "").strip()
    if not compact.isdecimal():
        return None
    return int(compact) > 0


def _parse_tiers(value: str | None) -> tuple[FindchipsPriceTier, ...]:
    if value is None or not value.strip():
        return ()
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE") from error
    if not isinstance(payload, list):
        raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE")

    tiers: list[FindchipsPriceTier] = []
    for item in payload:
        if not isinstance(item, list) or len(item) != 3:
            raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE")
        raw_break, raw_currency, raw_price = item
        if isinstance(raw_break, bool):
            raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE")
        if isinstance(raw_break, int):
            break_quantity = raw_break
        elif isinstance(raw_break, str) and raw_break.isdecimal():
            break_quantity = int(raw_break)
        else:
            raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE")
        if not isinstance(raw_currency, str) or not isinstance(raw_price, str):
            raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE")
        if "," in raw_price and not re.fullmatch(
            r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", raw_price
        ):
            raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE")
        try:
            unit_price = Decimal(raw_price.replace(",", ""))
        except InvalidOperation as error:
            raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE") from error
        try:
            tier = FindchipsPriceTier(
                break_quantity=break_quantity,
                unit_price=unit_price,
                currency=raw_currency.upper(),
            )
        except (TypeError, ValueError) as error:
            raise FindchipsParseError("PRICE_TIERS_UNPARSEABLE") from error
        tiers.append(tier)
    return tuple(tiers)


_CHINA_TZ = timezone(timedelta(hours=8))


def _parse_optional_date(value: str | None) -> datetime | None:
    if value is None or not value.strip():
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
        raise FindchipsParseError("QUOTE_DATE_UNPARSEABLE") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_CHINA_TZ)
    return parsed.astimezone(UTC)


class _FindchipsParser(HTMLParser):
    def __init__(self, target_mpn: str | None = None) -> None:
        super().__init__(convert_charrefs=True)
        self.target_mpn = target_mpn
        self.result_container_found = False
        self.explicit_no_results = False
        self._empty_message: list[str] | None = None
        self.offers: list[FindchipsOffer] = []
        self._row: dict[str, str | None] | None = None
        self._visible_tiers: list[FindchipsPriceTier] = []
        self._in_price_list = False
        self._tier_label: str | None = None
        self._tier_value: str | None = None
        self._tier_base_currency: str | None = None
        self._active_span: str | None = None
        self._span_text: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = dict(attrs)
        classes = frozenset((values.get("class") or "").split())
        if tag == "p" and {"alert", "alert-info", "no-results"} <= classes:
            self._empty_message = []
        if "distributor-results" in classes:
            self.result_container_found = True
        if tag == "tr" and values.get("data-mfrpartnumber") is not None:
            if self.target_mpn is not None and price_source_mpn_match(
                self.target_mpn, values["data-mfrpartnumber"] or ""
            ) is None:
                return
            self._row = values
            self._visible_tiers = []
            return
        if self._row is None:
            return
        if tag == "ul" and "price-list" in classes:
            self._in_price_list = True
        elif self._in_price_list and tag == "li":
            self._tier_label = None
            self._tier_value = None
            self._tier_base_currency = None
        elif self._in_price_list and tag == "span" and (
            "label" in classes or "value" in classes
        ):
            self._active_span = "label" if "label" in classes else "value"
            self._span_text = []
            if self._active_span == "value":
                self._tier_base_currency = values.get("data-basecurrency")

    def handle_data(self, data: str) -> None:
        if self._empty_message is not None:
            self._empty_message.append(data)
        if self._active_span is not None:
            self._span_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "p" and self._empty_message is not None:
            message = " ".join("".join(self._empty_message).split())
            expected = (f"No results were found for {lookup_mpn_prefix(self.target_mpn)}."
                        if self.target_mpn is not None else None)
            self.explicit_no_results = (
                message == expected if expected is not None
                else re.fullmatch(r"No results were found for .+\.", message) is not None
            )
            self._empty_message = None
        if self._row is None:
            return
        if tag == "span" and self._active_span is not None:
            value = "".join(self._span_text).strip()
            if self._active_span == "label":
                self._tier_label = value
            else:
                self._tier_value = value
            self._active_span = None
        elif tag == "li" and self._in_price_list and self._tier_value:
            if self._tier_label is None or not self._tier_label.isdecimal():
                raise FindchipsParseError("VISIBLE_PRICE_TIER_UNPARSEABLE")
            self._visible_tiers.append(
                _parse_visible_tier(
                    int(self._tier_label), self._tier_value,
                    self._tier_base_currency,
                )
            )
        elif tag == "ul" and self._in_price_list:
            self._in_price_list = False
        elif tag == "tr":
            values = self._row
            self.offers.append(
                FindchipsOffer(
                    mpn=values["data-mfrpartnumber"] or "",
                    stock_positive=_parse_stock_presence(values.get("data-instock")),
                    tiers=(
                        tuple(self._visible_tiers)
                        if self._visible_tiers
                        else _parse_tiers(values.get("data-price"))
                    ),
                    observed_at=_parse_optional_date(
                        values.get("data-quotedate")
                        or values.get("data-quote-date")
                        or values.get("data-date")
                    ),
                )
            )
            self._row = None
            self._in_price_list = False


def _parse_visible_tier(
    break_quantity: int, display_text: str, base_currency: str | None
) -> FindchipsPriceTier:
    compact = " ".join(display_text.split())
    match = re.fullmatch(
        r"(?:(HK)\$|(USD)\s*\$|\$)\s*(\d[\d,]*(?:\.\d+)?)",
        compact,
        re.IGNORECASE,
    )
    if match is None:
        raise FindchipsParseError("VISIBLE_PRICE_TIER_UNPARSEABLE")
    currency = "HKD" if match.group(1) else "USD" if match.group(2) else (base_currency or "").upper()
    if currency not in {"USD", "HKD"}:
        raise FindchipsParseError("VISIBLE_PRICE_CURRENCY_UNPARSEABLE")
    price_text = match.group(3)
    if "," in price_text and not re.fullmatch(
        r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", price_text
    ):
        raise FindchipsParseError("VISIBLE_PRICE_TIER_UNPARSEABLE")
    return FindchipsPriceTier(
        break_quantity, Decimal(price_text.replace(",", "")), currency
    )


def parse_findchips_offers(
    html: str, target_mpn: str | None = None
) -> tuple[FindchipsOffer, ...]:
    """Parse safe offer facts without retaining stock quantities or raw HTML."""

    if _is_findchips_login_page(html):
        raise FindchipsPageUnavailable("LOGIN_REQUIRED")

    parser = _FindchipsParser(target_mpn)
    try:
        parser.feed(html)
    except FindchipsError:
        raise
    except Exception as error:
        raise FindchipsParseError("RESULT_DOCUMENT_UNPARSEABLE") from error
    if parser.explicit_no_results and parser.offers:
        raise FindchipsParseError("RESULT_DOCUMENT_CONFLICT")
    if not parser.result_container_found and not parser.explicit_no_results:
        raise FindchipsParseError("RESULT_CONTAINER_MISSING")
    return tuple(parser.offers)


def select_applicable_tier(
    tiers: tuple[FindchipsPriceTier, ...],
    customer_quantity: int,
) -> FindchipsPriceTier | None:
    """Select the lowest displayed supported unit price; quantity is irrelevant."""

    del customer_quantity
    eligible = [tier for tier in tiers if tier.currency in {"USD", "HKD"}]
    return (
        min(eligible, key=lambda tier: (tier.unit_price, tier.break_quantity))
        if eligible
        else None
    )


def select_lowest_valid_price(
    offers: tuple[FindchipsOffer, ...],
    target_mpn: str,
    customer_quantity: int,
) -> tuple[str, FindchipsPriceTier] | None:
    """Select the lowest displayed USD price from matched stocked offers."""

    applicable: list[tuple[str, FindchipsPriceTier]] = []
    for offer in offers:
        if price_source_mpn_match(target_mpn, offer.mpn) is None:
            continue
        if offer.stock_positive is not True:
            continue
        tier = select_applicable_tier(offer.tiers, customer_quantity)
        if tier is not None:
            applicable.append((offer.mpn, tier))
    if not applicable:
        return None
    return min(
        applicable,
        key=lambda selection: (
            selection[1].unit_price,
            selection[1].break_quantity,
            selection[0].casefold(),
        ),
    )


class FindchipsAdapter:
    """Build a Findchips source result using an injected USD/RMB quote."""

    def __init__(
        self,
        client: FindchipsPageClient,
        fx_provider: UsdRmbProvider,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client
        self._fx_provider = fx_provider
        self._clock = clock or (lambda: datetime.now(UTC))

    def _unavailable(
        self,
        target_mpn: str,
        code: str,
        *,
        captured_at: datetime | None = None,
        source_url: str | None = None,
        fields: tuple[EvidenceField, ...] = (),
    ) -> SourceResult:
        evidence = SourceEvidence(
            source=ResearchSource.FINDCHIPS,
            query_mpn=target_mpn,
            matched_mpn=None,
            outcome=SourceOutcome.SOURCE_UNAVAILABLE,
            captured_at=captured_at or self._clock(),
            source_url=source_url,
            fields=(EvidenceField("failure_code", code), *fields),
        )
        return SourceResult(
            source=ResearchSource.FINDCHIPS,
            outcome=SourceOutcome.SOURCE_UNAVAILABLE,
            evidence=evidence,
        )

    def search(self, target_mpn: str, customer_quantity: int) -> SourceResult:
        del customer_quantity  # displayed tiers are independent of inquiry quantity
        try:
            page = self._client.fetch_first_page(target_mpn)
        except FindchipsError as error:
            return self._unavailable(
                target_mpn,
                error.code,
                source_url=error.source_url,
            )

        try:
            offers = parse_findchips_offers(page.html, target_mpn)
        except FindchipsError as error:
            return self._unavailable(
                target_mpn,
                error.code,
                captured_at=page.captured_at,
                source_url=page.url,
            )

        now = self._clock()
        cutoff = calendar_month_cutoff(now)
        mpn_matched_offers = [
            offer
            for offer in offers
            if price_source_mpn_match(target_mpn, offer.mpn) is not None
        ]
        matched_offers = [
            offer
            for offer in mpn_matched_offers
            if (
                offer.observed_at is None
                or cutoff <= offer.observed_at <= now
            )
        ]
        if not mpn_matched_offers:
            evidence = SourceEvidence(
                source=ResearchSource.FINDCHIPS,
                query_mpn=target_mpn,
                matched_mpn=None,
                outcome=SourceOutcome.NO_STRICT_MPN_MATCH,
                captured_at=page.captured_at,
                source_url=page.url,
                fields=(
                    EvidenceField("inspected_offer_count", len(offers)),
                    EvidenceField("matched_mpn_offer_count", 0),
                ),
            )
            return SourceResult(
                source=ResearchSource.FINDCHIPS,
                outcome=SourceOutcome.NO_STRICT_MPN_MATCH,
                evidence=evidence,
            )
        if not matched_offers:
            evidence = SourceEvidence(
                source=ResearchSource.FINDCHIPS,
                query_mpn=target_mpn,
                matched_mpn=mpn_matched_offers[0].mpn,
                outcome=SourceOutcome.NO_VALID_PRICE,
                captured_at=page.captured_at,
                source_url=page.url,
                fields=(
                    EvidenceField("inspected_offer_count", len(offers)),
                    EvidenceField(
                        "matched_mpn_offer_count", len(mpn_matched_offers)
                    ),
                ),
            )
            return SourceResult(
                source=ResearchSource.FINDCHIPS,
                outcome=SourceOutcome.NO_VALID_PRICE,
                evidence=evidence,
            )

        # A row can display tiers in different currencies. Do not discard one
        # using the unconverted number before the FX comparison below.
        priced = [
            (offer, tier)
            for offer in matched_offers
            for tier in offer.tiers
            if tier.currency in {"USD", "HKD"}
        ]
        stocked = [(offer, tier) for offer, tier in priced if offer.stock_positive is True]
        out_of_stock = [
            (offer, tier) for offer, tier in priced if offer.stock_positive is False
        ]
        count_fields = (
            EvidenceField("inspected_offer_count", len(offers)),
            EvidenceField("matched_mpn_offer_count", len(matched_offers)),
            EvidenceField("stocked_price_offer_count", len(stocked)),
            EvidenceField("out_of_stock_price_offer_count", len(out_of_stock)),
        )
        if not stocked and not out_of_stock:
            evidence = SourceEvidence(
                source=ResearchSource.FINDCHIPS,
                query_mpn=target_mpn,
                matched_mpn=matched_offers[0].mpn,
                outcome=SourceOutcome.NO_VALID_PRICE,
                captured_at=page.captured_at,
                source_url=page.url,
                fields=count_fields,
            )
            return SourceResult(
                source=ResearchSource.FINDCHIPS,
                outcome=SourceOutcome.NO_VALID_PRICE,
                evidence=evidence,
            )

        try:
            fx_quote = self._fx_provider.get_quote()
            if not isinstance(fx_quote, UsdRmbQuote):
                raise TypeError("FX provider returned an invalid quote")
            rates = {"USD": fx_quote.rate}
            if any(tier.currency == "HKD" for _, tier in stocked + out_of_stock):
                hkd_rate = self._fx_provider.get_hkd_rmb_rate()
                if not isinstance(hkd_rate, Decimal) or not hkd_rate.is_finite() or hkd_rate <= 0:
                    raise ValueError("Invalid HKD/RMB rate")
                rates["HKD"] = hkd_rate
        except Exception:  # noqa: BLE001 - external provider boundary
            return self._unavailable(
                target_mpn,
                "FX_QUOTE_UNAVAILABLE",
                captured_at=page.captured_at,
                source_url=page.url,
                fields=count_fields,
            )

        def lowest(
            selections: list[tuple[FindchipsOffer, FindchipsPriceTier]],
        ) -> tuple[FindchipsOffer, FindchipsPriceTier] | None:
            return (
                min(
                    selections,
                    key=lambda item: (
                        item[1].unit_price * rates[item[1].currency],
                        item[0].mpn.casefold(),
                        item[1].break_quantity,
                    ),
                )
                if selections
                else None
            )

        stocked_selection = lowest(stocked)
        out_of_stock_selection = lowest(out_of_stock)

        def candidate(selection: tuple[FindchipsOffer, FindchipsPriceTier] | None):
            if selection is None:
                return None
            offer, tier = selection
            match = price_source_mpn_match(target_mpn, offer.mpn)
            return PriceCandidate(
                source=ResearchSource.FINDCHIPS,
                matched_mpn=offer.mpn,
                raw_price=tier.unit_price,
                raw_currency=tier.currency,
                normalized_rmb_price=tier.unit_price * rates[tier.currency],
                captured_at=page.captured_at,
                source_url=page.url,
                display_mpn=(
                    offer.mpn if match is MpnMatchKind.SUFFIX else None
                ),
            )

        stocked_candidate = candidate(stocked_selection)
        out_of_stock_candidate = candidate(out_of_stock_selection)
        evidence_match = (
            stocked_selection or out_of_stock_selection
        )
        assert evidence_match is not None
        matched_mpn = evidence_match[0].mpn
        evidence = SourceEvidence(
            source=ResearchSource.FINDCHIPS,
            query_mpn=target_mpn,
            matched_mpn=matched_mpn,
            outcome=SourceOutcome.SUCCESS,
            captured_at=page.captured_at,
            source_url=page.url,
            fields=(
                *count_fields,
                EvidenceField("fx_base_currency", fx_quote.base_currency),
                EvidenceField("fx_quote_currency", fx_quote.quote_currency),
                EvidenceField("fx_rate", fx_quote.rate),
                EvidenceField("hkd_rmb_rate", rates.get("HKD")),
                EvidenceField("fx_captured_at", fx_quote.captured_at),
                EvidenceField("fx_source_label", fx_quote.source_label),
                EvidenceField(
                    "stocked_raw_price",
                    stocked_candidate.raw_price if stocked_candidate else None,
                ),
                EvidenceField(
                    "stocked_raw_currency",
                    stocked_candidate.raw_currency if stocked_candidate else None,
                ),
                EvidenceField(
                    "stocked_fx_rate",
                    rates[stocked_candidate.raw_currency] if stocked_candidate else None,
                ),
                EvidenceField(
                    "stocked_rmb_price",
                    stocked_candidate.normalized_rmb_price
                    if stocked_candidate
                    else None,
                ),
                EvidenceField(
                    "out_of_stock_raw_price",
                    out_of_stock_candidate.raw_price if out_of_stock_candidate else None,
                ),
                EvidenceField(
                    "out_of_stock_raw_currency",
                    out_of_stock_candidate.raw_currency if out_of_stock_candidate else None,
                ),
                EvidenceField(
                    "out_of_stock_fx_rate",
                    rates[out_of_stock_candidate.raw_currency] if out_of_stock_candidate else None,
                ),
                EvidenceField(
                    "out_of_stock_rmb_price",
                    out_of_stock_candidate.normalized_rmb_price
                    if out_of_stock_candidate
                    else None,
                ),
            ),
        )
        return SourceResult(
            source=ResearchSource.FINDCHIPS,
            outcome=SourceOutcome.SUCCESS,
            evidence=evidence,
            price_candidate=stocked_candidate,
            out_of_stock_candidate=out_of_stock_candidate,
        )
