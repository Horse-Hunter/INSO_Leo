"""Additive V1.2 SQLite schema, consistent backup, and durable state.

This module is not wired into the production launcher in Stage 2A. Callers must
quiesce Workflow and close all application DB handles before migration.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .v12_contracts import (
    ActiveAlertDTO,
    AlertType,
    BusinessState,
    DeliveryOutcome,
    DuplicateCheckResult,
    EventType,
    NotificationCommand,
    NotificationKind,
    NotificationRecipient,
    PurchaseOutcome,
    ReasonCode,
    RecipientDeliveryResult,
    ReconciliationOutcome,
    ReconciliationResult,
    WorkflowEvent,
)
from .v12_evidence import validate_evidence_reference

V12_SCHEMA_VERSION = 1201
V1_WORKFLOW_COLUMNS = (
    "id",
    "spreadsheet",
    "worksheet",
    "row_number",
    "inquiry_id",
    "record_identity_json",
    "mpn_json",
    "brand_json",
    "quantity_json",
    "importance_raw_json",
    "status",
    "attempt_count",
    "next_attempt_at",
    "research_status",
    "resolved_brand",
    "brand_update_status",
    "last_error",
    "created_at",
    "updated_at",
)
_ATTEMPT_DELAYS = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=15))
_OPAQUE_REF = re.compile(r"^rec_[a-f0-9]{32}$")


class V12DatabaseError(RuntimeError):
    """A sanitized database maintenance or state error."""


class V12SchemaMismatch(V12DatabaseError):
    pass


class BackupCollision(V12DatabaseError):
    pass


class SimulatedMaintenanceCrash(RuntimeError):
    """Test-only injected interruption; never includes external data."""


FaultHook = Callable[[str, Path | None], None]
QuiesceFactory = Callable[[], AbstractContextManager[None]]


def migrate_v12(
    database_path: str | Path,
    backup_directory: str | Path,
    *,
    quiesce: QuiesceFactory,
    clock: Callable[[], datetime] | None = None,
    fault_hook: FaultHook | None = None,
) -> Path | None:
    """Back up and transactionally create V1.2 tables; never downgrade/drop.

    ``quiesce`` is mandatory and represents the composition-root guarantee
    that workers are stopped and all other application DB handles are closed.
    The caller must not supply a live production path in Stage 2A.
    """

    path = Path(database_path)
    backup_dir = Path(backup_directory)
    if quiesce is None:
        raise V12DatabaseError("workflow quiescence is required")
    observed_at = _as_utc((clock or (lambda: datetime.now(UTC)))())
    with quiesce():
        with _connect(path) as inspect_connection:
            version = int(inspect_connection.execute("PRAGMA user_version").fetchone()[0])
            if version == V12_SCHEMA_VERSION:
                _verify_v12_schema(inspect_connection)
                return None
            if version != 0:
                raise V12SchemaMismatch("database version is inconsistent")
            _verify_v1_baseline(inspect_connection)

        backup_path = create_verified_backup(
            path,
            backup_dir,
            clock=lambda: observed_at,
            fault_hook=fault_hook,
        )
        _fault(fault_hook, "before_migration", backup_path)
        connection = _connect(path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version == V12_SCHEMA_VERSION:
                _verify_v12_schema(connection)
                connection.commit()
                return backup_path
            if version != 0:
                raise V12SchemaMismatch("database version changed during migration")
            _verify_v1_baseline(connection)
            _create_v12_schema(connection)
            _fault(fault_hook, "during_migration", backup_path)
            connection.execute(
                "INSERT INTO workflow_v12_schema_migrations "
                "(version, migration_id, applied_at) VALUES (?, ?, ?)",
                (V12_SCHEMA_VERSION, "v1_2_additive_001", _time_text(observed_at)),
            )
            connection.execute(f"PRAGMA user_version = {V12_SCHEMA_VERSION}")
            _fault(fault_hook, "before_migration_commit", backup_path)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        with _connect(path) as verify:
            _verify_v12_schema(verify)
        return backup_path


def create_verified_backup(
    database_path: str | Path,
    backup_directory: str | Path,
    *,
    clock: Callable[[], datetime] | None = None,
    fault_hook: FaultHook | None = None,
    pages_per_step: int = 32,
) -> Path:
    """Use SQLite online backup, verify it, then atomically publish a new file."""

    try:
        return _create_verified_backup_impl(
            database_path,
            backup_directory,
            clock=clock,
            fault_hook=fault_hook,
            pages_per_step=pages_per_step,
        )
    except (BackupCollision, V12DatabaseError, SimulatedMaintenanceCrash):
        raise
    except Exception:  # noqa: BLE001 - sanitize filesystem/sqlite adapter failures
        # Do not retain driver/OS messages: they can contain paths or data.
        raise V12DatabaseError("consistent database backup failed") from None


def _create_verified_backup_impl(
    database_path: str | Path,
    backup_directory: str | Path,
    *,
    clock: Callable[[], datetime] | None,
    fault_hook: FaultHook | None,
    pages_per_step: int,
) -> Path:

    source_path = Path(database_path)
    backup_dir = Path(backup_directory)
    if not source_path.is_file():
        raise V12DatabaseError("source database is unavailable")
    backup_dir.mkdir(parents=True, exist_ok=True)
    observed_at = _as_utc((clock or (lambda: datetime.now(UTC)))())
    stamp = observed_at.strftime("%Y%m%dT%H%M%S%fZ")
    final_path = backup_dir / f"workflow-v12-pre-migration-{stamp}.sqlite3"
    if final_path.exists():
        raise BackupCollision("timestamped backup already exists")
    temp_path = backup_dir / f".{final_path.name}.{uuid.uuid4().hex}.tmp"
    if temp_path.exists():
        raise BackupCollision("temporary backup path already exists")

    _fault(fault_hook, "backup_started", temp_path)
    source = _connect(source_path)
    destination = _connect(temp_path)
    source_count = -1
    try:
        _verify_v1_baseline(source)
        source_count = int(
            source.execute("SELECT count(*) FROM workflow_items").fetchone()[0]
        )

        def progress(_status: int, _remaining: int, _total: int) -> None:
            _fault(fault_hook, "backup_progress", temp_path)

        source.backup(destination, pages=pages_per_step, progress=progress)
        destination.commit()
    except Exception:
        destination.close()
        source.close()
        raise
    else:
        destination.close()
        source.close()

    _fault(fault_hook, "backup_copied", temp_path)
    _fsync_file(temp_path)
    with _connect(temp_path, read_only=True) as backup:
        _verify_integrity(backup)
        _verify_v1_baseline(backup)
        backup_count = int(
            backup.execute("SELECT count(*) FROM workflow_items").fetchone()[0]
        )
        if backup_count != source_count:
            raise V12DatabaseError("backup table counts do not match")
    _fault(fault_hook, "backup_verified", temp_path)
    _fault(fault_hook, "before_backup_publish", temp_path)
    if final_path.exists():
        raise BackupCollision("timestamped backup already exists")
    try:
        # Windows os.rename fails instead of replacing an existing destination.
        os.rename(temp_path, final_path)
    except FileExistsError as exc:
        raise BackupCollision("timestamped backup already exists") from exc
    _fsync_directory(backup_dir)
    _fault(fault_hook, "backup_published", final_path)
    return final_path


class V12Store:
    """Persistence API for additive V1.2 business/events/alerts/ledgers."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        with _connect(self.database_path) as connection:
            _verify_v12_schema(connection)

    def append_event(self, event: WorkflowEvent) -> None:
        with _transaction(self.database_path) as connection:
            _insert_event(connection, event)

    def set_business_state(
        self,
        inquiry_id: str,
        state: BusinessState,
        event: WorkflowEvent,
    ) -> None:
        if event.inquiry_id != inquiry_id:
            raise ValueError("event inquiry identity mismatch")
        with _transaction(self.database_path) as connection:
            connection.execute(
                "INSERT INTO workflow_v12_inquiry_state "
                "(inquiry_id, business_state, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(inquiry_id) DO UPDATE SET "
                "business_state=excluded.business_state, updated_at=excluded.updated_at",
                (inquiry_id, state.value, _time_text(event.occurred_at)),
            )
            _insert_event(connection, event)

    def record_missing_customer(self, inquiry_id: str, at: datetime) -> None:
        event = WorkflowEvent(
            event_id=_new_id("evt"),
            inquiry_id=inquiry_id,
            event_type=EventType.DATA_QUALITY_MISSING_CUSTOMER,
            occurred_at=at,
            source_module="sheets",
            reason_code=ReasonCode.CUSTOMER_NAME_MISSING,
        )
        alert_id = _new_id("alt")
        with _transaction(self.database_path) as connection:
            _insert_event(connection, event)
            _raise_alert(
                connection,
                alert_id=alert_id,
                inquiry_id=inquiry_id,
                alert_type=AlertType.DATA_QUALITY,
                reason_code=ReasonCode.CUSTOMER_NAME_MISSING,
                event_id=event.event_id,
                at=at,
            )

    def record_duplicate_result(self, result: DuplicateCheckResult) -> None:
        evidence_ref = (
            None
            if result.evidence_ref is None
            else validate_evidence_reference(result.evidence_ref)
        )
        result_id = _new_id("dup")
        event_type = (
            EventType.DUPLICATE_CHECK_CONFIRMED
            if result.outcome.value == "CONFIRMED"
            else EventType.DUPLICATE_CHECK_FAILED
        )
        event = WorkflowEvent(
            _new_id("evt"),
            result.inquiry_id,
            event_type,
            result.checked_at,
            "inso",
            reason_code=result.reason_code,
            evidence_ref=evidence_ref,
        )
        with _transaction(self.database_path) as connection:
            connection.execute(
                "INSERT INTO workflow_v12_duplicate_results "
                "(result_id, inquiry_id, outcome, repeated, target_mpn_canonical, "
                "historical_date, historical_mpn, historical_quantity, quantity_equal, "
                "creator, inso_quote, currency, checked_at, evidence_ref, reason_code) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    result_id,
                    result.inquiry_id,
                    result.outcome.value,
                    None if result.repeated is None else int(result.repeated),
                    result.target_mpn_canonical,
                    _time_text(result.historical_date),
                    result.historical_mpn,
                    result.historical_quantity,
                    None if result.quantity_equal is None else int(result.quantity_equal),
                    result.creator,
                    None if result.inso_quote is None else str(result.inso_quote),
                    result.currency,
                    _time_text(result.checked_at),
                    evidence_ref,
                    _reason(result.reason_code),
                ),
            )
            _insert_event(connection, event)
            if result.outcome.value == "CONFIRMED" and result.repeated:
                _raise_alert(
                    connection,
                    alert_id=_new_id("alt"),
                    inquiry_id=result.inquiry_id,
                    alert_type=AlertType.DUPLICATE_ORDER,
                    reason_code=result.reason_code or ReasonCode.DUPLICATE_ORDER_DETECTED,
                    event_id=event.event_id,
                    at=result.checked_at,
                    deduplicate_by_type=True,
                )

    def raise_alert(
        self,
        *,
        inquiry_id: str,
        alert_type: AlertType,
        reason_code: ReasonCode,
        event: WorkflowEvent,
    ) -> str:
        if event.inquiry_id != inquiry_id:
            raise ValueError("event inquiry identity mismatch")
        alert_id = _new_id("alt")
        with _transaction(self.database_path) as connection:
            _insert_event(connection, event)
            _raise_alert(
                connection,
                alert_id=alert_id,
                inquiry_id=inquiry_id,
                alert_type=alert_type,
                reason_code=reason_code,
                event_id=event.event_id,
                at=event.occurred_at,
            )
        return alert_id

    def enqueue_notification(self, command: NotificationCommand) -> None:
        if not command.recipients:
            raise ValueError("notification requires at least one recipient")
        if command.created_at.tzinfo is None:
            raise ValueError("notification timestamp must be timezone-aware")
        event = WorkflowEvent(
            _new_id("evt"), command.inquiry_id,
            EventType.NOTIFICATION_COMMAND_CREATED,
            command.created_at, "workflow",
        )
        with _transaction(self.database_path) as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO workflow_v12_notification_commands "
                "(command_id, inquiry_id, kind, subject, text_body, html_body, "
                "created_at, payload_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    command.command_id,
                    command.inquiry_id,
                    command.kind.value,
                    command.subject,
                    command.text_body,
                    command.html_body,
                    _time_text(command.created_at),
                    command.payload_version,
                ),
            )
            inserted = cursor.rowcount == 1
            if not inserted:
                existing = connection.execute(
                    "SELECT inquiry_id, kind, subject, text_body, html_body, "
                    "created_at, payload_version FROM workflow_v12_notification_commands "
                    "WHERE command_id=?",
                    (command.command_id,),
                ).fetchone()
                expected = (
                    command.inquiry_id, command.kind.value, command.subject,
                    command.text_body, command.html_body,
                    _time_text(command.created_at), command.payload_version,
                )
                if existing is None or tuple(existing) != expected:
                    raise V12DatabaseError("notification command idempotency conflict")
                persisted_recipients = {
                    item["recipient_id"]: item["address"]
                    for item in connection.execute(
                        "SELECT recipient_id, address FROM workflow_v12_notification_recipients "
                        "WHERE command_id=?",
                        (command.command_id,),
                    ).fetchall()
                }
                requested_recipients = {
                    item.recipient_id: item.address for item in command.recipients
                }
                if persisted_recipients != requested_recipients:
                    raise V12DatabaseError("notification recipient idempotency conflict")
            for recipient in command.recipients:
                if inserted:
                    connection.execute(
                        "INSERT INTO workflow_v12_notification_recipients "
                        "(command_id, recipient_id, address, outcome, attempt_count) "
                        "VALUES (?, ?, ?, 'PENDING', 0)",
                        (command.command_id, recipient.recipient_id, recipient.address),
                    )
                else:
                    prior = connection.execute(
                        "SELECT address FROM workflow_v12_notification_recipients "
                        "WHERE command_id=? AND recipient_id=?",
                        (command.command_id, recipient.recipient_id),
                    ).fetchone()
                    if prior is None or prior[0] != recipient.address:
                        raise V12DatabaseError("notification recipient idempotency conflict")
            if inserted:
                _insert_event(connection, event)

    def claim_due_notifications(
        self, *, now: datetime, limit: int = 16
    ) -> tuple[NotificationCommand, ...]:
        """Atomically claim each recipient independently for one fake send pass."""

        if limit <= 0:
            raise ValueError("limit must be positive")
        claimed: list[NotificationCommand] = []
        with _transaction(self.database_path) as connection:
            rows = connection.execute(
                "SELECT r.command_id, r.recipient_id, r.address, c.inquiry_id, "
                "c.kind, c.subject, c.text_body, c.html_body, c.created_at, "
                "c.payload_version, r.attempt_count "
                "FROM workflow_v12_notification_recipients r "
                "JOIN workflow_v12_notification_commands c USING(command_id) "
                "WHERE r.outcome IN ('PENDING', 'RETRYABLE_FAILURE') "
                "AND (r.next_attempt_at IS NULL OR r.next_attempt_at <= ?) "
                "ORDER BY r.next_attempt_at, r.command_id, r.recipient_id LIMIT ?",
                (_time_text(now), limit),
            ).fetchall()
            grouped: dict[str, tuple[sqlite3.Row, list[NotificationRecipient]]] = {}
            for row in rows:
                connection.execute(
                    "UPDATE workflow_v12_notification_recipients "
                    "SET outcome='SENDING', attempt_count=attempt_count+1 "
                    "WHERE command_id=? AND recipient_id=? "
                    "AND outcome IN ('PENDING', 'RETRYABLE_FAILURE')",
                    (row["command_id"], row["recipient_id"]),
                )
                command_id = row["command_id"]
                if command_id not in grouped:
                    grouped[command_id] = (row, [])
                grouped[command_id][1].append(
                    NotificationRecipient(row["recipient_id"], row["address"])
                )
            for row, recipients in grouped.values():
                claimed.append(
                    NotificationCommand(
                        row["command_id"], row["inquiry_id"],
                        NotificationKind(row["kind"]), tuple(recipients),
                        row["subject"], row["text_body"], row["html_body"],
                        _parse_time(row["created_at"]), row["payload_version"],
                    )
                )
        return tuple(claimed)

    def record_notification_result(
        self,
        *,
        command_id: str,
        recipient_id: str,
        outcome: DeliveryOutcome,
        at: datetime,
        reason_code: ReasonCode | None = None,
    ) -> RecipientDeliveryResult:
        if outcome not in {
            DeliveryOutcome.SENT,
            DeliveryOutcome.RETRYABLE_FAILURE,
            DeliveryOutcome.PERMANENT_FAILURE,
            DeliveryOutcome.UNKNOWN,
        }:
            raise ValueError("result outcome is not terminal")
        alert_to_raise: tuple[str, str, AlertType, ReasonCode, str, datetime] | None = None
        result: RecipientDeliveryResult
        with _transaction(self.database_path) as connection:
            row = connection.execute(
                "SELECT r.attempt_count, r.outcome, c.inquiry_id "
                "FROM workflow_v12_notification_recipients r "
                "JOIN workflow_v12_notification_commands c USING(command_id) "
                "WHERE command_id=? AND recipient_id=?",
                (command_id, recipient_id),
            ).fetchone()
            if row is None:
                raise KeyError((command_id, recipient_id))
            if row["outcome"] != DeliveryOutcome.SENDING.value:
                raise V12DatabaseError("recipient is not in a sending attempt")
            attempt = int(row["attempt_count"])
            next_at: datetime | None = None
            persisted_outcome = outcome
            if outcome is DeliveryOutcome.RETRYABLE_FAILURE:
                if attempt <= len(_ATTEMPT_DELAYS):
                    next_at = _as_utc(at) + _ATTEMPT_DELAYS[attempt - 1]
                else:
                    persisted_outcome = DeliveryOutcome.PERMANENT_FAILURE
            connection.execute(
                "UPDATE workflow_v12_notification_recipients SET outcome=?, "
                "next_attempt_at=?, reason_code=?, last_attempt_at=? "
                "WHERE command_id=? AND recipient_id=?",
                (
                    persisted_outcome.value,
                    _time_text(next_at),
                    _reason(reason_code),
                    _time_text(at),
                    command_id,
                    recipient_id,
                ),
            )
            inquiry_id = row["inquiry_id"]
            event_type = (
                EventType.NOTIFICATION_DELIVERY_SUCCEEDED
                if persisted_outcome is DeliveryOutcome.SENT
                else EventType.NOTIFICATION_RETRY_SCHEDULED
                if persisted_outcome is DeliveryOutcome.RETRYABLE_FAILURE and next_at
                else EventType.NOTIFICATION_DELIVERY_FAILED
            )
            event = WorkflowEvent(
                _new_id("evt"), inquiry_id, event_type, at, "notification",
                reason_code=reason_code, attempt=attempt,
            )
            _insert_event(connection, event)
            if persisted_outcome is not DeliveryOutcome.SENT:
                alert_to_raise = (
                    _new_id("alt"), inquiry_id, AlertType.NOTIFICATION_FAILED,
                    reason_code or ReasonCode.NOTIFICATION_UNKNOWN,
                    event.event_id, at,
                )
            if alert_to_raise:
                aid, iid, alert_type, alert_reason, event_id, raised_at = alert_to_raise
                _raise_alert(
                    connection,
                    alert_id=aid,
                    inquiry_id=iid,
                    alert_type=alert_type,
                    reason_code=alert_reason,
                    event_id=event_id,
                    at=raised_at,
                    deduplicate_by_type=True,
                    scope_key=command_id,
                )
            if _all_recipients_sent(connection, command_id):
                _recover_alerts(
                    connection,
                    inquiry_id,
                    AlertType.NOTIFICATION_FAILED,
                    event,
                    at,
                    scope_key=command_id,
                )
            result = RecipientDeliveryResult(
                command_id,
                recipient_id,
                persisted_outcome,
                attempt,
                at,
                reason_code=reason_code,
                next_attempt_at=next_at,
            )
        return result

    def recover_abandoned_notification_attempts(self, *, at: datetime) -> int:
        """A crash during send is UNKNOWN and is never auto-queued again."""

        with _transaction(self.database_path) as connection:
            rows = connection.execute(
                "SELECT command_id, recipient_id FROM workflow_v12_notification_recipients "
                "WHERE outcome='SENDING'"
            ).fetchall()
            for row in rows:
                connection.execute(
                    "UPDATE workflow_v12_notification_recipients SET outcome='UNKNOWN', "
                    "reason_code=? WHERE command_id=? AND recipient_id=?",
                    (
                        ReasonCode.NOTIFICATION_UNKNOWN.value,
                        row["command_id"], row["recipient_id"],
                    ),
                )
                inquiry = connection.execute(
                    "SELECT inquiry_id FROM workflow_v12_notification_commands WHERE command_id=?",
                    (row["command_id"],),
                ).fetchone()
                event = WorkflowEvent(
                    _new_id("evt"), inquiry["inquiry_id"],
                    EventType.NOTIFICATION_DELIVERY_FAILED, at, "notification",
                    reason_code=ReasonCode.NOTIFICATION_UNKNOWN,
                )
                _insert_event(connection, event)
                _raise_alert(
                    connection,
                    alert_id=_new_id("alt"),
                    inquiry_id=inquiry["inquiry_id"],
                    alert_type=AlertType.NOTIFICATION_FAILED,
                    reason_code=ReasonCode.NOTIFICATION_UNKNOWN,
                    event_id=event.event_id,
                    at=at,
                    deduplicate_by_type=True,
                    scope_key=row["command_id"],
                )
            return len(rows)

    def set_purchase_state(
        self,
        inquiry_id: str,
        command_id: str,
        outcome: PurchaseOutcome,
        *,
        at: datetime,
        reason_code: ReasonCode | None = None,
        saved_record_ref: str | None = None,
    ) -> None:
        if outcome not in {
            PurchaseOutcome.PRE_SAVE_READY,
            PurchaseOutcome.AI_RECOGNIZED,
            PurchaseOutcome.VALIDATION_FAILED,
        }:
            raise V12DatabaseError("purchase result requires a guarded transition")
        with _transaction(self.database_path) as connection:
            current = connection.execute(
                "SELECT outcome FROM workflow_v12_purchase_state WHERE inquiry_id=?",
                (inquiry_id,),
            ).fetchone()
            if current is not None and current["outcome"] in {
                PurchaseOutcome.UNKNOWN_WRITE_OUTCOME.value,
                PurchaseOutcome.READ_ONLY_RECONCILIATION_REQUIRED.value,
                PurchaseOutcome.SAVED.value,
                PurchaseOutcome.CONFIRMED_NOT_SAVED.value,
                PurchaseOutcome.MANUAL_REVIEW.value,
            }:
                raise V12DatabaseError("purchase state requires reconciliation")
            connection.execute(
                "INSERT INTO workflow_v12_purchase_state "
                "(inquiry_id, command_id, outcome, reason_code, saved_record_ref, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(inquiry_id) DO UPDATE SET "
                "command_id=excluded.command_id, outcome=excluded.outcome, "
                "reason_code=excluded.reason_code, saved_record_ref=excluded.saved_record_ref, "
                "updated_at=excluded.updated_at",
                (
                    inquiry_id, command_id, outcome.value, _reason(reason_code),
                    _safe_ref(saved_record_ref), _time_text(at),
                ),
            )
            event_type = {
                PurchaseOutcome.PRE_SAVE_READY: EventType.PURCHASE_DRAFT_STARTED,
                PurchaseOutcome.AI_RECOGNIZED: EventType.AI_RECOGNITION_READY,
                PurchaseOutcome.VALIDATION_FAILED: EventType.AI_RECOGNITION_MISMATCH,
            }[outcome]
            event = WorkflowEvent(
                _new_id("evt"), inquiry_id, event_type, at, "inso",
                reason_code=reason_code,
            )
            _insert_event(connection, event)
            if outcome is PurchaseOutcome.VALIDATION_FAILED:
                _raise_alert(
                    connection,
                    alert_id=_new_id("alt"), inquiry_id=inquiry_id,
                    alert_type=AlertType.PURCHASE_EXCEPTION,
                    reason_code=reason_code or ReasonCode.AI_RECOGNITION_MISMATCH,
                    event_id=event.event_id, at=at, deduplicate_by_type=True,
                    scope_key="ai-recognition",
                )

    def begin_save_dispatch(self, inquiry_id: str, *, at: datetime) -> None:
        """Persist UNKNOWN before a future dispatch boundary; never dispatches."""

        event = WorkflowEvent(
            _new_id("evt"), inquiry_id, EventType.SAVE_OUTCOME_UNKNOWN,
            at, "workflow", reason_code=ReasonCode.SAVE_OUTCOME_UNKNOWN,
        )
        with _transaction(self.database_path) as connection:
            row = connection.execute(
                "SELECT command_id, outcome FROM workflow_v12_purchase_state WHERE inquiry_id=?",
                (inquiry_id,),
            ).fetchone()
            if row is None or row["outcome"] not in {
                PurchaseOutcome.PRE_SAVE_READY.value,
                PurchaseOutcome.AI_RECOGNIZED.value,
            }:
                raise V12DatabaseError("purchase state is not eligible for dispatch arming")
            connection.execute(
                "UPDATE workflow_v12_purchase_state SET outcome=?, reason_code=?, "
                "saved_record_ref=NULL, updated_at=? WHERE inquiry_id=?",
                (
                    PurchaseOutcome.UNKNOWN_WRITE_OUTCOME.value,
                    ReasonCode.SAVE_OUTCOME_UNKNOWN.value,
                    _time_text(at), inquiry_id,
                ),
            )
            _insert_event(connection, event)
            _raise_alert(
                connection,
                alert_id=_new_id("alt"), inquiry_id=inquiry_id,
                alert_type=AlertType.PURCHASE_EXCEPTION,
                reason_code=ReasonCode.SAVE_OUTCOME_UNKNOWN,
                event_id=event.event_id, at=at, deduplicate_by_type=True,
                scope_key="save-outcome",
            )

    def reconcile_unknown_save(
        self,
        inquiry_id: str,
        reconciler: ReadOnlySaveReconciler,
        *,
        at: datetime,
    ) -> PurchaseOutcome:
        """Apply only a typed read-only result; raw exceptions never persist."""

        current = self._purchase_outcome(inquiry_id)
        if current is PurchaseOutcome.UNKNOWN_WRITE_OUTCOME:
            self._transition_reconciliation_required(inquiry_id, at)
        elif current is not PurchaseOutcome.READ_ONLY_RECONCILIATION_REQUIRED:
            raise V12DatabaseError("save reconciliation is not required")
        try:
            result = reconciler.reconcile(inquiry_id)
        except Exception as exc:  # noqa: BLE001 - fail closed on reconciler errors
            del exc
            result = ReconciliationResult(
                ReconciliationOutcome.UNKNOWN,
                at,
                reason_code=ReasonCode.RECONCILIATION_UNREADABLE,
            )
        target: PurchaseOutcome
        event_type: EventType
        reason = result.reason_code
        saved_ref = None
        if result.outcome is ReconciliationOutcome.CONFIRMED_SAVED:
            required_fields = {"mpn", "brand", "quantity"}
            if (
                not _safe_ref(result.saved_record_ref)
                or result.candidate_count != 1
                or not required_fields.issubset(result.verified_fields)
            ):
                target = PurchaseOutcome.MANUAL_REVIEW
                event_type = EventType.RECONCILIATION_AMBIGUOUS
                reason = ReasonCode.RECONCILIATION_UNREADABLE
            else:
                target = PurchaseOutcome.SAVED
                event_type = EventType.RECONCILIATION_CONFIRMED_SAVED
                saved_ref = result.saved_record_ref
        elif result.outcome is ReconciliationOutcome.CONFIRMED_NOT_SAVED:
            if not result.authoritative or result.candidate_count != 0:
                target = PurchaseOutcome.MANUAL_REVIEW
                event_type = EventType.RECONCILIATION_AMBIGUOUS
                reason = ReasonCode.RECONCILIATION_UNREADABLE
            else:
                target = PurchaseOutcome.CONFIRMED_NOT_SAVED
                event_type = EventType.RECONCILIATION_CONFIRMED_NOT_SAVED
        else:
            target = PurchaseOutcome.MANUAL_REVIEW
            event_type = EventType.RECONCILIATION_AMBIGUOUS
            reason = reason or (
                ReasonCode.RECONCILIATION_AMBIGUOUS
                if result.outcome is ReconciliationOutcome.AMBIGUOUS
                else ReasonCode.RECONCILIATION_UNREADABLE
            )
        event = WorkflowEvent(
            _new_id("evt"), inquiry_id, event_type, result.reconciled_at,
            "inso", reason_code=reason,
        )
        with _transaction(self.database_path) as connection:
            connection.execute(
                "UPDATE workflow_v12_purchase_state SET outcome=?, reason_code=?, "
                "saved_record_ref=?, updated_at=? WHERE inquiry_id=?",
                (target.value, _reason(reason), _safe_ref(saved_ref), _time_text(at), inquiry_id),
            )
            _insert_event(connection, event)
            if target is PurchaseOutcome.SAVED:
                _recover_alerts(
                    connection, inquiry_id, AlertType.PURCHASE_EXCEPTION, event,
                    result.reconciled_at, scope_key="save-outcome",
                )
            elif target is PurchaseOutcome.MANUAL_REVIEW:
                _raise_alert(
                    connection,
                    alert_id=_new_id("alt"), inquiry_id=inquiry_id,
                    alert_type=AlertType.PURCHASE_EXCEPTION,
                    reason_code=reason or ReasonCode.RECONCILIATION_AMBIGUOUS,
                    event_id=event.event_id, at=result.reconciled_at,
                    deduplicate_by_type=True,
                    scope_key="save-outcome",
                )
        return target

    def rearm_after_confirmed_absence(
        self, inquiry_id: str, *, operator_acknowledged: bool, at: datetime
    ) -> None:
        if not operator_acknowledged:
            raise V12DatabaseError("operator acknowledgement is required")
        event = WorkflowEvent(
            _new_id("evt"), inquiry_id, EventType.HUMAN_RESOLUTION_RECORDED,
            at, "workflow", reason_code=ReasonCode.SAVE_OUTCOME_UNKNOWN,
        )
        with _transaction(self.database_path) as connection:
            row = connection.execute(
                "SELECT outcome FROM workflow_v12_purchase_state WHERE inquiry_id=?",
                (inquiry_id,),
            ).fetchone()
            if row is None or row["outcome"] != PurchaseOutcome.CONFIRMED_NOT_SAVED.value:
                raise V12DatabaseError("authoritative absence has not been confirmed")
            connection.execute(
                "UPDATE workflow_v12_purchase_state SET outcome=?, reason_code=NULL, updated_at=? "
                "WHERE inquiry_id=?",
                (PurchaseOutcome.PRE_SAVE_READY.value, _time_text(at), inquiry_id),
            )
            _insert_event(connection, event)
            _recover_alerts(
                connection, inquiry_id, AlertType.PURCHASE_EXCEPTION, event, at,
                scope_key="save-outcome",
            )

    def active_alerts(self, inquiry_id: str) -> tuple[ActiveAlertDTO, ...]:
        with _connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT alert_id, inquiry_id, alert_type, reason_code, raised_at, active "
                "FROM workflow_v12_active_alerts WHERE inquiry_id=? AND active=1 "
                "ORDER BY raised_at DESC, alert_id DESC",
                (inquiry_id,),
            ).fetchall()
        return tuple(
            ActiveAlertDTO(
                row["alert_id"], row["inquiry_id"], AlertType(row["alert_type"]),
                ReasonCode(row["reason_code"]), _parse_time(row["raised_at"]),
                bool(row["active"]),
            )
            for row in rows
        )

    def latest_active_alert(self, inquiry_id: str) -> ActiveAlertDTO | None:
        rows = self.active_alerts(inquiry_id)
        return rows[0] if rows else None

    def event_history(self, inquiry_id: str) -> tuple[WorkflowEvent, ...]:
        with _connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT event_id, inquiry_id, event_type, occurred_at, source_module, "
                "reason_code, attempt, evidence_ref FROM workflow_v12_events "
                "WHERE inquiry_id=? ORDER BY occurred_at, event_id",
                (inquiry_id,),
            ).fetchall()
        return tuple(
            WorkflowEvent(
                row["event_id"], row["inquiry_id"], EventType(row["event_type"]),
                _parse_time(row["occurred_at"]), row["source_module"],
                _as_reason(row["reason_code"]), row["attempt"], row["evidence_ref"],
            )
            for row in rows
        )

    def recipient_results(self, command_id: str) -> tuple[RecipientDeliveryResult, ...]:
        with _connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT r.recipient_id, r.outcome, r.attempt_count, r.next_attempt_at, "
                "r.reason_code, r.last_attempt_at, c.created_at "
                "FROM workflow_v12_notification_recipients r "
                "JOIN workflow_v12_notification_commands c USING(command_id) "
                "WHERE r.command_id=? "
                "ORDER BY recipient_id",
                (command_id,),
            ).fetchall()
        return tuple(
            RecipientDeliveryResult(
                command_id,
                row["recipient_id"],
                DeliveryOutcome(row["outcome"]),
                int(row["attempt_count"]),
                _parse_time(row["last_attempt_at"])
                if row["last_attempt_at"] else _parse_time(row["created_at"]),
                reason_code=ReasonCode(row["reason_code"])
                if row["reason_code"] else None,
                next_attempt_at=_parse_time(row["next_attempt_at"])
                if row["next_attempt_at"] else None,
            )
            for row in rows
        )

    def purchase_state(self, inquiry_id: str) -> PurchaseOutcome:
        return self._purchase_outcome(inquiry_id)

    def _purchase_outcome(self, inquiry_id: str) -> PurchaseOutcome:
        with _connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT outcome FROM workflow_v12_purchase_state WHERE inquiry_id=?",
                (inquiry_id,),
            ).fetchone()
        if row is None:
            raise KeyError(inquiry_id)
        return PurchaseOutcome(row["outcome"])

    def _transition_reconciliation_required(self, inquiry_id: str, at: datetime) -> None:
        event = WorkflowEvent(
            _new_id("evt"), inquiry_id, EventType.RECONCILIATION_STARTED,
            at, "workflow", reason_code=ReasonCode.SAVE_OUTCOME_UNKNOWN,
        )
        with _transaction(self.database_path) as connection:
            connection.execute(
                "UPDATE workflow_v12_purchase_state SET outcome=?, updated_at=? "
                "WHERE inquiry_id=? AND outcome=?",
                (
                    PurchaseOutcome.READ_ONLY_RECONCILIATION_REQUIRED.value,
                    _time_text(at), inquiry_id,
                    PurchaseOutcome.UNKNOWN_WRITE_OUTCOME.value,
                ),
            )
            _insert_event(connection, event)


