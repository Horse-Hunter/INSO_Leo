from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from src.inso.session import SecurityViolation
from src.launcher.inso_session import (
    InsoAuthenticationError,
    attach_inso_research_session,
    ensure_inso_authenticated,
)


class FakeLocator:
    def __init__(self, count: int = 1, visible: bool = True) -> None:
        self._count = count
        self._visible = visible

    def count(self) -> int:
        return self._count

    def is_visible(self) -> bool:
        return self._visible

    def is_enabled(self) -> bool:
        return True


class FakeFrame:
    def __init__(self, url: str, *, shell: bool = False) -> None:
        self.url = url
        self.name = "main" if shell else ""
        self._shell = shell

    def locator(self, _selector: str) -> FakeLocator:
        return FakeLocator(1 if self._shell else 0)


class FakePage:
    def __init__(self, context, *, shell: bool = False) -> None:
        self.context = context
        self.closed = False
        self.main_frame = FakeFrame("https://yingsuo.alperp.cn/", shell=shell)
        self.frames = [self.main_frame]
        if shell:
            self.shell_frame = FakeFrame(
                "https://yingsuo.alperp.cn/skins/etaoerp/InnerEnquiry/YeWuXJ/List.aspx",
                shell=True,
            )
            self.frames.append(self.shell_frame)

    def is_closed(self) -> bool:
        return self.closed


class FakeContext:
    def __init__(self, *, shell_pages: int = 1) -> None:
        self.pages = [FakePage(self, shell=False)]
        self.pages.extend(FakePage(self, shell=True) for _ in range(shell_pages))


class FakeBrowser:
    def __init__(self, contexts) -> None:
        self.contexts = contexts
        self.connected = True

    def is_connected(self) -> bool:
        return self.connected


@dataclass
class FakeBrowserHandle:
    owned: bool
    close_count: int = 0
    disconnect_count: int = 0

    def close(self) -> None:
        self.close_count += 1

    def disconnect(self) -> None:
        self.disconnect_count += 1


class FakePlaywright:
    def __init__(self, browser) -> None:
        self.chromium = SimpleNamespace(connect_over_cdp=lambda _endpoint: browser)
        self.stop_count = 0

    def start(self):
        return self

    def stop(self) -> None:
        self.stop_count += 1


def attach(browser, browser_handle, drained=lambda _cycle: True):
    playwright = FakePlaywright(browser)
    session = attach_inso_research_session(
        "http://127.0.0.1:9222/",
        browser_handle,
        cycle_id="cycle-1",
        cycle_is_drained=drained,
        playwright_factory=lambda: playwright,
    )
    return session, playwright


def test_reused_session_uses_verified_shell_and_leaves_all_pages_open() -> None:
    context = FakeContext()
    browser = FakeBrowser([context])
    browser_handle = FakeBrowserHandle(owned=False)
    unrelated_page, shell_page = context.pages
    session, playwright = attach(browser, browser_handle)

    with session.operation_access().operation_page() as operation:
        assert operation.page is shell_page
        assert operation.shell_frame is shell_page.shell_frame
    session.close_after_drain()

    assert all(not page.is_closed() for page in context.pages)
    assert browser.connected is True
    assert browser_handle.close_count == 0
    assert browser_handle.disconnect_count == 1
    assert playwright.stop_count == 0
    assert unrelated_page.is_closed() is False


def test_login_redirect_and_wrong_origin_are_not_shell_candidates() -> None:
    for invalid in ("https://yingsuo.alperp.cn/login.aspx", "https://example.invalid/"):
        context = FakeContext()
        context.pages[1].main_frame.url = invalid
        browser = FakeBrowser([context])
        with pytest.raises(SecurityViolation):
            attach(browser, FakeBrowserHandle(owned=False))
        assert all(not page.is_closed() for page in context.pages)


def test_pinned_page_removed_from_context_fails_closed() -> None:
    context = FakeContext()
    browser = FakeBrowser([context])
    session, _ = attach(browser, FakeBrowserHandle(owned=False))
    operation = session.operation_access().operation_page()
    context.pages.remove(context.pages[1])

    with pytest.raises(SecurityViolation):
        _ = operation.page


