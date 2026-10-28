"""Offline automatic7d gate; no production config/browser/database/SMTP."""
import sqlite3
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.launcher.google_web import GoogleSheetsWebService
from src.sheets.tp_brief import BRIEF_HEADERS, BriefLine, BriefReader
from src.workflow.quotation_age import age_reason, quotation_age_date
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_quotation import QuotationOutcome, V13Candidate, V13Stopped
from tests.inso.test_v13_quotation_read import NOW
from tests.workflow.test_v13_quotation import WS, cycle, item, source


@pytest.mark.parametrize('value,expected', [
    (NOW, None), (NOW-timedelta(days=6), None), (NOW-timedelta(days=7), None),
    (NOW-timedelta(days=7, microseconds=1), 'QUOTE_AGE_EXPIRED'),
    (NOW-timedelta(days=8), 'QUOTE_AGE_EXPIRED'),
    (NOW+timedelta(microseconds=1), 'QUOTE_AGE_UNVERIFIED'),
    (NOW.replace(tzinfo=None), 'QUOTE_AGE_UNVERIFIED'),
    (None, 'QUOTE_AGE_UNVERIFIED'), ('invalid', 'QUOTE_AGE_UNVERIFIED'),
    (date(2026, 9, 30), None), (date(2026, 9, 29), 'QUOTE_AGE_EXPIRED'),
    (date(2026, 10, 8), 'QUOTE_AGE_UNVERIFIED'),
])
def test_calendar_and_rolling_boundaries(value, expected):
    assert age_reason(value, NOW) == expected


def test_shanghai_day_not_utc_day_and_naive_clock():
    utc = NOW.astimezone(UTC)  # UTC is still October6, Shanghai is October7.
    assert age_reason(date(2026, 9, 30), utc) is None
    assert age_reason(date(2026, 9, 29), utc) == 'QUOTE_AGE_EXPIRED'
    assert age_reason(NOW, NOW.replace(tzinfo=None)) == 'QUOTE_AGE_UNVERIFIED'
    instant = datetime(2026, 11, 3, tzinfo=ZoneInfo('America/New_York'))
    assert age_reason(instant.astimezone(UTC)-timedelta(days=7), instant) is None


@pytest.mark.parametrize('age,expected', [(8,'QUOTE_AGE_EXPIRED'), (None,'QUOTE_AGE_UNVERIFIED')])
def test_real_query_loop_skips_before_tab_query_retry_and_side_effect(age, expected):
    service, ops, quotes, waits = cycle([], sources=[source(2, '已报价给客户')])
    service._store.inquiry_intake_at = lambda _: None if age is None else NOW-timedelta(days=age)
    result, = service.run(WS)
    assert result.outcome.value == expected and result.quotation is None
    assert ops.events == quotes.calls == waits == []
    assert service.quote_age_skips[expected] == 1


@pytest.mark.parametrize('status', ['发给采购', '采购已报价'])
def test_other_statuses_never_use_age_or_brief(status):
    service, ops, quotes, _ = cycle([()], sources=[source(2,status)])
    service._store.inquiry_intake_at = lambda _: pytest.fail('age lookup for unaffected status')
    service._brief_snapshot = lambda _: pytest.fail('Brief lookup for unaffected status')
    assert service.run(WS)[0].outcome is QuotationOutcome.NO_RECENT_QUOTE
    assert len(quotes.calls) == 1 and len(ops.events) == 2


def test_explicit_manual_scope_keeps_existing_authorization_path():
    service, _ops, quotes, _ = cycle([()], sources=[source(2,'已报价给客户')])
    service._automatic_refresh = False
    service._store.inquiry_intake_at = lambda _: pytest.fail('manual age gate')
    assert service.run(WS)[0].outcome is QuotationOutcome.NO_RECENT_QUOTE
    assert len(quotes.calls) == 1


def test_clock_crosses_cutoff_before_execute_not_discovery():
    service, ops, quotes, _ = cycle([], sources=[source(2,'已报价给客户')])
    candidate, = service.read_candidates(WS)
    service._store.inquiry_intake_at = lambda _: NOW-timedelta(days=7)
    service._clock = lambda: NOW+timedelta(microseconds=1)
    assert service.execute_candidate(candidate,WS).outcome is QuotationOutcome.QUOTE_AGE_EXPIRED
    assert not ops.events and not quotes.calls


def brief(day='2026-09-30', **changes):
    data={'sheet':'2026','sheet_row':'2','mpn':'MPN','mfr':'brand','qty':'5','rfq_date':day}
    data.update(changes)
    return BriefLine(2,tuple(data.get(h,'') for h in BRIEF_HEADERS))


