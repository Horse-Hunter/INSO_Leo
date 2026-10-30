import sqlite3
from collections import deque
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


def build(tmp_path, outcomes=(DeliveryOutcome.SENT,), *, day=None):
    path = tmp_path / "synthetic.sqlite3"
    WorkflowStateStore(path)
    migrate_v12(path, tmp_path / "backups", quiesce=lambda: nullcontext())
    V13HoldStore(path).migrate()
    store, outbox = TpStore(path), V12Store(path)
    store.migrate()
    transport = FakeNotificationTransport({"owner": outcomes, "ops": outcomes})
    worker = V12NotificationWorker(outbox, transport)
    lines = [brief()]
    if day is not None:
        from src.sheets.tp_brief import BRIEF_HEADERS, BriefLine
        data = {h: lines[0].get(h) for h in BRIEF_HEADERS}
        data["rfq_date"] = day.isoformat()
        lines = [BriefLine(2, tuple(data[h] for h in BRIEF_HEADERS))]
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
    assert len(cycle.research.calls) == 1 and len(transport.calls) == 2
    lines[0] = brief(price="3 USD")
    cycle.run("synthetic", now=NOW+timedelta(hours=2))
    assert len(cycle.research.calls) == 1
    cycle.run("synthetic", now=NOW+timedelta(hours=3), manual_key=key)
    assert len(cycle.research.calls) == 2 and len(transport.calls) == 4
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
    assert len(transport.calls) == (4 if outcome is DeliveryOutcome.RETRYABLE_FAILURE else 2)


def test_claim_excludes_auto_and_manual_even_with_two_store_connections(tmp_path):
    cycle, _, _, _, path = build(tmp_path)
    order, = cycle.read_orders("synthetic")
    key = cycle.store.register(order, NOW)
    assert cycle.store.claim(key, order, NOW)
    second = TpStore(path)
    assert second.claim(key, order, NOW) is None
    assert second.claim(key, order, NOW, manual=True) is None


@pytest.mark.parametrize("owner,ops,expected,allowed", [
    ("SENT", "UNKNOWN", "UNKNOWN", False),
    ("UNKNOWN", "SENT", "UNKNOWN", False),
    ("SENT", "RETRYABLE_FAILURE", "RETRYABLE_FAILURE", False),
    ("SENT", "PERMANENT_FAILURE", "PERMANENT_FAILURE", True),
    ("SENT", "SENT", "SENT", True),
])
def test_all_recipients_control_completion_and_manual_retry(tmp_path, owner, ops, expected, allowed):
    cycle, _, _, transport, _ = build(tmp_path)
    transport._outcomes["owner"] = deque([DeliveryOutcome(owner)])
    transport._outcomes["ops"] = deque([DeliveryOutcome(ops)])
    cycle.run("synthetic", now=NOW)
    key = cycle.store.rows()[0]["task_id"]
    assert cycle.store.delivery(key) == expected
    assert cycle.store.manual_allowed(key) is allowed
    first_calls = tuple(transport.calls)
    cycle.run("synthetic", now=NOW + timedelta(minutes=15))
    assert len(cycle.research.calls) == 1
    assert all(call[1] == "ops" for call in transport.calls[len(first_calls):])


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
    assert len(cycle.research.calls) == 1 and len(transport.calls) == 2


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
    assert "请人工加急跟进：暂无有效报价。" in command.text_body
    assert "最低：" not in command.text_body
    assert "各来源报价" not in command.text_body
    assert "不足两档" not in command.text_body
    assert "预计订单总价" not in command.text_body
    assert {r.address for r in command.recipients} == {"linan229@qq.com", "shawn@inso-hk.com"}


def test_tp_equal_target_not_urgent_and_current_quote_has_no_fabricated_date(tmp_path):
    cycle, _, _, _, _ = build(tmp_path)
    order, = cycle.read_orders("synthetic")
    result = cycle.research.execute_tp("tp_synthetic", order, now=NOW)
    result = replace(result, target_rmb=result.lowest.rmb)
    assert tp_mail(order, result, "tp_synthetic:0", NOW).text_body.startswith("最低价等于 TP。")
    current = replace(result.lowest, offer=replace(result.lowest.offer, quoted_at=None, current=True))
    result = replace(result, lowest=current, sources=tuple(replace(s, quotes=(current,)) for s in result.sources))
    body = tp_mail(order, result, "tp_synthetic:0", NOW).text_body
    assert "现价" in body and "报价日期未提供" not in body


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


@pytest.mark.parametrize("sheets", [("2026",) * 4, ("2026", "2026", "SHAHAB", "SHAHAB")])
def test_four_orders_batch_sources_and_completed_poll_reads_no_sources(tmp_path, sheets):
    from collections import Counter
    cycle, lines, reader, transport, _ = build(tmp_path, (DeliveryOutcome.SENT,) * 4)
    lines[:] = [brief(sheet=s, row=str(r)) for r, s in enumerate(sheets, 10)]
    counts = Counter()
    def read(worksheet):
        counts[worksheet.worksheet] += 1
        return tuple(source(sheet=worksheet.worksheet, position=r) for r in range(10, 14))
    reader.read_rows = read
    read_brief = cycle.brief.read
    def counted_brief(spreadsheet):
        counts["brief"] += 1
        return read_brief(spreadsheet)
    cycle.brief.read = counted_brief
    cycle.run("synthetic", now=NOW)
    # One snapshot per sheet + four fresh target-only final checks (was20).
    assert counts == Counter(sheets) + Counter(sheets) + Counter({s: 1 for s in sheets}) + Counter(brief=9)
    assert len(transport.calls) == 8
    counts.clear()
    cycle.run("synthetic", now=NOW + timedelta(minutes=15))
    assert counts == {"brief": 1}
    assert len(transport.calls) == 8
    counts.clear()
    cycle.run("synthetic", now=NOW + timedelta(minutes=30),
              manual_key=task_key("synthetic", "2026", 10))
    assert counts == {"brief": 3, "2026": 3}