class ReadOnlySaveReconciler:
    """Structural interface documented as an ABC-free fake/live boundary."""

    def reconcile(self, inquiry_id: str) -> ReconciliationResult:
        raise NotImplementedError


class FakeSaveReconciler(ReadOnlySaveReconciler):
    def __init__(self, result: ReconciliationResult | None = None, *, error: Exception | None = None):
        self.result = result
        self.error = error
        self.calls: list[str] = []

    def reconcile(self, inquiry_id: str) -> ReconciliationResult:
        self.calls.append(inquiry_id)
        if self.error is not None:
            raise self.error
        if self.result is None:
            return ReconciliationResult(
                ReconciliationOutcome.UNKNOWN,
                datetime.now(UTC),
                reason_code=ReasonCode.RECONCILIATION_UNREADABLE,
            )
        return self.result


def _create_v12_schema(connection: sqlite3.Connection) -> None:
    ddl = [
        """CREATE TABLE workflow_v12_schema_migrations (
            version INTEGER PRIMARY KEY, migration_id TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL)""",
        """CREATE TABLE workflow_v12_inquiry_state (
            inquiry_id TEXT PRIMARY KEY REFERENCES workflow_items(inquiry_id) ON DELETE RESTRICT,
            business_state TEXT NOT NULL, updated_at TEXT NOT NULL)""",
        """CREATE TABLE workflow_v12_events (
            event_id TEXT PRIMARY KEY,
            inquiry_id TEXT NOT NULL REFERENCES workflow_items(inquiry_id) ON DELETE RESTRICT,
            event_type TEXT NOT NULL, occurred_at TEXT NOT NULL, source_module TEXT NOT NULL,
            schema_version INTEGER NOT NULL, reason_code TEXT, attempt INTEGER,
            evidence_ref TEXT, payload_json TEXT NOT NULL)""",
        """CREATE TRIGGER workflow_v12_events_no_update
            BEFORE UPDATE ON workflow_v12_events
            BEGIN SELECT RAISE(ABORT, 'workflow events are append-only'); END""",
        """CREATE TRIGGER workflow_v12_events_no_delete
            BEFORE DELETE ON workflow_v12_events
            BEGIN SELECT RAISE(ABORT, 'workflow events are append-only'); END""",
        (
            "CREATE INDEX workflow_v12_events_inquiry_time "
            "ON workflow_v12_events(inquiry_id, occurred_at, event_id)"
        ),
        """CREATE TABLE workflow_v12_active_alerts (
            alert_id TEXT PRIMARY KEY,
            inquiry_id TEXT NOT NULL REFERENCES workflow_items(inquiry_id) ON DELETE RESTRICT,
            alert_type TEXT NOT NULL, reason_code TEXT NOT NULL,
            raised_event_id TEXT NOT NULL REFERENCES workflow_v12_events(event_id),
            active INTEGER NOT NULL CHECK(active IN (0,1)), raised_at TEXT NOT NULL,
            recovered_at TEXT, recovered_by_event_id TEXT REFERENCES workflow_v12_events(event_id),
            scope_key TEXT NOT NULL DEFAULT '')""",
        (
            "CREATE INDEX workflow_v12_alerts_active "
            "ON workflow_v12_active_alerts(inquiry_id, active, raised_at)"
        ),
        """CREATE TABLE workflow_v12_duplicate_results (
            result_id TEXT PRIMARY KEY,
            inquiry_id TEXT NOT NULL REFERENCES workflow_items(inquiry_id) ON DELETE RESTRICT,
            outcome TEXT NOT NULL, repeated INTEGER CHECK(repeated IN (0,1)),
            target_mpn_canonical TEXT NOT NULL, historical_date TEXT, historical_mpn TEXT,
            historical_quantity INTEGER, quantity_equal INTEGER CHECK(quantity_equal IN (0,1)),
            creator TEXT, inso_quote TEXT, currency TEXT, checked_at TEXT NOT NULL,
            evidence_ref TEXT, reason_code TEXT)""",
        """CREATE TABLE workflow_v12_notification_commands (
            command_id TEXT PRIMARY KEY,
            inquiry_id TEXT NOT NULL REFERENCES workflow_items(inquiry_id) ON DELETE RESTRICT,
            kind TEXT NOT NULL, subject TEXT NOT NULL, text_body TEXT NOT NULL,
            html_body TEXT, created_at TEXT NOT NULL, payload_version INTEGER NOT NULL)""",
        """CREATE TABLE workflow_v12_notification_recipients (
            command_id TEXT NOT NULL REFERENCES workflow_v12_notification_commands(command_id) ON DELETE RESTRICT,
            recipient_id TEXT NOT NULL, address TEXT NOT NULL, outcome TEXT NOT NULL,
            attempt_count INTEGER NOT NULL DEFAULT 0, next_attempt_at TEXT, reason_code TEXT,
            last_attempt_at TEXT, PRIMARY KEY(command_id, recipient_id))""",
        (
            "CREATE INDEX workflow_v12_notification_due "
            "ON workflow_v12_notification_recipients(outcome, next_attempt_at)"
        ),
        """CREATE TABLE workflow_v12_purchase_state (
            inquiry_id TEXT PRIMARY KEY REFERENCES workflow_items(inquiry_id) ON DELETE RESTRICT,
            command_id TEXT NOT NULL, outcome TEXT NOT NULL, reason_code TEXT,
            saved_record_ref TEXT, evidence_ref TEXT, updated_at TEXT NOT NULL)""",
    ]
    for statement in ddl:
        connection.execute(statement)


