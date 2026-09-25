from __future__ import annotations

import sqlite3
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.workflow import WorkflowStateStore
from src.workflow.v12_contracts import (
    AlertType,
    BusinessState,
    DuplicateCheckResult,
    DuplicateOutcome,
    EventType,
    PurchaseOutcome,
    ReasonCode,
    ReconciliationOutcome,
    ReconciliationResult,
    WorkflowEvent,
)
from src.workflow.v12_store import (
    V12_SCHEMA_VERSION,
    BackupCollision,
    FakeSaveReconciler,
    SimulatedMaintenanceCrash,
    V12DatabaseError,
    V12SchemaMismatch,
    V12Store,
    create_verified_backup,
    migrate_v12,
)

NOW = datetime(2026, 9, 25, 8, tzinfo=UTC)
INQUIRY = "inq_0123456789abcdef01234567"


def make_v1_database(path: Path, *, inquiry_id: str = INQUIRY) -> None:
    WorkflowStateStore(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO workflow_items (spreadsheet, worksheet, row_number, inquiry_id, "
            "record_identity_json, mpn_json, brand_json, quantity_json, importance_raw_json, "
            "status, attempt_count, next_attempt_at, research_status, resolved_brand, "
            "brand_update_status, last_error, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'QUEUED', 0, ?, NULL, NULL, NULL, NULL, ?, ?)",
            (
                "sheet-id", "2026", 4, inquiry_id, "{}", '"MPN-1"', '"Brand"', "10", '"A"',
                NOW.isoformat(), NOW.isoformat(), NOW.isoformat(),
            ),
        )


def migrate(path: Path, backups: Path, **kwargs) -> Path | None:
    kwargs.setdefault("clock", lambda: NOW)
    return migrate_v12(
        path,
        backups,
        quiesce=lambda: nullcontext(),
        **kwargs,
    )


def test_consistent_online_backup_includes_committed_wal_activity(tmp_path: Path) -> None:
    database = tmp_path / "workflow.sqlite3"
    backups = tmp_path / "backups"
    make_v1_database(database)
    writer = sqlite3.connect(database)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute(
        "INSERT INTO workflow_items (spreadsheet, worksheet, row_number, inquiry_id, "
        "record_identity_json, mpn_json, brand_json, quantity_json, importance_raw_json, "
        "status, attempt_count, next_attempt_at, created_at, updated_at) "
        "VALUES ('sheet-id','2026',5,'inq_fedcba9876543210fedcba98','{}','\"M2\"','\"B2\"','2','\"B\"','QUEUED',0,?,?,?)",
        (NOW.isoformat(), NOW.isoformat(), NOW.isoformat()),
    )
    writer.commit()  # keep the WAL connection open while online backup runs

    backup = create_verified_backup(
        database,
        backups,
        clock=lambda: NOW,
        pages_per_step=1,
    )

    assert backup.is_file()
    with sqlite3.connect(backup) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT count(*) FROM workflow_items").fetchone()[0] == 2
    writer.close()


def test_backup_interruption_leaves_temp_and_never_publishes_final(tmp_path: Path) -> None:
    database = tmp_path / "workflow.sqlite3"
    backups = tmp_path / "backups"
    make_v1_database(database)

    def interrupt(stage: str, _path: Path | None) -> None:
        if stage == "backup_progress":
            raise SimulatedMaintenanceCrash("synthetic interruption")

    with pytest.raises(SimulatedMaintenanceCrash):
        create_verified_backup(database, backups, clock=lambda: NOW, fault_hook=interrupt, pages_per_step=1)
    assert not list(backups.glob("workflow-v12-pre-migration-*.sqlite3"))
    assert list(backups.glob("*.tmp"))


@pytest.mark.parametrize("fault_stage", ["during_migration", "before_migration_commit"])
def test_migration_crash_rolls_back_additive_ddl_and_can_retry(
    tmp_path: Path, fault_stage: str
) -> None:
    database = tmp_path / "workflow.sqlite3"
    backups = tmp_path / "backups"
    make_v1_database(database)

    def interrupt(stage: str, _path: Path | None) -> None:
        if stage == fault_stage:
            raise SimulatedMaintenanceCrash("synthetic migration crash")

    with pytest.raises(SimulatedMaintenanceCrash):
        migrate(database, backups, fault_hook=interrupt)
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
        names = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "workflow_v12_events" not in names
        assert connection.execute("SELECT count(*) FROM workflow_items").fetchone()[0] == 1

    backup = migrate(database, tmp_path / "retry-backups", clock=lambda: NOW + timedelta(seconds=1))
    assert backup is not None
    V12Store(database)
    assert migrate(database, tmp_path / "ignored-backups", clock=lambda: NOW) is None


def test_migration_creates_verified_backup_then_commits_version_and_record_together(
    tmp_path: Path,
) -> None:
    database = tmp_path / "workflow.sqlite3"
    make_v1_database(database)

    backup = migrate(database, tmp_path / "backups")

    assert backup is not None and backup.exists()
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == V12_SCHEMA_VERSION
        assert connection.execute(
            "SELECT migration_id FROM workflow_v12_schema_migrations"
        ).fetchone()[0] == "v1_2_additive_001"
        assert connection.execute("SELECT count(*) FROM workflow_items").fetchone()[0] == 1
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_backup_collision_fails_without_overwriting_existing_file(tmp_path: Path) -> None:
    database = tmp_path / "workflow.sqlite3"
    backups = tmp_path / "backups"
    make_v1_database(database)
    backups.mkdir()
    prior = backups / "workflow-v12-pre-migration-20260925T080000000000Z.sqlite3"
    prior.write_bytes(b"keep-me")

    with pytest.raises(BackupCollision):
        create_verified_backup(database, backups, clock=lambda: NOW)
    assert prior.read_bytes() == b"keep-me"


def test_invalid_temp_backup_and_disk_full_seam_are_sanitized_and_not_published(
    tmp_path: Path,
) -> None:
    database = tmp_path / "workflow.sqlite3"
    make_v1_database(database)

    def corrupt(stage: str, path: Path | None) -> None:
        if stage == "backup_copied" and path is not None:
            path.write_bytes(b"not sqlite")

    with pytest.raises(V12DatabaseError, match="consistent database backup failed"):
        create_verified_backup(database, tmp_path / "corrupt", clock=lambda: NOW, fault_hook=corrupt)

    def disk_full(stage: str, _path: Path | None) -> None:
        if stage == "backup_copied":
            raise OSError("SECRET_CANARY_disk_full")

    with pytest.raises(V12DatabaseError) as caught:
        create_verified_backup(database, tmp_path / "disk-full", clock=lambda: NOW, fault_hook=disk_full)
    assert "SECRET_CANARY" not in str(caught.value)


def test_partial_inconsistent_version_is_rejected_without_downgrade(tmp_path: Path) -> None:
    database = tmp_path / "workflow.sqlite3"
    make_v1_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version=44")

    with pytest.raises(V12SchemaMismatch):
        migrate(database, tmp_path / "backups")
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 44
        assert connection.execute("SELECT count(*) FROM workflow_items").fetchone()[0] == 1


def test_additive_state_event_alert_and_missing_customer_are_transactional(tmp_path: Path) -> None:
    database = tmp_path / "workflow.sqlite3"
    make_v1_database(database)
    migrate(database, tmp_path / "backups")
    store = V12Store(database)
    at = NOW + timedelta(seconds=1)
    event = WorkflowEvent(
        "evt_business_1", INQUIRY, EventType.RESEARCH_STARTED, at, "workflow"
    )

    store.set_business_state(INQUIRY, BusinessState.RESEARCHING, event)
    store.record_missing_customer(INQUIRY, at + timedelta(seconds=1))

    assert store.latest_active_alert(INQUIRY).alert_type is AlertType.DATA_QUALITY
    history = store.event_history(INQUIRY)
    assert [item.event_type for item in history] == [
        EventType.RESEARCH_STARTED,
        EventType.DATA_QUALITY_MISSING_CUSTOMER,
    ]
    with sqlite3.connect(database) as connection:
        v1_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name='workflow_items'"
        ).fetchone()[0]
        assert "MANUAL_REVIEW" in v1_sql
        assert connection.execute("SELECT status FROM workflow_items").fetchone()[0] == "QUEUED"
        payload = connection.execute(
            "SELECT payload_json FROM workflow_v12_events WHERE event_id='evt_business_1'"
        ).fetchone()[0]
        assert payload == '{"attempt":null,"evidence_ref":null,"reason_code":null}'


