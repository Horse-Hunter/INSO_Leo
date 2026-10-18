import sqlite3
from dataclasses import replace
from decimal import Decimal

import pytest

from src.workflow.v13_quotation import QuotationOutcome, RowErrorReason
from tests.workflow.test_v13_quote_update import EXISTS, POPUP, found, service


class Prices:
    def __init__(self, value=None):
        self.value, self.writes = value, []

    def get(self, inquiry):
        return self.value

    def record(self, inquiry, price):
        self.writes.append((inquiry, price))
        self.value = price


def refresh(status, baseline, price):
    updater, source, io, actions, _ = service()
    source.before = status
    source.after = [status]
    prices = Prices(None if baseline is None else Decimal(baseline))
    updater._prices = prices
    result = replace(found(), source_status=status)
    raw = list(result.quotation.payload)
    raw[7] = price
    result = replace(result, quotation=replace(result.quotation, payload=tuple(raw)))
    return updater, result, io, actions, prices, source


@pytest.mark.parametrize('status', ['采购已报价', '已报价给客户'])
@pytest.mark.parametrize('price', ['0', '12.3'])
def test_existing_record_first_observation_only_bootstraps(status, price):
    updater, result, io, actions, prices, _ = refresh(status, None, price)
    assert updater.update_one(result).outcome is QuotationOutcome.BASELINE_RECORDED
    assert prices.value == Decimal(price)
    assert not io.writes and not actions.opened


@pytest.mark.parametrize('status', ['采购已报价', '已报价给客户'])
@pytest.mark.parametrize('baseline,price,expected', [
    ('10', '9', True), ('10', '10', False), ('10', '11', False),
    ('0', '5', True), ('0', '0', False), ('10', '0', False),
])
def test_refresh_only_lower_or_zero_to_positive_preserves_status(status, baseline, price, expected):
    updater, result, io, actions, prices, source = refresh(status, baseline, price)
    final = updater.update_one(result)
    assert final.outcome is (QuotationOutcome.UPDATED_INSERTED if expected else QuotationOutcome.PRICE_UNCHANGED)
    assert actions.clicks == int(expected)
    assert len(prices.writes) == int(expected)
    assert source.after == [status]
    if expected:
        assert len(io.writes) == 1 and actions.closed == 1
        assert prices.value == Decimal(price)


@pytest.mark.parametrize('popup', [EXISTS, '未知结果'])
def test_skip_or_unconfirmed_refresh_records_comparison_only(popup):
    updater, result, _, actions, prices, _ = refresh('已报价给客户', '10', '8')
    actions.popups = [popup]
    final = updater.update_one(result)
    assert final.outcome is QuotationOutcome.BASELINE_RECORDED
    assert final.row_error_reason is RowErrorReason.UPDATE_RESULT_UNCONFIRMED
    assert prices.value == Decimal(8) and actions.clicks == 1


def test_refresh_status_change_does_not_count_as_success():
    updater, result, _, _, prices, source = refresh('已报价给客户', '10', '8')
    source.after = ['采购已报价']
    assert updater.update_one(result).row_error_reason is RowErrorReason.SOURCE_CHANGED
    assert not prices.writes


def test_new_popup_supplementary_warnings_do_not_hide_one_insert():
    updater, result, _, actions, prices, _ = refresh('采购已报价', '10', '8')
    actions.popups = [POPUP + '\n状态已推进为「采购已报价」：0行\n红色包装尾缀匹配（请复核）：TEST-A <- TEST-A01\n需确认：TEST-A：量不足']
    assert updater.update_one(result).outcome is QuotationOutcome.UPDATED_INSERTED
    assert prices.value == Decimal(8)


