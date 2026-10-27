"""Optional bounded read actors composed over the ONE WorkflowRuntime.

Not enabled by ProductionBackend. No durable queue, business write, credential
or Playwright object crosses a thread. Runtime owns admission/FIFO/deadlines;
this launcher component owns transport, fixed-thread clients and terminal drain.
"""
import re
import threading
from dataclasses import dataclass
from queue import Empty, Full, Queue
from time import monotonic

from src.research.cdp_pages import (
    PageResourceAdmission,
    PageTargetCleanupError,
    PageTargetOwnershipError,
)
from src.research.market_contracts import MarketPayloadLimitError
from src.research.runtime import ResearchMarketSession
from src.research.site_login import SITE_AUTH_RECOVERY_REASONS, SiteLoginError
from src.workflow.market_messages import (
    MarketCompletion,
    MarketFault,
    MarketFaultScope,
    MarketProgress,
    MarketReadRequest,
    MarketStage,
    MarketTerminal,
)
from src.workflow.service import OrderResourceOwnershipError, WorkflowRuntime


@dataclass(frozen=True, slots=True)
class MarketActorFault:
    actor: int
    fault: MarketFault

    def __post_init__(self):
        if (type(self.actor) is not int or not 0 <= self.actor < 2 or type(self.fault) is not MarketFault
                or self.fault.scope is not MarketFaultScope.GLOBAL_STOP):
            raise ValueError("MARKET_ACTOR_FAULT_INVALID")


