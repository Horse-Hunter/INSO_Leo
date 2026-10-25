import json
from contextlib import contextmanager
from datetime import timedelta
from threading import Event
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState
from src.launcher import backend as launcher
from src.launcher.google_web import _range
from src.sheets.tp_brief import BRIEF_HEADERS, BriefReader
from tests.launcher import test_google_web as grid
from tests.launcher.test_backend import _write_runtime_configs
from tests.research.test_tp import NOW
from tests.sheets.test_tp_brief import brief
from tests.workflow.test_tp_research import build

web = grid.web  # register the existing synthetic UI fixture


def test_dedicated_native_brief_read_no_new_write_whitelist(web, monkeypatch):
    service, browser, rows, original = web
    monkeypatch.setitem(grid.TITLES, "RFQ_BRIEF", 31)
    rows["RFQ_BRIEF"] = [list(BRIEF_HEADERS), list(brief().values)]
    actual, = BriefReader(service).read("synthetic")
    assert actual.get("target_price") == "2 USD"
    assert original.closed is False and browser.connected
    assert all(p.closed for p in browser.contexts[0].pages[1:])
    for kwargs in ({"range": "'RFQ_BRIEF'!A1:Q"}, {"range": "'RFQ_BRIEF'!H2"}, {}):
        with pytest.raises(ValueError):
            service.update(spreadsheetId="synthetic", valueInputOption="RAW",
                           body={"values": [["FORBIDDEN"]]}, **kwargs).execute()
    with pytest.raises(ValueError):
        service._execute({}, write=True, brief_read=True)
    with pytest.raises(ValueError):
        _range("'RFQ_BRIEF'!A1:Q")  # shared getter/update parser remains closed


def test_manual_tp_uses_same_idle_command_path_and_no_purchase_or_quotation(tmp_path, monkeypatch):
    cycle, _lines, _, transport, _ = build(tmp_path)
    cycle.run("synthetic", now=NOW)
    key = cycle.store.rows()[0]["task_id"]
    backend = launcher.ProductionBackend(root=tmp_path)
    legacy = SimpleNamespace(record_identity=SimpleNamespace(
        worksheet=SimpleNamespace(spreadsheet="synthetic", worksheet="2026"), row_position=10))
    backend._tp, backend._store, backend._manual_reader = cycle, SimpleNamespace(
        all_items=lambda: (), get_by_inquiry_id=lambda _: legacy), object()
    backend._state, backend._next_poll_at = RunState.RUNNING, NOW+timedelta(minutes=15)
    monkeypatch.setattr(launcher, "utc_now", lambda: NOW)
    assert backend.can_order_action(key, "tp")
    assert backend.can_order_action("synthetic-legacy-row", "tp")
    assert backend.request_order_action("synthetic-legacy-row", "tp") is None
    execute = backend._execute_order_action
    def execute_and_stop(request):
        assert backend._manual_busy and not backend._poll_idle.is_set()
        execute(request)
        backend._stop.set()
    monkeypatch.setattr(backend, "_execute_order_action", execute_and_stop)
    monkeypatch.setattr(backend, "_release_idle_browser", lambda **kwargs: None)
    monkeypatch.setattr(backend, "_close_inso_order_tab", lambda **kwargs: None)
    assert backend._wait_between_polls(900)
    assert backend.get_manual_order_result().success
    assert len(cycle.research.calls) == 2
    # First explicit generation used a fake with no next SENT outcome -> UNKNOWN.
    assert len(transport.calls) == 4 and not cycle.store.manual_allowed(key)
    assert any(row.inquiry_id == key for row in backend.get_result_history())


