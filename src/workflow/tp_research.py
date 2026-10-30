"""Independent requirement identity and lifecycle; existing outbox owns delivery."""
import json
import sqlite3
import threading
from collections import Counter
from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from src.sheets.pending import identify_worksheet_row
from src.sheets.tp_brief import TpLocalError, TpOrder, bind_tp_order, source_worksheet

from .v12_contracts import NotificationCommand, NotificationKind, NotificationRecipient
from .v12_store import V12Store, create_verified_backup


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
        outcomes = {r.outcome.value for r in V12Store(self.path).recipient_results(row["command_id"])}
        if not outcomes:
            return None
        # One successful recipient must never hide another's unknown/in-flight
        # attempt. Reuse the outbox's recipient-scoped retries, never replay SENT.
        for pending in ("UNKNOWN", "SENDING", "PENDING", "RETRYABLE_FAILURE"):
            if pending in outcomes:
                return pending
        if "SUPPRESSED" in outcomes:
            return "SUPPRESSED"
        if outcomes <= {"SENT", "PERMANENT_FAILURE"}:
            return "PERMANENT_FAILURE" if "PERMANENT_FAILURE" in outcomes else "SENT"
        return "UNKNOWN"

    def manual_allowed(self, key):
        row = self.get(key)
        return row["state"] in {"MAIL_QUEUED", "FAILED"} and self.delivery(key) in {
            None, "SENT", "PERMANENT_FAILURE", "SUPPRESSED"}

    def claim(self, key, order, now, *, manual=False):
        from .automatic_admission import age_reason
        if not manual and age_reason(order.rfq_date, now, module="tp"):
            return None
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
                from .automatic_admission import age_reason
                if age_reason(load_order(row["order_json"]).rfq_date, now, module="tp"):
                    continue
                command = db.execute("SELECT 1 FROM workflow_v12_notification_commands WHERE command_id=?",
                                     (row["command_id"],)).fetchone()
                db.execute("UPDATE workflow_requirements SET state=?,updated_at=? WHERE task_id=?",
                           ("MAIL_QUEUED" if command else "PENDING", now.isoformat(), row["task_id"]))


def tp_mail(order, result, command_id, now):
    from src.research.report import render_market_report
    text, html = render_market_report(order, result)
    return NotificationCommand(command_id, None, NotificationKind.TP_RESEARCH,
        (NotificationRecipient("owner", "linan229@qq.com"),
         NotificationRecipient("ops", "shawn@inso-hk.com")),
        "【INSO】TP 专项调研", text, html, now)


