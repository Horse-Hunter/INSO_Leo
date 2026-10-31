"""CEO D/E/sender gates: synthetic threads, source records and TLS only."""
import threading
from datetime import timedelta
from types import SimpleNamespace

import pytest

from src.launcher.research_budget import ResearchBudget, ResearchDeferred
from src.order_mail.research_requests import ACCOUNT, ResearchInbox
from src.research.detailed import DetailedOrder
from src.workflow.mail_research import InquiryCatalog
from tests.order_mail.test_research_requests import IMAP
from tests.workflow.test_mail_research import receive, scene
from tests.workflow.test_v12_notifications import NOW


def test_local_or_previous_poll_cannot_prove_latest_when_main_stopped():
    catalog = InquiryCatalog()
    old = DetailedOrder("MPN", "BRAND", 999, "OLD_CUSTOMER", "2026-09-01")
    catalog.observe("one", (("old", old, NOW-timedelta(days=30)),))
    # External Google has a newer row; no current complete observation here.
    assert catalog.match("MPN", now=NOW) is None


def test_stopped_main_old_cache_report_has_no_customer_quantity_total(tmp_path):
    service, inbox, smtp, calls, *_ = scene(tmp_path)
    service.catalog.observe("old", (("old", DetailedOrder("MPN", "BRAND", 999, "OLD_CUSTOMER", "2026-09-01"), NOW-timedelta(days=30)),))
    receive(service, inbox)
    service.run_one(); service.worker.run_due(now=NOW)
    with service.store.connect() as db:
        text = db.execute("SELECT text_body FROM workflow_v12_notification_commands WHERE command_id LIKE 'mail-research:%'").fetchone()[0]
    assert "OLD_CUSTOMER" not in text and "999" not in text
    assert "订单总价：" not in text and len(smtp.calls) == 1
    assert all(quantity is None for _, _, quantity in calls)


@pytest.mark.parametrize("mode", ["slow", "hung"])
def test_background_first_cannot_hold_due_foreground_until_read_returns(mode):
    budget = ResearchBudget()
    entered, release, progressed = threading.Event(), threading.Event(), threading.Event()
    failures = []
    def background():
        try:
            with budget.background():
                entered.set()
                assert release.wait(3)
        except AssertionError as exc:
            failures.append(exc)
    def main():
        with budget.foreground():
            progressed.set()
    bg = threading.Thread(target=background)
    fg = threading.Thread(target=main)
    bg.start()
    assert entered.wait(1)
    fg.start()
    try:
        assert progressed.wait(.25), "due main exceeded250ms while background still blocked"
        assert bg.is_alive() and not release.is_set()
    finally:
        release.set(); bg.join(2); fg.join(2)
    assert not failures


@pytest.mark.parametrize("claims", [b"", b"Authentication-Results: mx.qq.com; dkim=pass header.d=inso-hk.com; dmarc=pass header.from=inso-hk.com\r\n", b"Received-SPF: pass\r\nReturn-Path: <sales2@inso-hk.com>\r\n"])
def test_forged_exact_from_and_self_asserted_auth_never_enter_research(claims):
    from tests.workflow.test_mail_research import header
    client = IMAP()
    client.uid = lambda *_: ("OK", [(b"101 (UID 101)", claims+header())])
    with ResearchInbox(credentials=lambda _: SimpleNamespace(username=ACCOUNT, password="synthetic"), factory=lambda *a, **k: client) as inbox:
        try:
            _, mails = inbox.read(100)
        except ValueError as exc:
            assert str(exc) == "SENDER_AUTH_UNVERIFIED"
        else:
            assert mails == (), "matching From is not sender authenticity"
    assert client.closed


