from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from src.inso.session import SecurityViolation
from src.launcher.inso_session import (
    InsoAuthenticationError,
    InsoSessionGuard,
    InsoSessionOutcome,
    _existing_or_new_login_page,
    _list_page_is_authenticated,
    attach_inso_research_session,
    ensure_inso_authenticated,
)

_LIST_URL = "https://yingsuo.alperp.cn/skins/etaoerp//InnerEnquiry/YeWuXJ/List.aspx"
_LOGIN_URL = "https://yingsuo.alperp.cn/login.aspx?t=islogin"
_CHECKING_URL = "https://yingsuo.alperp.cn/skins/etaoerp/home/checking.aspx?gourl=x"


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
    def __init__(
        self, url: str, *, shell: bool = False, grid: str = "visible"
    ) -> None:
        self.url = url
        self.name = "main" if shell else ""
        self._shell = shell
        self._grid = grid

    def locator(self, selector: str) -> FakeLocator:
        if not self._shell:
            return FakeLocator(0)
        if selector == "#_id_dg":
            if self._grid == "absent":
                return FakeLocator(0)
            return FakeLocator(1, visible=self._grid == "visible")
        return FakeLocator(1)


class FakePage:
    def __init__(self, context, *, shell: bool = False, grid: str = "visible") -> None:
        self.context = context
        self.closed = False
        self.renders_list = False
        self.gotos: list[str] = []
        self.main_frame = FakeFrame("https://yingsuo.alperp.cn/", shell=shell)
        self.frames = [self.main_frame]
        if shell:
            self.shell_frame = FakeFrame(
                "https://yingsuo.alperp.cn/skins/etaoerp/InnerEnquiry/YeWuXJ/List.aspx",
                shell=True,
                grid=grid,
            )
            self.frames.append(self.shell_frame)

    def is_closed(self) -> bool:
        return self.closed

    def close(self):
        self.closed = True

    def evaluate(self, _script):
        """The ERP's own markers, as a real page reports them."""

        if "fn?.BillTab" in _script:
            return True

        if self.renders_list:
            return {
                "grid": 1,
                "detail": 1,
                "select": 1,
                "stub": 0,
                "detailDrawn": 1,
                "selectDrawn": 1,
            }
        return {
            "grid": 0,
            "detail": 0,
            "select": 0,
            "stub": 1,
            "detailDrawn": 0,
            "selectDrawn": 0,
        }

    def goto(self, url, wait_until=None, timeout=None):
        """A navigation only lands on the list when the session is live."""

        self.gotos.append(url)
        if not self.renders_list:
            self.main_frame.url = "https://yingsuo.alperp.cn/login.aspx?t=islogin"


class FakeContext:
    def __init__(self, *, shell_pages: int = 1, grid: str = "visible") -> None:
        self.pages = [FakePage(self, shell=False)]
        self.pages.extend(
            FakePage(self, shell=True, grid=grid) for _ in range(shell_pages)
        )

    def new_page(self) -> FakePage:
        page = FakePage(self, shell=False)
        self.pages.append(page)
        return page


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


def test_explicit_owned_order_page_does_not_borrow_an_existing_shell():
    context = FakeContext(shell_pages=2)
    browser = FakeBrowser([context])
    handle = FakeBrowserHandle(owned=False)
    order_page = context.pages[-1]
    session = attach_inso_research_session(
        "http://127.0.0.1:9222", handle, cycle_id="order",
        cycle_is_drained=lambda _: True,
        playwright_factory=lambda: FakePlaywright(browser),
        operation_page=order_page, owns_operation_page=True,
    )
    assert session.operation_access().operation_page().page is order_page
    session.close_owned_operation_tab()
    assert order_page.closed
    assert not context.pages[1].closed
    assert browser.connected and handle.close_count == 0


