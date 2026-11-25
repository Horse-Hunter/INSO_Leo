"""Real Backend + original queue + fake SMTP; no production or sockets."""
from datetime import timedelta
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState
from src.launcher.backend import ProductionBackend
from src.launcher.inso_session import InsoAuthenticationError
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v12_notifications import V12NotificationWorker
from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
from tests.workflow.test_v12_notifications import NOW, prepared_store
from tests.workflow.test_v12_smtp_transport import FakeCredentials, ScriptedSMTP, login


def harness(tmp_path, monkeypatch, *, smtp=None):
    backend = ProductionBackend(root=tmp_path)
    backend._v12_store = prepared_store(tmp_path)
    from src.workflow.v13_integration import V13HoldStore
    V13HoldStore(backend._v12_store.database_path).migrate()
    backend._v13_ledger_ready = True
    backend._run_id = "synthetic-run"
    backend._state = RunState.RUNNING
    monkeypatch.setattr("src.launcher.backend.utc_now", lambda: NOW)
    server = smtp or ScriptedSMTP()
    transport = QQSMTPTransport(config=QQSMTPConfig(sender_address="sender@example.invalid"),
        credentials=FakeCredentials(login()), smtp_factory=lambda *a, **kw: server, clock=lambda: NOW)
    worker = V12NotificationWorker(backend._v12_store, transport,
                                  review_current=backend._review_current_mail, scope="business")
    backend._v12_composition = SimpleNamespace(coordinator=SimpleNamespace(run_notifications=lambda **kw: 0))
    return backend, worker, server