def test_only_complete_post_request_live_sources_can_enrich_and_expire():
    catalog = InquiryCatalog()
    catalog.configure_sources(("sheetA", "sheetB"))
    old = DetailedOrder("MPN", quantity=10, customer="OLD", rfq_date="2026-09-01")
    new = DetailedOrder("MPN", quantity=20, customer="NEW", rfq_date="2026-09-25")
    catalog.observe("sheetA", (("old", old, NOW-timedelta(days=2)),), observed_at=NOW-timedelta(seconds=1))
    catalog.observe("sheetB", (), observed_at=NOW-timedelta(seconds=1))
    assert catalog.match("MPN", now=NOW, not_before=NOW) is None
    catalog.observe("sheetA", (("old", old, NOW-timedelta(days=2)),), observed_at=NOW)
    assert catalog.match("MPN", now=NOW, not_before=NOW) is None  # Missing fresh second sheet.
    catalog.observe("sheetB", (("new", new, NOW),), observed_at=NOW)
    assert catalog.match("MPN", now=NOW, not_before=NOW) == new
    assert catalog.match("MPN", now=NOW+timedelta(seconds=121)) is None
    catalog.invalidate("sheetA")  # Google fails; old success cannot qualify.
    assert catalog.match("MPN", now=NOW) is None
    catalog.observe("sheetA", (("conflict", old, NOW),), observed_at=NOW)
    assert catalog.match("MPN", now=NOW) is None  # Cross-sheet same newest timestamp.
    catalog.configure_sources(("sheetA", "sheetB"))  # Restart cannot revive freshness.
    assert catalog.match("MPN", now=NOW) is None


def test_restart_discards_even_recent_persisted_customer_progress(tmp_path):
    from dataclasses import asdict

    from src.workflow.mail_research import MailResearchService
    service, inbox, smtp, calls, *_ = scene(tmp_path)
    receive(service, inbox)
    with service.store.connect() as db:
        key = db.execute("SELECT task_id FROM workflow_mail_research").fetchone()[0]
    stale = DetailedOrder("MPN", "OLD_BRAND", 999, "OLD_CUSTOMER", "2026-09-01")
    service.store.checkpoint(key, {"order": asdict(stale), "reference_at": NOW.isoformat()})
    service.store.migrate()
    restarted = MailResearchService(store=service.store, inbox_factory=service.inbox_factory,
        source_reader=service.source_reader, fx_provider=None, catalog=InquiryCatalog(),
        outbox=service.outbox, worker=service.worker, clock=lambda: NOW)
    service.worker._review_current = restarted.review_mail
    service.worker._prepare_content = restarted.prepare_mail
    restarted.run_one(); service.worker.run_due(now=NOW)
    with service.store.connect() as db:
        text = db.execute("SELECT text_body FROM workflow_v12_notification_commands").fetchone()[0]
    assert "OLD_CUSTOMER" not in text and "999" not in text and "OLD_BRAND" not in text
    assert all(qty is None for _, _, qty in calls) and len(smtp.calls) == 1


def test_smtp_downgrades_enrichment_if_source_expires_after_ready(tmp_path):
    from tests.workflow.test_rfq016_regressions import real_fake_smtp
    service, inbox, _, _, clock, _ = scene(tmp_path)
    service.catalog.configure_sources(("sheet",))
    service.catalog.observe("sheet", (("order", DetailedOrder("MPN", "BRAND", 999, "OLD_CUSTOMER", "2026-09-01"), NOW),), observed_at=NOW)
    receive(service, inbox)
    service.run_one()
    clock[0] += timedelta(seconds=121)
    worker, smtp = real_fake_smtp(service.outbox, now=clock[0], review_current=service.review_mail)
    worker._prepare_content = service.prepare_mail
    assert worker.run_due(now=clock[0]) == 1
    text = smtp.message.get_body(preferencelist=("plain",)).get_content()
    assert "OLD_CUSTOMER" not in text and "999" not in text and "订单总价：" not in text
    assert "仅市场单价" in text


def test_live_source_observer_excludes_discovery_partial_and_failed_reads():
    from src.sheets import WorksheetIdentity
    from src.sheets.google_reader import GoogleSheetsReadError, GoogleSheetsRowReader
    from tests.sheets.test_google_reader import FakeSheetsService
    source = WorksheetIdentity("synthetic", "2026")
    service = FakeSheetsService({"values": [["未发", "", "CUSTOMER", "", "MPN", "BRAND", 10]]})
    service.get_discovery = service.values_resource.get
    service.values_resource.get_discovery = service.values_resource.get
    observed = []
    callback = lambda *args: observed.append(args)
    reader = GoogleSheetsRowReader(service, on_live_observation=callback)
    with reader.discovery_scope():
        reader.read_discovery_rows(source)
        assert observed == []
        reader.read_rows(source)
    assert len(observed) == 1 and observed[0][0] == source and observed[0][2].tzinfo is not None
    GoogleSheetsRowReader(service, first_row=5, on_live_observation=callback).read_rows(source)
    failing = GoogleSheetsRowReader(FakeSheetsService(failure=ValueError("synthetic")), on_live_observation=callback)
    with pytest.raises(GoogleSheetsReadError):
        failing.read_rows(source)
    assert len(observed) == 1