def test_fresh_login_never_selects_an_existing_inso_page(monkeypatch):
    context = FakeContext()
    observed = []
    monkeypatch.setattr(InsoSessionGuard, "_log_in", lambda self, page: observed.append(page) or False)
    monkeypatch.setattr(InsoSessionGuard, "_prove", lambda self, page: True)
    guard = InsoSessionGuard(login=_Login(), context=lambda: context, fresh_page=True)
    old_pages = tuple(context.pages)
    assert guard.ensure_authenticated().outcome is InsoSessionOutcome.AUTHENTICATED
    assert guard.opened_page not in old_pages
    assert observed == [guard.opened_page]


def test_failed_fresh_lease_closes_only_the_new_tab(monkeypatch):
    context = FakeContext()
    new_page = FakePage(context)
    browser = FakeBrowser([context])
    monkeypatch.setattr("src.launcher.inso_session.ensure_inso_authenticated", lambda *_a, **_k: new_page)
    with pytest.raises(SecurityViolation):
        attach_inso_research_session(
            "http://127.0.0.1:9222", FakeBrowserHandle(owned=False),
            cycle_id="cycle", cycle_is_drained=lambda _c: True,
            playwright_factory=lambda: FakePlaywright(browser), login=_Login(), fresh_page=True,
        )
    assert new_page.closed
    assert all(not page.closed for page in context.pages)


@pytest.mark.parametrize("challenge", ["CAPTCHA", "手机验证码", "设备验证"])
def test_fresh_manual_verification_page_survives_backend_cleanup(tmp_path, monkeypatch, challenge):
    from src.gui.contracts import RunState
    from src.launcher import backend as launcher
    from src.launcher.browser_bootstrap import BrowserBootstrapError, BrowserHandle

    context = FakeContext()
    old_pages = tuple(context.pages)
    page = _LoginPage(context, body_text=challenge)

    def new_page():
        context.pages.append(page)
        return page

    monkeypatch.setattr(context, "new_page", new_page)
    browser = FakeBrowser([context])
    playwright = FakePlaywright(browser)
    closures = []
    handle = BrowserHandle(owned=False, browser=browser, playwright=playwright,
        close_fn=lambda: closures.append("browser"), cleanup_fn=lambda: closures.append("profile"))
    backend = launcher.ProductionBackend(root=tmp_path, browser_acquirer=lambda *_a, **_k: handle)
    monkeypatch.setattr(launcher, "assess_readiness", lambda *_a, **_k: SimpleNamespace(ready=True))
    monkeypatch.setattr(launcher, "CoreLoginBridge", lambda: SimpleNamespace(login=lambda _site: _Login()))
    monkeypatch.setattr(backend, "_alert_owner_of_login", lambda **_k: None)
    parks = []
    monkeypatch.setattr(launcher, "park_shared_cdp", lambda browser: parks.append(browser))
    config = SimpleNamespace(cdp=SimpleNamespace(cdp_url="http://127.0.0.1:9222"))

    with pytest.raises(BrowserBootstrapError) as error:
        backend._open_research_session(config, object())
    assert isinstance(error.value.__cause__, InsoAuthenticationError)
    assert error.value.__cause__.reason_code == "MANUAL_VERIFICATION_REQUIRED"
    assert not page.closed and page.clicks == 0
    backend._runtime_error(error.value)
    assert backend.get_status().state is RunState.MANUAL_REVIEW
    assert backend._immediate_stop_requested()
    backend._close_inso_order_tab()
    # Also exercise the existing MANUAL_REVIEW guard with a retained attachment.
    backend._browser_handle = SimpleNamespace(browser=browser)
    backend._close_inso_order_tab()
    backend._browser_handle = None
    backend.shutdown()
    assert parks == [browser], "only the pre-inquiry park is allowed"
    assert not page.closed and all(not p.closed for p in old_pages)
    assert browser.connected and browser.contexts == [context]
    assert page in context.pages and closures == []
    assert playwright.stop_count == 1, "disconnect the client, never close Chrome"


