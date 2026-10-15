from types import SimpleNamespace

import pytest

from src.core.site_retry import retryable_site_failure
from src.launcher.backend import ProductionBackend
from src.research.source_contracts import ResearchSource, SourceOutcome
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


@pytest.mark.parametrize('code', ['LOGIN_REQUIRED', 'AUTHENTICATION_REQUIRED', 'AUTHENTICATED_SHELL_UNAVAILABLE'])
def test_inso_authorization_still_stops_before_reset_or_retry(code, monkeypatch):
    backend = ProductionBackend()
    calls = []
    monkeypatch.setattr(backend._stop, 'wait', lambda seconds: pytest.fail('unsafe auth retry'))
    monkeypatch.setattr(backend, '_close_inso_order_tab', lambda: pytest.fail('must retain auth page'))
    def stop(iid, source):
        raise V12Fault(FaultScope.GLOBAL_STOP, 'INSO_AUTHENTICATION_REQUIRED')
    monkeypatch.setattr(backend, '_observe_source_failure', stop)
    def operation():
        calls.append(1)
        return result(ResearchSource.INSO, code)
    with pytest.raises(V12Fault, match='INSO_AUTHENTICATION_REQUIRED'):
        backend._run_inso_query('synthetic', operation, lambda: None)
    assert calls == [1]
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
