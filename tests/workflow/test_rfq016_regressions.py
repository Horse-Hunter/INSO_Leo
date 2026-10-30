"""RFQ-016 synthetic regressions. No live systems or customer data."""
from dataclasses import replace
from datetime import timedelta

from src.launcher.v13_integration import notify_runtime_fault
from src.sheets.pending import query_pending_records
from src.workflow.v12_contracts import (
    BusinessState,
    DeliveryOutcome,
    EventType,
    WorkflowEvent,
)
from src.workflow.v12_notifications import (
    FakeNotificationTransport,
    V12NotificationWorker,
)
from src.workflow.v13_integration import V13HoldStore
from tests.workflow.test_v12_flow import NOW as FLOW_NOW
from tests.workflow.test_v12_flow import SHEET, FakeSheetsReader, _make_flow
from tests.workflow.test_v12_notifications import NOW, prepared_store


def test_recoverable_google_warning_never_reaches_smtp(tmp_path):
    store = prepared_store(tmp_path)
    V13HoldStore(store.database_path).migrate()
    smtp = FakeNotificationTransport({"owner": (DeliveryOutcome.SENT,)})
    notify_runtime_fault(store, "run-one", "GOOGLE_READ_RETRY_EXHAUSTED", at=NOW)
    V12NotificationWorker(store, smtp).run_due(now=NOW)
    assert smtp.calls == []


def test_month_old_durable_queue_does_not_research(tmp_path):
    flow, queue, ledger, research, checker, _, writer, _ = _make_flow(tmp_path)
    flow._brief_snapshot = lambda _: ()
    record = query_pending_records(FakeSheetsReader(), SHEET)[0]
    queue.enqueue(record, now=FLOW_NOW-timedelta(days=31))
    iid = queue.inquiry_id_for(record.record_identity)
    ledger.set_business_state(iid, BusinessState.QUEUED, WorkflowEvent("old-queue", iid, EventType.DUPLICATE_CHECK_STARTED, FLOW_NOW-timedelta(days=31), "workflow"))
    flow.poll_and_process(FakeSheetsReader(), SHEET, now=FLOW_NOW)
    assert research.inputs == []
    assert checker.calls == []
    assert writer.commands == []


# Actual SMTP adapter with an injected in-memory SMTP server: no socket/Vault.
import sqlite3
from datetime import datetime, timezone

import pytest

from src.gui.contracts import V12BusinessLabel, V12OrderStateDTO
from src.launcher.source_status import SourceStatusProjection
from src.workflow.automatic_admission import age_reason
from src.workflow.v12_contracts import (
    NotificationCommand,
    NotificationKind,
    NotificationRecipient,
)
from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
from src.workflow.v12_store import V12Store
from tests.workflow.test_v12_notifications import INQUIRY
from tests.workflow.test_v12_smtp_transport import FakeCredentials, ScriptedSMTP, login


def proof(*, now=NOW, category="persistent_stop", **changes):
    result = {"incident_key": "synthetic-program-read", "module": "Google Sheets", "business_module": "inquiry",
                  "reason_code": "PROGRAM_OPERATION_BLOCKED", "category": category, "inquiry_id": INQUIRY,
                  "verified_at": now.isoformat(), "inquiry_day": now.date().isoformat(),
                  "original_event": "original-source-read", "active": True, "current_business": True,
                  "needs_owner": True, "verified": True, "retries_exhausted": True, "completed_cycles": 3,
                  "last_success": (now-timedelta(hours=3)).isoformat(),
                  "action": "核对原程序读取授权；不要重发采购", "uncertainty": "当前原表状态尚未重新读取"}
    result.update(changes)
    return result


def incident_command(now=NOW):
    return NotificationCommand("to-be-assigned", INQUIRY, NotificationKind.PURCHASE_EXCEPTION,
        (NotificationRecipient("owner", "owner@example.invalid"),),
        "需要处理：程序读取持续受阻", "请核对原程序；不能据此认定Google整站不可用。", None, now)


