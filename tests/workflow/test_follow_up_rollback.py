"""Run preserved readers/startup against new synthetic DBs while mail is outstanding."""
import io
import json
import os
import sqlite3
import subprocess
import sys
import zipfile
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from src.launcher.purchase_completion import PurchaseCompletionActions
from src.sheets import WorksheetRow
from src.workflow.purchase_follow_up import PurchaseFollowUp
from src.workflow.v12_contracts import (
    BusinessState,
    DeliveryOutcome,
    EventType,
    NotificationKind,
    PurchaseOutcome,
    ReconciliationOutcome,
    ReconciliationResult,
    WorkflowEvent,
)
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v12_store import FakeSaveReconciler
from src.workflow.v13_follow_up_store import TABLE, V13PurchaseFollowUpStore
from tests.workflow.test_purchase_follow_up import local
from tests.workflow.test_v12_flow import (
    SHEET,
    FakeSheetsReader,
    ResearchBusinessFacts,
    _make_flow,
)

LEGACY_REFS = {
    "formal_v13": "03f4bf3328b0931b4bdc5dc05865b9f35322cf7e",
    "formal_v12": "d75a1fa1db5371b59363bd733538f7fd0fb245e6",
}


def confirmed_status_fixture(tmp_path):
    start = local("2026-10-09T17:00")
    flow, store, ledger, *_ = _make_flow(tmp_path,
        facts=ResearchBusinessFacts("货足", Decimal(10), Decimal(2)))
    sheet = FakeSheetsReader(tier="C")
    result = flow.poll_and_process(sheet, SHEET, now=start)[0]
    iid = result.inquiry_id
    ledger.begin_save_dispatch(iid, at=start, save_and_send=True)
    ledger.record_submit_click(iid, at=start)  # Synthetic receipt, no browser/dispatch.
    reconciler = FakeSaveReconciler(ReconciliationResult(
        ReconciliationOutcome.CONFIRMED_SAVED, start,
        saved_record_ref="rec_" + "a" * 32, candidate_count=1, authoritative=True,
        verified_fields=frozenset({"mpn", "submission_time", "new_record"})))
    assert ledger.reconcile_unknown_save(iid, reconciler, at=start) is PurchaseOutcome.SAVED
    ledger.set_business_state(iid, BusinessState.PURCHASE_RECORDED,
        WorkflowEvent("confirmed-synthetic-save", iid, EventType.PURCHASE_DATA_SAVED, start, "workflow"))
    episodes = V13PurchaseFollowUpStore(ledger.database_path)
    episodes.migrate()
    calls = []
    def write(worksheet, row):
        assert worksheet == SHEET and row == sheet.row.row_position
        calls.append(row)
        sheet.row = WorksheetRow(row, {**sheet.row.cells, "A": "发给采购"})
    sheet.write_purchase_status = write
    action = PurchaseCompletionActions(workflow_store=store, v12_store=ledger,
        reader=sheet, writer_factory=lambda: sheet, clock=lambda: start, follow_up_store=episodes)
    saved = replace(result, purchase_outcome=PurchaseOutcome.SAVED, business_state=BusinessState.PURCHASE_RECORDED)
    return store, ledger, episodes, sheet, action, saved, calls, start


@pytest.fixture(scope="session")
def legacy_sources(tmp_path_factory):
    root = Path(__file__).resolve().parents[2]
    result = {}
    for name, ref in LEGACY_REFS.items():
        snapshot = tmp_path_factory.mktemp(name)
        archive = subprocess.run(["git", "archive", "--format=zip", ref, "src"],
            cwd=root, capture_output=True, check=True).stdout
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            zipped.extractall(snapshot)
        result[name] = snapshot
    return result


OLD_READER_CHECK = r"""
import json,sqlite3,sys
from datetime import datetime
from pathlib import Path
from src.workflow.store import WorkflowStateStore
from src.workflow.v12_store import V12Store,migrate_v12
from src.workflow.v12_flow import V12WorkflowCoordinator
from src.workflow.v12_contracts import EventType,NotificationKind,PurchaseOutcome
from contextlib import nullcontext
path=Path(sys.argv[1]); now=datetime.fromisoformat(sys.argv[2]); iid=sys.argv[3]
assert 'PURCHASE_STATUS_RECORDED' not in EventType.__members__
assert 'PURCHASE_FOLLOW_UP' not in NotificationKind.__members__
import src.workflow.v12_store as loaded
assert Path(loaded.__file__).resolve().is_relative_to(Path.cwd())
workflow=WorkflowStateStore(path)
ledger=V12Store(path)
assert migrate_v12(path,path.parent/'old-reader-backups',quiesce=nullcontext) is None
history=ledger.event_history(iid)
assert history and all(isinstance(event.event_type,EventType) for event in history)
coordinator=V12WorkflowCoordinator(workflow,ledger,None,None,None,None,None,())
coordinator.initialize_run_state(now=now)
assert ledger.purchase_state(iid) is PurchaseOutcome.SAVED
with sqlite3.connect(path) as db:
    outstanding=db.execute("SELECT outcome FROM workflow_v12_notification_recipients "
        "WHERE command_id LIKE 'purchase-follow-up:%'").fetchall()
    assert outstanding and all(row[0] in {'PENDING','RETRYABLE_FAILURE'} for row in outstanding)
    assert db.execute("SELECT count(*) FROM workflow_v13_purchase_follow_up_episodes").fetchone()[0]==1
commands=ledger.claim_due_notifications(now=now,limit=64)
follow=[command for command in commands if command.command_id.startswith('purchase-follow-up:')]
assert len(follow)==1 and follow[0].kind is NotificationKind.PURCHASE_EXCEPTION
assert {r.address for r in follow[0].recipients}=={'linan229@qq.com','shawn@inso-hk.com'}
print(json.dumps({'schema':True,'events':True,'startup':True,'claim_pending_or_retryable':True,
                  'sidecar_ignored':True,'saved_no_replay':True}))
"""


