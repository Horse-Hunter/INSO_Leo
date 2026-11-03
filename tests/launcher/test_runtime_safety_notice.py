"""Real Backend + original queue + fake SMTP; no production or sockets."""
from datetime import timedelta
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState
from src.launcher.backend import ProductionBackend
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