def real_fake_smtp(store, now=NOW, review_current=None):
    smtp = ScriptedSMTP()
    transport = QQSMTPTransport(config=QQSMTPConfig(sender_address="sender@example.invalid"),
        credentials=FakeCredentials(login()), smtp_factory=lambda *a, **k: smtp, clock=lambda: now)
    return V12NotificationWorker(store, transport, review_current=review_current), smtp


def test_three_completed_cycles_across_restarts_send_exactly_once_through_smtp(tmp_path):
    store = prepared_store(tmp_path)
    path = store.database_path
    for cycle in range(3):
        store = V12Store(path)
        store.observe_incident(incident_command(), proof(), occurrence=f"cycle-{cycle}")
        worker, smtp = real_fake_smtp(store)
        worker.run_due(now=NOW)
        assert smtp.send_attempts == int(cycle == 2)
    # A different run/cycle is not a different incident, and SENT is immutable.
    store.observe_incident(incident_command(), proof(), occurrence="restart-four")
    worker, smtp = real_fake_smtp(V12Store(path))
    assert worker.run_due(now=NOW) == 0 and smtp.send_attempts == 0


@pytest.mark.parametrize("changes", [{"active": False}, {"current_business": False},
    {"needs_owner": False}, {"verified": False}, {"retries_exhausted": False},
    {"inquiry_day": "2026-08-01"}, {"action": ""}, {"category": "temporary_timeout"}])
def test_false_samples_have_zero_actual_smtp_attempts(tmp_path, changes):
    store = prepared_store(tmp_path)
    for cycle in range(3):
        store.observe_incident(incident_command(), proof(**changes), occurrence=str(cycle))
    worker, smtp = real_fake_smtp(store)
    worker.run_due(now=NOW)
    assert smtp.send_attempts == 0


def test_recovery_between_enqueue_and_send_suppresses_without_erasing_sent_unknown(tmp_path):
    store = prepared_store(tmp_path)
    for cycle in range(3):
        key = store.observe_incident(incident_command(), proof(), occurrence=str(cycle))
    store.resolve_incidents("Google Sheets", at=NOW)
    worker, smtp = real_fake_smtp(store)
    worker.run_due(now=NOW)
    assert smtp.send_attempts == 0
    with sqlite3.connect(store.database_path) as db:
        assert db.execute("SELECT outcome FROM workflow_v12_notification_recipients WHERE command_id=?", (key,)).fetchone()[0] == "SUPPRESSED"
        assert db.execute("SELECT suppression_reason FROM workflow_v12_notification_commands WHERE command_id=?", (key,)).fetchone()[0]


@pytest.mark.parametrize("category,reason", [("unknown_write", "UPDATE_RESULT_UNCONFIRMED"),
                                            ("manual_login", "MANUAL_VERIFICATION_REQUIRED")])
def test_verified_unknown_or_manual_login_immediate_one_mail(tmp_path, category, reason):
    store = prepared_store(tmp_path)
    evidence = proof(category=category, reason_code=reason, original_event="verified-native-event")
    for run in ("first", "restart", "third"):
        store.observe_incident(incident_command(), evidence, occurrence=run)
        worker, smtp = real_fake_smtp(store)
        worker.run_due(now=NOW)
        assert smtp.send_attempts == int(run == "first")


