"""Offline automatic maintenance; no credentials, SMTP or browser access."""
from datetime import timedelta
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState, SiteLoginOutcome, SiteLoginResult
from src.launcher import backend as launcher
from src.launcher.site_login_sweep import SiteLoginSweep, SiteSignInStep
from tests.launcher.test_backend import _sweep_backend
from tests.launcher.test_site_login_sweep import _Browser, _Page
from tests.workflow.test_v12_flow import NOW, _make_flow

_GOOD_RESULTS = (SiteLoginResult("GOOD", SiteLoginOutcome.ALREADY_SIGNED_IN),)


def configured(tmp_path, monkeypatch, results=_GOOD_RESULTS):
    backend = launcher.ProductionBackend(root=tmp_path)
    backend._state = RunState.RUNNING
    backend._v13_enabled = True
    backend._run_id = "synthetic-run"
    backend._cycle_id = "synthetic-cycle"
    backend._idle_login_since = NOW
    backend._v12_composition = SimpleNamespace(coordinator=SimpleNamespace(pending_rows_seen=0))
    backend._combined = SimpleNamespace(v12_paused=False)
    _flow, _, store, *_ = _make_flow(tmp_path)
    from src.workflow.v13_integration import V13HoldStore
    V13HoldStore(store.database_path).migrate()
    backend._v12_store = store
    calls = []
    monkeypatch.setattr(launcher, "utc_now", lambda: NOW + timedelta(minutes=30))
    backend._run_login_sweep = lambda **kw: calls.append(kw) or results
    return backend, calls, store


def test_two_empty_polls_require_real_half_hour_and_no_popup(tmp_path, monkeypatch):
    backend, calls, store = configured(tmp_path, monkeypatch)
    popups = []
    backend.on_login_all(popups.append)
    for minutes in (0, 15, 29):
        backend._idle_login_tick(now=NOW + timedelta(minutes=minutes))
        assert not calls
    backend._idle_login_tick(now=NOW + timedelta(minutes=30))
    assert calls == [{"background": True}]
    assert backend.get_login_all_report() is None and not popups
    backend._idle_login_tick(now=NOW + timedelta(minutes=45))
    assert len(calls) == 1
    backend._idle_login_tick(now=NOW + timedelta(minutes=60))
    assert len(calls) == 2 and backend._state is RunState.RUNNING
    assert not store.claim_due_notifications(now=NOW + timedelta(minutes=61))


def test_pending_row_resets_idle_even_if_invalid_or_preexisting(tmp_path, monkeypatch):
    backend, calls, _ = configured(tmp_path, monkeypatch)
    backend._idle_login_tick(now=NOW + timedelta(minutes=15))
    backend._v12_composition.coordinator.pending_rows_seen = 1
    backend._idle_login_tick(now=NOW + timedelta(minutes=30))
    backend._v12_composition.coordinator.pending_rows_seen = 0
    backend._idle_login_tick(now=NOW + timedelta(minutes=45))
    assert not calls
    backend._idle_login_tick(now=NOW + timedelta(minutes=60))
    assert len(calls) == 1


@pytest.mark.parametrize("state,paused,stop", [
    (RunState.QUOTATION_RUNNING, True, False), (RunState.MANUAL_REVIEW, False, False),
    (RunState.GLOBAL_STOP, False, False), (RunState.STOPPING_AFTER_CYCLE, False, False),
    (RunState.RUNNING, False, True),
])
def test_pause_stop_and_manual_conditions_do_not_sweep(tmp_path, monkeypatch, state, paused, stop):
    backend, calls, _ = configured(tmp_path, monkeypatch)
    backend._state = state
    backend._combined.v12_paused = paused
    if stop:
        backend._stop.set()
    for minutes in (15, 30, 45):
        backend._idle_login_tick(now=NOW + timedelta(minutes=minutes))
    assert not calls and backend._state is state


def test_failure_durable_owner_only_alert_without_business_hold_or_popup(tmp_path, monkeypatch):
    backend, calls, store = configured(tmp_path, monkeypatch, (
        SiteLoginResult("TEST_SITE", SiteLoginOutcome.NEEDS_HUMAN, "secret raw detail"),
        SiteLoginResult("GOOD_SITE", SiteLoginOutcome.SIGNED_IN),
    ))
    backend._idle_login_tick(now=NOW + timedelta(minutes=15))
    backend._idle_login_tick(now=NOW + timedelta(minutes=30))
    commands = store.claim_due_notifications(now=NOW + timedelta(minutes=31))
    assert len(commands) == 1
    command = commands[0]
    assert command.inquiry_id is None
    assert [r.address for r in command.recipients] == ["linan229@qq.com"]
    assert "TEST_SITE" in command.text_body and "secret" not in command.text_body
    assert backend._state is RunState.RUNNING and not backend._stop.is_set()
    assert backend.get_login_all_report() is None and len(calls) == 1


