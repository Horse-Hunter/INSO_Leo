"""Tests for the MockBackend lifecycle and contract."""

from time import sleep

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
