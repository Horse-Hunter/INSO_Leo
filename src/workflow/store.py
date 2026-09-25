"""SQLite-backed Workflow V1 state store."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.research import ResearchResult, ResearchStatus
from src.sheets import (
    IdentifyingSnapshot,
    PendingSheetRecord,
    SheetRecordIdentity,
    WorksheetIdentity,
)

from .models import WorkflowStatus, WorkItem

UTC = timezone.utc
DEFAULT_RETRY_DELAYS: tuple[timedelta, ...] = (
    timedelta(minutes=15),
    timedelta(minutes=30),
    timedelta(minutes=60),
)


class WorkflowStateStore:
    """Own durable deduplication, claiming, transitions, and restart state."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spreadsheet TEXT NOT NULL,
                    worksheet TEXT NOT NULL,
                    row_number INTEGER NOT NULL,
                    inquiry_id TEXT NOT NULL UNIQUE,
                    record_identity_json TEXT NOT NULL,
                    mpn_json TEXT NOT NULL,
                    brand_json TEXT NOT NULL,
                    quantity_json TEXT NOT NULL,
                    importance_raw_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN (
                        'QUEUED', 'RESEARCHING', 'RETRY_WAIT',
                        'COMPLETED', 'MANUAL_REVIEW', 'FAILED'
                    )),
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    next_attempt_at TEXT,
                    research_status TEXT,
                    resolved_brand TEXT,
                    brand_update_status TEXT,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE (spreadsheet, worksheet, row_number)
                )
                """
            )

    def enqueue(
        self,
        record: PendingSheetRecord,
        *,
        now: datetime | None = None,
    ) -> bool:
        observed_at = _as_utc(now or datetime.now(UTC))
        identity = record.record_identity
        key = _dedup_key(identity)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO workflow_items (
                    spreadsheet, worksheet, row_number, inquiry_id,
                    record_identity_json, mpn_json, brand_json, quantity_json,
                    importance_raw_json, status, next_attempt_at,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    identity.worksheet.spreadsheet,
                    identity.worksheet.worksheet,
                    identity.row_position,
                    _inquiry_id(key),
                    _identity_to_json(identity),
                    _value_to_json(record.model),
                    _value_to_json(record.brand),
                    _value_to_json(record.quantity),
                    _value_to_json(record.importance_raw),
                    WorkflowStatus.QUEUED.value,
                    _time_to_text(observed_at),
                    _time_to_text(observed_at),
                    _time_to_text(observed_at),
                ),
            )
            return cursor.rowcount == 1

    def claim_due(self, *, now: datetime | None = None) -> WorkItem | None:
        claimed_at = _as_utc(now or datetime.now(UTC))
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT * FROM workflow_items
                WHERE status IN ('QUEUED', 'RETRY_WAIT')
                  AND next_attempt_at <= ?
                ORDER BY next_attempt_at, id
                LIMIT 1
                """,
                (_time_to_text(claimed_at),),
            ).fetchone()
            if row is None:
                connection.commit()
                return None
            connection.execute(
                """
                UPDATE workflow_items
                SET status = 'RESEARCHING', attempt_count = attempt_count + 1,
                    next_attempt_at = NULL, updated_at = ?
                WHERE id = ?
                """,
                (_time_to_text(claimed_at), row["id"]),
            )
            refreshed = connection.execute(
                "SELECT * FROM workflow_items WHERE id = ?", (row["id"],)
            ).fetchone()
            connection.commit()
            return _row_to_item(refreshed)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def researching_items(self) -> tuple[WorkItem, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM workflow_items WHERE status = 'RESEARCHING' ORDER BY id"
            ).fetchall()
        return tuple(_row_to_item(row) for row in rows)

    def apply_research_result(
        self,
        item_id: int,
        result: ResearchResult,
        *,
        now: datetime | None = None,
        retry_delays: Sequence[timedelta] = DEFAULT_RETRY_DELAYS,
    ) -> WorkflowStatus:
        changed_at = _as_utc(now or datetime.now(UTC))
        item = self.get(item_id)
        if result.inquiry_id != item.inquiry_id:
            return self.schedule_retry(
                item_id,
                error="Research returned a different inquiry_id",
                now=changed_at,
                retry_delays=retry_delays,
            )
        if result.status in {ResearchStatus.SUCCESS, ResearchStatus.PARTIAL_SUCCESS}:
            target = WorkflowStatus.COMPLETED
            last_error = None
        elif result.status is ResearchStatus.EXCEPTION:
            target = WorkflowStatus.FAILED
            last_error = (
                result.reason_code.value
                if result.reason_code is not None
                else result.status.value
            )
        else:
            return self.schedule_retry(
                item_id,
                error=result.reason_code or result.status,
                now=changed_at,
                retry_delays=retry_delays,
                research_status=result.status.value,
                resolved_brand=result.resolved_brand,
            )
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE workflow_items
                SET status = ?, research_status = ?, resolved_brand = ?,
                    next_attempt_at = NULL, last_error = ?, updated_at = ?
                WHERE id = ? AND status = 'RESEARCHING'
                """,
                (
                    target.value,
                    result.status.value,
                    result.resolved_brand,
                    last_error,
                    _time_to_text(changed_at),
                    item_id,
                ),
            )
        return target

    def schedule_retry(
        self,
        item_id: int,
        *,
        error: object,
        now: datetime | None = None,
        retry_delays: Sequence[timedelta] = DEFAULT_RETRY_DELAYS,
        research_status: str | None = None,
        resolved_brand: str | None = None,
    ) -> WorkflowStatus:
        changed_at = _as_utc(now or datetime.now(UTC))
        item = self.get(item_id)
        if item.attempt_count <= len(retry_delays):
            target = WorkflowStatus.RETRY_WAIT
            next_attempt_at = changed_at + retry_delays[item.attempt_count - 1]
        else:
            target = WorkflowStatus.FAILED
            next_attempt_at = None
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE workflow_items
                SET status = ?, next_attempt_at = ?, research_status = ?,
                    resolved_brand = COALESCE(?, resolved_brand), last_error = ?,
                    updated_at = ?
                WHERE id = ? AND status = 'RESEARCHING'
                """,
                (
                    target.value,
                    _time_to_text(next_attempt_at),
                    research_status,
                    resolved_brand,
                    _safe_last_error(error, research_status),
                    _time_to_text(changed_at),
                    item_id,
                ),
            )
        return target

    def release_unprepared(
        self,
        item_id: int,
        *,
        now: datetime | None = None,
    ) -> None:
        """Undo a claim when launcher setup failed before Research executed."""

        changed_at = _as_utc(now or datetime.now(UTC))
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE workflow_items
                SET status = 'QUEUED',
                    attempt_count = CASE
                        WHEN attempt_count > 0 THEN attempt_count - 1
                        ELSE 0
                    END,
                    next_attempt_at = ?,
                    last_error = 'Research preparation requires manual handling',
                    updated_at = ?
                WHERE id = ? AND status = 'RESEARCHING'
                """,
                (_time_to_text(changed_at), _time_to_text(changed_at), item_id),
            )

    def record_brand_update(
        self,
        item_id: int,
        status: str,
        *,
        error: object | None = None,
        now: datetime | None = None,
    ) -> None:
        changed_at = _as_utc(now or datetime.now(UTC))
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE workflow_items
                SET brand_update_status = ?, last_error = COALESCE(?, last_error),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    None if error is None else _safe_brand_error(status),
                    _time_to_text(changed_at),
                    item_id,
                ),
            )

    def get(self, item_id: int) -> WorkItem:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM workflow_items WHERE id = ?", (item_id,)
            ).fetchone()
        if row is None:
            raise KeyError(item_id)
        return _row_to_item(row)

    def get_by_inquiry_id(self, inquiry_id: str) -> WorkItem:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM workflow_items WHERE inquiry_id = ?", (inquiry_id,)
            ).fetchone()
        if row is None:
            raise KeyError(inquiry_id)
        return _row_to_item(row)

    def all_items(self) -> tuple[WorkItem, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM workflow_items ORDER BY id"
            ).fetchall()
        return tuple(_row_to_item(row) for row in rows)


def _dedup_key(identity: SheetRecordIdentity) -> str:
    return "\x1f".join(
        (
            identity.worksheet.spreadsheet,
            identity.worksheet.worksheet,
            str(identity.row_position),
        )
    )


def _safe_last_error(error: object, research_status: str | None) -> str:
    """Persist only a fixed status or an exception class name, never its message."""

    if research_status is not None:
        return research_status
    if isinstance(error, BaseException):
        return type(error).__name__
    return "WORKFLOW_RETRY"


def _safe_brand_error(status: str) -> str:
    return {
        "CONFLICT": "BRAND_UPDATE_CONFLICT",
        "FAILED": "BRAND_UPDATE_FAILED",
    }.get(status, "BRAND_UPDATE_FAILED")


def _inquiry_id(key: str) -> str:
    return "inq_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def _identity_to_json(identity: SheetRecordIdentity) -> str:
    snapshot = identity.identifying_snapshot
    return json.dumps(
        {
            "spreadsheet": identity.worksheet.spreadsheet,
            "worksheet": identity.worksheet.worksheet,
            "row_position": identity.row_position,
            "snapshot": {
                "status": snapshot.status,
                "importance_raw": snapshot.importance_raw,
                "model": snapshot.model,
                "brand": snapshot.brand,
                "quantity": snapshot.quantity,
            },
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _identity_from_json(value: str) -> SheetRecordIdentity:
    payload = json.loads(value)
    snapshot = payload["snapshot"]
    return SheetRecordIdentity(
        worksheet=WorksheetIdentity(payload["spreadsheet"], payload["worksheet"]),
        row_position=payload["row_position"],
        identifying_snapshot=IdentifyingSnapshot(
            status=snapshot["status"],
            importance_raw=snapshot["importance_raw"],
            model=snapshot["model"],
            brand=snapshot["brand"],
            quantity=snapshot["quantity"],
        ),
    )


def _value_to_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _row_to_item(row: sqlite3.Row) -> WorkItem:
    return WorkItem(
        id=row["id"],
        inquiry_id=row["inquiry_id"],
        record_identity=_identity_from_json(row["record_identity_json"]),
        mpn=json.loads(row["mpn_json"]),
        brand=json.loads(row["brand_json"]),
        quantity=json.loads(row["quantity_json"]),
        importance_raw=json.loads(row["importance_raw_json"]),
        status=WorkflowStatus(row["status"]),
        attempt_count=row["attempt_count"],
        next_attempt_at=_text_to_time(row["next_attempt_at"]),
        research_status=row["research_status"],
        resolved_brand=row["resolved_brand"],
        brand_update_status=row["brand_update_status"],
        last_error=row["last_error"],
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Workflow timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _time_to_text(value: datetime | None) -> str | None:
    return None if value is None else _as_utc(value).isoformat()


def _text_to_time(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)
