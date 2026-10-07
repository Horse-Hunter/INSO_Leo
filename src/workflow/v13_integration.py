"""Serial RFQ-006 orchestration; reuse the reviewed read/update engines."""

import json
import logging
import sqlite3
from dataclasses import asdict, replace
from hashlib import sha256

from src.sheets import query_quotation_candidates
from src.sheets.brand_write import SheetRecordConflict
from src.sheets.quotation_candidates import relocate_quotation_status
from src.sheets.worksheet_schema import worksheet_schema

from .v12_faults import FaultScope, V12Fault
from .v12_store import V12DatabaseError, create_verified_backup
from .v13_quotation import (
    QuotationOutcome,
    RowErrorReason,
    V13QuotationResult,
    V13SourceRowError,
    V13Stopped,
)

log = logging.getLogger(__name__)


class V13HoldStore:
    """One additive table in the existing DB; V1.2 user_version is unchanged."""

    def __init__(self, path):
        self.path = path

    def migrate(self):
        try:
            with sqlite3.connect(self.path) as db:
                present = db.execute(
                    "SELECT 1 FROM sqlite_master WHERE name='workflow_v13_holds'"
                ).fetchone()
            if not present:
                create_verified_backup(
                    self.path, self.path.parent / "backups" / "v13-upgrade"
                )
            with sqlite3.connect(self.path) as db:
                db.execute("BEGIN IMMEDIATE")
                # Extend the same mailbox ledger to unbound row/global alerts.
                info = tuple(
                    db.execute("PRAGMA table_info(workflow_v12_notification_commands)")
                )
                if next(row[3] for row in info if row[1] == "inquiry_id"):
                    db.execute("""CREATE TABLE workflow_v13_notification_upgrade (
                        command_id TEXT PRIMARY KEY, inquiry_id TEXT REFERENCES workflow_items(inquiry_id) ON DELETE RESTRICT,
                        kind TEXT NOT NULL, subject TEXT NOT NULL, text_body TEXT NOT NULL,
                        html_body TEXT, created_at TEXT NOT NULL, payload_version INTEGER NOT NULL)""")
                    db.execute(
                        "INSERT INTO workflow_v13_notification_upgrade SELECT * FROM workflow_v12_notification_commands"
                    )
                    db.execute("DROP TABLE workflow_v12_notification_commands")
                    db.execute(
                        "ALTER TABLE workflow_v13_notification_upgrade RENAME TO workflow_v12_notification_commands"
                    )
                db.execute("""CREATE TABLE IF NOT EXISTS workflow_v13_holds (
                    hold_key TEXT PRIMARY KEY, result_json TEXT NOT NULL,
                    observed_identity TEXT NOT NULL, reason TEXT NOT NULL,
                    episode INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1)""")
                columns = {
                    row[1]
                    for row in db.execute("PRAGMA table_info(workflow_v13_holds)")
                }
                if columns != {
                    "hold_key",
                    "result_json",
                    "observed_identity",
                    "reason",
                    "episode",
                    "active",
                }:
                    raise V12DatabaseError("V1.3 hold schema invalid")
        except (sqlite3.Error, V12DatabaseError):
            raise V12Fault(
                FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE"
            ) from None

    def active(self):
        try:
            with sqlite3.connect(self.path) as db:
                return tuple(
                    db.execute(
                        "SELECT hold_key,result_json,observed_identity,reason,episode FROM workflow_v13_holds WHERE active=1"
                    )
                )
        except sqlite3.Error:
            raise V12Fault(
                FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE"
            ) from None

    def hold(self, result, observed):
        identity = json.dumps(asdict(observed), ensure_ascii=False, sort_keys=True)
        key = result.inquiry_id or "unresolved:" + sha256(identity.encode()).hexdigest()
        payload = json.dumps(
            asdict(replace(result, quotation=None)), ensure_ascii=False
        )
        reason = result.row_error_reason.value
        try:
            with sqlite3.connect(self.path) as db:
                previous = db.execute(
                    "SELECT reason,episode,active FROM workflow_v13_holds WHERE hold_key=?",
                    (key,),
                ).fetchone()
                episode = (
                    (previous[1] + int(previous[0] != reason or not previous[2]))
                    if previous
                    else 1
                )
                db.execute(
                    "INSERT INTO workflow_v13_holds VALUES (?,?,?,?,?,1) ON CONFLICT(hold_key) DO UPDATE SET result_json=excluded.result_json,observed_identity=excluded.observed_identity,reason=excluded.reason,episode=excluded.episode,active=1",
                    (key, payload, identity, reason, episode),
                )
            return key, episode
        except sqlite3.Error:
            raise V12Fault(
                FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE"
            ) from None

    def close(self, key):
        try:
            with sqlite3.connect(self.path) as db:
                db.execute(
                    "UPDATE workflow_v13_holds SET active=0 WHERE hold_key=?", (key,)
                )
        except sqlite3.Error:
            raise V12Fault(
                FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE"
            ) from None


