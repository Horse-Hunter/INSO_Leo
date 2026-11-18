"""The Owner must read the reason on the "异常与通知" page, not in a log.

Owner rule (2026-11-17): a production fault has to explain itself in the product
UI -- what failed, when, which modules it stopped, what is still unconfirmed and
what to do next -- and it must survive closing and reopening the window.  These
tests pin the projection, the wording and the durable read-back.
"""

import sqlite3
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta

from src.gui.contracts import HealthReport, RunSession, RunState, WorkbenchSnapshot
from src.gui.workbench import fault_block
from src.launcher.fault_diagnostics import (
    FaultDiagnostic,
    build_diagnostic,
    describe,
)
from src.workflow.store import WorkflowStateStore
from src.workflow.v12_store import V12Store, migrate_v12

NOW = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)


def test_a_sheets_read_fault_names_the_dependent_modules_once():
    fault = build_diagnostic(
        "SHEETS_READ_UNAVAILABLE",
        site="Google Sheets",
        cause_class="SSLEOFError",
        first_seen=NOW,
        last_seen=NOW + timedelta(seconds=3),
        occurrences=4,
        escalation="已停止共享业务；本次没有达到三小时升级门限",
        external_effect="没有未结清的外部写入意图",
    )

    assert fault.title == "Google Sheets 数据读取失败"
    assert fault.related_modules == ("询价采购", "报价跟进", "目标价调研")
    assert fault.knock_on == fault.related_modules  # Merged, never three faults.
    assert fault.cause_class == "SSLEOFError"
    assert "已按上限重试" in fault.cause
    assert fault.occurrences == 4
    assert fault.active


def test_the_page_block_carries_every_field_the_owner_asked_for():
    fault = build_diagnostic(
        "SHEETS_READ_UNAVAILABLE",
        site="Google Sheets",
        cause_class="SSLEOFError",
        first_seen=NOW,
        last_seen=NOW,
        escalation="已停止共享业务；本次没有达到三小时升级门限",
        external_effect="没有未结清的外部写入意图；本次未确认任何新的外部写入",
    )

    block = fault_block(fault)
    for expected in ("【故障】Google Sheets 数据读取失败", "故障代码：SHEETS_READ_UNAVAILABLE",
                     "发生时间：", "影响模块：询价采购、报价跟进、目标价调研",
                     "具体原因：", "恢复过程：", "外部写入：", "建议操作：", "诊断位置："):
        assert expected in block


def test_an_unexplained_code_says_so_instead_of_inventing_a_cause():
    title, cause, action = describe("SOMETHING_NEW")

    assert "未分类故障" in title
    assert "没有已确认的中文说明" in cause
    assert "保留现场" in action


def test_the_record_never_carries_exception_text_or_credentials():
    """Only the class name travels; messages are where URLs and tokens hide."""

    fault = build_diagnostic(
        "SHEETS_READ_UNAVAILABLE",
        site="Google Sheets",
        cause_class="SSLEOFError",
        first_seen=NOW,
        last_seen=NOW,
    )
    payload = str(fault.to_dict())

    assert "SSLEOFError" in payload
    for secret in ("Bearer", "ya29.", "cookie", "Cookie", "access_token"):
        assert secret not in payload


def test_a_resolved_fault_is_reported_as_resolved_not_as_a_live_fault():
    fault = build_diagnostic("BROWSER_WAITING_RECOVERY", site="Browser/CDP",
                             first_seen=NOW, last_seen=NOW)
    resolved = FaultDiagnostic.from_dict(
        {**fault.to_dict(), "recovered_at": (NOW + timedelta(minutes=5)).isoformat()})

    assert not resolved.active
    assert fault_block(resolved).startswith("【已恢复】")


def test_diagnostics_round_trip_through_the_stored_json():
    fault = build_diagnostic("GOOGLE_OUTAGE_THREE_HOURS", site="Google Sheets",
                             first_seen=NOW, last_seen=NOW, occurrences=2)

    restored = FaultDiagnostic.from_dict(fault.to_dict())

    assert restored == fault


def _snapshot(faults):
    return WorkbenchSnapshot(
        1, RunSession(None, RunState.STOPPED, None, None),
        HealthReport((), "需要人工处理"), faults=faults)


def test_the_snapshot_defaults_to_no_faults():
    """An old caller that does not know about faults must keep working."""

    assert _snapshot(()).faults == ()


