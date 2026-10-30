from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.core.site_retry import retryable_site_failure
from src.gui.contracts import RunState
from src.launcher.backend import ProductionBackend
from src.research.inso_history import InsoHistoryAdapter, InsoReadError
from src.research.source_contracts import (
    ResearchSource,
    SourceEvidence,
    SourceOutcome,
    SourceResult,
)
from src.workflow.v12_faults import FaultScope, V12Fault


def result(site, code='LOGIN_NOT_CONFIRMED', success=False):
    source = SimpleNamespace(outcome=SourceOutcome.SUCCESS if success else SourceOutcome.SOURCE_UNAVAILABLE,
        evidence=SimpleNamespace(fields=[SimpleNamespace(key='failure_code', value=code)]))
    return SimpleNamespace(source_result=source) if site is ResearchSource.IC_NET else source


@pytest.mark.parametrize('site', [ResearchSource.IC_NET, ResearchSource.FINDCHIPS,
    ResearchSource.HQEW, ResearchSource.LCSC, ResearchSource.BOM_AI])
@pytest.mark.parametrize('recover', [True, False])
def test_all_external_sites_retry_three_times_before_returning_failure(site, recover, monkeypatch):
    backend = ProductionBackend()
    calls, waits = [], []
    monkeypatch.setattr(backend._stop, 'wait', lambda delay: waits.append(delay) or False)
    def operation():
        calls.append(1)
        return result(site, success=recover and len(calls) == 4)
    final = backend._run_source_query('synthetic', site, operation, lambda: pytest.fail('no CDP repair'))
    source = final.source_result if site is ResearchSource.IC_NET else final
    assert source.outcome is (SourceOutcome.SUCCESS if recover else SourceOutcome.SOURCE_UNAVAILABLE)
    assert len(calls) == 4 and waits == [2, 5, 10]
    backend.shutdown()


@pytest.mark.parametrize('code', ['MANUAL_VERIFICATION_REQUIRED', 'CAPTCHA',
    'CREDENTIALS_UNAVAILABLE', 'LOGIN_REJECTED', 'INTERACTIVE_CHALLENGE_REQUIRED'])
def test_human_security_or_rejected_missing_credentials_are_not_repeated(code, monkeypatch):
    backend = ProductionBackend()
    monkeypatch.setattr(backend._stop, 'wait', lambda delay: pytest.fail('must not retry'))
    calls = []
    def operation():
        calls.append(1)
        return result(ResearchSource.LCSC, code)
    backend._run_source_query('synthetic', ResearchSource.LCSC, operation, lambda: None)
    assert len(calls) == 1 and not retryable_site_failure(code)
    backend.shutdown()


def test_stop_interrupts_retry_without_observing_or_notifying(monkeypatch):
    backend = ProductionBackend()
    monkeypatch.setattr(backend._stop, 'wait', lambda delay: True)
    with pytest.raises(V12Fault, match='STOP_REQUESTED'):
        backend._run_source_query('synthetic', ResearchSource.LCSC, lambda: result(ResearchSource.LCSC), lambda: None)
    backend.shutdown()


def test_inso_keeps_existing_query_retry_budget_not_nested_login_retry(monkeypatch):
    backend = ProductionBackend()
    monkeypatch.setattr(backend._stop, 'wait', lambda delay: pytest.fail('existing INSO wrapper owns retries'))
    assert backend._run_source_query('synthetic', ResearchSource.INSO,
        lambda: result(ResearchSource.INSO), lambda: None).outcome is SourceOutcome.SOURCE_UNAVAILABLE
    backend.shutdown()


@pytest.mark.parametrize('code', ['LOGIN_NOT_CONFIRMED', 'SOURCE_UNAVAILABLE'])
def test_inso_transient_login_failure_does_not_notify_before_query_retries(monkeypatch, code):
    backend = ProductionBackend()
    calls, notes, waits = [], [], []
    monkeypatch.setattr(backend._stop, 'wait', lambda seconds: waits.append(seconds) or False)
    monkeypatch.setattr(backend, '_close_inso_order_tab', lambda: None)
    monkeypatch.setattr(backend, '_begin_inso_inquiry', lambda iid: None)
    monkeypatch.setattr(backend, '_observe_source_failure', lambda *args: notes.append(args))
    def operation():
        calls.append(1)
        return result(ResearchSource.INSO, code, success=len(calls) == 4)
    assert backend._run_inso_query('synthetic', operation, lambda: None).outcome is SourceOutcome.SUCCESS
    assert len(calls) == 4 and waits == [120, 120, 120] and not notes
    backend.shutdown()


