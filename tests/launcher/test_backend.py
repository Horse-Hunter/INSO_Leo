from __future__ import annotations

import json
import sqlite3
from contextlib import nullcontext
from datetime import datetime, timezone
from decimal import Decimal
from threading import Event, Lock, Thread
from time import monotonic, sleep
from types import SimpleNamespace
from typing import ClassVar

import pytest

from src.gui.contracts import (
    RunState,
    SiteLoginOutcome,
    SiteLoginResult,
)
from src.launcher import backend as launcher
from src.launcher.backend import (
    ProductionBackend,
    _decimal,
    _PreparedDuplicateChecker,
)
from src.launcher.browser_bootstrap import BrowserBootstrapError, BrowserHandle
from src.launcher.inso_session import InsoSessionOutcome, InsoSessionStatus
from src.research import ResearchInput, ResearchResult, ResearchStatus
from src.research.excel_output import ResearchExcelOutput
from src.research.service import ResearchService
from src.sheets import (
    CustomerNameSource,
    IdentifyingSnapshot,
    PendingSheetRecord,
    SheetRecordIdentity,
    WorksheetIdentity,
)
from src.workflow import WorkflowStateStore, WorkflowStatus, WorkflowWorker
from src.workflow.v12_contracts import (
    BusinessState,
    DeliveryOutcome,
    EventType,
    NotificationTransportResult,
    PurchaseDraftCommand,
    PurchaseDraftResult,
    PurchaseOutcome,
    ReasonCode,
    WorkflowEvent,
)
from src.workflow.v12_smtp_transport import QQSMTPTransport
from src.workflow.v12_store import V12_SCHEMA_VERSION, V12Store, migrate_v12


class _FakeInsoSession:
    def __init__(self, browser_handle):
        self.browser_handle = browser_handle

    def operation_access(self):
        return object()

    def close_after_drain(self):
        if self.browser_handle.owned:
            self.browser_handle.close()


class _FakeDuplicateChecker:
    def __init__(self, _reader):
        pass
    def check(self, inquiry_id, mpn, _quantity, *, at):
        from src.workflow.v12_contracts import DuplicateCheckResult, DuplicateOutcome
        return DuplicateCheckResult(inquiry_id, DuplicateOutcome.CONFIRMED, mpn, at, repeated=False)


@pytest.fixture(autouse=True)
def fake_inso_session_attachment(monkeypatch):
    monkeypatch.setattr(launcher, "InsoDuplicateHistoryChecker", _FakeDuplicateChecker)
    monkeypatch.setattr(QQSMTPTransport, "send_operator_alert", lambda *_a, **_k:
                        SimpleNamespace(outcome=DeliveryOutcome.SENT))
    monkeypatch.setattr(QQSMTPTransport, "send_one", lambda *_a, **_k:
                        NotificationTransportResult(DeliveryOutcome.SENT, ReasonCode.NOTIFICATION_SENT))
    monkeypatch.setattr(
        launcher,
        "attach_inso_research_session",
        lambda _endpoint, browser_handle, **_kwargs: _FakeInsoSession(browser_handle),
    )


def test_run_counters_count_business_completion_not_research_completion(tmp_path):
    backend = ProductionBackend(root=tmp_path)
    backend._inquiries = ["research-only", "sent"]
    backend._store = SimpleNamespace(all_items=lambda: tuple(
        SimpleNamespace(inquiry_id=iid, status=WorkflowStatus.COMPLETED)
        for iid in backend._inquiries))
    states = {"research-only": "ROUTING", "sent": "PURCHASE_RECORDED"}
    backend._v12_store = SimpleNamespace(business_state=lambda iid: SimpleNamespace(value=states[iid]))
    backend._active_inso_inquiry = "research-only"
    status = backend.get_status()
    assert status.orders_found == 2
    assert status.completed == 1
    assert status.in_progress == 1