@pytest.mark.parametrize("enabled,frozen,expected", [
    (False, False, False), (True, False, True),
    (None, True, False), (False, True, False),
])
def test_existing_poll_and_fifteen_minute_wait_opt_in_tp_no_extra_thread(tmp_path, monkeypatch, enabled, frozen, expected):
    from src.launcher import tp_composition
    production, config, rows = _write_runtime_configs(tmp_path)
    cfg = json.loads(production.read_text())
    if enabled is not None:
        cfg["tp_enabled"] = enabled
    if frozen:
        monkeypatch.setattr(launcher.sys, "frozen", True, raising=False)
        monkeypatch.setattr(launcher.sys, "executable", str(tmp_path / "INSO_V1.5.exe"))
    production.write_text(json.dumps(cfg))
    calls, scope = [], []
    service = __import__('tests.launcher.test_backend', fromlist=['_SheetsService'])._SheetsService(rows, Event())
    @contextmanager
    def poll_scope():
        scope.append(True)
        try:
            yield
        finally:
            scope.pop()
    service.poll_scope = poll_scope
    monkeypatch.setattr(launcher, "build_google_web_service", lambda *a, **k: service)
    monkeypatch.setattr(launcher, "assess_readiness", lambda *a, **k: SimpleNamespace(missing_site_ids=()))
    monkeypatch.setattr(launcher, "build_research_service", lambda *a, **k: SimpleNamespace())
    def build_tp(**kwargs):
        calls.append("built")
        def run(*a, **k):
            assert not scope  # previous native page pool retired; same serial poll
            calls.append("tp")
        return SimpleNamespace(run=run, issues={}, store=SimpleNamespace(rows=lambda: ()))
    monkeypatch.setattr(tp_composition, "build_tp_cycle", build_tp)
    backend = launcher.ProductionBackend(root=tmp_path, config_path=config,
                                         production_config_path=production)
    # Composition/scheduling only; no Owner notification or credential lookup.
    monkeypatch.setattr(backend, "_alert_owner_of_login", lambda **_kwargs: None)
    waits = []
    def wait(seconds):
        waits.append(seconds)
        backend._stop.set()
        return True
    monkeypatch.setattr(backend, "_wait_between_polls", wait)
    backend._run()
    assert calls == (["built", "tp"] if expected else [])
    assert waits == [900]


def test_tp_site_failure_uses_nullable_outbox_not_fake_v14_inquiry(tmp_path):
    from src.research.source_contracts import (
        EvidenceField,
        ResearchSource,
        SourceEvidence,
        SourceOutcome,
    )
    from src.research.tp import TpSourceResult
    cycle, _, _, _, _ = build(tmp_path)
    backend = launcher.ProductionBackend(root=tmp_path)
    backend._v12_store = cycle.outbox
    def forbidden_lookup(_):
        pytest.fail("TP must not query a fabricated V1.4 inquiry ID")
    backend._store = SimpleNamespace(get_by_inquiry_id=forbidden_lookup)
    result = TpSourceResult(ResearchSource.HQEW, SourceOutcome.SOURCE_UNAVAILABLE,
        SourceEvidence(ResearchSource.HQEW, "TEST-ABC", None, SourceOutcome.SOURCE_UNAVAILABLE,
                       NOW, fields=(EvidenceField("failure_code", "SOURCE_UNAVAILABLE"),)))
    backend._observe_source_failure("tp_synthetic", result)
    assert cycle.outbox.claim_due_notifications(now=launcher.utc_now())


def test_native_brief_schema_fault_local_but_source_schema_remains_shared(web, monkeypatch):
    from src.sheets.tp_brief import TpLocalError
    from src.workflow.v12_faults import V12Fault
    service, _, rows, _ = web
    monkeypatch.setitem(grid.TITLES, "RFQ_BRIEF", 31)
    rows["RFQ_BRIEF"] = [["changed header"]]
    with pytest.raises(TpLocalError, match="TP_BRIEF_SCHEMA_UNAVAILABLE"):
        BriefReader(service).read("synthetic")
    with pytest.raises(V12Fault, match="SHEETS_SCHEMA_UNAVAILABLE"):
        service._headers([["changed header"]], "2026")


