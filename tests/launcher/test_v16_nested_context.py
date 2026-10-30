"""Real independent closure -> CombinedCycle -> durable flow, isolated ports only."""
import logging
import sqlite3
from contextlib import nullcontext
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState
from src.launcher import backend as launcher
from src.launcher.workbench_snapshot import RuntimeObservation
from src.workflow.service import WorkflowRuntime
from src.workflow.v12_contracts import DeliveryOutcome
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v12_smtp_transport import QQSMTPTransport
from src.workflow.v13_integration import CombinedCycle
from src.workflow.v13_quotation import V13Stopped
from tests.workflow.test_rfq006_integration import fixture as quote_fixture
from tests.workflow.test_tp_research import build as tp_fixture
from tests.workflow.test_v12_flow import NOW, SHEET, FakeSheetsReader, _make_flow
from tests.workflow.test_v13_quotation import WS


@pytest.mark.parametrize("inner", ["quotation", "tp"])
@pytest.mark.parametrize("failure", [None, "timeout", "raw_timeout", "pause", "stop", "cancel", "shared", "cleanup", "pagefault"])
@pytest.mark.parametrize("outer_pause", [False, True])
def test_real_nested_closure_restores_context_and_durable_guards(
        tmp_path, monkeypatch, caplog, inner, failure, outer_pause):
    backend = launcher.ProductionBackend(root=tmp_path)
    caplog.set_level(logging.INFO, logger="src.launcher.backend")
    monkeypatch.setattr(QQSMTPTransport, "send_operator_alert",
        lambda *_a, **_k: SimpleNamespace(outcome=DeliveryOutcome.SENT))
    time = SimpleNamespace(tick=0.0)
    # Pending-pause cases also freeze wall time: cache isolation must not depend
    # on two tasks receiving different wall-clock timestamps.
    clock = lambda: NOW if outer_pause else NOW + timedelta(seconds=time.tick)
    monkeypatch.setattr(launcher, "utc_now", clock)
    monkeypatch.setattr(launcher, "monotonic", lambda: time.tick)
    backend._observation = RuntimeObservation(clock=clock, timer=lambda: time.tick)
    backend._observation.enable(quotation=True, tp=True)
    backend._state = RunState.RUNNING
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({"inquiry": 900, inner: 900}, timer=lambda: time.tick)
    backend._module_runtime = runtime
    flow, store, ledger, research, _, _, writer, _mail = _make_flow(tmp_path / "inquiry")
    backend._store, backend._v12_store = store, ledger
    backend._v12_composition = SimpleNamespace(coordinator=flow)
    backend._purchase_completion = SimpleNamespace(process=lambda *_a, **_k: True,
        retry_saved_statuses=lambda **_: None)
    flow._row_wait = backend._wait_between_rows
    flow._stop_requested = backend._stop.is_set
    reader = FakeSheetsReader()
    one = reader.row
    reader.read_rows = lambda _: (one, replace(one, row_position=4))
    reader.discovery_scope = nullcontext
    reader.clear_discovery_snapshot = lambda: None
    qdb, _, _, _, _, _, integrated, _ = quote_fixture(tmp_path / "quote", [()])
    quote_service = integrated()
    quote_service.observe = backend._observe_quotation
    tp, _, _, transport, tpdb = tp_fixture(tmp_path / "tp", day=NOW.date())
    backend._tp = tp
    entered, completed, outer_identity = [], [], []
    pending = V12Fault(FaultScope.V12_PAUSE, "OUTER_PENDING_PAUSE")
    original_research = research.execute
    def outer_research(item):
        if not outer_identity:
            outer_identity.append((backend._cycle_id, backend._last_poll))
            backend._research_acquire_failure = (backend._last_poll, "outer-cache")
        else:
            assert (backend._cycle_id, backend._last_poll) == outer_identity[0]
            assert backend._research_acquire_failure == (outer_identity[0][1], "outer-cache")
        backend._observe_stage("inquiry", "合成采购调研", order_ref=item.inquiry_id)
        time.tick += 2
        return original_research(item)
    research.execute = outer_research
    def result(value):
        backend._complete_inquiry(value)  # real log/cycle attribution and notification drain
        completed.append(value.inquiry_id)
        if outer_pause:
            backend._module_pause_requested = pending
    flow._on_result = result
    def inner_port():
        entered.append((backend._cycle_id, backend._last_poll))
        assert entered[-1][0] != outer_identity[0][0]
        outer = backend._observation.modules["inquiry"]
        assert outer.status == "等待执行" and outer.stage == "订单间安全等待"
        assert backend._research_acquire_failure is None
        backend._observe_stage(inner, "合成只读端口", order_ref="inner-order")
        time.tick += 10
        backend._research_acquire_failure = (backend._last_poll, "inner-cache")
        if failure == "timeout":
            raise V12Fault(FaultScope.GLOBAL_STOP, "IC_NET_UNAVAILABLE")
        if failure == "raw_timeout":
            raise TimeoutError("synthetic unclassified read timeout")
        if failure == "pause":
            raise V12Fault(FaultScope.V12_PAUSE, "INNER_PAUSE")
        if failure == "pagefault":
            from src.research.cdp_pages import PageTargetCreationUncertain
            fault = PageTargetCreationUncertain((OSError("synthetic response lost"),))
            backend._page_admission.invalidate(fault)
            raise fault
        if failure == "shared":
            raise sqlite3.DatabaseError("synthetic integrity fault")
        if failure == "stop":
            backend._stop.set()
        if failure == "cancel":
            backend._stop.set()
            raise V13Stopped("synthetic cancellation")
    # Keep both real domain engines. Only their external data ports are synthetic.
    original_read = quote_service.cycle._quotes.read
    quote_service.cycle._quotes.read = lambda *a, **k: (inner_port() or original_read(*a, **k))
    tp.research.hook = inner_port
    def pause(fault):
        previous = backend._module_pause_requested
        backend._pause_v12(fault)
        if previous is not None:
            assert backend._module_pause_requested is previous
    backend._combined = CombinedCycle(flow, lambda _: quote_service.run(WS),
        on_pause=pause, stop_requested=backend._stop.is_set)
    for method in ("_check_site_recovery", "_refresh_dashboard_counts", "_cache_workbench",
                   "_notify", "_idle_login_tick", "_refresh"):
        monkeypatch.setattr(backend, method, lambda *_a, **_k: None)
    def close(*_a, **_k):
        if failure == "cleanup" and backend._module_contexts[-1:] == [inner] and entered:
            raise RuntimeError("synthetic cleanup failure")
    monkeypatch.setattr(backend, "_close_inso_order_tab", close)
    monkeypatch.setattr(backend._stop, "wait", lambda seconds: (setattr(time, "tick", time.tick+seconds) or False))
    monkeypatch.setattr(backend, "_wait_between_polls", lambda _: True)
    expected = failure in {"shared", "cleanup", "cancel", "pagefault"} or (failure == "raw_timeout" and inner == "quotation")
    if expected:
        with pytest.raises((sqlite3.DatabaseError, RuntimeError)) as raised:
            backend._run_independent_poll(runtime, {"spreadsheet_id": "synthetic"}, None,
                SimpleNamespace(poll_scope=nullcontext), reader, (SHEET,), None)
        if failure == "cleanup":
            assert raised.value.reason == "INSO_OPERATION_NOT_CLOSED"
            assert str(raised.value.__cause__) == "synthetic cleanup failure"
        if failure == "cancel":
            assert isinstance(raised.value, V13Stopped)
    else:
        backend._run_independent_poll(runtime, {"spreadsheet_id": "synthetic"}, None,
            SimpleNamespace(poll_scope=nullcontext), reader, (SHEET,), None)
    assert entered and (backend._cycle_id, backend._last_poll) == outer_identity[0]
    assert backend._module_pause_requested is None and not backend._module_contexts
    assert not backend._observation._module_scopes
    assert backend._research_acquire_failure == (outer_identity[0][1], "outer-cache")
    cards = backend._observation.modules
    assert cards["inquiry"].cycle_started_at == NOW
    assert cards[inner].cycle_elapsed_seconds == 10
    assert cards["inquiry"].cycle_finished_at == clock()
    assert backend._observation.cycle_started_at == NOW
    assert backend._observation.cycle_started_monotonic == 0
    assert backend._observation.cycle_finished_at == clock()
    if failure not in {"stop", "cancel", "shared", "cleanup", "raw_timeout", "pagefault"}:
        assert len(completed) == 2 and time.tick >= 124  # original120s minimum
        wait = [t for t in backend._observation.timings if t.module_id == "inquiry"
                and t.stage == "订单间安全等待"]
        assert len(wait) == 1 and wait[0].elapsed_seconds >= 120
    else:
        assert len(completed) == 1  # no next purchase after STOP/shared failure
    logs = [r for r in caplog.records if getattr(r, "business_module", None) == "V1.2"]
    assert logs and all(r.cycle_id == outer_identity[0][0] for r in logs)
    receipts = [r for r in caplog.records if getattr(r, "scheduled_module", None) == inner]
    assert [r.cycle_phase for r in receipts] == ["begin", "completed" if failure is None
        else "stopped" if failure in {"stop", "cancel"} else "deferred" if failure == "timeout"
        else "paused" if failure == "pause" else "failed"]
    assert all(r.cycle_id == entered[0][0] for r in receipts)
    assert not any(running for _, running, _ in runtime.module_plans().values())
    if outer_pause and not expected:
        assert runtime.module_plans()["inquiry"][2]
    if failure in {"cleanup", "pagefault"}:
        assert runtime.module_resource_failed
        with pytest.raises(RuntimeError, match="MODULE_RESOURCE_OWNERSHIP_LOST"):
            runtime.claim_due_module()
    with sqlite3.connect(qdb) as db:
        assert db.execute('pragma integrity_check').fetchone() == ('ok',)
    with sqlite3.connect(tpdb) as db:
        assert db.execute('pragma integrity_check').fetchone() == ('ok',)
    assert not writer.commands  # no valid business price, never fabricate a purchase
    assert len(transport.calls) <= 2  # never duplicate TP delivery


