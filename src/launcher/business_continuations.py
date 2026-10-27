"""Launcher assembly of original module continuations over ONE WorkflowRuntime.

No timer/thread/ledger here. Existing owner poll thread calls this cooperative
loop; fixed market actors own only immutable read queries. Production default
remains off until explicit reviewed assembly selection, never a config bypass.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
from time import monotonic
from uuid import uuid4

from src.research.source_contracts import ResearchSource
from src.sheets.brand_write import SheetRecordConflict
from src.sheets.pending import identify_worksheet_row
from src.sheets.tp_brief import TpLocalError
from src.workflow.market_messages import (
    MarketFault,
    MarketFaultScope,
    MarketModule,
    MarketTaskIdentity,
)
from src.workflow.service import OrderResourceOwnershipError
from src.workflow.tp_research import task_key, tp_local_failure_reason
from src.workflow.v12_contracts import BusinessState
from src.workflow.v13_quotation import V13QuotationResult, V13SourceRowError

from .market_continuation import (
    MarketContinuationCancelled,
    MarketContinuationFault,
    OwnerMarketResearch,
)


@dataclass
class _ModuleRun:
    module: str
    cycle: str
    started_at: object
    started: float
    orders: object = field(repr=False)
    current: object = field(default=None, repr=False)
    identity: object = field(default=None, repr=False)
    work: object = field(default=None, repr=False)
    research: object = field(default=None, repr=False)
    receipts: tuple = ()
    quote_result: object = field(default=None, repr=False)
    acquire_failure: object = field(default=None, repr=False)
    pause: object = field(default=None, repr=False)


def run_business_continuations(backend, runtime, cfg, rc, web, reader, worksheets, episodes):
    """Actual domain ports; optional explicit composition, not live acceptance."""
    from .backend import utc_now
    from .v13_quotation import quotation_operation_scope
    actors = backend._market_actor_factory(runtime, rc, backend._page_admission,
                                           business_continuations=True)
    backend._market_actors = actors
    active, busy, draining = {}, set(), []
    notified_revision = -1
    observation = backend._observation
    prior_parallel = observation.concurrent_modules
    observation.concurrent_modules = True

    @contextmanager
    def scope():
        with web.poll_scope(), quotation_operation_scope(), reader.discovery_scope():
            yield

    @contextmanager
    def context(run):
        parent = (backend._cycle_id, backend._last_poll, backend._research_acquire_failure,
                  backend._module_pause_requested)
        backend._cycle_id, backend._last_poll = run.cycle, run.started_at
        backend._research_acquire_failure, backend._module_pause_requested = run.acquire_failure, run.pause
        backend._module_contexts.append(run.module)
        try:
            with observation.module_scope(run.module):
                yield
        finally:
            run.acquire_failure, run.pause = backend._research_acquire_failure, backend._module_pause_requested
            backend._module_contexts.pop()
            (backend._cycle_id, backend._last_poll, backend._research_acquire_failure,
             backend._module_pause_requested) = parent

    def orders(module):
        waiting = actors.deferred_auth_sources
        if waiting and actors.quiescent:
            backend._close_inso_order_tab()
            sites = {'ic.net': 'icnet', 'findchips': 'findchips', 'hqew': 'hqew', 'lcsc': 'lcsc'}
            selected = frozenset(sites[source.value] for source in waiting if source.value in sites)
            if selected:
                actors.recover_sites_on_owner(lambda: backend._run_login_sweep(
                    background=True, only_sites=selected))
        if module == 'inquiry':
            flow = backend._v12_composition.coordinator
            flow.begin_poll_cycle()
            for worksheet in worksheets:
                records = flow.discover_pending(reader, worksheet, now=utc_now())
                records, held, _ = flow.prepare_pending(records, now=utc_now())
                for record in records:
                    key = flow._workflow_store.inquiry_id_for(record.record_identity)
                    item = flow._workflow_store.get_by_inquiry_id(key)
                    state = flow._v12_store.business_state(key)
                    if (key not in held and item.status.value in {'QUEUED', 'RETRY_WAIT'}
                            and item.next_attempt_at is not None and item.next_attempt_at <= utc_now()
                            and state not in {BusinessState.INTERRUPTED_UNSENT,
                                BusinessState.INTERRUPTED_POSSIBLY_SENT, BusinessState.HUMAN_COMPLETED,
                                BusinessState.SOURCE_CHANGED}):
                        yield (record, key, record.record_identity)
        elif module == 'tp':
            pending = backend._tp.read_continuation_orders(cfg['spreadsheet_id'], now=utc_now())
            for order in pending:
                key = task_key(order.spreadsheet, order.sheet, order.row)
                try:
                    source = backend._tp.continuation_source(order)
                except ValueError as error:
                    reason = tp_local_failure_reason(error)
                    if not reason:
                        raise
                    backend._tp.issues[key] = reason
                    continue
                yield (order, key, source)
        else:
            for worksheet in worksheets:
                integrated = backend._quotation_factory(worksheet)
                records, blocked_ids, blocked_rows = integrated.prepare_run(worksheet)
                candidates = integrated.cycle.read_candidates(worksheet)
                rows = {row.row_position: row for row in reader.read_rows(worksheet)}
                for candidate in candidates:
                    if candidate.inquiry_id in blocked_ids or candidate.source_row_position in blocked_rows:
                        continue
                    if isinstance(candidate, V13QuotationResult):
                        integrated.settle_result(candidate, records)
                        continue  # Canonical operational hold, no invented inquiry ID.
                    row = rows.get(candidate.source_row_position)
                    if row is None:
                        continue
                    yield ((integrated, candidate, records), candidate.inquiry_id,
                           identify_worksheet_row(worksheet, row))


    def finish(run, error=None):
        # Reuse the original backend's exact fault/defer/three-hour/cleanup policy
        # and original module deadline completion. No parallel failure policy.
        previous = backend._module_execute
        def terminal(_module):
            if error is not None:
                raise error
            if run.pause is not None:
                raise run.pause
        backend._module_execute = terminal
        try:
            with context(run):
                backend._run_independent_job(run.module, started=run.started)
        finally:
            backend._module_execute = previous
            if run.work is not None and runtime.business_continuation_active(run.work.lease):
                draining.append(run)  # fatal path still owes acknowledged owner cleanup
            elif run.identity is not None and run.work is None:
                runtime.cancel_business_request(run.identity)
            active.pop(run.module, None)

    def cancel_work(run, *, defer=None):
        with context(run):
            return cancel_work_scoped(run, defer=defer)

    def cancel_work_scoped(run, *, defer=None):
        if run.work is not None and not runtime.business_continuation_active(run.work.lease):
            run.work = run.research = None  # domain already confirmed its terminal
        if run.work is None:
            if run.identity is not None:
                runtime.cancel_business_request(run.identity)
            return
        if defer is not None and run.module == 'inquiry':
            run.work.defer(defer)
        elif defer is not None and run.module == 'tp':
            run.work.fail()
        else:
            run.work.cancel()
        run.work = run.research = None

    def close_owner_read_phase():
        # Market waits must never retain another task's protected INSO access.
        # Do not repeatedly park Chrome while a read is simply still pending.
        if backend._inso_session is not None or backend._active_inso_inquiry is not None:
            backend._close_inso_order_tab()

    def prepare_owner_inso(run):
        backend._begin_inso_inquiry(run.identity.domain_task_id)
        backend._ensure_research_ready(rc, cfg)

    def step(run):
        with context(run), scope():
            actors.require_owner_resources(runtime)
            if run.work is not None:
                if run.module == 'quotation':
                    if run.quote_result is None:
                        observation.stage(run.module, '查询受保护历史报价', site='INSO',
                                          order_ref=run.identity.domain_task_id)
                        run.quote_result = run.work.read_owner()
                        return
                    observation.stage(run.module, '接续报价结果并核验来源',
                                      order_ref=run.identity.domain_task_id)
                    run.work.complete(run.quote_result)
                    run.quote_result = None
                else:
                    if run.work.research.source is ResearchSource.INSO:
                        prepare_owner_inso(run)
                    try:
                        result = run.research.advance(run.receipts)
                    finally:
                        close_owner_read_phase()
                    run.receipts = ()
                    if result is None:
                        return
                    actors.require_owner_resources(runtime)
                    observation.stage(run.module, '接续业务结果并核验来源',
                                      order_ref=run.identity.domain_task_id)
                    if run.module == 'inquiry':
                        prepare_owner_inso(run)  # rebind before original purchase route
                    run.work.complete(result)
                backend._close_inso_order_tab()
                run.work = run.research = run.current = run.identity = None
                return
            if run.current is None:
                try:
                    run.current = next(run.orders)
                except StopIteration:
                    if run.module == 'inquiry':
                        backend._purchase_completion.retry_saved_statuses(at=utc_now())
                        backend._idle_login_tick(now=utc_now())
                    elif run.module == 'tp':
                        backend._tp.store.record_issues(backend._tp.issues, utc_now())
                        if backend._tp.issues:
                            backend._append_log('WARNING', f'TP 有 {len(backend._tp.issues)} 条待核对，其他任务继续。')
                    finish(run)
                    return
                item, key, source = run.current
                run.identity = MarketTaskIdentity(MarketModule(run.module), run.cycle,
                    'business_' + uuid4().hex, key, source)
            if not runtime.business_admission_ready(run.identity):
                observation.wait(run.module, '等待来源订单资源')
                return
            item = run.current[0]
            observation.stage(run.module, '核验原始订单并准备调研', order_ref=run.identity.domain_task_id)
            if run.module == 'inquiry':
                run.work = backend._v12_composition.coordinator.begin_continuation(
                    item, run.identity, runtime, reader, now=utc_now())
            elif run.module == 'tp':
                run.work = backend._tp.begin_continuation(item, run.identity, runtime, now=utc_now())
            else:
                integrated, candidate, records = item
                run.work = integrated.begin_continuation(candidate, run.identity, runtime, records)
            if run.work is None:
                # Admission was ready; domain may have become completed/not due.
                runtime.cancel_business_request(run.identity)
                run.current = run.identity = None
                return
            if run.module != 'quotation':
                close_owner_read_phase()  # duplicate/preparation phase closed before yielding
                run.research = OwnerMarketResearch(runtime, actors, run.work.lease,
                                                   run.work.research, due_at=runtime.module_plans()[run.module][0])
                # Canonical first source is IC.net: submit immediately, never
                # postpone dispatch behind the next protected Owner query.
                run.research.advance()

    def tick():
        nonlocal notified_revision
        completed = actors.drain()
        if actors.faults:
            for fault in actors.faults:
                backend.accept_market_fault(fault)
            return
        # Account for EVERY terminal before applying any successful payload.
        for message in completed:
            run = active.get(message.identity.module.value)
            if (run is None or run.identity is None or run.identity.domain_task_id != message.identity.domain_task_id
                    or run.cycle != message.identity.cycle_id or run.receipts):
                actors.invalidate_owner_result()
                raise OrderResourceOwnershipError()
            run.receipts = (message,)
        if backend._stop.is_set():
            return
        # Canonical earliest-due module selection is reused; no second timer.
        module = runtime.claim_due_module(exclude=busy)
        if module is not None:
            now = utc_now()
            run = _ModuleRun(module, 'cycle_' + uuid4().hex, now, monotonic(), orders(module))
            active[module] = run
            with context(run):
                observation.begin_module(module)
                backend._log_module_cycle(module, 'begin', 0)
            runtime.yield_module_resource(module)
            backend._publish_module_plans()
        for run in tuple(sorted(active.values(), key=lambda r:
                (r.work is not None, runtime.module_plans()[r.module][0], r.started))):
            if run.module in busy or backend._stop.is_set():
                continue
            runtime.resume_module_resource(run.module)
            busy.add(run.module)
            try:
                step(run)
            except MarketContinuationFault as error:
                if error.fault.scope is MarketFaultScope.GLOBAL_STOP:
                    backend.accept_market_fault(error.fault)
                    raise
                cancel_work(run, defer=error.fault.reason)
                finish(run, error)
            except (TpLocalError, SheetRecordConflict, V13SourceRowError) as error:
                if run.module == 'tp':
                    reason = tp_local_failure_reason(error)
                    if not reason:
                        finish(run, error)
                        raise
                    backend._tp.issues[run.identity.domain_task_id if run.identity else 'cycle'] = reason
                cancel_work(run)
                run.current = run.identity = run.quote_result = None
            except MarketContinuationCancelled:
                cancel_work(run)
            except Exception as error:
                if run.module == 'tp' and tp_local_failure_reason(error):
                    backend._tp.issues[run.identity.domain_task_id if run.identity else 'cycle'] = tp_local_failure_reason(error)
                    cancel_work(run, defer=tp_local_failure_reason(error))
                    run.current = run.identity = run.quote_result = None
                    continue
                # Original backend security/integrity classifier owns escalation.
                if run.module in active:
                    finish(run, error)
                raise
            finally:
                busy.discard(run.module)
                if run.module in active and not runtime.module_resource_failed:
                    runtime.yield_module_resource(run.module)
        actors.dispatch_ready()
        for progress in actors.take_progress():
            run = active.get(progress.identity.module.value)
            if run is not None and run.work is not None and run.research is not None:
                site = run.research.progress_source(progress)
                if site is not None:
                    if progress.stage.value == 'queued':
                        observation.wait(run.module, '等待来源查询资源', site=site.value)
                    else:
                        observation.stage(run.module, '市场来源读取', site=site.value,
                                          order_ref=progress.identity.domain_task_id)
        if observation.revision != notified_revision:
            notified_revision = observation.revision
            backend._notify()

    try:
        actors.start()
        backend._continuation_pump = tick
        backend._continuation_reader = reader
        while not backend._stop.is_set():
            with backend._poll_gate:
                backend._poll_idle.clear()
                backend._next_poll_at = None
            tick()
            if not active and actors.quiescent:
                backend._close_inso_order_tab()
                backend._poll_idle.set()
                if backend._wait_between_polls(runtime.module_delay()):
                    break
            else:
                backend._stop.wait(0.05)
    finally:
        backend._continuation_pump = None
        backend._continuation_reader = None
        native_clean = actors.close(timeout=10)
        clean = native_clean and not actors.faults
        # Active work is never assumed cancelled merely because Stop was set.
        # close(False) leaves exact in-flight leases held and prevents clean exit.
        for run in (*tuple(active.values()), *draining):
            if run.work is not None:
                try:
                    cancel_work(run)
                except RuntimeError:
                    clean = False
            elif run.identity is not None:
                runtime.cancel_business_request(run.identity)
        if runtime.business_resource_counts()['active']:
            clean = False
        observation.concurrent_modules = prior_parallel
        if not clean:
            backend._poll_idle.clear()
            if actors.faults:
                backend.accept_market_fault(actors.faults[0])
            elif not native_clean:
                backend.accept_market_fault(MarketFault(MarketFaultScope.GLOBAL_STOP,
                    'CDP_PAGE_CLEANUP_UNCONFIRMED', ('RuntimeError',)))
            else:
                # A durable business outcome/source lease remains unknown; do
                # not mislabel that as failed CDP client initialization/cleanup.
                backend._runtime_error(OrderResourceOwnershipError())
            raise OrderResourceOwnershipError()
        backend._market_actors = None
        backend._module_runtime = None
        backend._poll_idle.set()
