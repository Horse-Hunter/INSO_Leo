"""Real scheduler + virtual clock; no website, credentials, SMTP or business replay."""
import json
import sqlite3
from datetime import timedelta
from threading import Event
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState
from src.launcher import backend as launcher
from src.launcher.backend import ProductionBackend, _website_failure
from src.workflow.v12_faults import FaultScope, V12Fault
from tests.launcher.test_backend import (
    _RecordingTransport,
    _SheetsService,
    _write_runtime_configs,
)


@pytest.mark.parametrize('reason,site', [
    ('INSO_QUERY_RETRIES_EXHAUSTED', 'INSO'),
    ('INSO_AUTHENTICATION_REQUIRED', 'INSO'),
    ('GOOGLE_SPREADSHEET_UNAVAILABLE', 'Google Sheets'),
    ('GOOGLE_AUTHENTICATION_REQUIRED', 'Google Sheets'),
    ('V13_FX_UNAVAILABLE', '汇率网站'),
    ('IC_NET_UNAVAILABLE', 'IC.net'),
])
def test_only_continuous_three_hour_same_site_outage_can_globally_stop(tmp_path, monkeypatch, reason, site):
    now = [100.0]
    monkeypatch.setattr(launcher, 'monotonic', lambda: now[0])
    backend = ProductionBackend(root=tmp_path)
    backend._state = RunState.RUNNING
    failure = V12Fault(FaultScope.GLOBAL_STOP, reason)
    assert backend._defer_website_poll(failure, timedelta(minutes=15), notify=False)
    now[0] += 10799
    assert backend._defer_website_poll(failure, timedelta(minutes=15), notify=False)
    assert backend._state is RunState.RUNNING and not backend._stop.is_set()
    assert backend._next_poll_at is not None
    now[0] += 1
    assert not backend._defer_website_poll(failure, timedelta(minutes=15), notify=False)
    monkeypatch.setattr(backend, '_alert_owner_of_login', lambda **kw: None)
    backend._runtime_error(failure)
    assert backend._state is RunState.GLOBAL_STOP and backend._stop.is_set()
    assert backend._site_outages[site] == 100
    backend.shutdown()


def test_success_resets_own_site_clock_and_other_sites_do_not_erase_it(tmp_path, monkeypatch):
    now = [0.0]
    monkeypatch.setattr(launcher, 'monotonic', lambda: now[0])
    backend = ProductionBackend(root=tmp_path)
    failures = {'INSO': V12Fault(FaultScope.GLOBAL_STOP, 'INSO_QUERY_RETRIES_EXHAUSTED'),
                'Google Sheets': V12Fault(FaultScope.GLOBAL_STOP, 'GOOGLE_SPREADSHEET_UNAVAILABLE')}
    for failure in failures.values():
        assert backend._defer_website_poll(failure, timedelta(minutes=15), notify=False)
    now[0] = 10799
    backend._site_recovered('INSO')
    assert 'INSO' not in backend._site_outages and backend._site_outages['Google Sheets'] == 0
    now[0] = 10801
    assert backend._defer_website_poll(failures['INSO'], timedelta(minutes=15), notify=False)
    assert backend._site_outages['INSO'] == 10801
    assert not backend._defer_website_poll(failures['Google Sheets'], timedelta(minutes=15), notify=False)
    backend.shutdown()


@pytest.mark.parametrize('reason', ['INSO_QUERY_RETRIES_EXHAUSTED', 'INSO_AUTHENTICATION_REQUIRED',
                                  'GOOGLE_SPREADSHEET_UNAVAILABLE', 'GOOGLE_AUTHENTICATION_REQUIRED',
                                  'CDP_RECONNECT_EXHAUSTED', 'V13_FX_UNAVAILABLE'])