@pytest.mark.parametrize("failure", ["AUTHENTICATION_REQUIRED", "AUTHENTICATED_SHELL_UNAVAILABLE"])
def test_ordinary_fresh_authentication_failure_still_closes_only_owned_tab(monkeypatch, failure):
    context = FakeContext()
    old_pages = tuple(context.pages)
    page = _LoginPage(context)
    context.pages.append(page)
    monkeypatch.setattr(context, "new_page", lambda: page)

    def fail_login(_guard, _page):
        raise InsoAuthenticationError(failure)

    monkeypatch.setattr(InsoSessionGuard, "_log_in", fail_login)
    browser = FakeBrowser([context])
    with pytest.raises(InsoAuthenticationError) as error:
        ensure_inso_authenticated(browser, _Login(), fresh_page=True)
    assert error.value.reason_code == failure
    assert page.closed and all(not p.closed for p in old_pages)
    assert browser.connected and browser.contexts == [context]


def test_login_guard_stays_on_the_current_order_page(monkeypatch):
    context = FakeContext(shell_pages=2)
    selected = context.pages[-1]
    observed = []
    monkeypatch.setattr(InsoSessionGuard, "_log_in", lambda self, page: observed.append(page) or True)
    monkeypatch.setattr(InsoSessionGuard, "_prove", lambda self, page: True)
    guard = InsoSessionGuard(login=_Login(), context=lambda: context, page=lambda: selected)
    assert guard.ensure_authenticated().outcome is InsoSessionOutcome.RESTORED
    assert guard.authenticated_page is selected
    assert observed == [selected]


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


def test_collapsed_result_grid_still_verifies_but_a_missing_grid_does_not() -> None:
    """A duplicate query legitimately collapses the grid; it must not blind us.

    An empty read-only exact query zeroes #_id_dg while the authenticated list
    shell stays usable, so the next poll cycle must still attach. A genuinely
    absent grid -- and a login/landing page that never had one -- stays closed.
    """

    collapsed = FakeContext(shell_pages=1, grid="collapsed")
    session, _ = attach(FakeBrowser([collapsed]), FakeBrowserHandle(owned=False))
    assert session is not None
    with session.operation_access().operation_page() as operation:
        assert operation.shell_frame is collapsed.pages[1].shell_frame

    for grid in ("absent", "visible"):
        for shell_pages in (0, 2):
            context = FakeContext(shell_pages=shell_pages, grid=grid)
            with pytest.raises(SecurityViolation):
                attach(FakeBrowser([context]), FakeBrowserHandle(owned=False))


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
        self.page.clicked = True
        if self.page.authenticates and self.page.redirects_after_click:
            # The ERP's own script navigates away from the form once the submit
            # succeeds. The guard waits for exactly this before navigating.
            self.page.main_frame.url = "https://yingsuo.alperp.cn/"

    def inner_text(self):
        return self.page.body_text


class _LoginPage(FakePage):
    def wait_for_timeout(self, _milliseconds):
        pass

    def __init__(self, context, *, button_count=1, authenticates=True, body_text=""):
        super().__init__(context, shell=False)
        self.main_frame.url = "https://yingsuo.alperp.cn/login.aspx"
        self.button_count = button_count
        self.authenticates = authenticates
        self.body_text = body_text
        self.clicks = 0
        self.clicked = False
        self.redirects_after_click = True
        self.values = {}
        self.write_failures = {}
        self.control_visible = True
        self.control_enabled = True

    def goto(self, url, wait_until=None, timeout=None):
        """Model the live ERP: submitting the form is what makes the list render."""

        self.gotos.append(url)
        if url == _LOGIN_URL:
            self.main_frame.url = url
            self.frames = [self.main_frame]
            self.renders_list = False
            return
        if self.authenticates and self.clicked:
            self.main_frame.url = url
            self.renders_list = True
            return
        self.main_frame.url = "https://yingsuo.alperp.cn/login.aspx?t=islogin"

    def locator(self, selector):
        if selector == "a#iframe_YeWuXJ_menu":
            page = self

            class Entry(FakeLocator):
                def click(self, **_kwargs):
                    page.menu_clicks = getattr(page, "menu_clicks", 0) + 1
                    page.shell_frame = FakeFrame(_LIST_URL, shell=True)
                    page.frames = [page.main_frame, page.shell_frame]
                    page.renders_list = True

            return Entry(count=int(self.main_frame.url == "https://yingsuo.alperp.cn/"))
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