def test_old_pending_legacy_faults_do_not_reach_smtp_and_sent_unknown_stay_intact(tmp_path):
    store = prepared_store(tmp_path)
    for index, outcome in enumerate(("PENDING", "RETRYABLE_FAILURE", "SENT", "UNKNOWN")):
        key = f"legacy-{index}"
        with sqlite3.connect(store.database_path) as db:
            db.execute("INSERT INTO workflow_v12_notification_commands (command_id,inquiry_id,kind,subject,text_body,created_at,payload_version) VALUES (?,?,?,'old warning','old warning',?,1)",
                       (key, INQUIRY, "PURCHASE_EXCEPTION", (NOW-timedelta(days=31)).isoformat()))
            db.execute("INSERT INTO workflow_v12_notification_recipients (command_id,recipient_id,address,outcome) VALUES (?,'owner','owner@example.invalid',?)", (key,outcome))
    worker, smtp = real_fake_smtp(store)
    worker.run_due(now=NOW)
    assert smtp.send_attempts == 0
    with sqlite3.connect(store.database_path) as db:
        outcomes = [r[0] for r in db.execute("SELECT outcome FROM workflow_v12_notification_recipients ORDER BY command_id")]
    assert outcomes == ["SUPPRESSED", "SUPPRESSED", "SENT", "UNKNOWN"]


@pytest.mark.parametrize("kind", [NotificationKind.IMPORTANT_ORDER, NotificationKind.TP_RESEARCH])
def test_current_legal_business_mail_still_reaches_fake_smtp(tmp_path, kind):
    store = prepared_store(tmp_path)
    command = replace(incident_command(), command_id="legal-business", kind=kind)
    store.enqueue_notification(command)
    worker, smtp = real_fake_smtp(store)
    assert worker.run_due(now=NOW) == 1 and smtp.send_attempts == 1


@pytest.mark.parametrize("today,day,allowed", [
    ("2026-03-31", "2026-02-28", True), ("2026-03-31", "2026-02-27", False),
    ("2024-03-31", "2024-02-29", True), ("2024-03-31", "2024-02-28", False),
    ("2026-01-31", "2025-12-31", True), ("2026-10-30", "2026-10-31", False)])
@pytest.mark.parametrize("module", ["tp", "future_personalized_requirement"])
def test_calendar_month_boundaries_are_shared(today, day, allowed, module):
    now = datetime.fromisoformat(today).replace(tzinfo=timezone(timedelta(hours=8)))
    assert (age_reason(day, now, module=module) is None) is allowed


@pytest.mark.parametrize("status", ["发给采购", "采购已报价", "已报价给客户"])
def test_all_automatic_quote_statuses_expire_before_inso(status):
    from tests.workflow.test_v13_quotation import NOW as QUOTE_NOW
    from tests.workflow.test_v13_quotation import WS, cycle, source
    service, operations, quotes, _ = cycle([], sources=[source(2, status)])
    service._store.inquiry_intake_at = lambda _: QUOTE_NOW-timedelta(days=8)
    result, = service.run(WS)
    assert result.outcome.value == "QUOTE_AGE_EXPIRED"
    assert not operations.events and not quotes.calls


@pytest.mark.parametrize("status", ["发给采购", "采购已报价", "已报价给客户"])
def test_owner_single_quote_age_exemption_retains_current_status_gate(status):
    from tests.workflow.test_v13_quotation import NOW as QUOTE_NOW
    from tests.workflow.test_v13_quotation import WS, cycle, source
    service, _operations, quotes, _ = cycle([()], sources=[source(2, status)])
    service._store.inquiry_intake_at = lambda _: QUOTE_NOW-timedelta(days=31)
    service._automatic_refresh = False
    result, = service.run(WS)
    assert result.outcome.value == "NO_RECENT_QUOTE" and len(quotes.calls) == 1


@pytest.mark.parametrize("status", ["已报价给客户", "发给采购", "采购已报价"])
def test_recent_non_pending_inquiry_never_reenters_automatic_research(tmp_path, status):
    flow, queue, ledger, research, checker, _, writer, _ = _make_flow(tmp_path)
    reader = FakeSheetsReader()
    record, = query_pending_records(reader, SHEET)
    queue.enqueue(record, now=FLOW_NOW)
    iid = queue.inquiry_id_for(record.record_identity)
    ledger.set_business_state(iid, BusinessState.QUEUED,
        WorkflowEvent("queued", iid, EventType.DUPLICATE_CHECK_STARTED, FLOW_NOW, "workflow"))
    reader.row.cells["A"] = status
    assert flow.poll_and_process(reader, SHEET, now=FLOW_NOW) == ()
    assert not research.inputs and not checker.calls and not writer.commands


