"""All synthetic: fake IMAP/Google/market/CDP/SMTP; no external effects."""
import json
import threading
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from email.header import Header
from types import SimpleNamespace

import pytest

from src.order_mail.research_requests import (
    ACCOUNT,
    ResearchMail,
    parse_research_header,
)
from src.research.detailed import DetailedOrder, TpOffer, TpQuote, TpSourceResult
from src.research.source_contracts import PRICE_SOURCES, SourceEvidence, SourceOutcome
from src.workflow.mail_research import InquiryCatalog, MailResearchService
from src.workflow.mail_research_store import MailResearchStore
from src.workflow.v12_contracts import DeliveryOutcome
from src.workflow.v12_notifications import (
    FakeNotificationTransport,
    V12NotificationWorker,
)
from src.workflow.v13_integration import V13HoldStore
from tests.workflow.test_v12_notifications import NOW, prepared_store


def header(subject="调研 STM32F103C8T6", sender="sales2@inso-hk.com"):
    return ("From: " + sender + "\r\nSubject: " + Header(subject, "utf-8").encode()
            + "\r\nDate: Fri, 30 Oct 2026 10:00:00 +0800\r\nMessage-ID: <synthetic@example.invalid>\r\n\r\n").encode()


@pytest.mark.parametrize("subject", ["调研 STM32F103C8T6", "调研STM32F103C8T6"])
def test_header_request(subject):
    assert parse_research_header(header(subject)).mpn == "STM32F103C8T6"


@pytest.mark.parametrize("subject,sender", [("调研", "sales2@inso-hk.com"),
    ("调研 MPN DROP ALL", "sales2@inso-hk.com"), ("Re: 调研MPN", "sales2@inso-hk.com"),
    ("调研MPN", "sales2@inso-hk.com.attacker.invalid"), ("调研MPN", '"sales2@inso-hk.com" <attacker@example.invalid>'),
    ("调研MPN", "sal\u200bes2@inso-hk.com"), ("调研MPN", "sales2@inso-hk.com, other@example.invalid")])
def test_untrusted_header_ignored(subject, sender):
    assert parse_research_header(header(subject, sender)) is None


def scene(tmp_path, *, capacity=64, outbox=None):
    outbox = outbox or prepared_store(tmp_path)
    V13HoldStore(outbox.database_path).migrate()
    store = MailResearchStore(outbox.database_path, capacity=capacity)
    store.migrate()
    inbox = SimpleNamespace(validity=1, latest=100, messages=[], checks=0)
    class Inbox:
        def __enter__(self):
            inbox.checks += 1
            self.validity, self.latest = inbox.validity, inbox.latest
            return self
        def __exit__(self, *_):
            pass
        def read(self, after, limit=32):
            upper = min(inbox.latest, after+limit)
            return upper, tuple((uid, mail) for uid, mail in inbox.messages if after < uid <= upper)
    calls = []
    def read(key, source, order, reference, fx):
        calls.append((key, source, order.quantity))
        offer = TpOffer(source, order.mpn, Decimal(2), "RMB", None, True)
        return TpSourceResult(source, SourceOutcome.SUCCESS,
            SourceEvidence(source, order.mpn, order.mpn, SourceOutcome.SUCCESS, reference),
            (TpQuote(offer, Decimal(2)),)), "货多"
    transport = FakeNotificationTransport({"ops": (DeliveryOutcome.SENT,)*200, "owner": (DeliveryOutcome.SENT,)*20})
    worker = V12NotificationWorker(outbox, transport, scope="mail")
    clock, timer = [NOW], [0.0]
    service = MailResearchService(store=store, inbox_factory=Inbox, source_reader=read,
        fx_provider=None, catalog=InquiryCatalog(), outbox=outbox, worker=worker,
        clock=lambda: clock[0], timer=lambda: timer[0])
    worker._review_current = service.review_mail
    return service, inbox, transport, calls, clock, timer


def receive(service, inbox, count=1):
    service.poll_once()  # establishes baseline, ignores historic100
    inbox.messages = [(101+i, ResearchMail("MPN", NOW.isoformat(), f"<mail-{i}>")) for i in range(count)]
    inbox.latest = 100+count
    service.poll_once()