@pytest.mark.parametrize("change", ["qty", "mpn", "price", "duplicate", "removed"])
def test_target_only_fresh_check_still_blocks_changed_identity_or_target(tmp_path, change):
    cycle, lines, reader, transport, _ = build(tmp_path)
    def mutate():
        if change == "qty":
            reader.rows = [source(qty=101)]
        elif change == "mpn":
            reader.rows = [source(mpn="OTHER")]
        elif change == "price":
            lines[0] = brief(price="3 USD")
        elif change == "duplicate":
            lines.append(brief(row="010", price=""))
        else:
            lines.clear()
    cycle.research.hook = mutate
    cycle.run("synthetic", now=NOW)
    assert not transport.calls
    assert cycle.store.rows()[0]["state"] == "FAILED"
    assert cycle.issues


@pytest.mark.parametrize("phase", ["schema", "research", "mail", "mail_runtime"])
def test_local_failure_persisted_safe_retry_and_manual_failure(tmp_path, monkeypatch, phase):
    from src.sheets.tp_brief import TpLocalError
    from src.workflow import tp_research
    cycle, _, _, transport, path = build(tmp_path)
    def fail(*a, **k):
        if phase == "mail_runtime":
            raise RuntimeError("synthetic pure TP mail composition failure")
        if phase == "mail":
            raise TypeError("synthetic malformed TP result")
        raise TpLocalError("TP_BRIEF_SCHEMA_UNAVAILABLE" if phase == "schema" else "TP_RESEARCH_FAILED")
    target, attr = ((cycle.brief, "read") if phase == "schema" else
                    (cycle.research, "execute_tp") if phase == "research" else (tp_research, "tp_mail"))
    original = getattr(target, attr)
    monkeypatch.setattr(target, attr, fail)
    cycle.run("synthetic", now=NOW)
    assert not transport.calls and cycle.issues
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT reason FROM workflow_tp_failures").fetchall()
    if phase != "schema":
        key = cycle.store.rows()[0]["task_id"]
        assert cycle.store.get(key)["state"] == "FAILED"
        with pytest.raises(TpLocalError):
            cycle.run("synthetic", now=NOW, manual_key=key)
    monkeypatch.setattr(target, attr, original)
    cycle.run("synthetic", now=NOW + timedelta(minutes=15))
    assert len(transport.calls) == 2
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM workflow_tp_failures").fetchone()[0] == 0


@pytest.mark.parametrize("phase", ["brief", "source", "prepare", "research", "outbox", "worker"])
@pytest.mark.parametrize("kind", ["safety", "database", "unknown", "wrapped", "auth", "ledger", "wrapped_unknown"])
def test_shared_and_unclassified_faults_never_swallowed(tmp_path, phase, kind):
    from src.inso.session import SecurityViolation
    from src.launcher.inso_session import InsoAuthenticationError
    from src.sheets.tp_brief import TpLocalError
    from src.workflow.v12_faults import FaultScope, V12Fault
    from src.workflow.v12_store import V12DatabaseError
    cycle, _, reader, transport, _ = build(tmp_path)
    error = (V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE") if kind == "safety" else
             sqlite3.DatabaseError("synthetic integrity fault") if kind == "database" else
             RuntimeError("unclassified fault") if kind == "unknown" else
             InsoAuthenticationError("MANUAL_VERIFICATION_REQUIRED") if kind == "auth" else
             V12DatabaseError("synthetic ledger fault") if kind == "ledger" else
             TpLocalError("TP_RESEARCH_FAILED"))
    if kind == "wrapped":
        error.__cause__ = SecurityViolation("synthetic ownership fault")
    if kind == "wrapped_unknown":
        error.__cause__ = RuntimeError("unclassified shared fault")
    def fail(*a, **k):
        raise error
    if phase == "brief":
        cycle.brief.read = fail
    elif phase == "source":
        reader.read_rows = fail
    elif phase == "prepare":
        cycle.prepare = fail
    elif phase == "research":
        cycle.research.execute_tp = fail
    elif phase == "outbox":
        cycle.outbox.enqueue_notification = fail
    else:
        cycle.worker.run_due = fail
    with pytest.raises(type(error)) as caught:
        cycle.run("synthetic", now=NOW)
    assert caught.value is error
    assert not transport.calls


@pytest.mark.parametrize("kind", ["data", "invalid_input", "fx", "fx_redirect"])
def test_tp_research_data_and_fx_failure_classification(tmp_path, kind):
    from src.research.contracts import InvalidResearchInput
    from src.research.ecb_fx import EcbFxError
    from src.research.tp import TpFx
    cycle, _, _, transport, _ = build(tmp_path)
    def fail():
        if kind == "invalid_input":
            raise InvalidResearchInput("synthetic invalid model input")
        if kind == "data":
            raise TypeError("synthetic invalid TP projection")
        def quote():
            raise EcbFxError("ECB_UNTRUSTED_REDIRECT" if kind == "fx_redirect" else "ECB_FETCH_FAILED")
        TpFx(SimpleNamespace(get_quote=quote), NOW).convert(Decimal(1), "USD")
    cycle.research.hook = fail
    if kind == "fx_redirect":
        with pytest.raises(ValueError, match="FX_QUOTE_UNAVAILABLE"):
            cycle.run("synthetic", now=NOW)
    else:
        cycle.run("synthetic", now=NOW)
        assert cycle.issues
        assert cycle.store.rows()[0]["state"] == "FAILED"
    assert not transport.calls