def test_actual_poll_thread_survives_site_fault_and_reaches_next_poll(tmp_path, monkeypatch, reason):
    production, config, rows = _write_runtime_configs(tmp_path)
    settings = json.loads(production.read_text(encoding='utf-8'))
    settings.update(v13_enabled=True, quotation_input={'gid': '0', 'input_row': 1, 'first_column': 1})
    production.write_text(json.dumps(settings), encoding='utf-8')
    _RecordingTransport.sent.clear()
    monkeypatch.setattr(launcher, 'QQSMTPTransport', _RecordingTransport)
    monkeypatch.setattr('src.launcher.v12_composition.QQSMTPTransport', _RecordingTransport)
    monkeypatch.setattr(launcher, 'build_google_web_service', lambda *a, **kw: _SheetsService(rows, Event()))
    monkeypatch.setattr(launcher, 'assess_readiness', lambda *a, **kw: SimpleNamespace(ready=True, missing_site_ids=()))
    monkeypatch.setattr(launcher, 'build_research_service', lambda *a, **kw: SimpleNamespace(execute=lambda _: None))
    backend = ProductionBackend(root=tmp_path, config_path=config, production_config_path=production)
    refresh = backend._refresh_dashboard_counts
    polls, waits = [], []
    def poll(*a, **kw):
        polls.append(True)
        if len(polls) == 1:
            raise V12Fault(FaultScope.GLOBAL_STOP, reason)
        return refresh(*a, **kw)
    def wait(seconds):
        waits.append(seconds)
        assert backend._state is RunState.RUNNING and not backend._stop.is_set()
        assert backend._next_poll_at is not None
        backend._v12_composition.coordinator.run_notifications(now=launcher.utc_now())
        if len(waits) == 1:
            return False
        backend._stop.set()
        return True
    monkeypatch.setattr(backend, '_refresh_dashboard_counts', poll)
    monkeypatch.setattr(backend, '_wait_between_polls', wait)
    try:
        backend.start()
        backend._thread.join(10)
        assert not backend._thread.is_alive() and len(polls) == 2 and waits == [900, 900]
        assert len(_RecordingTransport.sent) == 1
        assert '已停止' not in _RecordingTransport.sent[0][2]
        assert '等待恢复' in _RecordingTransport.sent[0][2]
        assert backend._store.all_items() == ()
    finally:
        backend.shutdown()


@pytest.mark.parametrize('reason', ['GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED', 'GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED',
                                  'SHEETS_SCHEMA_UNAVAILABLE', 'WORKFLOW_LEDGER_UNAVAILABLE'])
def test_unknown_write_or_local_data_failure_is_not_a_site_retry(tmp_path, monkeypatch, reason):
    backend = ProductionBackend(root=tmp_path)
    failure = V12Fault(FaultScope.GLOBAL_STOP, reason)
    assert not backend._defer_website_poll(failure, timedelta(minutes=15), notify=False)
    monkeypatch.setattr(backend, '_alert_owner_of_login', lambda **kw: None)
    backend._runtime_error(failure)
    assert backend._state is RunState.MODULE_PAUSED and backend._stop.is_set()
    assert not backend._site_outages
    backend.shutdown()


def test_database_cause_cannot_be_mislabeled_as_site_outage():
    failure = V12Fault(FaultScope.GLOBAL_STOP, 'SHEETS_READ_UNAVAILABLE')
    failure.__cause__ = sqlite3.DatabaseError('synthetic local failure')
    assert _website_failure(failure) is None


def test_human_inso_challenge_only_probes_without_credential_or_business_retry(tmp_path, monkeypatch):
    backend = ProductionBackend(root=tmp_path)
    monkeypatch.setattr(backend, '_alert_owner_of_login', lambda **kw: None)
    backend._manual_review('synthetic', 'INSO：MANUAL_VERIFICATION_REQUIRED')
    assert backend._state is RunState.RUNNING and not backend._stop.is_set()
    assert 'INSO' in backend._site_manual_wait
    probes = []
    def available(browser):
        probes.append(browser)
        return len(probes) == 2
    monkeypatch.setattr('src.launcher.inso_session.authenticated_inso_shell_available', available)
    with pytest.raises(launcher.InsoAuthenticationError, match='MANUAL_VERIFICATION_REQUIRED'):
        backend._check_site_recovery()
    assert backend._defer_website_poll(launcher.InsoAuthenticationError('MANUAL_VERIFICATION_REQUIRED'),
                                       timedelta(minutes=15), notify=False)
    backend._check_site_recovery()
    assert 'INSO' not in backend._site_manual_wait and 'INSO' in backend._site_outages
    backend._site_recovered('INSO')  # Only a proven business read clears the outage timer.
    assert not backend._site_outages
    backend.shutdown()


