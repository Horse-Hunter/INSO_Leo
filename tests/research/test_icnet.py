from datetime import UTC, datetime
from pathlib import Path
from typing import Self

import pytest

from src.research.icnet import (
    BrandResolution,
    CdpIcNetClient,
    IcNetAdapter,
    IcNetLogin,
    IcNetPage,
    IcNetPageUnavailable,
    IcNetParseError,
    IcNetRow,
    classify_stock,
    extract_manufacturer_display,
    parse_icnet_rows,
    select_brand_by_frequency,
    sum_certified_stock,
)
from src.research.source_contracts import ResearchSource, SourceOutcome

CAPTURED_AT = datetime(2026, 9, 22, 8, 0, tzinfo=UTC)
FIXTURE = Path(__file__).parent / "fixtures" / "icnet_results_minimal.html"


class FakeClient:
    def __init__(self, html: str) -> None:
        self.html = html
        self.queries: list[str] = []

    def fetch_first_page(self, mpn: str) -> IcNetPage:
        self.queries.append(mpn)
        return IcNetPage(
            html=self.html,
            url=f"https://www.ic.net.cn/search/{mpn}.html?isExact=1",
            captured_at=CAPTURED_AT,
        )


class UnavailableClient:
    def fetch_first_page(self, mpn: str) -> IcNetPage:
        raise IcNetPageUnavailable(
            "RESULT_PAGE_BLOCKED",
            f"https://www.ic.net.cn/search/{mpn}.html?isExact=1",
        )


class FakeLocator:
    def __init__(self, count: int, text: str = "") -> None:
        self._count = count
        self._text = text

    @property
    def first(self) -> "FakeLocator":
        return self

    def count(self) -> int:
        return self._count

    def inner_text(self) -> str:
        return self._text

    def is_visible(self) -> bool:
        return False


class FakeCdpPage:
    def __init__(
        self,
        url: str,
        html: str,
        *,
        has_body: bool = True,
        response_status: int | None = None,
    ) -> None:
        self.url = url
        self.html = html
        self.has_body = has_body
        self.response_status = response_status
        self.goto_calls: list[tuple[str, str, int]] = []
        self.closed = False
        self.fills: list[tuple[str, str]] = []
        self.clicks: list[str] = []

    def goto(self, url: str, *, wait_until: str, timeout: int):
        self.goto_calls.append((url, wait_until, timeout))
        self.url = url
        if self.response_status is None:
            return None
        return type("Response", (), {"status": self.response_status})()

    def wait_for_load_state(self, state: str, *, timeout: int) -> None:
        assert state == "load"
        assert timeout > 0

    def wait_for_timeout(self, timeout: int) -> None:
        assert timeout >= 0

    def fill(self, selector: str, value: str, *, timeout: int) -> None:
        assert timeout > 0
        self.fills.append((selector, value))

    def click(self, selector: str, *, timeout: int) -> None:
        assert timeout > 0
        self.clicks.append(selector)

    def locator(self, selector: str) -> FakeLocator:
        assert selector == "body"
        return FakeLocator(int(self.has_body), self.html)

    def content(self) -> str:
        return self.html

    def close(self) -> None:
        self.closed = True


def _plain_page() -> FakeCdpPage:
    return FakeCdpPage("about:blank", "<html><body></body></html>")


class _CdpSession:
    def __init__(self) -> None:
        self.detached = False

    def send(self, method: str, _params: object) -> dict[str, str]:
        assert method == "Target.createTarget"
        return {"targetId": "target-1"}

    def detach(self) -> None:
        self.detached = True


class _PendingPage:
    """Mirrors Playwright's ``context.expect_page()`` handshake."""

    def __init__(self, context: "FakeCdpContext") -> None:
        self._context = context
        self.value: FakeCdpPage | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> bool:
        self.value = self._context.new_page()
        return False