class TpCycle:
    """Runs exclusively on the existing poll/manual thread; DB claim is final guard."""
    def __init__(self, *, store, brief, reader, research, outbox, worker,
                 prepare=lambda _key: None, stop_requested=lambda: False, clock=None, report_observer=None):
        self.store, self.brief, self.reader = store, brief, reader
        self.research, self.outbox, self.worker = research, outbox, worker
        self.clock = clock
        self.report_observer = report_observer
        self.prepare, self.stop_requested = prepare, stop_requested
        self.issues = {}
        self._continuation_sources = {}

    def _line_key(self, spreadsheet, line):
        pointer = line.get("sheet_row")
        if line.get("sheet") not in {"2026", "SHAHAB"} or not pointer.isdecimal() or int(pointer) < 1:
            raise ValueError("TP_SOURCE_UNMATCHED")
        return task_key(spreadsheet, line.get("sheet"), int(pointer))

    def read_orders(self, spreadsheet, *, manual_key=None, now=None):
        from datetime import UTC, datetime

        from .automatic_admission import age_reason
        now = self.clock() if self.clock else now or datetime.now(UTC)
        self._continuation_sources = {}
        read_brief = self.brief.read if manual_key is not None else getattr(self.brief, "read_discovery", self.brief.read)
        lines = read_brief(spreadsheet)
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
                    read = (self.reader.read_rows if manual_key is not None else
                            getattr(self.reader, "read_discovery_rows", self.reader.read_rows))
                    snapshots[source] = tuple(read(source))
                order = bind_tp_order(line, spreadsheet, snapshots[source])
                target = next(row for row in snapshots[source] if row.row_position == order.row)
                if manual_key is None and age_reason(order.rfq_date, now, module="tp"):
                    self.issues[key] = "TP_AGE_EXCLUDED"
                    continue
                self._continuation_sources[key] = order, identify_worksheet_row(source, target)
                orders.append(order)
            except ValueError as exc:
                if not tp_local_failure_reason(exc):
                    raise
                self.issues[line.brief_row] = str(exc)
        return orders

    def continuation_source(self, order):
        """Reuse THIS discovery batch, not another native read of every TP row."""
        key = task_key(order.spreadsheet, order.sheet, order.row)
        observed = self._continuation_sources.get(key)
        if observed is None or observed[0] != order:
            raise TpLocalError("TP_SOURCE_CHANGED")
        return observed[1]

    def read_continuation_orders(self, spreadsheet, *, now):
        """Same positive TP-only isolation at asynchronous cycle discovery."""
        self.issues = {}
        try:
            return self.read_orders(spreadsheet, now=now)
        except ValueError as error:
            reason = tp_local_failure_reason(error)
            if not reason:
                raise
            self.issues["cycle"] = reason
            self.store.record_issues(self.issues, now)
            return ()

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
        worksheet = source_worksheet(order.spreadsheet, line)
        rows = tuple(self.reader.read_rows(worksheet))
        current = bind_tp_order(line, order.spreadsheet, rows)
        if current != order:
            raise TpLocalError("TP_SOURCE_CHANGED")
        targets = [row for row in rows if row.row_position == order.row]
        if len(targets) != 1:
            raise TpLocalError("TP_SOURCE_AMBIGUOUS")
        return identify_worksheet_row(worksheet, targets[0])


    def complete_order(self, order, key, command, result, *, now, expected_source=None,
                       before_enqueue=lambda: None, manual=False):
        """Original owner only. Same source/command/Stop gates before enqueue."""
        now = self.clock() if self.clock else now
        if key != task_key(order.spreadsheet, order.sheet, order.row):
            raise TpLocalError("TP_IDENTITY_CHANGED")
        state = self.store.get(key)
        if (state["state"] != "RESEARCHING" or state["command_id"] != command
                or state["order_json"] != order_json(order)):
            raise TpLocalError("TP_TASK_BUSY_OR_DELIVERY_UNCONFIRMED")
        if self.stop_requested():
            self.store.finish(key, "FAILED", now, "TP_STOPPED")
            return
        from .automatic_admission import age_reason
        if not manual and age_reason(order.rfq_date, now, module="tp"):
            self.issues[key] = "TP_AGE_EXCLUDED"
            self.store.finish(key, "EXCLUDED", now, "TP_AGE_EXCLUDED")
            return
        current = self._revalidate(order)
        if expected_source is not None and current != expected_source:
            raise TpLocalError("TP_SOURCE_CHANGED")
        try:
            mail = tp_mail(order, result, command, now)
            if self.report_observer is not None:
                self.report_observer(order, result, now)
            if manual:
                from dataclasses import replace
                mail = replace(mail, review=json.dumps({"manual": True, "owner_request": command}))
        except (ValueError, TypeError, AttributeError, KeyError, ArithmeticError, RuntimeError) as exc:
            if type(exc).__module__ not in {"builtins", "decimal"}:
                raise
            raise _TpDataError("TP_MAIL_PREPARATION_FAILED") from None
        # Recheck after the source read/composition, before persistent enqueue.
        if self.stop_requested():
            self.store.finish(key, "FAILED", now, "TP_STOPPED")
            return
        before_enqueue()
        self.outbox.enqueue_notification(mail)
        self.store.finish(key, "MAIL_QUEUED", now)

    def begin_continuation(self, order, identity, runtime, *, now, manual=False):
        """Optional E path; claim SAME source resource before durable TP work.

        No worker/Browser enters Workflow. Caller advances returned Research on
        owner/market ports and returns to this same durable business finish.
        """
        from .market_messages import MarketModule, MarketTaskIdentity
        now = self.clock() if self.clock else now
        key = task_key(order.spreadsheet, order.sheet, order.row)
        if (type(identity) is not MarketTaskIdentity or identity.module is not MarketModule.TP
                or identity.domain_task_id != key):
            raise ValueError("TP_CONTINUATION_IDENTITY_INVALID")
        if self.stop_requested():
            return None
        from .automatic_admission import age_reason
        if not manual and age_reason(order.rfq_date, now, module="tp"):
            return None
        if self._revalidate(order) != identity.source_record:
            raise TpLocalError("TP_SOURCE_CHANGED")
        lease = runtime.claim_business_continuation(identity)
        if lease is None:
            return None
        work = TpOrderContinuation(self, runtime, lease, order, now)
        work.manual = manual
        try:
            self.store.register(order, now)
            command = self.store.claim(key, order, now, manual=manual)
            if command is None:
                work.cancel()
                return None
            work.command = command
            self.prepare(key)
            work.research = self.research.begin_tp(key, order, now=now)
            return work
        except Exception:
            work.fail()
            raise


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
        orders = self.read_orders(spreadsheet, manual_key=manual_key, now=now)
        found = False
        for order in orders:
            if self.stop_requested():
                break
            key = task_key(order.spreadsheet, order.sheet, order.row)
            if manual_key is not None and manual_key != key:
                continue
            from .automatic_admission import age_reason
            current_now = self.clock() if self.clock else now
            if manual_key is None and age_reason(order.rfq_date, current_now, module="tp"):
                self.issues[key] = "TP_AGE_EXCLUDED"
                continue
            self._revalidate(order)
            self.store.register(order, current_now)
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
                self.complete_order(order, key, command, result, now=now, manual=manual_key is not None)
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