def test_v12_event_history_is_database_enforced_append_only(tmp_path: Path) -> None:
    database = tmp_path / "workflow.sqlite3"
    make_v1_database(database)
    migrate(database, tmp_path / "backups")
    store = V12Store(database)
    store.append_event(
        WorkflowEvent("evt_immutable", INQUIRY, EventType.RESEARCH_STARTED, NOW, "workflow")
    )
    with sqlite3.connect(database) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE workflow_v12_events SET source_module='gui' WHERE event_id='evt_immutable'"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM workflow_v12_events WHERE event_id='evt_immutable'"
            )


def test_duplicate_result_alert_and_latest_active_alert_dto(tmp_path: Path) -> None:
    database = tmp_path / "workflow.sqlite3"
    make_v1_database(database)
    migrate(database, tmp_path / "backups")
    store = V12Store(database)
    result = DuplicateCheckResult(
        INQUIRY,
        DuplicateOutcome.CONFIRMED,
        "ABC-1",
        NOW,
        repeated=True,
        historical_date=NOW - timedelta(hours=2),
        historical_mpn="ABC-1",
        historical_quantity=7,
        quantity_equal=False,
        creator="synthetic",
        inso_quote=None,
    )

    store.record_duplicate_result(result)

    active = store.active_alerts(INQUIRY)
    assert len(active) == 1
    assert active[0].alert_type is AlertType.DUPLICATE_ORDER
    assert active[0].reason_code is ReasonCode.DUPLICATE_ORDER_DETECTED