def restore_result(payload):
    from src.sheets import IdentifyingSnapshot, SheetRecordIdentity, WorksheetIdentity

    from .v13_quotation import V13QuotationResult

    data = json.loads(payload)
    identity = data["record_identity"]
    if identity:
        data["record_identity"] = SheetRecordIdentity(
            WorksheetIdentity(**identity["worksheet"]),
            identity["row_position"],
            IdentifyingSnapshot(**identity["identifying_snapshot"]),
        )
    if data["source_worksheet"]:
        data["source_worksheet"] = WorksheetIdentity(**data["source_worksheet"])
    data["outcome"] = QuotationOutcome(data["outcome"])
    data["row_error_reason"] = RowErrorReason(data["row_error_reason"])
    data["quotation"] = (
        None  # Hold stores operational outcome, never raw quotation payload.
    )
    return V13QuotationResult(**data)


class V13IntegratedCycle:
    def __init__(
        self,
        *,
        reader,
        store,
        holds,
        cycle,
        updater_factory,
        notify,
        observe,
        stop_requested=lambda: False,
    ):
        self.reader, self.store, self.holds = reader, store, holds
        self.cycle, self.updater_factory = cycle, updater_factory
        self.notify, self.observe, self.stop = notify, observe, stop_requested

    def run(self, worksheet):
        blocked_ids, blocked_locations = set(), set()
        # Strict identity first; original location is a human-status barrier only.
        from src.sheets import (
            IdentifyingSnapshot,
            SheetRecordIdentity,
            WorksheetIdentity,
        )

        for key, payload, identity_json, reason, episode in self.holds.active():
            try:
                result = restore_result(payload)
                observed = json.loads(identity_json)
                identity = SheetRecordIdentity(
                    WorksheetIdentity(**observed["worksheet"]),
                    observed["row_position"],
                    IdentifyingSnapshot(**observed["identifying_snapshot"]),
                )
            except (ValueError, KeyError, TypeError):
                raise V12Fault(
                    FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE"
                ) from None
            self.notify(
                result, key, episode
            )  # Repair a crash between hold commit and enqueue; deduplicated.
            if identity.worksheet != worksheet:
                continue
            if result.inquiry_id:
                blocked_ids.add(result.inquiry_id)
            try:
                rows = tuple(self.reader.read_rows(worksheet))
            except Exception:  # noqa: BLE001 - shared read boundary or isolated row adapter
                raise V12Fault(
                    FaultScope.GLOBAL_STOP, "SHEETS_READ_UNAVAILABLE"
                ) from None
            try:
                located = relocate_quotation_status(
                    identity,
                    rows,
                    expected_brand=identity.identifying_snapshot.brand,
                    accepted_statuses=("发给采购", "采购已报价"),
                )
            except SheetRecordConflict:
                log.warning("V1.3 held source cannot be safely located")
                # Never bind/query/write using this fallback: only block automation
                # and let the Owner's status at the original position close a hold.
                anchors = [row for row in rows if row.row_position == identity.row_position]
                if len(anchors) != 1:
                    self.observe(result, key)
                    continue
                located = anchors[0]
                status = located.cells.get(worksheet_schema(worksheet.worksheet).status_column)
                if status != "采购已报价":
                    blocked_locations.add(identity.row_position)
                    self.observe(result, key)
                    continue
            if (
                located.cells.get(worksheet_schema(worksheet.worksheet).status_column)
                == "采购已报价"
            ):
                self.holds.close(key)
                blocked_ids.discard(result.inquiry_id)
                self.observe(
                    replace(
                        result,
                        outcome=QuotationOutcome.UPDATED_ALREADY_EXISTS,
                        row_error_reason=None,
                    ),
                    key,
                )
            else:
                blocked_locations.add(located.row_position)
                self.observe(result, key)

        try:
            observed_records = query_quotation_candidates(self.reader, worksheet)
        except Exception:  # noqa: BLE001 - shared read boundary or isolated row adapter
            raise V12Fault(FaultScope.GLOBAL_STOP, "SHEETS_READ_UNAVAILABLE") from None

        def skip(candidate):
            return (
                candidate.inquiry_id in blocked_ids
                or candidate.source_row_position in blocked_locations
            )

        def settle(result):
            if self.stop():
                raise V13Stopped("STOP_REQUESTED")
            try:
                final = (
                    self.updater_factory().update_one(result)
                    if result.outcome is QuotationOutcome.QUOTE_FOUND
                    else result
                )
                if not isinstance(final, V13QuotationResult):
                    raise TypeError("invalid updater result contract")
            except V13SourceRowError as exc:
                final = replace(result, outcome=QuotationOutcome.ROW_FAILED, row_error_reason=exc.reason)
            except (V12Fault, V13Stopped):
                raise
            except (sqlite3.Error, V12DatabaseError):
                raise V12Fault(
                    FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE"
                ) from None
            except Exception:  # noqa: BLE001 - shared read boundary or isolated row adapter
                raise V12Fault(FaultScope.GLOBAL_STOP, "V13_INTERNAL_FAILURE") from None
            key = final.inquiry_id
            if final.outcome is QuotationOutcome.ROW_FAILED:
                record = next(
                    (
                        r
                        for r in observed_records
                        if r.row_position == final.source_row_position
                    ),
                    None,
                )
                identity = record.record_identity if record else final.record_identity
                if identity is None:
                    raise V12Fault(FaultScope.GLOBAL_STOP, "HOLD_IDENTITY_UNAVAILABLE")
                # Strip quotation data from durable operational state.
                key, episode = self.holds.hold(replace(final, quotation=None), identity)
                self.notify(final, key, episode)
            self.observe(final, key)
            return final

        return self.cycle.run(worksheet, skip=skip, on_result=settle)