def test_ordinary_login_recovery_reopens_the_list_before_trusting_anything() -> None:
    """A page that already renders the list is proven live, without a login.

    The proof is the navigation itself: the page is sent to the list again and
    judged by what the ERP renders, never by what an old document still shows.
    """

    context = FakeContext(shell_pages=0)
    page = _LiveListPage(context)
    browser = _login_browser(page)

    ensure_inso_authenticated(browser, _Login())

    assert page.gotos == [_LOGIN_URL]
    assert page.menu_clicks == 1


def test_ordinary_login_recovery_fills_confirmed_controls_once_then_verifies_shell() -> None:
    context = FakeContext(shell_pages=0)
    page = _LoginPage(context)
    browser = _login_browser(page)

    ensure_inso_authenticated(browser, _Login())

    assert page.clicks == 1
    assert page.values == {
        "username": "synthetic-user",
        "password": "synthetic-password",
    }
    assert page.gotos == [_LOGIN_URL]
    assert page.menu_clicks == 1
    assert page.main_frame.url == "https://yingsuo.alperp.cn/"
    assert page.renders_list is True


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


def test_live_inso_login_page_mobile_code_challenge_requires_human_handling() -> None:
    """Real INSO login page wording must fail closed to manual handling.

    Observed live on the real login page: the form renders 获取验证码 /
    发送至手机尾号：xxxxxxx 8217 and a required 手机验证码 field, and
    ``/services/sys/sys_login.ashx?action=Login`` answers with
    ``登录失败，请输入手机验证码！`` even for a correct username/password.
    The code is delivered to the Owner's phone, so this is a human-only
    challenge: the adapter must not attempt the login and must not treat the
    session as recoverable.
    """

    context = FakeContext(shell_pages=0)
    page = _LoginPage(
        context,
        body_text="英索实业 手机验证码 获取验证码 发送至手机尾号：xxxxxxx 8217 登录",
    )

    with pytest.raises(InsoAuthenticationError) as error:
        ensure_inso_authenticated(_login_browser(page), _Login())

    assert error.value.reason_code == "MANUAL_VERIFICATION_REQUIRED"
    assert page.clicks == 0


@pytest.mark.parametrize(
    "body_text",
    ("请输入验证码", "验证码已发送", "短信验证码", "动态口令", "安全验证"),
)
def test_demanded_verification_code_still_fails_closed(body_text) -> None:
    context = FakeContext(shell_pages=0)
    page = _LoginPage(context, body_text=body_text)

    with pytest.raises(InsoAuthenticationError) as error:
        ensure_inso_authenticated(_login_browser(page), _Login())

    assert error.value.reason_code == "MANUAL_VERIFICATION_REQUIRED"
    assert page.clicks == 0


# ---------------------------------------------------------------------------
# Proving the session, and getting it back.
#
# Owner finding (2026-10-01): the login died mid-run and every later ERP step
# failed as a missing control, so the operator saw 采购录单异常 and only found
# out by logging in by hand. Owner rule (2026-10-01): every INSO entry reopens
# the page and re-establishes the login. These tests pin what may count as
# proof of a live session, and that neither a leftover document nor a raw HTTP
# answer ever may.
# ---------------------------------------------------------------------------