@pytest.mark.parametrize("legacy_state", ["PENDING", "READY"])
def test_legacy_unverified_requests_never_research_or_send(tmp_path, legacy_state):
    import json
    service, inbox, smtp, calls, *_ = scene(tmp_path)
    receive(service, inbox)
    if legacy_state == "READY":
        service.run_one()
    with service.store.connect() as db:
        payload = json.loads(db.execute("SELECT payload FROM workflow_mail_research").fetchone()[0])
        payload.pop("sender_verified")
        db.execute("UPDATE workflow_mail_research SET payload=?", (json.dumps(payload),))
    calls.clear()
    service.run_one(); service.worker.run_due(now=NOW)
    assert calls == [] and smtp.calls == []


def test_unverified_sender_retains_cursor_and_polls_without_alert(tmp_path):
    service, *_ = scene(tmp_path)
    client = IMAP()
    service.inbox_factory = lambda: ResearchInbox(credentials=lambda _: SimpleNamespace(username=ACCOUNT, password="synthetic"), factory=lambda *a, **k: client)
    service.poll_once()  # baseline101
    # New header exact From, still no provider-grounded proof.
    client.response = lambda field: (field, [b"1" if field == "UIDVALIDITY" else b"103"])
    from tests.workflow.test_mail_research import header
    client.uid = lambda *_: ("OK", [(b"102 (UID 102)", header())])
    for _ in range(3):
        service.poll_once(); service.worker.run_due(now=NOW)
    assert service.health == "SENDER_AUTH_UNVERIFIED" and service.store.cursor(ACCOUNT) == (1, 101)
    with service.store.connect() as db:
        assert db.execute("SELECT count(*) FROM workflow_mail_research").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM workflow_v12_notification_commands").fetchone()[0] == 0


@pytest.mark.parametrize("site", ["slow", "hung", "closed_before_retry"])
def test_native_owned_background_first_defers_checkpoint_and_never_closes_main(tmp_path, site):
    from time import monotonic

    from src.launcher.research_budget import foreground_resources
    from src.research.cdp_pages import PageResourceAdmission, new_background_page
    from src.research.detailed import TpFx
    from src.research.mail_session import DetailedReadSession
    from tests.research.test_cdp_pages import RacingTargets
    from tests.research.test_market_read import attach_scope_target
    service, inbox, smtp, _, *_ = scene(tmp_path)
    receive(service, inbox)
    protocol, admission = RacingTargets(), PageResourceAdmission()
    protocol._inso_page_admission = admission
    budget = ResearchBudget()
    entered, release, progressed = threading.Event(), threading.Event(), threading.Event()
    pages, errors, latencies = [], [], []
    def read(*_args, **_kwargs):
        page = attach_scope_target(protocol, new_background_page(protocol, protocol, timeout_ms=1234))
        pages.append(page)
        entered.set()
        assert release.wait(3)
        if site == "closed_before_retry":
            page.closed = True
        return SimpleNamespace(), None
    def source_reader(key, source, order, reference, fx):
        session = object.__new__(DetailedReadSession)
        session._thread, session._admission = threading.get_ident(), admission
        session._service = SimpleNamespace(read_detailed_source=read)
        with budget.background() as check:
            session.read_checkpoint = check
            return session.read_source(key, source, order, reference, TpFx(None, reference))
    service.source_reader = source_reader
    class Main:
        _background_research_budget = budget
        @foreground_resources
        def due(self):
            assert not pages[0].closed  # Main must never cancel another thread's target.
            progressed.set()
    def run_main():
        begin = monotonic()
        try:
            Main().due()
        except AssertionError as exc:
            errors.append(exc)
        latencies.append(monotonic()-begin)
    bg = threading.Thread(target=service.run_one)
    main = threading.Thread(target=run_main)
    bg.start()
    assert entered.wait(1)
    main.start()
    try:
        assert progressed.wait(.25), "original main due work exceeded250ms"
        assert bg.is_alive() and not release.is_set()
        with pytest.raises(ResearchDeferred, match="FOREGROUND_PRIORITY"), budget.background():
            pytest.fail("no overlapping/new background target")
        assert len(pages) == 1
    finally:
        release.set(); bg.join(2); main.join(2)
    assert not errors and max(latencies) < .25 and not bg.is_alive()
    assert len(pages) == 1 and pages[0].closed
    assert all(not page.is_closed() for page in protocol.pages if page not in pages)
    service.worker.run_due(now=NOW)
    with service.store.connect() as db:
        job = db.execute("SELECT state,attempts,progress FROM workflow_mail_research").fetchone()
    assert job[0] == "PENDING" and job[1] == 0 and "HQEW" not in job[2]
    assert smtp.calls == []


