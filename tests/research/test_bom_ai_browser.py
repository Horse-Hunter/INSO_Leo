from typing import Self

import pytest

from src.research.bom_ai import (
    BomAiBrowserConfig,
    BomAiClientError,
    BomAiLogin,
    PlaywrightBomAiAuthenticatedBrowser,
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


class FakeLocator:
    def __init__(self, name: str, calls: list, count: int, html: str) -> None:
        self.name = name
        self.calls = calls
        self._count = count
        self._html = html

    def count(self) -> int:
        return self._count

    @property
    def first(self) -> "FakeLocator":
        return self

    def is_visible(self) -> bool:
        return self._count > 0

    def inner_text(self) -> str:
        return self._html

    def fill(self, value: str) -> None:
        self.calls.append(("fill", self.name, value))

    def click(self) -> None:
        self.calls.append(("click", self.name, None))


class FakePage:
    def __init__(
        self,
        url: str = LOGIN_URL,
        html: str = "<html>ok</html>",
        visible_text: str | None = None,
    ) -> None:
        self.url = url
        self.html = html
        self.visible_text = html if visible_text is None else visible_text
        self.calls: list = []
        self.login_form_present = True

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        assert wait_until == "domcontentloaded"
        assert timeout > 0
        self.url = url
        self.calls.append(("goto", url, None))

    def locator(self, selector: str) -> FakeLocator:
        count = 1
        if not self.login_form_present and selector in {
            "#username",
            "#password",
            "#login-button",
            "#company",
        }:
            count = 0
        return FakeLocator(selector, self.calls, count, self.visible_text)

    def wait_for_timeout(self, timeout: int) -> None:
        assert timeout >= 0

    def wait_for_selector(self, selector: str, *, state: str, timeout: int) -> None:
        assert state == "visible"
        assert timeout > 0
        self.calls.append(("wait_for_selector", selector, None))

    def content(self) -> str:
        return self.html


class FakeBrowser:
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.closed = False

    def new_page(self) -> FakePage:
        return self.page

    def close(self) -> None:
        self.closed = True


class FakeChromium:
    def __init__(self, browser: FakeBrowser) -> None:
        self.browser = browser

    def launch(self, *, channel: str, headless: bool) -> FakeBrowser:
        assert channel == "chrome"
        assert not headless
        return self.browser


class FakePlaywright:
    def __init__(self, chromium: FakeChromium) -> None:
        self.chromium = chromium

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _browser(page: FakePage, config: BomAiBrowserConfig) -> tuple[
    PlaywrightBomAiAuthenticatedBrowser, FakeBrowser
]:
    fake_browser = FakeBrowser(page)
    acquisition = PlaywrightBomAiAuthenticatedBrowser(
        config,
        settle_ms=0,
        playwright_factory=lambda: FakePlaywright(FakeChromium(fake_browser)),
    )
    return acquisition, fake_browser


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


def test_browser_logs_in_and_captures_the_target_model_page() -> None:
    page = FakePage()
    acquisition, fake_browser = _browser(page, _config(post_login_ready_selector="#app"))

    capture = acquisition.fetch_price_page(
        " ABC-1 ", BomAiLogin("synthetic-user", "synthetic-password")
    )

    assert ("fill", "#username", "synthetic-user") in page.calls
    assert ("fill", "#password", "synthetic-password") in page.calls
    assert ("click", "#login-button", None) in page.calls
    assert ("goto", "https://www.bom.ai/search/ABC-1", None) in page.calls
    assert ("wait_for_selector", "#app", None) in page.calls
    assert capture.url == "https://www.bom.ai/search/ABC-1"
    assert capture.html == "<html>ok</html>"
    assert fake_browser.closed


def test_browser_skips_login_when_no_form_is_present() -> None:
    page = FakePage()
    page.login_form_present = False
    acquisition, _ = _browser(page, _config())

    acquisition.fetch_price_page("ABC", BomAiLogin("u", "p"))

    assert all(call[0] != "fill" for call in page.calls)
    assert ("goto", "https://www.bom.ai/search/ABC", None) in page.calls


def test_hidden_challenge_word_is_not_treated_as_visible_verification() -> None:
    page = FakePage(html="<script>captcha</script>", visible_text="normal result")
    page.login_form_present = False
    acquisition, _ = _browser(page, _config())
    capture = acquisition.fetch_price_page("ABC", BomAiLogin("u", "p"))
    assert capture.html == "<script>captcha</script>"


def test_company_selector_requires_a_company_credential() -> None:
    page = FakePage()
    acquisition, _ = _browser(page, _config(company_selector="#company"))

    with pytest.raises(BomAiClientError) as error:
        acquisition.fetch_price_page("ABC", BomAiLogin("u", "p", None))

    assert error.value.code == "COMPANY_CREDENTIAL_UNAVAILABLE"


def test_challenge_and_cross_host_navigation_fail_closed() -> None:
    page = FakePage(html="<html>请完成安全验证 captcha</html>")
    acquisition, _ = _browser(page, _config())

    with pytest.raises(BomAiClientError) as challenge:
        acquisition.fetch_price_page("ABC", BomAiLogin("u", "p"))
    assert challenge.value.code == "INTERACTIVE_CHALLENGE_REQUIRED"

    class RedirectPage(FakePage):
        def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
            super().goto(url, wait_until=wait_until, timeout=timeout)
            if "search" in url:
                self.url = "https://unexpected.example/search/ABC"

    redirected, _ = _browser(RedirectPage(), _config())
    with pytest.raises(BomAiClientError) as cross_host:
        redirected.fetch_price_page("ABC", BomAiLogin("u", "p"))
    assert cross_host.value.code == "UNEXPECTED_NAVIGATION_HOST"


def test_browser_exposes_only_read_only_acquisition() -> None:
    acquisition, _ = _browser(FakePage(), _config())

    for forbidden in ("submit", "create_order", "write", "checkout", "purchase"):
        assert not hasattr(acquisition, forbidden)
