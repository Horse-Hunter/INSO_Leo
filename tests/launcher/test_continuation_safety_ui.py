"""Continuation-specific finite capacity, safety, UI and canonical sweep tests."""
from datetime import timedelta
from types import SimpleNamespace

import pytest

from src.gui.contracts import SiteLoginOutcome, SiteLoginResult
from src.launcher import site_login_sweep
from src.launcher.workbench_snapshot import RuntimeObservation
from src.research.cdp_pages import PageResourceAdmission, PageTargetOwnershipError
from src.research.market_contracts import MarketReadMode, MarketReadQuery
from src.research.source_contracts import ResearchSource as S
from src.workflow.market_messages import (
    BusinessTerminal,
    BusinessTerminalReceipt,
    MarketCompletion,
    MarketModule,
    MarketTerminal,
)
from src.workflow.service import WorkflowRuntime
from tests.research.test_tp import NOW
from tests.workflow.test_business_continuation import identity


def test_three_business_reservations_still_only_two_query_slots():
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({'inquiry': 900, 'quotation': 900, 'tp': 900})
    runtime.configure_market_reads(2, business_continuations=True)
    handles, requests = [], []
    for n, (module, source) in enumerate(zip(MarketModule, (S.HQEW, S.FINDCHIPS, S.LCSC), strict=True)):
        handle = runtime.claim_business_continuation(identity(module, row=43+n, token=module.value))
        handles.append(handle)
        mode = MarketReadMode.TP_OFFERS if module is MarketModule.TP else MarketReadMode.ORDINARY
        requests.append(runtime.prepare_business_market_read(handle,
            MarketReadQuery(source, mode, 'SYNTHETIC', 10, NOW), due_at=0))
    claimed = [runtime.claim_market_read(), runtime.claim_market_read()]
    assert all(pair is not None for pair in claimed)
    assert runtime.claim_market_read() is None
    for request, resource in claimed:
        assert runtime.commit_market_dispatch(request, resource)
    runtime.close_market_reads()
    for request, _ in claimed:
        runtime.acknowledge_market_terminal(MarketCompletion(request.identity, MarketTerminal.CANCELLED, 0, 0))
    for handle in handles:
        runtime.finish_business_continuation(handle, BusinessTerminalReceipt(handle.identity, BusinessTerminal.CANCELLED))
    assert runtime.business_resource_counts()['active'] == 0


def test_shared_safety_fault_between_query_and_owner_effect_closes_runtime():
    admission = PageResourceAdmission()
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({'tp': 900})
    runtime.configure_market_reads(2, business_continuations=True, safety_check=admission.require_open)
    handle = runtime.claim_business_continuation(identity())
    admission.invalidate(PageTargetOwnershipError(()))
    with pytest.raises(PageTargetOwnershipError):
        runtime.begin_business_effect(handle)
    assert runtime.module_resource_failed and runtime.business_resource_counts()['effects'] == 0
    runtime.finish_business_continuation(handle, BusinessTerminalReceipt(handle.identity, BusinessTerminal.CANCELLED))


def test_concurrent_ui_keeps_each_stage_cycle_and_resource_wait_duration():
    clock = SimpleNamespace(tick=0.0)
    view = RuntimeObservation(clock=lambda: NOW + timedelta(seconds=clock.tick), timer=lambda: clock.tick)
    view.enable(quotation=True, tp=True)
    view.concurrent_modules = True
    view.begin_module('inquiry')
    clock.tick = 5
    view.begin_module('quotation')
    clock.tick = 10
    view.begin_module('tp')
    assert all(module.started_monotonic is not None for module in view.modules.values())
    clock.tick = 15
    view.wait('tp', '等待来源查询资源', site='ic.net')
    start = view.modules['tp'].started_monotonic
    clock.tick = 30
    view.wait('tp', '等待来源查询资源', site='ic.net')
    assert view.modules['tp'].started_monotonic == start
    view.finish_module('quotation')
    assert view.modules['quotation'].cycle_elapsed_seconds == 25
    assert view.cycle_finished_at is None  # inquiry andTP cycles still active
    assert view.modules['inquiry'].cycle_started_monotonic == 0


def test_targeted_recovery_reuses_canonical_steps_without_unrelated_site_login(monkeypatch):
    steps = tuple(SimpleNamespace(key=key) for key in ('icnet', 'findchips', 'hqew', 'lcsc', 'bom-ai', 'inso'))
    monkeypatch.setattr(site_login_sweep, 'build_site_sign_in_steps', lambda **kw: steps)
    seen = []
    class Sweep:
        def __init__(self, browser, **kw):
            pass
        def run(self, selected):
            seen.extend(step.key for step in selected)
            return (SiteLoginResult('华强电子网', SiteLoginOutcome.ALREADY_SIGNED_IN),)
        def close(self):
            seen.append('closed')
    result = site_login_sweep.sweep_sites(object(), bom_ai=None, sweep_factory=Sweep,
                                         only_sites=frozenset({'hqew'}))
    assert seen == ['hqew', 'closed'] and result[0].outcome is SiteLoginOutcome.ALREADY_SIGNED_IN