def _store(tmp_path):
    database = tmp_path / "workflow.sqlite3"
    WorkflowStateStore(database)  # The supported V1.1 baseline this ledger migrates from.
    migrate_v12(database, tmp_path / "backups", quiesce=lambda: nullcontext(), clock=lambda: NOW)
    return V12Store(database), database


def _append_command(database, command_id, proof, created_at):
    import json

    with sqlite3.connect(database) as db:
        db.execute(
            "INSERT INTO workflow_v12_notification_commands"
            " (command_id, inquiry_id, kind, subject, text_body, html_body, created_at,"
            "  payload_version, review_json, suppression_reason)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (command_id, "inq_000000000000000000000000", "PURCHASE_EXCEPTION", "s", "t", None,
             created_at, 2, json.dumps(proof), None))
        db.commit()


def test_an_unresolved_fault_survives_a_restart(tmp_path):
    """Closing the window must not erase the reason the Owner needs to act on."""

    _sqlite_store, database = _store(tmp_path)
    fault = build_diagnostic("SHEETS_READ_UNAVAILABLE", site="Google Sheets",
                             cause_class="SSLEOFError", first_seen=NOW, last_seen=NOW)
    _append_command(database, "incident:one:1",
                    {"active": True, "diagnostic": fault.to_dict()},
                    "2026-11-17T09:55:08+00:00")

    restored = V12Store(database).recent_fault_diagnostics()

    assert [item.code for item in restored] == ["SHEETS_READ_UNAVAILABLE"]
    assert restored[0].cause_class == "SSLEOFError"
    assert restored[0].first_seen == fault.first_seen


def test_a_settled_incident_is_history_and_is_not_shown_as_live(tmp_path):
    _sqlite_store, database = _store(tmp_path)
    fault = build_diagnostic("SHEETS_READ_UNAVAILABLE", site="Google Sheets",
                             first_seen=NOW, last_seen=NOW)
    _append_command(database, "incident:one:1",
                    {"active": False, "diagnostic": fault.to_dict()},
                    "2026-11-17T09:55:08+00:00")

    assert V12Store(database).recent_fault_diagnostics() == ()


def test_the_same_code_is_reported_once_with_its_latest_occurrence(tmp_path):
    _sqlite_store, database = _store(tmp_path)
    fault = build_diagnostic("SHEETS_READ_UNAVAILABLE", site="Google Sheets",
                             first_seen=NOW, last_seen=NOW)
    for index, minute in enumerate((0, 5, 9)):
        _append_command(database, f"incident:one:{index}",
                        {"active": True, "diagnostic": fault.to_dict()},
                        f"2026-11-17T09:5{minute}:00+00:00")

    restored = V12Store(database).recent_fault_diagnostics()

    assert len(restored) == 1


def test_a_row_without_a_diagnostic_is_ignored(tmp_path):
    _sqlite_store, database = _store(tmp_path)
    _append_command(database, "incident:legacy:1", {"active": True},
                    "2026-11-17T09:55:08+00:00")

    assert V12Store(database).recent_fault_diagnostics() == ()


def test_the_stop_records_the_fault_and_whether_three_hours_applied(tmp_path, monkeypatch):
    """2026-11-17 17:55: one transient read stopped everything, not a 3h outage."""

    from src.workflow.v12_faults import FaultScope, V12Fault
    from tests.launcher.test_runtime_safety_notice import harness

    backend, _worker, _smtp = harness(tmp_path, monkeypatch)
    backend._runtime_error(V12Fault(FaultScope.GLOBAL_STOP, "SHEETS_READ_UNAVAILABLE"))

    faults = backend._fault_diagnostics()
    assert [item.code for item in faults] == ["SHEETS_READ_UNAVAILABLE"]
    fault = faults[0]
    assert fault.site == "Google Sheets"
    assert fault.related_modules == ("询价采购", "报价跟进", "目标价调研")
    assert "没有达到三小时升级门限" in fault.escalation
    assert "三小时未恢复" not in fault.escalation
    assert backend._state is RunState.MODULE_PAUSED


def test_a_recovered_site_marks_the_fault_resolved(tmp_path, monkeypatch):
    from src.workflow.v12_faults import FaultScope, V12Fault
    from tests.launcher.test_runtime_safety_notice import harness

    backend, _worker, _smtp = harness(tmp_path, monkeypatch)
    backend._runtime_error(V12Fault(FaultScope.GLOBAL_STOP, "SHEETS_READ_UNAVAILABLE"))
    assert backend._fault_diagnostics()[0].active

    backend._resolve_faults(site="Google Sheets")

    assert not backend._fault_diagnostics()[0].active
    assert backend._fault_diagnostics()[0].phase == "已恢复"