def test_login_unavailable_result_requests_manual_handling():
    seen = []
    manual = []
    result = ResearchResult(
        "synthetic-inquiry", ResearchStatus.PARTIAL_SUCCESS,
        remarks="立创：登录不可用",
    )
    observer = launcher._Observer(
        SimpleNamespace(execute=lambda _item: result),
        seen.append,
        lambda inquiry_id, remarks="": manual.append((inquiry_id, remarks)),
    )
    item = ResearchInput("synthetic-inquiry", "TEST-1", None, 1, None)

    assert observer.execute(item) is result
    assert seen == ["synthetic-inquiry"]
    # The stop reason travels with the verdict so the alert mail can say which
    # site asked for a human instead of only that something did.
    assert manual == [("synthetic-inquiry", "立创：登录不可用")]


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
        ["未发", None, "A", None, f"SYNTH-MPN-{index}", "Brand", index + 1]
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
    monkeypatch.setattr(QQSMTPTransport, "send_operator_alert", lambda *_args, **_kwargs:
                        SimpleNamespace(outcome=DeliveryOutcome.SENT))
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
    assert backend._v12_composition is not None
    assert isinstance(
        backend._v12_composition.notification_worker._transport, QQSMTPTransport
    )
    with sqlite3.connect(tmp_path / "production.sqlite3") as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == V12_SCHEMA_VERSION
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
                remarks="IC.net：需要人工验证",
            )

    captured["observer"].service = _ChallengeResearch()
    backend._purchase_completion = None  # No inquiry was enqueued in this composition-only fixture.
    with pytest.raises(launcher.ResearchPreparationError):
        captured["observer"].execute(ResearchInput("inq-challenge", "MPN", None, 1, None))
    assert "inq-challenge" in backend._inquiries
    assert "inq-challenge" in backend._manual_inquiries
    assert backend.get_status().state is RunState.MODULE_PAUSED
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
    assert _wait_until(lambda: backend.get_status().state is RunState.GLOBAL_STOP)
    backend._thread.join(timeout=5)

    item = backend._store.all_items()[0]
    assert browser_calls == [True, True, True]
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
    assert _wait_until(lambda: backend.get_status().state is RunState.GLOBAL_STOP)
    backend._thread.join(timeout=5)

    item = backend._store.all_items()[0]
    assert browser_calls == [True, True, True]
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
    assert len(calls) == 1  # Stop interrupts the row cooldown; no second row starts.
    assert callable(research_builder_kwargs[0]["inso_operation_access"])
    assert len(set(calls)) == 1
    assert len(backend._store.all_items()) == 3
    assert sum(item.status is WorkflowStatus.COMPLETED for item in backend._store.all_items()) == 1
    assert backend.get_status().state is RunState.STOPPED
    backend.shutdown()


def test_startup_releases_a_research_claim_left_by_an_interrupted_run(
    tmp_path, monkeypatch
):
    production, research_config, _rows = _write_runtime_configs(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    database = tmp_path / "production.sqlite3"
    store = WorkflowStateStore(database)
    identity = SheetRecordIdentity(
        WorksheetIdentity("synthetic-spreadsheet-id", "2026"),
        3,
        IdentifyingSnapshot(
            status="未发",
            importance_raw="A",
            model="SYNTH-MPN-0",
            brand=None,
            quantity=3,
        ),
    )
    store.enqueue(
        PendingSheetRecord(
            status="未发",
            importance_raw="A",
            model="SYNTH-MPN-0",
            brand=None,
            quantity=3,
            row_position=3,
            record_identity=identity,
        ),
        now=now,
    )
    stranded = store.claim_due(now=now)
    assert stranded is not None
    assert stranded.status is WorkflowStatus.RESEARCHING

    # Model the state production is really in after a hard kill: the row was
    # polled once, so V1.2 already knows it, and the process died with Research
    # in flight.
    migrate_v12(database, tmp_path / "backups", quiesce=lambda: nullcontext(), clock=lambda: now)
    v12_store = V12Store(database)
    v12_store.set_business_state(
        stranded.inquiry_id,
        BusinessState.RESEARCHING,
        WorkflowEvent(
            "evt_stranded",
            stranded.inquiry_id,
            EventType.RESEARCH_STARTED,
            now,
            "workflow",
        ),
    )
    v12_store.record_customer_snapshot(
        stranded.inquiry_id, "SHAHAB", CustomerNameSource.SHAHAB_FIXED, at=now
    )

    monkeypatch.setattr(
        launcher,
        "build_read_only_google_sheets_service",
        lambda _path: _SheetsService([], Event()),
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
            execute=lambda item: ResearchResult(item.inquiry_id, ResearchStatus.SUCCESS)
        ),
    )
    backend = ProductionBackend(
        config_path=research_config,
        production_config_path=production,
        cdp_probe=lambda _url: True,
        browser_acquirer=lambda *_args, **_kwargs: BrowserHandle(owned=False),
    )

    backend.start()
    # The worker thread owns startup, so the store only appears once the thread
    # has opened the database. Polling it before then would dereference None.
    assert _wait_until(lambda: backend._store is not None, timeout=8), (
        "the worker thread never finished starting up"
    )
    assert _wait_until(
        lambda: backend._store.get(stranded.id).status is WorkflowStatus.MANUAL_REVIEW,
        timeout=8,
    ), "an interrupted inquiry must be quarantined, never resumed automatically"
    assert backend._v12_store.business_state(stranded.inquiry_id) is BusinessState.INTERRUPTED_UNSENT

    backend.request_stop_after_cycle()
    backend._thread.join(timeout=5)
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
    assert backend.get_status().state is RunState.MODULE_PAUSED
    assert backend.get_health().overall == "需要人工处理"
    assert any("需要人工处理" in entry.message for entry in backend.get_logs())
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
    assert backend.get_status().state is RunState.MODULE_PAUSED
    assert backend.get_health().overall == "需要人工处理"
    assert any("RuntimeError" in entry.message for entry in backend.get_logs())
    backend.shutdown()


def test_research_playwright_provider_shares_then_releases_the_live_session():
    """Research must reuse the launcher's live CDP attachment, never reopen one.

    Before the session exists (and after it is released) the provider yields
    nothing, so each source falls back to its own connection instead of failing.
    """

    backend = ProductionBackend()
    assert backend._browser_handle is None
    assert backend._research_playwright_provider() is None

    class _FakePlaywright:
        stopped = False

        def stop(self) -> None:
            self.stopped = True

    playwright = _FakePlaywright()
    browser = object()
    backend._browser_handle = BrowserHandle(
        owned=False, playwright=playwright, browser=browser
    )
    assert backend._research_playwright_provider() == (playwright, browser)

    backend._browser_handle.disconnect()
    assert playwright.stopped is True
    assert backend._research_playwright_provider() is None
    backend.shutdown()