class _MarkerPage:
    """A page reduced to exactly what the liveness proof reads."""

    def __init__(self, url, markers) -> None:
        self.main_frame = SimpleNamespace(url=url)
        self._markers = markers

    def evaluate(self, _script):
        return self._markers


class _LiveListPage(_LoginPage):
    """A page that is already the rendered ERP inquiry list."""

    def __init__(self, context) -> None:
        super().__init__(context)
        self.renders_list = True
        self.main_frame.url = _LIST_URL


_APP_MARKERS = {
    "grid": 1,
    "detail": 1,
    "select": 1,
    "stub": 0,
    "detailDrawn": 1,
    "selectDrawn": 1,
}
#: What a just-navigated page looks like before layui finishes: the controls are
#: in the DOM but have no box yet. Measured live 2026-10-01 -- this is the state
#: the first duplicate check of every GUI session used to run against.
_NOT_YET_DRAWN = {
    "grid": 1,
    "detail": 1,
    "select": 1,
    "stub": 0,
    "detailDrawn": 0,
    "selectDrawn": 0,
}
#: What the ERP really answers for a dead session: 200, at the list page's own
#: URL, with its ``.winbox`` "session ended" dialog in the body.
_EXPIRY_STUB = {
    "grid": 0,
    "detail": 0,
    "select": 0,
    "stub": 1,
    "detailDrawn": 0,
    "selectDrawn": 0,
}


def test_the_erp_s_own_controls_are_the_proof_of_a_live_list() -> None:
    assert _list_page_is_authenticated(_MarkerPage(_LIST_URL, _APP_MARKERS)) is True


def test_controls_present_but_not_drawn_are_not_yet_a_ready_list() -> None:
    """Measured live 2026-10-01: only the navigation-following check failed.

    The list page is entered with ``wait_until="domcontentloaded"``, which
    returns while layui is still building the toolbar. Every GUI session's
    *first* duplicate check -- the only one that follows a fresh navigation --
    died with ``FAILED_STAGE=QUERY_INPUT`` because ``#DetailFieldValue`` was
    present but had no box yet; later checks in the same session, reusing the
    settled page, passed. Presence alone must therefore not certify readiness.
    """

    assert (
        _list_page_is_authenticated(_MarkerPage(_LIST_URL, _NOT_YET_DRAWN)) is False
    )


def test_the_expiry_stub_on_the_list_url_is_never_accepted() -> None:
    """Measured live on 2026-10-01: a dead session answers 200 at List.aspx.

    The body is the ERP's 2.7 kB ``.winbox`` dialog, so status, path and the
    absence of a password field all agree -- and all lie. Only the ERP's own
    controls count, which is why the raw-request probe was removed.
    """

    assert _list_page_is_authenticated(_MarkerPage(_LIST_URL, _EXPIRY_STUB)) is False


@pytest.mark.parametrize(
    "url",
    (_CHECKING_URL, "https://yingsuo.alperp.cn/login.aspx?t=islogin"),
)
def test_a_login_or_transit_landing_is_never_a_live_list(url) -> None:
    assert _list_page_is_authenticated(_MarkerPage(url, _APP_MARKERS)) is False


@pytest.mark.parametrize(
    "page",
    [
        _MarkerPage("https://example.invalid/List.aspx", _APP_MARKERS),
        SimpleNamespace(main_frame=SimpleNamespace(url=_LIST_URL)),
    ],
)
def test_an_unreadable_or_foreign_page_proves_nothing(page) -> None:
    assert _list_page_is_authenticated(page) is False


class _SmsChallengedLoginPage(_LoginPage):
    """The state the ERP's own JS creates once a code is demanded."""

    def locator(self, selector):
        if selector == "#YZM":
            return _LoginControl(self, count=1)
        return super().locator(selector)


def _guard(page, *, reattach=None, **kwargs) -> InsoSessionGuard:
    context = page.context
    context.pages = [page]
    kwargs.setdefault("wait", lambda _delay: None)
    return InsoSessionGuard(
        login=_Login(),
        context=lambda: context,
        reattach=reattach,
        **kwargs,
    )