@pytest.mark.parametrize("legacy", list(LEGACY_REFS))
@pytest.mark.parametrize("retryable", [False, True])
def test_actual_preserved_reader_can_rollback_with_outstanding_follow_up(tmp_path, legacy_sources, legacy, retryable):
    store, ledger, episodes, sheet, action, saved, calls, start = confirmed_status_fixture(tmp_path)
    assert episodes.latest(saved.inquiry_id) is None
    action.process(saved, at=start)
    episode = episodes.latest(saved.inquiry_id)
    assert episode and episode.confirmed_at == start and calls == [3]
    now = local("2026-10-12T11:00:01")
    follow = PurchaseFollowUp(reader=sheet, workflow_store=store, v12_store=ledger,
                             episodes=episodes, clock=lambda: now)
    assert follow.run(SHEET) == 1
    if retryable:
        command = ledger.claim_due_notifications(now=now)[0]
        assert command.kind is NotificationKind.PURCHASE_EXCEPTION
        for recipient in command.recipients:
            ledger.record_notification_result(command_id=command.command_id,
                recipient_id=recipient.recipient_id, outcome=DeliveryOutcome.RETRYABLE_FAILURE, at=now)
        now += timedelta(minutes=2)
    with sqlite3.connect(ledger.database_path) as db:
        assert db.execute("SELECT count(*) FROM workflow_v12_events WHERE event_type='PURCHASE_STATUS_RECORDED'").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM workflow_v12_notification_commands WHERE kind='PURCHASE_FOLLOW_UP'").fetchone()[0] == 0
        version = db.execute("PRAGMA user_version").fetchone()[0]
        assert version == 1201
    environment = {**os.environ, "PYTHONPATH": str(legacy_sources[legacy])}
    child = subprocess.run([sys.executable, "-c", OLD_READER_CHECK, str(ledger.database_path),
                            now.isoformat(), saved.inquiry_id], cwd=legacy_sources[legacy],
                           env=environment, capture_output=True, text=True, timeout=30, check=False)
    assert child.returncode == 0, child.stderr
    assert all(json.loads(child.stdout).values())


def test_real_sidecar_write_failure_preserves_saved_purchase_and_fails_closed(tmp_path):
    _, ledger, episodes, sheet, action, saved, calls, start = confirmed_status_fixture(tmp_path)
    with sqlite3.connect(ledger.database_path) as db:
        db.execute(f"CREATE TRIGGER fail_sidecar BEFORE INSERT ON {TABLE} "
                   "BEGIN SELECT RAISE(ABORT, 'synthetic disk failure'); END")
    with pytest.raises(V12Fault) as error:
        action.process(saved, at=start)
    assert error.value.scope is FaultScope.GLOBAL_STOP
    assert error.value.reason == "WORKFLOW_LEDGER_UNAVAILABLE"
    assert ledger.purchase_state(saved.inquiry_id) is PurchaseOutcome.SAVED
    assert ledger.business_state(saved.inquiry_id) is BusinessState.PURCHASE_RECORDED
    assert sheet.row.cells["A"] == "发给采购" and calls == [3]
    assert episodes.latest(saved.inquiry_id) is None
    action.process(saved, at=start)
    assert calls == [3] and episodes.latest(saved.inquiry_id) is None


def test_sidecar_migration_is_additive_backup_verified_and_idempotent(tmp_path):
    _, ledger, episodes, _, _, _, _, _ = confirmed_status_fixture(tmp_path)
    before = tuple((ledger.database_path.parent / 'backups' / 'v13-follow-up-upgrade').glob('*.sqlite3'))
    assert len(before) == 1
    with sqlite3.connect(before[0]) as backup:
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == 'ok'
        assert backup.execute("SELECT 1 FROM sqlite_master WHERE name=?", (TABLE,)).fetchone() is None
    episodes.migrate()
    assert tuple((ledger.database_path.parent / 'backups' / 'v13-follow-up-upgrade').glob('*.sqlite3')) == before
    with sqlite3.connect(ledger.database_path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1201
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