@pytest.mark.parametrize('site', tuple(ResearchSource))
def test_login_sweep_retries_same_owned_tab_then_reports_only_final_verdict(site):
    from src.gui.contracts import SiteLoginOutcome
    from src.launcher.site_login_sweep import SiteLoginSweep, SiteSignInStep
    from src.research.site_login import SiteLoginError
    pages, attempts, waits = [], [], []
    page = SimpleNamespace(close=lambda: None)
    def new_tab(*args, **kwargs):
        pages.append(page)
        return page
    sweep = SiteLoginSweep(SimpleNamespace(contexts=[object()]), timeout_ms=500,
        new_tab=new_tab, wait=lambda seconds: waits.append(seconds))
    def sign_in(tab):
        attempts.append(tab.page)
        if len(attempts) < 4:
            raise SiteLoginError('LOGIN_NOT_CONFIRMED')
        return False
    try:
        verdict, = sweep.run([SiteSignInStep(site.value, site.value, sign_in)])
        assert verdict.outcome is SiteLoginOutcome.SIGNED_IN
        assert len(pages) == 1 and attempts == [page]*4 and waits == [2, 5, 10]
    finally:
        sweep.close()


class InsoTestOutbox:
    """In-memory notification ledger; production observer and mail formatter stay real."""

    def __init__(self):
        self.commands = {}

    def notification_already_created(self, key, *args):
        return key in self.commands

    def enqueue_notification(self, command):
        self.commands[command.command_id] = command


def inso_failure(code):
    def fetch_history(mpn):
        raise InsoReadError(code)
    adapter = InsoHistoryAdapter(SimpleNamespace(fetch_history=fetch_history),
        SimpleNamespace(get_quote=lambda: pytest.fail('failure must not request FX')))
    return adapter.search('TEST-MPN', 1)


@pytest.mark.parametrize('code', ['LOGIN_REQUIRED', 'AUTHENTICATION_REQUIRED',
    'AUTHORIZATION_REQUIRED', 'AUTHENTICATED_SESSION_REQUIRED', 'AUTHENTICATED_SHELL_UNAVAILABLE',
    'CREDENTIALS_UNAVAILABLE', 'CREDENTIAL_NOT_CONFIGURED', 'CREDENTIAL_REJECTED', 'LOGIN_REJECTED',
    'MANUAL_VERIFICATION_REQUIRED', 'INTERACTIVE_CHALLENGE_REQUIRED', 'VERIFIED_SESSION_LEASE_REQUIRED',
    'SESSION_IDENTITY_UNVERIFIED', 'SESSION_STALE', 'SECURITY_EVENT', 'CAPTCHA_REQUIRED', 'OTP_REQUIRED'])
def test_inso_authorization_preserves_page_and_schedules_recovery_without_global_stop(code, monkeypatch):
    backend = ProductionBackend()
    backend._v12_store = outbox = InsoTestOutbox()
    calls = []
    monkeypatch.setattr(backend._stop, 'wait', lambda seconds: pytest.fail('unsafe auth retry'))
    monkeypatch.setattr(backend, '_close_inso_order_tab', lambda: pytest.fail('must retain auth page'))
    monkeypatch.setattr(backend, '_begin_inso_inquiry', lambda iid: pytest.fail('must not reopen auth page'))
    def operation():
        calls.append(1)
        return inso_failure(code)
    with pytest.raises(V12Fault, match='INSO_AUTHENTICATION_REQUIRED') as failure:
        backend._run_inso_query('synthetic', operation, lambda: pytest.fail('unsafe prepare retry'))
    assert calls == [1]
    assert failure.value.scope is FaultScope.GLOBAL_STOP
    assert backend._state is RunState.RUNNING and not backend._stop.is_set()
    assert backend._next_poll_at is not None and 'INSO' in backend._site_outages
    assert 'synthetic' in backend._manual_inquiries
    assert not outbox.commands  # No bound current business in this synthetic session sample.
    backend.shutdown()


@pytest.mark.parametrize('code', ['AUTHENTICATED_READ_UNAVAILABLE', 'AUTHENTICATED_READ_EMPTY',
    'RESPONSE_NOT_JSON', 'RESPONSE_ROWS_MISSING'])