def test_source_projection_fresh_customer_status_keeps_purchase_history_and_unknown():
    from tests.workflow.test_v13_quotation import WS, item, source
    projection = SourceStatusProjection()
    original = item(2)
    dto = V12OrderStateDTO(original.inquiry_id, V12BusinessLabel.SUBMIT_UNCONFIRMED, None,
                          waiting_label="写入待核对，不会自动重做")
    projection.observe(WS, [source(2, "已报价给客户")], [original], at=NOW)
    current = projection.project(dto, now=NOW)
    assert current.source_status == "已报价给客户" and current.source_fresh
    assert "待核对" in current.waiting_label and current.business_label == dto.business_label
    projection.observe(WS, (), [original], at=NOW, failed=True)
    stale = projection.project(dto, now=NOW)
    assert not stale.source_fresh and "状态待同步" in stale.waiting_label
    assert "待核对" in stale.waiting_label


def test_tp_old_persisted_pending_failed_and_manual_age_exemption(tmp_path):
    from src.sheets.tp_brief import BRIEF_HEADERS, BriefLine, bind_tp_order
    from src.workflow.tp_research import task_key
    from tests.research.test_tp import NOW as TP_NOW
    from tests.sheets.test_tp_brief import brief
    from tests.workflow.test_tp_research import build
    cycle, lines, reader, transport, _ = build(tmp_path)
    data = {h: brief().get(h) for h in BRIEF_HEADERS}
    data["rfq_date"] = (TP_NOW-timedelta(days=62)).date().isoformat()
    lines[:] = [BriefLine(2, tuple(data[h] for h in BRIEF_HEADERS))]
    order = bind_tp_order(lines[0], "synthetic", reader.rows)
    key = task_key("synthetic", "2026", 10)
    cycle.store.register(order, TP_NOW)
    cycle.run("synthetic", now=TP_NOW)
    cycle.store.finish(key, "FAILED", TP_NOW)
    cycle.run("synthetic", now=TP_NOW)
    assert not cycle.research.calls and not transport.calls
    cycle.run("synthetic", now=TP_NOW, manual_key=key)
    assert len(cycle.research.calls) == 1 and len(transport.calls) == 2



def production_scene(tmp_path):
    from types import SimpleNamespace

    from src.launcher.backend import ProductionBackend
    flow, queue, ledger, _research, _checker, _facts, _writer, _worker = _make_flow(tmp_path)
    reader = FakeSheetsReader()
    record, = query_pending_records(reader, SHEET)
    flow.prepare_pending((record,), now=FLOW_NOW)
    iid = queue.inquiry_id_for(record.record_identity)
    backend = ProductionBackend(root=tmp_path)
    backend._store, backend._v12_store = queue, ledger
    backend._mail_brief = SimpleNamespace(cached_lines=lambda _: ())
    backend._source_projection.observe(SHEET, (reader.row,), queue.all_items(), at=FLOW_NOW)
    backend._active_inso_inquiry = iid
    return backend, flow, queue, ledger, reader, record, iid


def test_actual_production_manual_login_producer_to_final_smtp_review_once(tmp_path):
    backend, _flow, _queue, ledger, _reader, _record, _iid = production_scene(tmp_path)
    backend._site_manual_wait.add("INSO")
    for run in ("first", "restart"):
        backend._notify_runtime_fault(run, "INSO_AUTHENTICATION_REQUIRED", at=FLOW_NOW)
        worker, smtp = real_fake_smtp(ledger, now=FLOW_NOW, review_current=backend._review_current_mail)
        worker.run_due(now=FLOW_NOW)
        assert smtp.send_attempts == int(run == "first")
        if smtp.message:
            assert "原Chrome" in smtp.message.get_content()
    backend.shutdown()


