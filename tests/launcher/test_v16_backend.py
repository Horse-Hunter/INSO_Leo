"""Canonical-backend integration: synthetic clocks, faults and actor boundaries."""
import sqlite3
import threading
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState
from src.launcher import backend as launcher
from src.workflow.service import WorkflowRuntime
from src.workflow.v12_faults import FaultScope, V12Fault


def prepared(tmp_path, monkeypatch):
    backend = launcher.ProductionBackend(root=tmp_path)
    clock = SimpleNamespace(tick=0.0)
    monkeypatch.setattr(launcher, "monotonic", lambda: clock.tick)
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({"inquiry": 900, "quotation": 60, "tp": 120},
                              timer=lambda: clock.tick)
    backend._module_runtime = runtime
    backend._state = RunState.RUNNING
    backend._observation.enable(quotation=True, tp=True)
    for name in ("_close_inso_order_tab", "_notify", "_cache_workbench"):
        monkeypatch.setattr(backend, name, lambda *_, **__: None)
    return backend, runtime, clock


def test_independent_loop_calls_existing_module_paths_without_combined_wait(tmp_path, monkeypatch):
    backend, runtime, _ = prepared(tmp_path, monkeypatch)
    calls = []
    def called(name):
        calls.append((name, threading.get_ident()))
    backend._combined = SimpleNamespace(
        run_inquiry=lambda *_, **__: called("inquiry"),
        run_quotation=lambda *_, **__: called("quotation"))
    backend._tp = SimpleNamespace(run=lambda *_, **__: called("tp"), issues={})
    backend._purchase_completion = SimpleNamespace(retry_saved_statuses=lambda **_: None)
    for name in ("_check_site_recovery", "_refresh_dashboard_counts", "_begin_poll_projection", "_idle_login_tick"):
        monkeypatch.setattr(backend, name, lambda *_, **__: None)
    waits = []
    def wait(seconds):
        waits.append(seconds)
        backend._stop.set()
        return True
    monkeypatch.setattr(backend, "_wait_between_polls", wait)
    backend._run_independent_poll(runtime, {"spreadsheet_id": "synthetic"}, None,
        SimpleNamespace(poll_scope=nullcontext), SimpleNamespace(discovery_scope=nullcontext), (), None)
    assert [name for name, _ in calls] == ["inquiry", "quotation", "tp"]
    assert len({owner for _, owner in calls}) == 1
    assert waits == [60]  # own quotation deadline, not a shared900s delay
    assert backend._module_runtime is None


