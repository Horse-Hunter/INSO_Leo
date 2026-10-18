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
def test_skip_or_unconfirmed_popup_never_advances_baseline(popup):
    updater, result, _, actions, prices, _ = refresh('已报价给客户', '10', '8')
    actions.popups = [popup]
    final = updater.update_one(result)
    assert final.outcome is QuotationOutcome.ROW_FAILED
    assert final.row_error_reason is RowErrorReason.UPDATE_RESULT_UNCONFIRMED
    assert not prices.writes


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
