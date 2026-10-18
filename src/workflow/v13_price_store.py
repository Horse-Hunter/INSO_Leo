"""Minimal local procurement baseline keyed by the canonical inquiry identity."""
import sqlite3
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .v12_faults import FaultScope, V12Fault
from .v12_store import V12DatabaseError, create_verified_backup

TABLE = "workflow_v13_procurement_prices"


class ProcurementPriceStore:
    def __init__(self, path):
        self.path = Path(path)

    def _connect(self):
        if not self.path.is_file():
            raise V12DatabaseError("workflow ledger missing")
        db = sqlite3.connect(self.path)
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def migrate(self):
        try:
            with self._connect() as db:
                present = db.execute("SELECT 1 FROM sqlite_master WHERE name=?", (TABLE,)).fetchone()
            if not present:
                create_verified_backup(self.path, self.path.parent / "backups" / "v13-price-upgrade")
            with self._connect() as db:
                db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
                    inquiry_id TEXT PRIMARY KEY REFERENCES workflow_items(inquiry_id) ON DELETE RESTRICT,
                    price_rmb TEXT NOT NULL)""")
                if {r[1] for r in db.execute(f"PRAGMA table_info({TABLE})")} != {"inquiry_id", "price_rmb"}:
                    raise V12DatabaseError("procurement baseline schema invalid")
        except (sqlite3.Error, V12DatabaseError):
            raise V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE") from None

    def get(self, inquiry_id):
        try:
            with self._connect() as db:
                row = db.execute(f"SELECT price_rmb FROM {TABLE} WHERE inquiry_id=?", (inquiry_id,)).fetchone()
            if row is None:
                return None
            value = Decimal(row[0])
            if not value.is_finite() or value < 0:
                raise ValueError
            return value
        except (sqlite3.Error, V12DatabaseError, InvalidOperation, ValueError):
            raise V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE") from None

    def record(self, inquiry_id, price):
        """Bootstrap or verified success only; positive minimum never regresses."""
        if not isinstance(price, Decimal) or not price.is_finite() or price < 0:
            raise ValueError("invalid procurement baseline")
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(f"SELECT price_rmb FROM {TABLE} WHERE inquiry_id=?", (inquiry_id,)).fetchone()
                if row is not None:
                    old = Decimal(row[0])
                    if not old.is_finite() or old < 0:
                        raise ValueError
                    if old > 0 and (price == 0 or price >= old):
                        return
                db.execute(f"INSERT INTO {TABLE} VALUES (?,?) ON CONFLICT(inquiry_id) "
                           "DO UPDATE SET price_rmb=excluded.price_rmb", (inquiry_id, str(price)))
        except (sqlite3.Error, V12DatabaseError, InvalidOperation, ValueError):
            raise V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE") from None