class FakeCdpContext:
    def __init__(self, pages: list[FakeCdpPage], spawn=None) -> None:
        self.pages = pages
        self.spawn = spawn or _plain_page

    def new_page(self) -> FakeCdpPage:
        page = self.spawn()
        self.pages.append(page)
        return page

    def expect_page(self, *, timeout: int) -> _PendingPage:
        assert timeout > 0
        return _PendingPage(self)


class FakeCdpBrowser:
    def __init__(self, context: FakeCdpContext) -> None:
        self.contexts = [context]

    def new_browser_cdp_session(self) -> _CdpSession:
        return _CdpSession()


class FakeChromium:
    def __init__(self, browser: FakeCdpBrowser) -> None:
        self.browser = browser
        self.connect_calls: list[tuple[str, int]] = []

    def connect_over_cdp(self, url: str, *, timeout: int) -> FakeCdpBrowser:
        self.connect_calls.append((url, timeout))
        return self.browser


class FakePlaywright:
    def __init__(self, chromium: FakeChromium) -> None:
        self.chromium = chromium

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _fields(result: object) -> dict[str, object]:
    source_result = result.source_result  # type: ignore[attr-defined]
    return {field.key: field.value for field in source_result.evidence.fields}


def _row_html(
    mpn: str,
    manufacturer: str,
    quantity: str = "1",
    certification: str = "",
) -> str:
    cert_html = f'<a class="{certification.lower()}"></a>' if certification else ""
    return f"""
      <li class="stair_tr">
        <div class="result_id">
          <span class="product_number"><a>{mpn}</a></span>
        </div>
        <div class="result_factory">{manufacturer}</div>
        <div class="result_totalNumber">{quantity}</div>
        <div class="result_supply"><p class="result_icons">{cert_html}</p></div>
      </li>
    """


def _page_html(*rows: str) -> str:
    return f'<html><body><div class="right_results"><ul>{"".join(rows)}</ul></div></body></html>'


def test_sanitized_fixture_parses_only_displayed_values() -> None:
    rows = parse_icnet_rows(FIXTURE.read_text(encoding="utf-8"))

    assert len(rows) == 4
    assert rows[0] == IcNetRow(
        mpn="ABC-123",
        manufacturer="Acme/艾克米",
        quantity=20,
        certifications=frozenset({"SSCP"}),
    )
    assert rows[1].quantity == 10
    assert rows[1].certifications == frozenset({"SSCP", "ICCP"})
    assert rows[2].quantity == 5
    assert rows[2].certifications == frozenset({"ICCP"})
    assert rows[3].mpn == "ABC-123-T"
    assert rows[3].quantity == 9999


def test_current_result_list_container_is_accepted() -> None:
    html = '<ul id="resultList">' + _row_html(
        "ABC-123", "Acme", "20", "SSCP"
    ) + "</ul>"

    assert parse_icnet_rows(html) == (
        IcNetRow("ABC-123", "Acme", 20, frozenset({"SSCP"})),
    )


@pytest.mark.parametrize(
    ("displayed", "expected"),
    [
        ("Analog Devices", "Analog Devices"),
        ("华芯", "华芯"),
        ("Telit/泰利特", "Telit"),
        ("德州仪器（TI）", "TI"),
        ("  NXP / 恩智浦  ", "NXP"),
        ("Alpha/Beta/阿尔法", None),
        ("", None),
        (None, None),
    ],
)
def test_manufacturer_display_extraction(
    displayed: str | None, expected: str | None
) -> None:
    assert extract_manufacturer_display(displayed) == expected


def test_brand_frequency_and_confirmed_tie_rules() -> None:
    assert select_brand_by_frequency(["Acme/艾克米", "Acme", "华芯"]).brand == "Acme"

    english_preferred = select_brand_by_frequency(["华芯", "VeryLongBrand"])
    assert english_preferred.brand == "VeryLongBrand"

    shorter_english = select_brand_by_frequency(["LongBrand", "TI"])
    assert shorter_english.brand == "TI"

    unresolved = select_brand_by_frequency(["AB", "CD"])
    assert unresolved == BrandResolution(
        brand=None,
        counts=(("AB", 1), ("CD", 1)),
        ambiguous_candidates=("AB", "CD"),
    )