@pytest.mark.parametrize('url', [None, 'https://docs.google.com/spreadsheets/example',
    'https://yingsuo.alperp.cn/login.aspx', 'https://yingsuo.alperp.cn/home.aspx',
    'https://yingsuo.alperp.cn/InnerEnquiry/YeWuXJ/List.aspx'])
def test_missing_inso_page_releases_only_manual_gate_not_outage(tmp_path, url):
    backend = ProductionBackend(root=tmp_path)
    context = SimpleNamespace(pages=[])
    if url is not None:
        context.pages.append(SimpleNamespace(is_closed=lambda: False, context=context,
            main_frame=SimpleNamespace(url=url), frames=[]))
    backend._browser_handle = SimpleNamespace(browser=SimpleNamespace(
        is_connected=lambda: True, contexts=[context]))
    backend._site_manual_wait.add('INSO')
    backend._site_outages.update(INSO=123.0, **{'Google Sheets': 456.0})
    backend._state = RunState.QUOTATION_RUNNING
    backend._combined = SimpleNamespace(v12_paused=True)
    try:
        if url is not None and 'yingsuo.alperp.cn' in url:
            with pytest.raises(launcher.InsoAuthenticationError, match='MANUAL_VERIFICATION_REQUIRED'):
                backend._check_site_recovery()
            assert 'INSO' in backend._site_manual_wait
            assert backend._combined.v12_paused
        else:
            backend._check_site_recovery()
            assert 'INSO' not in backend._site_manual_wait
            assert not backend._combined.v12_paused
            assert backend._state is RunState.RUNNING
        assert backend._site_outages == {'INSO': 123.0, 'Google Sheets': 456.0}
        assert not backend._stop.is_set()
    finally:
        backend._browser_handle = None  # Synthetic handle has no business/cleanup capability.
        backend._combined = None
        backend.shutdown()


def test_page_absence_requires_readable_connected_single_context():
    from src.launcher.inso_session import inso_session_page_absent

    context = SimpleNamespace(pages=[])
    assert inso_session_page_absent(SimpleNamespace(is_connected=lambda: True, contexts=[context]))
    assert not inso_session_page_absent(None)
    assert not inso_session_page_absent(SimpleNamespace(is_connected=lambda: False, contexts=[context]))
    assert not inso_session_page_absent(SimpleNamespace(is_connected=lambda: True, contexts=[]))
    assert not inso_session_page_absent(SimpleNamespace(is_connected=lambda: True, contexts=[context, context]))
    context.pages = [SimpleNamespace(is_closed=lambda: False)]  # Unreadable URL is not absence.
    assert not inso_session_page_absent(SimpleNamespace(is_connected=lambda: True, contexts=[context]))
    context.pages = [SimpleNamespace(is_closed=lambda: True)]
    assert inso_session_page_absent(SimpleNamespace(is_connected=lambda: True, contexts=[context]))



@pytest.mark.parametrize('reason', ['INSO_QUERY_RETRIES_EXHAUSTED', 'GOOGLE_SPREADSHEET_UNAVAILABLE'])
def test_actual_poller_observes_twelve_waits_before_three_hour_global_stop(tmp_path, monkeypatch, reason):
    production, config, rows = _write_runtime_configs(tmp_path)
    cfg = json.loads(production.read_text(encoding='utf-8'))
    cfg.update(v13_enabled=True, quotation_input={'gid': '0', 'input_row': 1, 'first_column': 1})
    production.write_text(json.dumps(cfg), encoding='utf-8')
    _RecordingTransport.sent.clear()
    monkeypatch.setattr(launcher, 'QQSMTPTransport', _RecordingTransport)
    monkeypatch.setattr('src.launcher.v12_composition.QQSMTPTransport', _RecordingTransport)
    monkeypatch.setattr(launcher, 'build_google_web_service', lambda *a, **kw: _SheetsService(rows, Event()))
    monkeypatch.setattr(launcher, 'assess_readiness', lambda *a, **kw: SimpleNamespace(ready=True, missing_site_ids=()))
    monkeypatch.setattr(launcher, 'build_research_service', lambda *a, **kw: SimpleNamespace(execute=lambda _: None))
    now, polls, waits = [0.0], [], []
    monkeypatch.setattr(launcher, 'monotonic', lambda: now[0])
    backend = ProductionBackend(root=tmp_path, config_path=config, production_config_path=production)
    def fail(*a, **kw):
        polls.append(now[0])
        raise V12Fault(FaultScope.GLOBAL_STOP, reason)
    def wait(seconds):
        assert not backend._stop.is_set() and backend._state is RunState.RUNNING
        waits.append(seconds)
        now[0] += seconds
        return False
    monkeypatch.setattr(backend, '_refresh_dashboard_counts', fail)
    monkeypatch.setattr(backend, '_wait_between_polls', wait)
    try:
        backend.start()
        backend._thread.join(10)
        assert not backend._thread.is_alive()
        assert polls == [900 * i for i in range(13)] and waits == [900] * 12
        assert backend._state is RunState.GLOBAL_STOP and backend._stop.is_set()
        assert len(_RecordingTransport.sent) == 2
        assert sum('连续三小时' in mail[2] for mail in _RecordingTransport.sent) == 1
        assert backend._store.all_items() == ()
    finally:
        backend.shutdown()