def test_price_store_is_additive_durable_minimum_and_requires_real_inquiry(tmp_path):
    from src.workflow.v12_faults import V12Fault
    from src.workflow.v13_price_store import ProcurementPriceStore
    from tests.workflow.test_rfq006_integration import fixture

    db, store, *_ = fixture(tmp_path, [])
    inquiry = store.all_items()[0].inquiry_id
    with sqlite3.connect(db) as connection:
        version = connection.execute('PRAGMA user_version').fetchone()[0]
    prices = ProcurementPriceStore(db)
    prices.migrate()
    prices.migrate()
    assert prices.get(inquiry) is None
    prices.record(inquiry, Decimal(0))
    prices.record(inquiry, Decimal('8.125'))
    prices.record(inquiry, Decimal(9))
    prices.record(inquiry, Decimal(0))
    assert ProcurementPriceStore(db).get(inquiry) == Decimal('8.125')
    prices.record(inquiry, Decimal(7))
    assert prices.get(inquiry) == Decimal(7)
    with pytest.raises(V12Fault):
        prices.record('not-an-inquiry', Decimal(1))
    with sqlite3.connect(db) as connection:
        assert connection.execute('PRAGMA user_version').fetchone()[0] == version
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
        assert len(connection.execute('SELECT * FROM workflow_items').fetchall()) == 1


@pytest.mark.parametrize('status', ['采购已报价', '已报价给客户'])
def test_refresh_candidate_keeps_original_internal_identity_and_status(status):
    from tests.inso.test_v13_quotation_read import quote
    from tests.workflow.test_v13_quotation import WS, cycle, item, source
    original = item(2)
    service, _, _, _ = cycle([(quote(),)], sources=[source(12,status)], items=[original])
    result, = service.run(WS)
    assert result.inquiry_id == original.inquiry_id
    assert result.record_identity is original.record_identity
    assert result.source_status == status and result.source_row_position == 12


@pytest.mark.parametrize('status', ['采购已报价', '已报价给客户'])
def test_refresh_hold_not_settled_by_unchanged_quoted_status(tmp_path, status):
    from tests.inso.test_v13_quotation_read import quote
    from tests.workflow.test_rfq006_integration import fixture
    from tests.workflow.test_v13_quotation import WS, source
    _, _, sheets, holds, _, quotes, make, _ = fixture(tmp_path, [(quote(),)])
    sheets.rows = [source(2,status)]
    make(lambda r: replace(r,outcome=QuotationOutcome.ROW_FAILED,
        row_error_reason=RowErrorReason.UPDATE_RESULT_UNCONFIRMED)).run(WS)
    before = holds.active()
    make().run(WS)
    assert holds.active() == before and len(quotes.calls) == 1


def test_different_currency_reuses_canonical_supplier_net_price_conversion():
    updater, result, _, actions, prices, _ = refresh('采购已报价', '60', '7')
    raw = list(result.quotation.payload)
    raw[4] = 'USD'
    raw[6] = '99999'  # List price/customer markup must not be the baseline.
    result = replace(result, quotation=replace(result.quotation,payload=tuple(raw)))
    updater._currency_rate = lambda currency: Decimal(8)
    assert updater.update_one(result).outcome is QuotationOutcome.UPDATED_INSERTED
    assert prices.value == Decimal(56) and actions.clicks == 1