def test_baseline_restart_uid_epoch_distinct_requests_and_exact_outbox(tmp_path):
    service, inbox, smtp, calls, _clock, _ = scene(tmp_path)
    inbox.messages = [(1, ResearchMail("OLD", None, None))]
    receive(service, inbox, 2)
    assert service.run_one() and service.run_one()
    assert len(calls) == 12
    service.worker.run_due(now=NOW)
    assert len(smtp.calls) == 2  # same model, different UID is independent
    service.store.migrate()  # restart; old inbox flags irrelevant
    service.poll_once()
    assert not service.run_one()
    assert service.worker.run_due(now=NOW) == 0
    inbox.validity = 2
    inbox.latest = 900
    service.poll_once()
    assert not service.run_one() and len(smtp.calls) == 2
    with service.store.connect() as db:
        reports = db.execute("SELECT text_body FROM workflow_v12_notification_commands WHERE command_id LIKE 'mail-research:%'").fetchall()
    for (text,) in reports:
        assert all(name in text for name in ("IC.net", "Findchips", "华强", "立创", "正能量", "INSO"))
        assert "TP" not in text and "目标价" not in text and "订单总价：" not in text
        assert "数量：未匹配" in text


def test_latest_exact_order_unique_ties_and_conflicts():
    catalog = InquiryCatalog()
    old = DetailedOrder("MPN", "BRAND", 100, "CUSTOMER", "2026-10-01")
    recent = replace(old, rfq_date="2026-10-30", quantity=200)
    catalog.observe("one", (("old", old, NOW-timedelta(days=2)), ("new", recent, NOW)))
    assert catalog.match("mpn") == recent
    assert catalog.match("MPN-SIMILAR") is None
    catalog.observe("two", (("same-date-other-order", recent, NOW),))
    assert catalog.match("MPN") is None
    catalog.observe("two", (("unknown-conflict", recent, None),))
    assert catalog.match("MPN") is None


def test_matching_quantity_reference_total_and_missing_brand(tmp_path):
    service, inbox, smtp, calls, *_ = scene(tmp_path)
    service.catalog.observe("verified", (("one", DetailedOrder("MPN", None, 200, "CUSTOMER", "2026-09-01"), NOW),))
    receive(service, inbox)
    service.run_one()
    service.worker.run_due(now=NOW)
    with service.store.connect() as db:
        text = db.execute("SELECT text_body FROM workflow_v12_notification_commands WHERE command_id LIKE 'mail-research:%'").fetchone()[0]
    assert "400 RMB" in text and "非正式报价" in text
    assert "品牌：None" not in text and len(smtp.calls) == 1
    assert all(quantity == 200 for _, _, quantity in calls)


def test_bounded_queue_does_not_advance_cursor_past_unaccepted_mail(tmp_path):
    service, inbox, *_ = scene(tmp_path, capacity=2)
    receive(service, inbox, 5)
    assert service.store.cursor(ACCOUNT)[1] == 100
    service.run_one(); service.run_one()
    service.poll_once()
    with service.store.connect() as db:
        assert db.execute("SELECT count(*) FROM workflow_mail_research").fetchone()[0] == 2
    service.worker.run_due(now=NOW)  # Only terminal SMTP results free active queue capacity.
    service.poll_once()
    with service.store.connect() as db:
        assert db.execute("SELECT count(*) FROM workflow_mail_research WHERE state='PENDING'").fetchone()[0] == 2
        assert db.execute("SELECT count(*) FROM workflow_mail_research").fetchone()[0] == 4


def test_polling_continues_while_research_blocked_and_business_stopped(tmp_path):
    service, inbox, _smtp, *_ = scene(tmp_path)
    receive(service, inbox)
    entered, release = threading.Event(), threading.Event()
    read = service.source_reader
    def slow(*args):
        entered.set()
        assert release.wait(3)
        return read(*args)
    service.source_reader = slow
    worker = threading.Thread(target=service.run_one)
    worker.start()
    assert entered.wait(2)
    for tick in range(1, 5):
        service.timer = lambda tick=tick: tick*120
        service.tick()
    assert inbox.checks == 6 and worker.is_alive()
    release.set(); worker.join(3)
    assert not worker.is_alive()
    service.start(); service.close()
    assert all(not thread.is_alive() for thread in service.threads)


def test_crash_after_result_before_enqueue_recovers_and_unknown_never_retries(tmp_path):
    service, inbox, smtp, *_ = scene(tmp_path)
    receive(service, inbox)
    service.run_one()
    claimed = service.outbox.claim_due_notifications(now=NOW, scope="mail")
    assert len(claimed) == 1
    service.outbox.recover_abandoned_notification_attempts(at=NOW, scope="business")
    service.outbox.record_notification_result(command_id=claimed[0].command_id, recipient_id="ops",
        outcome=DeliveryOutcome.UNKNOWN, at=NOW)
    service.store.migrate()
    service.poll_once()
    assert service.worker.run_due(now=NOW) == 0 and not smtp.calls


