from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from threading import Event, Lock
from time import monotonic, sleep
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState
from src.launcher import backend as launcher
from src.launcher.backend import ProductionBackend, _decimal
from src.launcher.browser_bootstrap import BrowserBootstrapError, BrowserHandle
from src.research import ResearchInput, ResearchResult, ResearchStatus
from src.research.excel_output import ResearchExcelOutput
from src.research.service import ResearchService
from src.workflow import WorkflowStatus, WorkflowWorker


class _FakeInsoSession:
    def __init__(self, browser_handle):
        self.browser_handle = browser_handle

    def operation_access(self):
        return object()

    def close_after_drain(self):
        if self.browser_handle.owned:
            self.browser_handle.close()


@pytest.fixture(autouse=True)
def fake_inso_session_attachment(monkeypatch):
    monkeypatch.setattr(
        launcher,
        "attach_inso_research_session",
        lambda _endpoint, browser_handle, **_kwargs: _FakeInsoSession(browser_handle),
    )


def test_login_unavailable_result_requests_manual_handling():
    seen = []
    manual = []
    result = ResearchResult(
        "synthetic-inquiry", ResearchStatus.PARTIAL_SUCCESS,
        remarks="立创：登录不可用",
    )
    observer = launcher._Observer(
        SimpleNamespace(execute=lambda _item: result), seen.append, manual.append
    )
    item = ResearchInput("synthetic-inquiry", "TEST-1", None, 1, None)

    assert observer.execute(item) is result
    assert seen == ["synthetic-inquiry"]
    assert manual == ["synthetic-inquiry"]


class _Request:
    def __init__(self, values, called):
        self.values, self.called = values, called

    def execute(self):
        self.called.set()
        return {"values": self.values}


class _Values:
    def __init__(self, values, called):
        self.rows, self.called = values, called

    def get(self, **_kwargs):
        return _Request(self.rows, self.called)


class _Spreadsheets:
    def __init__(self, values, called):
        self.values_api = _Values(values, called)

    def values(self):
        return self.values_api


class _SheetsService:
    def __init__(self, rows, called):
        self.resource = _Spreadsheets(rows, called)

    def spreadsheets(self):
        return self.resource


def _write_runtime_configs(tmp_path, *, pending_count=0):
    client_secret = tmp_path / "oauth-client.json"
    client_secret.write_text("{}", encoding="utf-8")
    production = tmp_path / "production.json"
    production.write_text(
        json.dumps(
            {
                "spreadsheet_id": "synthetic-spreadsheet-id",
                "worksheet_titles": ["2026"],
                "client_secret_file": str(client_secret),
                "sqlite_path": str(tmp_path / "production.sqlite3"),
            }
        ),
        encoding="utf-8",
    )
    research = tmp_path / "research.json"
    research.write_text(
        json.dumps(
            {
                "excel_output_path": str(tmp_path / "research.xlsx"),
                "bom_ai": {
                    "login_url": "https://www.bom.ai/",
                    "result_url_template": "https://www.bom.ai/parts/{mpn}",
                    "username_selector": "#user",
                    "password_selector": "#password",
                    "login_button_selector": "button[type=submit]",
                },
                "inso": {
                    "login_url": "https://example.invalid/",
                    "cdp_url": "http://127.0.0.1:9222",
                    "pagesize": 30,
                },
                "cdp": {"cdp_url": "http://127.0.0.1:9222"},
            }
        ),
        encoding="utf-8",
    )
    rows = [
        ["未发", None, "A", None, f"SYNTH-MPN-{index}", None, index]
        for index in range(pending_count)
    ]
    return production, research, rows


def _wait_until(predicate, timeout=5):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        if predicate():
            return True
        sleep(0.01)
    return bool(predicate())


