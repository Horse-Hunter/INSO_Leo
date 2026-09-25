from __future__ import annotations

from datetime import UTC, datetime

from src.launcher.backend import ProductionBackend
from src.sheets import (
    IdentifyingSnapshot,
    PendingSheetRecord,
    SheetRecordIdentity,
    WorksheetIdentity,
)
from src.workflow import WorkflowStateStore, WorkflowWorker

NOW = datetime(2026, 9, 26, tzinfo=UTC)
CANARY = "SECRET_CANARY_71B2"


class RaisingResearch:
    def execute(self, _research_input):
        raise RuntimeError(f"external failure {CANARY}")


def test_exception_canary_never_reaches_sqlite_or_gui_remark(tmp_path):
    database = tmp_path / "workflow.sqlite3"
    store = WorkflowStateStore(database)
    worksheet = WorksheetIdentity("synthetic-sheet", "2026")
    identity = SheetRecordIdentity(
        worksheet,
        2,
        IdentifyingSnapshot("未发", "A", "MPN-1", "Brand", 4),
    )
    record = PendingSheetRecord(
        "未发", "A", "MPN-1", "Brand", 4, 2, identity
    )
    assert store.enqueue(record, now=NOW)
    WorkflowWorker(store, RaisingResearch()).process_due_one(now=NOW)

    item = store.all_items()[0]
    assert item.last_error == "RuntimeError"
    assert CANARY not in database.read_bytes().decode("latin1", errors="ignore")

    backend = ProductionBackend(
        root=tmp_path,
        config_path=tmp_path / "missing-research.json",
        production_config_path=tmp_path / "missing-production.json",
    )
    backend._store = store
    backend._inquiries = [item.inquiry_id]
    backend._refresh()
    gui_order = backend.get_current_run_results()[0]
    assert CANARY not in gui_order.remark
    assert gui_order.remark == "RuntimeError"

    store.record_brand_update(
        item.id,
        "FAILED",
        error=RuntimeError(f"brand updater {CANARY}"),
        now=NOW,
    )
    assert store.get(item.id).last_error == "BRAND_UPDATE_FAILED"
    assert CANARY not in database.read_bytes().decode("latin1", errors="ignore")
    backend.shutdown()
