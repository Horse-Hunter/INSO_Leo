"""Original poll -> integrated quotation -> real TP/outbox, isolated data ports."""
from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState
from src.launcher import backend as launcher
from src.launcher.workbench_snapshot import RuntimeObservation
from src.research.cdp_pages import PageTargetCleanupError
from src.sheets import WorksheetIdentity, query_pending_records
from src.workflow.market_messages import MarketModule
from src.workflow.service import WorkflowRuntime
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_integration import CombinedCycle
from src.workflow.v13_quotation import QuotationOutcome, RowErrorReason, V13Stopped
from tests.inso.test_v13_quotation_read import quote
from tests.workflow.test_rfq006_integration import fixture as quote_fixture
from tests.workflow.test_tp_research import build as tp_fixture
from tests.workflow.test_v13_quotation import NOW, WS, source


def assembly(tmp_path, monkeypatch, *, mode='normal', duration=10):
    backend = launcher.ProductionBackend(root=tmp_path / 'app')
    clock = SimpleNamespace(tick=0.0)
    monkeypatch.setattr(launcher, 'monotonic', lambda: clock.tick)
    monkeypatch.setattr(launcher, 'utc_now', lambda: NOW + timedelta(seconds=clock.tick))
    backend._state = RunState.RUNNING
    backend._observation = RuntimeObservation(clock=lambda: NOW + timedelta(seconds=clock.tick),
                                               timer=lambda: clock.tick)
    backend._observation.enable(quotation=True, tp=True)
    runtime = WorkflowRuntime(None, None, ())
    clock.tick = 0.0 if mode == 'all_due' else -900.0
    runtime.configure_modules({'quotation': 900, 'tp': 900, **({'inquiry': 900} if mode == 'all_due' else {})}, timer=lambda: clock.tick)
    if mode != 'all_due':
        # Prior real completion calls establish TP due at5s, mid-first query.
        assert runtime.claim_due_module() == 'quotation'
        runtime.complete_module('quotation')
        assert runtime.claim_due_module() == 'tp'
        clock.tick = -895.0
        runtime.complete_module('tp')
        clock.tick = 0.0
    if mode == 'not_due':
        runtime.reset_module('tp')
    backend._module_runtime = runtime
    db, store, reader, holds, ledger, quotes, make, observed = quote_fixture(tmp_path / 'quote', [(), ()])
    reader.rows = [source(3, '未发', model='MPN2')]
    for row in query_pending_records(reader, WS):
        store.enqueue(row, now=NOW)
    reader.rows = [source(2), source(3, model='MPN2')]
    reader.discovery_scope = nullcontext
    cleared = []
    reader.clear_discovery_snapshot = lambda: cleared.append(clock.tick)
    backend._manual_reader = reader
    backend._store, backend._v12_store = store, ledger
    backend._manual_quote = (None, holds)
    integrated = make()
    integrated.stop = backend._stop.is_set
    integrated.cycle._stop = backend._stop.is_set
    ops = integrated.cycle._operations
    events = []
    old_read = quotes.read
    def read(*args):
        assert ops.active is not None
        if not quotes.calls:
            backend._research_acquire_failure = ('quote-cache', backend._cycle_id)
        else:
            assert backend._research_acquire_failure == ('quote-cache', backend._cycle_id)
        events.append(('quote_read', clock.tick, backend._cycle_id))
        clock.tick += duration
        assert not any(e[0] == 'brief' for e in events) or len(quotes.calls) > 0
        if mode == 'auth':
            from src.inso.quotation_read import InsoQuotationAuthenticationError
            raise InsoQuotationAuthenticationError('synthetic auth')
        return old_read(*args)
    quotes.read = read
    old_observe = integrated.observe
    outer_identity = []
    def observe(result, key):
        assert ops.active is None
        old_observe(result, key)
        outer_identity.append((backend._cycle_id, backend._last_poll))
        events.append(('settled', clock.tick, backend._cycle_id))
        if mode == 'outer_pause':
            backend._module_pause_requested = V12Fault(FaultScope.V12_PAUSE, 'OUTER_PAUSE')
        if mode == 'stop_before':
            backend._stop.set()
    integrated.observe = observe
    if mode.startswith('uncertain') or mode == 'confirmed':
        # Exercise original query->actual updater->hold/notify before callback.
        from tests.workflow.test_v13_quote_update import service
        updater, _, io, actions, _ = service()
        reason = mode.split(':')[1] if ':' in mode else 'confirmed'
        if reason == 'QUOTE_FOUND':
            from src.sheets.quotation_input import QuotationInputBusy
            io.write_failures = [QuotationInputBusy('synthetic busy')]
        elif reason == 'UPDATE_RESULT_UNCONFIRMED':
            actions.popups = [RuntimeError('synthetic unconfirmed response')]
            actions.source.after = ['发给采购'] * 50
        elif reason == 'QUOTE_INPUT_READBACK_MISMATCH':
            io.readbacks = [('bad',)] * 8
        elif reason == 'SOURCE_STATUS_NOT_UPDATED':
            actions.source.after = ['发给采购'] * 50
        integrated.updater_factory = lambda: updater
        quotes.responses = iter([(quote(),), (), ()])
    tp, _, _, transport, tpdb = tp_fixture(tmp_path / 'tp', day=NOW.date())
    backend._tp = tp
    tp.stop_requested = backend._stop.is_set
    old_brief = tp.brief.read
    def brief(*args):
        assert ops.active is None
        assert any(e[0] == 'settled' for e in events)
        assert not backend._poll_idle.is_set() and not backend._manual_idle()
        if mode == 'confirmed':
            assert not actions.active and actions.closed == 1 and actions.clicks == 1
        if not any(e[0] == 'brief' for e in events):
            events.append(('brief', clock.tick, backend._cycle_id))
        return old_brief(*args)
    tp.brief.read = brief
    def research():
        backend._research_acquire_failure = ('tp-cache', backend._cycle_id)
        clock.tick += 7
        if mode == 'tp_failure':
            raise V12Fault(FaultScope.V12_PAUSE, 'SYNTHETIC_TP_PAUSE')
        if mode == 'global':
            raise V12Fault(FaultScope.GLOBAL_STOP, 'WORKFLOW_LEDGER_UNAVAILABLE')
        if mode == 'stop_inner':
            backend._stop.set()
            raise V13Stopped('STOP_REQUESTED')
    tp.research.hook = research
    for method in ('_check_site_recovery', '_refresh_dashboard_counts', '_cache_workbench', '_notify'):
        monkeypatch.setattr(backend, method, lambda *a, **k: None)
    def cleanup():
        if mode == 'cleanup' and backend._module_contexts[-1:] == ['tp']:
            raise PageTargetCleanupError(())
    monkeypatch.setattr(backend, '_close_inso_order_tab', cleanup)
    monkeypatch.setattr(backend, '_wait_between_polls', lambda _: True)
    monkeypatch.setattr(launcher, 'settle_quotation_operations', lambda: not ops.protected and ops.active is None)
    backend._manual_write_service = lambda: SimpleNamespace(operations_idle=lambda: mode != 'unsafe_google', suspend_idle_poll=nullcontext)
    lease = None
    if mode in {'same_source', 'waiting_source'}:
        runtime.configure_order_leases(2)
        runtime.request_order_lease(WorksheetIdentity('synthetic', '2026'), 10, 'outer',
                                    module_id=MarketModule.QUOTATION)
        if mode == 'same_source':
            lease = runtime.try_claim_order_lease('outer')
    def run_quote(_):
        result = (integrated.run(WS) if mode == 'no_lending' else
                  integrated.run(WS, after_closed_candidate=backend._yield_quotation_to_tp))
        if mode.endswith(':cross_scope'):
            result += make().run(WS, after_closed_candidate=backend._yield_quotation_to_tp)
        if mode in {'same_source', 'waiting_source', 'outer_pause', 'unsafe_google', 'all_due'} or mode.startswith('uncertain'):
            backend._stop.set()  # End harness without a later ordinary top-level TP poll.
        return result
    backend._combined = CombinedCycle(None, run_quote, on_pause=lambda _: None,
                                      stop_requested=backend._stop.is_set)
    def run():
        backend._run_independent_poll(runtime, {'spreadsheet_id': 'synthetic'}, None,
            SimpleNamespace(poll_scope=nullcontext), reader, (WS,), None)
    return SimpleNamespace(**locals())