def test_certified_stock_strict_match_and_both_certifications_count_once() -> None:
    rows = list(parse_icnet_rows(FIXTURE.read_text(encoding="utf-8")))

    assert sum_certified_stock(rows, " abc-123 ") == (10034, 4)


def test_certified_stock_does_not_filter_by_brand() -> None:
    rows = [
        IcNetRow("ABC", "BrandA", 10, frozenset({"SSCP"})),
        IcNetRow("ABC", "BrandB", 20, frozenset({"ICCP"})),
    ]

    assert sum_certified_stock(rows, "abc") == (30, 2)


def test_qualified_unparseable_quantity_fails_closed() -> None:
    rows = [IcNetRow("ABC", "BrandA", None, frozenset({"SSCP"}))]

    with pytest.raises(IcNetParseError, match="QUALIFIED_QUANTITY_UNPARSEABLE"):
        sum_certified_stock(rows, "ABC")


def test_stock_label_includes_equality_in_low_stock() -> None:
    assert classify_stock(30, 10) == "货少"
    assert classify_stock(31, 10) == "货多"


def test_successful_adapter_result_has_evidence_and_no_price_candidate() -> None:
    client = FakeClient(FIXTURE.read_text(encoding="utf-8"))
    result = IcNetAdapter(client).search("ABC-123", None, 10)
    fields = _fields(result)

    assert client.queries == ["ABC-123"]
    assert result.source_result.source is ResearchSource.IC_NET
    assert result.source_result.outcome is SourceOutcome.SUCCESS
    assert result.source_result.price_candidate is None
    assert result.resolved_brand == "Acme"
    assert result.stock_label == "货多"
    assert fields["first_page_rows_inspected"] == 4
    assert fields["strict_mpn_rows"] == 4
    assert fields["brand_frequency_rows_used"] == 4
    assert fields["qualified_certified_rows"] == 4
    assert fields["certified_stock_total"] == 10034
    assert fields["customer_quantity"] == 10
    assert fields["stock_threshold"] == 30
    assert fields["stock_label"] == "货多"
    assert fields["brand_source"] == "ic.net"


def test_provided_brand_is_preserved_and_not_frequency_replaced() -> None:
    result = IcNetAdapter(
        FakeClient(FIXTURE.read_text(encoding="utf-8"))
    ).search("ABC-123", "Owner Brand", 100)
    fields = _fields(result)

    assert result.resolved_brand == "Owner Brand"
    assert fields["brand_source"] == "input"
    assert fields["brand_frequency_rows_used"] == 0


def test_brand_frequency_uses_at_most_first_twenty_rows() -> None:
    rows = [
        _row_html("ABC", "LongBrand" if index < 10 else "TI")
        for index in range(20)
    ]
    rows.append(_row_html("ABC", "LongBrand"))
    result = IcNetAdapter(FakeClient(_page_html(*rows))).search("ABC", None, 1)

    assert result.resolved_brand == "TI"
    assert _fields(result)["brand_frequency_rows_used"] == 20


def test_no_strict_match_is_not_source_unavailability() -> None:
    html = _page_html(_row_html("XABC-123-T", "Acme", "99", "SSCP"))
    result = IcNetAdapter(FakeClient(html)).search("ABC-123", None, 10)

    assert result.source_result.outcome is SourceOutcome.NO_STRICT_MPN_MATCH
    assert result.resolved_brand is None
    assert result.stock_label == "货少"
    assert result.source_result.evidence.matched_mpn is None


def test_description_text_is_not_a_certification_badge() -> None:
    row = _row_html("BCM957504-N425G", "Broadcom", "694")
    row = row.replace(
        '<div class="result_supply">',
        '<div class="result_explain" title="SSCP原装正品">SSCP原装正品</div>'
        '<div class="result_supply">',
    )
    result = IcNetAdapter(FakeClient(_page_html(row))).search(
        "BCM957504-N425G", "Broadcom", 200
    )
    assert result.stock_label == "货少"
    assert _fields(result)["certified_stock_total"] == 0