def test_transient_imap_errors_zero_alerts_and_confirmed_auth_once(tmp_path):
    from src.order_mail.research_requests import ImapAuthenticationRequired
    service, _, smtp, *_ = scene(tmp_path)
    class Broken:
        def __exit__(self, *_):
            pass
        def __enter__(self):
            raise TimeoutError("synthetic")
    service.inbox_factory = Broken
    for _ in range(5):
        service.poll_once(); service.worker.run_due(now=NOW)
    assert smtp.calls == []
    class Auth:
        def __exit__(self, *_):
            pass
        def __enter__(self):
            raise ImapAuthenticationRequired()
    service.inbox_factory = Auth
    for _ in range(5):
        service.poll_once(); service.worker.run_due(now=NOW)
    assert len(smtp.calls) == 1 and smtp.calls[0][1] == "owner"


def test_partial_source_failure_keeps_other_reports_no_fabrication(tmp_path):
    service, inbox, smtp, *_ = scene(tmp_path)
    read = service.source_reader
    def partial(key, source, *args):
        if source is PRICE_SOURCES[0]:
            raise TimeoutError()
        return read(key, source, *args)
    service.source_reader = partial
    receive(service, inbox)
    service.run_one(); service.worker.run_due(now=NOW)
    assert len(smtp.calls) == 1
    with service.store.connect() as db:
        report = json.loads(db.execute("SELECT report FROM workflow_mail_research").fetchone()[0])
    assert "IC.net：未取得有效报价" in report["text"]


def test_all_unavailable_fails_bounded_without_empty_success_mail(tmp_path):
    service, inbox, smtp, _, clock, _ = scene(tmp_path)
    def broken(*args):
        raise TimeoutError()
    service.source_reader = broken
    receive(service, inbox)
    for _ in range(4):
        service.run_one(); service.worker.run_due(now=clock[0])
        clock[0] += timedelta(seconds=120)
    with service.store.connect() as db:
        row = db.execute("SELECT state,attempts FROM workflow_mail_research").fetchone()
    assert tuple(row) == ("FAILED", 3) and not smtp.calls


def test_main_park_cannot_close_unmarked_owner_or_mail_page():
    from src.launcher.browser_bootstrap import park_shared_cdp
    from tests.launcher.test_sales_tab_isolation import Page
    human, mail, blank = Page("https://synthetic.invalid/"), Page("https://synthetic.invalid/"), Page("about:blank")
    context = SimpleNamespace(pages=[human, mail, blank])
    park_shared_cdp(SimpleNamespace(contexts=[context], is_connected=lambda: True))
    assert not human.closed and not mail.closed and not blank.closed


@pytest.mark.parametrize("closed", [False, True])
@pytest.mark.parametrize("open_status", ["未发", "发给采购", "采购已报价"])
def test_important_mail_actual_backend_async_six_sources_and_closed_suppression(tmp_path, closed, open_status):
    from src.research import ResearchResult, ResearchStatus
    from src.sheets import WorksheetRow
    from src.workflow.v12_contracts import NotificationKind
    from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
    from tests.workflow.test_rfq016_regressions import production_scene
    from tests.workflow.test_v12_flow import NOW as AT
    from tests.workflow.test_v12_flow import SHEET
    from tests.workflow.test_v12_smtp_transport import (
        FakeCredentials,
        ScriptedSMTP,
        login,
    )
    backend, flow, queue, ledger, reader, record, iid = production_scene(tmp_path)
    service, _, _, calls, clock, _ = scene(tmp_path, outbox=ledger)
    clock[0] = AT
    backend._mail_research_service = service
    from src.workflow.v12_contracts import NotificationRecipient
    flow._recipients = (NotificationRecipient("owner", "linan229@qq.com"), NotificationRecipient("ops", "shawn@inso-hk.com"))
    flow._enqueue_notification(iid, NotificationKind.IMPORTANT_ORDER,
        ResearchResult(iid, ResearchStatus.SUCCESS), AT, tier="A")
    smtp = ScriptedSMTP()
    transport = QQSMTPTransport(config=QQSMTPConfig(sender_address="sender@example.invalid"),
        credentials=FakeCredentials(login()), smtp_factory=lambda *a, **k: smtp, clock=lambda: AT)
    worker = V12NotificationWorker(ledger, transport, review_current=backend._review_current_mail,
        prepare_content=backend._prepare_business_mail, scope="business")
    with service.store.connect() as db:
        before = tuple(db.execute("SELECT * FROM workflow_items").fetchall())
    assert worker.run_due(now=AT) == 0 and not calls  # Only queues; no source read on purchase/send path.
    assert service.run_one() and len(calls) == 6
    reader.row = WorksheetRow(record.row_position, {**reader.row.cells, "A": open_status})
    backend._source_projection.observe(SHEET, (reader.row,), queue.all_items(), at=AT)
    if closed:
        reader.row = WorksheetRow(record.row_position, {**reader.row.cells, "A": "已报价给客户"})
        backend._source_projection.observe(SHEET, (reader.row,), queue.all_items(), at=AT)
    worker.run_due(now=AT)
    assert smtp.send_attempts == (0 if closed else 2)
    if not closed:
        html = smtp.message.get_body(preferencelist=("html",)).get_content()
        assert all(name in html for name in ("IC.net", "Findchips", "华强", "立创", "正能量", "INSO"))
        assert "高于 TP" not in html and "低于 TP" not in html
    with service.store.connect() as db:
        assert tuple(db.execute("SELECT * FROM workflow_items").fetchall()) == before
    backend.shutdown()