@pytest.mark.parametrize('duration', [10, 600])
def test_first_real_tp_read_between_completed_candidates_and_quote_resumes(tmp_path, monkeypatch, duration):
    a = assembly(tmp_path, monkeypatch, duration=duration)
    # All enabled modules initially due; quotation wins initial FIFO tie.
    a.run()
    names = [e[0] for e in a.events]
    assert names[:4] == ['quote_read', 'settled', 'brief', 'quote_read']
    assert a.events[2][1] == duration  # No preemption of long single candidate.
    assert a.events[3][1] == duration + 7  # Original TP can delay resumed quotation.
    assert a.outer_identity[0] == a.outer_identity[1]
    assert a.events[2][2] != a.outer_identity[0][0]
    assert a.backend._cycle_id == a.outer_identity[0][0]
    assert len(a.observed) == 2 and len(a.transport.calls) == 2
    assert not a.runtime.module_resource_failed and a.cleared
    assert a.backend._observation.modules['quotation'].cycle_elapsed_seconds == 2 * duration + 7
    a.tp.brief.read = a.old_brief
    a.tp.run('synthetic', now=NOW + timedelta(minutes=15))
    assert len(a.transport.calls) == 2 and len(a.tp.research.calls) == 1


@pytest.mark.parametrize('mode', ['same_source', 'waiting_source', 'outer_pause', 'unsafe_google', 'stop_before'])
def test_no_lending_with_source_or_stop_or_pause_or_unsafe_surface(tmp_path, monkeypatch, mode):
    a = assembly(tmp_path, monkeypatch, mode=mode)
    if mode == 'stop_before':
        with pytest.raises(V13Stopped):
            a.run()
    else:
        a.run()
    assert not any(e[0] == 'brief' for e in a.events)
    assert not a.transport.calls
    if mode == 'same_source':
        assert a.runtime.order_resource_counts()['active'] == 1
        a.runtime.release_order_lease(a.lease)
    elif mode == 'waiting_source':
        assert a.runtime.cancel_order_lease_request('outer')
    if mode == 'outer_pause':
        assert a.runtime.module_plans()['quotation'][2]