def test_duplicate_check_prepares_the_inso_session_first():
    """The repeat lookup runs before Research, so it must attach INSO itself.

    Without this the first duplicate lookup of a run reached INSO before the
    shared session existed and every check downgraded to
    ``DUPLICATE_LOOKUP_UNAVAILABLE`` -- recorded six times in the Owner's real
    runtime.
    """

    calls: list[str] = []

    class _FakeChecker:
        def check(self, inquiry_id, mpn, quantity, *, at):
            calls.append(f"check:{inquiry_id}:{mpn}")
            return "result"

    def _prepare() -> None:
        calls.append("prepare")

    checker = _PreparedDuplicateChecker(_FakeChecker(), _prepare)
    assert checker.check("inq_1", "MPN-1", 5, at="now") == "result"
    assert calls == ["prepare", "check:inq_1:MPN-1"]


def test_duplicate_check_still_delegates_when_preparation_fails():
    """A failure to attach INSO must stay a fail-closed non-decision.

    The checker owns that downgrade; preparation only ever adds availability.
    """

    class _FakeChecker:
        def check(self, inquiry_id, mpn, quantity, *, at):
            return "unavailable"

    def _prepare() -> None:
        raise RuntimeError("synthetic bootstrap failure")

    checker = _PreparedDuplicateChecker(_FakeChecker(), _prepare)
    with pytest.raises(RuntimeError):
        checker.check("inq_1", "MPN-1", 5, at="now")


def test_duplicate_check_without_a_preparer_is_a_passthrough():
    class _FakeChecker:
        def check(self, inquiry_id, mpn, quantity, *, at):
            return "result"

    checker = _PreparedDuplicateChecker(_FakeChecker())
    assert checker.check("inq_1", "MPN-1", 5, at="now") == "result"


class _StubPlaywright:
    def stop(self) -> None:  # pragma: no cover - teardown only
        pass


def test_idle_release_never_steals_the_session_from_an_in_flight_poll():
    """The worker tick runs every second but must not release mid-flow.

    Releasing while the poll still owns the shared INSO session tore it out from
    under the duplicate lookup and Research, so every real attempt failed.
    """

    class _FakeSession:
        closed = False

        def close_after_drain(self) -> None:
            self.closed = True

    backend = ProductionBackend()
    session = _FakeSession()
    backend._browser_handle = BrowserHandle(
        owned=False, playwright=_StubPlaywright(), browser=object()
    )
    backend._inso_session = session
    backend._research_ready = True

    backend._poll_idle.clear()  # a poll is mid-flow
    backend._release_idle_browser()
    assert backend._inso_session is session
    assert backend._research_ready is True
    assert session.closed is False

    backend._poll_idle.set()  # the due-work batch is drained
    backend._release_idle_browser()
    assert backend._inso_session is None
    assert backend._research_ready is False
    assert session.closed is True
    backend.shutdown()


def test_forced_idle_release_still_cleans_up_during_a_poll():
    """Shutdown and preparation failures must never be blocked by the guard."""

    class _FakeSession:
        closed = False

        def close_after_drain(self) -> None:
            self.closed = True

    backend = ProductionBackend()
    session = _FakeSession()
    backend._browser_handle = BrowserHandle(
        owned=False, playwright=_StubPlaywright(), browser=object()
    )
    backend._inso_session = session
    backend._research_ready = True
    backend._poll_idle.clear()

    backend._release_idle_browser(force=True)
    assert backend._inso_session is None
    assert session.closed is True
    backend.shutdown()


def test_idle_release_from_the_worker_thread_parks_the_client_for_its_owner():
    """The runtime acquires the Playwright client on the poller thread and releases
    the idle session from the worker thread. Stopping it there raises
    greenlet.error and orphans the driver process, so the release must park the
    client for the owning thread."""

    class _RecordingPlaywright:
        def __init__(self) -> None:
            self.stops = 0

        def stop(self) -> None:
            self.stops += 1

    class _FakeSession:
        def close_after_drain(self) -> None:
            # Mirrors InsoResearchSession.close_after_drain for a REUSED handle.
            handle.disconnect()

    backend = ProductionBackend()
    client = _RecordingPlaywright()
    handle = BrowserHandle(owned=False, playwright=client, browser=object())
    backend._browser_handle = handle
    backend._inso_session = _FakeSession()
    backend._research_ready = True
    backend._poll_idle.set()

    worker = Thread(target=backend._release_idle_browser, name="worker-like")
    worker.start()
    worker.join(10)

    assert backend._inso_session is None
    assert backend._research_ready is False
    assert client.stops == 0  # parked, never stopped from the releasing thread

    assert BrowserHandle.drain_deferred_stops() == 1  # the owning thread drains it
    assert client.stops == 1
    assert BrowserHandle.drain_deferred_stops() == 0
    backend.shutdown()


class _StubOperationPage:
    """Just enough surface for the live purchase writer to be constructed."""

    url = "https://yingsuo.alperp.cn/"


