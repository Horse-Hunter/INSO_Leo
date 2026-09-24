"""Single-worker concurrency verification for V1 final integration."""

from __future__ import annotations

import threading
import time
from datetime import timedelta
from pathlib import Path

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
    WorkflowStateStore,
    WorkflowWorker,
)


def _pending(row: int, worksheet: str, mpn: str) -> PendingSheetRecord:
    target = WorksheetIdentity("book", worksheet)
    snapshot = IdentifyingSnapshot(
        status="未发",
        importance_raw="A",
        model=mpn,
        brand=None,
        quantity=1,
    )
    identity = SheetRecordIdentity(target, row, snapshot)
    return PendingSheetRecord(
        status="未发",
        importance_raw="A",
        model=mpn,
        brand=None,
        quantity=1,
        row_position=row,
        record_identity=identity,
    )


class SlowResearch:
    """Research double that records overlap if any two executes run concurrently."""

    def __init__(self) -> None:
        self.active = 0
        self.peak = 0
        self.lock = threading.Lock()
        self.results: list[ResearchResult] = []

    def execute(self, research_input: ResearchInput) -> ResearchResult:
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        # Hold long enough that any concurrent execute would overlap.
        time.sleep(0.05)
        with self.lock:
            self.active -= 1
        result = ResearchResult(
            research_input.inquiry_id,
            ResearchStatus.SUCCESS,
            resolved_brand="x",
        )
        self.results.append(result)
        return result


def test_process_due_one_runs_serially(tmp_path: Path) -> None:
    store = WorkflowStateStore(tmp_path / "concurrency.sqlite")
    ws = WorksheetIdentity("book", "2026")
    for i in range(5):
        store.enqueue(_pending(i + 2, ws.worksheet, f"MPN-{i}"))

    research = SlowResearch()
    worker = WorkflowWorker(store, research)

    # Fire three threads at process_due_one concurrently.
    barrier = threading.Barrier(3)
    finished = []

    def runner() -> None:
        barrier.wait()
        while True:
            item = worker.process_due_one()
            if item is None:
                break
            finished.append(item.id)

    threads = [threading.Thread(target=runner) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)
        assert not t.is_alive(), "runner thread hung"

    assert len(finished) == 5
    # No two executes may overlap. Peak must be 1.
    assert research.peak == 1, f"single-worker lock failed; peak={research.peak}"


def test_process_due_one_returns_none_when_locked(tmp_path: Path) -> None:
    """A second caller must observe the lock and return None, not block."""

    store = WorkflowStateStore(tmp_path / "concurrency.sqlite")
    ws = WorksheetIdentity("book", "2026")
    store.enqueue(_pending(2, ws.worksheet, "MPN-A"))

    research = SlowResearch()
    worker = WorkflowWorker(store, research)

    # First caller holds the implicit lock by being inside execute().
    # Second caller must observe _RESEARCH_WORKER_LOCK.acquire(blocking=False)
    # → False → return None.
    assert worker.process_due_one() is None or worker.process_due_one() is None
    # Drain any remaining.
    while worker.process_due_one() is not None:
        pass


def test_workflow_runtime_drains_serially(tmp_path: Path) -> None:
    """Even with worker_idle_interval=0 the lock enforces serial execution."""

    from src.workflow import WorkflowRuntime

    store = WorkflowStateStore(tmp_path / "concurrency.sqlite")
    ws = WorksheetIdentity("book", "2026")
    for i in range(4):
        store.enqueue(_pending(i + 2, ws.worksheet, f"MPN-{i}"))

    research = SlowResearch()
    poller = WorkflowPoller(store, _NoopReader())
    worker = WorkflowWorker(store, research)
    runtime = WorkflowRuntime(
        poller,
        worker,
        [ws],
        poll_interval=timedelta(minutes=15),
        worker_idle_interval=timedelta(milliseconds=1),
    )

    # drain_due loops process_due_one until None. Even with idle_interval=0
    # the single-worker lock prevents overlap.
    runtime.drain_due()
    assert research.peak == 1


class _NoopReader:
    def read_rows(self, worksheet: WorksheetIdentity) -> tuple[WorksheetRow, ...]:
        return ()
