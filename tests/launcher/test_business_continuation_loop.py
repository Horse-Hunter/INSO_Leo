"""Real Backend/Runtime/domain continuation assembly, isolated synthetic clients.

NOT real browser overlap, wall-clock TP timeliness or production acceptance.
"""
import threading
from contextlib import nullcontext
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState
from src.launcher import backend as launcher
from src.launcher.market_actors import MarketReadActors
from src.launcher.purchase_completion import PurchaseCompletionActions
from src.research.cdp_pages import PageTargetOwnershipError
from src.research.icnet import IcNetResult
from src.research.market_contracts import MarketReadMode, MarketReadResult
from src.research.source_contracts import ResearchSource as S
from src.research.source_contracts import SourceEvidence, SourceOutcome, SourceResult
from src.research.tp import TpOffer, select_tp_offers
from src.sheets.pending import query_pending_records
from src.workflow.service import OrderResourceOwnershipError, WorkflowRuntime
from src.workflow.tp_research import TpCycle, TpStore
from src.workflow.v12_contracts import (
    BusinessState,
    EventType,
    PurchaseDraftResult,
    PurchaseOutcome,
)
from src.workflow.v13_integration import V13HoldStore, V13IntegratedCycle
from src.workflow.v13_quotation import V13QuotationCycle
from tests.inso.test_v13_quotation_read import quote
from tests.research.test_aggregation_service import _complete, _result, _service
from tests.research.test_tp import NOW
from tests.sheets.test_tp_brief import brief, source
from tests.workflow.test_v12_flow import (
    SHEET,
    FakeSheetsReader,
    ResearchBusinessFacts,
    _make_flow,
)
from tests.workflow.test_v13_quotation import Operations, Quotes, failure


