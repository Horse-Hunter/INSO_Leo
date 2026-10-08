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
    monkeypatch.setattr(backend, "_page_target_id", lambda p: str(id(p)))
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


class ProtectedPage:
    def __init__(self, context, url):
        self.context, self.url, self.closed = context, url, False
        self.target_id = str(id(self))
        context.pages.append(self)
    def is_closed(self):
        return self.closed
    def close(self):
        self.closed = True
        self.context.pages.remove(self)


class ProtectedContext:
    def __init__(self):
        self.pages = []
        self.new_page()
    def new_page(self):
        return ProtectedPage(self, "about:blank")
    def new_cdp_session(self, page):
        return SimpleNamespace(send=lambda method: {"targetInfo": {"targetId": page.target_id}}, detach=lambda: None)


@pytest.mark.parametrize("kind", ["human", "existing", "success"])
def test_actual_poll_finally_preserves_keepalive_targets_and_next_cycle(tmp_path, monkeypatch, kind):
    import json
    import sqlite3
    from threading import Event

    from src.workflow.v13_integration import CombinedCycle
    from tests.launcher.test_backend import (
        _RecordingTransport,
        _SheetsService,
        _write_runtime_configs,
    )
    production, rc, rows = _write_runtime_configs(tmp_path)
    config = json.loads(production.read_text(encoding="utf-8"))
    config.update(v13_enabled=True, quotation_input={"gid": "0", "input_row": 1, "first_column": 1})
    production.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(launcher, "build_read_only_google_sheets_service", lambda _: _SheetsService(rows, Event()))
    monkeypatch.setattr(launcher, "assess_readiness", lambda *a, **k: SimpleNamespace(ready=True, missing_site_ids=()))
    monkeypatch.setattr(launcher, "build_research_service", lambda *a, **k: SimpleNamespace(execute=lambda _: None))
    monkeypatch.setattr("src.launcher.v12_composition.QQSMTPTransport", _RecordingTransport)
    monkeypatch.setattr(launcher, "QQSMTPTransport", _RecordingTransport)
    context = ProtectedContext()
    browser = SimpleNamespace(contexts=[context], is_connected=lambda: True)
    handle = SimpleNamespace(browser=browser, owned=False, disconnect=lambda: None, close=lambda: None)
    backend = launcher.ProductionBackend(config_path=rc, production_config_path=production,
        root=tmp_path, browser_acquirer=lambda *a, **k: handle)
    preserved = []
    if kind == "existing":
        preserved.append(ProtectedPage(context, "https://manual.example/"))
    sweeps, cycles, cleanups = [], [], []
    def sweep(browser, **kw):
        sweeps.append(True)
        if kind == "human":
            preserved.append(ProtectedPage(context, "https://captcha.example/"))
        return (SiteLoginResult("TEST", SiteLoginOutcome.NEEDS_HUMAN if kind == "human" else SiteLoginOutcome.SIGNED_IN),)
    monkeypatch.setattr(launcher, "sweep_sites", sweep)
    def business(self, reader, worksheets, *, now):
        cycles.append(backend._state)
        self.v12.begin_poll_cycle()
        backend._browser_handle = handle
        if len(cycles) == 1:
            backend._idle_empty_polls = 1
            backend._idle_login_since = now - timedelta(minutes=31)
    monkeypatch.setattr(CombinedCycle, "run", business)
    close = backend._close_inso_order_tab
    def cleanup():
        close()
        cleanups.append(tuple(context.pages))
    monkeypatch.setattr(backend, "_close_inso_order_tab", cleanup)
    original_wait = backend._stop.wait
    def wait(seconds):
        if seconds == 900:
            if len(cycles) >= 2:
                backend._stop.set()
                return True
            return False
        return original_wait(seconds)
    backend._wait_between_polls = wait
    try:
        backend.start()
        backend._thread.join(timeout=8)
        assert not backend._thread.is_alive() and len(cycles) == 2
        assert cycles == [RunState.RUNNING, RunState.RUNNING]
        assert len(sweeps) == 1  # Protected repair page must not accumulate another sweep.
        if preserved:
            assert all(not p.closed and p in cleanups[0] for p in preserved)
            assert all(p in context.pages for p in preserved)
            backend._state = RunState.RUNNING
            backend._browser_handle = handle
            for page in preserved:
                page.close()  # Owner's manual closure releases protection on next cleanup.
            backend._close_inso_order_tab()
            assert not backend._keepalive_protected_targets
        assert len(context.pages) == 1 and context.pages[0].url == "about:blank"
        with sqlite3.connect(backend._v12_store.database_path) as db:
            count = db.execute("SELECT count(*) FROM workflow_v12_notification_commands WHERE command_id LIKE 'idle-login:%'").fetchone()[0]
            assert count == int(kind == "human")
            assert db.execute("SELECT count(*) FROM workflow_v13_holds").fetchone()[0] == 0
    finally:
        backend.shutdown()


