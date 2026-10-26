"""First CEO review: real wait loop and canonical permission gate, synthetic only."""

from datetime import UTC, datetime, timedelta
from math import ceil
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState
from src.gui.workbench import scheduling
from src.launcher import backend as launcher
from src.launcher.backend import ProductionBackend
from src.launcher.workbench_snapshot import RuntimeObservation
from src.workflow.v12_contracts import BusinessState, EventType, WorkflowEvent
from tests.launcher.test_manual_order import prepared
from tests.workflow.test_v12_flow import NOW


class VirtualTime:
    def __init__(self):
        self.base = datetime(2026, 1, 1, tzinfo=UTC)
        self.tick = 0.0

    def wall(self):
        return self.base + timedelta(seconds=self.tick)


class VirtualCondition:
    def __init__(self, clock, check):
        self.clock, self.check = clock, check
        self.waited = 0.0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def wait(self, seconds):
        self.check()
        self.clock.tick += seconds
        self.waited += seconds


def virtual_backend(tmp_path, monkeypatch):
    clock = VirtualTime()
    monkeypatch.setattr(launcher, "monotonic", lambda: clock.tick)
    monkeypatch.setattr(launcher, "utc_now", clock.wall)
    backend = ProductionBackend(root=tmp_path)
    backend._observation = RuntimeObservation(clock=clock.wall, timer=lambda: clock.tick)
    backend._observation.enable(quotation=True, tp=True)
    backend._state = RunState.RUNNING
    monkeypatch.setattr(backend, "_release_idle_browser", lambda: None)
    return backend, clock


@pytest.mark.parametrize("tp_minutes", [0, 5, 10, 20])
def test_tp_duration_never_shortens_actual_wait_or_ui_countdown(tmp_path, monkeypatch, tp_minutes):
    backend, clock = virtual_backend(tmp_path, monkeypatch)
    backend._observation.begin_cycle()
    legacy_deadline = clock.wall() + timedelta(minutes=15)
    backend._next_poll_at = legacy_deadline  # the existing manual-operation gate
    backend._notify()
    backend._observation.stage("tp", "合成 TP 调研")
    clock.tick += tp_minutes * 60
    assert "本轮进行中" in scheduling(backend.get_workbench_snapshot(), now=clock.wall(), tick=clock.tick)
    backend._observation.end_cycle()  # the normal post-TP boundary
    assert "等待调度确认" in scheduling(backend.get_workbench_snapshot(), now=clock.wall())
    wait_start = clock.wall()

    def check():
        snap = backend.get_workbench_snapshot()
        assert snap.planned_check_at == wait_start + timedelta(minutes=15)
        assert snap.session.next_poll_at == legacy_deadline
        remaining = ceil((snap.planned_check_at - clock.wall()).total_seconds())
        assert scheduling(snap, now=clock.wall()) == f"下次检查 {remaining // 60:02d}:{remaining % 60:02d}"
        assert not any(m.started_monotonic is not None for m in snap.modules)

    condition = VirtualCondition(clock, check)
    backend._manual_condition = condition
    assert backend._wait_between_polls(900) is False
    assert condition.waited == 900 and clock.wall() == wait_start + timedelta(minutes=15)
    assert backend._next_poll_at == legacy_deadline  # no early poll or permission expansion
    assert "计划时间已到" in scheduling(backend.get_workbench_snapshot(), now=clock.wall())


@pytest.mark.parametrize("reason,site", [
    ("GOOGLE_SPREADSHEET_UNAVAILABLE", "Google Sheets"),
    ("INSO_QUERY_RETRIES_EXHAUSTED", "INSO"),
])
def test_two_deferred_rounds_close_execution_and_then_recover(tmp_path, monkeypatch, reason, site):
    from src.workflow.v12_faults import FaultScope, V12Fault

    backend, clock = virtual_backend(tmp_path, monkeypatch)
    for _ in range(2):
        backend._observation.begin_cycle()
        clock.tick += 7
        assert backend._defer_website_poll(V12Fault(FaultScope.GLOBAL_STOP, reason),
                                           timedelta(minutes=15), notify=False)
        wait_start = clock.wall()
        measured = []

        def check(wait_start=wait_start, measured=measured):
            snap = backend.get_workbench_snapshot()
            assert snap.cycle_finished_at == wait_start
            assert snap.recovery_site == site
            assert snap.planned_check_at == wait_start + timedelta(minutes=15)
            text = scheduling(snap, now=clock.wall())
            assert f"等待{site}恢复" in text and "本轮进行中" not in text
            assert all(m.started_monotonic is None for m in snap.modules)
            durations = tuple(m.elapsed_seconds for m in snap.modules)
            if measured:
                assert durations == measured[0]  # recovery idle is not execution
            measured.append(durations)

        backend._manual_condition = VirtualCondition(clock, check)
        assert backend._wait_between_polls(900) is False
        assert backend._manual_condition.waited == 900 and not backend._stop.is_set()
    backend._site_recovered(site)
    backend._observation.begin_cycle()
    assert backend.get_workbench_snapshot().recovery_site is None
    assert "本轮进行中" in scheduling(backend.get_workbench_snapshot(), tick=clock.tick)


def test_request_rechecks_durable_permissions_after_positive_display_hint(tmp_path, monkeypatch):
    backend, _, _, ledger, _, _, _, inquiry = prepared(tmp_path, monkeypatch)
    backend._cache_workbench(force=True)
    # Use the existing state projection; this is only a request affordance.
    backend._manual_quote = SimpleNamespace()
    assert backend.order_action_hint(inquiry, "edit")
    assert backend.order_action_hint(inquiry, "purchase")
    ledger.set_business_state(inquiry, BusinessState.SUBMIT_UNCONFIRMED,
        WorkflowEvent("synthetic-review-armed", inquiry, EventType.SAVE_DISPATCH_ARMED, NOW, "workflow"))
    assert backend.order_action_hint(inquiry, "purchase")  # stale display is not authorization
    assert backend.request_order_action(inquiry, "purchase") is not None
    assert backend._manual_request is None
    backend._cache_workbench(force=True)
    assert not backend.order_action_hint(inquiry, "purchase")
    backend._manual_busy = True
    assert not backend.order_action_hint(inquiry, "edit")


def test_manual_command_keeps_original_full_wait_reset_and_stop(tmp_path, monkeypatch):
    backend, clock = virtual_backend(tmp_path, monkeypatch)
    backend._observation.begin_cycle()
    backend._next_poll_at = clock.wall() + timedelta(minutes=15)
    original_end = clock.wall()
    backend._observation.end_cycle()
    invoked = []

    def execute(_):
        assert backend._manual_busy and not backend._poll_idle.is_set()
        assert not backend._manual_idle()
        clock.tick += 120
        invoked.append(clock.wall())

    def check():
        snap = backend.get_workbench_snapshot()
        assert snap.cycle_finished_at == original_end
        if not invoked:
            backend._manual_request = ("synthetic", "synthetic", "tp", None, None)
        else:
            assert snap.planned_check_at == invoked[0] + timedelta(minutes=15)

    monkeypatch.setattr(backend, "_execute_order_action", execute)
    monkeypatch.setattr(backend, "_close_inso_order_tab", lambda: None)
    backend._manual_condition = VirtualCondition(clock, check)
    assert backend._wait_between_polls(900) is False
    assert len(invoked) == 1 and backend._manual_condition.waited == 900.25
    assert clock.wall() == invoked[0] + timedelta(minutes=15)
    backend._stop.set()
    assert backend._wait_between_polls(900) is True
    assert backend.get_workbench_snapshot().planned_check_at is None
