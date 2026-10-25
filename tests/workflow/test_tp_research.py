import sqlite3
from contextlib import nullcontext
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.research.source_contracts import PRICE_SOURCES, SourceEvidence, SourceOutcome
from src.research.tp import TpQuote, TpResearchResult, TpSourceResult
from src.workflow.store import WorkflowStateStore
from src.workflow.tp_research import TpCycle, TpStore, task_key, tp_mail
from src.workflow.v12_contracts import DeliveryOutcome
from src.workflow.v12_notifications import (
    FakeNotificationTransport,
    V12NotificationWorker,
)
from src.workflow.v12_store import V12Store, migrate_v12
from src.workflow.v13_integration import V13HoldStore
from tests.research.test_tp import NOW, offer
from tests.sheets.test_tp_brief import brief, source


class Research:
    def __init__(self):
        self.calls = []
        self.hook = lambda: None

    def execute_tp(self, key, order, *, now):
        self.calls.append((key, order))
        self.hook()
        q = TpQuote(offer("1"), Decimal(1))
        results = tuple(TpSourceResult(s, SourceOutcome.SUCCESS,
            SourceEvidence(s, order.mpn, None, SourceOutcome.SUCCESS, now),
            (replace(q, offer=replace(q.offer, source=s)),)) for s in PRICE_SOURCES)
        return TpResearchResult(results, q, None, "货少", Decimal(14), Decimal(100), Decimal(7))


def build(tmp_path, outcomes=(DeliveryOutcome.SENT,)):
    path = tmp_path / "synthetic.sqlite3"
    WorkflowStateStore(path)
    migrate_v12(path, tmp_path / "backups", quiesce=lambda: nullcontext())
    V13HoldStore(path).migrate()
    store, outbox = TpStore(path), V12Store(path)
    store.migrate()
    transport = FakeNotificationTransport({"owner": outcomes})
    worker = V12NotificationWorker(outbox, transport)
    lines = [brief()]
    reader = SimpleNamespace(rows=[source()], read_rows=lambda _: tuple(reader.rows))
    research = Research()
    cycle = TpCycle(store=store, brief=SimpleNamespace(read=lambda _: tuple(lines)),
        reader=reader, research=research, outbox=outbox, worker=worker)
    return cycle, lines, reader, transport, path


def test_historical_no_inquiry_15_minute_polls_tp_edits_and_manual_generation(tmp_path):
    cycle, lines, _reader, transport, path = build(tmp_path, (DeliveryOutcome.SENT, DeliveryOutcome.SENT))
    for i in range(4):
        cycle.run("synthetic", now=NOW+timedelta(minutes=15*i))
    key = task_key("synthetic", "2026", 10)
    assert len(cycle.research.calls) == len(transport.calls) == 1
    lines[0] = brief(price="3 USD")
    cycle.run("synthetic", now=NOW+timedelta(hours=2))
    assert len(cycle.research.calls) == 1
    cycle.run("synthetic", now=NOW+timedelta(hours=3), manual_key=key)
    assert len(cycle.research.calls) == len(transport.calls) == 2
    assert cycle.research.calls[-1][1].target_price == Decimal(3)
    assert cycle.store.get(key)["generation"] == 1
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM workflow_items").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM workflow_v12_notification_commands WHERE inquiry_id IS NOT NULL").fetchone()[0] == 0
    assert task_key("synthetic", "2026", 10, "other_requirement") != key


@pytest.mark.parametrize("outcome", [DeliveryOutcome.UNKNOWN, DeliveryOutcome.RETRYABLE_FAILURE,
                                   DeliveryOutcome.PERMANENT_FAILURE])
def test_delivery_failure_unknown_no_automatic_research_or_blind_manual_resend(tmp_path, outcome):
    cycle, _, _, transport, _ = build(tmp_path, (outcome, DeliveryOutcome.SENT))
    cycle.run("synthetic", now=NOW)
    key = task_key("synthetic", "2026", 10)
    assert cycle.store.manual_allowed(key) is (outcome is DeliveryOutcome.PERMANENT_FAILURE)
    cycle.run("synthetic", now=NOW+timedelta(minutes=15))
    assert len(cycle.research.calls) == 1
    assert len(transport.calls) == (2 if outcome is DeliveryOutcome.RETRYABLE_FAILURE else 1)


def test_claim_excludes_auto_and_manual_even_with_two_store_connections(tmp_path):
    cycle, _, _, _, path = build(tmp_path)
    order, = cycle.read_orders("synthetic")
    key = cycle.store.register(order, NOW)
    assert cycle.store.claim(key, order, NOW)
    second = TpStore(path)
    assert second.claim(key, order, NOW) is None
    assert second.claim(key, order, NOW, manual=True) is None