@pytest.mark.parametrize('soft_failure', [False, True])
def test_page_fault_latch_wins_over_translated_module_completion(tmp_path, monkeypatch, soft_failure):
    from src.research.cdp_pages import PageTargetCreationUncertain
    backend = launcher.ProductionBackend(root=tmp_path)
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({'inquiry': 900, 'tp': 900})
    assert runtime.claim_due_module() == 'inquiry'
    backend._module_runtime = runtime
    def translated(_):
        backend._page_admission.invalidate(PageTargetCreationUncertain((OSError('synthetic lost response'),)))
        if soft_failure:
            raise V12Fault(FaultScope.V12_PAUSE, 'TRANSLATED_SOURCE_FAILURE')
    backend._module_execute = translated
    monkeypatch.setattr(backend, '_close_inso_order_tab', lambda: None)
    monkeypatch.setattr(backend, '_cache_workbench', lambda **_: None)
    try:
        with pytest.raises(PageTargetCreationUncertain):
            backend._run_independent_job_scoped('inquiry')
        assert runtime.module_resource_failed
        assert all(paused for _, _, paused in runtime.module_plans().values())
        with pytest.raises(RuntimeError, match='MODULE_RESOURCE_OWNERSHIP_LOST'):
            runtime.claim_due_module()
    finally:
        backend.shutdown()

