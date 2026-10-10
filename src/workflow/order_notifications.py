"""Sales exceptions reuse V1.2 outbox/worker/1069 transport, old enums only."""
import hashlib
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


def exception_command(*, invocation_id, pi_no, part_number=None, situation, treatment, at):
    pi = pi_no or "未能确认"
    lines = [f"订单：{pi}"]
    if part_number:
        lines.append(f"型号：{part_number}")
    lines.extend([f"情况：{situation}", f"处理：{treatment}"])
    return NotificationCommand("v14-exception:" + invocation_id, "v14-notify:" + invocation_id,
        NotificationKind.PURCHASE_EXCEPTION, RECIPIENTS, f"订单录单异常｜{pi}",
        "\n".join(lines), None, at)


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
            QQSMTPTransport(config=QQSMTPConfig(sender_address="1069599116@qq.com"))))
        self._stop = threading.Event()
        self._thread = None
        if background:
            self._thread = threading.Thread(target=self._run, name="v14-notification-outbox", daemon=True)
            self._thread.start()

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