def test_the_page_already_on_the_list_is_reused_before_any_other() -> None:
    """The shell has to stay unique, so the list tab is the page to reopen.

    ``attach_inso_research_session`` refuses to lease unless exactly one page is
    the verified shell. Turning some *other* page into the list while a list tab
    is still open would create a second shell and abort the run; a leftover login
    tab is harmless by comparison, because it is not a shell.
    """

    context = FakeContext(shell_pages=0)
    login_page = _LoginPage(context)
    list_page = _LiveListPage(context)
    context.pages = [login_page, list_page]

    page, opened_here = _existing_or_new_login_page(context)

    assert page is list_page
    assert opened_here is False, "a tab that already existed is never ours"


def test_a_login_tab_is_used_when_no_list_tab_exists() -> None:
    context = FakeContext(shell_pages=0)
    login_page = _LoginPage(context)
    context.pages = [login_page]

    page, opened_here = _existing_or_new_login_page(context)

    assert page is login_page
    assert opened_here is False


def test_only_a_page_this_call_opened_is_reported_as_ours() -> None:
    context = FakeContext(shell_pages=0)
    context.pages = []

    page, opened_here = _existing_or_new_login_page(context)

    assert page in context.pages
    assert opened_here is True


def test_a_live_list_is_proven_without_logging_in() -> None:
    """The reopen is mandatory; the login is only what the reopen decides."""

    context = FakeContext(shell_pages=0)
    page = _LiveListPage(context)
    reattached: list[str] = []

    status = _guard(page, reattach=lambda: reattached.append(True)).ensure_authenticated()

    assert status.outcome is InsoSessionOutcome.RESTORED
    assert status.reauthenticated is True
    assert page.gotos == [_LOGIN_URL]
    assert page.menu_clicks == 1
    assert reattached == [True]


def test_a_run_entry_logs_in_without_proving_first() -> None:
    """Owner rule: a run entry re-establishes the login unconditionally.

    ``force_login`` skips the first proof, so the only navigation left is the
    one that has to confirm the login took.
    """

    context = FakeContext(shell_pages=0)
    page = _LoginPage(context)

    status = _guard(page).ensure_authenticated(force_login=True)

    assert status.outcome is InsoSessionOutcome.RESTORED
    assert page.clicks == 1
    assert page.gotos == [_LOGIN_URL]
    assert page.menu_clicks == 1


def test_native_business_menu_waits_for_its_home_plugin_and_never_gotos_list():
    context = FakeContext(shell_pages=0)
    page = _LoginPage(context)
    now = [0.0]
    evaluations = [0]
    original = page.evaluate

    def evaluate(script):
        if "fn?.BillTab" in script:
            evaluations[0] += 1
            return evaluations[0] >= 3
        return original(script)

    page.evaluate = evaluate
    status = _guard(page, wait=lambda delay: now.__setitem__(0, now[0] + delay),
                    clock=lambda: now[0]).ensure_authenticated()
    assert status.outcome is InsoSessionOutcome.RESTORED
    assert page.gotos == [_LOGIN_URL]
    assert page.menu_clicks == 1
    assert evaluations[0] >= 3
    assert now[0] >= 0.5


def test_native_menu_retries_once_only_when_first_click_created_no_frame():
    context = FakeContext(shell_pages=0)
    page = _LoginPage(context)
    now = [0.0]
    attempts = [0]
    original = page.locator

    def locator(selector):
        entry = original(selector)
        if selector == "a#iframe_YeWuXJ_menu":
            click = entry.click

            def click_once_ready(**kwargs):
                attempts[0] += 1
                if attempts[0] == 2:
                    click(**kwargs)

            entry.click = click_once_ready
        return entry

    page.locator = locator
    status = _guard(page, login_timeout_seconds=10,
                    wait=lambda delay: now.__setitem__(0, now[0] + delay),
                    clock=lambda: now[0]).ensure_authenticated()
    assert status.outcome is InsoSessionOutcome.RESTORED
    assert attempts == [2]
    assert now[0] >= 5
    assert page.gotos == [_LOGIN_URL]