def test_bad_qualified_quantity_maps_to_source_unavailable() -> None:
    html = _page_html(_row_html("ABC", "Acme", "unknown", "SSCP"))
    result = IcNetAdapter(FakeClient(html)).search("ABC", None, 10)

    assert result.source_result.outcome is SourceOutcome.SOURCE_UNAVAILABLE
    assert _fields(result)["failure_code"] == "QUALIFIED_QUANTITY_UNPARSEABLE"


def test_unexpected_page_shape_and_client_failure_are_source_unavailable() -> None:
    bad_page = IcNetAdapter(FakeClient("<html><body>login</body></html>")).search(
        "ABC", None, 10
    )
    blocked = IcNetAdapter(UnavailableClient()).search("ABC", None, 10)

    assert bad_page.source_result.outcome is SourceOutcome.SOURCE_UNAVAILABLE
    assert bad_page.stock_label == "待验证"
    assert _fields(bad_page)["failure_code"] == "RESULT_CONTAINER_MISSING"
    assert bad_page.source_result.evidence.source_url is not None
    assert blocked.source_result.outcome is SourceOutcome.SOURCE_UNAVAILABLE
    assert blocked.stock_label == "待验证"
    assert _fields(blocked)["failure_code"] == "RESULT_PAGE_BLOCKED"
    assert blocked.source_result.evidence.source_url is not None


def test_login_repr_does_not_expose_secret_values() -> None:
    login = IcNetLogin("user-secret", "password-secret")

    rendered = repr(login)
    assert "user-secret" not in rendered
    assert "password-secret" not in rendered



def _cdp_client(
    pages: list[FakeCdpPage],
    *,
    navigate: bool,
    cdp_url: str = "http://127.0.0.1:9333",
    spawn=None,
    login_provider=None,
) -> tuple[CdpIcNetClient, FakeChromium]:
    context = FakeCdpContext(pages, spawn=spawn)
    chromium = FakeChromium(FakeCdpBrowser(context))
    client = CdpIcNetClient(
        cdp_url=cdp_url,
        timeout_ms=1234,
        settle_ms=0,
        navigate=navigate,
        login_provider=login_provider,
        playwright_factory=lambda: FakePlaywright(chromium),
    )
    return client, chromium


@pytest.mark.parametrize(
    "cdp_url",
    [
        "http://localhost:9222",
        "http://127.0.0.1:9222",
        "http://[::1]:9222",
    ],
)
def test_cdp_client_accepts_loopback_endpoints(cdp_url: str) -> None:
    target_url = "https://www.ic.net.cn/search/ABC1.html"
    page = FakeCdpPage(target_url, FIXTURE.read_text(encoding="utf-8"))
    client, chromium = _cdp_client(
        [page],
        navigate=False,
        cdp_url=cdp_url,
    )

    client.fetch_first_page("ABC-123")

    assert chromium.connect_calls == [(cdp_url, 1234)]


def test_cdp_client_rejects_remote_endpoint() -> None:
    with pytest.raises(
        IcNetPageUnavailable,
        match="CDP_REMOTE_ENDPOINT_FORBIDDEN",
    ):
        _cdp_client(
            [],
            navigate=True,
            cdp_url="http://192.0.2.10:9222",
        )


def test_cdp_client_attach_only_reads_exact_existing_page() -> None:
    target_url = "https://www.ic.net.cn/search/ABC1.html"
    page = FakeCdpPage(target_url, FIXTURE.read_text(encoding="utf-8"))
    client, chromium = _cdp_client([page], navigate=False)

    captured = client.fetch_first_page("ABC-123")

    assert captured.url == target_url
    assert captured.html == page.html
    assert page.goto_calls == []
    assert chromium.connect_calls == [("http://127.0.0.1:9333", 1234)]


