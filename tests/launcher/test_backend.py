from decimal import Decimal
from threading import Event

from src.gui.contracts import RunState
from src.launcher.backend import ProductionBackend, _decimal


def test_duplicate_start_keeps_one_run_and_shutdown_joins_worker(tmp_path):
    backend = ProductionBackend(production_config_path=tmp_path / "missing.json")
    entered = Event()

    def controlled_run():
        entered.set()
        backend._stop.wait(2)

    backend._run = controlled_run
    backend.start()
    assert entered.wait(1)
    first = backend.run_id
    backend.start()
    assert backend.run_id == first
    assert backend.get_status().state is RunState.RUNNING
    backend.request_stop_after_cycle()
    assert backend.get_status().state is RunState.STOPPING_AFTER_CYCLE
    worker = backend._thread
    worker.join(timeout=2)
    assert worker is not None and not worker.is_alive()
    backend.shutdown()


def test_missing_runtime_fails_closed_to_manual_review(tmp_path):
    backend = ProductionBackend(
        production_config_path=tmp_path / "missing.json",
        config_path=tmp_path / "missing-research.json",
    )
    backend.start()
    backend._thread.join(timeout=2)
    assert backend.get_status().state is RunState.MANUAL_REVIEW
    assert backend.get_health().overall == "需要人工处理"
    assert "需要人工处理" in backend.get_logs()[-1].message
    backend.shutdown()


def test_session_tracks_executed_inquiry_ids_and_decimal_excel_display():
    backend = ProductionBackend()
    backend._seen("inq_seen")
    assert backend._inquiries == ["inq_seen"]
    assert _decimal("1586.74\n2000-Findchips") == Decimal("1586.74")
    assert _decimal("无结果") is None
