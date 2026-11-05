"""Sales exceptions reuse V1.2 outbox/worker/1069 transport, old enums only."""
import hashlib
import json
import sqlite3
import threading
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path

from .store import WorkflowStateStore
from .v12_contracts import (
    DeliveryOutcome,
    NotificationCommand,
    NotificationKind,
    NotificationRecipient,
    NotificationTransportResult,
    ReasonCode,
)
from .v12_notifications import V12NotificationWorker
from .v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
from .v12_store import V12Store, migrate_v12

OWNER_ADDRESS = "linan229@qq.com"
RECIPIENTS = (NotificationRecipient("owner", OWNER_ADDRESS),)
MANUAL_ORDER_CODES = frozenset({"ICNET", "INSO", "MAIL", "PDF", "RECEIPT", "UPLOAD",
                                 "LEAD_TIME", "REQUIRED", "SELECTION", "STRUCTURE", "TYPE"})


def exception_command(*, invocation_id, pi_no, part_number=None, situation, treatment, at, event_code=None):
    pi = pi_no or "未能确认"
    lines = [f"订单：{pi}"]
    if part_number:
        lines.append(f"型号：{part_number}")
    lines.extend([f"情况：{situation}", f"处理：{treatment}"])
    proof = None
    if event_code is not None and event_code not in MANUAL_ORDER_CODES:
        raise ValueError("manual order notification reason is not classified")
    if event_code in MANUAL_ORDER_CODES:
        proof = json.dumps({"incident_key": "manual-order:"+invocation_id,
            "category": "manual_order", "module": "sales_order", "reason_code": "MANUAL_ORDER_NEEDS_REVIEW",
            "original_event": invocation_id, "invocation_id": invocation_id, "event_code": event_code,
            "manual_invocation": True, "automatic_stopped": True, "active": True,
            "current_business": True, "verified": True, "needs_owner": True,
            "verified_at": at.isoformat(), "invoked_at": at.isoformat(),
            "business_key": hashlib.sha256(str(pi_no).encode()).hexdigest() if pi_no else None,
            "action": treatment, "uncertainty": "本次手工录单已停止，请核对保留的页面；未自动保存或提交审核。"}, sort_keys=True)
    return NotificationCommand("v14-exception:" + invocation_id, "v14-notify:" + invocation_id,
        NotificationKind.PURCHASE_EXCEPTION, RECIPIENTS, f"订单录单异常｜{pi}",
        "\n".join(lines), None, at, 2 if proof else 1, proof)


class _OwnerOnlyTransport:
    """Latest Owner rule also applies to recipients persisted by older versions."""
    def __init__(self, transport):
        self.transport = transport

    def send_one(self, command, recipient):
        if recipient.address.strip().casefold() != OWNER_ADDRESS:
            # No SMTP dispatch or command rewrite; settle the obsolete recipient.
            return NotificationTransportResult(DeliveryOutcome.PERMANENT_FAILURE,
                                               ReasonCode.NOTIFICATION_PERMANENT)
        return self.transport.send_one(command, recipient)


class OrderExceptionNotifications:
    """Independent recipient retries, isolated dev DB; never inquiry state."""
    def __init__(self, root, *, transport=None, background=True):
        directory = Path(root) / ".tmp" / "v14-notifications"
        database = directory / "outbox.sqlite3"
        WorkflowStateStore(database)
        migrate_v12(database, directory / "backups", quiesce=lambda: nullcontext())
        self.store = V12Store(database)
        self.store.recover_abandoned_notification_attempts(at=datetime.now(UTC))
        self.worker = V12NotificationWorker(self.store, _OwnerOnlyTransport(transport or
            QQSMTPTransport(config=QQSMTPConfig(sender_address="1069599116@qq.com"))), review_current=self._review_current)
        self._stop = threading.Event()
        self._thread = None
        if background:
            self._thread = threading.Thread(target=self._run, name="v14-notification-outbox", daemon=True)
            self._thread.start()

    def _review_current(self, command, now):
        from .automatic_admission import age_reason
        proof = json.loads(command.review or "{}")
        if (proof.get("category") != "manual_order"
                or command.recipients != RECIPIENTS):
            return "RECIPIENT_NOT_CONFIGURED"
        with sqlite3.connect(self.store.database_path) as db:
            row = db.execute("SELECT status,created_at FROM workflow_items WHERE inquiry_id=?",
                             (command.inquiry_id,)).fetchone()
        if row is None or row[0] != "MANUAL_REVIEW":
            return "EVENT_RECOVERED"
        if age_reason(row[1], now, module="inquiry"):
            return "ORDER_AGE_EXCLUDED"
        return None

    def resolve_order(self, pi_no, *, at):
        """Retire only mail evidence after verified manual preparation; no order mutation."""
        if not pi_no:
            return
        business_key = hashlib.sha256(str(pi_no).encode()).hexdigest()
        with sqlite3.connect(self.store.database_path) as db:
            for cid, payload in db.execute("SELECT command_id,review_json FROM workflow_v12_notification_commands").fetchall():
                try:
                    proof = json.loads(payload or "{}")
                except (TypeError, ValueError):
                    continue
                if not isinstance(proof, dict):
                    continue
                if (proof.get("category") == "manual_order" and proof.get("business_key") == business_key
                        and proof.get("active") is True):
                    proof.update(active=False, recovered_at=at.isoformat())
                    db.execute("UPDATE workflow_v12_notification_commands SET review_json=? WHERE command_id=?",
                               (json.dumps(proof, sort_keys=True), cid))

    def enqueue(self, command):
        # Existing schema requires a V1 FK parent. Keep a notification-only anchor
        # in this isolated DB, MANUAL_REVIEW (never eligible for inquiry claiming).
        # No V1.2 purchase/quotation state is created or modified.
        with sqlite3.connect(self.store.database_path) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO workflow_items (spreadsheet,worksheet,row_number,inquiry_id,"
                "record_identity_json,mpn_json,brand_json,quantity_json,importance_raw_json,"
                "status,created_at,updated_at) VALUES ('v14-notifications','outbox',?,?,"
                "'{}','null','null','null','null','MANUAL_REVIEW',?,?)",
                (int(hashlib.sha256(command.inquiry_id.encode()).hexdigest()[:12],16),
                 command.inquiry_id, command.created_at.isoformat(), command.created_at.isoformat()))
        self.store.enqueue_notification(command)

    def notify(self, **kwargs):
        command = exception_command(**kwargs)
        self.enqueue(command)
        self.worker.run_due(now=datetime.now(UTC))

    def _run(self):
        while not self._stop.is_set():
            try:
                self.worker.run_due(now=datetime.now(UTC))
            except Exception:  # noqa: BLE001, S110 - keep queued notification, never log payload
                pass
            self._stop.wait(5)

    def close(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(35)