def test_google_updated_without_main_poll_degrades_then_fresh_complete_view_enriches(tmp_path):
    from src.order_mail.research_requests import ResearchMail
    service, inbox, smtp, calls, clock, _ = scene(tmp_path)
    service.catalog.configure_sources(("2026", "SHAHAB"))
    old = DetailedOrder("MPN", quantity=999, customer="OLD_CUSTOMER", rfq_date="2026-09-01")
    external_latest = DetailedOrder("MPN", quantity=20, customer="NEW_CUSTOMER", rfq_date="2026-09-25")
    # Main stopped: Google changed after the last poll, even though cache is only1s old.
    service.catalog.observe("2026", (("old", old, NOW-timedelta(days=2)),), observed_at=NOW-timedelta(seconds=1))
    service.catalog.observe("SHAHAB", (), observed_at=NOW-timedelta(seconds=1))
    receive(service, inbox)
    service.run_one(); service.worker.run_due(now=NOW)
    assert all(qty is None for _, _, qty in calls)
    # Next request: only positive live reads of ALL configured sheets restore enrichment.
    clock[0] += timedelta(seconds=1)
    inbox.latest = 102
    inbox.messages = [(102, ResearchMail("MPN", None, "<second>", sender_verified=True))]
    service.poll_once()
    service.catalog.observe("2026", (("old", old, NOW-timedelta(days=2)), ("new", external_latest, NOW)), observed_at=clock[0])
    service.catalog.observe("SHAHAB", (), observed_at=clock[0])
    service.run_one(); service.worker.run_due(now=clock[0])
    with service.store.connect() as db:
        texts = [row[0] for row in db.execute("SELECT text_body FROM workflow_v12_notification_commands")]
    assert len(smtp.calls) == 2 and all("OLD_CUSTOMER" not in text for text in texts)
    assert any("NEW_CUSTOMER" in text and "40 RMB" in text for text in texts)
    assert [qty for _, _, qty in calls[6:]] == [20]*6


def test_successful_imap_read_with_unverified_sender_breaks_old_auth_failure_streak(tmp_path):
    from src.order_mail.research_requests import ImapAuthenticationRequired
    service, _, smtp, *_ = scene(tmp_path)
    service.poll_once()  # establish baseline before a later mail arrives
    class Auth:
        def __enter__(self):
            raise ImapAuthenticationRequired()
        def __exit__(self, *_):
            pass
    service.inbox_factory = Auth
    service.poll_once(); service.poll_once()
    # Successful TLS/login/select/header FETCH proves the old login block recovered,
    # even though sender origin is unavailable and the instruction must not run.
    service.inbox_factory = lambda: ResearchInbox(credentials=lambda _: SimpleNamespace(username=ACCOUNT, password="synthetic"), factory=lambda *a, **k: IMAP())
    service.poll_once()
    assert service.health == "SENDER_AUTH_UNVERIFIED"
    service.inbox_factory = Auth
    service.poll_once(); service.worker.run_due(now=NOW)
    assert service._auth_failures == 1 and smtp.calls == []