def _live_writer(form) -> launcher._LivePurchaseDraftWriter:
    return launcher._LivePurchaseDraftWriter(
        lambda: SimpleNamespace(operation_page=lambda: nullcontext(form))
    )


def _purchase_command() -> PurchaseDraftCommand:
    return PurchaseDraftCommand(
        command_id="cmd-live-1",
        inquiry_id="inq-live-1",
        customer_name="Majic",
        customer_tier="B",
        mpn="DRV8833PWR",
        brand="UNKNOWN",
        quantity=300,
        inventory_status="待验证",
        estimated_total=Decimal(2550),
        market_minimum_reference_price=Decimal("8.5"),
        quotation_type="普通询价",
        purchaser="陈熙",
        ai_input="DRV8833PWR      UNKNOWN      300",
    )


def test_the_inso_surface_is_cleared_before_and_after_every_order(monkeypatch) -> None:
    """Owner rule (2026-09-30): each order starts and ends with nothing open.

    The ERP keeps the 采购临时询价 window across orders, so an order that ends
    with it open makes the next order run against the previous order's form --
    which is how one order ended up with two purchasers selected. The clearing
    has to happen on both sides of every order, not only at shutdown.
    """

    steps: list[str] = []
    monkeypatch.setattr(
        launcher.InsoPurchaseWriter,
        "dismiss_order_surface",
        lambda self: not steps.append("clear") and True,
    )

    class _Coordinator:
        def __init__(self, **_kwargs) -> None:
            pass

        def prepare(self, command):
            steps.append("prepare")
            return PurchaseDraftResult(
                command_id=command.command_id,
                outcome=PurchaseOutcome.AI_RECOGNIZED,
                completed_at=datetime.now(timezone.utc),
            )

    monkeypatch.setattr(launcher, "CoordinatorPurchaseDraftWriter", _Coordinator)
    monkeypatch.setattr(launcher, "PlaywrightParentProductFields", lambda _form: object())

    result = _live_writer(_StubOperationPage()).prepare(_purchase_command())

    assert steps == ["clear", "prepare", "clear"]
    assert result.outcome is PurchaseOutcome.AI_RECOGNIZED


def test_a_surface_that_cannot_be_cleared_stops_the_order_first(monkeypatch) -> None:
    """A surface the backend cannot clear must stop the order, not ride on it."""

    steps: list[str] = []
    monkeypatch.setattr(
        launcher.InsoPurchaseWriter,
        "dismiss_order_surface",
        lambda self: not steps.append("clear") and False,
    )

    class _Coordinator:
        def __init__(self, **_kwargs) -> None:
            raise AssertionError("the order must not reach the form")

    monkeypatch.setattr(launcher, "CoordinatorPurchaseDraftWriter", _Coordinator)

    result = _live_writer(_StubOperationPage()).prepare(_purchase_command())

    assert steps == ["clear"]
    assert result.outcome is PurchaseOutcome.VALIDATION_FAILED


# ---------------------------------------------------------------------------
# An expired login must be reported as an expired login.
#
# Owner finding (2026-10-01): the session expired mid-run, the ERP frame was
# therefore absent, and every step failed as CONTROL_NOT_FOUND -- so the run log
# said 采购录单异常 for a login that had simply gone away. Only an expiry that is
# *proven* may be retried; anything else keeps its own honest reason.
# ---------------------------------------------------------------------------


class _StubSessionGuard:
    """Reports a scripted session outcome, one per call."""

    def __init__(self, *outcomes) -> None:
        self._outcomes = list(outcomes)
        self.calls = 0
        self.force_logins: list[bool] = []

    def ensure_authenticated(self, *, force_login: bool = False):
        self.calls += 1
        self.force_logins.append(force_login)
        outcome = (
            self._outcomes.pop(0) if len(self._outcomes) > 1 else self._outcomes[0]
        )
        return InsoSessionStatus(outcome)


def _guarded_live_writer(form, guard) -> launcher._LivePurchaseDraftWriter:
    return launcher._LivePurchaseDraftWriter(
        lambda: SimpleNamespace(operation_page=lambda: nullcontext(form)),
        session_guard_factory=lambda: guard,
    )


def _install_coordinator(monkeypatch, results) -> list[str]:
    """Install a coordinator that replays ``results`` and records each attempt."""

    attempts: list[str] = []

    class _Coordinator:
        def __init__(self, **_kwargs) -> None:
            pass

        def prepare(self, command):
            attempts.append("prepare")
            return results[min(len(attempts) - 1, len(results) - 1)](command)

    monkeypatch.setattr(
        launcher.InsoPurchaseWriter, "dismiss_order_surface", lambda self: True
    )
    monkeypatch.setattr(launcher, "CoordinatorPurchaseDraftWriter", _Coordinator)
    monkeypatch.setattr(launcher, "PlaywrightParentProductFields", lambda _form: object())
    return attempts


def _failed_draft(command) -> PurchaseDraftResult:
    return PurchaseDraftResult(
        command_id=command.command_id,
        outcome=PurchaseOutcome.VALIDATION_FAILED,
        completed_at=datetime.now(timezone.utc),
        reason_code=ReasonCode.CONTROL_NOT_FOUND,
    )