def _verify_v1_baseline(connection: sqlite3.Connection) -> None:
    tables = tuple(
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    )
    if tables != ("workflow_items",):
        raise V12SchemaMismatch("database does not match the supported V1.1 baseline")
    columns = tuple(row[1] for row in connection.execute("PRAGMA table_info(workflow_items)"))
    if columns != V1_WORKFLOW_COLUMNS:
        raise V12SchemaMismatch("V1.1 workflow table columns are not the expected baseline")
    create_sql = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='workflow_items'"
    ).fetchone()[0]
    required_sql = (
        "'QUEUED'", "'RESEARCHING'", "'RETRY_WAIT'", "'COMPLETED'",
        "'MANUAL_REVIEW'", "'FAILED'", "UNIQUE (spreadsheet, worksheet, row_number)",
    )
    normalized = " ".join(create_sql.upper().split())
    if any(fragment.upper() not in normalized for fragment in required_sql):
        raise V12SchemaMismatch("V1.1 workflow constraints are not the expected baseline")
    _verify_integrity(connection)


def _verify_v12_schema(connection: sqlite3.Connection) -> None:
    version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if version != V12_SCHEMA_VERSION:
        raise V12SchemaMismatch("V1.2 schema version is not committed")
    required = {
        "workflow_items",
        "workflow_v12_schema_migrations",
        "workflow_v12_inquiry_state",
        "workflow_v12_events",
        "workflow_v12_active_alerts",
        "workflow_v12_duplicate_results",
        "workflow_v12_notification_commands",
        "workflow_v12_notification_recipients",
        "workflow_v12_purchase_state",
    }
    present = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    if not required.issubset(present):
        raise V12SchemaMismatch("V1.2 schema is incomplete")
    triggers = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        )
    }
    if not {
        "workflow_v12_events_no_update",
        "workflow_v12_events_no_delete",
    }.issubset(triggers):
        raise V12SchemaMismatch("V1.2 event append-only guards are missing")
    migration = connection.execute(
        "SELECT migration_id FROM workflow_v12_schema_migrations WHERE version=?",
        (V12_SCHEMA_VERSION,),
    ).fetchone()
    if migration is None or migration[0] != "v1_2_additive_001":
        raise V12SchemaMismatch("V1.2 migration record is missing")