@pytest.mark.parametrize('reason', ['QUOTE_FOUND', 'UPDATE_RESULT_UNCONFIRMED',
                                    'QUOTE_INPUT_READBACK_MISMATCH', 'SOURCE_STATUS_NOT_UPDATED'])
def test_actual_updater_uncertainty_latches_no_lending_on_later_safe_row(tmp_path, monkeypatch, reason):
    a = assembly(tmp_path, monkeypatch, mode='uncertain:' + reason)
    a.run()
    assert len(a.observed) == 2
    if reason == 'QUOTE_FOUND':
        assert a.observed[0][0].outcome is QuotationOutcome.QUOTE_FOUND
    else:
        assert a.observed[0][0].row_error_reason is RowErrorReason(reason)
    assert not any(e[0] == 'brief' for e in a.events)
    assert not a.transport.calls


@pytest.mark.parametrize('mode', ['tp_failure', 'global', 'cleanup', 'stop_inner', 'auth'])
def test_nested_failures_preserve_owner_stop_and_original_module_context(tmp_path, monkeypatch, mode):
    a = assembly(tmp_path, monkeypatch, mode=mode)
    if mode in {'global', 'cleanup', 'stop_inner', 'auth'}:
        with pytest.raises((V12Fault, V13Stopped)):
            a.run()
    else:
        a.run()
        assert len(a.observed) == 2
        assert a.runtime.module_plans()['tp'][2]
    if mode in {'global', 'cleanup'}:
        assert a.runtime.module_resource_failed
        assert a.backend._stop.is_set()
        assert a.backend._state is RunState.GLOBAL_STOP
    if mode != 'auth':
        assert a.backend._cycle_id == a.outer_identity[0][0]
    assert not a.backend._module_contexts
    assert len(a.transport.calls) == (2 if mode == 'cleanup' else 0)


def test_manual_default_and_actor_paths_do_not_gain_lending(tmp_path, monkeypatch):
    a = assembly(tmp_path, monkeypatch)
    a.integrated.run(WS)
    assert not any(e[0] == 'brief' for e in a.events)
    a.backend._market_actor_factory = object()
    a.backend._yield_quotation_to_tp(None)
    assert not any(e[0] == 'brief' for e in a.events)


