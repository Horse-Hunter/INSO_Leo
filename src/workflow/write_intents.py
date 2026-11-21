"""Durable write-intent journal for Google documents (RFQ-021 / B6).

The in-process document hold is enough to serialise writers inside one process,
but it dies with that process. A restart therefore used to forget that a request
may already be in flight. This journal keeps the intent on disk:

* an intent row is committed **before** the external request is dispatched;
* it is settled only when the caller has evidence, never on a timeout;
* an unreadable, unwritable or missing ledger refuses every write (fail closed).

The journal never decides a business outcome. It only makes an unknown write
survive the process that produced it, so the next process refuses to write to
the same document until a human reconciles it.
"""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone

PENDING = "PENDING"
UNKNOWN = "UNKNOWN"
SETTLED = "SETTLED"
_OPEN_STATES = (PENDING, UNKNOWN)


class WriteLedgerUnavailable(RuntimeError):
    """The safety ledger cannot be trusted; every write must be refused."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteWriteIntentJournal:
    """Additive table in the existing workflow DB; no engine change."""

    def __init__(self, path) -> None:
        self._path = str(path)

    def migrate(self) -> None:
        try:
            with closing(sqlite3.connect(self._path)) as db, db:
                db.execute(
                    """CREATE TABLE IF NOT EXISTS workflow_write_intents (
                        intent_id TEXT PRIMARY KEY,
                        document_key TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        state TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        settled_at TEXT,
                        reason TEXT)"""
                )
                db.execute(
                    """CREATE INDEX IF NOT EXISTS workflow_write_intents_open
                        ON workflow_write_intents(document_key, state)"""
                )
        except sqlite3.Error as exc:
            raise WriteLedgerUnavailable(type(exc).__name__) from None

    def begin(self, document_key: str, kind: str) -> str:
        """Commit the intent before the caller dispatches anything."""
        intent_id = "wi_" + uuid.uuid4().hex
        try:
            with closing(sqlite3.connect(self._path)) as db, db:
                db.execute(
                    "INSERT INTO workflow_write_intents"
                    " (intent_id, document_key, kind, state, created_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (intent_id, str(document_key), str(kind), PENDING, _now()),
                )
        except sqlite3.Error as exc:
            raise WriteLedgerUnavailable(type(exc).__name__) from None
        return intent_id

    def settle(self, intent_id: str) -> None:
        """Record a confirmed outcome. No-op if the row already settled."""
        try:
            with closing(sqlite3.connect(self._path)) as db, db:
                db.execute(
                    "UPDATE workflow_write_intents SET state=?, settled_at=?"
                    " WHERE intent_id=? AND state IN (?, ?)",
                    (SETTLED, _now(), intent_id, PENDING, UNKNOWN),
                )
        except sqlite3.Error as exc:
            raise WriteLedgerUnavailable(type(exc).__name__) from None

    def mark_unknown(self, intent_id: str, reason: str) -> None:
        """Keep the intent open; this is what survives a crash or timeout."""
        try:
            with closing(sqlite3.connect(self._path)) as db, db:
                db.execute(
                    "UPDATE workflow_write_intents SET state=?, reason=?"
                    " WHERE intent_id=? AND state IN (?, ?)",
                    (UNKNOWN, str(reason)[:120], intent_id, PENDING, UNKNOWN),
                )
        except sqlite3.Error as exc:
            raise WriteLedgerUnavailable(type(exc).__name__) from None

    def open_reason(self, document_key: str) -> str | None:
        """Reason why this document is still unsafe to write, if it is."""
        try:
            with closing(sqlite3.connect(self._path)) as db:
                row = db.execute(
                    "SELECT state, reason FROM workflow_write_intents"
                    " WHERE document_key=? AND state IN (?, ?)"
                    " ORDER BY created_at LIMIT 1",
                    (str(document_key), PENDING, UNKNOWN),
                ).fetchone()
        except sqlite3.Error as exc:
            raise WriteLedgerUnavailable(type(exc).__name__) from None
        if row is None:
            return None
        state, reason = row
        return f"WRITE_INTENT_{state}" + (f":{reason}" if reason else "")

    def open_documents(self) -> dict[str, str]:
        """Every document still carrying an unsettled write intent."""
        try:
            with closing(sqlite3.connect(self._path)) as db:
                rows = db.execute(
                    "SELECT document_key, state FROM workflow_write_intents"
                    " WHERE state IN (?, ?)",
                    (PENDING, UNKNOWN),
                ).fetchall()
        except sqlite3.Error as exc:
            raise WriteLedgerUnavailable(type(exc).__name__) from None
        return {str(key): f"WRITE_INTENT_{state}" for key, state in rows}