def _recognized_draft(command) -> PurchaseDraftResult:
    return PurchaseDraftResult(
        command_id=command.command_id,
        outcome=PurchaseOutcome.AI_RECOGNIZED,
        completed_at=datetime.now(timezone.utc),
    )


def test_a_failed_draft_is_not_retried_when_the_session_was_never_gone(
    monkeypatch,
) -> None:
    """Only a session that really went is worth retrying.

    The entry call forces a login (Owner rule), so what has to answer "was it
    the session?" honestly is the diagnosis call after the failure. A session
    that proves live leaves the failure exactly as it happened.
    """

    attempts = _install_coordinator(monkeypatch, [_failed_draft])
    guard = _StubSessionGuard(InsoSessionOutcome.AUTHENTICATED)

    result = _guarded_live_writer(_StubOperationPage(), guard).prepare(
        _purchase_command()
    )

    assert attempts == ["prepare"]
    assert result.outcome is PurchaseOutcome.VALIDATION_FAILED
    assert result.reason_code is ReasonCode.CONTROL_NOT_FOUND
    assert guard.force_logins == [True, False]


def test_a_proven_expiry_is_logged_in_and_retried_once(monkeypatch) -> None:
    attempts = _install_coordinator(
        monkeypatch, [_failed_draft, _recognized_draft]
    )
    guard = _StubSessionGuard(
        InsoSessionOutcome.AUTHENTICATED, InsoSessionOutcome.RESTORED
    )

    result = _guarded_live_writer(_StubOperationPage(), guard).prepare(
        _purchase_command()
    )

    assert attempts == ["prepare", "prepare"]
    assert result.outcome is PurchaseOutcome.AI_RECOGNIZED
    assert guard.calls == 2
    assert guard.force_logins == [True, False]


def test_a_session_that_cannot_be_restored_is_reported_as_stale(monkeypatch) -> None:
    attempts = _install_coordinator(monkeypatch, [_failed_draft])
    guard = _StubSessionGuard(InsoSessionOutcome.AUTHENTICATED, InsoSessionOutcome.DEAD)

    result = _guarded_live_writer(_StubOperationPage(), guard).prepare(
        _purchase_command()
    )

    assert attempts == ["prepare"]
    assert result.outcome is PurchaseOutcome.VALIDATION_FAILED
    assert result.reason_code is ReasonCode.SESSION_STALE


def test_a_dead_session_stops_before_the_erp_is_touched(monkeypatch) -> None:
    """A login that cannot be established must not be discovered mid-draft."""

    attempts = _install_coordinator(monkeypatch, [_recognized_draft])
    guard = _StubSessionGuard(InsoSessionOutcome.DEAD)

    result = _guarded_live_writer(_StubOperationPage(), guard).prepare(
        _purchase_command()
    )

    assert attempts == []
    assert result.reason_code is ReasonCode.SESSION_STALE
    assert guard.calls == 1
    assert guard.force_logins == [True]


def test_purchase_session_loss_notifies_the_same_run_stop_callback(monkeypatch):
    calls = []
    guard = _StubSessionGuard(InsoSessionOutcome.DEAD)
    writer = launcher._LivePurchaseDraftWriter(
        lambda: _StubOperationPage(), session_guard_factory=lambda: guard,
        login_problem=lambda inquiry, reason: calls.append((inquiry, reason)),
    )
    result = writer.prepare(_purchase_command())
    assert result.reason_code is ReasonCode.SESSION_STALE
    assert calls == [("inq-live-1", "INSO：登录不可用")]


def test_a_guard_that_cannot_be_built_leaves_the_flow_alone(monkeypatch) -> None:
    """Without a stored credential the pre-existing behaviour stands."""

    attempts = _install_coordinator(monkeypatch, [_failed_draft])

    def _refuse():
        raise RuntimeError("no credential")

    writer = launcher._LivePurchaseDraftWriter(
        lambda: SimpleNamespace(operation_page=lambda: nullcontext(_StubOperationPage())),
        session_guard_factory=_refuse,
    )

    result = writer.prepare(_purchase_command())

    assert attempts == ["prepare"]
    assert result.reason_code is ReasonCode.CONTROL_NOT_FOUND
    assert result.reason_code is ReasonCode.CONTROL_NOT_FOUND


# ---------------------------------------------------------------------------
# 一键登录所有网站
#
# Owner request (2026-10-01): one dashboard button that walks the sites so a
# round of inquiry starts with live sessions, a popup either way, and -- when a
# run later loses a session mid-cycle -- a mail to the one person who can log
# back in, instead of a run that quietly continues with a source missing.
# ---------------------------------------------------------------------------


class _SweepHandle:
    """A browser handle as the sweep sees it: attached, not ours to stop."""

    owned = False

    def __init__(self) -> None:
        self.browser = SimpleNamespace(contexts=(SimpleNamespace(),))
        self.disconnected = False
        self.closed = False

    def disconnect(self) -> None:
        self.disconnected = True

    def close(self) -> None:
        self.closed = True