@pytest.mark.parametrize('six_uncertain', [False, True])
def test_10_to_8_uncertain_then_8_skips_then_6_updates_with_real_store_outbox_and_cycle(tmp_path, six_uncertain):
    from src.launcher.v13_integration import notify_refresh_uncertain, quotation_gui
    from src.workflow.v13_price_store import ProcurementPriceStore
    from src.workflow.v13_quote_update import (
        V13QuotationUpdater,
        WorkflowQuotationSource,
    )
    from tests.inso.test_v13_quotation_read import quote
    from tests.workflow.test_rfq006_integration import NOW, fixture
    from tests.workflow.test_v13_quotation import WS, source
    from tests.workflow.test_v13_quote_update import Actions, Input, Source

    def priced(value):
        raw = list(quote().payload)
        raw[7] = value
        return quote(payload=tuple(raw))
    db, store, sheets, holds, ledger, _, make, _ = fixture(tmp_path,
        [(priced('8'),), (priced('8'),), (priced('9'),), (priced('6'),), (priced('6'),)])
    sheets.rows = [source(2, '采购已报价')]
    inquiry = store.all_items()[0].inquiry_id
    prices = ProcurementPriceStore(db)
    prices.migrate()
    prices.record(inquiry, Decimal(10))
    actions = Actions(Source())
    actions.popups = ['未知结果']
    updater = V13QuotationUpdater(source=WorkflowQuotationSource(reader=sheets,store=store),
        quotation_input=Input(), actions=actions, wait=lambda _: False, price_store=prices,
        notify_refresh_uncertain=lambda r, old, new: notify_refresh_uncertain(ledger,r,old,new,at=NOW))
    first, = make(updater.update_one).run(WS)
    assert first.outcome is QuotationOutcome.BASELINE_RECORDED and first.row_error_reason
    assert '不确定' in quotation_gui(first,inquiry).waiting_label
    assert '已更新' not in quotation_gui(first,inquiry).waiting_label
    assert prices.get(inquiry) == Decimal(8) and actions.clicks == 1 and not holds.active()
    second, = make(updater.update_one).run(WS)
    assert second.outcome is QuotationOutcome.PRICE_UNCHANGED and actions.clicks == 1
    higher, = make(updater.update_one).run(WS)
    assert higher.outcome is QuotationOutcome.PRICE_UNCHANGED and actions.clicks == 1
    actions.popups = ['未知结果' if six_uncertain else POPUP]
    third, = make(updater.update_one).run(WS)
    assert third.outcome is (QuotationOutcome.BASELINE_RECORDED if six_uncertain else QuotationOutcome.UPDATED_INSERTED)
    assert prices.get(inquiry) == Decimal(6) and actions.clicks == 2 and not holds.active()
    fourth, = make(updater.update_one).run(WS)
    assert fourth.outcome is QuotationOutcome.PRICE_UNCHANGED and actions.clicks == 2
    # Re-delivering the same callback, including equivalent Decimal formatting,
    # must use the real mailbox's existing dedup contract.
    notify_refresh_uncertain(ledger, first, Decimal('10.00'), Decimal('8.000'), at=NOW)
    with sqlite3.connect(db) as connection:
        commands = connection.execute('SELECT subject,text_body FROM workflow_v12_notification_commands').fetchall()
        recipients = connection.execute('SELECT address FROM workflow_v12_notification_recipients').fetchall()
    assert len(commands) == 1 + int(six_uncertain)
    assert {address for address, in recipients} == {'linan229@qq.com'}
    assert all('Google写入结果不确定' in body and '请人工核对' in body for _,body in commands)
    assert '原采购价：10元' in commands[0][1] and '新采购价：8元' in commands[0][1]
    assert not holds.active()


@pytest.mark.parametrize('stage', ['preclick', 'click_dispatch', 'result_read', 'settlement'])
def test_only_possible_dispatch_advances_uncertain_baseline(stage):
    from src.workflow.v13_quote_update import (
        UpdateAttemptUnconfirmed,
        UpdateClickUnconfirmed,
    )
    updater, result, _, actions, prices, _ = refresh('已报价给客户','10','8')
    notices=[]
    updater._notify_refresh_uncertain=lambda r,old,new: notices.append((r,old,new))
    if stage == 'preclick':
        actions.open_quote_input=lambda: (_ for _ in ()).throw(UpdateAttemptUnconfirmed('not ready'))
    elif stage == 'click_dispatch':
        def uncertain_click():
            actions.clicks += 1
            raise UpdateClickUnconfirmed('may have executed')
        actions.click_update_quote=uncertain_click
    elif stage == 'result_read':
        actions.popups=[RuntimeError('PRIVATE_PROVIDER_TEXT')]
    else:
        from src.workflow.v12_faults import FaultScope, V12Fault
        actions.dismiss_error=V12Fault(FaultScope.GLOBAL_STOP,'GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED')
    final=updater.update_one(result)
    if stage == 'preclick':
        assert final.outcome is QuotationOutcome.ROW_FAILED
        assert prices.value == Decimal(10) and not notices and actions.clicks == 0
    else:
        assert final.outcome is QuotationOutcome.BASELINE_RECORDED
        assert prices.value == Decimal(8) and len(notices)==1 and actions.clicks==1


