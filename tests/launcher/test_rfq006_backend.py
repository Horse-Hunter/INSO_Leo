"""Exercise the production poll thread with synthetic config/Sheets and fake mail."""

import json
from threading import Event
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState
from src.launcher import backend as launcher
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v12_flow import V12WorkflowCoordinator
from src.workflow.v13_integration import V13IntegratedCycle
from tests.launcher.test_backend import (
    _RecordingTransport,
    _SheetsService,
    _wait_until,
    _write_runtime_configs,
)


@pytest.mark.parametrize("fault", [None, FaultScope.V12_PAUSE, FaultScope.GLOBAL_STOP])
def test_canonical_poll_combines_empty_purchase_quotation_and_interruptible_900s_wait(
    tmp_path, monkeypatch, fault
):
    production, rc, rows = _write_runtime_configs(tmp_path)
    cfg = json.loads(production.read_text(encoding="utf-8"))
    cfg.update(
        v13_enabled=True,
        quotation_input={
            "gid": "0",
            "input_row": 1,
            "first_column": 1,
        },
    )
    production.write_text(json.dumps(cfg), encoding="utf-8")
    observed = Event()
    events = []
    monkeypatch.setattr(
        launcher,
        "build_read_only_google_sheets_service",
        lambda _: _SheetsService(rows, Event()),
    )
    monkeypatch.setattr(
        launcher,
        "assess_readiness",
        lambda *a, **k: SimpleNamespace(ready=True, missing_site_ids=()),
    )
    monkeypatch.setattr(
        launcher,
        "build_research_service",
        lambda *a, **k: SimpleNamespace(execute=lambda _: None),
    )
    monkeypatch.setattr(
        "src.launcher.v12_composition.QQSMTPTransport", _RecordingTransport
    )
    monkeypatch.setattr(launcher, "QQSMTPTransport", _RecordingTransport)
    original = V12WorkflowCoordinator.poll_and_process

    def purchase(self, *a, **k):
        events.append("V12")
        if fault:
            raise V12Fault(
                fault,
                "IC_NET_UNAVAILABLE"
                if fault is FaultScope.V12_PAUSE
                else "INSO_AUTHENTICATION_REQUIRED",
            )
        return original(self, *a, **k)

    monkeypatch.setattr(V12WorkflowCoordinator, "poll_and_process", purchase)
    run = V13IntegratedCycle.run

    def quotation(self, *a, **k):
        events.append("V13")
        output = run(self, *a, **k)
        observed.set()
        return output

    monkeypatch.setattr(V13IntegratedCycle, "run", quotation)
    browser_calls = []
    backend = launcher.ProductionBackend(
        config_path=rc,
        production_config_path=production,
        root=tmp_path,
        browser_acquirer=lambda *a, **k: browser_calls.append(True),
    )
    try:
        backend.start()
        if fault is FaultScope.GLOBAL_STOP:
            assert _wait_until(
                lambda: backend.get_status().state is RunState.GLOBAL_STOP
            )
            assert events == ["V12"]
        else:
            assert observed.wait(5)
            assert _wait_until(lambda: backend.get_status().next_poll_at is not None)
            delta = (
                backend.get_status().next_poll_at - backend._last_poll
            ).total_seconds()
            assert 899 <= delta <= 910
            assert events == ["V12", "V13"] and not browser_calls
            expected = RunState.QUOTATION_RUNNING if fault else RunState.RUNNING
            assert backend.get_status().state is expected
            first = backend._thread
            backend.start()
            assert (
                backend._thread is first
            )  # No overlapping scheduler, including purchase pause.
            backend.request_stop_after_cycle()
        backend._thread.join(timeout=5)
        assert not backend._thread.is_alive()
    finally:
        backend.shutdown()


@pytest.mark.parametrize("site,scope", [
    ("FINDCHIPS", None), ("HQEW", None), ("LCSC", None), ("BOM_AI", None),
    ("INSO", FaultScope.GLOBAL_STOP), ("IC_NET", FaultScope.V12_PAUSE),
])
@pytest.mark.parametrize("code", ["MANUAL_VERIFICATION_REQUIRED", "QUERY_TIMEOUT", "RESULT_PARSE_FAILED", "private raw html token=password"])
def test_website_issue_uses_durable_229_alert_dedup_and_preserves_scope(tmp_path, monkeypatch, site, scope, code):
    import sqlite3

    from src.research.source_contracts import ResearchSource, SourceOutcome
    from src.workflow.v12_contracts import DeliveryOutcome
    from src.workflow.v12_notifications import (
        FakeNotificationTransport,
        V12NotificationWorker,
    )
    from tests.research.test_aggregation_service import _result
    from tests.workflow.test_rfq006_integration import fixture
    from tests.workflow.test_v12_flow import NOW
    db, store, _sheets, _holds, ledger, _quotes, _make, _observed = fixture(tmp_path, [])
    monkeypatch.setattr(launcher, "utc_now", lambda: NOW)
    iid = store.all_items()[0].inquiry_id
    backend = launcher.ProductionBackend(root=tmp_path)
    backend._v12_store, backend._store = ledger, store
    backend._state, backend._v13_enabled = RunState.RUNNING, True
    result = _result(ResearchSource[site], SourceOutcome.SOURCE_UNAVAILABLE, failure_code=code)
    expected_scope = scope if site != "INSO" or code == "MANUAL_VERIFICATION_REQUIRED" else None
    for _ in range(2):
        if expected_scope:
            with pytest.raises(V12Fault) as raised:
                backend._observe_source_failure(iid, result)
            assert raised.value.scope is expected_scope
        else:
            backend._observe_source_failure(iid, result)
    if expected_scope is FaultScope.V12_PAUSE:
        backend._active_inso_inquiry = iid
        backend._pause_v12(V12Fault(expected_scope, "IC_NET_UNAVAILABLE"))
    transport = FakeNotificationTransport({"owner": (DeliveryOutcome.RETRYABLE_FAILURE,)})
    V12NotificationWorker(ledger, transport).run_due(now=NOW)
    with sqlite3.connect(db) as c:
        commands = c.execute("SELECT subject,text_body FROM workflow_v12_notification_commands").fetchall()
        assert len(commands) == 1
        assert ResearchSource[site].value in commands[0][1] and iid in commands[0][1] and "MPN" in commands[0][1]
        assert "请人工检查网站登录/可用性" in commands[0][1]
        assert "password" not in commands[0][1] and "private" not in commands[0][1]
        assert c.execute("SELECT address FROM workflow_v12_notification_recipients").fetchall() == [("linan229@qq.com",)]
    if expected_scope is None:
        assert backend._state is RunState.RUNNING and not backend._stop.is_set()
    assert len(store.all_items()) == 1
    backend.shutdown()