def _fault(error, admission, *, initializing=False):
    current, seen, classes = error, set(), []
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        name = type(current).__name__
        classes.append(name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", name) else "UnclassifiedError")
        if isinstance(current, (PageTargetCleanupError, OrderResourceOwnershipError)):
            reason = current.reason
            page_fault = current if isinstance(current, PageTargetCleanupError) else PageTargetOwnershipError(())
            admission.invalidate(page_fault)
            return MarketFault(MarketFaultScope.GLOBAL_STOP, reason, tuple(classes[:8]))
        current = current.__cause__ or current.__context__
    try:
        admission.require_open()
    except PageTargetCleanupError as shared:
        return MarketFault(MarketFaultScope.GLOBAL_STOP, shared.reason, tuple(classes[:8]))
    if initializing or not isinstance(error, Exception):
        admission.invalidate(PageTargetOwnershipError((error,)))
        return MarketFault(MarketFaultScope.GLOBAL_STOP, 'MARKET_ACTOR_INITIALIZATION_FAILED', tuple(classes[:8]))
    code = (error.reason_code if isinstance(error, SiteLoginError) else
            getattr(error, 'reason', None) or getattr(error, 'code', None))
    if code == 'MARKET_OWNER_REQUIRED' or isinstance(error, MarketPayloadLimitError):
        return MarketFault(MarketFaultScope.SITE_DEFER, 'MARKET_OWNER_REQUIRED', tuple(classes[:8]))
    if code in SITE_AUTH_RECOVERY_REASONS:
        return MarketFault(MarketFaultScope.SITE_DEFER, 'MARKET_AUTH_REQUIRED', tuple(classes[:8]))
    return MarketFault(MarketFaultScope.FAILED, 'MARKET_SOURCE_FAILED', tuple(classes[:8]))


def _requires_auth(result):
    ordinary = result.ordinary or result.icnet_context
    if ordinary is None:
        return False
    evidence = getattr(ordinary, 'source_result', ordinary).evidence
    return any(field.key == 'failure_code' and isinstance(field.value, str)
               and field.value in SITE_AUTH_RECOVERY_REASONS
               for field in evidence.fields)


def _progress(queue, message):
    try:
        queue.put_nowait(message)
    except Full:
        pass  # Bounded observations may coalesce; terminal results may NOT drop.


def _actor_loop(index, config, admission, stopped, inbox, outbox, progress, transport_lock, session_type):
    # No Backend or WorkflowRuntime reference is passed into this worker.
    try:
        with session_type(config, admission) as session:
            while not stopped.is_set():
                request = inbox.get()
                if request is None:
                    break
                started = monotonic()
                if stopped.is_set():
                    outbox.put(MarketCompletion(request.identity, MarketTerminal.CANCELLED, started, started))
                    break
                _progress(progress, MarketProgress(request.identity, MarketStage.STARTED, started))
                try:
                    admission.require_open()
                    _progress(progress, MarketProgress(request.identity, MarketStage.READING, monotonic()))
                    result = session.read(request.query)
                    admission.require_open()  # Reject faults softened by any adapter.
                    if (result.source is not request.query.source or result.mode is not request.query.mode):
                        raise PageTargetOwnershipError((ValueError("MARKET_RESULT_IDENTITY_MISMATCH"),))
                    if _requires_auth(result):
                        terminal = MarketCompletion(request.identity, MarketTerminal.FAILED, started, monotonic(),
                            fault=MarketFault(MarketFaultScope.SITE_DEFER, 'MARKET_AUTH_REQUIRED'))
                    elif stopped.is_set():
                        terminal = MarketCompletion(request.identity, MarketTerminal.CANCELLED, started, monotonic())
                    else:
                        terminal = MarketCompletion(request.identity, MarketTerminal.SUCCEEDED, started,
                                                    monotonic(), result=result)
                except BaseException as error:  # noqa: BLE001 - worker must acknowledge cancellation
                    fault = _fault(error, admission)
                    terminal = MarketCompletion(request.identity, MarketTerminal.FAILED, started, monotonic(), fault=fault)
                    if fault.scope is MarketFaultScope.GLOBAL_STOP:
                        stopped.set()
                outbox.put(terminal)
                _progress(progress, MarketProgress(request.identity, MarketStage.FINISHED, monotonic()))
    except BaseException as error:  # noqa: BLE001 - terminal receipt must not be lost
        outbox.put(MarketActorFault(index, _fault(error, admission, initializing=True)))
        stopped.set()
    finally:
        # If Stop won before a queued request was consumed, acknowledge that it
        # never touched a page. One slot per actor means at most one such item.
        # Serialize final inbox retirement with submit. Even when a fault sets
        # Stop between commit and enqueue, the worker cannot exit its final
        # drain before that admitted producer has finished submitting/canceling.
        with transport_lock:
            try:
                request = inbox.get_nowait()
            except Empty:
                request = None
            if request is not None:
                now = monotonic()
                outbox.put(MarketCompletion(request.identity, MarketTerminal.CANCELLED, now, now))


class MarketReadActors:
    """Explicitly started optional Launcher bridge, never a new scheduler."""

    def __init__(self, runtime, config, admission, *, workers=2, session_type=ResearchMarketSession):
        if (type(runtime) is not WorkflowRuntime or not isinstance(admission, PageResourceAdmission)
                or type(workers) is not int or not 1 <= workers <= 2 or not isinstance(session_type, type)):
            raise ValueError("MARKET_ACTOR_CONFIG_INVALID")
        self._runtime, self._config, self._admission = runtime, config, admission
        self._owner, self._workers, self._session_type = threading.get_ident(), workers, session_type
        self._stop = threading.Event()
        self._transport_lock = threading.RLock()
        self._inboxes = [Queue(maxsize=1) for _ in range(workers)]
        # At most one job terminal and one client-teardown fault per actor.
        self._outbox = Queue(maxsize=workers * 2)
        self._progress = Queue(maxsize=workers * 4)
        self._threads, self._slots = [], {}
        self._blocked_sources = set()
        self._owner_required_sources = set()
        self._paused = False
        self._started = False
        self._faults = []

    def _check_owner(self):
        if threading.get_ident() != self._owner:
            raise OrderResourceOwnershipError()

    @property
    def admission(self):
        return self._admission

    @property
    def stopped(self):
        return self._stop.is_set()

    def require_owner_resources(self, runtime):
        self._check_owner()
        if runtime is not self._runtime or not self._started:
            raise OrderResourceOwnershipError()
        try:
            self._admission.require_open()
        except PageTargetCleanupError as error:
            runtime.fail_market_reads(_fault(error, self._admission))
            self.request_stop()
            raise
        if runtime.module_resource_failed:
            raise OrderResourceOwnershipError()
        if self._stop.is_set():
            raise RuntimeError("MARKET_ACTORS_STOPPED")

    def invalidate_owner_result(self):
        self._check_owner()
        error = PageTargetOwnershipError(())
        self._admission.invalidate(error)
        self._runtime.fail_market_reads(_fault(error, self._admission))
        self.request_stop()

    def site_deferred(self, source):
        self._check_owner()
        return source in self._blocked_sources

    def requires_owner(self, source):
        self._check_owner()
        return source in self._owner_required_sources

    def recover_sites_on_owner(self, sweep):
        """Explicit original Owner recovery, reusing the canonical login sweep.

        Not a worker login, timer or automatic unverified unblock. Any active
        market pages must first acknowledge terminal cleanup. Failed/manual
        verdicts preserve the block and protected pages; only exact successful
        canonical site verdicts re-admit that source.
        """
        from src.gui.contracts import SiteLoginOutcome, SiteLoginResult
        from src.research.source_contracts import ResearchSource
        self.require_owner_resources(self._runtime)
        if not self.quiescent:
            return ()
        prior, self._paused = self._paused, True
        try:
            results = sweep()  # Original Owner callback, NEVER sent to workers.
            self.require_owner_resources(self._runtime)
            if (type(results) is not tuple or any(type(r) is not SiteLoginResult for r in results)
                    or len({r.site for r in results}) != len(results)):
                raise ValueError("MARKET_RECOVERY_VERDICT_INVALID")
            labels = {'IC 现货网': ResearchSource.IC_NET, 'Findchips': ResearchSource.FINDCHIPS,
                      '华强电子网': ResearchSource.HQEW, '立创商城': ResearchSource.LCSC}
            recovered = []
            for result in results:
                source = labels.get(result.site)
                if (source in self._blocked_sources and source not in self._owner_required_sources
                        and result.outcome in {SiteLoginOutcome.ALREADY_SIGNED_IN, SiteLoginOutcome.SIGNED_IN}):
                    self._blocked_sources.remove(source)
                    recovered.append(source)
            return tuple(recovered)
        except BaseException as error:
            fault = _fault(error, self._admission)
            if fault.scope is MarketFaultScope.GLOBAL_STOP:
                self._runtime.fail_market_reads(fault)
                self.request_stop()
            raise
        finally:
            self._paused = prior

    def owner_source_available(self, source):
        """Owner-side canonical read cannot race a worker's same-site query."""
        self._check_owner()
        return source not in {request.query.source for request, _ in self._slots.values()}

    def start(self):
        self._check_owner()
        if self._started or self._stop.is_set():
            raise RuntimeError("MARKET_ACTORS_ALREADY_STARTED_OR_STOPPED")
        self._admission.require_open()
        self._runtime.configure_market_reads(self._workers)
        self._started = True
        try:
            for index, inbox in enumerate(self._inboxes):
                thread = threading.Thread(target=_actor_loop,
                    args=(index, self._config, self._admission, self._stop, inbox,
                          self._outbox, self._progress, self._transport_lock, self._session_type),
                    name=f'market-read-{index}', daemon=False)
                thread.start()
                self._threads.append(thread)
        except BaseException as error:
            self._admission.invalidate(PageTargetOwnershipError((error,)))
            self._runtime.fail_market_reads(MarketFault(MarketFaultScope.GLOBAL_STOP,
                'MARKET_ACTOR_INITIALIZATION_FAILED', (type(error).__name__,)))
            self.request_stop()
            raise

    def admit(self, request):
        self._check_owner()
        if not self._started or self._stop.is_set():
            return False
        if type(request) is not MarketReadRequest:
            raise ValueError("MARKET_REQUEST_INVALID")
        self._admission.require_open()
        accepted = self._runtime.admit_market_read(request)
        if accepted:
            _progress(self._progress, MarketProgress(request.identity, MarketStage.QUEUED, monotonic()))
        return accepted

    def dispatch_ready(self):
        """Returns immediately; never waits on a Research batch or source query."""
        self._check_owner()
        with self._transport_lock:
            return self._dispatch_ready_locked()

    def _dispatch_ready_locked(self):
        if not self._started or self._stop.is_set() or self._paused:
            return 0
        self._admission.require_open()
        dispatched = 0
        for index, inbox in enumerate(self._inboxes):
            if index in self._slots:
                continue
            # Conservatively serialize same-site queries; different sites overlap.
            blocked = self._blocked_sources | {r.query.source for r, _ in self._slots.values()}
            claimed = self._runtime.claim_market_read(blocked_sources=blocked)
            if claimed is None:
                break
            request, lease = claimed
            if not self._runtime.commit_market_dispatch(request, lease):
                continue
            self._slots[index] = request, lease
            try:
                inbox.put_nowait(request)
            except Full:
                # Submission did not occur: exact owner supplies a cancellation
                # terminal instead of freeing a possibly active foreign job.
                now = monotonic()
                completion = MarketCompletion(request.identity, MarketTerminal.CANCELLED, now, now)
                self._runtime.acknowledge_market_terminal(completion)
                del self._slots[index]
                raise RuntimeError("MARKET_INBOX_NOT_EMPTY") from None
            dispatched += 1
        return dispatched

    def request_stop(self):
        """Thread-safe signal only; scheduler owner performs lease drain."""
        with self._transport_lock:
            self._stop.set()
            for inbox in self._inboxes:
                try:
                    inbox.put_nowait(None)
                except Full:
                    pass  # Worker finally acknowledges the unconsumed request.

    def drain(self):
        self._check_owner()
        if not self._started:
            return ()
        completed = []
        while True:
            try:
                message = self._outbox.get_nowait()
            except Empty:
                break
            if type(message) is MarketActorFault:
                self._faults.append(message.fault)
                self._runtime.fail_market_reads(message.fault)
                self.request_stop()
                # Worker emits separate cancellation for an unconsumed job.
                continue
            index = next((i for i, (r, _) in self._slots.items()
                          if r.identity == message.identity), None)
            if index is None:
                self._admission.invalidate(PageTargetOwnershipError(()))
                self.request_stop()
                raise OrderResourceOwnershipError()
            request, _ = self._slots[index]
            self._runtime.acknowledge_market_terminal(message)
            del self._slots[index]
            if message.fault is not None:
                if message.fault.scope is MarketFaultScope.GLOBAL_STOP:
                    self._faults.append(message.fault)
                    self.request_stop()
                elif message.fault.scope is MarketFaultScope.SITE_DEFER:
                    self._blocked_sources.add(request.query.source)
                    if message.fault.reason == 'MARKET_OWNER_REQUIRED':
                        self._owner_required_sources.add(request.query.source)
            completed.append(message)
        if self._stop.is_set():
            self._runtime.close_market_reads()
        return tuple(completed)

    def take_progress(self):
        self._check_owner()
        messages = []
        while True:
            try:
                messages.append(self._progress.get_nowait())
            except Empty:
                return tuple(messages)

    def pause_dispatch(self):
        self._check_owner()
        self._paused = True

    @property
    def quiescent(self):
        return not self._slots

    @property
    def faults(self):
        return tuple(self._faults)

    def close(self, *, timeout=10):
        """Bounded normal drain only; never terminates a worker or Chrome."""
        self._check_owner()
        self.request_stop()
        deadline = monotonic() + timeout
        while any(thread.is_alive() for thread in self._threads) and monotonic() < deadline:
            self.drain()
            for thread in self._threads:
                thread.join(timeout=0.01)
        self.drain()
        return not self._slots and not any(thread.is_alive() for thread in self._threads)