def test_the_cause_label_keeps_only_a_class_name_and_a_stable_code(tmp_path):
    """A CDP sub-reason must reach the page; a free-text message must not."""

    from src.launcher.backend import ProductionBackend
    from src.launcher.browser_bootstrap import BrowserBootstrapError

    backend = ProductionBackend(root=tmp_path)
    coded = BrowserBootstrapError("CDP_ATTACH_FAILED")
    assert backend._fault_cause_label(coded) == "BrowserBootstrapError(CDP_ATTACH_FAILED)"

    free_text = BrowserBootstrapError("approved Chrome failed to launch")
    assert backend._fault_cause_label(free_text) == "BrowserBootstrapError"

    outer = RuntimeError("wrapper")
    outer.__cause__ = coded
    assert backend._fault_cause_label(outer) == "BrowserBootstrapError(CDP_ATTACH_FAILED)"


# --- CEO RFQ-022 review P1-A: a deferred read must still reach the GUI --------

def _tls_fault():
    from tests.launcher.test_google_transient_read_recovery import _tls_fault as build

    return build()


def test_a_recoverable_read_failure_still_reaches_the_gui(tmp_path, monkeypatch):
    """No mail, no alert, no stop -- but the Owner must still see the reason.

    This is the most common fault path after the TLS fix: the reader retries next
    round. Recording it only in the log is exactly the hole the Owner reported.
    """
    from datetime import timedelta

    from tests.launcher.test_runtime_safety_notice import NOW as RUN_NOW
    from tests.launcher.test_runtime_safety_notice import harness

    backend, worker, smtp = harness(tmp_path, monkeypatch)
    assert backend._defer_website_poll(_tls_fault(), timedelta(minutes=15),
                                       notify=False, recoverable_read=True)

    faults = backend._fault_diagnostics()
    assert [item.code for item in faults] == ["GOOGLE_WAITING_RECOVERY"]
    fault = faults[0]
    assert fault.site == "Google Sheets"
    assert fault.occurrences == 1
    assert fault.next_retry_at == (RUN_NOW + timedelta(minutes=15)).isoformat()
    assert "未停止" in fault.escalation
    # A deferral must never read like a shared stop on the page.
    assert "没有停止任何模块" in fault.impact
    assert "未停止" not in fault.impact
    assert backend._state is RunState.RUNNING and not backend._stop.is_set()

    worker.run_due(now=NOW)
    assert smtp.send_attempts == 0                              # never a nuisance mail
    assert backend._v12_store.recent_fault_diagnostics() == ()   # never a durable incident


def test_a_deferred_read_counts_up_and_clears_on_a_real_recovery(tmp_path, monkeypatch):
    from datetime import timedelta

    from tests.launcher.test_runtime_safety_notice import harness

    backend, _worker, _smtp = harness(tmp_path, monkeypatch)
    for _ in range(3):
        backend._defer_website_poll(_tls_fault(), timedelta(minutes=15),
                                    notify=False, recoverable_read=True)
    fault = backend._fault_diagnostics()[0]
    assert fault.occurrences == 3
    assert fault.first_seen == fault.last_seen

    backend._site_recovered("Google Sheets")
    recovered = backend._fault_diagnostics()[0]
    assert not recovered.active
    assert recovered.next_retry_at is None
    assert backend.get_workbench_snapshot().faults[0].code == "GOOGLE_WAITING_RECOVERY"


# --- CEO RFQ-022 review P1-B: recovery must be durable ------------------------

def test_recovery_settles_the_durable_incident_so_a_restart_stays_quiet(tmp_path, monkeypatch):
    from src.workflow.v12_faults import FaultScope, V12Fault
    from src.workflow.v12_store import V12Store
    from tests.launcher.test_runtime_safety_notice import harness

    backend, _worker, _smtp = harness(tmp_path, monkeypatch)
    backend._runtime_error(V12Fault(FaultScope.GLOBAL_STOP, "SHEETS_READ_UNAVAILABLE"))
    path = backend._v12_store.database_path
    assert [f.code for f in V12Store(path).recent_fault_diagnostics()] == ["SHEETS_READ_UNAVAILABLE"]

    backend._resolve_faults(site="Google Sheets")

    assert not backend._fault_diagnostics()[0].active
    # The restart view is a fresh read of the same ledgers, nothing from memory.
    assert V12Store(path).recent_fault_diagnostics() == ()


