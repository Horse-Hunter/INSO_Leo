"""Actual isolated actor transport -> canonical TP -> original durable outbox.

Fake source clients only; no network/SMTP/production databases. This is NOT
actual-browser concurrency or production scheduler/TP-deadline acceptance.
"""
import threading
from dataclasses import replace
from decimal import Decimal
from time import monotonic
from types import SimpleNamespace

import pytest

from src.launcher.market_actors import MarketReadActors
from src.launcher.market_continuation import (
    MarketContinuationCancelled,
    OwnerMarketResearch,
)
from src.research.cdp_pages import PageResourceAdmission, PageTargetOwnershipError
from src.research.icnet import IcNetResult
from src.research.market_contracts import MarketReadResult
from src.research.service import ResearchService
from src.research.source_contracts import ResearchSource as S
from src.research.source_contracts import SourceEvidence, SourceOutcome, SourceResult
from src.research.tp import TpOffer, select_tp_offers
from src.sheets.tp_brief import TpLocalError
from src.workflow.market_messages import (
    BusinessResearchCompletion,
    MarketModule,
    MarketTaskIdentity,
)
from src.workflow.service import WorkflowRuntime
from src.workflow.tp_research import task_key
from tests.research.test_tp import NOW, Fx
from tests.workflow.test_tp_research import build


def fixture(tmp_path, monkeypatch):
    from src.research import tp
    cycle, lines, reader, transport, _path = build(tmp_path)
    original = cycle.research
    native = SourceResult(S.IC_NET, SourceOutcome.NO_VALID_PRICE,
        SourceEvidence(S.IC_NET, 'TEST-ABC', None, SourceOutcome.NO_VALID_PRICE, NOW))
    cycle.research = ResearchService(icnet=SimpleNamespace(search=lambda *a: IcNetResult(native)),
        findchips=object(), hqew=object(), lcsc=object(), bom_ai=object(), inso=object(),
        output=None, fx_provider=Fx())
    monkeypatch.setattr(tp, 'collect_tp', lambda adapter, site, mpn, qty, now, fx:
        select_tp_offers(site, (TpOffer(site, mpn, Decimal(2), 'USD', now, False),),
                         query=mpn, now=now, fx=fx))
    class Session:
        def __init__(self, config, admission):
            self.admission = admission
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, query):
            if query.source is S.IC_NET:
                return MarketReadResult(query.source, query.mode, offers=(), icnet_context=IcNetResult(native))
            return MarketReadResult(query.source, query.mode,
                offers=(TpOffer(query.source, query.mpn, Decimal(1), 'USD', NOW, False),))
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({'inquiry': 900, 'quotation': 900, 'tp': 900})
    admission = PageResourceAdmission()
    actors = MarketReadActors(runtime, None, admission, session_type=Session)
    actors.start()
    order, = cycle.read_orders('synthetic')
    identity = MarketTaskIdentity(MarketModule.TP, 'tp-cycle-one', 'tp-business-one',
        task_key(order.spreadsheet, order.sheet, order.row), cycle._revalidate(order))
    return cycle, order, identity, runtime, actors, admission, lines, reader, transport, original


def run_research(driver, actors):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        result = driver.advance(actors.drain())
        actors.dispatch_ready()
        if result is not None:
            return result
        threading.Event().wait(0.001)  # finite offline test yielding to real workers
    pytest.fail('isolated continuation did not finish')


def test_tp_real_domain_continuation_keeps_resource_until_source_check_and_outbox(tmp_path, monkeypatch):
    cycle, order, identity, runtime, actors, _, _, _, transport, _ = fixture(tmp_path, monkeypatch)
    try:
        work = cycle.begin_continuation(order, identity, runtime, now=NOW)
        driver = OwnerMarketResearch(runtime, actors, work.lease, work.research, due_at=0)
        result = run_research(driver, actors)
        assert result.result.lowest.rmb == 7 and result.result.second.rmb == 14
        other = replace(identity, module=MarketModule.INQUIRY, request_id='inquiry-business',
                        domain_task_id='inq_existing')
        assert runtime.claim_business_continuation(other) is None
        assert runtime.business_resource_counts()['active'] == 1
        work.complete(result)
        assert runtime.business_resource_counts() == {'active': 0, 'reads': 0, 'effects': 0, 'unknown': 0}
        assert cycle.store.get(identity.domain_task_id)['state'] == 'MAIL_QUEUED'
        assert not transport.calls  # enqueued only; never invoke SMTP
        with pytest.raises(RuntimeError, match='LIFETIME'):
            work.complete(result)
        assert runtime.claim_business_continuation(other) is not None
    finally:
        assert actors.close()


