"""Read-only IC.net Brand and market-stock adapter."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
from ipaddress import ip_address
from typing import Protocol
from urllib.parse import quote, urlsplit

from .source_contracts import (
    EvidenceField,
    ResearchSource,
    SourceEvidence,
    SourceOutcome,
    SourceResult,
    is_strict_mpn_match,
)

ICNET_SITE_ID = "ic.net.cn"
ICNET_HOME_URL = "https://www.ic.net.cn/"
ICNET_LOGIN_URL = "https://member.ic.net.cn/login.php"
ICNET_USER_AGENT = "INSO-Leo-Research/1.0 (read-only IC.net adapter)"



def _is_loopback_hostname(hostname: str) -> bool:
    if hostname.casefold() == "localhost":
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False



def _is_icnet_url(url: str) -> bool:
    hostname = urlsplit(url).hostname
    if hostname is None:
        return False
    normalized = hostname.casefold()
    return normalized == "ic.net.cn" or normalized.endswith(".ic.net.cn")


_VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
_CJK_RE = re.compile(r"[㐀-䶿一-鿿]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_HIDDEN_CLASS_RE = re.compile(
    r"\.([A-Za-z_][A-Za-z0-9_-]*)\s*\{([^{}]*)\}", re.DOTALL
)
_DISPLAY_NONE_RE = re.compile(r"display\s*:\s*none\b", re.IGNORECASE)
_CERTIFICATION_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:SSCP|ICCP)(?![A-Za-z0-9])", re.IGNORECASE
)


class IcNetError(RuntimeError):
    """Base class for safe, non-secret IC.net adapter failures."""

    def __init__(self, code: str, source_url: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.source_url = source_url


class IcNetPageUnavailable(IcNetError):
    """The approved browser path could not return a usable result page."""


class IcNetParseError(IcNetError):
    """The returned result document cannot be parsed reliably."""


@dataclass(frozen=True, slots=True)
class IcNetLogin:
    """An in-memory login supplied by the project Credential Provider."""

    username: str = field(repr=False)
    password: str = field(repr=False)


class IcNetLoginProvider(Protocol):
    """Research-facing credential capability; storage details stay in Core."""

    def get_login(self, site_id: str) -> IcNetLogin | None:
        """Return one configured login without logging or persisting it."""


@dataclass(frozen=True, slots=True)
class IcNetPage:
    """One in-memory first-page capture."""

    html: str = field(repr=False)
    url: str
    captured_at: datetime


class IcNetPageClient(Protocol):
    """Network boundary replaced by fixtures in default tests."""

    def fetch_first_page(self, mpn: str) -> IcNetPage:
        """Return the authenticated exact-model first page."""


@dataclass(frozen=True, slots=True)
class IcNetRow:
    """Minimum non-contact product data parsed from one displayed result row."""

    mpn: str
    manufacturer: str | None
    quantity: int | None
    certifications: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class BrandResolution:
    """Deterministic Brand selection plus auditable candidate counts."""

    brand: str | None
    counts: tuple[tuple[str, int], ...]
    ambiguous_candidates: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class IcNetResult:
    """IC.net-specific context around the generic source result."""

    source_result: SourceResult
    resolved_brand: str | None = None
    stock_label: str | None = None


class _Node:
    __slots__ = ("attrs", "children", "data", "parent", "tag")

    def __init__(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
        parent: _Node | None = None,
    ) -> None:
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children: list[_Node] = []
        self.data: list[str] = []

    @property
    def classes(self) -> frozenset[str]:
        return frozenset((self.attrs.get("class") or "").split())

    def descendants(self) -> list[_Node]:
        result: list[_Node] = []
        for child in self.children:
            result.append(child)
            result.extend(child.descendants())
        return result


class _TreeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("root", [])
        self._stack = [self.root]

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        node = _Node(tag, attrs, self._stack[-1])
        self._stack[-1].children.append(node)
        if tag not in _VOID_ELEMENTS:
            self._stack.append(node)

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_ELEMENTS:
            self._stack.pop()

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index].tag == tag:
                del self._stack[index:]
                return

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self._stack[-1].data.append(text)


def _has_class(node: _Node, class_name: str) -> bool:
    return class_name in node.classes


def _nodes_with_class(node: _Node, class_name: str) -> list[_Node]:
    return [item for item in node.descendants() if _has_class(item, class_name)]


def _hidden_classes(html: str) -> frozenset[str]:
    return frozenset(
        class_name
        for class_name, declarations in _HIDDEN_CLASS_RE.findall(html)
        if _DISPLAY_NONE_RE.search(declarations)
    )


def _is_hidden(node: _Node, boundary: _Node, hidden_classes: frozenset[str]) -> bool:
    current: _Node | None = node
    while current is not None:
        if current.classes & hidden_classes:
            return True
        if _DISPLAY_NONE_RE.search(current.attrs.get("style") or ""):
            return True
        if current is boundary:
            break
        current = current.parent
    return False


def _visible_text(node: _Node, boundary: _Node, hidden_classes: frozenset[str]) -> str:
    if _is_hidden(node, boundary, hidden_classes):
        return ""
    parts = list(node.data)
    for child in node.children:
        text = _visible_text(child, boundary, hidden_classes)
        if text:
            parts.append(text)
    return " ".join(" ".join(parts).split())


def _single_visible_text(
    row: _Node,
    class_name: str,
    hidden_classes: frozenset[str],
) -> str | None:
    values = {
        text
        for node in _nodes_with_class(row, class_name)
        if (text := _visible_text(node, row, hidden_classes))
    }
    if len(values) != 1:
        return None
    return values.pop()


def _parse_quantity(value: str | None) -> int | None:
    if value is None:
        return None
    compact = value.replace(",", "").strip()
    if not compact.isdecimal():
        return None
    return int(compact)


def _row_certifications(
    row: _Node, hidden_classes: frozenset[str]
) -> frozenset[str]:
    certifications: set[str] = set()
    for node in [row, *row.descendants()]:
        if _is_hidden(node, row, hidden_classes):
            continue
        for class_name in node.classes:
            if class_name.casefold() in {"sscp", "iccp"}:
                certifications.add(class_name.upper())
        for attribute in ("title", "alt"):
            value = node.attrs.get(attribute) or ""
            certifications.update(match.upper() for match in _CERTIFICATION_RE.findall(value))
    return frozenset(certifications)


def parse_icnet_rows(html: str) -> tuple[IcNetRow, ...]:
    """Parse displayed product fields without retaining raw HTML or contacts."""

    parser = _TreeParser()
    parser.feed(html)
    nodes = parser.root.descendants()
    if not any(_has_class(node, "right_results") for node in nodes):
        raise IcNetParseError("RESULT_CONTAINER_MISSING")

    hidden_classes = _hidden_classes(html)
    product_rows = [
        node
        for node in nodes
        if node.tag == "li"
        and _has_class(node, "stair_tr")
        and _nodes_with_class(node, "product_number")
    ]
    rows: list[IcNetRow] = []
    for row in product_rows:
        mpn = _single_visible_text(row, "product_number", hidden_classes)
        if not mpn:
            raise IcNetParseError("VISIBLE_MPN_MISSING")
        manufacturer = _single_visible_text(row, "result_factory", hidden_classes)
        quantity_text = _single_visible_text(row, "result_totalNumber", hidden_classes)
        rows.append(
            IcNetRow(
                mpn=mpn,
                manufacturer=manufacturer,
                quantity=_parse_quantity(quantity_text),
                certifications=_row_certifications(row, hidden_classes),
            )
        )
    return tuple(rows)


def extract_manufacturer_display(value: str | None) -> str | None:
    """Keep a displayed mono-language label or a separable English component."""

    if value is None:
        return None
    displayed = " ".join(value.split())
    if not displayed:
        return None
    has_latin = bool(_LATIN_RE.search(displayed))
    has_cjk = bool(_CJK_RE.search(displayed))
    if has_latin != has_cjk:
        return displayed
    if not (has_latin and has_cjk):
        return displayed

    parts = [
        " ".join(part.split()).strip(" ,;-")
        for part in re.split(r"[/／|｜()（）]", displayed)
    ]
    english_parts = [
        part
        for part in parts
        if part and _LATIN_RE.search(part) and not _CJK_RE.search(part)
    ]
    if len(english_parts) == 1:
        return english_parts[0]
    return None


def _is_english_candidate(value: str) -> bool:
    return bool(_LATIN_RE.search(value)) and not bool(_CJK_RE.search(value))


def select_brand_by_frequency(values: list[str | None]) -> BrandResolution:
    """Apply the confirmed frequency, English, then shorter-English tie rules."""

    candidates = [
        candidate
        for value in values
        if (candidate := extract_manufacturer_display(value)) is not None
    ]
    counts = Counter(candidates)
    ordered_counts = tuple(sorted(counts.items(), key=lambda item: (-item[1], item[0])))
    if not counts:
        return BrandResolution(None, ())

    highest = max(counts.values())
    leaders = [candidate for candidate, count in counts.items() if count == highest]
    if len(leaders) == 1:
        return BrandResolution(leaders[0], ordered_counts)

    english = [candidate for candidate in leaders if _is_english_candidate(candidate)]
    if english:
        shortest = min(len(candidate) for candidate in english)
        leaders = [candidate for candidate in english if len(candidate) == shortest]
    if len(leaders) == 1:
        return BrandResolution(leaders[0], ordered_counts)
    return BrandResolution(None, ordered_counts, tuple(sorted(leaders)))


def sum_certified_stock(rows: list[IcNetRow], target_mpn: str) -> tuple[int, int]:
    """Sum each strict-MPN SSCP/ICCP row once, failing closed on bad quantity."""

    qualified = [
        row
        for row in rows
        if is_strict_mpn_match(target_mpn, row.mpn) and row.certifications
    ]
    if any(row.quantity is None for row in qualified):
        raise IcNetParseError("QUALIFIED_QUANTITY_UNPARSEABLE")
    return sum(row.quantity or 0 for row in qualified), len(qualified)


def classify_stock(total: int, customer_quantity: int) -> str:
    """Return the confirmed V1 IC.net market-stock display label."""

    return "货少" if total <= customer_quantity * 3 else "货多"


class PlaywrightIcNetClient:
    """Bounded headed-browser client for authenticated, read-only model search."""

    def __init__(
        self,
        login_provider: IcNetLoginProvider,
        *,
        timeout_ms: int = 45_000,
        headless: bool = False,
        channel: str = "chrome",
    ) -> None:
        self._login_provider = login_provider
        self._timeout_ms = timeout_ms
        self._headless = headless
        self._channel = channel

    def fetch_first_page(self, mpn: str) -> IcNetPage:
        login = self._login_provider.get_login(ICNET_SITE_ID)
        if login is None:
            raise IcNetPageUnavailable("CREDENTIAL_NOT_CONFIGURED")
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise IcNetPageUnavailable("PLAYWRIGHT_NOT_INSTALLED") from error

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    channel=self._channel,
                    headless=self._headless,
                )
                try:
                    page = browser.new_page(user_agent=ICNET_USER_AGENT)
                    page.goto(
                        ICNET_LOGIN_URL,
                        wait_until="domcontentloaded",
                        timeout=self._timeout_ms,
                    )
                    for selector in ("#username", "#password", "#btn_login"):
                        page.wait_for_selector(
                            selector,
                            state="visible",
                            timeout=self._timeout_ms,
                        )
                    username = page.locator("#username")
                    password = page.locator("#password")
                    login_button = page.locator("#btn_login")
                    if not all(
                        locator.count() == 1 for locator in (username, password, login_button)
                    ):
                        raise IcNetPageUnavailable("LOGIN_FORM_UNAVAILABLE")
                    username.fill(login.username)
                    password.fill(login.password)
                    login_button.click()
                    page.wait_for_timeout(3_000)
                    captcha = page.locator("#loginCode")
                    if captcha.count() and captcha.is_visible():
                        raise IcNetPageUnavailable("INTERACTIVE_CHALLENGE_REQUIRED")
                    if "login.php" in page.url.casefold():
                        raise IcNetPageUnavailable("LOGIN_NOT_CONFIRMED")

                    page.goto(
                        ICNET_HOME_URL,
                        wait_until="domcontentloaded",
                        timeout=self._timeout_ms,
                    )
                    for selector in ("#key", "input[name=isExact]", "#btn_topSearch"):
                        page.wait_for_selector(
                            selector,
                            state="visible",
                            timeout=self._timeout_ms,
                        )
                    search_input = page.locator("#key")
                    exact = page.locator("input[name=isExact]")
                    submit = page.locator("#btn_topSearch")
                    if not all(
                        locator.count() == 1 for locator in (search_input, exact, submit)
                    ):
                        raise IcNetPageUnavailable("SEARCH_FORM_UNAVAILABLE")
                    search_input.fill(mpn)
                    exact.check()
                    submit.click()
                    page.wait_for_timeout(5_000)
                    if page.locator("body").count() == 0:
                        raise IcNetPageUnavailable("RESULT_PAGE_BLOCKED", page.url)
                    result_url = page.url
                    expected_path = f"/search/{quote(mpn, safe='')}.html"
                    if expected_path.casefold() not in result_url.casefold():
                        raise IcNetPageUnavailable(
                            "RESULT_NAVIGATION_FAILED",
                            result_url,
                        )
                    html = page.content()
                    return IcNetPage(html, result_url, datetime.now(UTC))
                finally:
                    browser.close()
        except IcNetPageUnavailable:
            raise
        except PlaywrightTimeoutError as error:
            raise IcNetPageUnavailable("BROWSER_TIMEOUT") from error
        except Exception as error:
            raise IcNetPageUnavailable("BROWSER_FAILURE") from error


class CdpIcNetClient:
    """Read one result page through an Owner-approved ordinary Chrome session."""

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
            raise IcNetPageUnavailable("CDP_REMOTE_ENDPOINT_FORBIDDEN")
        self._cdp_url = cdp_url
        self._timeout_ms = timeout_ms
        self._settle_ms = settle_ms
        self._navigate = navigate
        self._playwright_factory = playwright_factory

    def fetch_first_page(self, mpn: str) -> IcNetPage:
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
                raise IcNetPageUnavailable("PLAYWRIGHT_NOT_INSTALLED") from error
            factory = sync_playwright
            timeout_error = PlaywrightTimeoutError

        target_url = f"{ICNET_HOME_URL}search/{quote(mpn, safe='')}.html"
        current_url: str | None = None
        try:
            with factory() as playwright:  # type: ignore[attr-defined]
                browser = playwright.chromium.connect_over_cdp(
                    self._cdp_url,
                    timeout=self._timeout_ms,
                )
                if not browser.contexts:
                    raise IcNetPageUnavailable("CDP_CONTEXT_UNAVAILABLE")
                context = browser.contexts[0]
                pages = list(context.pages)
                exact_pages = [
                    page
                    for page in pages
                    if page.url.rstrip("/").casefold()
                    == target_url.rstrip("/").casefold()
                ]

                if not self._navigate:
                    if not exact_pages:
                        raise IcNetPageUnavailable("CDP_TARGET_PAGE_NOT_OPEN")
                    page = exact_pages[0]
                else:
                    icnet_pages = [
                        page
                        for page in pages
                        if _is_icnet_url(page.url)
                    ]
                    if exact_pages:
                        page = exact_pages[0]
                    elif icnet_pages:
                        page = icnet_pages[0]
                    else:
                        page = context.new_page()
                    page.goto(
                        target_url,
                        wait_until="domcontentloaded",
                        timeout=self._timeout_ms,
                    )
                    page.wait_for_load_state(
                        "load",
                        timeout=self._timeout_ms,
                    )
                    page.wait_for_timeout(self._settle_ms)

                current_url = page.url
                if page.locator("body").count() == 0:
                    raise IcNetPageUnavailable(
                        "RESULT_PAGE_BLOCKED",
                        current_url,
                    )
                expected_path = f"/search/{quote(mpn, safe='')}.html"
                if expected_path.casefold() not in current_url.casefold():
                    raise IcNetPageUnavailable(
                        "RESULT_NAVIGATION_FAILED",
                        current_url,
                    )
                return IcNetPage(
                    page.content(),
                    current_url,
                    datetime.now(UTC),
                )
        except IcNetPageUnavailable:
            raise
        except timeout_error as error:
            raise IcNetPageUnavailable(
                "BROWSER_TIMEOUT",
                current_url,
            ) from error
        except Exception as error:
            raise IcNetPageUnavailable(
                "BROWSER_FAILURE",
                current_url,
            ) from error


class IcNetAdapter:
    """Build Research-owned IC.net evidence without price candidates."""

    def __init__(
        self,
        client: IcNetPageClient,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))

    def search(
        self,
        target_mpn: str,
        input_brand: str | None,
        customer_quantity: int,
    ) -> IcNetResult:
        try:
            page = self._client.fetch_first_page(target_mpn)
        except IcNetError as error:
            evidence = SourceEvidence(
                source=ResearchSource.IC_NET,
                query_mpn=target_mpn,
                matched_mpn=None,
                outcome=SourceOutcome.SOURCE_UNAVAILABLE,
                captured_at=self._clock(),
                source_url=error.source_url,
                fields=(EvidenceField("failure_code", error.code),),
            )
            return IcNetResult(
                SourceResult(
                    source=ResearchSource.IC_NET,
                    outcome=SourceOutcome.SOURCE_UNAVAILABLE,
                    evidence=evidence,
                )
            )

        try:
            rows = parse_icnet_rows(page.html)
        except IcNetError as error:
            evidence = SourceEvidence(
                source=ResearchSource.IC_NET,
                query_mpn=target_mpn,
                matched_mpn=None,
                outcome=SourceOutcome.SOURCE_UNAVAILABLE,
                captured_at=page.captured_at,
                source_url=page.url,
                fields=(EvidenceField("failure_code", error.code),),
            )
            return IcNetResult(
                SourceResult(
                    source=ResearchSource.IC_NET,
                    outcome=SourceOutcome.SOURCE_UNAVAILABLE,
                    evidence=evidence,
                )
            )

        strict_rows = [
            row for row in rows if is_strict_mpn_match(target_mpn, row.mpn)
        ]
        if not strict_rows:
            evidence = SourceEvidence(
                source=ResearchSource.IC_NET,
                query_mpn=target_mpn,
                matched_mpn=None,
                outcome=SourceOutcome.NO_STRICT_MPN_MATCH,
                captured_at=page.captured_at,
                source_url=page.url,
                fields=(
                    EvidenceField("first_page_rows_inspected", len(rows)),
                    EvidenceField("strict_mpn_rows", 0),
                ),
            )
            return IcNetResult(
                SourceResult(
                    source=ResearchSource.IC_NET,
                    outcome=SourceOutcome.NO_STRICT_MPN_MATCH,
                    evidence=evidence,
                )
            )

        if input_brand is not None and input_brand.strip():
            resolved_brand = input_brand
            brand_source = "input"
            brand_resolution = BrandResolution(input_brand, ())
            brand_rows_used = 0
        else:
            brand_rows = [
                row
                for row in rows[:20]
                if is_strict_mpn_match(target_mpn, row.mpn)
            ]
            brand_resolution = select_brand_by_frequency(
                [row.manufacturer for row in brand_rows]
            )
            resolved_brand = brand_resolution.brand
            brand_source = "ic.net" if resolved_brand is not None else "unresolved"
            brand_rows_used = sum(
                extract_manufacturer_display(row.manufacturer) is not None
                for row in brand_rows
            )

        try:
            stock_total, certified_rows = sum_certified_stock(rows, target_mpn)
        except IcNetParseError as error:
            evidence = SourceEvidence(
                source=ResearchSource.IC_NET,
                query_mpn=target_mpn,
                matched_mpn=None,
                outcome=SourceOutcome.SOURCE_UNAVAILABLE,
                captured_at=page.captured_at,
                source_url=page.url,
                fields=(EvidenceField("failure_code", error.code),),
            )
            return IcNetResult(
                SourceResult(
                    source=ResearchSource.IC_NET,
                    outcome=SourceOutcome.SOURCE_UNAVAILABLE,
                    evidence=evidence,
                )
            )

        threshold = customer_quantity * 3
        stock_label = classify_stock(stock_total, customer_quantity)
        fields = (
            EvidenceField("first_page_rows_inspected", len(rows)),
            EvidenceField("strict_mpn_rows", len(strict_rows)),
            EvidenceField("brand_frequency_rows_used", brand_rows_used),
            EvidenceField(
                "brand_candidate_counts",
                json.dumps(
                    dict(brand_resolution.counts),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            ),
            EvidenceField(
                "brand_ambiguity",
                json.dumps(
                    brand_resolution.ambiguous_candidates,
                    ensure_ascii=False,
                ),
            ),
            EvidenceField("brand_source", brand_source),
            EvidenceField("qualified_certified_rows", certified_rows),
            EvidenceField("certified_stock_total", stock_total),
            EvidenceField("customer_quantity", customer_quantity),
            EvidenceField("stock_threshold", threshold),
            EvidenceField("stock_label", stock_label),
        )
        evidence = SourceEvidence(
            source=ResearchSource.IC_NET,
            query_mpn=target_mpn,
            matched_mpn=strict_rows[0].mpn,
            outcome=SourceOutcome.SUCCESS,
            captured_at=page.captured_at,
            source_url=page.url,
            fields=fields,
        )
        return IcNetResult(
            SourceResult(
                source=ResearchSource.IC_NET,
                outcome=SourceOutcome.SUCCESS,
                evidence=evidence,
            ),
            resolved_brand=resolved_brand,
            stock_label=stock_label,
        )