class TpOrderContinuation:
    """One original-owner TP claim, canonical outbox, no additional ledger."""
    def __init__(self, cycle, runtime, lease, order, now):
        self._cycle, self._runtime, self.lease = cycle, runtime, lease
        self.order, self.now = order, now
        self.command, self.research = None, None
        self._owner, self._closed = threading.get_ident(), False

    def _check(self):
        if self._owner != threading.get_ident() or self._closed:
            raise RuntimeError("TP_CONTINUATION_OWNER_OR_LIFETIME_INVALID")

    def _release(self, terminal):
        from .market_messages import BusinessTerminalReceipt
        self._runtime.finish_business_continuation(self.lease,
            BusinessTerminalReceipt(self.lease.identity, terminal))
        self._closed = True

    def complete(self, completion):
        from .market_messages import (
            BusinessEffectTerminal,
            BusinessResearchCompletion,
            BusinessTerminal,
        )
        self._check()
        if type(completion) is not BusinessResearchCompletion or completion.identity != self.lease.identity:
            raise ValueError("TP_CONTINUATION_RESULT_MISMATCH")
        result = completion.result
        self._runtime.require_business_continuation(self.lease)
        self._runtime.begin_business_effect(self.lease)
        try:
            self._cycle.complete_order(self.order, self.lease.identity.domain_task_id,
                self.command, result, now=self.now, expected_source=self.lease.identity.source_record,
                before_enqueue=lambda: self._runtime.require_business_continuation(self.lease),
                manual=getattr(self, "manual", False))
        except Exception:
            # No blind retry after enqueue: canonical command lookup is the
            # authority. If reconciliation itself fails, retain the source.
            try:
                self._recover()
            except Exception:
                self._runtime.acknowledge_business_effect(self.lease, BusinessEffectTerminal.UNKNOWN)
                raise
            self._runtime.acknowledge_business_effect(self.lease, BusinessEffectTerminal.CONFIRMED)
            self._release(BusinessTerminal.FAILED)
            raise
        self._runtime.acknowledge_business_effect(self.lease, BusinessEffectTerminal.CONFIRMED)
        self._release(BusinessTerminal.COMPLETED)

    def _recover(self):
        if self.command is None:
            return
        key = self.lease.identity.domain_task_id
        state = self._cycle.store.get(key)
        if state["command_id"] != self.command or state["order_json"] != order_json(self.order):
            raise RuntimeError("TP_CONTINUATION_COMMAND_CHANGED")
        self._cycle.store.recover(self.now, key=key)
        if self._cycle.store.get(key)["state"] in {"PENDING", "RESEARCHING"}:
            self._cycle.store.finish(key, "FAILED", self.now, "TP_RESEARCH_UNCONFIRMED")

    def fail(self):
        from .market_messages import BusinessTerminal, BusinessTerminalReceipt
        self._check()
        try:
            self._recover()
        except Exception:
            self._runtime.finish_business_continuation(self.lease,
                BusinessTerminalReceipt(self.lease.identity, BusinessTerminal.UNKNOWN))
            raise
        self._release(BusinessTerminal.FAILED)

    def cancel(self):
        from .market_messages import BusinessTerminal
        self._check()
        self._recover()
        self._release(BusinessTerminal.CANCELLED)


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
