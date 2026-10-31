"""Owner-authorized subject-only policy; offline activation/backlog guards."""
import json
from types import SimpleNamespace

import pytest

from src.order_mail.research_requests import (
    ACCOUNT,
    TRIGGER_POLICY,
    ResearchInbox,
    parse_research_header,
)
from tests.order_mail.test_research_requests import IMAP
from tests.workflow.test_mail_research import header, scene
from tests.workflow.test_v12_notifications import NOW


@pytest.mark.parametrize("sender", ["other@example.invalid", "sales2@inso-hk.com", "bad From"])
def test_owner_subject_policy_accepts_any_sender(sender):
    assert parse_research_header(header(sender=sender)).mpn == "STM32F103C8T6"


def test_native_receiver_no_fixed_false_block_for_legal_subject():
    with ResearchInbox(credentials=lambda _: SimpleNamespace(username=ACCOUNT, password="synthetic"), factory=lambda *a, **k: IMAP()) as inbox:
        upper, mails = inbox.read(100)
    assert upper == 101 and len(mails) == 1


def test_existing_blocked_cursor_gets_one_activation_baseline_not_history(tmp_path):
    service, inbox, smtp, calls, *_ = scene(tmp_path)
    # Prior version had a valid cursor100 but authentication blocked101..500.
    with service.store.connect() as db:
        db.execute("INSERT INTO workflow_mail_cursor VALUES (?,?,?)", (ACCOUNT, 1, 100))
    inbox.latest = 500
    from src.order_mail.research_requests import ResearchMail
    inbox.messages = [(101, ResearchMail("OLD", None, None))]
    service.poll_once()
    assert service.store.cursor(ACCOUNT) == (1, 500)
    assert not service.run_one() and calls == [] and smtp.calls == []
    service.store.migrate()
    inbox.latest = 501
    service.poll_once()  # restart must not rebase501 away
    assert service.store.cursor(ACCOUNT) == (1, 501)


@pytest.mark.parametrize("subject", ["调研", "调研 ", "Re: 调研 MPN", "调研 MPN EXTRA", "调研 https://invalid", "调研 MPN;echo", "调研 型号", "调研 "+"X"*129])
def test_invalid_subject_cannot_trigger(subject):
    assert parse_research_header(header(subject, "any@example.invalid")) is None


@pytest.mark.parametrize("unknown", [False, True])
def test_native_subject_pipeline_first_enable_restart_and_terminal_smtp(tmp_path, unknown):
    from src.workflow.v12_contracts import DeliveryOutcome
    from tests.workflow.test_rfq016_regressions import real_fake_smtp
    service, _, _, reads, *_ = scene(tmp_path)
    client = IMAP()
    latest = [500]
    client.response = lambda field: (field, [b"1" if field == "UIDVALIDITY" else str(latest[0]+1).encode()])
    client.uid = lambda *_: ("OK", [(f"{latest[0]} (UID {latest[0]})".encode(), header("调研 MPN", "any@example.invalid"))])
    service.inbox_factory = lambda: ResearchInbox(credentials=lambda _: SimpleNamespace(username=ACCOUNT, password="synthetic"), factory=lambda *a, **k: client)
    with service.store.connect() as db:
        db.execute("INSERT INTO workflow_mail_cursor VALUES (?,?,?)", (ACCOUNT, 1, 100))
    service.poll_once()
    assert not service.run_one() and reads == []  #101..500 are never fetched/replayed.
    latest[0] = 501
    service.poll_once(); service.poll_once()
    assert service.run_one() and len(reads) == 6 and not service.run_one()
    worker, smtp = real_fake_smtp(service.outbox, now=NOW, review_current=service.review_mail)
    worker._scope, worker._prepare_content = "mail", service.prepare_mail
    if unknown:
        smtp._send_error = TimeoutError("synthetic uncertain send")
    assert worker.run_due(now=NOW) == 1
    if not unknown:
        assert str(smtp.message["To"]) == "shawn@inso-hk.com" and smtp.message["Cc"] is None
        body = smtp.message.get_body(preferencelist=("plain",)).get_content()
        assert "仅市场单价" in body and "订单总价：" not in body
    with service.store.connect() as db:
        outcomes = [r[0] for r in db.execute("SELECT outcome FROM workflow_v12_notification_recipients")]
        assert outcomes == [DeliveryOutcome.UNKNOWN.value if unknown else DeliveryOutcome.SENT.value]
    service.store.migrate(); service.poll_once()
    assert worker.run_due(now=NOW) == 0 and smtp.send_attempts == 1
    latest[0] = 502
    service.poll_once()
    assert service.run_one() and len(reads) == 12  # Same MPN, different new UID.
    assert worker.run_due(now=NOW) == 1 and smtp.send_attempts == 2


def test_old_pending_and_ready_policy_cannot_block_or_replay_new_tasks(tmp_path):
    from src.order_mail.research_requests import ResearchMail
    service, inbox, smtp, reads, *_ = scene(tmp_path, capacity=1)
    with service.store.connect() as db:
        for state in ("PENDING", "BLOCKED", "READY"):
            db.execute("INSERT INTO workflow_mail_research (task_id,origin,payload,state,created_at) VALUES (?,'imap',?,?,?)",
                ("mail-research:legacy-"+state, json.dumps({"mpn":"OLD","sender_verified":True}), state, NOW.isoformat()))
        before = [tuple(r) for r in db.execute("SELECT * FROM workflow_mail_research")]
    service.poll_once()
    inbox.latest = 101
    inbox.messages = [(101, ResearchMail("MPN", None, "<new>", TRIGGER_POLICY))]
    service.poll_once()
    assert service.run_one() and len(reads) == 6
    service.worker.run_due(now=NOW)
    assert len(smtp.calls) == 1
    with service.store.connect() as db:
        assert [tuple(r) for r in db.execute("SELECT * FROM workflow_mail_research WHERE task_id LIKE 'mail-research:legacy-%'")] == before


@pytest.mark.parametrize("field,value", [("uid", 999), ("after_uid", 101), ("account", "other@example.invalid"), ("trigger_policy", "legacy"), ("mpn", "BAD MPN")])
def test_persisted_request_binding_is_rechecked_before_research_and_send(tmp_path, field, value):
    from tests.workflow.test_mail_research import receive
    service, inbox, smtp, reads, *_ = scene(tmp_path)
    receive(service, inbox)
    with service.store.connect() as db:
        row = db.execute("SELECT task_id,payload FROM workflow_mail_research").fetchone()
        payload = json.loads(row[1]); payload[field] = value
        db.execute("UPDATE workflow_mail_research SET payload=? WHERE task_id=?", (json.dumps(payload), row[0]))
    service.run_one(); service.worker.run_due(now=NOW)
    assert reads == [] and smtp.calls == []