def test_an_inquiry_only_recovery_also_settles_the_durable_incident(tmp_path, monkeypatch):
    """Quotation may stay closed while inquiry recovers; the stop must still settle."""
    from src.workflow.v12_faults import FaultScope, V12Fault
    from src.workflow.v12_store import V12Store
    from tests.launcher.test_runtime_safety_notice import harness

    backend, _worker, _smtp = harness(tmp_path, monkeypatch)
    backend._runtime_error(V12Fault(FaultScope.GLOBAL_STOP, "SHEETS_READ_UNAVAILABLE"))
    backend._resolve_faults_after_success("inquiry")

    assert V12Store(backend._v12_store.database_path).recent_fault_diagnostics() == ()


def test_settling_a_runtime_incident_leaves_order_alerts_alone(tmp_path, monkeypatch):
    from src.workflow.v12_faults import FaultScope, V12Fault
    from tests.launcher.test_runtime_safety_notice import harness

    backend, _worker, _smtp = harness(tmp_path, monkeypatch)
    backend._runtime_error(V12Fault(FaultScope.GLOBAL_STOP, "SHEETS_READ_UNAVAILABLE"))
    import sqlite3

    def alert_rows():
        with sqlite3.connect(backend._v12_store.database_path) as db:
            return db.execute("SELECT count(*) FROM workflow_v12_active_alerts").fetchone()[0]

    before = alert_rows()
    backend._resolve_faults(site="Google Sheets")
    assert alert_rows() == before


# --- CEO RFQ-022 review P2: one order's exception must name a real action -----

def _order(model="SYNTH", *, sheet="2026", row=982):
    from types import SimpleNamespace

    return SimpleNamespace(inquiry_id="inq_" + "a" * 24, model=model, module_id="inquiry",
                           source_sheet=sheet, source_row=row)


def _state(*codes):
    from types import SimpleNamespace

    return SimpleNamespace(active_alerts=tuple(
        SimpleNamespace(reason_code=SimpleNamespace(value=code)) for code in codes))


def test_an_order_exception_names_the_reason_and_the_next_step():
    from src.gui.workbench import order_exception_block

    block = order_exception_block(_order(), _state("SAVE_OUTCOME_UNKNOWN"), "需核对")

    assert "原因：保存后没有收到确认回执" in block
    assert "建议：先到 INSO 核对" in block
    assert "位置：2026 第 982 行" in block
    assert "本单停在已记录状态" not in block


def test_an_unclassified_order_alert_admits_the_cause_is_unconfirmed():
    from src.gui.workbench import order_exception_block

    block = order_exception_block(_order(), _state("SOMETHING_NEW"), "需核对")

    assert "原因尚未确认" in block
    assert "SOMETHING_NEW" in block
    assert "建议：" in block


def test_an_order_without_a_reason_is_not_given_an_invented_cause():
    from src.gui.workbench import order_exception_block

    block = order_exception_block(_order(), _state(), "需核对")

    assert "没有记录到带原因的异常" in block
    assert "原因：" not in block


def test_the_write_ledger_statement_is_proven_not_guessed(tmp_path, monkeypatch):
    """A stop must not claim "ledger unreadable" because of a wrong import.

    The first cut imported a class that does not exist, so every shared stop
    would have told the Owner the write ledger was unreadable even when it was
    clean and empty.
    """
    from src.workflow.write_intents import SqliteWriteIntentJournal
    from tests.launcher.test_runtime_safety_notice import harness

    backend, _worker, _smtp = harness(tmp_path, monkeypatch)
    SqliteWriteIntentJournal(backend._v12_store.database_path).migrate()

    assert "没有未结清的外部写入意图" in backend._external_effect_state()


def test_an_unreadable_write_ledger_is_reported_as_unproven(tmp_path, monkeypatch):
    from tests.launcher.test_runtime_safety_notice import harness

    backend, _worker, _smtp = harness(tmp_path, monkeypatch)
    # No journal table at all: an absent ledger is not a clean ledger.
    assert "写入台账不可读" in backend._external_effect_state()