@pytest.mark.parametrize("fault", ["schema", "research", "mail", "shared"])
def test_tp_fault_boundary_keeps_ordinary_followup_poll_or_shared_stop(tmp_path, monkeypatch, fault):
    from src.launcher import tp_composition
    from src.sheets.tp_brief import TpLocalError
    from src.workflow import tp_research
    from src.workflow.v12_faults import FaultScope, V12Fault
    cycle_dir = tmp_path / "tp"
    cycle_dir.mkdir()
    cycle, _, _, _, _ = build(cycle_dir)
    error = V12Fault(FaultScope.GLOBAL_STOP, "SYNTHETIC_SHARED_SAFETY_FAULT")
    if fault == "schema":
        cycle.brief = BriefReader(SimpleNamespace(read_brief=lambda _: {"values": [["wrong"]]}))
    else:
        def fail(*a, **k):
            if fault == "shared":
                raise error
            if fault == "mail":
                raise TypeError("synthetic mail data error")
            raise TpLocalError("TP_RESEARCH_FAILED")
        target, name = ((tp_research, "tp_mail") if fault == "mail" else (cycle.research, "execute_tp"))
        monkeypatch.setattr(target, name, fail)
    production, config, rows = _write_runtime_configs(tmp_path)
    cfg = json.loads(production.read_text())
    cfg["tp_enabled"] = True
    production.write_text(json.dumps(cfg))
    service = __import__('tests.launcher.test_backend', fromlist=['_SheetsService'])._SheetsService(rows, Event())
    normal_polls, waits, failures = [], [], []
    @contextmanager
    def scope():
        normal_polls.append(True)
        yield
    service.poll_scope = scope
    monkeypatch.setattr(launcher, "build_google_web_service", lambda *a, **k: service)
    monkeypatch.setattr(launcher, "assess_readiness", lambda *a, **k: SimpleNamespace(missing_site_ids=()))
    monkeypatch.setattr(launcher, "build_research_service", lambda *a, **k: SimpleNamespace())
    monkeypatch.setattr(tp_composition, "build_tp_cycle", lambda **k: cycle)
    backend = launcher.ProductionBackend(root=tmp_path, config_path=config, production_config_path=production)
    def wait(seconds):
        waits.append(seconds)
        if len(waits) == 2:
            backend._stop.set()
            return True
        return False
    monkeypatch.setattr(backend, "_wait_between_polls", wait)
    def runtime_error(exc):
        failures.append(exc)
        backend._stop.set()
    monkeypatch.setattr(backend, "_runtime_error", runtime_error)
    backend._run()
    if fault == "shared":
        assert failures == [error] and len(normal_polls) == 1 and not waits
    else:
        assert not failures and len(normal_polls) == 2 and waits == [900, 900]
        assert cycle.issues


def test_manual_tp_local_failure_reports_failure_without_stopping_other_work(tmp_path, monkeypatch):
    from src.sheets.tp_brief import TpLocalError
    cycle, _, _, _, _ = build(tmp_path)
    cycle.run("synthetic", now=NOW)
    key = cycle.store.rows()[0]["task_id"]
    def fail(*a, **k):
        raise TpLocalError("TP_RESEARCH_FAILED")
    cycle.research.execute_tp = fail
    backend = launcher.ProductionBackend(root=tmp_path)
    backend._tp = cycle
    monkeypatch.setattr(backend, "_refresh", lambda: None)
    backend._execute_order_action(("synthetic-request", key, "tp", None, None))
    assert not backend.get_manual_order_result().success
    assert not backend._stop.is_set()
    assert cycle.store.get(key)["state"] == "FAILED"


def test_manual_tp_does_not_swallow_shared_fault_wrapped_as_local(tmp_path):
    from src.inso.session import SecurityViolation
    from src.sheets.tp_brief import TpLocalError
    cycle, _, _, _, _ = build(tmp_path)
    cycle.run("synthetic", now=NOW)
    key = cycle.store.rows()[0]["task_id"]
    error = TpLocalError("TP_RESEARCH_FAILED")
    error.__cause__ = SecurityViolation("synthetic shared security fault")
    def fail(*a, **k):
        raise error
    cycle.research.execute_tp = fail
    backend = launcher.ProductionBackend(root=tmp_path)
    backend._tp = cycle
    with pytest.raises(TpLocalError) as caught:
        backend._execute_order_action(("synthetic-request", key, "tp", None, None))
    assert caught.value is error


def test_manual_missing_task_local_but_corrupt_order_payload_propagates(tmp_path, monkeypatch):
    cycle, _, _, _, _ = build(tmp_path)
    backend = launcher.ProductionBackend(root=tmp_path)
    backend._tp = cycle
    monkeypatch.setattr(backend, "_refresh", lambda: None)
    backend._execute_order_action(("request", "tp_missing", "tp", None, None))
    assert not backend.get_manual_order_result().success and not backend._stop.is_set()
    cycle.run("synthetic", now=NOW)
    key = cycle.store.rows()[0]["task_id"]
    with cycle.store.connect() as db:
        db.execute("UPDATE workflow_requirements SET order_json='{}' WHERE task_id=?", (key,))
    with pytest.raises(KeyError):
        backend._execute_order_action(("request", key, "tp", None, None))
