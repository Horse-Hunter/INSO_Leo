"""One canonical source lease spans reads and owner effects; no real business."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from src.research.market_contracts import (
    MarketReadMode,
    MarketReadQuery,
    MarketReadResult,
)
from src.research.source_contracts import ResearchSource
from src.sheets.pending import (
    IdentifyingSnapshot,
    SheetRecordIdentity,
    WorksheetIdentity,
)
from src.workflow.market_messages import (
    BusinessEffectTerminal,
    BusinessTerminal,
    BusinessTerminalReceipt,
    MarketCompletion,
    MarketModule,
    MarketTaskIdentity,
    MarketTerminal,
)
from src.workflow.service import OrderResourceOwnershipError, WorkflowRuntime


def runtime():
    value = WorkflowRuntime(None, None, ())
    value.configure_modules({'inquiry': 900, 'quotation': 900, 'tp': 900})
    value.configure_market_reads(2)
    return value


def identity(module=MarketModule.TP, *, row=43, cycle='cycle-one', token='business-one'):
    record = SheetRecordIdentity(WorksheetIdentity('synthetic', '2026'), row,
                                IdentifyingSnapshot('pending', None, 'SYNTHETIC', None, 10))
    return MarketTaskIdentity(module, cycle, token, 'existing-domain-task-' + module.value, record)


def query():
    return MarketReadQuery(ResearchSource.HQEW, MarketReadMode.TP_OFFERS, 'SYNTHETIC', 10,
                           datetime(2026, 10, 27, tzinfo=UTC))


def finish(value, handle, terminal=BusinessTerminal.COMPLETED):
    value.finish_business_continuation(handle, BusinessTerminalReceipt(handle.identity, terminal))


def read_terminal(value, handle):
    request = value.prepare_business_market_read(handle, query(), due_at=0)
    assert value.claim_market_read() == (request, handle.resource)
    assert value.commit_market_dispatch(request, handle.resource)
    terminal = MarketCompletion(request.identity, MarketTerminal.SUCCEEDED, 1, 2,
        result=MarketReadResult(ResearchSource.HQEW, MarketReadMode.TP_OFFERS, offers=()))
    value.acknowledge_market_terminal(terminal)
    return terminal


def test_query_terminal_does_not_release_source_during_fx_revalidation_and_business_effect():
    value = runtime()
    handle = value.claim_business_continuation(identity())
    others = [identity(MarketModule.INQUIRY, token='inquiry'), identity(MarketModule.QUOTATION, token='quote')]
    assert all(value.claim_business_continuation(other) is None for other in others)
    independent = value.claim_business_continuation(identity(row=44, token='independent'))
    assert independent is not None
    read_terminal(value, handle)
    assert value.order_resource_counts()['active'] == 2
    assert all(value.claim_business_continuation(other) is None for other in others)
    with pytest.raises(RuntimeError, match='BUSINESS_TERMINAL_UNACKNOWLEDGED'):
        value.release_order_lease(handle.resource)
    value.begin_business_effect(handle)  # Real domain code must still freshly verify authorization.
    with pytest.raises(RuntimeError, match='BUSINESS_WORK_RUNNING'):
        finish(value, handle)
    value.acknowledge_business_effect(handle, BusinessEffectTerminal.CONFIRMED)
    finish(value, handle)
    first = value.claim_business_continuation(others[0])
    assert first is not None and value.claim_business_continuation(others[1]) is None
    finish(value, first)
    second = value.claim_business_continuation(others[1])
    finish(value, second)
    finish(value, independent)
    assert value.order_resource_counts()['active'] == 0


@pytest.mark.parametrize('unknown', [False, True])
def test_stop_does_not_prove_inflight_or_effect_terminal(unknown):
    value = runtime()
    handle = value.claim_business_continuation(identity())
    request = value.prepare_business_market_read(handle, query(), due_at=0)
    value.claim_market_read()
    value.commit_market_dispatch(request, handle.resource)
    value.close_market_reads()
    with pytest.raises(RuntimeError, match='BUSINESS_WORK_RUNNING'):
        finish(value, handle, BusinessTerminal.CANCELLED)
    value.acknowledge_market_terminal(MarketCompletion(request.identity, MarketTerminal.CANCELLED, 1, 2))
    if unknown:
        with pytest.raises(RuntimeError, match='BUSINESS_EFFECT_UNCONFIRMED'):
            finish(value, handle, BusinessTerminal.UNKNOWN)
        assert value.module_resource_failed and value.business_resource_counts()['unknown'] == 1
        assert value.order_resource_counts()['active'] == 1
    else:
        finish(value, handle, BusinessTerminal.CANCELLED)
        assert value.order_resource_counts()['active'] == 0


def test_unknown_owner_effect_cannot_be_released_as_success_or_reconfigured():
    value = runtime()
    handle = value.claim_business_continuation(identity())
    value.begin_business_effect(handle)
    value.acknowledge_business_effect(handle, BusinessEffectTerminal.UNKNOWN)
    with pytest.raises(RuntimeError, match='BUSINESS_EFFECT_UNCONFIRMED'):
        finish(value, handle)
    assert value.order_resource_counts()['active'] == 1
    with pytest.raises(RuntimeError):
        value.configure_modules({'tp': 900})


def test_exact_owner_handle_and_terminal_identity_are_required():
    value = runtime()
    handle = value.claim_business_continuation(identity())
    with pytest.raises(OrderResourceOwnershipError):
        finish(value, replace(handle))
    with ThreadPoolExecutor(max_workers=1) as pool, pytest.raises(OrderResourceOwnershipError):
        pool.submit(finish, value, handle).result()
    with pytest.raises(OrderResourceOwnershipError):
        value.finish_business_continuation(handle, BusinessTerminalReceipt(
            replace(handle.identity, cycle_id='stale-cycle'), BusinessTerminal.COMPLETED))
    finish(value, handle)
    with pytest.raises(OrderResourceOwnershipError):
        finish(value, handle)


def test_new_transport_ids_reject_late_query_from_previous_stage_or_reused_business_identity():
    value = runtime()
    original = identity()
    handle = value.claim_business_continuation(original)
    old = read_terminal(value, handle)
    newer = value.prepare_business_market_read(handle, query(), due_at=0)
    assert newer.identity.request_id != old.identity.request_id
    with pytest.raises(OrderResourceOwnershipError):
        value.acknowledge_market_terminal(old)
    value.close_market_reads()  # Newer query not submitted; cancel its reservation only.
    finish(value, handle, BusinessTerminal.CANCELLED)
    assert value.business_resource_counts()['reads'] == 0
    assert value.order_resource_counts()['active'] == 0