def test_tp_source_change_before_effect_blocks_email(tmp_path, monkeypatch):
    cycle, order, identity, runtime, actors, _, _, reader, transport, original = fixture(tmp_path, monkeypatch)
    try:
        work = cycle.begin_continuation(order, identity, runtime, now=NOW)
        result = BusinessResearchCompletion(identity, original.execute_tp(identity.domain_task_id, order, now=NOW))
        row = reader.rows[0]
        reader.rows[0] = replace(row, cells={**row.cells, 'A': 'changed'})
        with pytest.raises(TpLocalError, match='TP_SOURCE_CHANGED'):
            work.complete(result)
        assert runtime.business_resource_counts()['active'] == 0
        assert cycle.store.get(identity.domain_task_id)['state'] == 'FAILED'
        assert not transport.calls
    finally:
        assert actors.close()


def test_enqueue_commit_then_error_adopts_same_immutable_command(tmp_path, monkeypatch):
    cycle, order, identity, runtime, actors, _, _, _, transport, original = fixture(tmp_path, monkeypatch)
    try:
        work = cycle.begin_continuation(order, identity, runtime, now=NOW)
        enqueue = cycle.outbox.enqueue_notification
        def committed_then_error(command):
            enqueue(command)
            raise RuntimeError('synthetic after commit')
        monkeypatch.setattr(cycle.outbox, 'enqueue_notification', committed_then_error)
        with pytest.raises(RuntimeError, match='after commit'):
            work.complete(BusinessResearchCompletion(identity, original.execute_tp(identity.domain_task_id, order, now=NOW)))
        assert cycle.store.get(identity.domain_task_id)['state'] == 'MAIL_QUEUED'
        assert runtime.business_resource_counts()['active'] == 0
        assert not transport.calls
    finally:
        assert actors.close()


def test_unknown_reconciliation_holds_source_and_closes_admission(tmp_path, monkeypatch):
    cycle, order, identity, runtime, actors, _, _, _, _, original = fixture(tmp_path, monkeypatch)
    try:
        work = cycle.begin_continuation(order, identity, runtime, now=NOW)
        def fail(*a, **kw):
            raise RuntimeError('synthetic DB unavailable')
        monkeypatch.setattr(cycle.outbox, 'enqueue_notification', fail)
        monkeypatch.setattr(cycle.store, 'recover', fail)
        with pytest.raises(RuntimeError, match='DB unavailable'):
            work.complete(BusinessResearchCompletion(identity, original.execute_tp(identity.domain_task_id, order, now=NOW)))
        assert runtime.module_resource_failed
        assert runtime.business_resource_counts()['unknown'] == 1
        assert runtime.business_resource_counts()['active'] == 1
    finally:
        assert actors.close()


def test_stop_prevents_result_application_and_known_cancel_releases(tmp_path, monkeypatch):
    cycle, order, identity, runtime, actors, _, _, _, transport, _ = fixture(tmp_path, monkeypatch)
    try:
        work = cycle.begin_continuation(order, identity, runtime, now=NOW)
        driver = OwnerMarketResearch(runtime, actors, work.lease, work.research, due_at=0)
        actors.request_stop()
        actors.drain()
        with pytest.raises(MarketContinuationCancelled):
            driver.advance()
        work.cancel()
        assert runtime.business_resource_counts()['active'] == 0
        assert not transport.calls
    finally:
        assert actors.close()


def test_global_resource_fault_precedes_success_application(tmp_path, monkeypatch):
    cycle, order, identity, runtime, actors, admission, _, _, transport, _ = fixture(tmp_path, monkeypatch)
    try:
        work = cycle.begin_continuation(order, identity, runtime, now=NOW)
        driver = OwnerMarketResearch(runtime, actors, work.lease, work.research, due_at=0)
        admission.invalidate(PageTargetOwnershipError(()))
        with pytest.raises(PageTargetOwnershipError):
            driver.advance()
        assert runtime.module_resource_failed
        assert work.research.source is S.IC_NET and not transport.calls
        work.cancel()
    finally:
        assert actors.close()


def test_late_other_cycle_result_cannot_apply_to_current_domain_task(tmp_path, monkeypatch):
    cycle, order, identity, runtime, actors, _, _, _, transport, original = fixture(tmp_path, monkeypatch)
    try:
        work = cycle.begin_continuation(order, identity, runtime, now=NOW)
        stale = BusinessResearchCompletion(replace(identity, cycle_id='previous-cycle'),
            original.execute_tp(identity.domain_task_id, order, now=NOW))
        with pytest.raises(ValueError, match='RESULT_MISMATCH'):
            work.complete(stale)
        assert cycle.store.get(identity.domain_task_id)['state'] == 'RESEARCHING'
        assert runtime.business_resource_counts()['active'] == 1 and not transport.calls
        work.cancel()
    finally:
        assert actors.close()
