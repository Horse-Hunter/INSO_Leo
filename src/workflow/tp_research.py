"""Independent requirement identity and lifecycle; existing outbox owns delivery."""
import json
import sqlite3
from collections import Counter
from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from src.research.source_contracts import money_text
from src.sheets.tp_brief import TpOrder, bind_tp_order, source_worksheet

from .v12_contracts import NotificationCommand, NotificationKind, NotificationRecipient
from .v12_store import create_verified_backup


def task_key(spreadsheet, sheet, row, kind="target_price"):
    return "tp_" + sha256(json.dumps([spreadsheet, sheet, row, kind],
                                     separators=(",", ":")).encode()).hexdigest()[:32]


def order_json(order):
    return json.dumps(asdict(order), default=str, ensure_ascii=False, sort_keys=True)


def load_order(value):
    fields = json.loads(value)
    fields["target_price"] = Decimal(fields["target_price"])
    return TpOrder(**fields)


class TpStore:
    def __init__(self, path):
        self.path = Path(path)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def migrate(self):
        with self.connect() as db:
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='workflow_requirements'").fetchone()
        if not exists:
            create_verified_backup(self.path, self.path.parent / "backups" / "tp-upgrade")
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS workflow_requirements (
                task_id TEXT PRIMARY KEY, kind TEXT NOT NULL, order_json TEXT NOT NULL,
                generation INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL,
                command_id TEXT, reason TEXT, updated_at TEXT NOT NULL)""")

    def rows(self):
        with self.connect() as db:
            return tuple(db.execute("SELECT * FROM workflow_requirements ORDER BY task_id"))

    def get(self, key):
        with self.connect() as db:
            row = db.execute("SELECT * FROM workflow_requirements WHERE task_id=?", (key,)).fetchone()
        if row is None:
            raise KeyError(key)
        return row

    def register(self, order, now):
        key = task_key(order.spreadsheet, order.sheet, order.row)
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO workflow_requirements "
                       "(task_id,kind,order_json,state,updated_at) VALUES (?, 'target_price', ?, 'PENDING', ?)",
                       (key, order_json(order), now.isoformat()))
        return key

    def delivery(self, key):
        row = self.get(key)
        with self.connect() as db:
            result = db.execute("SELECT outcome FROM workflow_v12_notification_recipients WHERE command_id=?",
                                (row["command_id"],)).fetchone()
        return result[0] if result else None

    def manual_allowed(self, key):
        row = self.get(key)
        return row["state"] in {"MAIL_QUEUED", "FAILED"} and self.delivery(key) in {
            None, "SENT", "PERMANENT_FAILURE"}

    def claim(self, key, order, now, *, manual=False):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM workflow_requirements WHERE task_id=?", (key,)).fetchone()
            if row is None:
                return None
            original = load_order(row["order_json"])
            if (original.spreadsheet, original.sheet, original.row, original.mpn, original.quantity) != (
                    order.spreadsheet, order.sheet, order.row, order.mpn, order.quantity):
                raise ValueError("TP_IDENTITY_CHANGED")
            if manual:
                if not self.manual_allowed(key):
                    return None
                generation = row["generation"] + 1
            else:
                if row["state"] not in {"PENDING", "FAILED"}:
                    return None
                generation = row["generation"]
            command = f"{key}:{generation}"
            db.execute("UPDATE workflow_requirements SET state='RESEARCHING', generation=?, "
                       "command_id=?, order_json=?, reason=NULL, updated_at=? WHERE task_id=?",
                       (generation, command, order_json(order), now.isoformat(), key))
        return command

    def finish(self, key, state, now, reason=None):
        with self.connect() as db:
            db.execute("UPDATE workflow_requirements SET state=?,reason=?,updated_at=? WHERE task_id=?",
                       (state, reason, now.isoformat(), key))

    def recover(self, now, *, key=None):
        """Startup only under existing app single-instance guard, before any worker."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT * FROM workflow_requirements WHERE state='RESEARCHING'"
                              + (" AND task_id=?" if key else ""), (key,) if key else ()).fetchall()
            for row in rows:
                command = db.execute("SELECT 1 FROM workflow_v12_notification_commands WHERE command_id=?",
                                     (row["command_id"],)).fetchone()
                db.execute("UPDATE workflow_requirements SET state=?,updated_at=? WHERE task_id=?",
                           ("MAIL_QUEUED" if command else "PENDING", now.isoformat(), row["task_id"]))