def test_actual_safety_stop_without_any_current_order_notifies_owner_once(tmp_path, monkeypatch):
    backend, worker, smtp = harness(tmp_path, monkeypatch)
    backend._runtime_error(V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED"))
    assert worker.run_due(now=NOW) == 1
    assert smtp.send_attempts == 1
    assert smtp.message["To"] == "linan229@qq.com"
    text = smtp.message.get_body(preferencelist=("plain",)).get_content()
    assert "安全暂停" in text and "不能据此判断Google整体不可用" in text
    assert "尚不能确认" in text
    backend._runtime_error(V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED"))
    assert worker.run_due(now=NOW) == 0 and smtp.send_attempts == 1


@pytest.mark.parametrize("change", ["recovered", "owner_stop", "different_run", "reason_changed", "closed"])
def test_obsolete_or_recovered_stop_never_sends(tmp_path, monkeypatch, change):
    backend, worker, smtp = harness(tmp_path, monkeypatch)
    backend._runtime_error(V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED"))
    if change == "recovered": backend._state = RunState.RUNNING; backend._stop.clear()
    elif change == "owner_stop": backend._state = RunState.STOPPED
    elif change == "different_run": backend._run_id = "next-run"
    elif change == "reason_changed": backend._runtime_stop_reason = "OTHER"
    else: backend._closed = True
    worker.run_due(now=NOW)
    assert smtp.send_attempts == 0


def test_temporary_read_and_normal_stop_do_not_create_safety_notice(tmp_path, monkeypatch):
    backend, worker, smtp = harness(tmp_path, monkeypatch)
    backend._notify_runtime_fault("temporary", "GOOGLE_READ_RETRY_EXHAUSTED", at=NOW)
    backend._stop.set(); backend._state = RunState.STOPPED
    backend._notify_runtime_fault("normal", "GOOGLE_TAB_IDENTITY_UNCONFIRMED", at=NOW)
    worker.run_due(now=NOW)
    assert smtp.send_attempts == 0


def test_restart_same_unresolved_incident_keeps_sent_protection(tmp_path, monkeypatch):
    backend, worker, smtp = harness(tmp_path, monkeypatch)
    backend._runtime_error(V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED"))
    worker.run_due(now=NOW)
    backend._run_id = "restarted"
    backend._runtime_error(V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED"))
    worker.run_due(now=NOW+timedelta(seconds=1))
    assert smtp.send_attempts == 1


def test_unknown_smtp_result_is_never_retried_after_restart(tmp_path, monkeypatch):
    backend, worker, smtp = harness(tmp_path, monkeypatch,
        smtp=ScriptedSMTP(send_error=TimeoutError("synthetic send accepted or lost")))
    backend._runtime_error(V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED"))
    worker.run_due(now=NOW)
    assert smtp.send_attempts == 1
    backend._run_id = "restarted"
    backend._runtime_error(V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED"))
    worker.run_due(now=NOW+timedelta(seconds=5))
    assert smtp.send_attempts == 1


def test_original_mail_thread_sends_after_poller_stop_before_evidence_enqueue(tmp_path, monkeypatch):
    import json
    import threading
    import time

    from src.launcher import backend as launcher
    from src.launcher.browser_bootstrap import BrowserHandle
    from tests.launcher.test_backend import _SheetsService, _write_runtime_configs

    production, research, rows = _write_runtime_configs(tmp_path)
    cfg = json.loads(production.read_text(encoding="utf-8"))
    cfg.update(v16_enabled=True, v13_enabled=True,
               quotation_input={"input_row": 1, "first_column": 1, "gid": "0"})
    production.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setattr(launcher, "build_google_web_service", lambda *a, **kw: _SheetsService(rows, threading.Event()))
    monkeypatch.setattr(launcher, "assess_readiness", lambda *a, **kw: SimpleNamespace(ready=True, missing_site_ids=()))
    backend = ProductionBackend(config_path=research, production_config_path=production,
        cdp_probe=lambda _: True, browser_acquirer=lambda *a, **kw: BrowserHandle(owned=False))
    smtp = ScriptedSMTP()
    transport = QQSMTPTransport(config=QQSMTPConfig(sender_address="sender@example.invalid"),
        credentials=FakeCredentials(login()), smtp_factory=lambda *a, **kw: smtp)
    real_send = transport.send_one
    owners = []
    def send(_self, command, recipient):
        owners.append(threading.current_thread().name)
        return real_send(command, recipient)
    monkeypatch.setattr(QQSMTPTransport, "send_one", send)
    bound = threading.Event()
    original_bind = V12NotificationWorker.bind_delivery_thread
    def bind(worker):
        original_bind(worker)
        bound.set()
    monkeypatch.setattr(V12NotificationWorker, "bind_delivery_thread", bind)
    def fail(*a, **kw):
        assert bound.wait(3)
        raise V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_TAB_IDENTITY_UNCONFIRMED")
    monkeypatch.setattr(backend, "_run_independent_poll", fail)
    original_notice = backend._notify_runtime_fault
    def delayed_notice(*a, **kw):
        assert backend._stop.is_set()
        time.sleep(0.1)  # Worker wakes before this incident exists in SQLite.
        original_notice(*a, **kw)
    monkeypatch.setattr(backend, "_notify_runtime_fault", delayed_notice)
    backend.start()
    backend._thread.join(8)
    try:
        assert not backend._thread.is_alive()
        assert smtp.send_attempts == 1
        assert owners == ["production-research-worker"]
        assert backend._stop.is_set()
    finally:
        backend.shutdown()


def test_owner_stop_cleanup_does_not_become_a_new_business_failure_notice(tmp_path, monkeypatch):
    backend, worker, smtp = harness(tmp_path, monkeypatch)
    backend.request_stop_after_cycle()
    backend._runtime_error(V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_OPERATION_NOT_CLOSED"))
    worker.run_due(now=NOW)
    assert smtp.send_attempts == 0


class _Clock:
    """One controllable clock for the backend, the evidence and the transport."""

    def __init__(self, now=NOW):
        self.now = now


class _Clock:
    """One controllable clock for the backend, the evidence and the transport."""

    def __init__(self, now=NOW):
        self.now = now


def _blocked_browser(tmp_path, monkeypatch):
    """A real backend on a controllable clock with the browser channel down."""
    clock = _Clock()
    backend, _worker, _smtp = harness(tmp_path, monkeypatch)
    monkeypatch.setattr("src.launcher.backend.utc_now", lambda: clock.now)
    server = ScriptedSMTP()
    transport = QQSMTPTransport(
        config=QQSMTPConfig(sender_address="sender@example.invalid"),
        credentials=FakeCredentials(login()),
        smtp_factory=lambda *a, **kw: server, clock=lambda: clock.now)
    worker = V12NotificationWorker(backend._v12_store, transport,
                                  review_current=backend._review_current_mail, scope="business")
    # Still blocked, as `_defer_website_poll` leaves it.
    backend._site_outages = {"Browser/CDP": 0.0}
    backend._site_fault_since = {"Browser/CDP": clock.now}
    return backend, worker, server, clock


def _block(backend, worker, clock, minutes, *, cycle):
    clock.now = NOW + timedelta(minutes=minutes)
    backend._cycle_id = cycle
    backend._notify_runtime_fault("browser-blocked", "BROWSER_WAITING_RECOVERY", at=clock.now)
    return worker.run_due(now=clock.now)


def test_a_browser_block_is_reported_once_the_outage_passes_45_minutes(tmp_path, monkeypatch):
    """Owner decision 2026-11-23: a stuck browser must say so, by duration.

    Amended after review: the trigger is the length of *this* outage, not a count
    of cycles. Inquiry and quotation report different cycle ids, so a count could
    be satisfied by two modules failing inside the same quarter hour.
    """

    backend, worker, smtp, clock = _blocked_browser(tmp_path, monkeypatch)

    for minutes in (0, 15, 30):
        _block(backend, worker, clock, minutes, cycle=f"cycle-{minutes}")
        assert smtp.send_attempts == 0, f"{minutes} minutes must stay silent"

    _block(backend, worker, clock, 46, cycle="cycle-46")
    assert smtp.send_attempts == 1

    assert smtp.message["To"] == "linan229@qq.com"
    text = smtp.message.get_body(preferencelist=("plain",)).get_content()
    assert "Browser/CDP" in text and "关闭该 Chrome 的窗口" in text

    # Once, not once per cycle: the incident keeps its SENT protection.
    _block(backend, worker, clock, 61, cycle="cycle-61")
    assert smtp.send_attempts == 1


def test_two_modules_failing_in_the_same_window_do_not_shorten_the_threshold(tmp_path, monkeypatch):
    """The review finding: inquiry and quotation cycles must not add up to 45 min."""

    backend, worker, smtp, clock = _blocked_browser(tmp_path, monkeypatch)

    # Three observations inside ten minutes, each a different cycle id -- the old
    # rule counted this as "3 completed cycles" and mailed immediately.
    for minutes, cycle in ((0, "inquiry-cycle-a"), (5, "quotation-cycle-b"),
                           (10, "inquiry-cycle-c")):
        _block(backend, worker, clock, minutes, cycle=cycle)
        assert smtp.send_attempts == 0

    _block(backend, worker, clock, 46, cycle="quotation-cycle-d")
    assert smtp.send_attempts == 1


def test_a_browser_block_with_no_order_at_all_still_reports(tmp_path, monkeypatch):
    """No pending purchase order: the block is still program-level news.

    The store holds no items here, so the old order-bound proof could never be
    built and the Owner heard nothing however long the browser stayed dead.
    """

    backend, worker, smtp, clock = _blocked_browser(tmp_path, monkeypatch)
    backend._store = SimpleNamespace(all_items=list, get_by_inquiry_id=lambda _id: None)

    _block(backend, worker, clock, 46, cycle="cycle-46")

    assert smtp.send_attempts == 1
    text = smtp.message.get_body(preferencelist=("plain",)).get_content()
    assert "Browser/CDP" in text


def test_a_recovered_browser_block_does_not_mail_after_the_fact(tmp_path, monkeypatch):
    backend, worker, smtp, clock = _blocked_browser(tmp_path, monkeypatch)

    clock.now = NOW + timedelta(minutes=46)
    backend._cycle_id = "cycle-46"
    backend._notify_runtime_fault("browser-blocked", "BROWSER_WAITING_RECOVERY", at=clock.now)
    backend._site_outages = {}  # reconnected before the worker ran
    worker.run_due(now=clock.now)

    assert smtp.send_attempts == 0


def test_a_restarted_outage_clock_earns_its_own_45_minutes(tmp_path, monkeypatch):
    """A new outage after recovery starts its own clock, whatever came before."""

    backend, worker, smtp, clock = _blocked_browser(tmp_path, monkeypatch)
    _block(backend, worker, clock, 46, cycle="cycle-46")
    assert smtp.send_attempts == 1

    # Recovered, then blocked again ten minutes before this observation.
    backend._site_outages = {"Browser/CDP": 0.0}
    backend._site_fault_since = {"Browser/CDP": NOW + timedelta(minutes=50)}
    _block(backend, worker, clock, 60, cycle="cycle-60")

    assert smtp.send_attempts == 1


def test_google_waits_keep_their_three_hour_rule(tmp_path, monkeypatch):
    """The change is scoped to Browser/CDP; Google still needs the 3-hour mark."""

    backend, worker, smtp = harness(tmp_path, monkeypatch)
    backend._site_outages = {"Google Sheets": 0.0}
    backend._site_fault_since = {"Google Sheets": NOW - timedelta(minutes=90)}

    for cycle in range(3):
        backend._cycle_id = f"cycle-{cycle}"
        backend._notify_runtime_fault("google-blocked", "GOOGLE_WAITING_RECOVERY", at=NOW)
        worker.run_due(now=NOW)

    assert smtp.send_attempts == 0


def _stopped_chain(code):
    """The shape production produced: a wrapper that hides the real reason."""
    try:
        raise InsoAuthenticationError(code)
    except InsoAuthenticationError:
        try:
            raise V12Fault(FaultScope.GLOBAL_STOP, "V13_INTERNAL_FAILURE") from None
        except V12Fault as fault:
            return fault


def test_an_unclassified_internal_stop_still_reaches_the_owner(tmp_path, monkeypatch):
    """2026-11-24 20:52: the stop was recorded, then silently suppressed.

    Its evidence carried actual_stop_reason="V12_INTERNAL_FAILURE", which cannot
    match the review's `[A-Z_]{1,64}` shape, so the notice died as
    RUNTIME_STOP_UNVERIFIED and the program stayed down for 25 hours unnoticed.
    """

    backend, worker, smtp = harness(tmp_path, monkeypatch)
    backend._runtime_error(V12Fault(FaultScope.GLOBAL_STOP, "V13_INTERNAL_FAILURE"))

    assert worker.run_due(now=NOW) == 1
    assert smtp.send_attempts == 1
    text = smtp.message.get_body(preferencelist=("plain",)).get_content()
    assert "INTERNAL_FAILURE_UNCLASSIFIED" in text


def test_the_stop_mail_names_the_real_reason_when_the_wrapper_had_none(tmp_path, monkeypatch):
    """The wrapper code has digits; the underlying reason does not, so use it."""

    backend, worker, smtp = harness(tmp_path, monkeypatch)
    backend._runtime_error(_stopped_chain("AUTHENTICATED_SHELL_UNAVAILABLE"))

    assert worker.run_due(now=NOW) == 1
    text = smtp.message.get_body(preferencelist=("plain",)).get_content()
    assert "AUTHENTICATED_SHELL_UNAVAILABLE" in text