@pytest.mark.parametrize('fault_kind', ['page', 'order'])
@pytest.mark.parametrize('wrapping', ['direct', 'cause', 'context'])
def test_runtime_resource_fault_is_global_not_attributed_to_last_order(tmp_path, monkeypatch, wrapping, fault_kind):
    from src.research.cdp_pages import PageTargetCreationUncertain
    backend = launcher.ProductionBackend(root=tmp_path)
    from src.workflow.service import OrderResourceOwnershipError
    fault = (PageTargetCreationUncertain((OSError('synthetic response lost'),))
             if fault_kind == 'page' else OrderResourceOwnershipError())
    error = fault if wrapping == 'direct' else RuntimeError('synthetic adapter wrapper')
    if wrapping == 'cause':
        error.__cause__ = fault
    elif wrapping == 'context':
        error.__context__ = fault
    backend._active_inso_inquiry = 'historic-synthetic-order'
    backend._v13_ledger_ready = True
    backend._v12_store = object()
    notices = []
    backend._v12_composition = SimpleNamespace(coordinator=SimpleNamespace(run_notifications=lambda **_: None))
    monkeypatch.setattr(launcher, 'notify_runtime_fault', lambda store, run, reason, **_: notices.append(reason))
    monkeypatch.setattr(backend, '_record_fault_alert', lambda *_: pytest.fail('must not blame historic order'))
    try:
        backend._runtime_error(error)
        assert backend._state is RunState.GLOBAL_STOP
        assert backend._stop.is_set()
        assert notices == [fault.reason]
    finally:
        backend.shutdown()



def test_immutable_actor_fault_uses_original_backend_global_stop(tmp_path, monkeypatch):
    from src.workflow.market_messages import MarketFault, MarketFaultScope
    backend = launcher.ProductionBackend(root=tmp_path)
    backend._active_inso_inquiry = 'historic-synthetic-order'
    backend._v13_ledger_ready = True
    backend._v12_store = object()
    notices = []
    backend._v12_composition = SimpleNamespace(coordinator=SimpleNamespace(run_notifications=lambda **_: None))
    monkeypatch.setattr(launcher, 'notify_runtime_fault', lambda store, run, reason, **_: notices.append(reason))
    monkeypatch.setattr(backend, '_record_fault_alert', lambda *_: pytest.fail('not a historical order fault'))
    try:
        fault = MarketFault(MarketFaultScope.GLOBAL_STOP, 'CDP_PAGE_OWNERSHIP_UNCONFIRMED', ('ValueError',))
        backend.accept_market_fault(fault)
        assert backend._state is RunState.GLOBAL_STOP and backend._stop.is_set()
        assert notices == [fault.reason]
        from src.research.cdp_pages import PageTargetCleanupError
        with pytest.raises(PageTargetCleanupError) as caught:
            backend._page_admission.require_open()
        assert caught.value.reason == fault.reason
        assert caught.value.failure_classes == ('ValueError',)
    finally:
        backend.shutdown()
