"""Resource arbitration contracts only, never business permission or live success."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from src.sheets import WorksheetIdentity
from src.workflow.service import OrderResourceOwnershipError, WorkflowRuntime

SHEET = WorksheetIdentity('synthetic-spreadsheet', '2026')


def runtime(capacity=3):
    value = WorkflowRuntime(None, None, ())
    value.configure_modules({'inquiry': 900, 'quotation': 900, 'tp': 900})
    value.configure_order_leases(capacity)
    return value


def test_same_original_row_is_fifo_across_requirement_tokens_while_other_rows_can_run():
    value = runtime()
    assert value.request_order_lease(SHEET, 43, 'inquiry:cycle-one')
    assert value.request_order_lease(SHEET, 43, 'target-price:cycle-two')
    assert value.request_order_lease(SHEET, 44, 'quotation:cycle-three')
    assert value.try_claim_order_lease('target-price:cycle-two') is None
    first = value.try_claim_order_lease('inquiry:cycle-one')
    other = value.try_claim_order_lease('quotation:cycle-three')
    assert first is not None and other is not None
    assert value.try_claim_order_lease('target-price:cycle-two') is None
    value.release_order_lease(first)
    second = value.try_claim_order_lease('target-price:cycle-two')
    assert second is not None
    value.release_order_lease(second)
    value.release_order_lease(other)
    assert value.order_resource_counts() == {'capacity': 3, 'active': 0, 'waiting': 0, 'closed': False}


def test_source_sheet_and_spreadsheet_both_participate_in_order_exclusion():
    value = runtime()
    for token, sheet in [('a', SHEET), ('b', replace(SHEET, worksheet='SHAHAB')),
                         ('c', replace(SHEET, spreadsheet='synthetic-other'))]:
        assert value.request_order_lease(sheet, 43, token)
    leases = [value.try_claim_order_lease(token) for token in ('a', 'b', 'c')]
    assert all(leases)
    for lease in leases:
        value.release_order_lease(lease)


def test_finite_budget_defers_admission_without_consuming_work_or_allocating_extra_state():
    value = runtime(2)
    assert value.request_order_lease(SHEET, 1, 'one')
    assert value.request_order_lease(SHEET, 1, 'one')  # pending request is idempotent
    assert value.request_order_lease(SHEET, 2, 'two')
    for _ in range(1000):
        assert value.request_order_lease(SHEET, 3, 'three') is False
    assert value.order_resource_counts()['waiting'] == 2
    one = value.try_claim_order_lease('one')
    value.release_order_lease(one)
    assert value.request_order_lease(SHEET, 3, 'three')


def test_cancelled_waiter_does_not_starve_next_waiter_and_active_cannot_be_cancelled():
    value = runtime()
    for token in ('one', 'two', 'three'):
        value.request_order_lease(SHEET, 43, token)
    one = value.try_claim_order_lease('one')
    with pytest.raises(RuntimeError, match='ORDER_STILL_RUNNING'):
        value.cancel_order_lease_request('one')
    assert value.cancel_order_lease_request('two')
    value.release_order_lease(one)
    three = value.try_claim_order_lease('three')
    assert three is not None
    value.release_order_lease(three)
    assert value.cancel_order_lease_request('absent') is False


def test_forged_duplicate_and_foreign_thread_releases_never_free_an_active_order():
    value = runtime()
    value.request_order_lease(SHEET, 43, 'one')
    one = value.try_claim_order_lease('one')
    with pytest.raises(OrderResourceOwnershipError):
        value.release_order_lease(replace(one))  # equal fields are not the actual granted lease
    with ThreadPoolExecutor(max_workers=1) as pool, pytest.raises(OrderResourceOwnershipError):
        pool.submit(value.release_order_lease, one).result()
    assert value.order_resource_counts()['active'] == 1
    with pytest.raises(RuntimeError, match='ORDER_ALREADY_CLAIMED'):
        value.try_claim_order_lease('one')
    value.release_order_lease(one)
    with pytest.raises(OrderResourceOwnershipError):
        value.release_order_lease(one)


def test_stop_cancels_only_undispatched_requests_active_work_must_drain():
    value = runtime()
    value.request_order_lease(SHEET, 43, 'one')
    value.request_order_lease(SHEET, 43, 'two')
    one = value.try_claim_order_lease('one')
    value.close_order_admissions()
    assert value.order_resource_counts() == {'capacity': 3, 'active': 1, 'waiting': 0, 'closed': True}
    with pytest.raises(RuntimeError, match='ORDER_ADMISSIONS_CLOSED'):
        value.request_order_lease(SHEET, 44, 'three')
    value.release_order_lease(one)
    assert value.order_resource_counts()['active'] == 0


def test_shared_module_abort_closes_order_admissions_but_preserves_active_lease_for_drain():
    value = runtime()
    assert value.claim_due_module() == 'inquiry'
    value.request_order_lease(SHEET, 43, 'one')
    value.request_order_lease(SHEET, 43, 'two')
    one = value.try_claim_order_lease('one')
    value.abort_module_resource()
    assert value.order_resource_counts()['active'] == 1
    assert value.order_resource_counts()['waiting'] == 0
    with pytest.raises(RuntimeError, match='MODULE_RESOURCE_OWNERSHIP_LOST'):
        value.request_order_lease(SHEET, 44, 'three')
    value.release_order_lease(one)
    with pytest.raises(RuntimeError, match='MODULE_RESOURCE_OWNERSHIP_LOST'):
        value.configure_order_leases(3)


@pytest.mark.parametrize('capacity', [0, -1, True, 1.5])
def test_invalid_budgets_refused(capacity):
    with pytest.raises(ValueError, match='INVALID_ORDER_RESOURCE_CAPACITY'):
        runtime(capacity)


@pytest.mark.parametrize('sheet,row,token', [(None,43,'one'), (SHEET,True,'one'),
    (SHEET,0,'one'), (SHEET,43,''), (replace(SHEET,spreadsheet=''),43,'one')])
def test_invalid_source_identifiers_do_not_create_resource_requests(sheet,row,token):
    value = runtime()
    with pytest.raises(ValueError, match='INVALID_ORDER_RESOURCE_IDENTITY'):
        value.request_order_lease(sheet,row,token)
    assert value.order_resource_counts()['waiting'] == 0


def test_default_closed_and_cancelled_request_cannot_be_claimed():
    value = WorkflowRuntime(None,None,())
    with pytest.raises(RuntimeError, match='ORDER_ADMISSIONS_CLOSED'):
        value.request_order_lease(SHEET,43,'one')
    value.configure_order_leases(1)
    value.request_order_lease(SHEET,43,'one')
    value.cancel_order_lease_request('one')
    assert value.try_claim_order_lease('one') is None


def test_reconfiguration_cannot_steal_live_resource_claims():
    value = runtime()
    value.request_order_lease(SHEET,43,'one')
    with pytest.raises(RuntimeError, match='ORDER_RESOURCES_RUNNING'):
        value.configure_order_leases(5)
    with pytest.raises(RuntimeError, match='MODULES_RUNNING'):
        value.configure_modules({'tp':900})
    with pytest.raises(OrderResourceOwnershipError):
        value.request_order_lease(SHEET,44,'one')
    assert value.order_resource_counts()['waiting'] == 1


@pytest.mark.parametrize('fatal', [False, True])
def test_terminal_close_cannot_be_rearmed_by_configuration_after_drain(fatal):
    value = runtime()
    value.request_order_lease(SHEET, 1, 'running')
    active = value.try_claim_order_lease('running')
    value.request_order_lease(SHEET, 1, 'waiting')
    if fatal:
        assert value.claim_due_module() == 'inquiry'
        value.abort_module_resource()
    else:
        value.close_order_admissions()
    assert value.order_resource_counts()['waiting'] == 0
    value.release_order_lease(active)
    if fatal:
        with pytest.raises(RuntimeError, match='MODULE_RESOURCE_OWNERSHIP_LOST'):
            value.configure_modules({'inquiry': 900})
    else:
        value.configure_modules({'inquiry': 900})
    with pytest.raises(RuntimeError, match='MODULE_RESOURCE_OWNERSHIP_LOST|ORDER_ADMISSIONS_CLOSED'):
        value.configure_order_leases(3)
    with pytest.raises(RuntimeError, match='MODULE_RESOURCE_OWNERSHIP_LOST|ORDER_ADMISSIONS_CLOSED'):
        value.request_order_lease(SHEET, 2, 'new')
    assert value.order_resource_counts()['active'] == 0
    fresh = runtime()
    assert fresh.request_order_lease(SHEET, 2, 'explicit-fresh-runtime')


def test_close_before_initial_configuration_is_terminal_too():
    value = WorkflowRuntime(None, None, ())
    value.close_order_admissions()
    value.configure_modules({'tp': 900})
    with pytest.raises(RuntimeError, match='ORDER_ADMISSIONS_CLOSED'):
        value.configure_order_leases(2)


@pytest.mark.parametrize('stop_first', [True, False])
def test_stop_at_claim_dispatch_boundary_cancels_reservation_or_drains_actual_work(stop_first):
    value = runtime()
    value.request_order_lease(SHEET, 1, 'one')
    lease = value.try_claim_order_lease('one')
    if stop_first:
        # Stop may originate on GUI thread; only admitting owner releases.
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(value.close_order_admissions).result()
        assert value.begin_order_dispatch(lease) is False
        value.cancel_reserved_order_lease(lease)
    else:
        assert value.begin_order_dispatch(lease) is True
        value.close_order_admissions()
        with pytest.raises(RuntimeError, match='ORDER_STILL_RUNNING'):
            value.cancel_reserved_order_lease(lease)
        value.release_order_lease(lease)  # actual worker terminal acknowledged
    assert value.order_resource_counts()['active'] == 0
    with pytest.raises(OrderResourceOwnershipError):
        value.begin_order_dispatch(lease)


def test_dispatch_identity_and_duplicate_dispatch_are_strict():
    value = runtime()
    value.request_order_lease(SHEET, 1, 'one')
    lease = value.try_claim_order_lease('one')
    with pytest.raises(OrderResourceOwnershipError):
        value.begin_order_dispatch(replace(lease))
    with ThreadPoolExecutor(max_workers=1) as pool, pytest.raises(OrderResourceOwnershipError):
        pool.submit(value.begin_order_dispatch, lease).result()
    assert value.begin_order_dispatch(lease)
    with pytest.raises(RuntimeError, match='ORDER_ALREADY_DISPATCHED'):
        value.begin_order_dispatch(lease)
    value.release_order_lease(lease)


def test_busy_source_waiters_do_not_fill_other_sources_execution_budget():
    value = runtime(2)
    for token in ['inquiry', 'quotation', 'tp']:
        assert value.request_order_lease(SHEET, 1, token)
    assert not value.request_order_lease(SHEET, 1, 'extra')
    assert value.request_order_lease(SHEET, 2, 'independent-tp')
    first = value.try_claim_order_lease('inquiry')
    independent = value.try_claim_order_lease('independent-tp')
    assert first is not None and independent is not None
    assert value.try_claim_order_lease('quotation') is None
    value.release_order_lease(independent)
    value.release_order_lease(first)
    next_one = value.try_claim_order_lease('quotation')
    assert next_one is not None
    value.release_order_lease(next_one)
    last = value.try_claim_order_lease('tp')
    value.release_order_lease(last)
    assert value.order_resource_counts()['waiting'] == 0
