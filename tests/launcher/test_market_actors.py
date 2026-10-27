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



def test_submission_refusal_after_commit_acknowledges_unsubmitted_request(monkeypatch):
    from queue import Full
    runtime, _, actors = setup_actors()
    original = actors._inboxes[0].put_nowait
    def refuse_job(message):
        if message is not None:
            raise Full
        return original(message)
    monkeypatch.setattr(actors._inboxes[0], 'put_nowait', refuse_job)
    try:
        assert actors.admit(request('slow'))
        with pytest.raises(RuntimeError, match='MARKET_INBOX_NOT_EMPTY'):
            actors.dispatch_ready()
        assert runtime.order_resource_counts()['active'] == 0
        assert not Session.read_events['slow'].is_set()
    finally:
        assert actors.close()


@pytest.mark.parametrize('_iteration', range(20))
def test_stop_after_commit_before_queue_submission_never_executes_request(monkeypatch, _iteration):
    runtime, _, actors = setup_actors()
    original = actors._inboxes[0].put_nowait
    def stop_in_gap(message):
        if message is not None:
            actors.request_stop()
        return original(message)
    monkeypatch.setattr(actors._inboxes[0], 'put_nowait', stop_in_gap)
    try:
        assert actors.admit(request('slow'))
        # Depending on the worker consuming Stop's sentinel, the job is either
        # rejected before submission or acknowledged canceled by worker finally.
        try:
            actors.dispatch_ready()
        except RuntimeError as error:
            assert str(error) == 'MARKET_INBOX_NOT_EMPTY'
        assert actors.close()
        assert not Session.read_events['slow'].is_set()
        assert runtime.order_resource_counts()['active'] == 0
    finally:
        assert actors.close()



def test_initializer_fault_cannot_exit_before_already_committed_enqueue_is_reconciled(monkeypatch):
    barrier = threading.Barrier(3)
    fail = threading.Event()
    class FailingInitializer:
        def __init__(self, *_args):
            pass
        def __enter__(self):
            barrier.wait(timeout=3)
            assert fail.wait(3)
            raise RuntimeError('synthetic initializer failure')
        def __exit__(self, *_exc):
            return False
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({'quotation': 900, 'tp': 900})
    actors = MarketReadActors(runtime, None, PageResourceAdmission(), session_type=FailingInitializer)
    actors.start()
    barrier.wait(timeout=3)
    original = actors._inboxes[0].put_nowait
    def fault_in_submission_gap(message):
        if message is not None:
            fail.set()
            assert actors._stop.wait(3)  # Failure reached immutable terminal boundary.
        return original(message)
    monkeypatch.setattr(actors._inboxes[0], 'put_nowait', fault_in_submission_gap)
    try:
        assert actors.admit(request('slow'))
        actors.dispatch_ready()
        assert actors.close()
        assert runtime.module_resource_failed
        assert runtime.order_resource_counts()['active'] == 0
        assert actors.faults
    finally:
        fail.set()
        actors.close()



@pytest.mark.parametrize('code', ['MANUAL_VERIFICATION_REQUIRED', 'SESSION_STALE', 'SECURITY_EVENT',
    'OTP_REQUIRED', 'VERIFIED_SESSION_LEASE_REQUIRED', 'SESSION_IDENTITY_UNVERIFIED', 'LOGIN_REQUIRED',
    'LOGIN_NOT_CONFIRMED', 'LOGIN_CONTROL_AMBIGUOUS'])