def test_mail_report_through_original_smtp_adapter_only_shawn_once_after_restart(tmp_path):
    from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
    from tests.workflow.test_v12_smtp_transport import (
        FakeCredentials,
        ScriptedSMTP,
        login,
    )
    service, inbox, _, _, clock, _ = scene(tmp_path)
    smtp = ScriptedSMTP()
    worker = V12NotificationWorker(service.outbox, QQSMTPTransport(
        config=QQSMTPConfig(sender_address="sender@example.invalid"), credentials=FakeCredentials(login()),
        smtp_factory=lambda *a, **k: smtp, clock=lambda: clock[0]), scope="mail", review_current=service.review_mail)
    receive(service, inbox)
    service.run_one()
    worker.run_due(now=NOW)
    assert smtp.send_attempts == 1
    assert str(smtp.message["To"]) == "shawn@inso-hk.com" and smtp.message["Cc"] is None
    service.store.migrate(); service.poll_once()
    worker.run_due(now=NOW)
    assert smtp.send_attempts == 1


def test_720_simulated_polls_no_active_queue_growth_or_cross_task_state(tmp_path):
    service, inbox, _smtp, calls, clock, timer = scene(tmp_path, capacity=4)
    service.tick()
    for tick in range(1, 721):
        timer[0] = tick*120
        clock[0] = NOW+timedelta(seconds=timer[0])
        inbox.latest = 100+tick
        inbox.messages = [(100+tick, ResearchMail("MPN", None, str(tick)))]
        service.tick()
        assert service.run_one()
        service.worker.run_due(now=clock[0])
        with service.store.connect() as db:
            assert db.execute("SELECT count(*) FROM workflow_mail_research WHERE state IN ('PENDING','RUNNING')").fetchone()[0] == 0
    assert len(calls) == 720*6 and inbox.checks == 721
    assert len({key for key, _, _ in calls}) == 720
    assert not service.threads  # No per-task worker/thread creation.