def test_unique_cached_brief_precedes_intake_and_does_not_require_target_price():
    ws=replace(WS,worksheet='2026');i=item(2)
    candidate=V13Candidate(i.inquiry_id,replace(i.record_identity,worksheet=ws),'MPN',2,'已报价给客户')
    value,kind=quotation_age_date(candidate,source(2,'已报价给客户'),[brief()],lambda:pytest.fail('fallback'))
    assert value == date(2026,9,30) and kind == 'RFQ_DATE_PROXY'


@pytest.mark.parametrize('lines', [[brief(),brief('2026-10-06')], [brief(mpn='OTHER')],
    [brief(qty='6')], [brief(mfr='OTHER')], [brief(sheet_row='99')], [brief(sheet='SHAHAB')]])
def test_ambiguous_or_conflicting_brief_never_selects_an_arbitrary_date(lines):
    i=item(2);ws=replace(WS,worksheet='2026')
    candidate=V13Candidate(i.inquiry_id,replace(i.record_identity,worksheet=ws),'MPN',2,'已报价给客户')
    assert quotation_age_date(candidate,source(2,'已报价给客户'),lines,lambda:NOW) == (NOW,'LOCAL_INTAKE_PROXY')


@pytest.mark.parametrize('day', ['invalid','2026-10-08'])
def test_bad_selected_brief_date_is_unverified_not_recent_fallback(day):
    i=item(2);ws=replace(WS,worksheet='2026')
    candidate=V13Candidate(i.inquiry_id,replace(i.record_identity,worksheet=ws),'MPN',2,'已报价给客户')
    value,_=quotation_age_date(candidate,source(2,'已报价给客户'),[brief(day)],lambda:NOW)
    assert age_reason(value,NOW) == 'QUOTE_AGE_UNVERIFIED'


def test_cache_peek_never_acquires_client_or_downloads_and_is_detached():
    time=[0.0];svc=GoogleSheetsWebService(lambda:pytest.fail('session opened'),timer=lambda:time[0])
    reader=BriefReader(svc)
    assert reader.cached_lines('fake') == ()
    svc._remember(('fake','RFQ_BRIEF'),[BRIEF_HEADERS,brief().values])
    assert reader.cached_lines('fake') == (brief(),)
    copy=svc.peek_brief_snapshot('fake');copy['values'][1][4]='CHANGED'
    assert reader.cached_lines('fake')[0].get('mpn') == 'MPN'
    time[0]=60
    assert reader.cached_lines('fake') == ()
    svc._stop_requested=lambda:True
    with pytest.raises(V13Stopped):reader.cached_lines('fake')


def test_shared_failure_not_disguised_as_age_skip():
    service, ops, _, _=cycle([],sources=[source(2,'已报价给客户')])
    def fail(_):raise sqlite3.OperationalError('synthetic DB failure')
    service._store.inquiry_intake_at=fail
    with pytest.raises(V12Fault) as exc:service.run(WS)
    assert exc.value.reason == 'WORKFLOW_LEDGER_UNAVAILABLE'
    assert exc.value.scope is FaultScope.GLOBAL_STOP and not ops.events


@pytest.mark.parametrize('raw', ['2026-09-01T00:00:00+00:00','bad','2026-10-06T00:00:00'])
def test_actual_store_and_integrated_owner_skip_do_not_write_quote_or_mail(tmp_path,raw):
    from tests.workflow.test_rfq006_integration import NOW as clock
    from tests.workflow.test_rfq006_integration import fixture
    db,store,sheets,holds,_ledger,quotes,make,_=fixture(tmp_path,[])
    sheets.rows=[source(2,'已报价给客户')]
    with sqlite3.connect(db) as conn:
        conn.execute('UPDATE workflow_items SET created_at=?',(raw,))
        before=list(conn.iterdump())
    flow=make(lambda _:pytest.fail('quote updater called'))
    flow.cycle._clock=lambda:clock
    result,=flow.run(WS)
    assert result.outcome in {QuotationOutcome.QUOTE_AGE_EXPIRED,QuotationOutcome.QUOTE_AGE_UNVERIFIED}
    assert not quotes.calls and not holds.active()
    with sqlite3.connect(db) as conn:
        assert list(conn.iterdump()) == before
    inquiry=store.all_items()[0].inquiry_id
    if raw in {'bad','2026-10-06T00:00:00'}:
        assert store.inquiry_intake_at(inquiry) is None
    else:
        assert store.inquiry_intake_at(inquiry) is not None