@pytest.mark.parametrize("outbox_failure", [False, True])
def test_sweep_and_notification_exceptions_are_not_workflow_faults(tmp_path, monkeypatch, outbox_failure):
    backend, _, store = configured(tmp_path, monkeypatch)
    def failed(**kw):
        raise RuntimeError("secret provider error")
    backend._run_login_sweep = failed
    if outbox_failure:
        store.enqueue_notification = lambda command: (_ for _ in ()).throw(RuntimeError("secret db"))
    backend._idle_login_tick(now=NOW + timedelta(minutes=15))
    backend._idle_login_tick(now=NOW + timedelta(minutes=30))
    assert backend._state is RunState.RUNNING and not backend._stop.is_set()
    assert all("secret" not in log.message for log in backend.get_logs())


@pytest.mark.parametrize("failure,existing_nonblank", [(False, False), (True, False), (False, True)])
def test_background_reuses_canonical_sweep_safe_cleanup_and_disconnect(tmp_path, monkeypatch, failure, existing_nonblank):
    results = [SiteLoginResult("TEST", SiteLoginOutcome.NEEDS_HUMAN if failure else SiteLoginOutcome.SIGNED_IN)]
    backend, handle = _sweep_backend(tmp_path, monkeypatch, results)
    page = SimpleNamespace(url="https://manual/" if existing_nonblank else "about:blank", is_closed=lambda: False)
    handle.browser.contexts = [SimpleNamespace(pages=[page])]
    observed = []
    monkeypatch.setattr(launcher, "sweep_sites", lambda browser, **kw: observed.append(kw) or tuple(results))
    parked = []
    monkeypatch.setattr(launcher, "park_shared_cdp", parked.append)
    blank = []
    monkeypatch.setattr(launcher, "new_background_page", lambda *a, **k: blank.append(True))
    assert backend._run_login_sweep(background=True) == tuple(results)
    assert observed[0]["present_failures"] is False
    assert observed[0]["wait"] == backend._stop.wait
    assert len(parked) == int(not failure and not existing_nonblank)
    assert len(blank) == int(existing_nonblank)
    assert handle.disconnected is True and handle.closed is False
    assert backend.get_login_all_report() is None


def test_background_sweep_continues_after_failed_site_without_foreground(tmp_path):
    pages = []
    def new_tab(*a, **k):
        page = _Page()
        page.bring_to_front = lambda: pytest.fail("background must not activate Chrome")
        pages.append(page)
        return page
    sweep = SiteLoginSweep(_Browser(), new_tab=new_tab, present_failures=False)
    def failed(tab):
        raise RuntimeError("synthetic")
    results = sweep.run([SiteSignInStep("bad", "bad", failed), SiteSignInStep("good", "good", lambda tab: True)])
    sweep.close()
    assert [r.outcome for r in results] == [SiteLoginOutcome.UNAVAILABLE, SiteLoginOutcome.ALREADY_SIGNED_IN]
    assert len(pages) == 2 and not pages[0].closed and pages[1].closed


def test_stop_between_sites_prevents_next_login():
    attempted = []
    sweep = SiteLoginSweep(_Browser(), new_tab=lambda *a, **k: _Page(),
        present_failures=False, stop_requested=lambda: bool(attempted))
    results = sweep.run([SiteSignInStep(str(i), str(i), lambda tab: attempted.append(True) or True) for i in range(3)])
    sweep.close()
    assert len(results) == 1 and len(attempted) == 1


def test_pending_observation_aggregates_all_worksheets_and_resets(tmp_path, monkeypatch):
    from src.workflow import v12_flow
    from tests.workflow.test_rfq003_resilience import rows
    from tests.workflow.test_v12_flow import SHEET
    flow, *_ = _make_flow(tmp_path)
    monkeypatch.setattr(v12_flow, "query_pending_records", lambda *a: rows())
    flow._workflow_store.all_items = lambda: ()
    flow.process_pending = lambda records, **kw: ()
    flow.begin_poll_cycle()
    flow.poll_and_process(None, SHEET, now=NOW)
    flow.poll_and_process(None, SHEET, now=NOW)
    assert flow.pending_rows_seen == 4
    flow.begin_poll_cycle()
    assert flow.pending_rows_seen == 0


def test_idle_sweep_borrows_existing_poller_cdp_without_second_playwright(tmp_path, monkeypatch):
    results = [SiteLoginResult("TEST", SiteLoginOutcome.SIGNED_IN)]
    backend, handle = _sweep_backend(tmp_path, monkeypatch, results)
    handle.browser.contexts = [SimpleNamespace(pages=[SimpleNamespace(url="about:blank", is_closed=lambda: False)])]
    backend._browser_handle = handle
    backend._browser_acquirer = lambda *a, **kw: pytest.fail("must reuse the poller client")
    monkeypatch.setattr(launcher, "park_shared_cdp", lambda browser: None)
    assert backend._run_login_sweep(background=True) == tuple(results)
    assert not handle.disconnected and not handle.closed


@pytest.mark.parametrize("result", [None, (), (object(),)])
def test_invalid_maintenance_result_is_only_operational_warning(tmp_path, monkeypatch, result):
    backend, _, store = configured(tmp_path, monkeypatch)
    backend._run_login_sweep = lambda **kw: result
    backend._idle_login_tick(now=NOW + timedelta(minutes=15))
    backend._idle_login_tick(now=NOW + timedelta(minutes=30))
    assert backend._state is RunState.RUNNING and not backend._stop.is_set()
    assert len(store.claim_due_notifications(now=NOW + timedelta(minutes=31))) == 1