def tp_mail(order, result, command_id, now):
    def quote(q):
        if q is None:
            return "无有效报价"
        o = q.offer
        when = "现价，报价日期未提供" if o.current else o.quoted_at.isoformat()
        stock = "；无库存" if not o.stocked else ""
        return (f"{money_text(o.price)} {o.currency} / {money_text(q.rmb)} RMB，"
                f"{o.source.value}，{when}{stock}")
    urgent = result.lowest is None or result.lowest.rmb < result.target_rmb
    lines = ["请人工加急跟进" if urgent else "TP 专项调研",
             f"客户：{order.customer or '未提供'}；原始订单：{order.sheet} 第{order.row}行",
             f"询价日期：{order.rfq_date}；型号：{order.mpn}；数量：{order.quantity}",
             f"TP：{order.target_raw}；折合 {money_text(result.target_rmb)} RMB",
             f"货量：{result.stock_label}",
             "预计订单总价：" + (f"{money_text(result.estimated_total)} RMB" if result.estimated_total is not None else "无法计算（无有效价格）")]
    from src.research.tp import distinct_two
    for source in result.sources:
        pool = [q for q in source.quotes if q.offer.stocked] or list(source.quotes)
        pair = distinct_two(pool)
        first, second = (pair + (None, None))[:2]
        lines.append(f"{source.source.value}（窗口≤{source.months}个月）：最低 {quote(first)}；"
                     f"次低 {quote(second) if second else '不足两档有效价格'}"
                     + ("；来源暂不可用" if source.outcome.value == "SOURCE_UNAVAILABLE" else ""))
    lines.extend(["全局真实最低：" + quote(result.lowest),
                  "全局真实次低：" + (quote(result.second) if result.second else "不足两档有效价格")])
    lines.append("价格排名以本次已获取的有效报价为准；相同单价只计一档。")
    if result.fallback:
        lines.append("仅无库存报价兜底；不代表现货可得。")
    return NotificationCommand(command_id, None, NotificationKind.TP_RESEARCH,
        (NotificationRecipient("owner", "linan229@qq.com"),),
        "【INSO】TP 专项调研", "\n".join(lines), None, now)


class TpCycle:
    """Runs exclusively on the existing poll/manual thread; DB claim is final guard."""
    def __init__(self, *, store, brief, reader, research, outbox, worker,
                 prepare=lambda _key: None, stop_requested=lambda: False):
        self.store, self.brief, self.reader = store, brief, reader
        self.research, self.outbox, self.worker = research, outbox, worker
        self.prepare, self.stop_requested = prepare, stop_requested
        self.issues = {}

    def read_orders(self, spreadsheet):
        lines = self.brief.read(spreadsheet)
        counts = Counter((r.get("sheet"), r.get("sheet_row")) for r in lines if r.get("target_price").strip())
        orders = []
        self.issues = {}
        for line in lines:
            if not line.get("target_price").strip():
                continue
            try:
                if counts[(line.get("sheet"), line.get("sheet_row"))] != 1:
                    raise ValueError("TP_SOURCE_AMBIGUOUS")
                if line.get("sheet") not in {"2026", "SHAHAB"}:
                    raise ValueError("TP_SOURCE_UNMATCHED")
                source = source_worksheet(spreadsheet, line)
                orders.append(bind_tp_order(line, spreadsheet, self.reader.read_rows(source)))
            except ValueError as exc:
                self.issues[line.brief_row] = str(exc)
        return orders

    def run(self, spreadsheet, *, now, manual_key=None):
        orders = self.read_orders(spreadsheet)
        found = False
        for order in orders:
            if self.stop_requested():
                break
            key = task_key(order.spreadsheet, order.sheet, order.row)
            if manual_key is not None and manual_key != key:
                continue
            self.store.register(order, now)
            found = True
            try:
                command = self.store.claim(key, order, now, manual=manual_key is not None)
            except ValueError:
                self.issues[key] = "TP_IDENTITY_CHANGED"
                if manual_key is not None:
                    raise
                continue
            if command is None:
                if manual_key is not None:
                    raise ValueError("TP_TASK_BUSY_OR_DELIVERY_UNCONFIRMED")
                continue
            try:
                self.prepare(key)
                result = self.research.execute_tp(key, order, now=now)
                if self.stop_requested():
                    self.store.finish(key, "FAILED", now, "TP_STOPPED")
                    continue
                # Re-read BOTH Brief and source after research, before queueing mail.
                current = [o for o in self.read_orders(spreadsheet)
                           if task_key(o.spreadsheet, o.sheet, o.row) == key]
                if current != [order]:
                    raise ValueError("TP_SOURCE_CHANGED")
                self.outbox.enqueue_notification(tp_mail(order, result, command, now))
                self.store.finish(key, "MAIL_QUEUED", now)
            except Exception as exc:
                # An enqueue may have committed before a crash/error. Inspect its
                # immutable key before making read-only research eligible again.
                self.store.recover(now, key=key)
                if self.store.get(key)["state"] == "PENDING":
                    self.store.finish(key, "FAILED", now, "TP_RESEARCH_UNCONFIRMED")
                if isinstance(exc, ValueError) and str(exc) in {"TP_SOURCE_CHANGED", "FX_QUOTE_UNAVAILABLE"}:
                    self.issues[key] = str(exc)
                    if manual_key is None:
                        continue
                raise
        self.worker.run_due(now=now)
        if manual_key is not None and not found:
            raise ValueError("TP_SOURCE_UNMATCHED")