@pytest.mark.parametrize("fault", [sqlite3.OperationalError("synthetic"),
    V12Fault(FaultScope.GLOBAL_STOP, "SHEETS_SCHEMA_UNAVAILABLE"),
    V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE")])
def test_shared_integrity_and_safety_faults_propagate(tmp_path, monkeypatch, fault):
    backend, runtime, _ = prepared(tmp_path, monkeypatch)
    backend._module_execute = lambda _: (_ for _ in ()).throw(fault)
    assert runtime.claim_due_module() == "inquiry"
    with pytest.raises(type(fault)):
        backend._run_independent_job("inquiry")


def test_website_backoff_and_module_pause_leave_other_due_modules_ready(tmp_path, monkeypatch):
    backend, runtime, _ = prepared(tmp_path, monkeypatch)
    backend._module_execute = lambda _: (_ for _ in ()).throw(
        V12Fault(FaultScope.GLOBAL_STOP, "IC_NET_UNAVAILABLE"))
    monkeypatch.setattr(backend, "_defer_website_poll", lambda *_a, **_k: True)
    assert runtime.claim_due_module() == "inquiry"
    backend._run_independent_job("inquiry")
    assert runtime.module_plans()["inquiry"][0] == 900
    assert runtime.claim_due_module() == "quotation"
    backend._module_execute = lambda _: (_ for _ in ()).throw(
        V12Fault(FaultScope.V12_PAUSE, "SYNTHETIC_LOCAL"))
    backend._run_independent_job("quotation")
    assert runtime.module_plans()["quotation"][2]
    assert runtime.claim_due_module() == "tp"
    assert not backend._stop.is_set()


def test_completed_row_cooldown_runs_due_modules_without_shortening_safety_wait(tmp_path, monkeypatch):
    backend, runtime, clock = prepared(tmp_path, monkeypatch)
    calls = []
    refreshed = []
    backend._manual_reader = SimpleNamespace(clear_discovery_snapshot=lambda: refreshed.append(True))
    def execute(module):
        calls.append(module)
        clock.tick += 30
    backend._module_execute = execute
    def wait(seconds):
        clock.tick += seconds
        return False
    monkeypatch.setattr(backend._stop, "wait", wait)
    assert runtime.claim_due_module() == "inquiry"
    assert backend._wait_between_rows(120) is False
    assert clock.tick == 120
    assert calls == ["quotation", "tp", "quotation"]
    assert len(refreshed) == len(calls)
    assert runtime.module_plans()["inquiry"][1]
    runtime.complete_module("inquiry")  # resource returned to original actor


def test_idle_overall_wait_preserves_each_modules_actual_deadline(tmp_path, monkeypatch):
    from datetime import timedelta
    backend, runtime, _ = prepared(tmp_path, monkeypatch)
    for name in ("inquiry", "quotation", "tp"):
        assert runtime.claim_due_module() == name
        runtime.complete_module(name)
    before = launcher.utc_now()
    backend._publish_poll_wait(60)
    cards = backend._observation.modules
    for name, seconds in (("inquiry", 900), ("quotation", 60), ("tp", 120)):
        assert before + timedelta(seconds=seconds-1) < cards[name].next_check_at
        assert cards[name].next_check_at < launcher.utc_now() + timedelta(seconds=seconds+1)


def test_stopped_runtime_never_claims_or_executes_due_business(tmp_path, monkeypatch):
    backend, runtime, _ = prepared(tmp_path, monkeypatch)
    backend._stop.set()
    backend._run_independent_poll(runtime, {}, None, None, None, (), None)
    assert not any(running for _, running, _ in runtime.module_plans().values())


def test_wrapped_browser_error_never_hides_real_security_violation(tmp_path, monkeypatch):
    from src.inso.session import SecurityViolation
    backend, runtime, _ = prepared(tmp_path, monkeypatch)
    error = launcher.BrowserBootstrapError("synthetic")
    error.__cause__ = SecurityViolation("ownership unverified")
    backend._module_execute = lambda _: (_ for _ in ()).throw(error)
    monkeypatch.setattr(backend, "_defer_website_poll", lambda *_a, **_k:
                        pytest.fail("security fault must never become site backoff"))
    assert runtime.claim_due_module() == "inquiry"
    with pytest.raises(launcher.BrowserBootstrapError):
        backend._run_independent_job("inquiry")


def test_manual_actor_keeps_gates_and_resets_only_its_module(tmp_path, monkeypatch):
    backend, runtime, clock = prepared(tmp_path, monkeypatch)
    for name in ("inquiry", "quotation", "tp"):
        assert runtime.claim_due_module() == name
        runtime.complete_module(name)
    backend._manual_request = ("synthetic", "tp-synthetic", "tp", None, None)
    calls = []
    def execute(request):
        assert backend._manual_busy and not backend._poll_idle.is_set()
        assert not backend._manual_idle()
        clock.tick += 5
        calls.append(request)
    monkeypatch.setattr(backend, "_execute_order_action", execute)
    monkeypatch.setattr(backend, "_invalidate_order_view", lambda _: None)
    class Condition:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def wait(self, seconds):
            clock.tick += seconds
            if clock.tick >= 60:
                backend._stop.set()
    backend._manual_condition = Condition()
    assert backend._wait_between_polls(60)
    assert len(calls) == 1
    assert runtime.module_plans()["tp"][0] == 125
    assert runtime.module_plans()["quotation"][0] == 60
    assert runtime.module_plans()["inquiry"][0] == 900
    assert not backend._manual_idle() and not backend._manual_busy
