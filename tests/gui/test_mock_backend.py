"""Tests for the MockBackend lifecycle and contract."""

import logging
from threading import Event, Thread
from time import monotonic, sleep

import pytest

from src.gui.contracts import OrderStatus, RunState
from src.gui.mock_backend import MockBackend


@pytest.fixture
def backend():
    instance = MockBackend(cycle_seconds=0.5)
    yield instance
    instance.shutdown()


def test_backend_initial_state_is_stopped(backend):
    status = backend.get_status()
    assert status.state == RunState.STOPPED
    assert status.run_id is None


def test_start_creates_run_id(backend):
    backend.start()
    assert backend.run_id is not None
    status = backend.get_status()
    assert status.state == RunState.RUNNING
    backend.shutdown()


def test_start_is_idempotent_while_running(backend):
    backend.start()
    first_id = backend.run_id
    backend.start()  # should be ignored
    assert backend.run_id == first_id
    backend.shutdown()


def test_stop_after_cycle_returns_to_stopped(backend):
    backend.start()
    sleep(0.1)
    backend.request_stop_after_cycle()

    # Wait for the worker to finish the current compressed cycle.
    sleep(1.5)

    status = backend.get_status()
    assert status.state == RunState.STOPPED
    assert status.stopped_at is not None


def test_orders_appear_after_cycle(backend):
    backend.start()
    sleep(1.0)
    backend.request_stop_after_cycle()
    sleep(1.0)

    results = backend.get_current_run_results()
    assert len(results) >= 1
    order = results[0]
    assert order.model
    assert order.quantity > 0
    assert order.status in {
        OrderStatus.COMPLETED,
        OrderStatus.PARTIAL,
        OrderStatus.MANUAL_REVIEW,
    }


def test_results_tagged_with_current_run_id(backend):
    backend.start()
    sleep(1.0)
    backend.request_stop_after_cycle()
    sleep(1.0)

    run_id = backend.run_id
    results = backend.get_current_run_results()
    for order in results:
        assert order.run_id == run_id


def test_health_report_has_four_components(backend):
    health = backend.get_health()
    assert len(health.items) == 4
    names = {item.component for item in health.items}
    assert names == {"Google Sheets", "Browser/CDP", "Credential", "Research"}


def test_mock_sources_keep_the_gui_display_names(backend):
    order = backend._generate_order()
    assert tuple(source.source for source in order.sources) == (
        "INSO",
        "Findchips",
        "华强",
        "立创",
        "正能量",
    )


def test_mock_health_is_defined_by_gui_components(backend):
    initial = {item.component: item.status for item in backend.get_health().items}
    assert initial == {
        "Google Sheets": "正常",
        "Browser/CDP": "正常",
        "Credential": "正常",
        "Research": "正常",
    }

    backend.start()
    running = {item.component: item.status for item in backend.get_health().items}
    assert running == {
        "Google Sheets": "正在运行",
        "Browser/CDP": "正在运行",
        "Credential": "正常",
        "Research": "正在运行",
    }
    backend.shutdown()


def test_diagnostics_expose_worker_state(backend):
    diag = backend.get_diagnostics()
    assert diag.worker_state == "stopped"
    backend.start()
    sleep(0.2)
    diag = backend.get_diagnostics()
    assert diag.worker_state == "running"
    assert diag.run_id is not None
    backend.shutdown()


def test_status_callback_fires_on_start(backend):
    snapshots = []

    def cb(status):
        snapshots.append(status)

    backend.on_status_change(cb)
    backend.start()
    sleep(0.2)
    backend.shutdown()

    assert any(s.state == RunState.RUNNING for s in snapshots)


def test_shutdown_joins_worker_and_unregisters_callbacks(backend):
    backend.on_status_change(lambda _status: None)
    backend.on_log(lambda _entry: None)
    backend.start()
    worker = backend._worker

    backend.shutdown()

    assert worker is not None
    assert not worker.is_alive()
    assert backend._status_callbacks == []
    assert backend._log_callbacks == []
    assert backend._ring_log._listeners == []


def test_info_logging_listener_does_not_deadlock_start_stop_or_shutdown():
    backend = MockBackend(cycle_seconds=3.0)
    backend_logger = logging.getLogger("src.gui.mock_backend")
    previous_level = backend_logger.level
    backend_logger.setLevel(logging.INFO)
    received_logs = []
    backend.on_log(received_logs.append)
    actions = []

    def run_actions():
        backend.start()
        actions.append("start")
        backend.request_stop_after_cycle()
        actions.append("stop")
        backend.shutdown()
        actions.append("shutdown")

    action_thread = Thread(target=run_actions, daemon=True)
    try:
        action_thread.start()
        action_thread.join(timeout=5.0)
        assert not action_thread.is_alive(), "backend operation hung with INFO listener"
        assert actions == ["start", "stop", "shutdown"]
        assert received_logs
    finally:
        backend_logger.setLevel(previous_level)
        if not action_thread.is_alive():
            backend.shutdown()


def test_stop_during_cycle_finishes_that_cycle_then_stops(backend):
    cycle_started = Event()
    finish_cycle = Event()
    cycle_count = 0

    def controlled_cycle():
        nonlocal cycle_count
        cycle_count += 1
        cycle_started.set()
        assert finish_cycle.wait(timeout=2.0)
        order = backend._generate_order()
        with backend._lock:
            backend._orders.append(order)

    backend._run_cycle = controlled_cycle
    backend.start()
    worker = backend._worker
    assert cycle_started.wait(timeout=2.0)

    backend.request_stop_after_cycle()
    assert backend.get_status().state == RunState.STOPPING_AFTER_CYCLE
    finish_cycle.set()
    assert worker is not None
    worker.join(timeout=2.0)

    assert not worker.is_alive()
    assert cycle_count == 1
    assert len(backend.get_current_run_results()) == 1
    assert backend.get_status().state == RunState.STOPPED


def test_stop_during_idle_wait_does_not_start_another_cycle(backend):
    backend._cycle_seconds = 30.0
    cycle_count = 0

    def quick_cycle():
        nonlocal cycle_count
        cycle_count += 1
        order = backend._generate_order()
        with backend._lock:
            backend._orders.append(order)

    backend._run_cycle = quick_cycle
    backend.start()
    worker = backend._worker
    deadline = monotonic() + 2.0
    while monotonic() < deadline:
        with backend._lock:
            idle = not backend._cycle_active and backend._state == RunState.RUNNING
        if idle:
            break
        sleep(0.005)
    assert idle, "worker did not enter its cycle interval"

    backend.request_stop_after_cycle()
    assert worker is not None
    worker.join(timeout=2.0)

    assert not worker.is_alive()
    assert cycle_count == 1
    assert len(backend.get_current_run_results()) == 1
    assert backend.get_status().state == RunState.STOPPED
