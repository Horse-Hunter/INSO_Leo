"""Read-only HQEW cloud-price adapter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from ipaddress import ip_address
from time import monotonic, sleep
from typing import Protocol
from urllib.parse import parse_qs, quote, urlsplit

from src.core.mpn import lookup_mpn_prefix

from .cdp_pages import new_background_page
from .site_login import (
    REJECTED_PASSWORD_TEXT,
    LoginCheckbox,
    LoginForm,
    SiteLoginError,
    await_login_outcome,
    challenge_present,
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

HQEW_RESULT_URL = "https://p.hqew.com/yunquote/"
#: Canonical credential site id; matches the entry in the Core vault.
HQEW_SITE_ID = "p.hqew.com"
HQEW_LOGIN_URL = "https://passport.hqew.com/login"

#: HQEW's ordinary account form. Its captcha, Aliyun challenge and slider are
#: all served hidden and only revealed when the site wants a human, so they are
#: listed as challenges -- never as fields this code would try to fill.
HQEW_LOGIN_FORM = LoginForm(
    username="#J_loginName",
    password="#J_loginPsw",
    submit="#J_btnLogin",
    # J_uislider is the visible advertisement carousel, NOT a CAPTCHA.
    challenge=("#J_verifyCode", "#J_AliyunVerifyCode"),
    rejection=REJECTED_PASSWORD_TEXT,
    options=(LoginCheckbox('label[for="J_checkpripolicy_account"]'),),
)


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
class HqewLogin:
    """An in-memory HQEW login supplied by the project Credential Provider."""

    username: str = field(repr=False)
    password: str = field(repr=False)


class HqewLoginProvider(Protocol):
    """Research-facing credential capability; storage details stay in Core."""

    def get_login(self, site_id: str) -> HqewLogin | None:
        """Return one configured login without logging or persisting it."""


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
    return f"{HQEW_RESULT_URL}{quote(lookup_mpn_prefix(mpn), safe='')}.html?y4=1"


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
    encoded_mpn = quote(lookup_mpn_prefix(mpn), safe="")
    expected_path = f"/yunquote/{encoded_mpn}.html"
    if not _is_hqew_url(url):
        return False
    if parsed.path.casefold() == expected_path.casefold():
        return True
    # HQEW currently redirects the legacy result URL through its same-site
    # yunquote endpoint. Accept only a redirect whose declared target is the
    # exact requested model URL; no broader URL guessing is permitted.
    if parsed.path.casefold() != "/yunquote":
        return False
    target = parse_qs(parsed.query).get("toUrl", [None])[0]
    if not isinstance(target, str):
        return False
    redirected = urlsplit(target)
    return bool(
        _is_hqew_url(target)
        and redirected.path.casefold() == expected_path.casefold()
    )


def _is_hqew_login_page(html: str) -> bool:
    folded = html.casefold()
    return (
        ("type=\"password\"" in folded or "type='password'" in folded)
        and "登录" in html
    )


def _is_hqew_login_url(url: str) -> bool:
    """True while the tab is on HQEW's passport login path."""

    parsed = urlsplit(url)
    return (
        (parsed.hostname or "").casefold() == "passport.hqew.com"
        and parsed.path.casefold().startswith("/login")
    )


def hqew_login_page_open(page: object) -> bool:
    """Settle predicate: has HQEW's own script carried us off the form yet?"""

    return _is_hqew_login_url(getattr(page, "url", "") or "")


