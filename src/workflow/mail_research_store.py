"""Independent request identities in the original SQLite database; no business rows."""
import json
import sqlite3
from contextlib import contextmanager
from hashlib import sha256

from src.order_mail.research_requests import ACCOUNT, TRIGGER_POLICY

from .v12_store import create_verified_backup


class MailResearchStore:
    def __init__(self, path, *, capacity=64):
        self.path, self.capacity = path, capacity

    @contextmanager
    def connect(self, *, timeout=10):
        db = sqlite3.connect(self.path, timeout=timeout)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def migrate(self):
        with self.connect() as db:
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='workflow_mail_research'").fetchone()
        if not exists:
            create_verified_backup(self.path, self.path.parent / "backups" / "mail-research-upgrade")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS workflow_mail_cursor (account TEXT PRIMARY KEY, validity INTEGER NOT NULL, last_uid INTEGER NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS workflow_mail_research (
                task_id TEXT PRIMARY KEY, origin TEXT NOT NULL, payload TEXT NOT NULL,
                state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, next_at TEXT,
                progress TEXT NOT NULL DEFAULT '{}', report TEXT, failure TEXT,
                created_at TEXT NOT NULL)""")
            db.execute("CREATE INDEX IF NOT EXISTS workflow_mail_research_pending ON workflow_mail_research(state,created_at)")
            db.execute("CREATE INDEX IF NOT EXISTS workflow_mail_research_delivery ON workflow_mail_research(origin,state,created_at)")
            db.execute("UPDATE workflow_mail_research SET state='PENDING' WHERE state='RUNNING'")

    def resource_blocked(self):
        with self.connect() as db:
            return db.execute("SELECT 1 FROM workflow_mail_research WHERE task_id='mail-research:resource-health' AND state='RESOURCE_BLOCKED'").fetchone() is not None

    def block_resource(self, now):
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO workflow_mail_research (task_id,origin,payload,state,created_at) VALUES ('mail-research:resource-health','health','{}','RESOURCE_BLOCKED',?)", (now.isoformat(),))

    def cursor(self, account):
        with self.connect() as db:
            row = db.execute("SELECT validity,last_uid FROM workflow_mail_cursor WHERE account=?", (account,)).fetchone()
        return tuple(row) if row else None

    def establish_subject_baseline(self, account, validity, latest):
        """One atomic policy activation; existing blocked UID backlog is history.

        The second cursor row is a durable policy marker, not another mailbox.
        Subsequent restarts keep normal UID progress and accepted task identity.
        """
        if account != ACCOUNT:
            raise ValueError("IMAP_ACCOUNT_UNCONFIRMED")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            marker = "policy:"+TRIGGER_POLICY+":"+account
            if db.execute("SELECT 1 FROM workflow_mail_cursor WHERE account=?", (marker,)).fetchone():
                return False
            db.execute("INSERT INTO workflow_mail_cursor VALUES (?,?,?)", (marker, validity, latest))
            db.execute("INSERT OR REPLACE INTO workflow_mail_cursor VALUES (?,?,?)", (account, validity, latest))
            return True

    def admitted_subject_request(self, job):
        """Recheck persisted origin, policy, UID binding and activation boundary."""
        try:
            payload = json.loads(job["payload"])
            if job["origin"] != "imap" or payload.get("trigger_policy") != TRIGGER_POLICY or payload.get("account") != ACCOUNT:
                return False
            validity, uid, after = (payload[k] for k in ("uid_validity", "uid", "after_uid"))
            if any(type(n) is not int for n in (validity, uid, after)) or validity <= 0 or not 0 <= after < uid:
                return False
            expected = "mail-research:"+sha256(f"{ACCOUNT}:{validity}:{uid}".encode()).hexdigest()
            if job["task_id"] != expected:
                return False
            from src.order_mail.research_requests import parse_research_subject
            if parse_research_subject("调研 "+payload["mpn"]) != payload["mpn"]:
                return False
            marker = self.cursor("policy:"+TRIGGER_POLICY+":"+ACCOUNT)
            return marker is not None and (validity != marker[0] or uid > marker[1])
        except (ValueError, TypeError, KeyError):
            return False

    @staticmethod
    def _active_count(db):
        # A report awaiting SMTP is still queued work, not a completed request.
        return db.execute("""SELECT count(*) FROM workflow_mail_research m WHERE
            (m.state IN ('PENDING','RUNNING','BLOCKED') AND (m.origin!='imap' OR
                CASE WHEN json_valid(m.payload) THEN json_extract(m.payload,'$.trigger_policy') END='subject-only-v1')) OR
            (m.origin='imap' AND m.state='READY' AND
                CASE WHEN json_valid(m.payload) THEN json_extract(m.payload,'$.trigger_policy') END='subject-only-v1' AND NOT EXISTS (
                SELECT 1 FROM workflow_v12_notification_recipients r
                WHERE r.command_id=m.task_id AND r.outcome IN ('SENT','UNKNOWN','PERMANENT_FAILURE','SUPPRESSED')))""").fetchone()[0]

    def accept_scan(self, account, validity, upper, messages, now):
        """Request insert + high-water advance are one transaction. Full => retry range."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT validity,last_uid FROM workflow_mail_cursor WHERE account=?", (account,)).fetchone()
            if previous is None or previous[0] != validity:
                db.execute("INSERT OR REPLACE INTO workflow_mail_cursor VALUES (?,?,?)", (account, validity, upper))
                return 0  # Reset is a new baseline, never replay the previous epoch.
            count = self._active_count(db)
            added = 0
            for uid, mail in messages:
                if mail.trigger_policy != TRIGGER_POLICY or uid <= previous[1]:
                    continue
                key = "mail-research:" + sha256(f"{account}:{validity}:{uid}".encode()).hexdigest()
                if db.execute("SELECT 1 FROM workflow_mail_research WHERE task_id=?", (key,)).fetchone():
                    continue
                if count + added >= self.capacity:
                    return added  # Cursor stays; duplicates safely skipped next scan.
                from dataclasses import asdict
                payload = {**asdict(mail), "account": account, "uid_validity": validity, "uid": uid, "after_uid": previous[1]}
                db.execute("INSERT INTO workflow_mail_research (task_id,origin,payload,state,created_at) VALUES (?,?,?,'PENDING',?)",
                    (key, "imap", json.dumps(payload), now.isoformat()))
                added += 1
            db.execute("UPDATE workflow_mail_cursor SET last_uid=? WHERE account=?", (max(upper, previous[1]), account))
            return added

    def request_business(self, command, order, now):
        from dataclasses import asdict
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if self._active_count(db) >= self.capacity:
                return False
            db.execute("INSERT OR IGNORE INTO workflow_mail_research (task_id,origin,payload,state,created_at) VALUES (?,?,?,'PENDING',?)",
                (command.command_id, "business", json.dumps(asdict(order)), now.isoformat()))
            return True

    @staticmethod
    def _recovery_key(command_id):
        return "business-recovery:" + command_id

    def defer_business_recovery(self, command_id, now, *, deadline):
        from time import monotonic
        with self.connect(timeout=0.1) as db:
            db.set_progress_handler(lambda: int(monotonic() >= deadline), 1000)
            db.execute("BEGIN IMMEDIATE")
            key = self._recovery_key(command_id)
            db.execute("INSERT OR IGNORE INTO workflow_mail_research (task_id,origin,payload,state,created_at) VALUES (?,'business-recovery',?,'RECOVERY_WAIT',?)",
                       (key, json.dumps({"original": command_id}), now.isoformat()))
            self._defer_recovery_row(db, key, now)

    @staticmethod
    def _defer_recovery_row(db, key, now):
        """Bound transient recovery checks independently of actual research attempts."""
        from datetime import timedelta

        row = db.execute("SELECT progress,payload FROM workflow_mail_research WHERE task_id=? AND state='RECOVERY_WAIT' AND (next_at IS NULL OR next_at<=?)", (key, now.isoformat())).fetchone()
        if row is None:
            return
        try:
            progress = json.loads(row[0] or "{}")
            count = int(progress.get("deferrals", 0)) + 1
        except (ValueError, TypeError, AttributeError):
            count = 3
        # Notification creation time does not prove source age; manual requests
        # may be age-exempt. Keep UNKNOWN deferred until source can be reviewed.
        delay = min(900, 60 * 2**min(count-1, 4))
        db.execute("UPDATE workflow_mail_research SET progress=?,next_at=? WHERE task_id=?",
                   (json.dumps({"deferrals": count}), (now+timedelta(seconds=delay)).isoformat(), key))

    def schedule_business_recovery(self, command, recipient, order, now, *, deadline, expected_state, expected_report):
        """Recreate or retry one eligible job; durable backoff never clears holds."""
        from dataclasses import asdict
        from datetime import timedelta
        from time import monotonic

        with self.connect(timeout=0.1) as db:
            db.set_progress_handler(lambda: int(monotonic() >= deadline), 1000)
            db.execute("BEGIN IMMEDIATE")
            recipient_row = db.execute("SELECT address,outcome FROM workflow_v12_notification_recipients WHERE command_id=? AND recipient_id=?",
                                       (command.command_id, recipient.recipient_id)).fetchone()
            if recipient_row is None or recipient_row[0] != recipient.address or recipient_row[1] != "SENT":
                return False
            key = self._recovery_key(command.command_id)
            db.execute("INSERT OR IGNORE INTO workflow_mail_research (task_id,origin,payload,state,created_at) VALUES (?,'business-recovery',?,'RECOVERY_WAIT',?)",
                       (key, json.dumps({"original": command.command_id}), now.isoformat()))
            control = db.execute("SELECT state,attempts,next_at FROM workflow_mail_research WHERE task_id=?", (key,)).fetchone()
            if (control is None or control[0] != "RECOVERY_WAIT" or control[1] >= 3
                    or control[2] is not None and control[2] > now.isoformat()):
                return False
            if db.execute("SELECT 1 FROM workflow_mail_research WHERE task_id='mail-research:resource-health' AND state='RESOURCE_BLOCKED'").fetchone():
                self._defer_recovery_row(db, key, now)
                return False
            job = db.execute("SELECT origin,payload,state,next_at,report FROM workflow_mail_research WHERE task_id=?", (command.command_id,)).fetchone()
            if (job is None) != (expected_state is None):
                self._defer_recovery_row(db, key, now)
                return False
            if job is not None and (job[0] != "business" or job[2] not in {"READY", "FAILED"}
                    or job[2] != expected_state or job[4] != expected_report
                    or json.loads(job[1]) != asdict(order) or job[3] is not None and job[3] > now.isoformat()):
                self._defer_recovery_row(db, key, now)
                return False
            if self._active_count(db) >= self.capacity:
                self._defer_recovery_row(db, key, now)
                return False
            if job is None:
                db.execute("INSERT INTO workflow_mail_research (task_id,origin,payload,state,created_at) VALUES (?,'business',?,'PENDING',?)",
                           (command.command_id, json.dumps(asdict(order)), now.isoformat()))
            else:
                db.execute("UPDATE workflow_mail_research SET state='PENDING',progress='{}',report=NULL,failure=NULL,next_at=NULL WHERE task_id=? AND origin='business' AND state IN ('READY','FAILED')",
                           (command.command_id,))
            db.execute("UPDATE workflow_mail_research SET attempts=attempts+1,next_at=? WHERE task_id=?",
                       ((now+timedelta(minutes=15)).isoformat(), key))
            return True

    def get(self, key):
        with self.connect() as db:
            row = db.execute("SELECT * FROM workflow_mail_research WHERE task_id=?", (key,)).fetchone()
        return dict(row) if row else None

    def claim(self, now):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM workflow_mail_research WHERE state='PENDING' AND (origin!='imap' OR CASE WHEN json_valid(payload) THEN json_extract(payload,'$.trigger_policy') END='subject-only-v1') AND (next_at IS NULL OR next_at<=?) ORDER BY created_at,task_id LIMIT 1", (now.isoformat(),)).fetchone()
            if row is None:
                return None
            db.execute("UPDATE workflow_mail_research SET state='RUNNING' WHERE task_id=?", (row["task_id"],))
            return dict(row)

    def checkpoint(self, key, progress):
        encoded = json.dumps(progress)
        if len(encoded) > 131072:
            raise ValueError("REPORT_FACT_BUDGET_EXCEEDED")
        with self.connect() as db:
            db.execute("UPDATE workflow_mail_research SET progress=? WHERE task_id=?", (encoded, key))

    def refresh_business(self, key):
        with self.connect() as db:
            db.execute("UPDATE workflow_mail_research SET state='PENDING',progress='{}',report=NULL,attempts=0,next_at=NULL WHERE task_id=? AND origin='business' AND state='READY'", (key,))

    def close_delivery(self, key, outcome):
        if outcome not in {"SENT", "UNKNOWN", "PERMANENT_FAILURE", "SUPPRESSED"}:
            return
        with self.connect() as db:
            db.execute("UPDATE workflow_mail_research SET state=? WHERE task_id=? AND origin='imap' AND state='READY'", ("DELIVERY_"+outcome, key))

    def finish(self, key, *, state, report=None, failure=None, next_at=None):
        with self.connect() as db:
            db.execute("UPDATE workflow_mail_research SET state=?,report=?,failure=?,next_at=?,attempts=attempts+? WHERE task_id=?",
                       (state, json.dumps(report) if report else None, failure, next_at.isoformat() if next_at else None, int(failure is not None), key))