def test_the_page_block_separates_a_deferral_from_a_shared_stop():
    from src.gui.workbench import fault_block

    deferred = build_diagnostic("GOOGLE_WAITING_RECOVERY", site="Google Sheets",
                                first_seen=NOW, last_seen=NOW, deferred=True)
    stop = build_diagnostic("SHEETS_READ_UNAVAILABLE", site="Google Sheets",
                            first_seen=NOW, last_seen=NOW)

    deferred_block = fault_block(deferred)
    assert "业务影响：本轮只推迟了这一步" in deferred_block
    assert "本次停止了" not in deferred_block

    stop_block = fault_block(stop)
    assert "业务影响：本次停止了 询价采购、报价跟进、目标价调研" in stop_block


# --- CEO RFQ-022 closure: a scoped recovery must not settle another order -----

def _two_order_ledger(tmp_path):
    """A (authorised) and B (not authorised), plus program-level evidence."""
    from src.workflow.v12_store import V12Store
    from src.workflow.v13_integration import V13HoldStore
    from tests.workflow.test_rfq021_r5_incident_scope import (
        INQUIRY as A,
    )
    from tests.workflow.test_rfq021_r5_incident_scope import (
        OTHER as B,
    )
    from tests.workflow.test_rfq021_r5_incident_scope import (
        _database,
        _incident,
    )

    store = V12Store(_database(tmp_path / "workflow.sqlite3"))
    V13HoldStore(store.database_path).migrate()
    code = "SHEETS_READ_UNAVAILABLE"
    ids = {
        "a": "incident:a:0",
        "b": "incident:b:0",
        "program": "incident:program:0",
        "b_site": "incident:bsite:0",
    }
    _incident(store, command_id=ids["a"], inquiry_id=A, module="business_runtime",
              proof={"inquiry_id": A, "diagnostic": {"code": code}})
    _incident(store, command_id=ids["b"], inquiry_id=B, module="business_runtime",
              proof={"inquiry_id": B, "diagnostic": {"code": code}})
    _incident(store, command_id=ids["program"], inquiry_id=A, module="business_runtime",
              proof={"diagnostic": {"code": code}})
    _incident(store, command_id=ids["b_site"], inquiry_id=B, module="Google Sheets",
              proof={"inquiry_id": B, "diagnostic": {"code": code}})
    return store, ids, A, B


def _scoped_backend(store, backends_scope):
    from types import SimpleNamespace

    from src.gui.contracts import RunState
    from src.launcher.backend import ProductionBackend

    backend = ProductionBackend(root=store.database_path.parent)
    backend._v12_store = store
    backend._v13_ledger_ready = True
    backend._run_id = "scoped-run"
    backend._state = RunState.RUNNING
    backend._enforce_scope = True
    backend._run_scope = SimpleNamespace(inquiry_ids=frozenset({backends_scope}))
    return backend


def test_a_scoped_recovery_never_settles_another_orders_incident(tmp_path):
    """CEO 2026-11-18: the persistence path must honour the order scope.

    Order A recovers. Its own incident and the program-level record settle; B's
    records -- same module, same diagnostic code, different order -- must stay
    active, or the next real outage looks "already recovered".
    """
    import sqlite3

    from tests.workflow.test_rfq021_r5_incident_scope import _active

    store, ids, A, _B = _two_order_ledger(tmp_path)
    backend = _scoped_backend(store, A)
    backend._record_fault_diagnostic("SHEETS_READ_UNAVAILABLE", site="Google Sheets")

    def counts():
        with sqlite3.connect(store.database_path) as db:
            return (db.execute("SELECT count(*) FROM workflow_v12_active_alerts").fetchone()[0],
                    db.execute("SELECT count(*) FROM workflow_v13_holds").fetchone()[0])

    before = counts()
    backend._resolve_faults(site="Google Sheets")

    assert _active(store, ids["program"]) is False
    assert _active(store, ids["a"]) is False
    assert _active(store, ids["b"]) is True
    assert _active(store, ids["b_site"]) is True
    assert counts() == before


def test_an_unscoped_backend_keeps_the_historical_settlement(tmp_path):
    from tests.workflow.test_rfq021_r5_incident_scope import _active

    store, ids, _A, _B = _two_order_ledger(tmp_path)
    backend = _scoped_backend(store, _A)
    backend._enforce_scope = False
    backend._run_scope = None
    backend._record_fault_diagnostic("SHEETS_READ_UNAVAILABLE", site="Google Sheets")

    backend._resolve_faults(site="Google Sheets")

    assert _active(store, ids["program"]) is False
    assert _active(store, ids["a"]) is False
    assert _active(store, ids["b"]) is False
    assert _active(store, ids["b_site"]) is False