def test_actual_production_persistent_read_block_counts_cycles_not_restarts(tmp_path):
    backend, _flow, queue, ledger, _reader, _record, _iid = production_scene(tmp_path)
    backend._site_outages["Google Sheets"] = 0.0
    backend._source_projection.observe(SHEET, (), queue.all_items(), at=FLOW_NOW, failed=True)
    for index, minutes in enumerate((15, 30, 180)):
        now = FLOW_NOW+timedelta(minutes=minutes)
        backend._cycle_id = f"finished-cycle-{index}"
        backend._notify_runtime_fault(f"run-{index}", "GOOGLE_READ_RETRY_EXHAUSTED" if index < 2 else "GOOGLE_OUTAGE_THREE_HOURS", at=now)
        worker, smtp = real_fake_smtp(ledger, now=now, review_current=backend._review_current_mail)
        worker.run_due(now=now)
        assert smtp.send_attempts == int(index == 2)
    backend.shutdown()


def test_native_quote_unknown_mail_and_latest_source_status_do_not_clear_hold(tmp_path, monkeypatch):
    from src.launcher import backend as launcher
    monkeypatch.setattr(launcher, "utc_now", lambda: FLOW_NOW)
    from src.sheets import WorksheetRow
    from src.workflow.v13_integration import restore_result
    from src.workflow.v13_quotation import (
        QuotationOutcome,
        RowErrorReason,
        V13QuotationResult,
    )
    backend, _flow, queue, ledger, reader, record, iid = production_scene(tmp_path)
    holds = V13HoldStore(ledger.database_path)
    holds.migrate()
    result = V13QuotationResult(iid, record.record_identity, record.model, QuotationOutcome.ROW_FAILED,
        None, RowErrorReason.UPDATE_RESULT_UNCONFIRMED, SHEET, record.row_position,
        effect_uncertain=True)
    key, episode = holds.hold(result, record.record_identity)
    reader.row = WorksheetRow(record.row_position, {**reader.row.cells, "A": "已报价给客户"})
    backend._source_projection.observe(SHEET, (reader.row,), queue.all_items(), at=FLOW_NOW)
    backend._notify_quotation(restore_result(holds.active()[0][1]), key, episode, at=FLOW_NOW)
    worker, smtp = real_fake_smtp(ledger, now=FLOW_NOW, review_current=backend._review_current_mail)
    worker.run_due(now=FLOW_NOW)
    assert smtp.send_attempts == 1 and "待人工核实" in smtp.message.get_content()
    before = holds.active()
    holds.close(key)
    holds.close_many((key,))
    assert holds.active() == before
    dto = backend.get_v12_order_state(iid)
    assert dto.source_fresh and dto.source_status == "已报价给客户"
    assert ledger.unknown_write_active(iid, f"{key}:{episode}")
    backend.shutdown()


def test_preclick_quote_timeout_is_not_a_verified_unknown_write_email(tmp_path):
    from src.workflow.v13_quotation import (
        QuotationOutcome,
        RowErrorReason,
        V13QuotationResult,
    )
    backend, _flow, _queue, ledger, _reader, record, iid = production_scene(tmp_path)
    holds = V13HoldStore(ledger.database_path)
    holds.migrate()
    result = V13QuotationResult(iid, record.record_identity, record.model, QuotationOutcome.ROW_FAILED,
        None, RowErrorReason.UPDATE_RESULT_UNCONFIRMED, SHEET, record.row_position)
    key, episode = holds.hold(result, record.record_identity)
    backend._notify_quotation(result, key, episode, at=FLOW_NOW)
    worker, smtp = real_fake_smtp(ledger, now=FLOW_NOW, review_current=backend._review_current_mail)
    worker.run_due(now=FLOW_NOW)
    assert smtp.send_attempts == 0 and not ledger.unknown_write_active(iid, f"{key}:{episode}")
    backend.shutdown()