@pytest.mark.parametrize("completed", [False, True])
def test_follow_up_original_clock_and_backend_to_actual_smtp(tmp_path, completed):
    from src.sheets import WorksheetRow
    from src.workflow.purchase_follow_up import PurchaseFollowUp
    from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
    from src.workflow.v13_follow_up_store import V13PurchaseFollowUpStore
    from tests.workflow.test_rfq016_regressions import production_scene
    from tests.workflow.test_v12_flow import NOW as START
    from tests.workflow.test_v12_flow import SHEET
    from tests.workflow.test_v12_smtp_transport import (
        FakeCredentials,
        ScriptedSMTP,
        login,
    )
    backend, _, queue, ledger, reader, record, iid = production_scene(tmp_path)
    now = START+timedelta(days=3, hours=6)  # Tuesday15:00 Shanghai; intake remains within7days.
    reader.row = WorksheetRow(record.row_position, {**reader.row.cells, "A": "发给采购"})
    backend._source_projection.observe(SHEET, (reader.row,), queue.all_items(), at=now)
    episodes = V13PurchaseFollowUpStore(ledger.database_path); episodes.migrate()
    episodes.record_confirmed(iid, confirmed_at=now-timedelta(hours=6))
    follow = PurchaseFollowUp(reader=reader, workflow_store=queue, v12_store=ledger, clock=lambda: now, episodes=episodes)
    assert follow.run(SHEET) == 1
    service, _, _, calls, clock, _ = scene(tmp_path, outbox=ledger)
    clock[0] = now
    backend._mail_research_service = service
    smtp = ScriptedSMTP()
    worker = V12NotificationWorker(ledger, QQSMTPTransport(config=QQSMTPConfig(sender_address="sender@example.invalid"),
        credentials=FakeCredentials(login()), smtp_factory=lambda *a, **k: smtp, clock=lambda: now), scope="business",
        review_current=backend._review_current_mail, prepare_content=backend._prepare_business_mail)
    assert worker.run_due(now=now) == 0 and calls == []
    assert service.run_one() and len(calls) == 6
    if completed:
        reader.row = WorksheetRow(record.row_position, {**reader.row.cells, "A": "已报价给客户"})
        backend._source_projection.observe(SHEET, (reader.row,), queue.all_items(), at=now)
    worker.run_due(now=now)
    assert smtp.send_attempts == (0 if completed else 2)
    if not completed:
        text = smtp.message.get_body(preferencelist=("plain",)).get_content()
        assert "3个工作小时" in text and "发给采购时间" in text and "正能量" in text
    backend.shutdown()


def test_resource_uncertainty_persists_restart_is_local_and_notifies_owner_once(tmp_path):
    from src.research.cdp_pages import PageTargetCleanupError
    service, inbox, smtp, _calls, *_ = scene(tmp_path)
    receive(service, inbox)
    def uncertain(*_):
        raise PageTargetCleanupError(())
    service.source_reader = uncertain
    assert service.run_one()
    service.worker.run_due(now=NOW)
    assert len(smtp.calls) == 1 and smtp.calls[0][1] == "owner"
    assert service.store.resource_blocked() and not service.run_one()
    restarted = MailResearchService(store=service.store, inbox_factory=service.inbox_factory,
        source_reader=lambda *_: pytest.fail("no new target after unresolved resource uncertainty"), fx_provider=None,
        catalog=service.catalog, outbox=service.outbox, worker=service.worker, clock=lambda: NOW)
    restarted.poll_once()
    assert not restarted.run_one()
    service.worker.run_due(now=NOW)
    assert len(smtp.calls) == 1


def test_canonical_tp_result_cache_is_bounded_fresh_and_cross_spreadsheet_safe(tmp_path):
    from src.research.detailed import TpFx, finish_tp
    service, _, _, _, *_ = scene(tmp_path)
    order = DetailedOrder("MPN", "BRAND", 10, "CUSTOMER", "2026-10-01", "2026", 2, spreadsheet="one")
    results = tuple(service.source_reader("synthetic", source, order, NOW, TpFx(None, NOW))[0] for source in PRICE_SOURCES)
    result = finish_tp(order, SimpleNamespace(stock_label="货多"), results, target_rmb=Decimal(10), fx=TpFx(None, NOW))
    service.remember_report(order, result, NOW)
    assert "TP" not in service.cached_report(order, NOW)["text"]
    assert service.cached_report(replace(order, spreadsheet="two"), NOW) is None
    assert service.cached_report(order, NOW+timedelta(minutes=16)) is None
    for index in range(100):
        service.remember_report(replace(order, row=index), result, NOW)
    assert len(service._report_cache) == 64



def test_same_unresolved_report_delivery_incident_alerts_owner_once(tmp_path):
    service, inbox, smtp, *_ = scene(tmp_path)
    smtp._outcomes["ops"].clear()
    smtp._outcomes["ops"].extend([DeliveryOutcome.UNKNOWN, DeliveryOutcome.UNKNOWN])
    receive(service, inbox, 2)
    for _ in range(2):
        service.run_one(); service.worker.run_due(now=NOW)
        service.audit_delivery(); service.worker.run_due(now=NOW)
    assert sum(recipient == "owner" for _, recipient in smtp.calls) == 1
    assert sum(recipient == "ops" for _, recipient in smtp.calls) == 2