@pytest.mark.parametrize('mode', ['complete', 'stop', 'initialization_fault', 'teardown_fault', 'quotation_retry', 'tp_header_fault', 'tp_source_changed', 'inflight_fault', 'inquiry_wait', 'purchase_unknown', 'brand_cleanup_fault', 'mail_guard_fault', 'status_write_pending', 'cycle_parity', 'recovery_verified', 'recovery_unverified'])
def test_actual_three_domain_backend_assembly_without_whole_research_wait(tmp_path, monkeypatch, mode):
    flow, store, ledger, _, _, _, writer, notification_worker = _make_flow(tmp_path,
        facts=ResearchBusinessFacts('货少', Decimal(14), Decimal(2)))
    source_changed = threading.Event()
    row = FakeSheetsReader(brand='' if mode == 'brand_cleanup_fault' else 'Brand-X').row
    quote_row = replace(row, row_position=5, cells={**row.cells, 'E': 'MPN5'})
    class Reader:
        def __init__(self):
            self.rows = [row, source(position=4, mpn='TEST-TP')]
        def read_rows(self, worksheet):
            assert worksheet == SHEET
            if source_changed.is_set():
                self.rows[1] = replace(self.rows[1], cells={**self.rows[1].cells, 'G': 101})
            return tuple(self.rows)
        def discovery_scope(self):
            return nullcontext()
    reader = Reader()
    reader.rows.append(quote_row)
    if mode == 'inquiry_wait':
        reader.rows.append(replace(row, row_position=6, cells={**row.cells, 'E': 'MPN6'}))
    original = next(r for r in query_pending_records(reader, SHEET) if r.row_position == 5)
    store.enqueue(original, now=NOW)
    flow._set_state(store.inquiry_id_for(original.record_identity), BusinessState.PURCHASE_RECORDED,
                    EventType.PURCHASE_DATA_SAVED, NOW)
    reader.rows[1] = replace(reader.rows[1], cells={**reader.rows[1].cells, 'A': 'TP_ONLY'})
    reader.rows[2] = replace(quote_row, cells={**quote_row.cells, 'A': '发给采购'})
    holds = V13HoldStore(tmp_path / 'workflow.sqlite3')
    holds.migrate()
    tp_store = TpStore(tmp_path / 'workflow.sqlite3')
    tp_store.migrate()
    values = _complete({S.HQEW: _result(S.HQEW, SourceOutcome.SUCCESS, '2')})
    def service():
        return _service(tmp_path / 'synthetic.xlsx', values)
    flow._research = service()
    monkeypatch.setattr('src.research.tp.collect_tp', lambda adapter, site, mpn, qty, now, fx:
        select_tp_offers(site, (TpOffer(site, mpn, Decimal(3), 'RMB', now, False),),
                         query=mpn, now=now, fx=fx))
    stopped = threading.Event()
    class Session:
        def __init__(self, config, admission):
            self.service = service()
        def __enter__(self):
            if mode == 'initialization_fault':
                raise RuntimeError('synthetic initializer failure')
            return self
        def __exit__(self, *args):
            if mode == 'teardown_fault':
                raise RuntimeError('synthetic teardown failure')
            return False
        def read(self, query):
            if mode == 'inflight_fault' and query.mode is MarketReadMode.ORDINARY and query.source is S.HQEW:
                raise PageTargetOwnershipError(())
            if mode == 'tp_source_changed' and query.mode is MarketReadMode.TP_OFFERS and query.source is S.LCSC:
                source_changed.set()
            if mode == 'stop' and query.mode is MarketReadMode.TP_OFFERS:
                stopped.set()
            if query.mode is MarketReadMode.ORDINARY:
                return self.service.read_market_source(query)
            if query.source is S.IC_NET:
                native = SourceResult(S.IC_NET, SourceOutcome.NO_VALID_PRICE,
                    SourceEvidence(S.IC_NET, query.mpn, None, SourceOutcome.NO_VALID_PRICE, NOW))
                return MarketReadResult(query.source, query.mode, offers=(), icnet_context=IcNetResult(native))
            return MarketReadResult(query.source, query.mode,
                offers=(TpOffer(query.source, query.mpn, Decimal(2), 'RMB', NOW, False),))
    clock = SimpleNamespace(tick=0.0)
    class Stop:
        def __init__(self):
            self.event = stopped
        def is_set(self):
            return self.event.is_set()
        def set(self):
            self.event.set()
        def clear(self):
            self.event.clear()
        def wait(self, seconds):
            clock.tick += 10
            assert clock.tick < 2000, 'synthetic assembly did not converge'
            return self.event.wait(min(seconds, 0.001))
    def factory(runtime, cfg, admission, **options):
        return MarketReadActors(runtime, cfg, admission, session_type=Session, **options)
    backend = launcher.ProductionBackend(root=tmp_path, market_actor_factory=factory)
    backend._stop = Stop()
    backend._state = RunState.RUNNING
    backend._observation.enable(quotation=True, tp=True)
    backend._v12_composition = SimpleNamespace(coordinator=flow)
    flow._row_wait = backend._wait_between_rows
    purchase_at = []
    prepare_purchase = writer.prepare
    def purchase(command):
        purchase_at.append(clock.tick)
        if mode in {'purchase_unknown', 'status_write_pending'}:
            outcome = PurchaseOutcome.UNKNOWN_WRITE_OUTCOME if mode == 'purchase_unknown' else PurchaseOutcome.SAVED
            ledger.set_purchase_state(command.inquiry_id, command.command_id, outcome, at=NOW)
            return PurchaseDraftResult(command.command_id, outcome, NOW)
        return prepare_purchase(command)
    writer.prepare = purchase
    backend._v12_store, backend._store = ledger, store
    def failed_status_writer():
        raise TimeoutError('synthetic Google status write unavailable')
    backend._purchase_completion = PurchaseCompletionActions(workflow_store=store, v12_store=ledger,
        reader=reader, writer_factory=failed_status_writer, clock=lambda: NOW)
    flow._on_result = backend._complete_inquiry
    backend._refresh = lambda: None
    backend._idle_login_tick = lambda **kw: None
    def close_owner(**kw):
        backend._inso_session = None
        backend._active_inso_inquiry = None
    backend._close_inso_order_tab = close_owner
    owner_prepared = []
    def prepare_owner(*args):
        owner_prepared.append((backend._active_inso_inquiry, backend._cycle_id))
    backend._ensure_research_ready = prepare_owner
    backend._notify = lambda: None
    parity = mode == 'cycle_parity'
    reset_states, count_states, recovery_checks = [], [], []
    owner_thread = threading.get_ident()
    original_reset = backend._begin_poll_projection
    original_counts = backend._refresh_dashboard_counts
    original_recovery = backend._check_site_recovery
    def reset_projection():
        assert threading.get_ident() == owner_thread and operations.active is None
        before = (set(backend._poll_inquiries), set(backend._poll_quotation_completed))
        original_reset()
        assert not backend._poll_inquiries and not backend._poll_quotation_completed
        reset_states.append(before)
    def counts(*args, **kwargs):
        assert threading.get_ident() == owner_thread and operations.active is None
        original_counts(*args, **kwargs)
        status = backend.get_status()
        count_states.append((backend._module_contexts[-1], status.new_orders,
                             status.awaiting_quotation, status.overdue_quotation))
    def recovery(*args):
        assert threading.get_ident() == owner_thread and operations.active is None
        recovery_checks.append(backend._module_contexts[-1])
        original_recovery(*args)
    backend._begin_poll_projection = reset_projection
    backend._refresh_dashboard_counts = counts
    backend._check_site_recovery = recovery
    if parity:
        backend._poll_inquiries.add('stale-previous-cycle')
        backend._poll_quotation_completed.add('stale-previous-cycle')
    if mode.startswith('recovery_'):
        backend._site_manual_wait.add('INSO')
        backend._site_outages.update({'INSO': 0, 'IC.net': 0})
        backend._combined = SimpleNamespace(v12_paused=True)
        backend._state = RunState.QUOTATION_RUNNING
        def verified(browser):
            assert threading.get_ident() == owner_thread
            assert not writer.commands and not updates and not tp_prepared
            return mode == 'recovery_verified'
        monkeypatch.setattr('src.launcher.inso_session.authenticated_inso_shell_available', verified)
    backend._cache_workbench = lambda **kw: None
    backend._v13_ledger_ready = False
    if mode == 'brand_cleanup_fault':
        def brand_failure(identity, brand):
            error = PageTargetOwnershipError(())
            backend._page_admission.invalidate(error)
            raise error
        flow._brand_updater = SimpleNamespace(update_brand=brand_failure)
    backend._alert_owner_of_login = lambda **kw: None
    backend._tp = TpCycle(store=tp_store,
        brief=SimpleNamespace(read=lambda _: (brief(row='4', mpn='TEST-TP', price='2 RMB'),)),
        reader=reader, research=service(), outbox=ledger, worker=notification_worker)
    responses = ([failure()] if mode == 'quotation_retry' else []) + [(quote(at=NOW, model='MPN5'),)]
    quotes, operations = Quotes(responses), Operations()
    if mode == 'mail_guard_fault':
        from src.workflow import tp_research
        compose = tp_research.tp_mail
        def compose_then_resource_fault(*args, **kwargs):
            mail = compose(*args, **kwargs)
            backend._page_admission.invalidate(PageTargetOwnershipError(()))
            return mail
        monkeypatch.setattr(tp_research, 'tp_mail', compose_then_resource_fault)
    if mode == 'tp_header_fault':
        def bad_header(_spreadsheet):
            raise ValueError('TP_HEADER_INVALID')
        backend._tp.brief.read = bad_header
    tp_prepared = []
    def tp_prepare(key):
        assert operations.active is None
        tp_prepared.append(clock.tick)
    backend._tp.prepare = tp_prepare
    updates = []
    def quotation_factory(worksheet):
        cycle = V13QuotationCycle(reader=reader, store=store, operations=operations,
            quote_reader=quotes, clock=lambda: NOW, wait=backend._closed_retry_wait)
        return V13IntegratedCycle(reader=reader, store=store, holds=holds, cycle=cycle,
            updater_factory=lambda: SimpleNamespace(update_one=lambda result: updates.append(result) or result),
            notify=lambda *a: None, observe=lambda *a: None)
    backend._quotation_factory = quotation_factory
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({'inquiry': 900, 'quotation': 900, 'tp': 900}, timer=lambda: clock.tick)
    backend._module_runtime = runtime
    if mode == 'quotation_retry':
        runtime._module_due['tp'] = 40
    elif mode == 'inquiry_wait':
        runtime._module_due['tp'] = 150
    backend._observation.timer = lambda: clock.tick
    backend._observation.clock = lambda: NOW + timedelta(seconds=clock.tick)
    episodes = None
    if parity:
        from src.workflow.v13_follow_up_store import V13PurchaseFollowUpStore
        episodes = V13PurchaseFollowUpStore(tmp_path / 'workflow.sqlite3')
        episodes.migrate()
        episodes.record_confirmed(store.inquiry_id_for(original.record_identity),
                                  confirmed_at=NOW - timedelta(days=10))
    cycles = []
    backend._log_module_cycle = lambda module, phase, seconds: cycles.append(
        (module, phase, backend._cycle_id, clock.tick))
    waits, first_projection = [], []
    def end_wait(seconds):
        waits.append(seconds)
        if parity and len(waits) < 4:
            if len(waits) == 1:
                assert count_states[:2] == [('inquiry', 1, 1, 1), ('quotation', 1, 1, 1)]
                # Normal projection API records this round; next inquiry must
                # clear it, not accumulate it with the prior round.
                backend._seen('completed-first-cycle')
                backend._poll_quotation_completed.add('completed-first-cycle')
                first_projection.append((set(backend._poll_inquiries), set(backend._poll_quotation_completed)))
                reader.rows = [replace(r, cells={**r.cells, 'A': '成交'}) for r in reader.rows]
            clock.tick += seconds
            return False
        backend._stop.set()
        return True
    backend._wait_between_polls = end_wait
    monkeypatch.setattr(launcher, 'utc_now', lambda: NOW + timedelta(seconds=clock.tick))
    monkeypatch.setattr(launcher, 'monotonic', lambda: clock.tick)
    monkeypatch.setattr('src.launcher.business_continuations.monotonic', lambda: clock.tick)
    if mode == 'recovery_unverified':
        with pytest.raises(launcher.InsoAuthenticationError, match='MANUAL_VERIFICATION_REQUIRED'):
            backend._run_independent_poll(runtime, {'spreadsheet_id': SHEET.spreadsheet}, None,
                SimpleNamespace(poll_scope=nullcontext), reader, (SHEET,), episodes)
        assert 'INSO' in backend._site_manual_wait and 'INSO' in backend._site_outages
        assert backend._combined.v12_paused
        assert not writer.commands and not updates and not tp_store.rows() and not count_states
        assert recovery_checks == ['inquiry']
        assert runtime.business_resource_counts()['active'] == 0
        return
    if mode in {'initialization_fault', 'teardown_fault', 'inflight_fault', 'purchase_unknown', 'brand_cleanup_fault', 'mail_guard_fault', 'status_write_pending'}:
        with pytest.raises((OrderResourceOwnershipError, RuntimeError)):
            backend._run_independent_poll(runtime, {'spreadsheet_id': SHEET.spreadsheet}, None,
                SimpleNamespace(poll_scope=nullcontext), reader, (SHEET,), episodes)
        assert backend._state is RunState.GLOBAL_STOP
        assert runtime.module_resource_failed
        if mode in {'purchase_unknown', 'brand_cleanup_fault', 'status_write_pending'}:
            from src.workflow.service import _RESEARCH_WORKER_LOCK
            assert runtime.business_resource_counts()['unknown'] == 1
            assert _RESEARCH_WORKER_LOCK.acquire(blocking=False)
            _RESEARCH_WORKER_LOCK.release()
        if mode in {'inflight_fault', 'brand_cleanup_fault'}:
            assert not purchase_at and not writer.commands
            assert all(row['state'] != 'MAIL_QUEUED' for row in tp_store.rows())
        if mode == 'mail_guard_fault':
            assert tp_store.rows()[0]['state'] == 'FAILED'
        return
    else:
        backend._run_independent_poll(runtime, {'spreadsheet_id': SHEET.spreadsheet}, None,
            SimpleNamespace(poll_scope=nullcontext), reader, (SHEET,), episodes)
    if parity:
        # Repeated due waits may finish modules at different instants. Verify
        # per-cycle hooks, not per-tick counts or a second statistics system.
        starts = [m for m, phase, _, _ in cycles if phase == 'begin']
        assert starts.count('inquiry') >= 2
        assert len(reset_states) == starts.count('inquiry')
        assert reset_states[0] == ({'stale-previous-cycle'}, {'stale-previous-cycle'})
        assert reset_states[1] == first_projection[0]
        assert 'stale-previous-cycle' not in reset_states[1][0]
        assert len(count_states) == starts.count('inquiry') + starts.count('quotation')
        assert sorted(recovery_checks) == sorted(starts)
        assert all(state[1:] == (0, 0, 0) for state in count_states[2:])
        status = backend.get_status()
        assert (status.new_orders, status.awaiting_quotation, status.overdue_quotation) == (0, 0, 0)
        assert not backend._poll_inquiries and not backend._poll_quotation_completed
        assert len(writer.commands) == len(updates) == len(tp_store.rows()) == 1
        assert backend._market_actors is None and runtime.business_resource_counts()['active'] == 0
        return
    assert len({cycle for _, phase, cycle, _ in cycles if phase == 'begin'}) == 3
    if mode == 'recovery_verified':
        assert recovery_checks == ['inquiry', 'quotation', 'tp']
        assert 'INSO' not in backend._site_manual_wait
        assert 'INSO' in backend._site_outages  # Only business proof clears outage.
        assert not backend._combined.v12_paused and backend._state is RunState.RUNNING
    if mode in {'complete', 'quotation_retry', 'tp_header_fault', 'tp_source_changed', 'inquiry_wait', 'recovery_verified'}:
        assert {module for module, phase, _, _ in cycles if phase == 'completed'} == {'inquiry', 'quotation', 'tp'}
        assert writer.commands and updates
        assert owner_prepared and all(key and cycle for key, cycle in owner_prepared)
        if mode == 'tp_header_fault':
            assert backend._tp.issues == {'cycle': 'TP_HEADER_INVALID'}
            assert not tp_store.rows() and not runtime.module_resource_failed
        elif mode == 'tp_source_changed':
            assert tp_store.rows()[0]['state'] == 'FAILED'
            assert backend._tp.issues and not runtime.module_resource_failed
        else:
            assert len(tp_store.rows()) == 1 and tp_store.rows()[0]['state'] == 'MAIL_QUEUED'
        if mode == 'quotation_retry':
            assert len(quotes.calls) == 2
            assert tp_prepared and 40 <= tp_prepared[0] < 140
            assert backend._observation.modules['quotation'].cycle_elapsed_seconds >= 120
        if mode == 'inquiry_wait':
            assert len(purchase_at) == 2 and purchase_at[1] - purchase_at[0] >= 120
            assert 150 <= tp_prepared[0] < purchase_at[1]
        for module in ('inquiry', 'quotation', 'tp'):
            assert {cycle for name, _, cycle, _ in cycles if name == module} == {
                next(cycle for name, phase, cycle, _ in cycles if name == module and phase == 'begin')}
    else:
        assert all(row['state'] != 'MAIL_QUEUED' for row in tp_store.rows())
    assert backend._market_actors is None and runtime.business_resource_counts()['active'] == 0
    assert operations.active is None and runtime.order_resource_counts()['active'] == 0
