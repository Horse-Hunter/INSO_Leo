"""Polling, single-worker execution, recovery, and scheduler wiring."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime, timedelta, timezone
from typing import Protocol

from src.research import ResearchInput, ResearchResult
from src.sheets import (
    PendingSheetRecord,
    SheetRecordIdentity,
    WorksheetIdentity,
    WorksheetRowReader,
    query_pending_records,
)
from src.sheets.brand_write import (
    SheetRecordConflict,
    TargetedBrandWriter,
    write_brand_safely,
)

from .models import WorkflowStatus, WorkItem
from .store import DEFAULT_RETRY_DELAYS, WorkflowStateStore

UTC = timezone.utc
_SHEET_POLL_LOCK = threading.Lock()
_RESEARCH_WORKER_LOCK = threading.Lock()


class ResearchExecutor(Protocol):
    def execute(self, research_input: ResearchInput) -> ResearchResult: ...


class CompletionChecker(Protocol):
    """Temporary seam until Research defines completion confirmation."""

    def completed_result(self, inquiry_id: str) -> ResearchResult | None: ...


class BrandUpdater(Protocol):
    def update_brand(self, identity: SheetRecordIdentity, brand: str) -> None: ...


class SheetsSafeBrandUpdater:
    """Delegate relocation, blank checking, and targeted writing to Sheets."""

    def __init__(
        self,
        reader: WorksheetRowReader,
        writer: TargetedBrandWriter,
    ) -> None:
        self._reader = reader
        self._writer = writer

    def update_brand(self, identity: SheetRecordIdentity, brand: str) -> None:
        write_brand_safely(self._reader, self._writer, identity, brand)


class WorkflowPoller:
    """Scan every configured worksheet and persist every pending record."""

    def __init__(self, store: WorkflowStateStore, reader: WorksheetRowReader) -> None:
        self._store = store
        self._reader = reader

    def poll(
        self,
        worksheets: Iterable[WorksheetIdentity],
        *,
        now: datetime | None = None,
    ) -> int:
        if not _SHEET_POLL_LOCK.acquire(blocking=False):
            return 0
        try:
            added = 0
            for worksheet in worksheets:
                records: tuple[PendingSheetRecord, ...] = query_pending_records(
                    self._reader, worksheet
                )
                for record in records:
                    added += self._store.enqueue(record, now=now)
            return added
        finally:
            _SHEET_POLL_LOCK.release()


class WorkflowWorker:
    """Process at most one due work item per call and never overlap itself."""

    def __init__(
        self,
        store: WorkflowStateStore,
        research: ResearchExecutor,
        *,
        brand_updater: BrandUpdater | None = None,
        retry_delays: Sequence[timedelta] = DEFAULT_RETRY_DELAYS,
    ) -> None:
        self._store = store
        self._research = research
        self._brand_updater = brand_updater
        self._retry_delays = tuple(retry_delays)

    def process_due_one(self, *, now: datetime | None = None) -> WorkItem | None:
        if not _RESEARCH_WORKER_LOCK.acquire(blocking=False):
            return None
        try:
            item = self._store.claim_due(now=now)
            if item is None:
                return None
            try:
                result = self._research.execute(_research_input(item))
            except Exception as exc:  # noqa: BLE001 - collaborator failures are retryable
                self._store.schedule_retry(
                    item.id,
                    error=exc,
                    now=now,
                    retry_delays=self._retry_delays,
                )
                return self._store.get(item.id)
            self._finish(item, result, now=now)
            return self._store.get(item.id)
        finally:
            _RESEARCH_WORKER_LOCK.release()

    def recover_interrupted(
        self,
        checker: CompletionChecker,
        *,
        now: datetime | None = None,
    ) -> tuple[WorkItem, ...]:
        recovered: list[WorkItem] = []
        for item in self._store.researching_items():
            try:
                result = checker.completed_result(item.inquiry_id)
            except Exception as exc:  # noqa: BLE001 - recovery must fail closed
                self._store.schedule_retry(
                    item.id,
                    error=exc,
                    now=now,
                    retry_delays=self._retry_delays,
                )
            else:
                if result is None:
                    self._store.schedule_retry(
                        item.id,
                        error="Interrupted Research was not confirmed complete",
                        now=now,
                        retry_delays=self._retry_delays,
                    )
                else:
                    self._finish(item, result, now=now)
            recovered.append(self._store.get(item.id))
        return tuple(recovered)

    def _finish(
        self,
        item: WorkItem,
        result: ResearchResult,
        *,
        now: datetime | None,
    ) -> None:
        final_status = self._store.apply_research_result(
            item.id,
            result,
            now=now,
            retry_delays=self._retry_delays,
        )
        if final_status not in {
            WorkflowStatus.COMPLETED,
            WorkflowStatus.MANUAL_REVIEW,
        } or not result.resolved_brand:
            return
        if self._brand_updater is None:
            self._store.record_brand_update(item.id, "NOT_CONFIGURED", now=now)
            return
        try:
            self._brand_updater.update_brand(item.record_identity, result.resolved_brand)
        except SheetRecordConflict as exc:
            self._store.record_brand_update(item.id, "CONFLICT", error=exc, now=now)
        except Exception as exc:  # noqa: BLE001 - preserve completed Research state
            self._store.record_brand_update(item.id, "FAILED", error=exc, now=now)
        else:
            self._store.record_brand_update(item.id, "UPDATED", now=now)


class WorkflowRuntime:
    """Run the 15-minute poller and single Research worker independently."""

    def __init__(
        self,
        poller: WorkflowPoller,
        worker: WorkflowWorker,
        worksheets: Iterable[WorksheetIdentity],
        *,
        poll_interval: timedelta = timedelta(minutes=15),
        worker_idle_interval: timedelta = timedelta(seconds=1),
    ) -> None:
        if poll_interval.total_seconds() <= 0:
            raise ValueError("poll_interval must be positive")
        if worker_idle_interval.total_seconds() <= 0:
            raise ValueError("worker_idle_interval must be positive")
        self.poller = poller
        self.worker = worker
        self.worksheets = tuple(worksheets)
        self.poll_interval = poll_interval
        self.worker_idle_interval = worker_idle_interval

    def run_poll(self, *, now: datetime | None = None) -> int:
        return self.poller.poll(self.worksheets, now=now)

    def drain_due(self, *, now: datetime | None = None) -> int:
        processed = 0
        while self.worker.process_due_one(now=now) is not None:
            processed += 1
        return processed

    def run_forever(
        self,
        stop_event: threading.Event,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        poll_thread = threading.Thread(
            target=self.run_poller_forever,
            args=(stop_event,),
            kwargs={"clock": clock},
            name="workflow-poller",
        )
        worker_thread = threading.Thread(
            target=self.run_worker_forever,
            args=(stop_event,),
            kwargs={"clock": clock},
            name="workflow-research-worker",
        )
        poll_thread.start()
        worker_thread.start()
        poll_thread.join()
        worker_thread.join()

    def run_poller_forever(
        self,
        stop_event: threading.Event,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        while not stop_event.is_set():
            self.run_poll(now=clock())
            stop_event.wait(self.poll_interval.total_seconds())

    def run_worker_forever(
        self,
        stop_event: threading.Event,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        while not stop_event.is_set():
            if self.worker.process_due_one(now=clock()) is None:
                stop_event.wait(self.worker_idle_interval.total_seconds())


def _research_input(item: WorkItem) -> ResearchInput:
    return ResearchInput(
        inquiry_id=item.inquiry_id,
        mpn=item.mpn,
        brand=item.brand,
        quantity=item.quantity,
        importance_raw=item.importance_raw,
    )
