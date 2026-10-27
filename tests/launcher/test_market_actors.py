"""Isolated actual thread/queue paths, NOT real-browser/business acceptance."""
import threading
from dataclasses import replace
from datetime import UTC, datetime
from time import monotonic

import pytest

from src.launcher.market_actors import MarketReadActors
from src.research.cdp_pages import PageResourceAdmission, PageTargetOwnershipError
from src.research.icnet import IcNetResult
from src.research.market_contracts import (
    MarketReadMode,
    MarketReadQuery,
    MarketReadResult,
)
from src.research.source_contracts import (
    ResearchSource,
    SourceEvidence,
    SourceOutcome,
    SourceResult,
)
from src.sheets.pending import (
    IdentifyingSnapshot,
    SheetRecordIdentity,
    WorksheetIdentity,
)
from src.workflow.market_messages import (
    MarketModule,
    MarketReadRequest,
    MarketTaskIdentity,
    MarketTerminal,
)
from src.workflow.service import WorkflowRuntime


def request(token, module=MarketModule.QUOTATION, row=1, source=ResearchSource.HQEW, due=0):
    record = SheetRecordIdentity(WorksheetIdentity('synthetic', '2026'), row,
                                IdentifyingSnapshot('pending', None, 'SYNTHETIC', None, 10))
    identity = MarketTaskIdentity(module, 'cycle-' + token, token, 'domain-' + token, record)
    mode = MarketReadMode.TP_OFFERS if module is MarketModule.TP else MarketReadMode.ORDINARY
    query = MarketReadQuery(source, mode, token, 10, datetime(2026, 10, 27, tzinfo=UTC))
    return MarketReadRequest(identity, query, due, monotonic())


class Session:
    entered = None
    release = None
    read_events = None
    threads = None
    fault = None

    def __init__(self, config, admission):
        self.owner = threading.get_ident()
        self.admission = admission
        Session.threads.add(self.owner)

    def __enter__(self):
        return self

    def read(self, query):
        assert self.owner == threading.get_ident()
        Session.read_events[query.mpn].set()
        if query.mpn == 'slow':
            assert Session.release.wait(5)
        if Session.fault is not None and query.mpn == 'fault':
            raise Session.fault
        if query.mode is MarketReadMode.TP_OFFERS:
            return MarketReadResult(query.source, query.mode, offers=())
        result = SourceResult(query.source, SourceOutcome.NO_VALID_PRICE,
            SourceEvidence(query.source, query.mpn, None, SourceOutcome.NO_VALID_PRICE, query.reference_at))
        return MarketReadResult(query.source, query.mode,
                                ordinary=IcNetResult(result) if query.source is ResearchSource.IC_NET else result)

    def __exit__(self, *_exc):
        assert self.owner == threading.get_ident()
        return False


def setup_actors():
    Session.entered = threading.Event()
    Session.release = threading.Event()
    Session.read_events = {name: threading.Event() for name in ('slow', 'tp', 'same', 'fault', 'queued')}
    Session.threads = set()
    Session.fault = None
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({'inquiry': 900, 'quotation': 900, 'tp': 900})
    admission = PageResourceAdmission()
    actors = MarketReadActors(runtime, None, admission, session_type=Session)
    actors.start()
    return runtime, admission, actors


def drain_until(actors, count):
    finished = []
    deadline = monotonic() + 5
    while len(finished) < count and monotonic() < deadline:
        finished.extend(actors.drain())
        # A finite test wait, not an added production scheduler/monitor.
        threading.Event().wait(0.005)
    assert len(finished) == count
    return finished


def test_long_query_does_not_block_nonblocking_dispatch_or_independent_tp_result():
    runtime, _, actors = setup_actors()
    try:
        assert actors.admit(request('slow'))
        assert actors.dispatch_ready() == 1
        assert Session.read_events['slow'].wait(2)
        assert actors.admit(request('tp', MarketModule.TP, 2, ResearchSource.LCSC))
        assert actors.dispatch_ready() == 1  # no wait for slow quotation
        assert Session.read_events['tp'].wait(2)
        completed = drain_until(actors, 1)
        assert completed[0].identity.module is MarketModule.TP
        assert not Session.release.is_set()
        assert runtime.order_resource_counts()['active'] == 1
        Session.release.set()
        assert drain_until(actors, 1)[0].identity.module is MarketModule.QUOTATION
        assert 1 <= len(Session.threads) <= 2
    finally:
        Session.release.set()
        assert actors.close()


def test_same_original_row_never_dispatches_second_module_before_terminal_ack():
    runtime, _, actors = setup_actors()
    try:
        assert actors.admit(request('slow'))
        assert actors.admit(request('same', MarketModule.TP, 1, ResearchSource.LCSC))
        assert actors.dispatch_ready() == 1
        assert Session.read_events['slow'].wait(2)
        assert not Session.read_events['same'].is_set()
        assert actors.dispatch_ready() == 0
        Session.release.set()
        drain_until(actors, 1)
        assert actors.dispatch_ready() == 1
        assert Session.read_events['same'].wait(2)
        drain_until(actors, 1)
        assert runtime.order_resource_counts()['active'] == 0
    finally:
        Session.release.set()
        assert actors.close()


