"""Deterministic scheduler cadence verification for V1 final integration."""

from __future__ import annotations

import threading
from datetime import timedelta
from pathlib import Path

import pytest

from src.research import ResearchInput, ResearchResult, ResearchStatus
from src.sheets import (
    IdentifyingSnapshot,
    PendingSheetRecord,
    SheetRecordIdentity,
    WorksheetIdentity,
    WorksheetRow,
)
from src.workflow import (
    WorkflowPoller,
    WorkflowRuntime,
    WorkflowStateStore,
    WorkflowWorker,
)

POLL_INTERVAL = timedelta(minutes=15)


class SyntheticReader:
    def __init__(self) -> None:
        self.polls: list[WorksheetIdentity] = []

    def read_rows(self, worksheet: WorksheetIdentity) -> tuple[WorksheetRow, ...]:
        self.polls.append(worksheet)
        return ()


class RecordingResearch:
    def execute(self, research_input: ResearchInput) -> ResearchResult:
        return ResearchResult(
            research_input.inquiry_id,
            ResearchStatus.SUCCESS,
            resolved_brand="x",
        )


def _pending(row: int, worksheet: str) -> PendingSheetRecord:
    target = WorksheetIdentity("book", worksheet)
    snapshot = IdentifyingSnapshot(
        status="未发",
        importance_raw="A",
        model="MPN",
        brand=None,
        quantity=1,
    )
    identity = SheetRecordIdentity(target, row, snapshot)
    return PendingSheetRecord(
        status="未发",
        importance_raw="A",
        model="MPN",
        brand=None,
        quantity=1,
        row_position=row,
        record_identity=identity,
    )


def test_poll_interval_is_15_minutes(tmp_path: Path) -> None:
    store = WorkflowStateStore(tmp_path / "scheduler.sqlite")
    poller = WorkflowPoller(store, SyntheticReader())
    worker = WorkflowWorker(store, RecordingResearch())
    ws = WorksheetIdentity("book", "2026")
    runtime = WorkflowRuntime(poller, worker, [ws])
    assert runtime.poll_interval == POLL_INTERVAL
    assert runtime.poll_interval == timedelta(minutes=15)


def test_invalid_poll_interval_fails_closed(tmp_path: Path) -> None:
    store = WorkflowStateStore(tmp_path / "scheduler.sqlite")
    poller = WorkflowPoller(store, SyntheticReader())
    worker = WorkflowWorker(store, RecordingResearch())
    ws = WorksheetIdentity("book", "2026")
    with pytest.raises(ValueError):
        WorkflowRuntime(
            poller,
            worker,
            [ws],
            poll_interval=timedelta(0),
        )
    with pytest.raises(ValueError):
        WorkflowRuntime(
            poller,
            worker,
            [ws],
            poll_interval=timedelta(seconds=-1),
        )


def test_run_poller_forever_observes_poll_interval(tmp_path: Path) -> None:
    store = WorkflowStateStore(tmp_path / "scheduler.sqlite")
    reader = SyntheticReader()
    poller = WorkflowPoller(store, reader)
    worker = WorkflowWorker(store, RecordingResearch())
    ws = WorksheetIdentity("book", "2026")
    runtime = WorkflowRuntime(
        poller,
        worker,
        [ws],
        poll_interval=POLL_INTERVAL,
        worker_idle_interval=timedelta(milliseconds=10),
    )

    # Capture every wait timeout the scheduler thread makes. The test body's
    # own stop_event.wait() calls are excluded by recording only after the
    # scheduler thread is started and cleared after we stop it.
    sleeps: list[float] = []

    real_wait = threading.Event.wait
    recording = False

    def fake_wait(self: threading.Event, timeout: float | None = None) -> bool:
        if recording:
            sleeps.append(timeout or 0.0)
        return real_wait(self, 0.0)

    threading.Event.wait = fake_wait  # type: ignore[method-assign]
    stop = threading.Event()
    try:
        thread = threading.Thread(
            target=runtime.run_poller_forever,
            args=(stop,),
            daemon=True,
        )
        recording = True
        thread.start()
        # Let it run a few cycles, then stop.
        real_wait(stop, 0.05)
        recording = False
        stop.set()
        thread.join(timeout=1.0)
    finally:
        threading.Event.wait = real_wait  # type: ignore[method-assign]

    assert sleeps, "scheduler never waited"
    # Every recorded wait must be the poll cadence or a 0.0 from stop_event
    # unblocking — no other value is acceptable.
    for s in sleeps:
        assert s in (0.0, POLL_INTERVAL.total_seconds()), sleeps
    # And there must be at least one full-cadence wait.
    assert any(s == POLL_INTERVAL.total_seconds() for s in sleeps), sleeps
    assert len(reader.polls) >= 1


def test_run_worker_forever_has_separate_idle_interval(tmp_path: Path) -> None:
    """Worker idle interval is independent of poll cadence."""

    store = WorkflowStateStore(tmp_path / "scheduler.sqlite")
    poller = WorkflowPoller(store, SyntheticReader())
    worker = WorkflowWorker(store, RecordingResearch())
    ws = WorksheetIdentity("book", "2026")
    runtime = WorkflowRuntime(
        poller,
        worker,
        [ws],
        poll_interval=POLL_INTERVAL,
        worker_idle_interval=timedelta(milliseconds=50),
    )
    assert runtime.worker_idle_interval == timedelta(milliseconds=50)
    assert runtime.poll_interval != runtime.worker_idle_interval


def test_run_forever_starts_poller_and_worker_threads(tmp_path: Path) -> None:
    """End-to-end scheduler thread orchestration smoke."""

    store = WorkflowStateStore(tmp_path / "scheduler.sqlite")
    reader = SyntheticReader()
    poller = WorkflowPoller(store, reader)
    worker = WorkflowWorker(store, RecordingResearch())
    ws = WorksheetIdentity("book", "2026")
    runtime = WorkflowRuntime(
        poller,
        worker,
        [ws],
        poll_interval=timedelta(milliseconds=20),
        worker_idle_interval=timedelta(milliseconds=10),
    )

    stop = threading.Event()
    thread = threading.Thread(
        target=runtime.run_forever,
        args=(stop,),
        daemon=True,
    )
    thread.start()
    import time

    time.sleep(0.1)
    stop.set()
    thread.join(timeout=1.0)

    # At least one poll should have happened.
    assert reader.polls.count(ws) >= 1
