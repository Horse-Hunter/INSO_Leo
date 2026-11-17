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