def _insert_event(connection: sqlite3.Connection, event: WorkflowEvent) -> None:
    if event.occurred_at.tzinfo is None:
        raise ValueError("event timestamp must be timezone-aware")
    if event.attempt is not None and event.attempt < 0:
        raise ValueError("event attempt must be nonnegative")
    if event.source_module not in {"workflow", "inso", "notification", "sheets", "launcher"}:
        raise ValueError("event source module is not allowlisted")
    evidence_ref = (
        None
        if event.evidence_ref is None
        else validate_evidence_reference(event.evidence_ref)
    )
    safe_payload = {
        "reason_code": _reason(event.reason_code),
        "attempt": event.attempt,
        "evidence_ref": evidence_ref,
    }
    connection.execute(
        "INSERT INTO workflow_v12_events "
        "(event_id, inquiry_id, event_type, occurred_at, source_module, schema_version, "
        "reason_code, attempt, evidence_ref, payload_json) "
        "VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)",
        (
            event.event_id,
            event.inquiry_id,
            event.event_type.value,
            _time_text(event.occurred_at),
            event.source_module,
            _reason(event.reason_code),
            event.attempt,
            evidence_ref,
            json.dumps(safe_payload, sort_keys=True, separators=(",", ":")),
        ),
    )


def _raise_alert(
    connection: sqlite3.Connection,
    *,
    alert_id: str,
    inquiry_id: str,
    alert_type: AlertType,
    reason_code: ReasonCode,
    event_id: str,
    at: datetime,
    deduplicate_by_type: bool = False,
    scope_key: str = "",
) -> None:
    if deduplicate_by_type:
        existing = connection.execute(
            "SELECT alert_id FROM workflow_v12_active_alerts "
            "WHERE inquiry_id=? AND alert_type=? AND scope_key=? AND active=1 LIMIT 1",
            (inquiry_id, alert_type.value, scope_key),
        ).fetchone()
        if existing is not None:
            return
    connection.execute(
        "INSERT INTO workflow_v12_active_alerts "
        "(alert_id, inquiry_id, alert_type, reason_code, raised_event_id, active, raised_at, scope_key) "
        "VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
        (alert_id, inquiry_id, alert_type.value, reason_code.value, event_id, _time_text(at), scope_key),
    )