class CombinedCycle:
    """Run A then B without another wait; only V1.2-local faults pause A."""

    def __init__(self, v12, v13, *, on_pause, stop_requested=lambda: False):
        self.v12, self.v13, self.on_pause, self.stop = (
            v12,
            v13,
            on_pause,
            stop_requested,
        )
        self.v12_paused = False

    def run(self, reader, worksheets, *, now):
        self.v12.begin_poll_cycle()
        if not self.v12_paused:
            try:
                for worksheet in worksheets:
                    if self.stop():
                        return
                    self.v12.poll_and_process(reader, worksheet, now=now)
            except (sqlite3.Error, V12DatabaseError):
                raise V12Fault(
                    FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE"
                ) from None
            except V12Fault as exc:
                if exc.scope is FaultScope.GLOBAL_STOP:
                    raise
                self.v12_paused = True
                self.on_pause(exc)
            except Exception as exc:  # noqa: BLE001 - classify the isolated V1.2 boundary
                # The reviewed Research worker can wrap preparation faults. Preserve
                # their shared cause instead of treating the wrapper as a local blocker.
                cause, visited = exc, set()
                while cause is not None and id(cause) not in visited:
                    visited.add(id(cause))
                    if (
                        isinstance(cause, V12Fault)
                        and cause.scope is FaultScope.GLOBAL_STOP
                    ):
                        raise cause
                    name = type(cause).__name__
                    reason = (
                        "WORKFLOW_LEDGER_UNAVAILABLE"
                        if isinstance(cause, (sqlite3.Error, V12DatabaseError))
                        else "SHEETS_READ_UNAVAILABLE"
                        if name.startswith("GoogleSheets")
                        else "INSO_AUTHENTICATION_REQUIRED"
                        if name == "InsoAuthenticationError"
                        else "CDP_SESSION_UNAVAILABLE"
                        if name == "BrowserBootstrapError"
                        else None
                    )
                    if reason:
                        raise V12Fault(FaultScope.GLOBAL_STOP, reason) from None
                    cause = cause.__cause__
                self.v12_paused = True
                self.on_pause(V12Fault(FaultScope.V12_PAUSE, "V12_INTERNAL_FAILURE"))
        for worksheet in worksheets:
            if self.stop():
                return
            self.v13(worksheet)