def test_all_market_sources_unavailable_does_not_erase_legal_business_notice(tmp_path):
    from src.workflow.v12_contracts import (
        NotificationCommand,
        NotificationKind,
        NotificationRecipient,
    )
    service, _, _, _, clock, _ = scene(tmp_path)
    command = NotificationCommand("important:synthetic", None, NotificationKind.IMPORTANT_ORDER,
        (NotificationRecipient("owner", "linan229@qq.com"),), "Important", "Original verified business event", None, NOW)
    service.store.request_business(command, DetailedOrder("MPN", quantity=10), NOW)
    def unavailable(*_):
        raise TimeoutError()
    service.source_reader = unavailable
    for _ in range(3):
        service.run_one()
        clock[0] += timedelta(seconds=120)
    job = service.store.get(command.command_id)
    assert job["state"] == "READY"
    report = json.loads(job["report"])
    assert "详细调研暂未完成" in report["text"] and report["text"].count("未取得有效报价") >= 6
    assert "预计订单总价" not in report["text"]


def test_delivery_terminal_state_is_not_rescanned_as_an_active_request(tmp_path):
    service, inbox, smtp, *_ = scene(tmp_path)
    receive(service, inbox)
    service.run_one(); service.worker.run_due(now=NOW)
    service.audit_delivery()
    with service.store.connect() as db:
        assert db.execute("SELECT state FROM workflow_mail_research WHERE origin='imap'").fetchone()[0] == "DELIVERY_SENT"
        assert service.store._active_count(db) == 0
    service.store.migrate(); service.poll_once(); service.worker.run_due(now=NOW)
    assert len(smtp.calls) == 1



def test_actual_imap_temporary_login_rejection_never_reaches_smtp(tmp_path):
    import imaplib

    from src.order_mail.research_requests import ACCOUNT, ResearchInbox
    from tests.workflow.test_rfq016_regressions import real_fake_smtp
    service, *_ = scene(tmp_path)
    class Busy:
        def login(self, *_):
            raise imaplib.IMAP4.error("[UNAVAILABLE] temporary server maintenance")
        def logout(self):
            pass
    service.inbox_factory = lambda: ResearchInbox(credentials=lambda _: SimpleNamespace(username=ACCOUNT, password="synthetic"), factory=lambda *a, **k: Busy())
    worker, smtp = real_fake_smtp(service.outbox, now=NOW, review_current=service.review_mail)
    for _ in range(5):
        service.poll_once(); worker.run_due(now=NOW)
    assert smtp.send_attempts == 0


def test_receiver_loop_survives_local_queue_or_alert_exception(tmp_path):
    service, *_ = scene(tmp_path)
    def broken():
        raise RuntimeError("synthetic local ledger unavailable")
    service.tick = broken
    stopped = [False]
    service.stop_event = SimpleNamespace(is_set=lambda: stopped[0], wait=lambda _: stopped.__setitem__(0, True))
    service._receive()
    assert stopped[0] and service.health == "WAITING_RECOVERY"



def test_unmatched_report_keeps_canonically_resolved_source_brand(tmp_path):
    from src.research.detailed import TpFx
    from src.research.icnet import IcNetResult
    from src.research.service import ResearchService
    from src.research.source_contracts import PriceCandidate, SourceResult
    service, inbox, *_ = scene(tmp_path)
    evidence = SourceEvidence(PRICE_SOURCES[0], "MPN", "MPN", SourceOutcome.SUCCESS, NOW)
    candidate = PriceCandidate(PRICE_SOURCES[0], "MPN", Decimal(2), "RMB", Decimal(2), NOW)
    native = IcNetResult(SourceResult(PRICE_SOURCES[0], SourceOutcome.SUCCESS, evidence, candidate),
                        resolved_brand="VERIFIED-BRAND", stock_label="货多")
    canonical = ResearchService(icnet=SimpleNamespace(search=lambda *_: native), findchips=None,
        hqew=None, lcsc=None, bom_ai=None, inso=None, output=None)
    original_read = service.source_reader
    def read(key, source, order, reference, fx):
        return canonical.read_detailed_source(source, order, now=reference, fx=fx) if source is PRICE_SOURCES[0] else original_read(key, source, order, reference, fx)
    service.source_reader = read
    receive(service, inbox)
    service.run_one()
    with service.store.connect() as db:
        report = json.loads(db.execute("SELECT report FROM workflow_mail_research WHERE origin='imap'").fetchone()[0])
    assert "品牌：VERIFIED-BRAND" in report["text"]
    assert "询价数量：未匹配" in report["text"] and "订单总价：" not in report["text"]
    assert canonical.read_detailed_source(PRICE_SOURCES[0], DetailedOrder("MPN"), now=NOW, fx=TpFx(None, NOW))
