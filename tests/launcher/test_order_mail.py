import threading

from src.launcher.backend import ProductionBackend
from src.order_mail import inspection


def test_mail_check_one_shot_serial_and_shutdown_waits(tmp_path, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    calls = []
    def check():
        calls.append(1)
        entered.set()
        release.wait(5)
        return inspection.InspectionReport("SUCCESS", "synthetic sanitized report")
    monkeypatch.setattr(inspection, "inspect_order_mail", check)
    backend = ProductionBackend(root=tmp_path)
    assert backend.start_order_mail_check()
    assert entered.wait(2)
    assert not backend.start_order_mail_check()
    assert backend.order_mail_running()
    release.set()
    backend.shutdown()
    assert not backend.order_mail_running()
    assert calls == [1] and backend.get_order_mail_report() == "synthetic sanitized report"
    assert not backend.start_order_mail_check()
    assert backend._thread is None and backend._store is None


def test_worker_error_is_sanitized(tmp_path, monkeypatch):
    def fail():
        raise ValueError("SENSITIVE secret provider body")
    monkeypatch.setattr(inspection, "inspect_order_mail", fail)
    backend = ProductionBackend(root=tmp_path)
    backend.start_order_mail_check()
    backend.shutdown()
    assert "SENSITIVE" not in backend.get_order_mail_report()