def test_production_composition_builds_real_seams_without_network(
    tmp_path, monkeypatch
):
    production, research_config, rows = _write_runtime_configs(tmp_path)
    sheets_called = Event()
    readiness_calls = []
    monkeypatch.setattr(
        launcher,
        "build_read_only_google_sheets_service",
        lambda _path: _SheetsService(rows, sheets_called),
    )
    monkeypatch.setattr(
        launcher,
        "assess_readiness",
        lambda *_args, **_kwargs: (
            readiness_calls.append(True)
            or SimpleNamespace(ready=True, missing_site_ids=())
        ),
    )

    import src.research.runtime as research_runtime

    monkeypatch.setattr(
        research_runtime,
        "assess_readiness",
        lambda *_args, **_kwargs: SimpleNamespace(ready=True, missing_site_ids=()),
    )
    captured = {}
    real_worker = WorkflowWorker

    def capture_worker(store, observer, **kwargs):
        captured["observer"] = observer
        return real_worker(store, observer, **kwargs)

    monkeypatch.setattr(launcher, "WorkflowWorker", capture_worker)
    backend = ProductionBackend(
        config_path=research_config, production_config_path=production,
        cdp_probe=lambda _url: True,
        browser_acquirer=lambda *_args, **_kwargs: BrowserHandle(owned=False),
    )
    backend.start()
    assert sheets_called.wait(5), "production Sheets reader was not composed/called"
    assert _wait_until(lambda: backend.get_health().overall == "正常")
    backend.request_stop_after_cycle()
    backend._thread.join(timeout=5)

    assert backend._thread is not None and not backend._thread.is_alive()
    assert readiness_calls
    assert backend._store is not None
    assert backend._store.database_path == tmp_path / "production.sqlite3"
    assert isinstance(captured["observer"].service, ResearchService)
    assert captured["observer"].seen.__self__ is backend
    assert captured["observer"].manual_review.__self__ is backend
    assert backend._last_poll is not None

    # Exercise the Observer seam after composition with a challenge result.
    class _ChallengeResearch:
        def execute(self, item):
            return ResearchResult(
                item.inquiry_id,
                ResearchStatus.RETRYABLE_FAILURE,
                remarks="需要人工验证",
            )

    captured["observer"].service = _ChallengeResearch()
    captured["observer"].execute(ResearchInput("inq-challenge", "MPN", None, 1, None))
    assert "inq-challenge" in backend._inquiries
    assert "inq-challenge" in backend._manual_inquiries
    assert backend.get_status().state is RunState.MANUAL_REVIEW
    assert not backend._drain_due_on_stop.is_set()
    backend.shutdown()


def test_empty_poll_defers_browser_bootstrap_until_an_inquiry_is_due(
    tmp_path, monkeypatch
):
    production, research_config, rows = _write_runtime_configs(tmp_path)
    sheets_called = Event()
    browser_calls = []
    monkeypatch.setattr(
        launcher,
        "build_read_only_google_sheets_service",
        lambda _path: _SheetsService(rows, sheets_called),
    )
    monkeypatch.setattr(
        launcher,
        "assess_readiness",
        lambda *_args, **_kwargs: SimpleNamespace(
            ready=True, missing_site_ids=()
        ),
    )
    monkeypatch.setattr(
        launcher,
        "build_research_service",
        lambda *_args, **_kwargs: SimpleNamespace(execute=lambda _item: None),
    )
    backend = ProductionBackend(
        config_path=research_config,
        production_config_path=production,
        cdp_probe=lambda _url: True,
        browser_acquirer=lambda *_args, **_kwargs: browser_calls.append(True),
    )

    backend.start()
    assert sheets_called.wait(5)
    assert _wait_until(lambda: backend.get_health().overall == "正常")
    assert browser_calls == []
    backend.request_stop_after_cycle()
    backend._thread.join(timeout=5)

    assert backend._thread is not None and not backend._thread.is_alive()
    assert backend.get_status().state is RunState.STOPPED
    backend.shutdown()


def test_browser_bootstrap_failure_enters_manual_review_without_research_retry(
    tmp_path, monkeypatch
):
    production, research_config, rows = _write_runtime_configs(
        tmp_path, pending_count=1
    )
    sheets_called = Event()
    browser_calls = []
    research_calls = []
    monkeypatch.setattr(
        launcher,
        "build_read_only_google_sheets_service",
        lambda _path: _SheetsService(rows, sheets_called),
    )
    monkeypatch.setattr(
        launcher,
        "assess_readiness",
        lambda *_args, **_kwargs: SimpleNamespace(ready=True, missing_site_ids=()),
    )
    monkeypatch.setattr(
        launcher,
        "build_research_service",
        lambda *_args, **_kwargs: SimpleNamespace(
            execute=lambda item: research_calls.append(item)
        ),
    )

    def fail_browser(*_args, **_kwargs):
        browser_calls.append(True)
        raise BrowserBootstrapError("synthetic bootstrap failure")

    backend = ProductionBackend(
        config_path=research_config,
        production_config_path=production,
        cdp_probe=lambda _url: True,
        browser_acquirer=fail_browser,
    )
    backend.start()
    assert sheets_called.wait(5)
    assert _wait_until(lambda: backend.get_status().state is RunState.MANUAL_REVIEW)
    backend._thread.join(timeout=5)

    item = backend._store.all_items()[0]
    assert browser_calls == [True]
    assert research_calls == []
    assert item.status is WorkflowStatus.QUEUED
    assert item.attempt_count == 0
    assert item.next_attempt_at is not None
    assert item.research_status is None
    backend.shutdown()