def _sweep_backend(tmp_path, monkeypatch, results, handle=None):
    production, research_config, _rows = _write_runtime_configs(tmp_path)
    handle = handle or _SweepHandle()
    monkeypatch.setattr(
        launcher, "sweep_sites", lambda _browser, **_kwargs: tuple(results)
    )
    backend = ProductionBackend(
        config_path=research_config,
        production_config_path=production,
        cdp_probe=lambda _url: True,
        browser_acquirer=lambda *_args, **_kwargs: handle,
    )
    return backend, handle


def test_one_click_login_reports_every_site_and_never_stops_the_owners_browser(
    tmp_path, monkeypatch
):
    backend, handle = _sweep_backend(
        tmp_path,
        monkeypatch,
        [
            SiteLoginResult("IC 现货网", SiteLoginOutcome.ALREADY_SIGNED_IN),
            SiteLoginResult("立创商城", SiteLoginOutcome.SIGNED_IN),
            SiteLoginResult(
                "正能量（Bom.Ai）",
                SiteLoginOutcome.NEEDS_HUMAN,
                "站点要求人工验证（滑块／验证码／短信）",
            ),
        ],
    )
    reports = []
    backend.on_login_all(reports.append)

    backend.start_login_all_sites()
    assert _wait_until(lambda: backend.get_login_all_report() is not None)

    report = backend.get_login_all_report()
    assert report is not None
    assert [result.site for result in report.results] == [
        "IC 现货网",
        "立创商城",
        "正能量（Bom.Ai）",
    ]
    assert report.all_signed_in is False
    assert [result.site for result in report.needing_attention] == ["正能量（Bom.Ai）"]
    assert reports and reports[-1] is report
    assert backend.login_all_running() is False

    # The Owner's own Chrome is attached and then let go, never stopped: it
    # holds the persistent profile they also log into by hand.
    assert handle.disconnected is True
    assert handle.closed is False
    backend.shutdown()


def test_a_sweep_that_finds_everything_signed_in_says_so(tmp_path, monkeypatch):
    backend, _handle = _sweep_backend(
        tmp_path,
        monkeypatch,
        [SiteLoginResult("立创商城", SiteLoginOutcome.ALREADY_SIGNED_IN)],
    )
    backend.start_login_all_sites()
    assert _wait_until(lambda: backend.get_login_all_report() is not None)

    report = backend.get_login_all_report()
    assert report is not None and report.all_signed_in is True
    assert report.needing_attention == ()
    backend.shutdown()


def test_a_second_click_while_a_sweep_is_in_flight_does_nothing(tmp_path, monkeypatch):
    release = Event()
    production, research_config, _rows = _write_runtime_configs(tmp_path)

    def slow_sweep(_browser, **_kwargs):
        release.wait(5)
        return (SiteLoginResult("立创商城", SiteLoginOutcome.SIGNED_IN),)

    monkeypatch.setattr(launcher, "sweep_sites", slow_sweep)
    backend = ProductionBackend(
        config_path=research_config,
        production_config_path=production,
        cdp_probe=lambda _url: True,
        browser_acquirer=lambda *_args, **_kwargs: _SweepHandle(),
    )
    backend.start_login_all_sites()
    assert _wait_until(lambda: backend.login_all_running() is True)

    backend.start_login_all_sites()  # idempotent, not a second thread
    release.set()
    assert _wait_until(lambda: backend.get_login_all_report() is not None)
    backend.shutdown()


def test_a_sweep_is_refused_while_a_round_of_inquiry_is_running(tmp_path, monkeypatch):
    backend, handle = _sweep_backend(tmp_path, monkeypatch, [])

    backend._state = RunState.RUNNING
    backend.start_login_all_sites()

    assert backend.login_all_running() is False
    assert handle.disconnected is False
    assert any("正在询价" in entry.message for entry in backend.get_logs())
    backend.shutdown()


def test_a_failed_sweep_setup_is_reported_as_a_site_like_any_other(
    tmp_path, monkeypatch
):
    production, research_config, _rows = _write_runtime_configs(tmp_path)

    def refuse(*_args, **_kwargs):
        raise BrowserBootstrapError("CDP unavailable")

    backend = ProductionBackend(
        config_path=research_config,
        production_config_path=production,
        cdp_probe=lambda _url: False,
        browser_acquirer=refuse,
    )

    backend.start_login_all_sites()
    assert _wait_until(lambda: backend.get_login_all_report() is not None)

    report = backend.get_login_all_report()
    assert report is not None and report.all_signed_in is False
    (result,) = report.results
    assert result.outcome is SiteLoginOutcome.UNAVAILABLE
    assert result.detail
    backend.shutdown()


class _RecordingTransport:
    """Stand in for the SMTP transport and record what was actually sent."""

    sent: ClassVar[list] = []

    def __init__(self, *, config, credentials=None) -> None:
        self.config = config

    def send_operator_alert(self, *, recipient, subject, text_body):
        self.sent.append((self.config, recipient, subject, text_body))
        return SimpleNamespace(outcome=DeliveryOutcome.SENT)

    def send_one(self, command, recipient):
        self.sent.append((self.config, recipient, command.subject, command.text_body))
        return NotificationTransportResult(DeliveryOutcome.SENT, ReasonCode.NOTIFICATION_SENT)