class CdpHqewClient:
    """Read HQEW through an Owner-authenticated ordinary Chrome session."""

    def __init__(
        self,
        *,
        cdp_url: str = "http://127.0.0.1:9222",
        timeout_ms: int = 45_000,
        settle_ms: int = 5_000,
        navigate: bool = True,
        login_provider: HqewLoginProvider | None = None,
        playwright_factory: Callable[[], object] | None = None,
    ) -> None:
        hostname = urlsplit(cdp_url).hostname
        if hostname is None or not _is_loopback_hostname(hostname):
            raise HqewPageUnavailable("CDP_REMOTE_ENDPOINT_FORBIDDEN")
        self._cdp_url = cdp_url
        self._timeout_ms = timeout_ms
        self._settle_ms = settle_ms
        self._navigate = navigate
        self._login_provider = login_provider
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
                if self._navigate:
                    # Owner rule (2026-10-01): every call opens its own page,
                    # signs in first when the site asks, does its work, and
                    # closes the page again. Reusing whichever tab an earlier
                    # call left behind is what let a stale document look like a
                    # fresh answer.
                    page = new_background_page(
                        browser, context, timeout_ms=self._timeout_ms
                    )
                    owned = True
                else:
                    exact_pages = [
                        candidate
                        for candidate in context.pages
                        if _is_expected_result_url(candidate.url, mpn)
                    ]
                    if not exact_pages:
                        raise HqewPageUnavailable("CDP_TARGET_PAGE_NOT_OPEN")
                    page = exact_pages[0]
                    owned = False

                try:
                    html, current_url = self._fetch(page, target_url, mpn, owned)
                    if _is_hqew_login_page(html):
                        # A login wall is a session problem to solve, never a
                        # business answer: sign in, then ask for the page again.
                        self._sign_in(page)
                        html, current_url = self._fetch(page, target_url, mpn, owned)
                        if _is_hqew_login_page(html):
                            raise HqewPageUnavailable(
                                "LOGIN_NOT_CONFIRMED", current_url
                            )
                    return HqewPage(html, current_url, datetime.now(UTC))
                finally:
                    if owned:
                        page.close()
        except HqewPageUnavailable:
            raise
        except timeout_error as error:
            raise HqewPageUnavailable("BROWSER_TIMEOUT", current_url) from error
        except Exception as error:
            raise HqewPageUnavailable("BROWSER_FAILURE", current_url) from error

    def _fetch(
        self, page: object, target_url: str, mpn: str, navigate: bool
    ) -> tuple[str, str]:
        """Navigate to the result page (when we own the tab) and read it.

        An attached tab is read exactly as found -- re-navigating a tab the
        Owner opened would discard whatever they were looking at.
        """

        if navigate:
            page.goto(  # type: ignore[attr-defined]
                target_url,
                wait_until="domcontentloaded",
                timeout=self._timeout_ms,
            )
            page.wait_for_load_state("load", timeout=self._timeout_ms)  # type: ignore[attr-defined]
            page.wait_for_timeout(self._settle_ms)  # type: ignore[attr-defined]
        current_url = page.url  # type: ignore[attr-defined]
        if page.locator("body").count() == 0:  # type: ignore[attr-defined]
            raise HqewPageUnavailable("RESULT_PAGE_BLOCKED", current_url)
        html = page.content()  # type: ignore[attr-defined]
        if "安全验证" in html or "captcha-reset" in html:
            raise HqewPageUnavailable(
                "INTERACTIVE_CHALLENGE_REQUIRED", current_url
            )
        if _is_hqew_login_page(html):
            # Reported to the caller rather than judged here: whether it is a
            # problem depends on whether a login can still be established.
            return html, current_url
        if not _is_expected_result_url(current_url, mpn):
            raise HqewPageUnavailable("RESULT_NAVIGATION_FAILED", current_url)
        return html, current_url

    def _sign_in(self, page: object) -> None:
        """Establish HQEW's own login once, or say why it cannot be done."""

        provider = self._login_provider
        login = provider.get_login(HQEW_SITE_ID) if provider is not None else None
        if login is None:
            # No configured credential: this stays the old, honest answer.
            raise HqewPageUnavailable("LOGIN_REQUIRED", page.url)  # type: ignore[attr-defined]
        try:
            ensure_hqew_signed_in(
                page,
                login=login,
                timeout_ms=self._timeout_ms,
            )
        except SiteLoginError as error:
            raise HqewPageUnavailable(
                error.reason_code, page.url  # type: ignore[attr-defined]
            ) from None


def ensure_hqew_signed_in(
    page: object,
    *,
    login: HqewLogin | None,
    timeout_ms: int,
    wait: Callable[[float], None] = sleep,
    clock: Callable[[], float] = monotonic,
) -> None:
    """Open HQEW's own sign-in page and complete one login there.

    HQEW serves its captcha, Aliyun challenge and slider hidden and reveals them
    only when it wants a human, so they are checked *before* the submit -- after
    one is visible there is nothing left to try.
    """

    if login is None:
        raise SiteLoginError("CREDENTIALS_UNAVAILABLE")
    page.goto(  # type: ignore[attr-defined]
        HQEW_LOGIN_URL,
        wait_until="domcontentloaded",
        timeout=timeout_ms,
    )
    if challenge_present(page, HQEW_LOGIN_FORM):
        raise SiteLoginError("MANUAL_VERIFICATION_REQUIRED")
    submit_login_form(
        page,
        form=HQEW_LOGIN_FORM,
        login=login,
        timeout_ms=timeout_ms,
    )
    await_login_outcome(
        page,
        form=HQEW_LOGIN_FORM,
        is_login_page=hqew_login_page_open,
        timeout_ms=timeout_ms,
        wait=wait,
        clock=clock,
    )


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
    if _is_hqew_login_page(html):
        raise HqewPageUnavailable("LOGIN_REQUIRED")
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