def test_readiness_failure_closes_owned_browser_without_research_retry(
    tmp_path, monkeypatch
):
    production, research_config, rows = _write_runtime_configs(
        tmp_path, pending_count=1
    )
    sheets_called = Event()
    closed = Event()
    browser_calls = []
    research_calls = []
    monkeypatch.setattr(
        launcher,
        "build_read_only_google_sheets_service",
        lambda _path: _SheetsService(rows, sheets_called),
    )

    def readiness(_url, *, cdp_probe):
        return SimpleNamespace(
            ready=cdp_probe("http://127.0.0.1:9222"),
            missing_site_ids=(),
        )

    monkeypatch.setattr(launcher, "assess_readiness", readiness)
    monkeypatch.setattr(
        launcher,
        "build_research_service",
        lambda *_args, **_kwargs: SimpleNamespace(
            execute=lambda item: research_calls.append(item)
        ),
    )

    def acquire_browser(*_args, **_kwargs):
        browser_calls.append(True)
        return BrowserHandle(owned=True, close_fn=closed.set)

    backend = ProductionBackend(
        config_path=research_config,
        production_config_path=production,
        cdp_probe=lambda _url: False,
        browser_acquirer=acquire_browser,
    )
    backend.start()
    assert sheets_called.wait(5)
    assert _wait_until(lambda: backend.get_status().state is RunState.MANUAL_REVIEW)
    backend._thread.join(timeout=5)

    item = backend._store.all_items()[0]
    assert browser_calls == [True]
    assert closed.is_set()
    assert research_calls == []
    assert item.status is WorkflowStatus.QUEUED
    assert item.attempt_count == 0
    assert item.next_attempt_at is not None
    backend.shutdown()


def test_stop_after_cycle_drains_every_due_item_from_current_poll(
    tmp_path, monkeypatch
):
    production, research_config, rows = _write_runtime_configs(
        tmp_path, pending_count=3
    )
    sheets_called = Event()
    entered_first = Event()
    release_first = Event()
    count_lock = Lock()
    calls = []
    research_builder_kwargs = []
    monkeypatch.setattr(
        launcher,
        "build_read_only_google_sheets_service",
        lambda _path: _SheetsService(rows, sheets_called),
    )
    monkeypatch.setattr(
        launcher,
        "assess_readiness",
        lambda *_args, **_kwargs: SimpleNamespace(ready=True, missing_site_ids=()),
    )

    class _Research:
        def execute(self, item):
            with count_lock:
                calls.append(item.inquiry_id)
                first = len(calls) == 1
            if first:
                entered_first.set()
                assert release_first.wait(5)
            return ResearchResult(item.inquiry_id, ResearchStatus.SUCCESS)

    def build_research(_config, **kwargs):
        research_builder_kwargs.append(kwargs)
        return _Research()

    monkeypatch.setattr(launcher, "build_research_service", build_research)
    backend = ProductionBackend(
        config_path=research_config, production_config_path=production,
        cdp_probe=lambda _url: True,
        browser_acquirer=lambda *_args, **_kwargs: BrowserHandle(owned=False),
    )
    backend.start()
    assert sheets_called.wait(5)
    assert entered_first.wait(5)
    backend.request_stop_after_cycle()
    release_first.set()
    backend._thread.join(timeout=5)

    assert backend._thread is not None and not backend._thread.is_alive()
    assert len(calls) == 3
    assert callable(research_builder_kwargs[0]["inso_operation_access"])
    assert len(set(calls)) == 3
    assert len(backend._store.all_items()) == 3
    assert all(
        item.status is WorkflowStatus.COMPLETED for item in backend._store.all_items()
    )
    assert backend.get_status().state is RunState.STOPPED
    backend.shutdown()


def test_duplicate_start_keeps_one_run_and_shutdown_joins_worker(tmp_path):
    backend = ProductionBackend(production_config_path=tmp_path / "missing.json")
    entered = Event()

    def controlled_run():
        entered.set()
        backend._stop.wait(2)

    backend._run = controlled_run
    backend.start()
    assert entered.wait(1)
    first = backend.run_id
    backend.start()
    assert backend.run_id == first
    assert backend.get_status().state is RunState.RUNNING
    backend.request_stop_after_cycle()
    assert backend.get_status().state is RunState.STOPPING_AFTER_CYCLE
    worker = backend._thread
    worker.join(timeout=2)
    assert worker is not None and not worker.is_alive()
    backend.shutdown()


