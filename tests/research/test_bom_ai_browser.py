from typing import Self

import pytest

from src.research.bom_ai import (
    BomAiBrowserConfig,
    BomAiClientError,
    BomAiLogin,
    CdpBomAiAuthenticatedBrowser,
)

LOGIN_URL = "https://www.bom.ai/login"
RESULT_TEMPLATE = "https://www.bom.ai/search/{mpn}"


def _config(**overrides: object) -> BomAiBrowserConfig:
    values: dict = {
        "login_url": LOGIN_URL,
        "result_url_template": RESULT_TEMPLATE,
        "username_selector": "#username",
        "password_selector": "#password",
        "login_button_selector": "#login-button",
    }
    values.update(overrides)
    return BomAiBrowserConfig(**values)


def test_config_rejects_insecure_incomplete_or_mismatched_settings() -> None:
    with pytest.raises(ValueError):
        _config(login_url="http://www.bom.ai/login")
    with pytest.raises(ValueError):
        _config(login_url="https://evil.example/login")
    with pytest.raises(ValueError):
        _config(result_url_template="https://www.bom.ai/search")
    with pytest.raises(ValueError):
        _config(result_url_template="https://evil.example/search/{mpn}")
    with pytest.raises(ValueError):
        _config(result_url_template="http://www.bom.ai/search/{mpn}")
    with pytest.raises(ValueError):
        _config(username_selector="   ")
    with pytest.raises(ValueError):
        _config(company_selector="   ")
    with pytest.raises(ValueError):
        _config(post_login_ready_selector="")


def test_result_url_quotes_the_trimmed_mpn() -> None:
    config = _config()

    assert config.result_url("  Ab c-1  ") == "https://www.bom.ai/search/Ab%20c-1"


class CdpLocator:
    def __init__(self, page: "CdpPage", selector: str, count: int = 1) -> None:
        self.page = page
        self.selector = selector
        self._count = count

    def count(self) -> int:
        if self.selector == "a.bom_layer_login:visible":
            return int(not self.page.logged_in)
        if self.selector == "#accountName:visible":
            return int(not self.page.logged_in)
        return self._count

    @property
    def first(self) -> "CdpLocator":
        return self

    @property
    def last(self) -> "CdpLocator":
        return self

    def locator(self, selector: str) -> "CdpLocator":
        return CdpLocator(self.page, selector)

    def get_by_text(self, text: str, *, exact: bool) -> "CdpLocator":
        assert (text, exact) == ("账号登录", True)
        return CdpLocator(self.page, text, self.page.account_tab_count)

    def nth(self, _index: int) -> "CdpLocator":
        return self

    def is_visible(self) -> bool:
        return True

    def fill(self, value: str, *, timeout: int | None = None) -> None:
        if timeout is not None:
            assert timeout > 0
        self.page.calls.append(("fill", self.selector, value))

    def click(self, *, timeout: int | None = None) -> None:
        if timeout is not None:
            assert timeout > 0
        self.page.calls.append(("click", self.selector, None))
        if self.selector == "#smsLoginBtn":
            self.page.logged_in = True
        if self.selector in self.page.options:
            self.page.options[self.selector] = not self.page.options[self.selector]

    def evaluate(self, _script: str) -> object:
        """The state of the checkbox this option label stands for.

        Measured live on www.bom.ai 2026-10-01: each label wraps its own
        ``input[type=checkbox]``, and "记住密码" reads as *on* while
        "30天内免登录" reads as off.
        """

        return self.page.options.get(self.selector)

    def inner_text(self) -> str:
        return self.page.visible_text


class CdpPage:
    def __init__(
        self,
        *,
        account_tab_count: int = 1,
        visible_text: str = "result",
        options: dict[str, bool] | None = None,
    ) -> None:
        self.url = "https://www.bom.ai/components-price/ABC.html"
        self.account_tab_count = account_tab_count
        self.visible_text = visible_text
        self.logged_in = False
        self.closed = False
        self.calls: list[tuple[str, str, str | None]] = []
        self.options = (
            {
                'text="30天内免登录"': False,
                'text="记住密码"': True,
            }
            if options is None
            else options
        )

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        assert wait_until == "domcontentloaded"
        assert timeout > 0
        self.url = url
        self.calls.append(("goto", url, None))

    def wait_for_timeout(self, timeout: int) -> None:
        assert timeout >= 0

    def fill(self, selector: str, value: str, *, timeout: int) -> None:
        raise AssertionError(
            f"page-level fill({selector!r}) can land on the wrong element"
        )

    def click(self, selector: str, *, timeout: int) -> None:
        raise AssertionError(
            f"page-level click({selector!r}) can land on the wrong element"
        )

    def locator(self, selector: str) -> CdpLocator:
        return CdpLocator(self, selector)

    def content(self) -> str:
        return "<html>result</html>"

    def close(self) -> None:
        self.closed = True


