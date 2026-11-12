"""F regression: actual Backend preparer/outbox/QQSMTPTransport; no sockets."""
from contextlib import contextmanager
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.research import ResearchResult, ResearchStatus
from src.sheets import WorksheetRow
from src.workflow.purchase_follow_up import PurchaseFollowUp
from src.workflow.v12_contracts import NotificationKind, NotificationRecipient
from src.workflow.v12_flow import ResearchBusinessFacts
from src.workflow.v12_notifications import V12NotificationWorker
from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
from src.workflow.v13_follow_up_store import V13PurchaseFollowUpStore
from tests.workflow.test_mail_research import scene
from tests.workflow.test_rfq016_regressions import production_scene
from tests.workflow.test_v12_flow import NOW, SHEET
from tests.workflow.test_v12_smtp_transport import FakeCredentials, ScriptedSMTP, login


class SMTP(ScriptedSMTP):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages = []
    def send_message(self, message):
        self.messages.append(message)
        return super().send_message(message)


@contextmanager
def notice(tmp_path, kind, monkeypatch, mode="missing", *, send_error=None, recipients=None):
    backend, flow, queue, ledger, reader, record, iid = production_scene(tmp_path)
    from threading import RLock
    brief_service = SimpleNamespace(_grid_lock=RLock(), token=(0, object()))
    brief_service.peek_brief_token = lambda _: brief_service.token
    backend._mail_brief.service = brief_service
    backend._mail_brief.cached_lines_bounded = lambda _, deadline: ()
    clock = [NOW if kind == "important" else NOW+timedelta(days=3, hours=6)]
    def refresh():
        backend._source_projection.observe(SHEET, (reader.row,), queue.all_items(), at=clock[0])
    if kind == "important":
        flow._recipients = recipients or (NotificationRecipient("owner", "linan229@qq.com"), NotificationRecipient("ops", "shawn@inso-hk.com"))
        flow._enqueue_notification(iid, NotificationKind.IMPORTANT_ORDER, ResearchResult(iid, ResearchStatus.SUCCESS), clock[0], tier="A",
            facts=ResearchBusinessFacts("历史库存样本", Decimal(54321), Decimal(4321)))
    else:
        reader.row = WorksheetRow(record.row_position, {**reader.row.cells, "A": "发给采购"})
        episodes = V13PurchaseFollowUpStore(ledger.database_path); episodes.migrate()
        episodes.record_confirmed(iid, confirmed_at=clock[0]-timedelta(hours=6))
        assert PurchaseFollowUp(reader=reader, workflow_store=queue, v12_store=ledger,
            clock=lambda: clock[0], episodes=episodes).run(SHEET) == 1
    refresh()
    service, _, _, reads, _, _ = scene(tmp_path, outbox=ledger)
    service.clock = lambda: clock[0]
    import src.launcher.mail_research_composition as composition
    if mode == "build_error":
        def fail(_):
            raise RuntimeError("synthetic startup unavailable")
        monkeypatch.setattr(composition, "build_mail_research", fail)
        backend.start_process_services()
        assert backend._mail_research_service is None
    elif mode == "start_error":
        def fail():
            raise RuntimeError("synthetic thread startup unavailable")
        service.start = fail
        monkeypatch.setattr(composition, "build_mail_research", lambda _: service)
        backend.start_process_services()
    elif mode != "missing":
        backend._mail_research_service = service
    if mode == "blocked":
        # Real Backend lifecycle with a no-network fake successful service start,
        # followed by persistent local resource protection.
        starts = []
        service.start = lambda: starts.append("started")
        backend._mail_research_service = None
        monkeypatch.setattr(composition, "build_mail_research", lambda _: service)
        backend.start_process_services()
        assert starts == ["started"] and backend._mail_research_service is service
        service.store.block_resource(clock[0])
        service._resource_blocked = True
    if mode == "queue_full":
        service.store.capacity = 0
    if mode == "ineligible":
        service.admit = lambda: False
    if mode == "exception":
        def fail(*_):
            raise RuntimeError("synthetic optional cache unavailable")
        service.cached_report = fail
    smtp = SMTP(send_error=send_error)
    transport = QQSMTPTransport(config=QQSMTPConfig(sender_address="sender@example.invalid"),
        credentials=FakeCredentials(login()), smtp_factory=lambda *a, **k: smtp, clock=lambda: clock[0])
    def worker(store=ledger):
        return V12NotificationWorker(store, transport, scope="business", review_current=backend._review_current_mail,
            prepare_content=backend._prepare_business_mail, guard_factory=backend._supplement_delivery_guard)
    state = SimpleNamespace(backend=backend, ledger=ledger, queue=queue, reader=reader, record=record,
        iid=iid, clock=clock, refresh=refresh, service=service, reads=reads, smtp=smtp, worker=worker)
    try:
        yield state
    finally:
        backend.shutdown()


@pytest.mark.parametrize("kind", ["important", "followup"])
@pytest.mark.parametrize("mode", ["build_error", "start_error", "blocked", "ineligible", "exception", "queue_full"])
def test_optional_failure_delivers_current_original_notice_after_bounded_wait(tmp_path, monkeypatch, kind, mode):
    with notice(tmp_path, kind, monkeypatch, mode) as n:
        initial = n.clock[0]
        for elapsed in (0, 60, 119):
            n.clock[0] = initial+timedelta(seconds=elapsed)
            n.refresh()
            assert n.worker().run_due(now=n.clock[0]) == 0
        if mode in {"blocked", "ineligible"}:
            assert not n.service.run_one()
        n.clock[0] = initial+timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        assert n.reads == []
        assert {str(m["To"]) for m in n.smtp.messages} == {"linan229@qq.com", "shawn@inso-hk.com"}
        for message in n.smtp.messages:
            body = message.get_body(preferencelist=("plain",)).get_content()
            assert "详细市场报价暂不可用" in body and "未核实" in body
            assert "订单总价" not in body and "市场最低参考价" not in body and "库存状态" not in body
            assert "54321" not in body and "4321" not in body and "历史库存样本" not in body
            if kind == "followup":
                assert "3个工作小时" in body and "发给采购时间" in body and "不要重发采购" in body


@pytest.mark.parametrize("kind", ["important", "followup"])
@pytest.mark.parametrize("when", [60, 120])
def test_recovered_detailed_report_wins_even_at_deadline_without_extra_mail(tmp_path, monkeypatch, kind, when):
    with notice(tmp_path, kind, monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=when)
        n.refresh()
        n.service.admit = lambda: True
        assert n.service.run_one() and len(n.reads) == 6
        assert n.worker().run_due(now=n.clock[0]) == 2
        for message in n.smtp.messages:
            body = message.get_body(preferencelist=("html",)).get_content()
            assert all(name in body for name in ("IC.net", "Findchips", "华强", "立创", "正能量", "INSO"))
            assert "详细市场报价暂不可用" not in body
        assert n.worker().run_due(now=n.clock[0]) == 0