def test_real_confirmed_update_finishes_before_tp_read(tmp_path, monkeypatch):
    a = assembly(tmp_path, monkeypatch, mode='confirmed')
    a.run()
    assert a.observed[0][0].outcome is QuotationOutcome.UPDATED_INSERTED
    assert len(a.io.writes) == a.actions.clicks == 1
    assert [e[0] for e in a.events][:4] == ['quote_read', 'settled', 'brief', 'quote_read']
    assert len(a.transport.calls) == 2


def test_stop_during_native_guard_cancels_before_tp_claim(tmp_path, monkeypatch):
    a = assembly(tmp_path, monkeypatch)
    def stop():
        a.backend._stop.set()
        return True
    a.backend._manual_write_service = lambda: SimpleNamespace(operations_idle=stop, suspend_idle_poll=nullcontext)
    with pytest.raises(V13Stopped):
        a.run()
    assert not a.tp.research.calls and not a.transport.calls
    assert not any(e[0] == 'brief' for e in a.events)


def test_only_due_tp_is_borrowed_while_other_module_stays_due(tmp_path, monkeypatch):
    a = assembly(tmp_path, monkeypatch, mode='all_due')
    a.run()
    assert any(e[0] == 'brief' for e in a.events)
    assert a.runtime.module_plans()['inquiry'] == (0, False, False)
    b = assembly(tmp_path / 'not_due', monkeypatch, mode='not_due')
    b.run()
    assert not b.tp.research.calls and not b.transport.calls


@pytest.mark.parametrize('outcome', ['SENT', 'UNKNOWN'])
def test_existing_receipts_never_replay_when_tp_is_borrowed(tmp_path, monkeypatch, outcome):
    from collections import deque

    from src.workflow.v12_contracts import DeliveryOutcome
    a = assembly(tmp_path, monkeypatch)
    spy = a.tp.brief.read
    a.tp.brief.read = a.old_brief
    for recipient in ('ops', 'owner'):
        a.transport._outcomes[recipient] = deque([DeliveryOutcome(outcome)])
    a.tp.run('synthetic', now=NOW)
    assert len(a.transport.calls) == 2 and len(a.tp.research.calls) == 1
    a.tp.brief.read = spy
    a.run()
    assert len(a.transport.calls) == 2 and len(a.tp.research.calls) == 1
    assert a.tp.store.delivery(a.tp.store.rows()[0]['task_id']) == outcome


def test_stop_after_reservation_before_run_has_no_tp_source_step(tmp_path, monkeypatch):
    a = assembly(tmp_path, monkeypatch)
    claim = a.runtime.claim_due_module
    def stop_before_dispatch(*, exclude=()):
        result = claim(exclude=exclude)
        if exclude:
            a.backend._stop.set()
        return result
    monkeypatch.setattr(a.runtime, 'claim_due_module', stop_before_dispatch)
    with pytest.raises(V13Stopped):
        a.run()
    assert not any(e[0] == 'brief' for e in a.events)
    assert not a.runtime.module_plans()['tp'][1]


def test_durable_unknown_barrier_survives_new_integrated_scope(tmp_path, monkeypatch):
    a = assembly(tmp_path, monkeypatch, mode='uncertain:SOURCE_STATUS_NOT_UPDATED:cross_scope')
    a.run()
    assert len(a.observed) == 4  # persisted hold observation plus a clean next-scope candidate
    assert a.observed[-1][0].outcome is QuotationOutcome.NO_RECENT_QUOTE
    assert a.holds.active()
    assert not any(e[0] == 'brief' for e in a.events)
    assert not a.tp.research.calls and not a.transport.calls


def test_paired_actual_domain_paths_reduce_tp_queue_and_bound_observed_quote_progress(tmp_path, monkeypatch):
    new = assembly(tmp_path / 'new', monkeypatch)
    new.run()
    old = assembly(tmp_path / 'default_off', monkeypatch, mode='no_lending')
    old.run()
    first_new = next(e[1] for e in new.events if e[0] == 'brief')
    first_old = next(e[1] for e in old.events if e[0] == 'brief')
    assert (first_new, first_old) == (10, 20)
    assert (first_new - 5, first_old - 5) == (5, 15)  # TP due mid-first query.
    assert new.events[3][:2] == ('quote_read', 17)
    assert new.backend._observation.modules['quotation'].cycle_elapsed_seconds == 27
    assert old.backend._observation.modules['quotation'].cycle_elapsed_seconds == 20
    assert len(new.observed) == len(old.observed) == 2
    assert len(new.transport.calls) == len(old.transport.calls) == 2
