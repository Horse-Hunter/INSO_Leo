"""Opaque local completion receipts; no customer/contract/PI/message text."""
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


class FilledOrders:
    def __init__(self, root):
        self.path = Path(root) / "runtime" / "v14-filled.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS filled (identity TEXT PRIMARY KEY, filled_at TEXT NOT NULL)")

    def contains(self, identities):
        with sqlite3.connect(self.path) as db:
            return any(db.execute("SELECT 1 FROM filled WHERE identity=?", (key,)).fetchone() for key in identities)

    def mark(self, identities):
        if not identities:
            raise ValueError("MAIL_IDENTITY_REQUIRED")
        with sqlite3.connect(self.path) as db:
            for key in identities:
                db.execute("INSERT OR IGNORE INTO filled VALUES (?,?)", (key, datetime.now(UTC).isoformat()))