def test_busy_input_defers_without_baseline_mail_or_hold_outcome():
    from src.sheets.quotation_input import QuotationInputBusy
    updater,result,io,actions,prices,_=refresh('采购已报价','10','8')
    actions.open_quote_input=lambda: (_ for _ in ()).throw(QuotationInputBusy('busy'))
    assert updater.update_one(result) is result
    assert prices.value==Decimal(10) and not io.writes and not actions.clicks


def test_preclick_retry_rearms_refresh_protection_before_its_first_dispatch():
    from src.workflow.v13_quote_update import UpdateAttemptUnconfirmed
    updater,result,_,actions,prices,_=refresh('采购已报价','10','8')
    opened,closed,clicked=actions.open_quote_input,actions.close,actions.click_update_quote
    state={'refresh':False,'prepared':0,'opens':0}
    def prepare():
        state['refresh']=True
        state['prepared']+=1
    def close():
        closed()
        state['refresh']=False
    def open_once():
        state['opens']+=1
        if state['opens']==1:
            raise UpdateAttemptUnconfirmed('preclick load failure')
        opened()
    def click():
        assert state['refresh']
        clicked()
    actions.prepare_price_refresh,actions.open_quote_input=prepare,open_once
    actions.close,actions.click_update_quote=close,click
    actions.popups=['未知结果']
    assert updater.update_one(result).outcome is QuotationOutcome.BASELINE_RECORDED
    assert state['prepared']==2 and actions.clicks==1 and prices.value==Decimal(8)


def test_uncertain_refresh_does_not_block_following_order(tmp_path):
    from src.launcher.v13_integration import notify_refresh_uncertain
    from src.sheets import query_pending_records
    from src.workflow.v13_price_store import ProcurementPriceStore
    from src.workflow.v13_quote_update import (
        V13QuotationUpdater,
        WorkflowQuotationSource,
    )
    from tests.inso.test_v13_quotation_read import quote
    from tests.workflow.test_rfq006_integration import NOW, fixture
    from tests.workflow.test_v13_quotation import WS, source
    from tests.workflow.test_v13_quote_update import Actions, Input, Source
    raw=list(quote().payload)
    raw[7]='8'
    first=quote(payload=tuple(raw))
    raw[1],raw[7]='SECOND','6'
    second=quote(payload=tuple(raw))
    _,store,sheets,holds,ledger,_,make,_=fixture(tmp_path,[(first,),(second,)])
    sheets.rows=[source(3,'未发',model='SECOND')]
    record,=query_pending_records(sheets,WS)
    store.enqueue(record,now=NOW)
    sheets.rows=[source(2,'采购已报价'),source(3,'已报价给客户',model='SECOND')]
    prices=ProcurementPriceStore(store.database_path)
    prices.migrate()
    for item in store.all_items():
        prices.record(item.inquiry_id,Decimal(10))
    actions=Actions(Source())
    actions.popups=['未知结果',POPUP]
    updater=V13QuotationUpdater(source=WorkflowQuotationSource(reader=sheets,store=store),
        quotation_input=Input(),actions=actions,wait=lambda _:False,price_store=prices,
        notify_refresh_uncertain=lambda r,old,new:notify_refresh_uncertain(ledger,r,old,new,at=NOW))
    results=make(updater.update_one).run(WS)
    assert [r.outcome for r in results]==[QuotationOutcome.BASELINE_RECORDED,QuotationOutcome.UPDATED_INSERTED]
    assert actions.clicks==2 and not holds.active()