@pytest.mark.parametrize(
    "result,expected",
    [
        (
            ReconciliationResult(
                ReconciliationOutcome.CONFIRMED_SAVED,
                NOW,
                "rec_" + "a" * 32,
                candidate_count=1,
                verified_fields=("mpn", "brand", "quantity"),
            ),
            PurchaseOutcome.SAVED,
        ),
        (
            ReconciliationResult(
                ReconciliationOutcome.CONFIRMED_NOT_SAVED,
                NOW,
                candidate_count=0,
                authoritative=True,
            ),
            PurchaseOutcome.CONFIRMED_NOT_SAVED,
        ),
        (
            ReconciliationResult(
                ReconciliationOutcome.AMBIGUOUS,
                NOW,
                candidate_count=2,
                reason_code=ReasonCode.RECONCILIATION_AMBIGUOUS,
            ),
            PurchaseOutcome.MANUAL_REVIEW,
        ),
        (
            ReconciliationResult(
                ReconciliationOutcome.CONFIRMED_SAVED,
                NOW,
                "rec_" + "b" * 32,
                candidate_count=2,
                verified_fields=("mpn", "brand", "quantity"),
            ),
            PurchaseOutcome.MANUAL_REVIEW,
        ),
        (
            ReconciliationResult(
                ReconciliationOutcome.UNKNOWN,
                NOW,
                reason_code=ReasonCode.RECONCILIATION_UNREADABLE,
            ),
            PurchaseOutcome.MANUAL_REVIEW,
        ),
    ],
)
def test_unknown_write_outcome_reconciles_without_automatic_second_save(
    tmp_path: Path,
    result: ReconciliationResult,
    expected: PurchaseOutcome,
) -> None:
    database = tmp_path / "workflow.sqlite3"
    make_v1_database(database)
    migrate(database, tmp_path / "backups")
    store = V12Store(database)
    store.set_purchase_state(INQUIRY, "purchase-command", PurchaseOutcome.PRE_SAVE_READY, at=NOW)

    # This is the durable pre-dispatch boundary. No Save Data adapter is called.
    store.begin_save_dispatch(INQUIRY, at=NOW + timedelta(seconds=1))
    restarted = V12Store(database)
    with pytest.raises(V12DatabaseError):
        restarted.begin_save_dispatch(INQUIRY, at=NOW + timedelta(seconds=2))

    actual = restarted.reconcile_unknown_save(
        INQUIRY, FakeSaveReconciler(result), at=NOW + timedelta(seconds=3)
    )

    assert actual is expected
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT outcome FROM workflow_v12_purchase_state WHERE inquiry_id=?",
            (INQUIRY,),
        ).fetchone()
        assert row[0] == expected.value
        assert connection.execute(
            "SELECT count(*) FROM workflow_v12_events WHERE event_type='SAVE_OUTCOME_UNKNOWN'"
        ).fetchone()[0] == 1
    if expected is PurchaseOutcome.SAVED:
        with pytest.raises(V12DatabaseError):
            restarted.begin_save_dispatch(INQUIRY, at=NOW + timedelta(seconds=4))
    else:
        with pytest.raises(V12DatabaseError):
            restarted.begin_save_dispatch(INQUIRY, at=NOW + timedelta(seconds=4))


