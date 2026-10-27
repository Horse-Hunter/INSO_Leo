"""Polling, single-worker execution, recovery, and scheduler wiring."""

from __future__ import annotations

import sqlite3
import threading
from collections import deque
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from time import monotonic
from typing import Protocol

from src.research import (
    InvalidResearchInput,
    ResearchInput,
    ResearchResult,
    ResearchStatus,
)
from src.sheets import (
    PendingSheetRecord,
    SheetRecordIdentity,
    WorksheetIdentity,
    WorksheetRowReader,
    query_pending_records,
    usable_brand,
)
from src.sheets.brand_write import (
    SheetRecordConflict,
    TargetedBrandWriter,
    write_brand_safely,
)

from .market_messages import MarketModule
from .models import WorkflowStatus, WorkItem
from .store import DEFAULT_RETRY_DELAYS, WorkflowStateStore
from .v12_store import V12DatabaseError

UTC = timezone.utc
_SHEET_POLL_LOCK = threading.Lock()
_RESEARCH_WORKER_LOCK = threading.Lock()


class ResearchExecutor(Protocol):
    def execute(self, research_input: ResearchInput) -> ResearchResult: ...


class ResearchPreparationError(RuntimeError):
    """Infrastructure failed before Research began; it is not a retryable result."""


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
        *,
        verify_readback: bool = False,
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._verify_readback = verify_readback

    def update_brand(self, identity: SheetRecordIdentity, brand: str) -> None:
        write_brand_safely(
            self._reader, self._writer, identity, brand, verify_readback=self._verify_readback
        )


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

    def process_due_one(self, *, now: datetime | None = None, inquiry_ids=None) -> WorkItem | None:
        if not _RESEARCH_WORKER_LOCK.acquire(blocking=False):
            return None
        try:
            item = (self._store.claim_due(now=now) if inquiry_ids is None
                    else self._store.claim_due(now=now, inquiry_ids=inquiry_ids))
            if item is None:
                return None
            try:
                result = self._research.execute(_research_input(item))
            except ResearchPreparationError:
                # Claiming increments an attempt before the executor runs. A
                # launcher preparation failure happened before Research, so
                # restore the queue state and let the composition root enter
                # manual handling without spending the business retry budget.
                self._store.release_unprepared(item.id, now=now)
                raise
            except InvalidResearchInput:
                # A worksheet row whose quantity is not a number violates the
                # Research contract deterministically. Retrying would fail the
                # same way and only burn the business retry budget, so stop
                # here; the row resumes once the worksheet data is corrected.
                self._store.abort_invalid_input(
                    item.id,
                    reason="INVALID_RESEARCH_INPUT",
                    now=now,
                )
                return self._store.get(item.id)
            except (sqlite3.Error, V12DatabaseError):
                raise
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
        allowed_final_status = {
            ResearchStatus.SUCCESS: WorkflowStatus.COMPLETED,
            ResearchStatus.PARTIAL_SUCCESS: WorkflowStatus.COMPLETED,
            ResearchStatus.EXCEPTION: WorkflowStatus.FAILED,
        }.get(result.status)
        if (
            allowed_final_status is None
            or final_status is not allowed_final_status
            or not result.resolved_brand
            or usable_brand(item.brand) is not None
        ):
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


class OrderResourceOwnershipError(RuntimeError):
    """A resource claim/release did not come from its exact scheduler owner."""

    reason = "ORDER_RESOURCE_OWNERSHIP_LOST"

    def __init__(self):
        super().__init__(self.reason)


