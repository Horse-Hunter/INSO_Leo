"""CEO blockers: production reviewer and crash boundaries, entirely synthetic."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.sheets import WorksheetRow
from src.workflow.v12_contracts import (
    NotificationCommand,
    NotificationKind,
    NotificationRecipient,
)
from tests.workflow.test_rfq016_regressions import production_scene, real_fake_smtp
from tests.workflow.test_v12_flow import NOW, SHEET
from tests.workflow.test_v13_quote_update import found, service


def test_unknown_refresh_persists_before_price_or_notice():
    updater, *_ = service()
    events = []
    updater._persist_uncertain = lambda result: events.append("hold")
    updater._notify_refresh_uncertain = lambda *args: events.append("notice")
    updater._prices = SimpleNamespace(record=lambda *args: events.append("price"))
    updater._uncertain_refresh(found(), Decimal(10), Decimal(8))
    assert events == ["hold", "notice", "price"]


def test_stale_source_three_cycles_never_sends_order_alert(tmp_path):
    backend, _, queue, ledger, _, _, _ = production_scene(tmp_path)
    backend._site_outages["Google Sheets"] = 0
    backend._source_projection.observe(SHEET, (), queue.all_items(), at=NOW, failed=True)
    for cycle in range(3):
        backend._cycle_id = str(cycle)
        at = NOW + timedelta(hours=3)
        backend._notify_runtime_fault(str(cycle), "GOOGLE_OUTAGE_THREE_HOURS", at=at)
    worker, smtp = real_fake_smtp(ledger, now=at, review_current=backend._review_current_mail)
    worker.run_due(now=at)
    assert smtp.send_attempts == 0
    backend.shutdown()


@pytest.mark.parametrize("kind", [NotificationKind.IMPORTANT_ORDER, NotificationKind.DUPLICATE_ORDER])
def test_completed_customer_suppresses_original_business_notice(tmp_path, kind):
    backend, _, queue, ledger, reader, record, iid = production_scene(tmp_path)
    ledger.enqueue_notification(NotificationCommand("old-new-order", iid, kind,
        (NotificationRecipient("owner", "linan229@qq.com"),), "重要询价", "待跟进", None, NOW))
    reader.row = WorksheetRow(record.row_position, {**reader.row.cells, "A": "已报价给客户"})
    backend._source_projection.observe(SHEET, (reader.row,), queue.all_items(), at=NOW)
    worker, smtp = real_fake_smtp(ledger, now=NOW, review_current=backend._review_current_mail)
    worker.run_due(now=NOW)
    assert smtp.send_attempts == 0
    backend.shutdown()


@pytest.mark.parametrize("boundary", ["hold_before", "hold_after", "notify", "price_before", "price_after"])
def test_native_dispatch_crash_restart_preserves_unknown_and_one_alert(tmp_path, boundary):
    from src.workflow.v13_price_store import ProcurementPriceStore
    from src.workflow.v13_quote_update import (
        V13QuotationUpdater,
        WorkflowQuotationSource,
    )
    from tests.inso.test_v13_quotation_read import quote
    from tests.workflow.test_rfq006_integration import NOW as AT
    from tests.workflow.test_rfq006_integration import fixture
    from tests.workflow.test_rfq016_regressions import real_fake_smtp
    from tests.workflow.test_v13_quotation import WS, source
    from tests.workflow.test_v13_quote_update import Actions, Input, Source

    class Crash(BaseException):
        pass
    raw = list(quote().payload)
    raw[7] = "8"
    quoted = replace(quote(), payload=tuple(raw))
    db, items, sheets, holds, ledger, _, make, _ = fixture(tmp_path, [(quoted,), (quoted,)])
    sheets.rows = [source(2, "采购已报价")]
    inquiry = items.all_items()[0].inquiry_id
    prices = ProcurementPriceStore(db)
    prices.migrate(); prices.record(inquiry, Decimal(10))
    actions = Actions(Source()); actions.popups = ["unknown"]
    def persist(pending):
        if boundary == "hold_before":
            raise Crash()
        token = holds.hold(replace(pending, quotation=None), pending.record_identity)
        if boundary == "hold_after":
            raise Crash()
        return token
    def notify(*_):
        if boundary == "notify":
            raise Crash()
    original_record = prices.record
    def record(*args):
        assert holds.active(), "price must never advance without durable UNKNOWN"
        if boundary == "price_before":
            raise Crash()
        original_record(*args)
        if boundary == "price_after":
            raise Crash()
    prices.record = record
    updater = V13QuotationUpdater(source=WorkflowQuotationSource(reader=sheets, store=items),
        quotation_input=Input(), actions=actions, wait=lambda _: False, price_store=prices,
        persist_uncertain=persist, notify_refresh_uncertain=notify)
    integrated = make()
    integrated.updater_factory = lambda: updater
    with pytest.raises(Crash):
        integrated.run(WS)
    assert actions.clicks == 1 and holds.active()
    prices.record = original_record
    for _ in range(2):
        assert make(updater.update_one).run(WS) == ()
    worker, smtp = real_fake_smtp(ledger, now=AT)
    worker.run_due(now=AT); worker.run_due(now=AT)
    assert actions.clicks == 1 and smtp.send_attempts == 1