def test_cdp_client_opens_its_own_page_and_closes_it() -> None:
    """Owner rule: every call opens a tab, uses it, and gives it back."""

    stale = FakeCdpPage(
        "https://www.ic.net.cn/search/STALE.html",
        FIXTURE.read_text(encoding="utf-8"),
    )
    client, chromium = _cdp_client(
        [stale],
        navigate=True,
        spawn=lambda: FakeCdpPage(
            "about:blank", FIXTURE.read_text(encoding="utf-8")
        ),
    )

    captured = client.fetch_first_page("  ABC-123  ")

    context = chromium.browser.contexts[0]
    target_url = "https://www.ic.net.cn/search/ABC1.html"
    assert captured.url == target_url
    assert stale.goto_calls == [], "an earlier tab must not be reused"
    assert len(context.pages) == 2
    assert context.pages[-1].goto_calls == [(target_url, "domcontentloaded", 1234)]
    assert context.pages[-1].closed is True


class _LoginLocator(FakeLocator):
    """One control on IC.net's own login page.

    Only the three form controls are visible: ``#loginCode`` stays hidden until
    the site distrusts the attempt, exactly as the live page behaves, which is
    why it must not count as a visible control here either.
    """

    _VISIBLE = frozenset({"#username", "#password", "#btn_login"})

    def __init__(self, page: "SessionExpiredCdpPage", selector: str) -> None:
        super().__init__(1)
        self._page = page
        self._selector = selector

    def nth(self, _index: int) -> "_LoginLocator":
        return self

    def is_visible(self) -> bool:
        return self._selector in self._VISIBLE

    def fill(self, value: str, *, timeout: int) -> None:
        assert timeout > 0
        self._page.fills.append((self._selector, value))

    def click(self, *, timeout: int) -> None:
        assert timeout > 0
        self._page.clicks.append(self._selector)
        if self._selector == "#btn_login":
            self._page.logged_in = True
            self._page.url = "https://www.ic.net.cn/"


class SessionExpiredCdpPage(FakeCdpPage):
    def __init__(self, html: str) -> None:
        super().__init__("https://www.ic.net.cn/", html)
        self.logged_in = False

    def goto(self, url: str, *, wait_until: str, timeout: int):
        self.goto_calls.append((url, wait_until, timeout))
        self.url = url if self.logged_in else "https://member.ic.net.cn/login.php"

    def click(self, selector: str, *, timeout: int) -> None:
        raise AssertionError(
            f"page-level click({selector!r}) can land on the wrong element"
        )

    def fill(self, selector: str, value: str, *, timeout: int) -> None:
        raise AssertionError(
            f"page-level fill({selector!r}) can land on the wrong element"
        )

    def locator(self, selector: str):
        if selector in {"#username", "#password", "#btn_login", "#loginCode"}:
            return _LoginLocator(self, selector)
        return super().locator(selector)


class LoginProvider:
    def get_login(self, site_id: str) -> IcNetLogin | None:
        assert site_id == "ic.net.cn"
        return IcNetLogin("test-user", "test-password")


def _expired_session_spawn() -> SessionExpiredCdpPage:
    return SessionExpiredCdpPage(FIXTURE.read_text(encoding="utf-8"))


def test_cdp_client_recovers_one_expired_session_with_existing_provider() -> None:
    client, chromium = _cdp_client(
        [],
        navigate=True,
        spawn=_expired_session_spawn,
        login_provider=LoginProvider(),
    )

    captured = client.fetch_first_page("ABC-123")

    page = chromium.browser.contexts[0].pages[-1]
    assert captured.url == "https://www.ic.net.cn/search/ABC1.html"
    assert ("#username", "test-user") in page.fills
    assert ("#password", "test-password") in page.fills
    assert page.clicks == ["#btn_login"]
    assert page.closed is True


def test_cdp_client_reports_login_required_without_existing_provider() -> None:
    page = SessionExpiredCdpPage(FIXTURE.read_text(encoding="utf-8"))
    client, _ = _cdp_client([page], navigate=True, spawn=_expired_session_spawn)

    with pytest.raises(IcNetPageUnavailable, match="LOGIN_REQUIRED"):
        client.fetch_first_page("ABC-123")