def test_created_at_immutable_across_enqueue_and_lifecycle_updates(tmp_path):
    from src.sheets import query_pending_records
    from src.workflow.store import WorkflowStateStore
    from tests.workflow.test_v13_quotation import Sheets
    db=tmp_path/'synthetic.sqlite3';store=WorkflowStateStore(db)
    row,=query_pending_records(Sheets([source(2,'未发')]),WS)
    assert store.enqueue(row,now=NOW-timedelta(days=8))
    inquiry=store.all_items()[0].inquiry_id
    first=store.inquiry_intake_at(inquiry)
    assert not store.enqueue(row,now=NOW)
    store.claim_due(now=NOW)
    assert store.inquiry_intake_at(inquiry) == first == NOW-timedelta(days=8)
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT updated_at FROM workflow_items').fetchone()[0] != first.isoformat()
    assert store.inquiry_intake_at('missing-id') is None


@pytest.mark.parametrize('delta', [timedelta(),timedelta(days=6),timedelta(days=7)])
def test_recent_customer_row_reaches_original_inso_query(delta):
    service,ops,quotes,_=cycle([()],sources=[source(2,'已报价给客户')])
    service._store.inquiry_intake_at=lambda _:NOW-delta
    assert service.run(WS)[0].outcome is QuotationOutcome.NO_RECENT_QUOTE
    assert len(quotes.calls)==1 and len(ops.tabs)==1


@pytest.mark.parametrize('day,expected', [('2026-09-29','QUOTE_AGE_EXPIRED'),('2026-10-08','QUOTE_AGE_UNVERIFIED'),('bad','QUOTE_AGE_UNVERIFIED')])
def test_actual_bound_brief_proxy_gate_overrides_recent_local_intake(day,expected):
    service,ops,quotes,_=cycle([],sources=[source(2,'已报价给客户')])
    ws=replace(WS,worksheet='2026')
    service._store.items[0].record_identity=replace(service._store.items[0].record_identity,worksheet=ws)
    service._reader.read_rows=lambda _: [source(2,'已报价给客户')]
    service._brief_snapshot=lambda _: [brief(day)]
    result,=service.run(ws)
    assert result.outcome.value==expected and service.quote_age_date_source=='RFQ_DATE_PROXY'
    assert not ops.events and not quotes.calls


def test_stop_during_optional_date_lookup_does_not_become_an_age_skip():
    stopped=[False]
    service,ops,_,_=cycle([],sources=[source(2,'已报价给客户')],stop=lambda:stopped[0])
    def snapshot(_):
        stopped[0]=True
        return ()
    service._brief_snapshot=snapshot
    with pytest.raises(V13Stopped):service.run(WS)
    assert not ops.events and sum(service.quote_age_skips.values())==0


def test_cache_peek_preserves_shared_safety_admission():
    def guard():raise V12Fault(FaultScope.GLOBAL_STOP,'CDP_PAGE_OWNERSHIP_UNCONFIRMED')
    svc=GoogleSheetsWebService(lambda:pytest.fail('session'),read_guard=guard)
    with pytest.raises(V12Fault) as exc:BriefReader(svc).cached_lines('fake')
    assert exc.value.reason=='CDP_PAGE_OWNERSHIP_UNCONFIRMED'


@pytest.mark.parametrize('include_current', [False,True])
def test_relocated_record_never_takes_date_of_occupant_at_old_position(include_current):
    service,ops,quotes,_=cycle([],sources=[source(2,'已报价给客户')])
    ws=replace(WS,worksheet='2026')
    service._store.items[0].record_identity=replace(service._store.items[0].record_identity,worksheet=ws)
    calls=[0]
    def read(_):
        calls[0]+=1
        return ([source(2,'已报价给客户')] if calls[0]==1 else
                [source(2,'已报价给客户',model='OTHER'),source(3,'已报价给客户')])
    service._reader.read_rows=read
    service._store.inquiry_intake_at=lambda _:NOW-timedelta(days=8)
    lines=[brief('2026-10-06',mpn='OTHER')]
    if include_current:lines.append(brief('2026-09-29',sheet_row='3'))
    service._brief_snapshot=lambda _:lines
    result,=service.run(ws)
    assert result.outcome is QuotationOutcome.QUOTE_AGE_EXPIRED
    assert service.quote_age_date_source==('RFQ_DATE_PROXY' if include_current else 'LOCAL_INTAKE_PROXY')
    assert not ops.events and not quotes.calls


@pytest.mark.parametrize('bound', [False,True])
def test_unbound_or_ambiguous_customer_identity_has_only_sanitized_counter(bound):
    service,ops,quotes,_=cycle([],sources=[source(2,'已报价给客户')],
                               items=[item(2),item(2)] if bound else [])
    assert service.run(WS)==()
    assert service.quote_age_skips=={'QUOTE_AGE_EXPIRED':0,'QUOTE_AGE_UNVERIFIED':1}
    assert not ops.events and not quotes.calls