@dataclass(frozen=True, slots=True)
class OrderResourceLease:
    """Ephemeral source-row exclusion, never durable business permission."""

    worksheet: WorksheetIdentity
    row_position: int
    request_token: str
    _owner_thread: int = field(repr=False)


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
        self._module_lock = threading.RLock()
        self._module_timer = monotonic
        self._module_due = {}
        self._module_periods = {}
        self._module_running = set()
        self._module_paused = set()
        self._module_resource = None
        self._module_owner = None
        self._module_resource_failed = False
        self._order_capacity = 0
        self._order_closed = True
        self._order_terminal = False
        self._order_requests = {}
        self._order_waiters = {}
        self._order_active = {}
        self._order_dispatched = set()

    def configure_order_leases(self, capacity):
        """Bound ephemeral admissions to the coordinator's finite worker budget.

        Default is closed/unconfigured. No pending DB work is consumed or dropped
        when the budget is full; the existing scheduler must retry admission.
        """
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise ValueError("INVALID_ORDER_RESOURCE_CAPACITY")
        with self._module_lock:
            if self._module_running or self._order_requests:
                raise RuntimeError("ORDER_RESOURCES_RUNNING")
            if self._module_resource_failed:
                raise RuntimeError("MODULE_RESOURCE_OWNERSHIP_LOST")
            if self._order_terminal:
                raise RuntimeError("ORDER_ADMISSIONS_CLOSED")
            self._order_capacity, self._order_closed = capacity, False

    def request_order_lease(self, worksheet, row_position, request_token, *, module_id):
        """Queue an original source key; matching snapshots/MPN are not lock keys.

        Callers first verify source identity through existing domain contracts.
        This lease cannot authorize Google writes, purchases or mail delivery.
        """
        if (not isinstance(module_id, MarketModule)
                or not isinstance(worksheet, WorksheetIdentity)
                or not isinstance(worksheet.spreadsheet, str) or not worksheet.spreadsheet.strip()
                or not isinstance(worksheet.worksheet, str) or not worksheet.worksheet.strip()
                or isinstance(row_position, bool) or not isinstance(row_position, int) or row_position < 1
                or not isinstance(request_token, str) or not request_token.strip() or len(request_token) > 160):
            raise ValueError("INVALID_ORDER_RESOURCE_IDENTITY")
        key = worksheet, row_position
        with self._module_lock:
            self._check_order_admission()
            if module_id.value not in self._module_periods:
                raise ValueError("ORDER_MODULE_NOT_CONFIGURED")
            old = self._order_requests.get(request_token)
            if old is not None:
                if old != (key, threading.get_ident(), module_id):
                    raise OrderResourceOwnershipError()
                if key in self._order_active and self._order_active[key].request_token == request_token:
                    raise RuntimeError("ORDER_ALREADY_CLAIMED")
                return True
            # Bound distinct source slots separately from same-row FIFO waiters.
            # At most one queued request per configured module per source slot.
            # Duplicate-key waiters cannot consume another row's execution slot.
            if key not in self._order_waiters and len(self._order_waiters) >= self._order_capacity:
                return False
            if any(self._order_requests[token][2] is module_id
                   for token in self._order_waiters.get(key, ())):
                return False
            self._order_requests[request_token] = key, threading.get_ident(), module_id
            self._order_waiters.setdefault(key, deque()).append(request_token)
            return True

    def _check_order_admission(self):
        if self._module_resource_failed:
            raise RuntimeError("MODULE_RESOURCE_OWNERSHIP_LOST")
        if self._order_closed:
            raise RuntimeError("ORDER_ADMISSIONS_CLOSED")

    def try_claim_order_lease(self, request_token):
        with self._module_lock:
            self._check_order_admission()
            pending = self._order_requests.get(request_token)
            if pending is None:
                return None
            key, owner, _ = pending
            if owner != threading.get_ident():
                raise OrderResourceOwnershipError()
            active = self._order_active.get(key)
            if active is not None:
                if active.request_token == request_token:
                    raise RuntimeError("ORDER_ALREADY_CLAIMED")
                return None
            if self._order_waiters[key][0] != request_token:
                return None
            if len(self._order_active) >= self._order_capacity:
                return None
            lease = OrderResourceLease(*key, request_token, owner)
            self._order_active[key] = lease
            return lease

    def _verify_order_lease(self, lease):
        if not isinstance(lease, OrderResourceLease):
            raise OrderResourceOwnershipError()
        key = lease.worksheet, lease.row_position
        if (self._order_active.get(key) is not lease
                or lease._owner_thread != threading.get_ident()
                or not self._order_waiters.get(key)
                or self._order_waiters[key][0] != lease.request_token):
            raise OrderResourceOwnershipError()
        return key

    def begin_order_dispatch(self, lease):
        """Atomic Stop/dispatch boundary, called by the admitting scheduler.

        True commits this request to the in-flight drain set. False means Stop
        won; caller must cancel its reservation, never submit it to a worker.
        A committed request must acknowledge terminal work before release.
        """
        with self._module_lock:
            self._verify_order_lease(lease)
            if lease.request_token in self._order_dispatched:
                raise RuntimeError("ORDER_ALREADY_DISPATCHED")
            if self._order_closed or self._module_resource_failed:
                return False
            self._order_dispatched.add(lease.request_token)
            return True

    def cancel_reserved_order_lease(self, lease):
        """Scheduler-only rollback of a claim that never crossed dispatch."""
        with self._module_lock:
            self._verify_order_lease(lease)
            if lease.request_token in self._order_dispatched:
                raise RuntimeError("ORDER_STILL_RUNNING")
            self.release_order_lease(lease)

    def release_order_lease(self, lease):
        """Only the admitting scheduler thread can release its exact live lease."""
        with self._module_lock:
            key = self._verify_order_lease(lease)
            self._order_dispatched.discard(lease.request_token)
            del self._order_active[key]
            del self._order_requests[lease.request_token]
            self._order_waiters[key].popleft()
            if not self._order_waiters[key]:
                del self._order_waiters[key]

    def cancel_order_lease_request(self, request_token):
        with self._module_lock:
            pending = self._order_requests.get(request_token)
            if pending is None:
                return False
            key, owner, _ = pending
            if owner != threading.get_ident():
                raise OrderResourceOwnershipError()
            if key in self._order_active and self._order_active[key].request_token == request_token:
                raise RuntimeError("ORDER_STILL_RUNNING")
            self._order_waiters[key].remove(request_token)
            del self._order_requests[request_token]
            if not self._order_waiters[key]:
                del self._order_waiters[key]
            return True

    def close_order_admissions(self):
        """Cancel only undispatched resource requests; active work must drain."""
        with self._module_lock:
            self._order_closed = True
            self._order_terminal = True
            active = {lease.request_token for lease in self._order_active.values()}
            for token in tuple(self._order_requests):
                if token not in active:
                    key, _, _ = self._order_requests.pop(token)
                    self._order_waiters[key].remove(token)
                    if not self._order_waiters[key]:
                        del self._order_waiters[key]

    def order_resource_counts(self):
        with self._module_lock:
            return {"capacity": self._order_capacity, "active": len(self._order_active),
                    "waiting": len(self._order_requests)-len(self._order_active),
                    "closed": self._order_closed or self._module_resource_failed}

    def configure_modules(self, intervals, *, timer=monotonic):
        """Extend the existing runtime, not business identities or persistent state.

        Shared browser/Sheets/Excel operations have one fixed thread owner.
        Recipient delivery remains on the existing independent mail worker.
        """
        if not intervals or set(intervals) - {"inquiry", "quotation", "tp"}:
            raise ValueError("INVALID_MODULE_INTERVALS")
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not 0 < v < float("inf") for v in intervals.values()):
            raise ValueError("INVALID_MODULE_INTERVALS")
        with self._module_lock:
            if self._module_resource_failed:
                raise RuntimeError("MODULE_RESOURCE_OWNERSHIP_LOST")
            if self._module_running or self._order_requests:
                raise RuntimeError("MODULES_RUNNING")
            self._module_timer = timer
            self._module_periods = dict(intervals)
            self._module_due = dict.fromkeys(intervals, timer())
            self._module_paused.clear()
            self._module_resource = self._module_owner = None

    def claim_due_module(self, *, exclude=()):
        with self._module_lock:
            if self._module_resource_failed:
                raise RuntimeError("MODULE_RESOURCE_OWNERSHIP_LOST")
            owner = threading.get_ident()
            if self._module_resource is not None or self._module_owner not in (None, owner):
                return None
            now = self._module_timer()
            due = [k for k, at in self._module_due.items() if at <= now
                   and k not in self._module_running | self._module_paused
                   and k not in exclude]
            if not due:
                return None
            key = min(due, key=lambda k: self._module_due[k])
            self._module_owner, self._module_resource = owner, key
            self._module_running.add(key)
            return key

    def complete_module(self, module, *, retry_after=None, pause=False):
        with self._module_lock:
            if self._module_resource != module or self._module_owner != threading.get_ident():
                raise RuntimeError("MODULE_RESOURCE_OWNERSHIP_LOST")
            self._module_running.remove(module)
            self._module_resource = None
            self._module_due[module] = self._module_timer() + (
                self._module_periods[module] if retry_after is None else retry_after)
            if pause:
                self._module_paused.add(module)

    def yield_module_resource(self, module):
        """Only at a closed order boundary, on the same browser-owner thread."""
        with self._module_lock:
            if self._module_resource != module or self._module_owner != threading.get_ident():
                raise RuntimeError("MODULE_RESOURCE_OWNERSHIP_LOST")
            self._module_resource = None

    def resume_module_resource(self, module):
        with self._module_lock:
            if (self._module_resource is not None or module not in self._module_running
                    or self._module_owner != threading.get_ident()):
                raise RuntimeError("MODULE_RESOURCE_OWNERSHIP_LOST")
            self._module_resource = module

    @property
    def module_resource_failed(self):
        with self._module_lock:
            return self._module_resource_failed

    def abort_module_resource(self):
        """A failed browser cleanup invalidates the whole actor, never reuses it."""
        with self._module_lock:
            if self._module_owner != threading.get_ident():
                raise RuntimeError("MODULE_RESOURCE_OWNERSHIP_LOST")
            self._module_resource_failed = True
            self.close_order_admissions()
            self._module_paused.update(self._module_periods)
            self._module_running.clear()
            self._module_resource = None

    def reset_module(self, module):
        with self._module_lock:
            if module in self._module_periods:
                self._module_due[module] = self._module_timer() + self._module_periods[module]

    def module_plans(self):
        with self._module_lock:
            return {k: (at, k in self._module_running, k in self._module_paused)
                    for k, at in self._module_due.items()}

    def module_delay(self):
        with self._module_lock:
            due = [at for k, at in self._module_due.items()
                   if k not in self._module_running | self._module_paused]
            return max(0, min(due) - self._module_timer()) if due else 1.0

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
    # The queue stores the Brand cell verbatim, so the persisted copy can still
    # hold a placeholder the Owner wrote.  Research is handed the same value it
    # would have read live: a placeholder is not a brand, and Research resolves
    # the missing one instead of accepting it.
    return ResearchInput(
        inquiry_id=item.inquiry_id,
        mpn=item.mpn,
        brand=usable_brand(item.brand),
        quantity=item.quantity,
        importance_raw=item.importance_raw,
    )