def test_sweep_unexpected_failure_still_publishes_a_popup_report(tmp_path, monkeypatch):
    backend, handle = _sweep_backend(tmp_path, monkeypatch, [])
    def fail(*_args, **_kwargs):
        raise RuntimeError("untrusted page text")
    monkeypatch.setattr(launcher, "sweep_sites", fail)
    backend.start_login_all_sites()
    assert _wait_until(lambda: backend.get_login_all_report() is not None)
    report = backend.get_login_all_report()
    assert not report.all_signed_in
    assert "untrusted" not in str(report)
    assert handle.disconnected and not handle.closed
    backend.shutdown()


def test_start_cannot_overlap_an_active_login_sweep(tmp_path, monkeypatch):
    backend, _handle = _sweep_backend(tmp_path, monkeypatch, [])
    release = Event()
    entered = Event()
    def slow(*_args, **_kwargs):
        entered.set()
        release.wait(5)
        return ()
    monkeypatch.setattr(launcher, "sweep_sites", slow)
    backend.start_login_all_sites()
    assert entered.wait(5)
    backend.start()
    assert backend._thread is None
    assert backend.get_status().state is RunState.STOPPED
    release.set()
    backend.shutdown()


def test_real_poll_seam_stops_batch_on_login_and_resumes_queued_inquiry(tmp_path, monkeypatch):
    production, config, rows = _write_runtime_configs(tmp_path, pending_count=3)
    repaired = False
    calls = []
    _RecordingTransport.sent = []
    monkeypatch.setattr(launcher, "QQSMTPTransport", _RecordingTransport)
    monkeypatch.setattr("src.launcher.v12_composition.QQSMTPTransport", _RecordingTransport)
    monkeypatch.setattr(launcher, "build_read_only_google_sheets_service",
                        lambda _path: _SheetsService(rows, Event()))
    monkeypatch.setattr(launcher, "assess_readiness",
                        lambda *_args, **_kwargs: SimpleNamespace(ready=True, missing_site_ids=()))

    class Research:
        def execute(self, item):
            calls.append(item.inquiry_id)
            return ResearchResult(item.inquiry_id,
                                  ResearchStatus.SUCCESS if repaired else ResearchStatus.PARTIAL_SUCCESS,
                                  remarks="" if repaired else "IC.net：需要人工验证")

    monkeypatch.setattr(launcher, "build_research_service", lambda *_args, **_kwargs: Research())
    backend = ProductionBackend(config_path=config, production_config_path=production,
                                cdp_probe=lambda _url: True,
                                browser_acquirer=lambda *_args, **_kwargs: BrowserHandle(owned=False))
    backend.start()
    backend._thread.join(5)
    assert not backend._thread.is_alive()
    assert len(calls) == 1, "login failure must not continue with the next inquiry"
    assert len(_RecordingTransport.sent) == 1
    assert all(item.status.value == "QUEUED" for item in backend._store.all_items())
    interrupted_id = calls[0]
    assert backend._v12_store.business_state(interrupted_id) is BusinessState.RESEARCH_RETRY_WAIT
    repaired = True
    rows.append(["未发", None, "A", None, "NEW-NORMAL-ROW", "Brand", 1])
    backend.start()
    assert _wait_until(lambda: len(calls) == 2)
    backend.request_stop_after_cycle()
    backend._thread.join(5)
    assert calls.count(interrupted_id) == 1, "the interrupted inquiry must not be resumed"
    assert len([m for m in _RecordingTransport.sent if "异常" in m[2]]) == 1
    backend.shutdown()


@pytest.mark.parametrize("settled,mail_settled", [(False, True), (True, False), (True, True)])
def test_row_completion_stops_next_row_until_submit_status_and_mail_settle(tmp_path, settled, mail_settled):
    backend = ProductionBackend(root=tmp_path)
    backend._state = RunState.RUNNING
    backend._purchase_completion = SimpleNamespace(process=lambda *_a, **_k: settled)
    backend._v12_store = SimpleNamespace(notifications_settled=lambda _iid: mail_settled)
    calls = []
    backend._v12_composition = SimpleNamespace(coordinator=SimpleNamespace(
        run_notifications=lambda **_k: calls.append("notifications")))
    backend._inso_session = SimpleNamespace(close_owned_operation_tab=lambda: calls.append("close"))
    backend._complete_inquiry(SimpleNamespace(inquiry_id="synthetic-inquiry"))
    assert calls == (["notifications", "close"] if settled else ["notifications"])
    assert backend._immediate_stop_requested() == (not settled)
    assert backend._active_inso_inquiry is None and backend._inso_session is None


def test_sweep_never_closes_even_a_browser_it_started():
    handle = _SweepHandle()
    handle.owned = True
    ProductionBackend._release_sweep_browser(handle)
    assert handle.disconnected and not handle.closed