class CdpContext:
    def __init__(self, page: CdpPage) -> None:
        self.pages = [page]


class CdpBrowser:
    def __init__(self, page: CdpPage) -> None:
        self.contexts = [CdpContext(page)]


class CdpChromium:
    def __init__(self, page: CdpPage) -> None:
        self.page = page

    def connect_over_cdp(self, url: str, *, timeout: int) -> CdpBrowser:
        assert url == "http://127.0.0.1:9222"
        assert timeout > 0
        return CdpBrowser(self.page)


class CdpPlaywright:
    def __init__(self, page: CdpPage) -> None:
        self.chromium = CdpChromium(page)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _cdp_browser(monkeypatch, page: CdpPage) -> CdpBomAiAuthenticatedBrowser:
    monkeypatch.setattr(
        "src.research.bom_ai.new_background_page",
        lambda _browser, _context, **_kwargs: page,
    )
    return CdpBomAiAuthenticatedBrowser(
        _config(
            username_selector="#accountName",
            password_selector="#smspassword",
            login_button_selector="#smsLoginBtn",
        ),
        settle_ms=0,
        playwright_factory=lambda: CdpPlaywright(page),
    )


def test_cdp_browser_recovers_one_expired_session_then_retries_original_page(
    monkeypatch,
) -> None:
    page = CdpPage()

    capture = _cdp_browser(monkeypatch, page).fetch_price_page(
        "ABC", BomAiLogin("user", "secret")
    )

    assert ("click", "账号登录", None) in page.calls
    assert ("fill", "#accountName", "user") in page.calls
    assert ("fill", "#smspassword", "secret") in page.calls
    assert page.calls.count(("goto", "https://www.bom.ai/search/ABC", None)) == 2
    assert capture.html == "<html>result</html>"
    assert page.closed is True, "the call must give its tab back"


def test_cdp_browser_reports_changed_login_ui_without_retrying(monkeypatch) -> None:
    page = CdpPage(account_tab_count=0)

    with pytest.raises(BomAiClientError) as error:
        _cdp_browser(monkeypatch, page).fetch_price_page(
            "ABC", BomAiLogin("user", "secret")
        )

    assert error.value.code == "RESULT_CHANGED"
    assert page.calls.count(("goto", "https://www.bom.ai/search/ABC", None)) == 1
    assert page.closed is True


def test_cdp_browser_stops_for_a_visible_challenge(monkeypatch) -> None:
    page = CdpPage(visible_text="请完成安全验证")

    with pytest.raises(BomAiClientError) as error:
        _cdp_browser(monkeypatch, page).fetch_price_page(
            "ABC", BomAiLogin("user", "secret")
        )

    assert error.value.code == "INTERACTIVE_CHALLENGE_REQUIRED"
    assert page.closed is True


def test_cdp_browser_leaves_an_option_that_is_already_on_alone(monkeypatch) -> None:
    """Owner rule 2026-10-01: "记住密码" and "30天内免登录" must both be on.

    "记住密码" defaults to on, so clicking it would turn it *off* -- the state
    is read before anything is clicked.
    """

    page = CdpPage()

    _cdp_browser(monkeypatch, page).fetch_price_page(
        "ABC", BomAiLogin("user", "secret")
    )

    assert ("click", 'text="30天内免登录"', None) in page.calls
    assert ("click", 'text="记住密码"', None) not in page.calls
    assert page.options == {
        'text="30天内免登录"': True,
        'text="记住密码"': True,
    }


def test_cdp_browser_refuses_to_submit_an_option_it_cannot_confirm(
    monkeypatch,
) -> None:
    """A label with no provable checkbox is not toggled blind."""

    page = CdpPage(options={})

    with pytest.raises(BomAiClientError) as error:
        _cdp_browser(monkeypatch, page).fetch_price_page(
            "ABC", BomAiLogin("user", "secret")
        )

    assert error.value.code == "LOGIN_OPTION_UNCONFIRMED"
    assert ("click", "#smsLoginBtn", None) not in page.calls
    assert page.closed is True