@pytest.mark.parametrize('recover_at', [2, 4, None])
def test_inso_authenticated_reads_observe_only_after_retry_exhaustion(code, recover_at, monkeypatch):
    backend = ProductionBackend()
    backend._v12_store = outbox = InsoTestOutbox()
    calls, waits, resets, prepares = [], [], [], []
    def still_silent():
        assert not outbox.commands and not backend._manual_inquiries
    def wait(seconds):
        still_silent()
        waits.append(seconds)
        return False
    def reset():
        still_silent()
        resets.append(1)
    def prepare():
        still_silent()
        prepares.append(1)
    monkeypatch.setattr(backend._stop, 'wait', wait)
    monkeypatch.setattr(backend, '_close_inso_order_tab', reset)
    monkeypatch.setattr(backend, '_begin_inso_inquiry', lambda iid: None)
    def operation():
        still_silent()
        calls.append(1)
        if len(calls) == recover_at:
            evidence = SourceEvidence(ResearchSource.INSO, 'TEST-MPN', None,
                SourceOutcome.NO_VALID_PRICE, datetime.now(UTC))
            return SourceResult(ResearchSource.INSO, SourceOutcome.NO_VALID_PRICE, evidence)
        return inso_failure(code)
    if recover_at:
        final = backend._run_inso_query('synthetic', operation, prepare)
        backend._observe_source_failure('synthetic', final)
        assert final.outcome is SourceOutcome.NO_VALID_PRICE
        assert not outbox.commands and len(resets) == recover_at - 1
    else:
        with pytest.raises(V12Fault, match='INSO_QUERY_RETRIES_EXHAUSTED') as failure:
            backend._run_inso_query('synthetic', operation, prepare)
        assert failure.value.scope is FaultScope.GLOBAL_STOP
        assert not outbox.commands and len(resets) == 4  # A recoverable query is local-only.
    attempts = recover_at or 4
    assert len(calls) == attempts and waits == [120] * (attempts - 1)
    assert len(prepares) == attempts - 1 and not backend._manual_inquiries
    assert not backend._stop.is_set()
    backend.shutdown()


def test_inso_typed_auth_exception_is_not_swallowed_as_retryable_read(monkeypatch):
    from src.launcher.inso_session import InsoAuthenticationError

    backend = ProductionBackend()
    calls = []
    monkeypatch.setattr(backend._stop, 'wait', lambda seconds: pytest.fail('unsafe auth retry'))
    monkeypatch.setattr(backend, '_close_inso_order_tab', lambda: pytest.fail('must retain auth page'))
    def operation():
        calls.append(1)
        raise InsoAuthenticationError('AUTHENTICATION_REQUIRED')
    with pytest.raises(InsoAuthenticationError):
        backend._run_inso_query('synthetic', operation, lambda: None)
    assert calls == [1]
    backend.shutdown()


def test_inso_stop_during_read_retry_never_notifies_failure(monkeypatch):
    backend = ProductionBackend()
    backend._v12_store = outbox = InsoTestOutbox()
    calls, resets = [], []
    monkeypatch.setattr(backend._stop, 'wait', lambda seconds: True)
    monkeypatch.setattr(backend, '_close_inso_order_tab', lambda: resets.append(1))
    def operation():
        calls.append(1)
        return inso_failure('AUTHENTICATED_READ_UNAVAILABLE')
    with pytest.raises(V12Fault, match='STOP_REQUESTED'):
        backend._run_inso_query('synthetic', operation, lambda: None)
    assert calls == [1] and resets == [1] and not outbox.commands
    backend.shutdown()


STOP_CODES = ('LOGIN_REQUIRED', 'AUTHENTICATION_REQUIRED', 'AUTHENTICATED_SHELL_UNAVAILABLE',
    'CREDENTIALS_UNAVAILABLE', 'CREDENTIAL_REJECTED', 'MANUAL_VERIFICATION_REQUIRED',
    'UNRECOGNIZED_SITE_ERROR', 'SOURCE_UNAVAILABLE', '')


@pytest.mark.parametrize('code', [*STOP_CODES, None, 0, 'BROWSER_TIMEOUT_UNKNOWN',
    'HTTP_REQUEST_FAILED', 'LOGIN_NOT_READY', 'SESSION_IDENTITY_UNVERIFIED'])
def test_retry_policy_is_closed_for_auth_missing_and_unknown_codes(code):
    assert not retryable_site_failure(code)


@pytest.mark.parametrize('code', ['BROWSER_TIMEOUT', 'LOGIN_PAGE_UNAVAILABLE', 'LOGIN_NOT_CONFIRMED',
    'RESULT_NAVIGATION_FAILED', 'SEARCH_NAVIGATION_FAILED', 'PRODUCT_NAVIGATION_FAILED'])
def test_only_explicit_adapter_transient_codes_allow_retry(code):
    assert retryable_site_failure(code)


@pytest.mark.parametrize('site', [ResearchSource.IC_NET, ResearchSource.FINDCHIPS,
    ResearchSource.HQEW, ResearchSource.LCSC, ResearchSource.BOM_AI])
