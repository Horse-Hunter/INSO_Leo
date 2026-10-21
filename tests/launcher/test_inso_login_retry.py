"""INSO authentication recovery only; no CDP, credential access or business writes."""
import pytest
from playwright.sync_api import Error as PageError
from playwright.sync_api import TimeoutError as PageTimeout

from src.launcher.inso_session import InsoSessionGuard, InsoSessionOutcome
from tests.launcher.test_inso_session import FakeContext, _guard, _Login, _LoginPage


def test_transient_login_navigation_reuses_page_and_only_leases_after_success():
    page = _LoginPage(FakeContext(shell_pages=0))
    original = page.goto
    calls, waits, leased = [], [], []

    def goto(*args, **kwargs):
        calls.append(1)
        if len(calls) < 3:
            page.main_frame.url = 'https://yingsuo.alperp.cn/login.aspx?t=islogin'
            page.url = page.main_frame.url  # Playwright exposes the partial landing as page.url too.
            raise PageTimeout('synthetic navigation timeout')
        return original(*args, **kwargs)

    page.goto = goto
    guard = _guard(page, wait=waits.append, reattach=lambda: leased.append(1))
    status = guard.ensure_authenticated()
    assert status.outcome is InsoSessionOutcome.RESTORED
    assert [delay for delay in waits if delay >= 2] == [2, 4] and calls == [1, 1, 1]
    assert page.clicks == 1 and leased == [1]
    assert guard.authenticated_page is page and guard.opened_page is None


@pytest.mark.parametrize('error, attempts, reason', [
    (PageTimeout('synthetic timeout'), 5, 'BROWSER_TIMEOUT'),
    (PageError('net::ERR_CONNECTION_RESET'), 5, 'LOGIN_PAGE_UNAVAILABLE'),
    (PageError('net::ERR_CERT_AUTHORITY_INVALID'), 1, 'AUTHENTICATION_REQUIRED'),
    (RuntimeError('synthetic unknown control'), 1, 'AUTHENTICATION_REQUIRED'),
])
def test_login_retry_bound_does_not_include_unknown_or_security_errors(error, attempts, reason):
    page = _LoginPage(FakeContext(shell_pages=0))
    calls, waits = [], []

    def goto(*args, **kwargs):
        calls.append(1)
        raise error

    page.goto = goto
    guard = _guard(page, wait=waits.append,
                   reattach=lambda: pytest.fail('failed login cannot lease business page'))
    status = guard.ensure_authenticated()
    assert status.outcome is InsoSessionOutcome.DEAD and status.reason_code == reason
    assert len(calls) == attempts and page.clicks == 0
    assert waits == ([2, 4, 6, 8] if attempts == 5 else [])


def test_native_shell_readiness_is_retried_before_declaring_auth_failure(monkeypatch):
    page = _LoginPage(FakeContext(shell_pages=0))
    waits, leased, proofs = [], [], []
    guard = _guard(page, wait=waits.append, reattach=lambda: leased.append(1))

    def prove(_page):
        proofs.append(1)
        return len(proofs) == 3

    monkeypatch.setattr(guard, '_prove', prove)
    status = guard.ensure_authenticated()
    assert status.outcome is InsoSessionOutcome.RESTORED
    assert waits == [2, 4] and len(proofs) == 3 and leased == [1]


@pytest.mark.parametrize('message, reason', [
    ('密码错误', 'CREDENTIAL_REJECTED'),
    ('验证码', 'MANUAL_VERIFICATION_REQUIRED'),
])
def test_challenge_or_rejection_after_first_timeout_stops_without_another_login(message, reason):
    page = _LoginPage(FakeContext(shell_pages=0))
    original = page.goto
    calls, waits = [], []

    def goto(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise PageTimeout('synthetic loading delay')
        page.body_text = message
        return original(*args, **kwargs)

    page.goto = goto
    status = _guard(page, wait=waits.append).ensure_authenticated()
    assert status.outcome is InsoSessionOutcome.DEAD and status.reason_code == reason
    assert waits == [2] and page.clicks == 0


def test_retries_keep_the_single_owned_fresh_login_tab(monkeypatch):
    context = FakeContext(shell_pages=0)
    opened, waits = [], []

    def new_page():
        page = _LoginPage(context)
        context.pages.append(page)
        opened.append(page)
        original = page.goto
        calls = []

        def goto(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                raise PageTimeout('synthetic loading delay')
            return original(*args, **kwargs)

        page.goto = goto
        return page

    monkeypatch.setattr(context, 'new_page', new_page)
    guard = InsoSessionGuard(login=_Login(), context=lambda: context,
                             fresh_page=True, wait=waits.append)
    assert guard.ensure_authenticated().outcome is InsoSessionOutcome.RESTORED
    assert len(opened) == 1 and guard.opened_page is opened[0]
    assert [delay for delay in waits if delay >= 2] == [2]