def test_stop_cancels_unsubmitted_and_drains_submitted_without_repeat():
    runtime, _, actors = setup_actors()
    try:
        assert actors.admit(request('slow'))
        assert actors.admit(request('queued', MarketModule.TP, 2, ResearchSource.HQEW))
        assert actors.dispatch_ready() == 1
        assert Session.read_events['slow'].wait(2)
        actors.request_stop()
        assert actors.dispatch_ready() == 0
        assert not actors.admit(request('tp', MarketModule.TP, 3, ResearchSource.LCSC))
        actors.drain()
        Session.release.set()
        completed = drain_until(actors, 1)
        assert completed[0].terminal is MarketTerminal.CANCELLED
        assert not Session.read_events['queued'].is_set()
        assert runtime.order_resource_counts()['active'] == 0
    finally:
        Session.release.set()
        assert actors.close()


def test_missing_native_lease_fault_crosses_thread_and_closes_shared_runtime():
    runtime, admission, actors = setup_actors()
    Session.fault = PageTargetOwnershipError((ValueError('synthetic missing lease'),))
    try:
        assert actors.admit(request('fault'))
        actors.dispatch_ready()
        assert Session.read_events['fault'].wait(2)
        completed = drain_until(actors, 1)
        assert completed[0].fault.reason == 'CDP_PAGE_OWNERSHIP_UNCONFIRMED'
        assert runtime.module_resource_failed
        with pytest.raises(PageTargetOwnershipError):
            admission.require_open()
        assert actors.dispatch_ready() == 0
        assert runtime.order_resource_counts()['active'] == 0
    finally:
        assert actors.close()


def test_coordinator_dispatch_requires_terminal_before_lease_release_and_rejects_wrong_cycle():
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({'quotation': 900, 'tp': 900})
    runtime.configure_market_reads(2)
    item = request('slow')
    assert runtime.admit_market_read(item)
    claimed, lease = runtime.claim_market_read()
    assert runtime.commit_market_dispatch(claimed, lease)
    with pytest.raises(RuntimeError, match='MARKET_TERMINAL_UNACKNOWLEDGED'):
        runtime.release_order_lease(lease)
    from src.workflow.market_messages import MarketCompletion
    terminal = MarketCompletion(item.identity, MarketTerminal.CANCELLED, 1, 1)
    from src.workflow.service import OrderResourceOwnershipError
    with pytest.raises(OrderResourceOwnershipError):
        runtime.acknowledge_market_terminal(replace(terminal,
            identity=replace(item.identity, cycle_id='foreign-cycle')))
    runtime.acknowledge_market_terminal(terminal)
    assert runtime.order_resource_counts()['active'] == 0



def test_actor_initialization_failure_latches_runtime_even_without_an_active_job():
    class Broken(Session):
        def __enter__(self):
            raise RuntimeError('synthetic attach failure')
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({'tp': 900})
    admission = PageResourceAdmission()
    actors = MarketReadActors(runtime, None, admission, session_type=Broken)
    actors.start()
    deadline = monotonic() + 2
    while not actors.faults and monotonic() < deadline:
        actors.drain()
        threading.Event().wait(0.005)
    assert actors.faults
    assert runtime.module_resource_failed
    assert actors.close()


def test_icnet_existing_pacing_is_shared_across_clients_without_blocking_other_sites():
    from src.research.icnet import ICNET_MIN_INTERVAL_SECONDS
    from src.workflow.market_messages import MarketCompletion
    clock = [100.0]
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({'quotation': 900, 'tp': 900}, timer=lambda: clock[0])
    runtime.configure_market_reads(2)
    item = request('first', source=ResearchSource.IC_NET)
    assert runtime.admit_market_read(item)
    original, lease = runtime.claim_market_read()
    assert runtime.commit_market_dispatch(original, lease)
    runtime.acknowledge_market_terminal(MarketCompletion(item.identity, MarketTerminal.CANCELLED, 100, 100))
    other = request('tp', MarketModule.TP, 2, ResearchSource.IC_NET)
    independent = request('same', MarketModule.QUOTATION, 3, ResearchSource.HQEW)
    assert runtime.admit_market_read(other) and runtime.admit_market_read(independent)
    assert runtime.claim_market_read()[0] == independent
    assert runtime.claim_market_read() is None
    clock[0] += ICNET_MIN_INTERVAL_SECONDS
    assert runtime.claim_market_read()[0] == other
    runtime.close_market_reads()  # Both are reserved, never dispatched.
    assert runtime.order_resource_counts()['active'] == 0


def test_stop_before_actor_start_cannot_rearm_existing_bridge():
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({'tp': 900})
    actors = MarketReadActors(runtime, None, PageResourceAdmission(), session_type=Session)
    actors.request_stop()
    assert actors.close()
    with pytest.raises(RuntimeError):
        actors.start()



def test_initialization_auth_fault_is_global_not_unacknowledged_site_defer():
    from src.launcher.market_actors import _fault
    from src.workflow.market_messages import MarketFaultScope
    admission = PageResourceAdmission()
    class AuthError(RuntimeError):
        code = 'LOGIN_REQUIRED'
    fault = _fault(AuthError(), admission, initializing=True)
    assert fault.scope is MarketFaultScope.GLOBAL_STOP
    assert fault.reason == 'MARKET_ACTOR_INITIALIZATION_FAILED'
    with pytest.raises(PageTargetOwnershipError):
        admission.require_open()


def test_runtime_reconfiguration_cannot_change_actor_lifecycle_or_pacing():
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({'quotation': 900})
    runtime.configure_market_reads(2)
    with pytest.raises(RuntimeError, match='MARKET_COORDINATOR_ALREADY_CONFIGURED'):
        runtime.configure_modules({'tp': 900})
    with pytest.raises(RuntimeError, match='MARKET_COORDINATOR_ALREADY_CONFIGURED'):
        runtime.configure_order_leases(20)
