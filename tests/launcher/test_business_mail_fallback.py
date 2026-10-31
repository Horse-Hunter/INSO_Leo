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
            prepare_content=backend._prepare_business_mail)
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
