import threading

from src.launcher import sales_header
from src.launcher.backend import ProductionBackend


def test_mail_check_one_shot_serial_and_shutdown_waits(tmp_path, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    calls = []
    def check(**kwargs):
        calls.append(1)
        entered.set()
        release.wait(5)
        return "WAITING_OWNER", "synthetic sanitized report"
    monkeypatch.setattr(sales_header, "run_sales_header_check", check)
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
    def fail(**kwargs):
        raise ValueError("SENSITIVE secret provider body")
    monkeypatch.setattr(sales_header, "run_sales_header_check", fail)
    backend = ProductionBackend(root=tmp_path)
    backend.start_order_mail_check()
    backend.shutdown()
    assert "SENSITIVE" not in backend.get_order_mail_report()


def test_sales_worker_does_not_pause_parallel_inquiry(tmp_path, monkeypatch):
    from src.gui.contracts import RunState

    entered, release = threading.Event(), threading.Event()
    inquiry_release = threading.Event()
    def check(**kwargs):
        assert kwargs["sample_number"] == 2
        entered.set()
        assert release.wait(5)
        return "WAITING_OWNER", "safe"
    monkeypatch.setattr(sales_header, "run_sales_header_check", check)
    backend = ProductionBackend(root=tmp_path)
    backend._state = RunState.RUNNING
    inquiry = threading.Thread(target=lambda: inquiry_release.wait(5))
    inquiry.start()
    backend._thread = inquiry
    try:
        assert backend.start_order_mail_check(sample_number=2)
        assert entered.wait(2)
        assert backend._state is RunState.RUNNING and inquiry.is_alive()
        release.set()
        backend._order_mail_thread.join(2)
        assert not backend.order_mail_running()
        assert backend.get_order_mail_stage() == "WAITING_OWNER"
        assert backend._state is RunState.RUNNING and backend._thread is inquiry
        assert inquiry.is_alive() and not backend._stop.is_set()
    finally:
        release.set()
        inquiry_release.set()
        inquiry.join(2)