@pytest.mark.parametrize("kind", ["important", "followup"])
@pytest.mark.parametrize("change", ["completed", "expired", "unverified_source"])
def test_fallback_deadline_never_overrides_current_business_gate(tmp_path, monkeypatch, kind, change):
    with notice(tmp_path, kind, monkeypatch, "missing") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(days=8) if change == "expired" else timedelta(seconds=120)
        if change == "completed":
            n.reader.row = WorksheetRow(n.record.row_position, {**n.reader.row.cells, "A": "已报价给客户"})
        n.refresh()
        if change == "unverified_source":
            n.backend._source_projection.observe(SHEET, (), n.queue.all_items(), at=n.clock[0], failed=True)
        assert n.worker().run_due(now=n.clock[0]) == 0 and n.smtp.send_attempts == 0


@pytest.mark.parametrize("change", ["status", "episode"])
def test_followup_changed_status_or_new_episode_cannot_use_old_fallback(tmp_path, monkeypatch, change):
    with notice(tmp_path, "followup", monkeypatch, "missing") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        if change == "episode":
            episodes = V13PurchaseFollowUpStore(n.ledger.database_path)
            episodes.record_confirmed(n.iid, confirmed_at=n.clock[0])
        else:
            n.reader.row = WorksheetRow(n.record.row_position, {**n.reader.row.cells, "A": "采购已报价"})
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 0 and n.smtp.send_attempts == 0


@pytest.mark.parametrize("kind", ["important", "followup"])
@pytest.mark.parametrize("outcome", ["SENT", "UNKNOWN"])
def test_restart_does_not_resend_terminal_recipients_after_fallback_and_recovery(tmp_path, monkeypatch, kind, outcome):
    from src.workflow.v12_store import V12Store
    with notice(tmp_path, kind, monkeypatch, "ineligible", send_error=TimeoutError("synthetic") if outcome == "UNKNOWN" else None) as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120); n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        with n.service.store.connect() as db:
            before = [tuple(r) for r in db.execute("SELECT * FROM workflow_v12_notification_recipients ORDER BY recipient_id")]
            assert {r[0] for r in db.execute("SELECT outcome FROM workflow_v12_notification_recipients")} == {outcome}
        # Optional service recovers after fallback; result cache is not a new notice.
        n.service.admit = lambda: True
        assert n.service.run_one()
        restarted = V12Store(n.ledger.database_path)
        restarted.recover_abandoned_notification_attempts(at=n.clock[0], scope="business")
        assert n.worker(restarted).run_due(now=n.clock[0]) == 0 and n.smtp.send_attempts == 2
        with n.service.store.connect() as db:
            assert [tuple(r) for r in db.execute("SELECT * FROM workflow_v12_notification_recipients ORDER BY recipient_id")] == before


@pytest.mark.parametrize("kind", ["important", "followup"])
def test_persistent_resource_quarantine_restart_keeps_original_notice_deadline(tmp_path, monkeypatch, kind):
    from src.launcher.backend import ProductionBackend
    from src.workflow.mail_research import InquiryCatalog, MailResearchService
    from src.workflow.v12_store import V12Store
    with notice(tmp_path, kind, monkeypatch, "blocked") as n:
        initial = n.clock[0]
        assert n.worker().run_due(now=initial) == 0
        n.clock[0] = initial+timedelta(seconds=119)
        restarted = ProductionBackend(root=tmp_path)
        restarted._store, restarted._v12_store = n.queue, V12Store(n.ledger.database_path)
        restarted._mail_brief = SimpleNamespace(cached_lines=lambda _: ())
        service = MailResearchService(store=n.service.store, inbox_factory=n.service.inbox_factory,
            source_reader=lambda *_: pytest.fail("protected resource must not be touched"), fx_provider=None,
            catalog=InquiryCatalog(), outbox=restarted._v12_store, worker=n.service.worker, clock=lambda: n.clock[0])
        restarted._mail_research_service = service
        transport = QQSMTPTransport(config=QQSMTPConfig(sender_address="sender@example.invalid"),
            credentials=FakeCredentials(login()), smtp_factory=lambda *a, **k: n.smtp, clock=lambda: n.clock[0])
        worker = V12NotificationWorker(restarted._v12_store, transport, scope="business",
            review_current=restarted._review_current_mail, prepare_content=restarted._prepare_business_mail)
        try:
            assert service._resource_blocked and not service.run_one()
            for elapsed in (119, 120, 121):
                n.clock[0] = initial+timedelta(seconds=elapsed)
                restarted._source_projection.observe(SHEET, (n.reader.row,), n.queue.all_items(), at=n.clock[0])
                assert worker.run_due(now=n.clock[0]) == (2 if elapsed == 120 else 0)
            assert n.smtp.send_attempts == 2
            assert service.store.resource_blocked()  # Fallback never clears protection.
        finally:
            restarted.shutdown()


def test_unconfigured_recipient_is_still_suppressed_at_fallback(tmp_path, monkeypatch):
    with notice(tmp_path, "important", monkeypatch, "missing",
            recipients=(NotificationRecipient("owner", "intruder@example.invalid"),)) as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120); n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 0 and n.smtp.send_attempts == 0
        with n.service.store.connect() as db:
            assert {r[0] for r in db.execute("SELECT outcome FROM workflow_v12_notification_recipients")} == {"SUPPRESSED"}


@pytest.mark.parametrize("kind", ["important", "followup"])
def test_optional_missing_service_adds_no_wait_or_mutation_to_notice_preparation(tmp_path, monkeypatch, kind):
    from time import monotonic
    with notice(tmp_path, kind, monkeypatch, "missing") as n:
        with n.service.store.connect() as db:
            before = db.execute("SELECT * FROM workflow_items").fetchall()
        begin = monotonic()
        assert n.worker().run_due(now=n.clock[0]) == 0
        assert monotonic()-begin < 1  # No sleep/research/retry wait in business sending path.
        assert n.reads == [] and n.service.threads == []
        with n.service.store.connect() as db:
            assert db.execute("SELECT * FROM workflow_items").fetchall() == before