# --- CEO RFQ-022 closure: a scoped recovery must not settle another order -----


def test_a_page_ownership_fault_explains_itself_in_the_gui(tmp_path, monkeypatch):
    """2026-11-18 11:48:45: the installed build showed only "未分类故障"."""
    from src.gui.workbench import fault_block
    from src.research.cdp_pages import PageTargetOwnershipError
    from src.workflow.v12_faults import FaultScope, V12Fault
    from tests.launcher.test_runtime_safety_notice import harness

    backend, _worker, _smtp = harness(tmp_path, monkeypatch)
    marker = ValueError("TAB_TARGET_ID_MISMATCH")
    ownership = PageTargetOwnershipError((marker,))
    ownership.__cause__ = marker
    fault = V12Fault(FaultScope.GLOBAL_STOP, "CDP_PAGE_OWNERSHIP_UNCONFIRMED")
    fault.__cause__ = ownership
    backend._module_contexts = ["quotation"]

    backend._runtime_error(fault)

    item = backend._fault_diagnostics()[0]
    assert item.code == "CDP_PAGE_OWNERSHIP_UNCONFIRMED"
    assert item.title == "Chrome 页面归属无法确认"
    assert item.stage == "quotation"
    assert item.cause_class == "ValueError(TAB_TARGET_ID_MISMATCH)"
    block = fault_block(item)
    assert "发生阶段：报价跟进（quotation）" in block
    assert "targetId" in block
    assert "建议操作：1) 保留当前 Chrome" in block
    assert "未分类故障" not in block


def test_the_ownership_marker_survives_into_the_cause_chain():
    """The GUI can only explain the sub-reason if the raise keeps it."""
    from src.research.cdp_pages import PageTargetOwnershipError

    marker = ValueError("TAB_TARGET_ID_MISMATCH")
    error = PageTargetOwnershipError((marker,))
    assert error.failure_classes == ("ValueError",)
    assert error.reason == "CDP_PAGE_OWNERSHIP_UNCONFIRMED"


def test_a_page_resource_stop_is_tied_to_the_browser_and_can_settle(tmp_path, monkeypatch):
    """Without a site, a hydrated stop could never be settled -> stale red forever."""
    from src.research.cdp_pages import PageTargetOwnershipError
    from src.workflow.v12_faults import FaultScope, V12Fault
    from src.workflow.v12_store import V12Store
    from tests.launcher.test_runtime_safety_notice import harness

    backend, _worker, _smtp = harness(tmp_path, monkeypatch)
    marker = ValueError("TAB_TARGET_ID_MISMATCH")
    ownership = PageTargetOwnershipError((marker,))
    ownership.__cause__ = marker
    fault = V12Fault(FaultScope.GLOBAL_STOP, "CDP_PAGE_OWNERSHIP_UNCONFIRMED")
    fault.__cause__ = ownership
    backend._runtime_error(fault)

    item = backend._fault_diagnostics()[0]
    assert item.site == "Browser/CDP"
    assert item.related_modules == ("询价采购", "报价跟进", "目标价调研")
    path = backend._v12_store.database_path
    assert [f.code for f in V12Store(path).recent_fault_diagnostics()] == [
        "CDP_PAGE_OWNERSHIP_UNCONFIRMED"]

    backend._resolve_faults_after_success("quotation")

    assert not backend._fault_diagnostics()[0].active
    assert V12Store(path).recent_fault_diagnostics() == ()


def test_a_legacy_unclassified_record_picks_up_the_catalogue_wording():
    """The 11-18 record was written before the code had a Chinese explanation."""
    legacy = {
        "code": "CDP_PAGE_OWNERSHIP_UNCONFIRMED",
        "title": "未分类故障（CDP_PAGE_OWNERSHIP_UNCONFIRMED）",
        "cause": "程序记录到故障代码 CDP_PAGE_OWNERSHIP_UNCONFIRMED，但该代码没有已确认的中文说明。",
        "action": "保留现场（日志与数据库）后交给技术处理；不要重复提交采购或报价。",
        "first_seen": "2026-11-18T03:48:45.390478+00:00",
        "last_seen": "2026-11-18T03:48:45.390478+00:00",
        "occurrences": 1,
    }

    restored = FaultDiagnostic.from_dict(legacy)

    assert restored.title == "Chrome 页面归属无法确认"
    assert "targetId" in restored.cause
    assert "保留当前 Chrome" in restored.action
    assert restored.first_seen == legacy["first_seen"]  # the evidence is untouched