def _recover_alerts(
    connection: sqlite3.Connection,
    inquiry_id: str,
    alert_type: AlertType,
    event: WorkflowEvent,
    at: datetime,
    scope_key: str | None = None,
) -> None:
    scope_clause = "" if scope_key is None else " AND scope_key=?"
    parameters: tuple[object, ...] = (
        _time_text(at), event.event_id, inquiry_id, alert_type.value
    )
    if scope_key is not None:
        parameters += (scope_key,)
    cursor = connection.execute(
        "UPDATE workflow_v12_active_alerts SET active=0, recovered_at=?, recovered_by_event_id=? "
        "WHERE inquiry_id=? AND alert_type=? AND active=1" + scope_clause,
        parameters,
    )
    if cursor.rowcount == 0:
        return
    # A separate event preserves recovery in the append-only history.
    recovery_event = WorkflowEvent(
        _new_id("evt"), inquiry_id, EventType.ALERT_RECOVERED, at,
        "workflow", reason_code=event.reason_code,
    )
    _insert_event(connection, recovery_event)


def _all_recipients_sent(connection: sqlite3.Connection, command_id: str) -> bool:
    row = connection.execute(
        "SELECT count(*), sum(CASE WHEN outcome='SENT' THEN 1 ELSE 0 END) "
        "FROM workflow_v12_notification_recipients WHERE command_id=?",
        (command_id,),
    ).fetchone()
    return bool(row[0]) and row[0] == row[1]


