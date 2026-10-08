"""V1.3-only additive episodes; old V1.2 tables/enums/version are untouched."""
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .v12_faults import FaultScope, V12Fault
from .v12_store import V12DatabaseError, create_verified_backup

TABLE = "workflow_v13_purchase_follow_up_episodes"


@dataclass(frozen=True, slots=True)
class ConfirmedPurchaseEpisode:
    episode_id: str
    inquiry_id: str
    confirmed_at: datetime


class V13PurchaseFollowUpStore:
    """Canonical inquiry FK plus sending time/id; no copied business snapshot."""
    def __init__(self, path):
        self.path = Path(path)

    def _connect(self):
        if not self.path.is_file():
            raise V12DatabaseError("workflow ledger missing")
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def migrate(self):
        try:
            with self._connect() as db:
                present = db.execute("SELECT 1 FROM sqlite_master WHERE name=?", (TABLE,)).fetchone()
            if not present:
                create_verified_backup(self.path, self.path.parent / "backups" / "v13-follow-up-upgrade")
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
                    episode_id TEXT PRIMARY KEY,
                    inquiry_id TEXT NOT NULL REFERENCES workflow_items(inquiry_id) ON DELETE RESTRICT,
                    confirmed_at TEXT NOT NULL)""")
                columns = {row[1] for row in db.execute(f"PRAGMA table_info({TABLE})")}
                if columns != {"episode_id", "inquiry_id", "confirmed_at"}:
                    raise V12DatabaseError("follow-up sidecar schema invalid")
                db.execute(f"CREATE INDEX IF NOT EXISTS workflow_v13_follow_up_inquiry ON {TABLE}(inquiry_id)")
        except (sqlite3.Error, V12DatabaseError):
            raise V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE") from None

    def record_confirmed(self, inquiry_id, *, confirmed_at):
        """Only called after a fresh changed=True status write/readback."""
        try:
            if confirmed_at.tzinfo is None:
                raise ValueError("confirmed timestamp must be timezone-aware")
            episode = ConfirmedPurchaseEpisode("episode_" + uuid.uuid4().hex, inquiry_id,
                                               confirmed_at.astimezone(UTC))
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute(f"INSERT INTO {TABLE} VALUES (?,?,?)", (
                    episode.episode_id, inquiry_id, episode.confirmed_at.isoformat()))
            return episode
        except (sqlite3.Error, V12DatabaseError, ValueError):
            raise V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE") from None

    def latest(self, inquiry_id):
        try:
            with self._connect() as db:
                row = db.execute(f"SELECT episode_id,inquiry_id,confirmed_at FROM {TABLE} "
                                 "WHERE inquiry_id=? ORDER BY rowid DESC LIMIT 1", (inquiry_id,)).fetchone()
            if row is None:
                return None
            stamp = datetime.fromisoformat(row[2])
            if stamp.tzinfo is None:
                raise ValueError("invalid local confirmed timestamp")
            return ConfirmedPurchaseEpisode(row[0], row[1], stamp)
        except (sqlite3.Error, V12DatabaseError, ValueError):
            raise V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE") from None