def test_explicit_manual_quote_does_not_bypass_unknown_write_protection(tmp_path):
    from src.launcher.manual_order import ManualRetryHolds
    from src.workflow.v13_quotation import (
        QuotationOutcome,
        RowErrorReason,
        V13QuotationResult,
    )
    backend, _flow, _queue, ledger, _reader, record, iid = production_scene(tmp_path)
    holds = V13HoldStore(ledger.database_path)
    holds.migrate()
    result = V13QuotationResult(iid, record.record_identity, record.model, QuotationOutcome.ROW_FAILED,
        None, RowErrorReason.UPDATE_RESULT_UNCONFIRMED, SHEET, record.row_position, effect_uncertain=True)
    holds.hold(result, record.record_identity)
    before = holds.active()
    with pytest.raises(ValueError, match="待人工核对"):
        ManualRetryHolds(holds, iid, record.record_identity)
    assert holds.active() == before
    backend.shutdown()


@pytest.mark.parametrize("historical", ["SENT", "UNKNOWN"])
def test_legacy_same_incident_delivery_is_not_replayed_with_new_key(tmp_path, historical):
    store = prepared_store(tmp_path)
    with sqlite3.connect(store.database_path) as db:
        db.execute("INSERT INTO workflow_v12_notification_commands (command_id,inquiry_id,kind,subject,text_body,created_at,payload_version) VALUES ('old-native-event',?,'PURCHASE_EXCEPTION','old','old',?,1)", (INQUIRY, NOW.isoformat()))
        db.execute("INSERT INTO workflow_v12_notification_recipients (command_id,recipient_id,address,outcome) VALUES ('old-native-event','owner','owner@example.invalid',?)", (historical,))
    evidence = proof(category="unknown_write", reason_code="UPDATE_RESULT_UNCONFIRMED",
                     legacy_commands=["old-native-event"])
    store.observe_incident(incident_command(), evidence, occurrence="restart")
    worker, smtp = real_fake_smtp(store)
    worker.run_due(now=NOW)
    assert smtp.send_attempts == 0
    with sqlite3.connect(store.database_path) as db:
        assert db.execute("SELECT outcome FROM workflow_v12_notification_recipients WHERE command_id='old-native-event'").fetchone()[0] == historical


def test_completed_source_status_cannot_qualify_an_old_queue_as_current_read_block(tmp_path):
    from src.sheets import WorksheetRow
    backend, _flow, queue, ledger, reader, record, _iid = production_scene(tmp_path)
    reader.row = WorksheetRow(record.row_position, {**reader.row.cells, "A": "已报价给客户"})
    backend._source_projection.observe(SHEET, (reader.row,), queue.all_items(), at=FLOW_NOW)
    backend._site_outages["Google Sheets"] = 0
    for cycle in range(3):
        backend._cycle_id = str(cycle)
        backend._notify_runtime_fault(str(cycle), "GOOGLE_OUTAGE_THREE_HOURS", at=FLOW_NOW)
    worker, smtp = real_fake_smtp(ledger, now=FLOW_NOW, review_current=backend._review_current_mail)
    worker.run_due(now=FLOW_NOW)
    assert smtp.send_attempts == 0
    backend.shutdown()



def test_temporarily_unavailable_final_review_defers_legal_business_mail(tmp_path):
    store = prepared_store(tmp_path)
    command = replace(incident_command(), command_id="current-business", kind=NotificationKind.IMPORTANT_ORDER)
    store.enqueue_notification(command)
    def unavailable(_command, _now):
        raise RuntimeError("synthetic source observation temporarily unavailable")
    worker, smtp = real_fake_smtp(store, review_current=unavailable)
    worker.run_due(now=NOW)
    assert smtp.send_attempts == 0
    worker, smtp = real_fake_smtp(store, review_current=lambda command, now: None)
    assert worker.run_due(now=NOW) == 1 and smtp.send_attempts == 1
