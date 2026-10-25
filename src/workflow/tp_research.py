"""Independent requirement identity and lifecycle; existing outbox owns delivery."""
import json
import sqlite3
from collections import Counter
from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from src.research.source_contracts import money_text
from src.sheets.tp_brief import TpLocalError, TpOrder, bind_tp_order, source_worksheet

from .v12_contracts import NotificationCommand, NotificationKind, NotificationRecipient
from .v12_store import create_verified_backup


class _TpDataError(TpLocalError):
    """Plain calculation failure captured at a TP data/composition boundary."""


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
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"workflow_requirements", "workflow_tp_failures"} <= tables:
            create_verified_backup(self.path, self.path.parent / "backups" / "tp-upgrade")
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS workflow_requirements (
                task_id TEXT PRIMARY KEY, kind TEXT NOT NULL, order_json TEXT NOT NULL,
                generation INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL,
                command_id TEXT, reason TEXT, updated_at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS workflow_tp_failures (
                fault_key TEXT PRIMARY KEY, reason TEXT NOT NULL, updated_at TEXT NOT NULL)""")

    def record_issues(self, issues, now):
        """Current TP holds, including rows that cannot safely form an order."""
        with self.connect() as db:
            db.execute("DELETE FROM workflow_tp_failures")
            db.executemany("INSERT INTO workflow_tp_failures VALUES (?, ?, ?)",
                           ((str(key), reason, now.isoformat()) for key, reason in issues.items()))

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

    def _line_key(self, spreadsheet, line):
        pointer = line.get("sheet_row")
        if line.get("sheet") not in {"2026", "SHAHAB"} or not pointer.isdecimal() or int(pointer) < 1:
            raise ValueError("TP_SOURCE_UNMATCHED")
        return task_key(spreadsheet, line.get("sheet"), int(pointer))

    def read_orders(self, spreadsheet, *, manual_key=None):
        lines = self.brief.read(spreadsheet)
        # Normalize physical anchors before counting; "010" and "10" are identical.
        counts = Counter()
        for line in lines:
            try:
                counts[self._line_key(spreadsheet, line)] += 1
            except ValueError:
                pass
        states = {row["task_id"]: row["state"] for row in self.store.rows()}
        snapshots = {}
        orders = []
        self.issues = {}
        for line in lines:
            if not line.get("target_price").strip():
                continue
            try:
                key = self._line_key(spreadsheet, line)
                if manual_key is not None and key != manual_key:
                    continue
                if manual_key is None and states.get(key) not in {None, "PENDING", "FAILED"}:
                    continue
                if counts[key] != 1:
                    raise ValueError("TP_SOURCE_AMBIGUOUS")
                if manual_key is not None and not self.store.manual_allowed(key):
                    raise TpLocalError("TP_TASK_BUSY_OR_DELIVERY_UNCONFIRMED")
                source = source_worksheet(spreadsheet, line)
                if source not in snapshots:
                    snapshots[source] = self.reader.read_rows(source)
                orders.append(bind_tp_order(line, spreadsheet, snapshots[source]))
            except ValueError as exc:
                if not tp_local_failure_reason(exc):
                    raise
                self.issues[line.brief_row] = str(exc)
        return orders

    def _revalidate(self, order):
        """Fresh native reads, but only bind the current target, never other orders."""
        key = task_key(order.spreadsheet, order.sheet, order.row)
        matches = []
        for line in self.brief.read(order.spreadsheet):
            try:
                if self._line_key(order.spreadsheet, line) == key:
                    matches.append(line)
            except ValueError:
                continue
        if len(matches) != 1:
            raise TpLocalError("TP_SOURCE_CHANGED")
        line = matches[0]
        current = bind_tp_order(line, order.spreadsheet,
                               self.reader.read_rows(source_worksheet(order.spreadsheet, line)))
        if current != order:
            raise TpLocalError("TP_SOURCE_CHANGED")

    def run(self, spreadsheet, *, now, manual_key=None):
        self.issues = {}
        try:
            self._run(spreadsheet, now=now, manual_key=manual_key)
        except ValueError as exc:
            reason = tp_local_failure_reason(exc)
            if not reason:
                raise
            self.issues[manual_key or "cycle"] = reason
            self.store.record_issues(self.issues, now)
            if manual_key is not None:
                raise TpLocalError(reason) from None
            return
        self.store.record_issues(self.issues, now)

    def _run(self, spreadsheet, *, now, manual_key=None):
        orders = self.read_orders(spreadsheet, manual_key=manual_key)
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
            except ValueError as exc:
                if not tp_local_failure_reason(exc):
                    raise
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
                try:
                    result = self.research.execute_tp(key, order, now=now)
                except (TypeError, AttributeError, ArithmeticError) as exc:
                    # Plain computation/data failures are TP-local. Typed or
                    # wrapped infrastructure/security exceptions remain shared.
                    if (type(exc).__module__ not in {"builtins", "decimal"}
                            or exc.__cause__ is not None or exc.__context__ is not None):
                        raise
                    raise _TpDataError("TP_RESEARCH_DATA_INVALID") from None
                if self.stop_requested():
                    self.store.finish(key, "FAILED", now, "TP_STOPPED")
                    continue
                self._revalidate(order)
                # Pure mail composition has no shared I/O; unexpected malformed
                # TP result data must not stop ordinary procurement/quotation.
                try:
                    mail = tp_mail(order, result, command, now)
                except (ValueError, TypeError, AttributeError, KeyError, ArithmeticError, RuntimeError) as exc:
                    if type(exc).__module__ not in {"builtins", "decimal"}:
                        raise
                    raise _TpDataError("TP_MAIL_PREPARATION_FAILED") from None
                self.outbox.enqueue_notification(mail)
                self.store.finish(key, "MAIL_QUEUED", now)
            except Exception as exc:
                # An enqueue may have committed before a crash/error. Inspect its
                # immutable key before making read-only research eligible again.
                self.store.recover(now, key=key)
                if self.store.get(key)["state"] == "PENDING":
                    self.store.finish(key, "FAILED", now, "TP_RESEARCH_UNCONFIRMED")
                reason = tp_local_failure_reason(exc)
                if reason:
                    if self.store.get(key)["state"] == "FAILED":
                        self.store.finish(key, "FAILED", now, reason)
                    self.issues[key] = reason
                    if manual_key is None:
                        continue
                    raise TpLocalError(reason) from None
                raise
        self.worker.run_due(now=now)
        if manual_key is not None and not found:
            raise ValueError("TP_SOURCE_UNMATCHED")


def tp_local_failure_reason(exc):
    """Positive classification only. Unknown and wrapped shared faults propagate."""
    from urllib.error import URLError

    from src.research.contracts import InvalidResearchInput
    from src.research.ecb_fx import EcbFxError

    reason = "TP_RESEARCH_INPUT_INVALID" if type(exc) is InvalidResearchInput else str(exc)
    pure, seen = False, set()
    while exc is not None:
        if id(exc) in seen:
            return None
        seen.add(id(exc))
        pure = pure or isinstance(exc, _TpDataError)
        local = isinstance(exc, TpLocalError) or type(exc) is InvalidResearchInput or (type(exc) is ValueError and (
            str(exc).startswith("TP_") or str(exc) == "FX_QUOTE_UNAVAILABLE"))
        computation = pure and (type(exc) in {ValueError, TypeError, AttributeError, KeyError, RuntimeError}
            or isinstance(exc, ArithmeticError) and type(exc).__module__ in {"builtins", "decimal"})
        fx = reason == "FX_QUOTE_UNAVAILABLE" and (
            type(exc) in {URLError, TimeoutError, ConnectionError, ConnectionResetError,
                          ConnectionAbortedError, ConnectionRefusedError}
            or type(exc) is EcbFxError and str(exc) in {
                "ECB_FETCH_FAILED", "ECB_INVALID_OBSERVATION", "ECB_DUPLICATE_OBSERVATION",
                "ECB_MISSING_OBSERVATION", "ECB_OBSERVATION_DATE_MISMATCH"}
            or type(exc).__module__ == "decimal" and isinstance(exc, ArithmeticError))
        if not (local or computation or fx):
            return None
        exc = exc.__cause__ or exc.__context__
    return reason