def test_a_gone_session_is_logged_back_in_once_and_re_leased() -> None:
    context = FakeContext(shell_pages=0)
    page = _LoginPage(context)
    reattached: list[str] = []

    status = _guard(page, reattach=lambda: reattached.append(True)).ensure_authenticated()

    assert status.outcome is InsoSessionOutcome.RESTORED
    assert status.reauthenticated is True
    assert page.clicks == 1
    assert page.values == {
        "username": "synthetic-user",
        "password": "synthetic-password",
    }
    assert page.gotos == [_LOGIN_URL]
    assert page.menu_clicks == 1
    assert reattached == [True]


def test_the_guard_waits_out_the_erp_redirect_before_navigating() -> None:
    """Submitting is not the same as finishing.

    The form posts through the ERP's own script, which then navigates. The list
    navigation must not be issued while the page is still on the form: arriving
    before the new session exists gets the login page served again, which reads
    as a failed login for a login that had worked. Measured live on 2026-10-01 --
    that race made the guard call a restored session dead.
    """

    now = [0.0]
    context = FakeContext(shell_pages=0)
    page = _LoginPage(context)
    page.redirects_after_click = False
    goto = page.goto
    navigated_at: list[float] = []

    def _goto(url, wait_until=None, timeout=None):
        navigated_at.append(now[0])
        return goto(url, wait_until=wait_until, timeout=timeout)

    page.goto = _goto

    def delayed_redirect(delay):
        now[0] += delay
        if now[0] >= 1.0:
            page.main_frame.url = "https://yingsuo.alperp.cn/"

    status = _guard(
        page,
        login_timeout_seconds=5.0,
        wait=delayed_redirect,
        clock=lambda: now[0],
    ).ensure_authenticated()

    assert status.outcome is InsoSessionOutcome.RESTORED
    assert page.clicks == 1
    # The first navigation is the pre-login proof. The second is the one that
    # follows the submit, and it must not be issued until the form is left.
    assert navigated_at == [0.0]
    assert now[0] >= 1.0
    assert page.menu_clicks == 1


def test_a_session_that_never_comes_back_is_reported_dead() -> None:
    context = FakeContext(shell_pages=0)
    page = _LoginPage(context, authenticates=False)
    reattached: list[str] = []

    status = _guard(
        page,
        reattach=lambda: reattached.append(True),
        login_timeout_seconds=0,
    ).ensure_authenticated()

    assert status.outcome is InsoSessionOutcome.DEAD
    assert status.reason_code == "AUTHENTICATED_SHELL_UNAVAILABLE"
    assert page.clicks == 1
    assert reattached == []


def test_a_revealed_mobile_code_block_is_left_to_the_owner() -> None:
    context = FakeContext(shell_pages=0)
    page = _SmsChallengedLoginPage(context)
    reattached: list[str] = []

    status = _guard(
        page,
        reattach=lambda: reattached.append(True),
        login_timeout_seconds=0,
    ).ensure_authenticated()

    assert status.outcome is InsoSessionOutcome.DEAD
    assert status.reason_code == "MANUAL_VERIFICATION_REQUIRED"
    assert page.clicks == 0
    assert reattached == []


def test_a_shell_that_cannot_be_re_leased_after_login_is_dead() -> None:
    context = FakeContext(shell_pages=0)
    page = _LoginPage(context)

    def _refuse() -> None:
        raise SecurityViolation("lease")

    status = _guard(page, reattach=_refuse).ensure_authenticated()

    assert status.outcome is InsoSessionOutcome.DEAD
    assert status.reason_code == "SESSION_IDENTITY_UNVERIFIED"