def test_authoritative_absence_requires_explicit_operator_rearm(tmp_path: Path) -> None:
    database = tmp_path / "workflow.sqlite3"
    make_v1_database(database)
    migrate(database, tmp_path / "backups")
    store = V12Store(database)
    store.set_purchase_state(INQUIRY, "purchase-command", PurchaseOutcome.PRE_SAVE_READY, at=NOW)
    store.begin_save_dispatch(INQUIRY, at=NOW + timedelta(seconds=1))
    absence = ReconciliationResult(
        ReconciliationOutcome.CONFIRMED_NOT_SAVED,
        NOW + timedelta(seconds=2),
        candidate_count=0,
        authoritative=True,
    )
    assert store.reconcile_unknown_save(INQUIRY, FakeSaveReconciler(absence), at=NOW) is PurchaseOutcome.CONFIRMED_NOT_SAVED
    with pytest.raises(V12DatabaseError):
        store.begin_save_dispatch(INQUIRY, at=NOW + timedelta(seconds=2))
    with pytest.raises(V12DatabaseError):
        store.rearm_after_confirmed_absence(INQUIRY, operator_acknowledged=False, at=NOW)
    store.rearm_after_confirmed_absence(INQUIRY, operator_acknowledged=True, at=NOW)
    store.begin_save_dispatch(INQUIRY, at=NOW + timedelta(seconds=3))
    with pytest.raises(V12DatabaseError):
        store.begin_save_dispatch(INQUIRY, at=NOW + timedelta(seconds=4))


def test_reconciler_exception_canary_is_not_persisted_or_exposed(tmp_path: Path) -> None:
    database = tmp_path / "workflow.sqlite3"
    make_v1_database(database)
    migrate(database, tmp_path / "backups")
    store = V12Store(database)
    store.set_purchase_state(INQUIRY, "purchase-command", PurchaseOutcome.PRE_SAVE_READY, at=NOW)
    store.begin_save_dispatch(INQUIRY, at=NOW + timedelta(seconds=1))
    result = store.reconcile_unknown_save(
        INQUIRY,
        FakeSaveReconciler(error=TimeoutError("SECRET_CANARY_9F8C_timeout")),
        at=NOW + timedelta(seconds=2),
    )

    assert result is PurchaseOutcome.MANUAL_REVIEW
    assert "SECRET_CANARY" not in repr(store.active_alerts(INQUIRY))
    assert "SECRET_CANARY" not in repr(store.event_history(INQUIRY))
    with sqlite3.connect(database) as connection:
        for (table,) in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'workflow_v12_%'"
        ):
            rows = tuple(tuple(row) for row in connection.execute(f"SELECT * FROM {table}"))
            assert "SECRET_CANARY" not in repr(rows)