def test_ambiguous_context_fails_closed_without_closing_any_page() -> None:
    browser = FakeBrowser([FakeContext(), FakeContext()])
    browser_handle = FakeBrowserHandle(owned=False)
    playwright = FakePlaywright(browser)

    with pytest.raises(SecurityViolation):
        attach_inso_research_session(
            "http://127.0.0.1:9222",
            browser_handle,
            cycle_id="cycle-1",
            cycle_is_drained=lambda _cycle: True,
            playwright_factory=lambda: playwright,
        )

    assert playwright.stop_count == 1
    assert browser_handle.close_count == 0
    assert all(not page.is_closed() for context in browser.contexts for page in context.pages)


def test_missing_or_multiple_verified_shells_fail_closed() -> None:
    for context in (FakeContext(shell_pages=0), FakeContext(shell_pages=2)):
        browser = FakeBrowser([context])
        with pytest.raises(SecurityViolation):
            attach(browser, FakeBrowserHandle(owned=False))
        assert all(not page.is_closed() for page in context.pages)


def test_shell_identity_change_fails_closed_before_next_operation() -> None:
    context = FakeContext()
    browser = FakeBrowser([context])
    session, _ = attach(browser, FakeBrowserHandle(owned=False))
    operation = session.operation_access().operation_page()
    shell_page = context.pages[1]
    shell_page.frames = [shell_page.main_frame]

    with pytest.raises(SecurityViolation):
        _ = operation.page


def test_app_owned_browser_closes_only_after_cycle_drain() -> None:
    browser = FakeBrowser([FakeContext()])
    browser_handle = FakeBrowserHandle(owned=True)
    drained = False
    session, _playwright = attach(browser, browser_handle, lambda _cycle: drained)
    pages = tuple(browser.contexts[0].pages)

    with pytest.raises(SecurityViolation):
        session.close_after_drain()
    assert browser_handle.close_count == 0

    drained = True
    session.close_after_drain()
    assert browser_handle.close_count == 1
    assert all(not page.is_closed() for page in pages)


@dataclass(frozen=True)
class _Login:
    username: str = "synthetic-user"
    password: str = "synthetic-password"
    company: str | None = None


class _LoginControl(FakeLocator):
    def __init__(self, page, *, count=1, name="", type_="", value="", field=None):
        super().__init__(count=count, visible=page.control_visible)
        self.page = page
        self.name = name
        self.type_ = type_
        self.value = value
        self.field = field
        self.filled = None

    def get_attribute(self, name):
        return {"name": self.name, "type": self.type_, "value": self.value}.get(name)

    def fill(self, value):
        self.filled = value
        if self.field and not self.page.write_failures.get(self.field, False):
            self.page.values[self.field] = value

    def input_value(self):
        return self.page.values.get(self.field, self.value)

    def click(self):
        self.page.clicks += 1
        if self.page.authenticates:
            self.page.main_frame.url = "https://yingsuo.alperp.cn/"
            self.page.shell_frame = FakeFrame(
                "https://yingsuo.alperp.cn/skins/etaoerp/InnerEnquiry/YeWuXJ/List.aspx",
                shell=True,
            )
            self.page.frames = [self.page.main_frame, self.page.shell_frame]

    def inner_text(self):
        return self.page.body_text


class _LoginPage(FakePage):
    def __init__(self, context, *, button_count=1, authenticates=True, body_text=""):
        super().__init__(context, shell=False)
        self.main_frame.url = "https://yingsuo.alperp.cn/login.aspx"
        self.button_count = button_count
        self.authenticates = authenticates
        self.body_text = body_text
        self.clicks = 0
        self.values = {}
        self.write_failures = {}
        self.control_visible = True
        self.control_enabled = True

    def locator(self, selector):
        if selector == "body":
            return _LoginControl(self)
        if selector == "input#personname:visible":
            return _LoginControl(self, name="personname", type_="text", field="username")
        if selector == "input#password:visible":
            return _LoginControl(self, name="password", type_="password", field="password")
        return _LoginControl(self, count=0)

    def get_by_text(self, text, *, exact):
        assert text == "登录" and exact is True
        control = _LoginControl(self, count=self.button_count, type_="button", value="登录")
        control.is_enabled = lambda: self.control_enabled
        return control


def _login_browser(page: FakePage) -> FakeBrowser:
    context = page.context
    context.pages = [page]
    return FakeBrowser([context])