@pytest.mark.parametrize('returned', [False, True])
def test_canonical_auth_reason_never_becomes_ordinary_source_success(code, returned):
    from src.research.source_contracts import EvidenceField
    from src.workflow.market_messages import MarketFaultScope
    class AuthBlocked(Session):
        def read(self, query):
            if not returned:
                class CanonicalError(RuntimeError):
                    pass
                error = CanonicalError('private text must not leave this thread')
                error.code = code
                raise error
            result = SourceResult(query.source, SourceOutcome.SOURCE_UNAVAILABLE,
                SourceEvidence(query.source, query.mpn, None, SourceOutcome.SOURCE_UNAVAILABLE,
                    query.reference_at, fields=(EvidenceField('failure_code', code),)))
            return MarketReadResult(query.source, query.mode, ordinary=result)
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({'quotation': 900, 'tp': 900})
    admission = PageResourceAdmission()
    actors = MarketReadActors(runtime, None, admission, session_type=AuthBlocked)
    actors.start()
    try:
        assert actors.admit(request('fault'))
        actors.dispatch_ready()
        completion = drain_until(actors, 1)[0]
        assert completion.terminal is MarketTerminal.FAILED
        assert completion.result is None
        assert completion.fault.scope is MarketFaultScope.SITE_DEFER
        assert completion.fault.reason == 'MARKET_AUTH_REQUIRED'
        assert ResearchSource.HQEW in actors._blocked_sources
        assert not runtime.module_resource_failed
        assert runtime.order_resource_counts()['active'] == 0
        admission.require_open()  # Recover only this site through original owner.
    finally:
        assert actors.close()


@pytest.mark.parametrize('code', ['SOURCE_UNAVAILABLE', 'READ_EMPTY', 'AUTHENTICATED_READ_UNAVAILABLE', 'LOGINish_private_text'])
def test_unknown_or_read_failure_code_is_not_guessed_as_auth(code):
    from src.launcher.market_actors import _fault
    from src.workflow.market_messages import MarketFaultScope
    class Failure(RuntimeError):
        pass
    error = Failure()
    error.code = code
    fault = _fault(error, PageResourceAdmission())
    assert fault.scope is MarketFaultScope.FAILED


@pytest.mark.parametrize('code', ['MANUAL_VERIFICATION_REQUIRED', 'SESSION_STALE',
    'SESSION_IDENTITY_UNVERIFIED', 'OTP_REQUIRED', 'SECURITY_EVENT', 'LOGIN_NOT_CONFIRMED'])
def test_direct_native_site_login_error_defers_site_and_acknowledges_resource(code):
    from src.research.site_login import SiteLoginError
    from src.workflow.market_messages import MarketFaultScope
    class NativeAuthBlocked(Session):
        def read(self, query):
            raise SiteLoginError(code)
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({'quotation': 900, 'tp': 900})
    admission = PageResourceAdmission()
    actors = MarketReadActors(runtime, None, admission, session_type=NativeAuthBlocked)
    actors.start()
    try:
        assert actors.admit(request('native-auth'))
        assert actors.dispatch_ready() == 1
        completion, = drain_until(actors, 1)
        assert completion.terminal is MarketTerminal.FAILED and completion.result is None
        assert completion.fault.scope is MarketFaultScope.SITE_DEFER
        assert completion.fault.reason == 'MARKET_AUTH_REQUIRED'
        assert completion.fault.exception_classes == ('SiteLoginError',)
        assert ResearchSource.HQEW in actors._blocked_sources
        assert runtime.order_resource_counts()['active'] == 0
        assert not runtime.module_resource_failed
        admission.require_open()
    finally:
        assert actors.close()


@pytest.mark.parametrize('code', ['READ_EMPTY', 'AUTHENTICATED_READ_UNAVAILABLE', 'LOGINish_private_text'])
def test_native_non_auth_reason_and_untyped_reason_code_not_inferred(code):
    from src.launcher.market_actors import _fault
    from src.research.site_login import SiteLoginError
    from src.workflow.market_messages import MarketFaultScope
    assert _fault(SiteLoginError(code), PageResourceAdmission()).scope is MarketFaultScope.FAILED
    foreign = RuntimeError('MANUAL_VERIFICATION_REQUIRED')
    foreign.reason_code = 'MANUAL_VERIFICATION_REQUIRED'
    assert _fault(foreign, PageResourceAdmission()).scope is MarketFaultScope.FAILED


def test_native_site_login_error_during_initialization_remains_global_stop():
    from src.launcher.market_actors import _fault
    from src.research.site_login import SiteLoginError
    from src.workflow.market_messages import MarketFaultScope
    fault = _fault(SiteLoginError('OTP_REQUIRED'), PageResourceAdmission(), initializing=True)
    assert fault.scope is MarketFaultScope.GLOBAL_STOP
    assert fault.reason == 'MARKET_ACTOR_INITIALIZATION_FAILED'
