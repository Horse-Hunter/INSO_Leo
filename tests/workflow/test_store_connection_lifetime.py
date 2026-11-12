"""Windows file-handle regression checks for existing workflow stores."""
from contextlib import nullcontext

from src.workflow.store import WorkflowStateStore
from src.workflow.v12_store import migrate_v12
from src.workflow.v13_integration import V13HoldStore


def test_workflow_store_closes_connection(tmp_path):
    path = tmp_path / "workflow.sqlite3"
    store = WorkflowStateStore(path)
    assert store.all_items() == ()
    moved = tmp_path / "renamed.sqlite3"
    path.rename(moved)
    assert moved.is_file()


def test_v13_hold_store_closes_connection(tmp_path):
    path = tmp_path / "workflow.sqlite3"
    WorkflowStateStore(path)
    migrate_v12(path, tmp_path / "backups", quiesce=nullcontext)
    store = V13HoldStore(path)
    store.migrate()
    assert store.active() == ()
    moved = tmp_path / "renamed.sqlite3"
    path.rename(moved)
    assert moved.is_file()