def test_cdp_client_classifies_http_forbidden_before_parser() -> None:
    client, _ = _cdp_client(
        [],
        navigate=True,
        spawn=lambda: FakeCdpPage(
            "https://www.ic.net.cn/",
            "<html><body>forbidden</body></html>",
            response_status=403,
        ),
    )

    with pytest.raises(IcNetPageUnavailable, match="HTTP_STATUS_403") as caught:
        client.fetch_first_page("ABC-123")

    assert caught.value.source_url == "https://www.ic.net.cn/search/ABC1.html"


def test_cdp_client_spaces_queries_to_the_same_site(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = _cdp_client(
        [],
        navigate=True,
        spawn=lambda: FakeCdpPage(
            "https://www.ic.net.cn/", FIXTURE.read_text(encoding="utf-8")
        ),
    )
    elapsed = [0.0]
    sleeps: list[float] = []
    monkeypatch.setattr("src.research.icnet.time.monotonic", lambda: elapsed[0])

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        elapsed[0] += seconds

    monkeypatch.setattr("src.research.icnet.time.sleep", sleep)
    client.fetch_first_page("ABC-123")
    elapsed[0] = 10.0
    client.fetch_first_page("ABC-123")
    assert sleeps == [80.0]


def test_cdp_client_navigation_does_not_reuse_unrelated_page() -> None:
    unrelated = FakeCdpPage(
        "https://evil.example/?next=ic.net.cn",
        FIXTURE.read_text(encoding="utf-8"),
    )
    client, chromium = _cdp_client(
        [unrelated],
        navigate=True,
        spawn=lambda: FakeCdpPage(
            "about:blank", FIXTURE.read_text(encoding="utf-8")
        ),
    )

    captured = client.fetch_first_page("ABC-123")

    target_url = "https://www.ic.net.cn/search/ABC1.html"
    context = chromium.browser.contexts[0]
    assert captured.url == target_url
    assert unrelated.goto_calls == []
    assert len(context.pages) == 2
    assert context.pages[1].goto_calls == [
        (target_url, "domcontentloaded", 1234)
    ]


def test_cdp_client_attach_only_requires_target_page_to_be_open() -> None:
    page = FakeCdpPage(
        "https://www.ic.net.cn/search/OTHER.html",
        FIXTURE.read_text(encoding="utf-8"),
    )
    client, _ = _cdp_client([page], navigate=False)

    with pytest.raises(IcNetPageUnavailable, match="CDP_TARGET_PAGE_NOT_OPEN"):
        client.fetch_first_page("ABC-123")

    assert page.goto_calls == []


def test_cdp_client_fails_closed_when_attached_page_has_no_body() -> None:
    target_url = "https://www.ic.net.cn/search/ABC1.html"
    page = FakeCdpPage(
        target_url,
        "<html></html>",
        has_body=False,
    )
    client, _ = _cdp_client([page], navigate=False)

    with pytest.raises(IcNetPageUnavailable, match="RESULT_PAGE_BLOCKED") as caught:
        client.fetch_first_page("ABC-123")

    assert caught.value.source_url == target_url


def test_cdp_client_identifies_visible_search_challenge() -> None:
    client, _ = _cdp_client(
        [],
        navigate=True,
        spawn=lambda: FakeCdpPage(
            "https://www.ic.net.cn/searchPnCode.php?l=ins",
            "对不起！您的速度太快了，请慢一点搜索！请依次点击汉字",
        ),
    )
    with pytest.raises(
        IcNetPageUnavailable, match="INTERACTIVE_CHALLENGE_REQUIRED"
    ):
        client.fetch_first_page("ABC-123")


def test_owner_wgi_suffix_brand_and_certified_stock_use_same_filter():
    html = _page_html(_row_html("WGI210IT S LJXS", "Intel", "100", "SSCP"),
                      _row_html("WGI211IT", "WrongBrand", "99999", "ICCP"))
    result = IcNetAdapter(FakeClient(html)).search("WGI210IT", None, 1)
    assert result.resolved_brand == "Intel"
    assert _fields(result)["certified_stock_total"] == 100
    assert _fields(result)["strict_mpn_rows"] == 1