def _transaction(database_path: Path):
    connection = _connect(database_path)

    class Transaction:
        def __enter__(self) -> sqlite3.Connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                return connection
            except Exception:
                connection.close()
                raise

        def __exit__(self, exc_type, exc, tb) -> None:
            try:
                if exc_type is None:
                    connection.commit()
                else:
                    connection.rollback()
            finally:
                connection.close()

    return Transaction()


def _connect(path: Path, *, read_only: bool = False) -> sqlite3.Connection:
    class ClosingConnection(sqlite3.Connection):
        def __exit__(self, exc_type, exc_value, traceback):
            try:
                return super().__exit__(exc_type, exc_value, traceback)
            finally:
                self.close()

    if read_only:
        connection = sqlite3.connect(
            f"{path.resolve().as_uri()}?mode=ro", uri=True, factory=ClosingConnection
        )
    else:
        connection = sqlite3.connect(path, timeout=30, factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def _verify_integrity(connection: sqlite3.Connection) -> None:
    results = tuple(row[0] for row in connection.execute("PRAGMA integrity_check"))
    if results != ("ok",):
        raise V12DatabaseError("backup integrity check failed")


def _fault(hook: FaultHook | None, stage: str, path: Path | None) -> None:
    if hook is not None:
        hook(stage, path)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _time_text(value: datetime | None) -> str | None:
    return None if value is None else _as_utc(value).isoformat()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _reason(value: ReasonCode | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, ReasonCode):
        raise TypeError("V1.2 reason code must be allowlisted")
    return value.value


def _as_reason(value: str | None) -> ReasonCode | None:
    return None if value is None else ReasonCode(value)


def _safe_ref(value: str | None) -> str | None:
    if value is None:
        return None
    if not _OPAQUE_REF.fullmatch(value):
        return None
    return value


def _fsync_file(path: Path) -> None:
    # Windows requires a writable descriptor for FlushFileBuffers/fsync.
    with path.open("r+b") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
