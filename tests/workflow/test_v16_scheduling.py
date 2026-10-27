"""Deterministic arbitration and real recipient-claim races, no production I/O."""
import threading
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from src.workflow.service import WorkflowRuntime
from src.workflow.v12_notifications import V12NotificationWorker


def runtime(periods=None):
    clock = SimpleNamespace(tick=0.0)
    run = WorkflowRuntime(None, None, ())
    run.configure_modules(periods or {"inquiry": 900, "quotation": 60, "tp": 120},
                          timer=lambda: clock.tick)
    return run, clock


def test_independent_completion_deadlines_no_shared_fifteen_minute_delay():
    run, clock = runtime()
    assert run.claim_due_module() == "inquiry"
    clock.tick = 300
    run.complete_module("inquiry")
    assert run.claim_due_module() == "quotation"
    clock.tick = 310
    run.complete_module("quotation")
    assert run.claim_due_module() == "tp"
    clock.tick = 360
    run.complete_module("tp")
    assert run.module_delay() == 10
    clock.tick = 370
    assert run.claim_due_module() == "quotation"
    assert run.module_plans()["inquiry"][0] == 1200
    assert run.module_plans()["tp"][0] == 480


def test_browser_resource_never_crosses_threads_or_overlaps_modules():
    run, _ = runtime()
    assert run.claim_due_module() == "inquiry"
    assert run.claim_due_module() is None
    run.yield_module_resource("inquiry")
    results = []
    thread = threading.Thread(target=lambda: results.append(run.claim_due_module()))
    thread.start()
    thread.join(2)
    assert results == [None]
    assert run.claim_due_module() == "quotation"
    run.complete_module("quotation")
    run.resume_module_resource("inquiry")
    run.complete_module("inquiry")
    assert run.claim_due_module() == "tp"


@pytest.mark.parametrize("value", [False, True, 0, -1, "900", float("nan"), float("inf")])
def test_invalid_periods_fail_before_execution(value):
    run = WorkflowRuntime(None, None, ())
    with pytest.raises(ValueError):
        run.configure_modules({"inquiry": value})


def test_failure_pause_and_manual_reset_do_not_delay_other_modules():
    run, clock = runtime()
    assert run.claim_due_module() == "inquiry"
    run.complete_module("inquiry", pause=True)
    assert run.claim_due_module() == "quotation"
    run.complete_module("quotation", retry_after=1800)
    assert run.claim_due_module() == "tp"
    run.complete_module("tp")
    clock.tick = 30
    run.reset_module("tp")
    assert run.module_plans()["quotation"][0] == 1800
    assert run.module_plans()["inquiry"][2]
    assert run.module_delay() == 120


def test_only_existing_delivery_worker_dispatches_while_browser_can_progress():
    entered, release = threading.Event(), threading.Event()
    claims = []

    class Store:
        def claim_due_notifications(self, **_):
            claims.append(threading.get_ident())
            entered.set()
            assert release.wait(2)
            return ()

    worker = V12NotificationWorker(Store(), None)
    worker.defer_delivery()
    assert worker.run_due(now=datetime.now(UTC)) == 0
    errors = []

    def deliver():
        try:
            worker.bind_delivery_thread()
            worker.run_due(now=datetime.now(UTC))
        except BaseException as exc:  # noqa: BLE001 - assert every worker failure on parent thread
            errors.append(exc)

    thread = threading.Thread(target=deliver)
    thread.start()
    try:
        assert entered.wait(2)
        run, _ = runtime()
        assert run.claim_due_module() == "inquiry"
        assert worker.run_due(now=datetime.now(UTC)) == 0
        run.complete_module("inquiry")
    finally:
        release.set()
        thread.join(2)
    assert not errors and not thread.is_alive() and len(claims) == 1


@pytest.mark.parametrize("second", ["SENT", "UNKNOWN"])
def test_atomic_recipient_claims_parallel_workers_and_restart_never_replay(tmp_path, second):
    from src.workflow.v12_contracts import DeliveryOutcome
    from src.workflow.v12_notifications import FakeNotificationTransport
    from tests.workflow.test_v12_notifications import NOW, command, prepared_store

    store = prepared_store(tmp_path)
    cmd = command()
    store.enqueue_notification(cmd)
    transport = FakeNotificationTransport({"a": (DeliveryOutcome.SENT,),
        "b": (DeliveryOutcome(second),)})
    barrier = threading.Barrier(3)
    errors = []
    def deliver():
        try:
            barrier.wait(2)
            V12NotificationWorker(store, transport).run_due(now=NOW)
        except BaseException as exc:  # noqa: BLE001 - assert every worker failure on parent thread
            errors.append(exc)
    threads = [threading.Thread(target=deliver) for _ in range(2)]
    for thread in threads:
        thread.start()
    try:
        barrier.wait(2)
    finally:
        for thread in threads:
            thread.join(3)
    assert not errors and all(not t.is_alive() for t in threads)
    assert sorted(transport.calls) == [(cmd.command_id, "a"), (cmd.command_id, "b")]
    store.enqueue_notification(cmd)  # immutable command already exists
    assert V12NotificationWorker(store, transport).run_due(now=NOW+timedelta(days=1)) == 0
    assert len(transport.calls) == 2


@pytest.mark.parametrize("outcome", ["SENT", "UNKNOWN"])
def test_tp_deferred_dispatch_retains_manual_auto_exclusion_and_history(tmp_path, outcome):
    from src.workflow.v12_contracts import DeliveryOutcome
    from tests.research.test_tp import NOW
    from tests.workflow.test_tp_research import build

    cycle, _, _, transport, _ = build(tmp_path, (DeliveryOutcome(outcome),))
    cycle.worker.defer_delivery()
    cycle.run("synthetic", now=NOW)
    key = cycle.store.rows()[0]["task_id"]
    assert not transport.calls
    assert not cycle.store.manual_allowed(key)
    errors = []
    def deliver():
        try:
            cycle.worker.bind_delivery_thread()
            cycle.worker.run_due(now=NOW)
        except BaseException as exc:  # noqa: BLE001 - assert every worker failure on parent thread
            errors.append(exc)
    thread = threading.Thread(target=deliver)
    thread.start()
    thread.join(3)
    assert not errors and not thread.is_alive() and len(transport.calls) == 2
    assert cycle.store.delivery(key) == outcome
    cycle.run("synthetic", now=NOW+timedelta(days=1))
    assert len(cycle.research.calls) == 1 and len(transport.calls) == 2
    assert cycle.store.manual_allowed(key) is (outcome == "SENT")