def test_preparation_authentication_failure_stops_and_alerts_only_owner(tmp_path, monkeypatch):
    from src.launcher.inso_session import InsoAuthenticationError
    _RecordingTransport.sent = []
    monkeypatch.setattr(launcher, "QQSMTPTransport", _RecordingTransport)
    backend, _handle = _sweep_backend(tmp_path, monkeypatch, [])
    backend._run_id = "auth-run"
    try:
        raise InsoAuthenticationError("MANUAL_VERIFICATION_REQUIRED")
    except InsoAuthenticationError as auth:
        failure = BrowserBootstrapError("identity not verified")
        failure.__cause__ = auth
    backend._runtime_error(failure)
    assert backend._stop.is_set()
    assert backend.get_status().state is RunState.GLOBAL_STOP
    assert len(_RecordingTransport.sent) == 1
    assert _RecordingTransport.sent[0][1].address == "linan229@qq.com"
    backend.shutdown()


def test_a_run_stopped_by_a_login_problem_mails_only_the_one_address(
    tmp_path, monkeypatch
):
    _RecordingTransport.sent = []
    monkeypatch.setattr(launcher, "QQSMTPTransport", _RecordingTransport)
    production, research_config, _rows = _write_runtime_configs(tmp_path)
    backend = ProductionBackend(
        config_path=research_config,
        production_config_path=production,
        cdp_probe=lambda _url: True,
    )
    backend._run_id = "run-synthetic"

    backend._manual_review("inq-1", "立创：需要人工验证")

    assert backend.get_status().state is RunState.STOPPED  # Other Research sites do not stop V1.2.
    assert len(_RecordingTransport.sent) == 1
    config, recipient, subject, body = _RecordingTransport.sent[0]
    assert recipient.address == "linan229@qq.com"
    assert recipient.address != config.sender_address
    assert "登录" in subject
    assert "立创：需要人工验证" in body
    backend.shutdown()


def test_only_one_mail_per_run_however_many_orders_hit_the_wall(
    tmp_path, monkeypatch
):
    _RecordingTransport.sent = []
    monkeypatch.setattr(launcher, "QQSMTPTransport", _RecordingTransport)
    production, research_config, _rows = _write_runtime_configs(tmp_path)
    backend = ProductionBackend(
        config_path=research_config,
        production_config_path=production,
        cdp_probe=lambda _url: True,
    )
    backend._run_id = "run-synthetic"

    backend._manual_review("inq-1", "立创：需要人工验证")
    backend._manual_review("inq-2", "华强：需要人工验证")
    assert len(_RecordingTransport.sent) == 1, "one interrupted run is one alarm"

    backend._run_id = "run-next"
    backend._manual_review("inq-3", "立创：需要人工验证")
    assert len(_RecordingTransport.sent) == 2, "a new run is a new alarm"
    backend.shutdown()


def test_a_mail_that_cannot_be_sent_never_changes_what_the_run_did(
    tmp_path, monkeypatch
):
    class _Exploding:
        def __init__(self, *, config) -> None:
            self.config = config

        def send_operator_alert(self, **_kwargs):
            raise RuntimeError("smtp unreachable")

    monkeypatch.setattr(launcher, "QQSMTPTransport", _Exploding)
    production, research_config, _rows = _write_runtime_configs(tmp_path)
    backend = ProductionBackend(
        config_path=research_config,
        production_config_path=production,
        cdp_probe=lambda _url: True,
    )
    backend._run_id = "run-synthetic"

    backend._manual_review("inq-1", "")

    assert backend.get_status().state is RunState.STOPPED
    assert any("登录提醒邮件" in entry.message for entry in backend.get_logs())
    backend.shutdown()


def _manual_reasons_for(remarks: str) -> list[tuple[str, str]]:
    """Run one synthetic research result past the observer and report the summons."""

    manual: list[tuple[str, str]] = []
    result = ResearchResult("inq", ResearchStatus.PARTIAL_SUCCESS, remarks=remarks)
    observer = launcher._Observer(
        SimpleNamespace(execute=lambda _item: result),
        lambda _inquiry_id: None,
        lambda inquiry_id, reason="": manual.append((inquiry_id, reason)),
    )
    try:
        observer.execute(ResearchInput("inq", "MPN", None, 1, None))
    except launcher.ResearchPreparationError:
        assert manual
    return manual


def test_every_login_verdict_stops_the_run_but_a_parse_failure_does_not():
    """The stop list is the session verdicts, not every unhappy source."""

    for remarks in (
        "立创：需要人工验证",
        "正能量：账号或密码被站点拒绝",
        "华强：没有可用的登录凭据",
        "IC 现货网：站点登录表单已变化",
        "INSO：登录不可用",
    ):
        assert _manual_reasons_for(remarks) == [("inq", remarks)], remarks

    assert _manual_reasons_for("立创：结果解析失败") == [], (
        "a parse failure is not a lost session and must not stop a run"
    )


def test_releasing_verified_shell_does_not_trigger_a_second_login(monkeypatch):
    backend = ProductionBackend.__new__(ProductionBackend)
    backend._research_gate = Lock()
    backend._browser_handle = object()
    backend._inso_cdp_url = "http://127.0.0.1:9222"
    backend._inso_session = SimpleNamespace(lease=SimpleNamespace(invalidate=lambda: None))
    backend._inso_guard = None
    backend._run_id = "test-run"
    backend._set_health = lambda *_args: None
    calls = []

    def attach(*_args, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr(launcher, "attach_inso_research_session", attach)
    backend._reattach_inso_session()
    assert len(calls) == 1
    assert "login" not in calls[0]
    assert backend._research_ready is True