def test_missing_runtime_fails_closed_to_manual_review(tmp_path):
    backend = ProductionBackend(
        production_config_path=tmp_path / "missing.json",
        config_path=tmp_path / "missing-research.json",
    )
    backend.start()
    backend._thread.join(timeout=2)
    assert backend.get_status().state is RunState.MANUAL_REVIEW
    assert backend.get_health().overall == "需要人工处理"
    assert "需要人工处理" in backend.get_logs()[-1].message
    backend.shutdown()


def test_history_is_cached_and_uses_research_owned_excel(tmp_path, monkeypatch):
    path = tmp_path / "results.xlsx"
    output = ResearchExcelOutput(path)
    output.upsert(
        "older", importance_raw="C", mpn="OLD", quantity=4,
        estimated_total=Decimal("12.50"), market_reference="3.125",
        research_status="SUCCESS",
        processed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    output.upsert(
        "newer", importance_raw="A", mpn="NEW", quantity=2,
        estimated_total=Decimal(8), market_reference="4",
        research_status="MANUAL_REVIEW_REQUIRED",
        processed_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    output.upsert(
        "partial", importance_raw="B", mpn="PARTIAL", quantity=1,
        research_status="PARTIAL_SUCCESS",
        processed_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
    )
    output.upsert(
        "exception", importance_raw="D", mpn="NO-QUOTE", quantity=1,
        research_status="EXCEPTION",
        processed_at=datetime(2026, 1, 4, 12, tzinfo=timezone.utc),
    )
    output.upsert(
        "retryable", importance_raw="D", mpn="RETRYABLE", quantity=1,
        research_status="RETRYABLE_FAILURE",
        processed_at=datetime(2026, 1, 5, tzinfo=timezone.utc),
    )
    backend = ProductionBackend(
        config_path=tmp_path / "missing-research.json",
        production_config_path=tmp_path / "missing-production.json",
    )
    backend._excel = path
    reads = 0
    real_read = ResearchExcelOutput.read_history

    def count_reads(self):
        nonlocal reads
        reads += 1
        return real_read(self)

    monkeypatch.setattr(ResearchExcelOutput, "read_history", count_reads)
    backend._refresh_history(force=True)
    snapshot = backend.get_result_history()
    assert reads == 1
    assert [order.inquiry_id for order in snapshot] == [
        "retryable", "exception", "partial", "newer", "older"
    ]
    assert [order.status.value for order in snapshot] == [
        "异常", "异常", "部分成功", "异常", "成功"
    ]
    assert snapshot[3].importance == "A"
    assert snapshot[4].total_price == Decimal("12.50")
    backend.get_result_history()
    backend._refresh_history()
    assert reads == 1


def test_legacy_history_without_saved_status_does_not_claim_history_as_outcome(tmp_path):
    path = tmp_path / "legacy-results.xlsx"
    ResearchExcelOutput(path).upsert(
        "legacy", importance_raw="B", mpn="LEGACY", processed_at=None
    )
    backend = ProductionBackend(
        config_path=tmp_path / "missing-research.json",
        production_config_path=tmp_path / "missing-production.json",
    )
    backend._excel = path
    backend._refresh_history(force=True)
    assert backend.get_result_history()[0].status.value == "--"


def test_next_poll_deadline_is_explicit_and_cleared_on_stop(tmp_path):
    backend = ProductionBackend(
        config_path=tmp_path / "missing-research.json",
        production_config_path=tmp_path / "missing-production.json",
    )
    backend._state = RunState.RUNNING
    assert backend.get_status().next_poll_at is None
    deadline = datetime(2026, 1, 1, tzinfo=timezone.utc)
    backend._next_poll_at = deadline
    assert backend.get_status().next_poll_at == deadline
    backend.request_stop_after_cycle()
    assert backend.get_status().next_poll_at is None
    assert backend.get_status().state is RunState.STOPPING_AFTER_CYCLE
    backend.shutdown()


def test_session_tracking_and_excel_decimal_display():
    backend = ProductionBackend()
    backend._seen("inq_seen")
    assert backend._inquiries == ["inq_seen"]
    assert _decimal("1586.74\n2000-Findchips") == Decimal("1586.74")
    assert _decimal("无结果") is None


def test_runtime_component_error_stops_poll_and_worker_fail_closed():
    backend = ProductionBackend()
    backend._runtime_error(RuntimeError("synthetic failure"))
    assert backend._stop.is_set()
    assert backend.get_status().state is RunState.MANUAL_REVIEW
    assert backend.get_health().overall == "需要人工处理"
    assert "RuntimeError" in backend.get_logs()[-1].message
    backend.shutdown()