def test_ordinary_login_recovery_reuses_a_verified_shell_without_clicking() -> None:
    context = FakeContext(shell_pages=1)
    browser = FakeBrowser([context])

    ensure_inso_authenticated(browser, _Login())

    assert all(not hasattr(page, "clicks") or page.clicks == 0 for page in context.pages)


def test_ordinary_login_recovery_fills_confirmed_controls_once_then_verifies_shell() -> None:
    context = FakeContext(shell_pages=0)
    page = _LoginPage(context)
    browser = _login_browser(page)

    ensure_inso_authenticated(browser, _Login())

    assert page.clicks == 1
    assert page.main_frame.url == "https://yingsuo.alperp.cn/"
    assert len(page.frames) == 2
    assert page.values == {"username": "synthetic-user", "password": "synthetic-password"}


@pytest.mark.parametrize("field", ("username", "password"))
def test_ordinary_login_recovery_does_not_submit_when_fill_readback_is_empty(field) -> None:
    context = FakeContext(shell_pages=0)
    page = _LoginPage(context)
    page.write_failures[field] = True

    with pytest.raises(InsoAuthenticationError) as error:
        ensure_inso_authenticated(_login_browser(page), _Login())

    assert error.value.reason_code == "AUTHENTICATION_REQUIRED"
    assert page.clicks == 0


def test_ordinary_login_recovery_requires_visible_enabled_unique_login_control() -> None:
    context = FakeContext(shell_pages=0)
    page = _LoginPage(context)
    page.control_enabled = False

    with pytest.raises(InsoAuthenticationError):
        ensure_inso_authenticated(_login_browser(page), _Login())

    assert page.clicks == 0


@pytest.mark.parametrize(
    "login,button_count,authenticates,body_text,expected",
    [
        (None, 1, True, "", "AUTHENTICATION_REQUIRED"),
        (_Login(), 2, True, "", "AUTHENTICATION_REQUIRED"),
        (_Login(), 1, False, "", "AUTHENTICATED_SHELL_UNAVAILABLE"),
        (_Login(), 1, True, "CAPTCHA", "MANUAL_VERIFICATION_REQUIRED"),
        (_Login(), 1, True, "设备验证", "MANUAL_VERIFICATION_REQUIRED"),
    ],
)
def test_ordinary_login_recovery_fails_closed(
    login, button_count, authenticates, body_text, expected
) -> None:
    context = FakeContext(shell_pages=0)
    page = _LoginPage(
        context,
        button_count=button_count,
        authenticates=authenticates,
        body_text=body_text,
    )

    with pytest.raises(InsoAuthenticationError) as error:
        ensure_inso_authenticated(
            _login_browser(page), login, timeout_seconds=0, wait=lambda _delay: None
        )

    assert error.value.reason_code == expected
    assert page.clicks <= 1


def test_ordinary_login_recovery_rejects_a_wrong_origin() -> None:
    context = FakeContext(shell_pages=0)
    page = _LoginPage(context)
    page.main_frame.url = "https://example.invalid/login.aspx"

    with pytest.raises(InsoAuthenticationError) as error:
        ensure_inso_authenticated(_login_browser(page), _Login())

    assert error.value.reason_code == "AUTHENTICATION_REQUIRED"
    assert page.clicks == 0


def test_authentication_failure_never_exposes_credential_values() -> None:
    secret = _Login(username="account-secret", password="password-secret")
    context = FakeContext(shell_pages=0)
    page = _LoginPage(context, button_count=2)

    with pytest.raises(InsoAuthenticationError) as error:
        ensure_inso_authenticated(_login_browser(page), secret)

    assert "account-secret" not in repr(error.value)
    assert "password-secret" not in repr(error.value)


def test_app_owned_browser_closes_when_manual_verification_stops_login() -> None:
    context = FakeContext(shell_pages=0)
    page = _LoginPage(context, body_text="CAPTCHA")
    browser = _login_browser(page)
    browser_handle = FakeBrowserHandle(owned=True)
    playwright = FakePlaywright(browser)

    with pytest.raises(InsoAuthenticationError) as error:
        attach_inso_research_session(
            "http://127.0.0.1:9222",
            browser_handle,
            cycle_id="cycle-1",
            cycle_is_drained=lambda _cycle: True,
            playwright_factory=lambda: playwright,
            login=_Login(),
        )

    assert error.value.reason_code == "MANUAL_VERIFICATION_REQUIRED"
    assert browser_handle.close_count == 1
    assert browser_handle.disconnect_count == 0