@pytest.mark.parametrize('code', STOP_CODES)
def test_every_research_site_stops_auth_and_unknown_without_repeat(site, code, monkeypatch):
    backend = ProductionBackend()
    calls = []
    monkeypatch.setattr(backend._stop, 'wait', lambda seconds: pytest.fail('unsafe retry wait'))
    def operation():
        calls.append(1)
        return result(site, code)
    backend._run_source_query('synthetic', site, operation, lambda: pytest.fail('unsafe reconnect'))
    assert calls == [1]
    backend.shutdown()


@pytest.mark.parametrize('site', [ResearchSource.IC_NET, ResearchSource.FINDCHIPS,
    ResearchSource.HQEW, ResearchSource.LCSC, ResearchSource.BOM_AI])
def test_unknown_no_code_source_exception_never_repeats(site, monkeypatch):
    backend = ProductionBackend()
    calls = []
    monkeypatch.setattr(backend._stop, 'wait', lambda seconds: pytest.fail('unsafe retry wait'))
    def operation():
        calls.append(1)
        raise RuntimeError('synthetic unclassified failure')
    with pytest.raises(RuntimeError):
        backend._run_source_query('synthetic', site, operation, lambda: pytest.fail('unsafe reconnect'))
    assert calls == [1]
    backend.shutdown()


@pytest.mark.parametrize('site', tuple(ResearchSource))
@pytest.mark.parametrize('code', (*STOP_CODES[:-1], None))
def test_every_login_sweep_step_including_inso_stops_auth_and_unknown(site, code):
    from src.launcher.site_login_sweep import SiteLoginSweep, SiteSignInStep
    from src.research.site_login import SiteLoginError
    calls, waits = [], []
    page = SimpleNamespace(close=lambda: None)
    sweep = SiteLoginSweep(SimpleNamespace(contexts=[object()]), timeout_ms=500,
        new_tab=lambda *a, **kw: page, wait=lambda seconds: waits.append(seconds), present_failures=False)
    def sign_in(tab):
        calls.append(1)
        if code is None:
            raise RuntimeError('synthetic unclassified failure')
        raise SiteLoginError(code)
    try:
        verdict, = sweep.run([SiteSignInStep(site.value, site.value, sign_in)])
        assert calls == [1] and not waits and verdict.site == site.value
    finally:
        sweep.close()

@pytest.mark.parametrize('wrapped', [False, True])
def test_shared_page_uncertainty_is_not_source_retry_or_success(wrapped):
    from src.research.cdp_pages import (
        PageTargetCreationUncertain,
        bind_page_admission,
    )
    backend = ProductionBackend()
    calls = []
    browser = SimpleNamespace()
    bind_page_admission(browser, backend._page_admission)
    def operation():
        calls.append('source')
        fault = PageTargetCreationUncertain((OSError('synthetic uncertain response'),))
        backend._page_admission.invalidate(fault)
        if wrapped:
            return result(ResearchSource.LCSC, code='SOURCE_UNAVAILABLE')
        raise RuntimeError('adapter wrapped cause') from fault
    try:
        with pytest.raises(PageTargetCreationUncertain):
            backend._run_source_query('synthetic', ResearchSource.LCSC, operation,
                lambda: pytest.fail('uncertain resource must not reconnect'))
        with pytest.raises(PageTargetCreationUncertain):
            backend._run_source_query('synthetic', ResearchSource.LCSC,
                lambda: pytest.fail('must not admit another source'), lambda: None)
        assert calls == ['source']
    finally:
        backend.shutdown()


def test_uncertain_resource_teardown_detaches_only_never_sweeps_pages(monkeypatch):
    from src.launcher.browser_bootstrap import BrowserHandle, park_shared_cdp
    from src.research.cdp_pages import PageTargetCreationUncertain, bind_page_admission
    backend = ProductionBackend()
    calls = []
    browser = SimpleNamespace()
    handle = BrowserHandle(owned=False, browser=browser,
        playwright=SimpleNamespace(stop=lambda: calls.append('disconnect')))
    backend._browser_handle = handle
    backend._inso_session = SimpleNamespace(close_after_drain=lambda: pytest.fail('uncertain page sweep'))
    bind_page_admission(browser, backend._page_admission)
    backend._page_admission.invalidate(PageTargetCreationUncertain((OSError('synthetic response lost'),)))
    try:
        with pytest.raises(PageTargetCreationUncertain):
            backend._close_inso_order_tab()
        with pytest.raises(PageTargetCreationUncertain):
            park_shared_cdp(browser)  # Even a direct legacy cleanup caller is refused.
        backend._release_idle_browser(force=True)
        assert calls == ['disconnect']
        assert backend._browser_handle is None
    finally:
        backend.shutdown()