@pytest.mark.parametrize("kind", ["important", "followup"])
@pytest.mark.parametrize("report_state", ["stale", "malformed"])
def test_unusable_ready_content_does_not_extend_deadline(tmp_path, monkeypatch, kind, report_state):
    with notice(tmp_path, kind, monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        with n.service.store.connect() as db:
            key = db.execute("SELECT task_id FROM workflow_mail_research WHERE origin='business'").fetchone()[0]
        report = {"completed_at": "bad-date" if report_state == "malformed" else (n.clock[0]-timedelta(minutes=16)).isoformat(),
            "text": "stale fabricated market54321", "html": "<p>stale fabricated market54321</p>"}
        n.service.store.finish(key, state="READY", report=report)
        n.clock[0] += timedelta(seconds=120); n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        assert all("54321" not in m.get_body(preferencelist=("plain",)).get_content() for m in n.smtp.messages)
        assert n.reads == []


@pytest.mark.parametrize("kind", [NotificationKind.TP_RESEARCH, NotificationKind.DUPLICATE_ORDER])
def test_unrelated_notification_preparation_has_no_optional_service_dependency(tmp_path, monkeypatch, kind):
    from dataclasses import replace
    with notice(tmp_path, "important", monkeypatch, "exception") as n:
        command, = n.ledger.claim_due_notifications(now=n.clock[0], scope="business")
        unrelated = replace(command, kind=kind)
        assert n.backend._prepare_business_mail(unrelated, n.clock[0]) is unrelated
        assert n.reads == [] and n.smtp.send_attempts == 0


@pytest.mark.parametrize("kind", ["important", "followup"])
def test_first_preparation_after_deadline_starts_research_and_sends_fallback(tmp_path, monkeypatch, kind):
    with notice(tmp_path, kind, monkeypatch, "ineligible") as n:
        n.clock[0] += timedelta(seconds=121)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        with n.service.store.connect() as db:
            assert db.execute("SELECT count(*) FROM workflow_mail_research").fetchone()[0] == 1
        assert n.smtp.send_attempts == 2

@pytest.mark.parametrize("usable", [False, None])
def test_unproven_ready_report_is_not_sent_as_detailed_content(tmp_path, monkeypatch, usable):
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        with n.service.store.connect() as db:
            key = db.execute("SELECT task_id FROM workflow_mail_research WHERE origin='business'").fetchone()[0]
        report = {"completed_at": n.clock[0].isoformat(), "text": "unproven quote", "html": "<p>unproven quote</p>"}
        if usable is not None:
            report["usable"] = usable
        n.service.store.finish(key, state="READY", report=report)
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        for message in n.smtp.messages:
            body = message.get_body(preferencelist=("plain",)).get_content()
            assert "unproven quote" not in body
            assert "详细市场报价暂不可用" in body

def test_ready_report_for_changed_order_is_not_attached(tmp_path, monkeypatch):
    import json
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        with n.service.store.connect() as db:
            key, payload = db.execute("SELECT task_id,payload FROM workflow_mail_research WHERE origin='business'").fetchone()
            order = json.loads(payload)
            order["quantity"] += 1
            db.execute("UPDATE workflow_mail_research SET payload=? WHERE task_id=?", (json.dumps(order), key))
        n.service.store.finish(key, state="READY", report={"usable": True, "completed_at": n.clock[0].isoformat(),
            "text": "wrong order report", "html": "<p>wrong order report</p>"})
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        assert all("wrong order report" not in m.get_body(preferencelist=("plain",)).get_content() for m in n.smtp.messages)

@pytest.mark.parametrize("detailed", [False, True])
def test_real_preparer_smtp_and_success_event_preserve_content_evidence(tmp_path, monkeypatch, detailed):
    import hashlib
    import json
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        if detailed:
            assert n.worker().run_due(now=n.clock[0]) == 0
            n.service.admit = lambda: True
            assert n.service.run_one()
        else:
            n.clock[0] += timedelta(seconds=120)
            n.refresh()
        captured = []
        prepare = n.backend._prepare_business_mail
        def capture(command, now):
            result = prepare(command, now)
            captured.append(result)
            return result
        n.backend._prepare_business_mail = capture
        assert n.worker().run_due(now=n.clock[0]) == 2
        with n.service.store.connect() as db:
            proofs = [json.loads(row[0])["notification_content"] for row in db.execute(
                "SELECT payload_json FROM workflow_v12_events WHERE event_type='NOTIFICATION_DELIVERY_SUCCEEDED'")]
        assert len(proofs) == len(captured) == len(n.smtp.messages) == 2
        for prepared, message, proof in zip(captured, n.smtp.messages, proofs):
            expected = hashlib.sha256(json.dumps([prepared.subject, prepared.text_body, prepared.html_body],
                ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
            assert proof["content_sha256"] == expected
            assert proof["kind"] == ("detailed" if detailed else "basic")
            assert message.get_body(preferencelist=("plain",)).get_content().rstrip("\n") == prepared.text_body.rstrip("\n")
            assert message.get_body(preferencelist=("html",)).get_content().rstrip("\n") == prepared.html_body.rstrip("\n")



def _exercise_dormant_supplement_guards_for_test(backend):
    """Exercise legacy guard internals with fake SMTP; production policy stays disabled."""
    from src.launcher.mail_research_composition import review_business_supplement

    original_review = backend._review_current_mail
    def review(command, now):
        import json
        if json.loads(command.review or "{}").get("business_supplement"):
            return review_business_supplement(backend, command, now)[0]
        return original_review(command, now)
    backend._review_current_mail = review

@pytest.mark.parametrize("kind", ["important", "followup"])
def test_ready_report_supplements_only_proven_basic_recipients_once(tmp_path, monkeypatch, kind):
    from src.launcher.mail_research_composition import queue_ready_business_supplements
    with notice(tmp_path, kind, monkeypatch, "ineligible") as n:
        _exercise_dormant_supplement_guards_for_test(n.backend)
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.service.admit = lambda: True
        assert n.service.run_one()
        assert queue_ready_business_supplements(n.backend, n.clock[0]) == 2
        assert n.worker().run_due(now=n.clock[0]) == 2
        assert queue_ready_business_supplements(n.backend, n.clock[0]) == 0
        assert n.worker().run_due(now=n.clock[0]) == 0
        assert n.smtp.send_attempts == 4
        import json
        with n.service.store.connect() as db:
            report = json.loads(db.execute("SELECT report FROM workflow_mail_research WHERE origin='business'").fetchone()[0])
        for message in n.smtp.messages[2:]:
            body = message.get_body(preferencelist=("plain",)).get_content()
            assert "详细市场报价暂不可用" not in body
            assert body.count(report["text"]) == 1
            assert all(name in body for name in ("IC.net", "Findchips", "华强", "立创", "正能量", "INSO"))

@pytest.mark.parametrize("state", ["original_unknown", "original_detailed", "changed_status", "stale_report"])
def test_supplement_protections_prevent_unsafe_delivery(tmp_path, monkeypatch, state):
    from src.launcher.mail_research_composition import queue_ready_business_supplements
    with notice(tmp_path, "important", monkeypatch, "ineligible",
                send_error=TimeoutError("synthetic") if state == "original_unknown" else None) as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        if state == "original_detailed":
            n.service.admit = lambda: True
            assert n.service.run_one()
        else:
            n.clock[0] += timedelta(seconds=120)
            n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        if state != "original_detailed":
            n.service.admit = lambda: True
            assert n.service.run_one()
        if state == "changed_status":
            assert queue_ready_business_supplements(n.backend, n.clock[0]) == 2
            n.reader.row = WorksheetRow(n.record.row_position, {**n.reader.row.cells, "A": "已报价给客户"})
            n.refresh()
            assert n.worker().run_due(now=n.clock[0]) == 0
        else:
            if state == "stale_report":
                n.clock[0] += timedelta(minutes=16)
                n.refresh()
            assert queue_ready_business_supplements(n.backend, n.clock[0]) == 0
        assert n.smtp.send_attempts == 2


def test_automatic_recovery_queues_only_original_recipient_who_got_basic(tmp_path, monkeypatch):
    from src.launcher.mail_research_composition import queue_ready_business_supplements
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        _exercise_dormant_supplement_guards_for_test(n.backend)
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        prepare = n.backend._prepare_business_mail
        calls = 0
        def first_basic_then_report(command, now):
            nonlocal calls
            result = prepare(command, now)
            calls += 1
            if calls == 1:
                n.service.admit = lambda: True
                assert n.service.run_one()
            return result
        n.backend._prepare_business_mail = first_basic_then_report
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.backend._prepare_business_mail = prepare
        worker = n.worker()
        n.service.recover_business = lambda now: queue_ready_business_supplements(n.backend, now)
        assert n.service.recover_business(n.clock[0]) == 1
        assert worker.run_due(now=n.clock[0]) == 1
        assert n.service.recover_business(n.clock[0]) == 0
        assert worker.run_due(now=n.clock[0]) == 0
        assert n.smtp.send_attempts == 3

def test_supplement_is_rechecked_with_actual_dispatch_clock(tmp_path, monkeypatch):
    from src.launcher.mail_research_composition import queue_ready_business_supplements
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.service.admit = lambda: True
        assert n.service.run_one()
        assert queue_ready_business_supplements(n.backend, n.clock[0]) == 2
        claimed_at = n.clock[0]
        worker = n.worker()
        def later():
            n.clock[0] = claimed_at + timedelta(minutes=16)
            n.refresh()
            return n.clock[0]
        worker._clock = later
        assert worker.run_due(now=claimed_at) == 0
        assert n.smtp.send_attempts == 2


def test_blocked_supplement_recovery_does_not_block_original_notifications(tmp_path, monkeypatch):
    from threading import Event, Thread
    with notice(tmp_path, "important", monkeypatch, "missing") as n:
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        entered, release = Event(), Event()
        def recover():
            entered.set()
            release.wait(5)
        thread = Thread(target=recover)
        thread.start()
        try:
            assert entered.wait(2)
            assert n.worker().run_due(now=n.clock[0]) == 2
        finally:
            release.set()
            thread.join(2)

def test_supplement_scan_skips_large_completed_batch(tmp_path):
    import hashlib
    import json

    import src.launcher.mail_research_composition as composition
    from tests.workflow.test_v12_notifications import INQUIRY, NOW
    service, _, _, _, _, _ = scene(tmp_path)
    backend = SimpleNamespace(_mail_research_service=service, _v12_store=service.outbox)
    report = json.dumps({"usable": True, "completed_at": NOW.isoformat(), "reference_at": NOW.isoformat()})
    recipient = NotificationRecipient("a", "a@example.invalid")
    with service.store.connect() as db:
        for index in range(257):
            key = "oldest" if index == 0 else f"newer-{index:03}"
            created = (NOW + timedelta(microseconds=index)).isoformat()
            inquiry = INQUIRY if not index else f"synthetic-inquiry-{index}"
            if index:
                db.execute("INSERT INTO workflow_items (spreadsheet,worksheet,row_number,inquiry_id,record_identity_json,mpn_json,brand_json,quantity_json,importance_raw_json,status,attempt_count,created_at,updated_at) SELECT spreadsheet,worksheet,?,? ,record_identity_json,mpn_json,brand_json,quantity_json,importance_raw_json,status,0,created_at,updated_at FROM workflow_items WHERE inquiry_id=?", (index+100, inquiry, INQUIRY))
            db.execute("INSERT INTO workflow_v12_notification_commands (command_id,inquiry_id,kind,subject,text_body,created_at,payload_version,review_json) VALUES (?,?,?,?,?,?,1,?)",
                (key, inquiry, "IMPORTANT_ORDER", "subject", "text", created, json.dumps({"business_decision": {}})))
            db.execute("INSERT INTO workflow_v12_notification_recipients (command_id,recipient_id,address,outcome,attempt_count) VALUES (?,?,?,'SENT',1)",
                (key, recipient.recipient_id, recipient.address))
            db.execute("INSERT INTO workflow_mail_research (task_id,origin,payload,state,report,created_at) VALUES (?,'business','{}','READY',?,?)", (key, report, created))
            digest = hashlib.sha256(json.dumps([key, recipient.recipient_id, recipient.address], ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
            payload = json.dumps({"notification_content": {"version": 1, "attempt": 1, "kind": "basic", "command_id": key, "recipient_digest": digest, "content_sha256": "a" * 64}})
            db.execute("INSERT INTO workflow_v12_events (event_id,inquiry_id,event_type,occurred_at,source_module,schema_version,attempt,payload_json) VALUES (?,?,'NOTIFICATION_DELIVERY_SUCCEEDED',?,'notification',1,1,?)", ("event-"+key, inquiry, created, payload))
            if index:
                supplement = composition._supplement_id(key, recipient)
                db.execute("INSERT INTO workflow_v12_notification_commands (command_id,inquiry_id,kind,subject,text_body,created_at,payload_version,review_json) VALUES (?,?,?,?,?,?,1,?)", (supplement, inquiry, "IMPORTANT_ORDER", "supplement", "text", created, json.dumps({"business_supplement": {"original": key}})))
                db.execute("INSERT INTO workflow_v12_notification_recipients (command_id,recipient_id,address,outcome,attempt_count) VALUES (?,?,?,'SENT',1)", (supplement, recipient.recipient_id, recipient.address))
    assert composition.queue_ready_business_supplements(backend, NOW) == 1


@pytest.mark.parametrize("failure", ["unknown", "abandoned_claim"])
def test_supplement_unknown_or_abandoned_is_never_resent(tmp_path, monkeypatch, failure):
    from src.launcher.mail_research_composition import queue_ready_business_supplements
    from src.workflow.v12_store import V12Store
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        _exercise_dormant_supplement_guards_for_test(n.backend)
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.service.admit = lambda: True
        assert n.service.run_one()
        assert queue_ready_business_supplements(n.backend, n.clock[0]) == 2
        if failure == "unknown":
            n.smtp._send_error = TimeoutError("synthetic")
            assert n.worker().run_due(now=n.clock[0]) == 2
            n.smtp._send_error = None
            expected_sends = 4
        else:
            assert len(n.ledger.claim_due_notifications(now=n.clock[0], scope="business")) == 2
            expected_sends = 2
        restarted = V12Store(n.ledger.database_path)
        restarted.recover_abandoned_notification_attempts(at=n.clock[0], scope="business")
        assert queue_ready_business_supplements(n.backend, n.clock[0]) == 0
        assert n.worker(restarted).run_due(now=n.clock[0]) == 0
        assert n.smtp.send_attempts == expected_sends


def test_missing_original_trigger_evidence_prevents_supplement(tmp_path, monkeypatch):
    from src.launcher.mail_research_composition import queue_ready_business_supplements
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.service.admit = lambda: True
        assert n.service.run_one()
        with n.service.store.connect() as db:
            db.execute("UPDATE workflow_v12_notification_commands SET review_json=NULL WHERE kind='IMPORTANT_ORDER'")
        assert queue_ready_business_supplements(n.backend, n.clock[0]) == 0
        assert n.smtp.send_attempts == 2

def test_supplement_scan_database_lock_is_short(tmp_path, monkeypatch):
    import sqlite3
    from time import monotonic

    from src.launcher.mail_research_composition import queue_ready_business_supplements
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.service.admit = lambda: True
        assert n.service.run_one()
        with sqlite3.connect(n.service.store.path, timeout=0.1) as locked:
            locked.execute("BEGIN IMMEDIATE")
            started = monotonic()
            with pytest.raises(sqlite3.OperationalError):
                queue_ready_business_supplements(n.backend, n.clock[0])
            assert monotonic() - started < 2
            locked.rollback()

def test_existing_research_worker_runs_recovery_callback(tmp_path):
    service, _, _, _, _, _ = scene(tmp_path)
    calls = []
    service.run_one = lambda: False
    service.worker.run_due = lambda **kwargs: 0
    service.audit_delivery = lambda: None
    def recover(now):
        calls.append(now)
        service.stop_event.set()
    service.recover_business = recover
    service._work()
    assert len(calls) == 1

def test_supplement_expiring_during_final_review_is_not_sent(tmp_path, monkeypatch):
    from src.launcher.mail_research_composition import queue_ready_business_supplements
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.service.admit = lambda: True
        assert n.service.run_one()
        assert queue_ready_business_supplements(n.backend, n.clock[0]) == 2
        start = n.clock[0]
        ticks = iter((start, start + timedelta(minutes=16), start + timedelta(minutes=16)))
        worker = n.worker()
        worker._clock = lambda: next(ticks, start + timedelta(minutes=16))
        assert worker.run_due(now=start) == 0
        assert n.smtp.send_attempts == 2

def test_recently_completed_report_with_old_source_data_is_not_sent(tmp_path, monkeypatch):
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        with n.service.store.connect() as db:
            key, = db.execute("SELECT task_id FROM workflow_mail_research WHERE origin='business'").fetchone()
        report = {"usable": True, "completed_at": n.clock[0].isoformat(),
                  "reference_at": (n.clock[0]-timedelta(minutes=16)).isoformat(),
                  "text": "outdated prices", "html": "<p>outdated prices</p>"}
        n.service.store.finish(key, state="READY", report=report)
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        assert all("outdated prices" not in m.get_body(preferencelist=("plain",)).get_content() for m in n.smtp.messages)

def test_supplement_expiring_during_smtp_login_never_reaches_send(tmp_path, monkeypatch):
    from src.launcher.mail_research_composition import queue_ready_business_supplements
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.service.admit = lambda: True
        assert n.service.run_one()
        assert queue_ready_business_supplements(n.backend, n.clock[0]) == 2
        initial = n.clock[0]
        login = n.smtp.login
        def slow_login(user, password):
            result = login(user, password)
            n.clock[0] = initial + timedelta(minutes=16)
            n.refresh()
            return result
        n.smtp.login = slow_login
        worker = n.worker()
        worker._clock = lambda: n.clock[0]
        worker.run_due(now=initial)
        assert n.smtp.send_attempts == 2

def test_original_detailed_report_expiring_during_login_falls_back_without_failure(tmp_path, monkeypatch):
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.service.admit = lambda: True
        assert n.service.run_one()
        start = n.clock[0]
        login = n.smtp.login
        def slow_login(user, password):
            result = login(user, password)
            n.clock[0] = start + timedelta(minutes=16)
            n.refresh()
            return result
        n.smtp.login = slow_login
        worker = n.worker()
        worker._clock = lambda: n.clock[0]
        assert worker.run_due(now=start) == 0
        assert n.smtp.send_attempts == 0
        n.smtp.login = login
        assert worker.run_due(now=n.clock[0]) == 2
        assert n.smtp.send_attempts == 2
        assert all("详细市场报价暂不可用" in m.get_body(preferencelist=("plain",)).get_content() for m in n.smtp.messages)

def test_supplement_order_status_changes_during_login_prevent_send(tmp_path, monkeypatch):
    from src.launcher.mail_research_composition import queue_ready_business_supplements
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.service.admit = lambda: True
        assert n.service.run_one()
        assert queue_ready_business_supplements(n.backend, n.clock[0]) == 2
        login = n.smtp.login
        def change_status(user, password):
            result = login(user, password)
            n.reader.row = WorksheetRow(n.record.row_position, {**n.reader.row.cells, "A": "已报价给客户"})
            n.refresh()
            return result
        n.smtp.login = change_status
        n.worker().run_due(now=n.clock[0])
        assert n.smtp.send_attempts == 2

def test_followup_episode_changes_during_login_prevent_supplement(tmp_path, monkeypatch):
    from src.launcher.mail_research_composition import queue_ready_business_supplements
    with notice(tmp_path, "followup", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.service.admit = lambda: True
        assert n.service.run_one()
        assert queue_ready_business_supplements(n.backend, n.clock[0]) == 2
        login = n.smtp.login
        def new_episode(user, password):
            result = login(user, password)
            V13PurchaseFollowUpStore(n.ledger.database_path).record_confirmed(n.iid, confirmed_at=n.clock[0])
            return result
        n.smtp.login = new_episode
        n.worker().run_due(now=n.clock[0])
        assert n.smtp.send_attempts == 2

def test_guard_rejects_two_source_snapshot_replacements(tmp_path, monkeypatch):
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        original = n.ledger.notification_command(n.ledger.claim_due_notifications(now=n.clock[0])[0].command_id)
        guard = n.backend._supplement_delivery_guard(original)
        try:
            n.refresh()
            n.refresh()
            assert guard() is False
        finally:
            guard.close()


@pytest.mark.parametrize("change", ["stop", "brief"])
def test_supplement_stop_or_brief_change_during_login_prevents_send(tmp_path, monkeypatch, change):
    from src.launcher.mail_research_composition import queue_ready_business_supplements
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.service.admit = lambda: True
        assert n.service.run_one()
        assert queue_ready_business_supplements(n.backend, n.clock[0]) == 2
        login = n.smtp.login
        changes = []
        def changed(user, password):
            result = login(user, password)
            if change == "stop":
                n.backend._owner_stop_requested = True
            else:
                changes.append(len(changes) + 1)
                n.backend._mail_brief.cached_lines = lambda _: ({"sheet": str(changes[-1])},)
                n.backend._mail_brief.service.token = (len(changes), object())
            return result
        n.smtp.login = changed
        n.worker().run_due(now=n.clock[0])
        assert n.smtp.send_attempts == 2


def test_supplement_guard_closes_if_clock_fails_after_creation(tmp_path, monkeypatch):
    from src.launcher.mail_research_composition import queue_ready_business_supplements
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        _exercise_dormant_supplement_guards_for_test(n.backend)
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.service.admit = lambda: True
        assert n.service.run_one()
        assert queue_ready_business_supplements(n.backend, n.clock[0]) == 2
        closed = []
        class Guard:
            def __call__(self): return True
            def close(self): closed.append(True)
        worker = n.worker()
        worker._guard_factory = lambda command, **kwargs: Guard()
        count = 0
        def clock():
            nonlocal count
            count += 1
            if count > 1:
                raise RuntimeError("synthetic clock failure")
            return n.clock[0]
        worker._clock = clock
        with pytest.raises(RuntimeError):
            worker.run_due(now=n.clock[0])
        assert closed == [True] and n.smtp.send_attempts == 2

def test_large_source_snapshot_does_not_block_supplement_guard(tmp_path, monkeypatch):
    from time import monotonic
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        original = n.ledger.notification_command(n.ledger.claim_due_notifications(now=n.clock[0])[0].command_id)
        rows = (n.reader.row,) + tuple(WorksheetRow(i, {"A": "未发"}) for i in range(10000, 20001))
        n.backend._source_projection.observe(SHEET, rows, n.queue.all_items(), at=n.clock[0])
        start = monotonic()
        guard = n.backend._supplement_delivery_guard(original)
        try:
            assert guard() is True
            assert monotonic()-start < 2
        finally:
            guard.close()


def test_projection_publish_lock_makes_supplement_guard_defer(tmp_path, monkeypatch):
    from threading import Event, Thread
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        original = n.ledger.notification_command(n.ledger.claim_due_notifications(now=n.clock[0])[0].command_id)
        guard = n.backend._supplement_delivery_guard(original)
        entered, release = Event(), Event()
        def hold_publish():
            with n.backend._source_projection._revision_lock:
                n.backend._source_projection.revision += 1
                entered.set()
                release.wait(3)
        thread = Thread(target=hold_publish)
        thread.start()
        try:
            assert entered.wait(2)
            assert guard() is False
        finally:
            release.set()
            thread.join(2)
            guard.close()

def test_source_copy_in_progress_blocks_old_snapshot_and_guard(tmp_path, monkeypatch):
    from collections.abc import Mapping
    from threading import Event, Thread
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        original = n.ledger.notification_command(n.ledger.claim_due_notifications(now=n.clock[0])[0].command_id)
        guard = n.backend._supplement_delivery_guard(original)
        entered, release = Event(), Event()
        class SlowCells(Mapping):
            def __iter__(self):
                entered.set()
                release.wait(3)
                return iter(n.reader.row.cells)
            def __len__(self): return len(n.reader.row.cells)
            def __getitem__(self, key): return n.reader.row.cells[key]
        row = WorksheetRow(n.record.row_position, SlowCells())
        thread = Thread(target=lambda: n.backend._source_projection.observe(SHEET, (row,), n.queue.all_items(), at=n.clock[0]))
        thread.start()
        try:
            assert entered.wait(2)
            assert n.backend._source_projection.snapshot(SHEET) is None
            assert guard() is False
        finally:
            release.set()
            thread.join(3)
            guard.close()
        assert not thread.is_alive()


def test_failed_source_copy_invalidates_prior_snapshot(tmp_path, monkeypatch):
    from collections.abc import Mapping
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        class BrokenCells(Mapping):
            def __iter__(self): raise ValueError("synthetic invalid cells")
            def __len__(self): return 1
            def __getitem__(self, key): raise KeyError(key)
        row = WorksheetRow(n.record.row_position, BrokenCells())
        with pytest.raises(ValueError):
            n.backend._source_projection.observe(SHEET, (row,), n.queue.all_items(), at=n.clock[0])
        assert n.backend._source_projection.snapshot(SHEET) is None
        assert n.backend._current_mail_source(n.iid, n.clock[0]) is None

def test_unrelated_ledger_write_during_login_does_not_block_supplement(tmp_path, monkeypatch):
    from src.launcher.mail_research_composition import queue_ready_business_supplements
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        _exercise_dormant_supplement_guards_for_test(n.backend)
        with n.service.store.connect() as db:
            db.execute("INSERT INTO workflow_items (spreadsheet,worksheet,row_number,inquiry_id,record_identity_json,mpn_json,brand_json,quantity_json,importance_raw_json,status,attempt_count,created_at,updated_at) SELECT spreadsheet,worksheet,999,'other-inquiry',record_identity_json,mpn_json,brand_json,quantity_json,importance_raw_json,status,0,created_at,updated_at FROM workflow_items WHERE inquiry_id=?", (n.iid,))
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.service.admit = lambda: True
        assert n.service.run_one()
        assert queue_ready_business_supplements(n.backend, n.clock[0]) == 2
        login = n.smtp.login
        counter = []
        def unrelated_write(user, password):
            result = login(user, password)
            counter.append(1)
            with n.service.store.connect() as db:
                db.execute("UPDATE workflow_items SET updated_at=? WHERE inquiry_id='other-inquiry'", (str(len(counter)),))
            return result
        n.smtp.login = unrelated_write
        assert n.worker().run_due(now=n.clock[0]) == 2
        assert n.smtp.send_attempts == 4

def test_older_source_copy_finishing_last_cannot_replace_newer(tmp_path, monkeypatch):
    from collections.abc import Mapping
    from threading import Event, Thread
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        entered, release = Event(), Event()
        old_cells = dict(n.reader.row.cells)
        class SlowCells(Mapping):
            def __iter__(self):
                entered.set()
                release.wait(3)
                return iter(old_cells)
            def __len__(self): return len(old_cells)
            def __getitem__(self, key): return old_cells[key]
        old = WorksheetRow(n.record.row_position, SlowCells())
        newer = WorksheetRow(n.record.row_position, {**old_cells, "A": "已报价给客户"})
        items = n.queue.all_items()
        thread = Thread(target=lambda: n.backend._source_projection.observe(SHEET, (old,), items, at=n.clock[0]))
        thread.start()
        try:
            assert entered.wait(2)
            assert n.backend._source_projection.observe(SHEET, (newer,), items, at=n.clock[0]) is True
            assert n.backend._source_projection.snapshot(SHEET)[0][0].cells["A"] == "已报价给客户"
        finally:
            release.set()
            thread.join(3)
        assert not thread.is_alive()
        assert n.backend._source_projection.snapshot(SHEET)[0][0].cells["A"] == "已报价给客户"


def test_source_read_failure_with_ledger_error_invalidates_old_snapshot(tmp_path, monkeypatch):
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.backend._source_projection.snapshot(SHEET) is not None
        monkeypatch.setattr(n.queue, "all_items", lambda: (_ for _ in ()).throw(RuntimeError("synthetic ledger failure")))
        n.backend._observe_source_rows(SHEET, (), True)
        assert n.backend._source_projection.snapshot(SHEET) is None
        assert n.backend._current_mail_source(n.iid, n.clock[0]) is None


def test_source_update_marks_pending_before_slow_ledger_read(tmp_path, monkeypatch):
    from threading import Event, Thread
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        entered, release = Event(), Event()
        original = n.queue.all_items
        def slow():
            entered.set()
            release.wait(3)
            return original()
        monkeypatch.setattr(n.queue, "all_items", slow)
        thread = Thread(target=lambda: n.backend._observe_source_rows(SHEET, (n.reader.row,), False))
        thread.start()
        try:
            assert entered.wait(2)
            assert n.backend._source_projection.snapshot(SHEET) is None
        finally:
            release.set()
            thread.join(3)
        assert not thread.is_alive()

def test_source_projection_marks_task_status_unverified_while_latest_read_pending(tmp_path, monkeypatch):
    from src.gui.contracts import V12BusinessLabel, V12OrderStateDTO
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        dto = V12OrderStateDTO(n.iid, V12BusinessLabel.PURCHASE_SENT, None)
        n.backend._source_projection.statuses[n.iid] = ("未发", n.clock[0], True)
        n.backend._source_projection._status_sources[n.iid] = SHEET
        assert n.backend._source_projection.project(dto, now=n.clock[0]).source_fresh
        ticket = n.backend._source_projection.begin_update(SHEET)
        try:
            pending = n.backend._source_projection.project(dto, now=n.clock[0])
            assert not pending.source_fresh and pending.source_status is None
        finally:
            n.backend._source_projection.end_update(SHEET, ticket=ticket)

def test_delayed_source_publication_keeps_original_observation_time(tmp_path, monkeypatch):
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        old = n.clock[0] - timedelta(minutes=16)
        ticket = n.backend._source_projection.begin_update(SHEET)
        assert not n.backend._observe_source_rows(SHEET, (n.reader.row,), False, ticket=ticket, observed_at=old)
        assert n.backend._source_projection.snapshot(SHEET)[1] == n.clock[0]

@pytest.mark.parametrize("mode", ["missing", "queue_full"])
def test_missing_business_research_recovers_after_basic_delivery(tmp_path, monkeypatch, mode):
    from src.launcher.mail_research_composition import (
        queue_ready_business_supplements,
        recover_missing_business_reports,
    )
    with notice(tmp_path, "important", monkeypatch, mode) as n:
        _exercise_dormant_supplement_guards_for_test(n.backend)
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.backend._mail_research_service = n.service
        n.service.store.capacity = 64
        assert recover_missing_business_reports(n.backend, n.clock[0]) == 1
        assert n.service.run_one()
        assert queue_ready_business_supplements(n.backend, n.clock[0]) == 2
        assert n.worker().run_due(now=n.clock[0]) == 2
        assert n.smtp.send_attempts == 4

def test_full_capacity_recovery_is_persistently_deferred_without_consuming_capacity(tmp_path, monkeypatch):
    from src.launcher.mail_research_composition import recover_missing_business_reports
    with notice(tmp_path, "important", monkeypatch, "queue_full") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        assert recover_missing_business_reports(n.backend, n.clock[0]) == 0
        with n.service.store.connect() as db:
            state, attempts, next_at = db.execute("SELECT state,attempts,next_at FROM workflow_mail_research WHERE origin='business-recovery'").fetchone()
            assert state == "RECOVERY_WAIT" and attempts == 0 and next_at
            assert n.service.store._active_count(db) == 0
        n.service.store.capacity = 64
        n.service.store.migrate()
        assert recover_missing_business_reports(n.backend, n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=61)
        n.refresh()
        assert recover_missing_business_reports(n.backend, n.clock[0]) == 1


def test_unavailable_business_report_recovery_has_persistent_limit_and_backoff(tmp_path, monkeypatch):
    import json

    from src.launcher.mail_research_composition import recover_missing_business_reports
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.service.admit = lambda: True
        n.service.source_reader = lambda *args: (_ for _ in ()).throw(TimeoutError("synthetic outage"))
        for _ in range(3):
            assert n.service.run_one()
            n.clock[0] += timedelta(seconds=121)
        n.refresh()
        with n.service.store.connect() as db:
            state, report = db.execute("SELECT state,report FROM workflow_mail_research WHERE origin='business'").fetchone()
            assert state == "READY" and json.loads(report)["usable"] is False
        for cycle in range(3):
            assert recover_missing_business_reports(n.backend, n.clock[0]) == 1
            assert n.service.run_one()
            assert recover_missing_business_reports(n.backend, n.clock[0]) == 0
            n.service.store.migrate()
            n.clock[0] += timedelta(minutes=15, seconds=1)
            n.refresh()
        assert recover_missing_business_reports(n.backend, n.clock[0]) == 0
        with n.service.store.connect() as db:
            attempts, state = db.execute("SELECT attempts,state FROM workflow_mail_research WHERE origin='business-recovery'").fetchone()
        assert attempts == 3 and state == "RECOVERY_WAIT"


@pytest.mark.parametrize("problem", ["closed", "expired", "unknown", "resource_blocked", "changed_model"])
def test_missing_report_recovery_respects_existing_business_protections(tmp_path, monkeypatch, problem):
    from src.launcher.mail_research_composition import recover_missing_business_reports
    with notice(tmp_path, "important", monkeypatch, "missing",
                send_error=TimeoutError("synthetic") if problem == "unknown" else None) as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.backend._mail_research_service = n.service
        if problem == "closed":
            n.reader.row = WorksheetRow(n.record.row_position, {**n.reader.row.cells, "A": "已报价给客户"})
        elif problem == "changed_model":
            n.reader.row = WorksheetRow(n.record.row_position, {**n.reader.row.cells, "E": "different"})
        elif problem == "expired":
            n.clock[0] += timedelta(days=8)
        elif problem == "resource_blocked":
            n.service.store.block_resource(n.clock[0])
        n.refresh()
        assert recover_missing_business_reports(n.backend, n.clock[0]) == 0
        with n.service.store.connect() as db:
            assert db.execute("SELECT count(*) FROM workflow_mail_research WHERE origin='business'").fetchone()[0] == 0

def test_recovery_deferral_counts_once_per_due_time(tmp_path, monkeypatch):
    import json
    from time import monotonic
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        store = n.service.store
        for _ in range(3):
            store.defer_business_recovery("same-command", n.clock[0], deadline=monotonic()+1)
        with store.connect() as db:
            state, progress = db.execute("SELECT state,progress FROM workflow_mail_research WHERE origin='business-recovery'").fetchone()
        assert state == "RECOVERY_WAIT" and json.loads(progress)["deferrals"] == 1
        for delay in (61, 121, 241):
            n.clock[0] += timedelta(seconds=delay)
            store.defer_business_recovery("same-command", n.clock[0], deadline=monotonic()+1)
        with store.connect() as db:
            state, progress = db.execute("SELECT state,progress FROM workflow_mail_research WHERE origin='business-recovery'").fetchone()
        assert state == "RECOVERY_WAIT" and json.loads(progress)["deferrals"] == 4


def test_business_job_rechecks_closed_order_before_any_research(tmp_path, monkeypatch):
    from src.launcher.mail_research_composition import review_business_job
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.reader.row = WorksheetRow(n.record.row_position, {**n.reader.row.cells, "A": "已报价给客户"})
        n.refresh()
        n.service.admit = lambda: True
        n.service.review_business_job = lambda job, payload, now: review_business_job(n.backend, job, payload, now)
        assert not n.service.run_one()
        assert n.reads == []


def test_business_job_recheck_allows_unchanged_order(tmp_path, monkeypatch):
    from src.launcher.mail_research_composition import review_business_job
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.service.admit = lambda: True
        n.service.review_business_job = lambda job, payload, now: review_business_job(n.backend, job, payload, now)
        assert n.service.run_one()
        assert len(n.reads) == 6


def test_temporary_missing_source_can_recover_after_multiple_deferrals(tmp_path, monkeypatch):
    from src.launcher.mail_research_composition import recover_missing_business_reports
    with notice(tmp_path, "important", monkeypatch, "missing") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.backend._mail_research_service = n.service
        original = n.backend._current_mail_source
        n.backend._current_mail_source = lambda *args, **kwargs: None
        for delay in (61, 121, 241, 481):
            assert recover_missing_business_reports(n.backend, n.clock[0]) == 0
            n.clock[0] += timedelta(seconds=delay)
        n.backend._current_mail_source = original
        n.refresh()
        assert recover_missing_business_reports(n.backend, n.clock[0]) == 1


@pytest.mark.parametrize("review,allowed", [("{}", True), ('{"business_decision": null}', False), ('{"business_decision": {}}', False)])
def test_original_a_tier_allows_only_absent_decision_snapshot(tmp_path, monkeypatch, review, allowed):
    from dataclasses import replace
    from time import monotonic

    from src.launcher.mail_research_composition import _recovery_order
    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        with n.service.store.connect() as db:
            command_id = db.execute("SELECT command_id FROM workflow_v12_notification_commands WHERE kind='IMPORTANT_ORDER'").fetchone()[0]
        command = replace(n.ledger.notification_command(command_id), review=review)
        result = _recovery_order(n.backend, command, command.recipients[0], n.clock[0], monotonic()+1, allow_current_a=True)
        assert (result is not None) is allowed
        assert _recovery_order(n.backend, command, command.recipients[0], n.clock[0], monotonic()+1) is None


def test_failed_constructed_service_retries_once_without_rebuilding(tmp_path, monkeypatch):
    with notice(tmp_path, "important", monkeypatch, "start_error") as n:
        starts = []
        n.service.start = lambda: starts.append("started")
        n.service.stop_event.set()
        n.backend._mail_start_retry_at = 0
        n.backend.retry_failed_process_service()
        n.backend._mail_start_retry_thread.join(timeout=2)
        assert starts == ["started"] and not n.backend._mail_start_failed
        n.backend.retry_failed_process_service()
        assert starts == ["started"]


def test_failed_service_is_not_restarted_while_former_thread_is_alive(tmp_path, monkeypatch):
    from threading import Event, Thread
    with notice(tmp_path, "important", monkeypatch, "start_error") as n:
        release = Event()
        previous = Thread(target=release.wait)
        previous.start()
        n.service.threads = [previous]
        starts = []
        n.service.start = lambda: starts.append("started")
        try:
            n.backend._mail_start_retry_at = 0
            n.backend.retry_failed_process_service()
            n.backend._mail_start_retry_thread.join(timeout=2)
            assert not starts and n.backend._mail_start_failed
        finally:
            release.set()
            previous.join(timeout=2)


def test_shutdown_serializes_with_failed_service_retry(tmp_path, monkeypatch):
    from threading import Event, Thread
    with notice(tmp_path, "important", monkeypatch, "start_error") as n:
        entered, release = Event(), Event()
        calls = []
        def start():
            calls.append("started")
            entered.set()
            assert release.wait(2)
        n.service.start = start
        n.backend._mail_start_retry_at = 0
        n.backend.retry_failed_process_service()
        assert entered.wait(2)
        closer = Thread(target=n.backend.shutdown)
        closer.start()
        try:
            assert not n.backend._closed
        finally:
            release.set()
            closer.join(timeout=3)
        assert not closer.is_alive() and n.backend._closed
        n.backend.retry_failed_process_service()
        assert calls == ["started"]


def test_failed_service_unknown_thread_identity_prevents_retry(tmp_path, monkeypatch):
    with notice(tmp_path, "important", monkeypatch, "start_error") as n:
        uncertain = SimpleNamespace(ident=None, is_alive=lambda: False)
        n.service.threads = [uncertain]
        starts = []
        n.service.start = lambda: starts.append("started")
        n.backend._mail_start_retry_at = 0
        n.backend.retry_failed_process_service()
        n.backend._mail_start_retry_thread.join(timeout=2)
        assert starts == [] and n.backend._mail_start_failed


def test_ready_report_recovery_never_sends_or_queues_a_supplement(tmp_path, monkeypatch):
    from src.launcher.mail_research_composition import (
        recover_business_reports_and_supplements,
    )

    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.service.admit = lambda: True
        assert n.service.run_one()
        recover_business_reports_and_supplements(n.backend, n.clock[0])
        assert n.worker().run_due(now=n.clock[0]) == 0
        assert n.smtp.send_attempts == 2
        with n.service.store.connect() as db:
            assert db.execute("SELECT count(*) FROM workflow_v12_notification_commands WHERE command_id LIKE 'business-supplement:%'").fetchone()[0] == 0


def test_previously_queued_supplements_are_suppressed_without_smtp(tmp_path, monkeypatch):
    from src.launcher.mail_research_composition import queue_ready_business_supplements

    with notice(tmp_path, "important", monkeypatch, "ineligible") as n:
        assert n.worker().run_due(now=n.clock[0]) == 0
        n.clock[0] += timedelta(seconds=120)
        n.refresh()
        assert n.worker().run_due(now=n.clock[0]) == 2
        n.service.admit = lambda: True
        assert n.service.run_one()
        assert queue_ready_business_supplements(n.backend, n.clock[0]) == 2
        assert n.worker().run_due(now=n.clock[0]) == 0
        assert n.smtp.send_attempts == 2
        with n.service.store.connect() as db:
            outcomes = db.execute("SELECT outcome FROM workflow_v12_notification_recipients WHERE command_id LIKE 'business-supplement:%'").fetchall()
        assert len(outcomes) == 2 and all(row[0] == "SUPPRESSED" for row in outcomes)


def test_background_recovery_does_not_research_or_queue_after_sent_notice(monkeypatch):
    from src.launcher import mail_research_composition as composition

    def unexpected(*args, **kwargs):
        pytest.fail("sent notice must not trigger extra research or a supplement")
    monkeypatch.setattr(composition, "recover_missing_business_reports", unexpected)
    monkeypatch.setattr(composition, "queue_ready_business_supplements", unexpected)
    assert composition.recover_business_reports_and_supplements(object(), NOW) is None