def test_prepared_duplicate_auth_failure_never_resets_human_page_or_consumes_read_retries():
    from src.launcher.backend import _PreparedDuplicateChecker
    from src.launcher.inso_session import InsoAuthenticationError
    calls = []
    def check(*args, **kw):
        calls.append(True)
        raise InsoAuthenticationError('MANUAL_VERIFICATION_REQUIRED')
    checker = _PreparedDuplicateChecker(SimpleNamespace(check=check),
        wait=lambda _: pytest.fail('human verification must not be retried'),
        reset=lambda: pytest.fail('human page must remain open'))
    with pytest.raises(InsoAuthenticationError):
        checker.check('synthetic', 'TEST', 1, at=launcher.utc_now())
    assert calls == [True]


def test_human_recovery_probe_does_not_trust_an_old_shell_while_a_login_challenge_remains(monkeypatch):
    from src.launcher import inso_session
    context = SimpleNamespace(pages=[])
    shell = SimpleNamespace(is_closed=lambda: False)
    login = SimpleNamespace(is_closed=lambda: False)
    context.pages[:] = [shell, login]
    browser = SimpleNamespace(is_connected=lambda: True, contexts=[context])
    monkeypatch.setattr(inso_session, '_is_inso_origin_page', lambda p: True)
    monkeypatch.setattr(inso_session, '_is_login_page', lambda p: p is login)
    monkeypatch.setattr(inso_session, '_human_verification_required', lambda p: False)
    monkeypatch.setattr(inso_session, '_verified_shell_frame', lambda p, c: object() if p is shell else None)
    assert not inso_session.authenticated_inso_shell_available(browser)
    context.pages.remove(login)
    assert inso_session.authenticated_inso_shell_available(browser)



def test_inso_query_success_clears_only_inso_when_fx_site_fails_after_the_read():
    from src.research.ecb_fx import EcbFxError
    from tests.inso.test_v13_quotation_read import NOW, priced
    from tests.workflow.test_v13_quotation import WS, cycle
    def missing_rate():
        raise EcbFxError('synthetic FX unavailable')
    service, _, _, _ = cycle([(priced(NOW, '1', 'USD'),)], fx=SimpleNamespace(get_quote=missing_rate))
    successes = []
    service._on_query_success = lambda: successes.append('INSO')
    service._on_fx_success = lambda: successes.append('FX')
    with pytest.raises(V12Fault, match='V13_FX_UNAVAILABLE'):
        service.run(WS)
    assert successes == ['INSO']



def test_human_page_survives_poll_cleanup_and_idle_release_while_scheduler_keeps_running(tmp_path, monkeypatch):
    backend = ProductionBackend(root=tmp_path)
    backend._state = RunState.RUNNING
    backend._site_outages['INSO'] = 1
    backend._site_manual_wait.add('INSO')
    calls = []
    backend._inso_session = SimpleNamespace(close_owned_operation_tab=lambda: pytest.fail('human page closed'))
    backend._browser_handle = SimpleNamespace(browser=object(), disconnect=lambda: calls.append('disconnect'))
    monkeypatch.setattr(backend, '_park_browser', lambda b: pytest.fail('human page parked/closed'))
    backend._close_inso_order_tab()
    backend._release_idle_browser(force=True)
    assert calls == ['disconnect'] and not backend._stop.is_set()
    assert backend._state is RunState.RUNNING and 'INSO' in backend._site_manual_wait
    backend.shutdown()