def test_detached_protected_target_check_never_relogs_before_idle_threshold(tmp_path, monkeypatch):
    backend, handle = _sweep_backend(tmp_path, monkeypatch, ())
    context = ProtectedContext()
    handle.browser = SimpleNamespace(contexts=[context], is_connected=lambda: True)
    backend._keepalive_protected_targets.add("owner-closed-target")
    monkeypatch.setattr(launcher, "sweep_sites", lambda *a, **kw: pytest.fail("check-only must not relog"))
    assert backend._run_login_sweep(background=True, check_only=True) == ()
    assert not backend._keepalive_protected_targets and handle.disconnected
    assert len(context.pages) == 1 and context.pages[0].url == "about:blank"


def test_protected_target_survives_new_cdp_page_wrappers(tmp_path):
    backend = launcher.ProductionBackend(root=tmp_path)
    first = ProtectedContext()
    original = ProtectedPage(first, "https://manual.example/")
    backend._protect_keepalive_pages([original])
    second = ProtectedContext()
    attached = ProtectedPage(second, original.url)
    attached.target_id = original.target_id
    browser = SimpleNamespace(contexts=[second], is_connected=lambda: True)
    backend._park_browser(browser)
    assert not attached.closed and attached in second.pages
    attached.close()
    backend._park_browser(browser)
    assert not backend._keepalive_protected_targets
    assert len(second.pages) == 1 and second.pages[0].url == "about:blank"


@pytest.mark.parametrize("state", [RunState.GLOBAL_STOP, RunState.MANUAL_REVIEW])
def test_stop_page_without_inso_session_is_not_closed_by_backend_release(tmp_path, state):
    backend = launcher.ProductionBackend(root=tmp_path)
    released = []
    backend._state = state
    backend._browser_handle = SimpleNamespace(owned=True,
        disconnect=lambda: released.append("detach"),
        close=lambda: pytest.fail("must retain settlement/manual operation page"))
    backend._inso_session = None
    backend._release_idle_browser(force=True)
    assert released == ["detach"]


def test_manual_login_failure_page_survives_later_research_cleanup(tmp_path, monkeypatch):
    result = SiteLoginResult("TEST", SiteLoginOutcome.NEEDS_HUMAN)
    backend, handle = _sweep_backend(tmp_path, monkeypatch, [result])
    context = ProtectedContext()
    handle.browser.contexts = [context]
    handle.browser.is_connected = lambda: True
    failed = []
    def sweep(browser, **options):
        assert "present_failures" not in options  # Manual button still presents its result.
        failed.append(ProtectedPage(context, "https://captcha.example/"))
        return (result,)
    monkeypatch.setattr(launcher, "sweep_sites", sweep)
    assert backend._run_login_sweep() == (result,)
    assert handle.disconnected and not handle.closed
    assert failed[0].target_id in backend._keepalive_protected_targets
    backend._park_browser(handle.browser)
    assert not failed[0].closed
    assert any(page.url == "about:blank" for page in context.pages)
    failed[0].close()  # Owner resolves/closes the human page.
    backend._park_browser(handle.browser)
    assert backend._keepalive_protected_targets == set()
    assert len(context.pages) == 1 and context.pages[0].url == "about:blank"