def test_crash_after_outbox_commit_adopts_same_command(tmp_path):
    cycle, _, _, transport, _ = build(tmp_path)
    enqueue = cycle.outbox.enqueue_notification
    def committed_then_lost(command):
        enqueue(command)
        raise RuntimeError("synthetic crash after commit")
    cycle.outbox.enqueue_notification = committed_then_lost
    with pytest.raises(RuntimeError):
        cycle.run("synthetic", now=NOW)
    key = task_key("synthetic", "2026", 10)
    assert cycle.store.get(key)["state"] == "MAIL_QUEUED"
    cycle.outbox.enqueue_notification = enqueue
    cycle.run("synthetic", now=NOW+timedelta(minutes=15))
    assert len(cycle.research.calls) == len(transport.calls) == 1


def test_crash_before_outbox_research_recoverable_and_sending_crash_unknown(tmp_path):
    cycle, _, _, _, _ = build(tmp_path)
    order, = cycle.read_orders("synthetic")
    key = cycle.store.register(order, NOW)
    command = cycle.store.claim(key, order, NOW)
    cycle.store.recover(NOW)
    assert cycle.store.get(key)["state"] == "PENDING"
    command = cycle.store.claim(key, order, NOW)
    result = cycle.research.execute_tp(key, order, now=NOW)
    cycle.outbox.enqueue_notification(tp_mail(order, result, command, NOW))
    cycle.outbox.claim_due_notifications(now=NOW)
    cycle.store.recover(NOW)
    cycle.outbox.recover_abandoned_notification_attempts(at=NOW)
    assert cycle.store.delivery(key) == "UNKNOWN"
    assert not cycle.store.manual_allowed(key)


def test_source_revalidation_conflict_prevents_mail_and_duplicate_brief_anchor_holds(tmp_path):
    cycle, lines, reader, transport, _ = build(tmp_path)
    cycle.research.hook = lambda: setattr(reader, "rows", [source(qty=101)])
    cycle.run("synthetic", now=NOW)
    assert not transport.calls
    assert cycle.issues
    lines.append(brief(price="3 USD"))
    assert cycle.read_orders("synthetic") == []
    assert all(v == "TP_SOURCE_AMBIGUOUS" for v in cycle.issues.values())


def test_empty_invalid_targets_never_research_or_send(tmp_path):
    cycle, lines, _, transport, _ = build(tmp_path)
    lines[:] = [brief(price=""), brief(price="not money", row="11")]
    cycle.run("synthetic", now=NOW)
    assert not cycle.research.calls and not transport.calls
    assert len(cycle.issues) == 1


def test_mail_no_fake_zero_second_date_and_urgent_when_no_valid_prices(tmp_path):
    cycle, _, _, _, _ = build(tmp_path)
    order, = cycle.read_orders("synthetic")
    result = cycle.research.execute_tp("tp_synthetic", order, now=NOW)
    empty_sources = tuple(replace(s, quotes=()) for s in result.sources)
    empty = replace(result, sources=empty_sources, lowest=None, second=None, estimated_total=None)
    command = tp_mail(order, empty, "tp_synthetic:0", NOW)
    assert command.inquiry_id is None
    assert command.text_body.startswith("请人工加急跟进")
    assert "全局真实最低：无有效报价" in command.text_body
    assert "全局真实最低：0" not in command.text_body
    assert "不足两档" in command.text_body
    assert len(command.recipients) == 1 and command.recipients[0].address == "linan229@qq.com"


def test_tp_equal_target_not_urgent_and_current_quote_has_no_fabricated_date(tmp_path):
    cycle, _, _, _, _ = build(tmp_path)
    order, = cycle.read_orders("synthetic")
    result = cycle.research.execute_tp("tp_synthetic", order, now=NOW)
    result = replace(result, target_rmb=result.lowest.rmb)
    assert tp_mail(order, result, "tp_synthetic:0", NOW).text_body.startswith("TP 专项调研")
    current = replace(result.lowest, offer=replace(result.lowest.offer, quoted_at=None, current=True))
    result = replace(result, lowest=current, sources=tuple(replace(s, quotes=(current,)) for s in result.sources))
    body = tp_mail(order, result, "tp_synthetic:0", NOW).text_body
    assert "现价，报价日期未提供" in body


def test_actual_simultaneous_claims_one_winner(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    cycle, _, _, _, path = build(tmp_path)
    order, = cycle.read_orders("synthetic")
    key = cycle.store.register(order, NOW)
    barrier = Barrier(2)
    def claim():
        barrier.wait()
        return TpStore(path).claim(key, order, NOW)
    with ThreadPoolExecutor(max_workers=2) as executor:
        a, b = executor.submit(claim), executor.submit(claim)
        assert sum(value is not None for value in (a.result(), b.result())) == 1
