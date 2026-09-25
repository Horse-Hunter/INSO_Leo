from __future__ import annotations

import threading
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
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
from src.sheets.brand_write import SheetRecordConflict
from src.workflow import (
    ResearchPreparationError,
    SheetsSafeBrandUpdater,
    WorkflowPoller,
    WorkflowRuntime,
    WorkflowStateStore,
    WorkflowStatus,
    WorkflowWorker,
)

NOW = datetime(2026, 9, 24, 1, 0, tzinfo=timezone.utc)


def pending(
    row_number: int = 2,
    *,
    spreadsheet: str = "book",
    worksheet: str = "requests",
    mpn: str = "MPN-1",
    brand: str | None = None,
    quantity: int = 10,
    importance_raw: str | None = " A ",
) -> PendingSheetRecord:
    target = WorksheetIdentity(spreadsheet, worksheet)
    snapshot = IdentifyingSnapshot(
        status="未发",
        importance_raw=importance_raw,
        model=mpn,
        brand=brand,
        quantity=quantity,
    )
    identity = SheetRecordIdentity(target, row_number, snapshot)
    return PendingSheetRecord(
        status="未发",
        importance_raw=importance_raw,
        model=mpn,
        brand=brand,
        quantity=quantity,
        row_position=row_number,
        record_identity=identity,
    )


def enqueue_one(store: WorkflowStateStore, **overrides: object) -> int:
    assert store.enqueue(pending(**overrides), now=NOW)
    return store.all_items()[0].id


class MappingReader:
    def __init__(self, rows: dict[WorksheetIdentity, Iterable[WorksheetRow]]) -> None:
        self.rows = {key: tuple(value) for key, value in rows.items()}
        self.calls: list[WorksheetIdentity] = []

    def read_rows(self, worksheet: WorksheetIdentity) -> tuple[WorksheetRow, ...]:
        self.calls.append(worksheet)
        return self.rows[worksheet]


class ResultResearch:
    def __init__(self, status: ResearchStatus, *, resolved_brand: str | None = None):
        self.status = status
        self.resolved_brand = resolved_brand
        self.inputs: list[ResearchInput] = []

    def execute(self, research_input: ResearchInput) -> ResearchResult:
        self.inputs.append(research_input)
        return ResearchResult(
            research_input.inquiry_id,
            self.status,
            resolved_brand=self.resolved_brand,
            remarks="retry me" if self.status is ResearchStatus.RETRYABLE_FAILURE else None,
        )


class RecordingBrandUpdater:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.calls: list[tuple[SheetRecordIdentity, str]] = []

    def update_brand(self, identity: SheetRecordIdentity, brand: str) -> None:
        self.calls.append((identity, brand))
        if self.failure is not None:
            raise self.failure


class CompletionResult:
    def __init__(self, result: ResearchResult | None) -> None:
        self.result = result
        self.calls: list[str] = []

    def completed_result(self, inquiry_id: str) -> ResearchResult | None:
        self.calls.append(inquiry_id)
        return self.result


def test_poll_scans_all_worksheets_enqueues_all_and_deduplicates_after_restart(
    tmp_path: Path,
) -> None:
    first = WorksheetIdentity("book", "requests")
    second = WorksheetIdentity("book", "shahab")
    reader = MappingReader(
        {
            first: [
                WorksheetRow(2, {"A": "未发", "C": " B ", "E": "ONE", "F": None, "G": 4}),
                WorksheetRow(3, {"A": "sent", "C": "A", "E": "SKIP", "F": None, "G": 1}),
                WorksheetRow(4, {"A": "未发", "C": "C", "E": "TWO", "F": "Maker", "G": 8}),
            ],
            second: [
                WorksheetRow(9, {"B": "未发", "D": "THREE", "E": None, "F": 12})
            ],
        }
    )
    database = tmp_path / "workflow.sqlite3"
    store = WorkflowStateStore(database)

    assert WorkflowPoller(store, reader).poll((first, second), now=NOW) == 3
    assert reader.calls == [first, second]
    original = store.all_items()
    assert [item.mpn for item in original] == ["ONE", "TWO", "THREE"]
    assert [item.importance_raw for item in original] == [" B ", "C", "A"]

    restarted = WorkflowStateStore(database)
    assert WorkflowPoller(restarted, reader).poll((first, second), now=NOW) == 0
    assert [item.inquiry_id for item in restarted.all_items()] == [
        item.inquiry_id for item in original
    ]
    assert all("-" not in item.inquiry_id for item in original)


def test_worker_processes_one_item_at_a_time_and_passes_canonical_input(
    tmp_path: Path,
) -> None:
    store = WorkflowStateStore(tmp_path / "workflow.db")
    enqueue_one(store, row_number=2, importance_raw=" A ")
    assert store.enqueue(pending(3, mpn="MPN-2", importance_raw="D"), now=NOW)

    class ReentrantResearch(ResultResearch):
        other_worker: WorkflowWorker

        def execute(self, research_input: ResearchInput) -> ResearchResult:
            assert self.other_worker.process_due_one(now=NOW) is None
            return super().execute(research_input)

    research = ReentrantResearch(ResearchStatus.SUCCESS)
    worker = WorkflowWorker(store, research)
    research.other_worker = WorkflowWorker(
        store, ResultResearch(ResearchStatus.SUCCESS)
    )

    first = worker.process_due_one(now=NOW)
    assert first is not None and first.status is WorkflowStatus.COMPLETED
    assert [item.status for item in store.all_items()] == [
        WorkflowStatus.COMPLETED,
        WorkflowStatus.QUEUED,
    ]
    second = worker.process_due_one(now=NOW)
    assert second is not None and second.status is WorkflowStatus.COMPLETED
    assert [(value.mpn, value.quantity, value.importance_raw) for value in research.inputs] == [
        ("MPN-1", 10, " A "),
        ("MPN-2", 10, "D"),
    ]
    assert research.inputs[0].inquiry_id == first.inquiry_id


@pytest.mark.parametrize(
    ("research_status", "workflow_status"),
    [
        (ResearchStatus.SUCCESS, WorkflowStatus.COMPLETED),
        (ResearchStatus.PARTIAL_SUCCESS, WorkflowStatus.COMPLETED),
        (ResearchStatus.EXCEPTION, WorkflowStatus.FAILED),
    ],
)
def test_terminal_research_results_map_to_workflow_states(
    tmp_path: Path,
    research_status: ResearchStatus,
    workflow_status: WorkflowStatus,
) -> None:
    store = WorkflowStateStore(tmp_path / f"{research_status.value}.db")
    enqueue_one(store)

    result = WorkflowWorker(store, ResultResearch(research_status)).process_due_one(now=NOW)

    assert result is not None and result.status is workflow_status
    assert result.research_status == research_status.value


def test_retry_schedule_is_15_30_60_then_failed(tmp_path: Path) -> None:
    store = WorkflowStateStore(tmp_path / "workflow.db")
    enqueue_one(store)
    worker = WorkflowWorker(store, ResultResearch(ResearchStatus.RETRYABLE_FAILURE))

    first = worker.process_due_one(now=NOW)
    assert first is not None
    assert first.status is WorkflowStatus.RETRY_WAIT
    assert first.next_attempt_at == NOW + timedelta(minutes=15)
    assert worker.process_due_one(now=NOW + timedelta(minutes=14)) is None

    second_time = NOW + timedelta(minutes=15)
    second = worker.process_due_one(now=second_time)
    assert second is not None
    assert second.next_attempt_at == second_time + timedelta(minutes=30)

    third_time = second_time + timedelta(minutes=30)
    third = worker.process_due_one(now=third_time)
    assert third is not None
    assert third.next_attempt_at == third_time + timedelta(minutes=60)

    fourth_time = third_time + timedelta(minutes=60)
    fourth = worker.process_due_one(now=fourth_time)
    assert fourth is not None
    assert fourth.status is WorkflowStatus.FAILED
    assert fourth.next_attempt_at is None
    assert fourth.attempt_count == 4


def test_preparation_failure_restores_claim_without_spending_retry_budget(
    tmp_path: Path,
) -> None:
    store = WorkflowStateStore(tmp_path / "workflow.db")
    enqueue_one(store)

    class PreparationFailure:
        def execute(self, _research_input: ResearchInput) -> ResearchResult:
            raise ResearchPreparationError("CDP browser requires manual handling")

    worker = WorkflowWorker(store, PreparationFailure())
    with pytest.raises(ResearchPreparationError):
        worker.process_due_one(now=NOW)

    item = store.all_items()[0]
    assert item.status is WorkflowStatus.QUEUED
    assert item.attempt_count == 0
    assert item.next_attempt_at == NOW
    assert item.research_status is None


def test_no_quote_exception_fails_without_retry(tmp_path: Path) -> None:
    store = WorkflowStateStore(tmp_path / "workflow.db")
    enqueue_one(store)
    worker = WorkflowWorker(store, ResultResearch(ResearchStatus.EXCEPTION))

    result = worker.process_due_one(now=NOW)

    assert result is not None
    assert result.status is WorkflowStatus.FAILED
    assert result.research_status == ResearchStatus.EXCEPTION.value
    assert result.next_attempt_at is None
    assert result.last_error == ResearchStatus.EXCEPTION.value


def test_no_quote_exception_still_uses_safe_brand_update(tmp_path: Path) -> None:
    store = WorkflowStateStore(tmp_path / "workflow.db")
    enqueue_one(store)
    updater = RecordingBrandUpdater()
    worker = WorkflowWorker(
        store,
        ResultResearch(ResearchStatus.EXCEPTION, resolved_brand="Resolved Maker"),
        brand_updater=updater,
    )

    result = worker.process_due_one(now=NOW)

    assert result is not None
    assert result.status is WorkflowStatus.FAILED
    assert result.next_attempt_at is None
    assert result.brand_update_status == "UPDATED"
    assert updater.calls == [(result.record_identity, "Resolved Maker")]


def test_no_quote_exception_brand_conflict_preserves_failed_terminal_state(
    tmp_path: Path,
) -> None:
    store = WorkflowStateStore(tmp_path / "workflow.db")
    enqueue_one(store)
    updater = RecordingBrandUpdater(SheetRecordConflict("human value exists"))
    worker = WorkflowWorker(
        store,
        ResultResearch(ResearchStatus.EXCEPTION, resolved_brand="Resolved Maker"),
        brand_updater=updater,
    )

    result = worker.process_due_one(now=NOW)

    assert result is not None
    assert result.status is WorkflowStatus.FAILED
    assert result.next_attempt_at is None
    assert result.brand_update_status == "CONFLICT"
    assert updater.calls == [(result.record_identity, "Resolved Maker")]


def test_no_quote_exception_brand_failure_preserves_failed_terminal_state(
    tmp_path: Path,
) -> None:
    store = WorkflowStateStore(tmp_path / "workflow.db")
    enqueue_one(store)
    updater = RecordingBrandUpdater(RuntimeError("synthetic write failure"))
    worker = WorkflowWorker(
        store,
        ResultResearch(ResearchStatus.EXCEPTION, resolved_brand="Resolved Maker"),
        brand_updater=updater,
    )

    result = worker.process_due_one(now=NOW)

    assert result is not None
    assert result.status is WorkflowStatus.FAILED
    assert result.next_attempt_at is None
    assert result.brand_update_status == "FAILED"
    assert updater.calls == [(result.record_identity, "Resolved Maker")]


def test_retryable_failure_exhaustion_never_updates_brand(tmp_path: Path) -> None:
    store = WorkflowStateStore(tmp_path / "workflow.db")
    enqueue_one(store)
    updater = RecordingBrandUpdater()
    worker = WorkflowWorker(
        store,
        ResultResearch(
            ResearchStatus.RETRYABLE_FAILURE, resolved_brand="Resolved Maker"
        ),
        brand_updater=updater,
    )
    attempt_times = (
        NOW,
        NOW + timedelta(minutes=15),
        NOW + timedelta(minutes=45),
        NOW + timedelta(minutes=105),
    )

    results = [worker.process_due_one(now=attempt_time) for attempt_time in attempt_times]

    assert all(result is not None for result in results)
    assert results[-1] is not None
    assert results[-1].status is WorkflowStatus.FAILED
    assert results[-1].attempt_count == 4
    assert updater.calls == []


def test_restart_recovery_confirms_completion_before_transition(tmp_path: Path) -> None:
    database = tmp_path / "workflow.db"
    store = WorkflowStateStore(database)
    enqueue_one(store)
    interrupted = store.claim_due(now=NOW)
    assert interrupted is not None

    restarted = WorkflowStateStore(database)
    brand = RecordingBrandUpdater()
    checker = CompletionResult(
        ResearchResult(
            interrupted.inquiry_id,
            ResearchStatus.SUCCESS,
            resolved_brand="Resolved Maker",
        )
    )
    worker = WorkflowWorker(
        restarted,
        ResultResearch(ResearchStatus.SUCCESS),
        brand_updater=brand,
    )

    recovered = worker.recover_interrupted(checker, now=NOW + timedelta(minutes=1))

    assert checker.calls == [interrupted.inquiry_id]
    assert recovered[0].status is WorkflowStatus.COMPLETED
    assert recovered[0].brand_update_status == "UPDATED"
    assert brand.calls == [(interrupted.record_identity, "Resolved Maker")]


def test_restart_recovery_unconfirmed_uses_retry_budget(tmp_path: Path) -> None:
    store = WorkflowStateStore(tmp_path / "workflow.db")
    enqueue_one(store)
    interrupted = store.claim_due(now=NOW)
    assert interrupted is not None
    checker = CompletionResult(None)

    recovered = WorkflowWorker(
        store, ResultResearch(ResearchStatus.SUCCESS)
    ).recover_interrupted(checker, now=NOW + timedelta(minutes=2))

    assert checker.calls == [interrupted.inquiry_id]
    assert recovered[0].status is WorkflowStatus.RETRY_WAIT
    assert recovered[0].next_attempt_at == NOW + timedelta(minutes=17)


def test_unconfirmed_fourth_interrupted_attempt_is_failed(tmp_path: Path) -> None:
    store = WorkflowStateStore(tmp_path / "workflow.db")
    item_id = enqueue_one(store)
    for offset in range(3):
        claimed = store.claim_due(now=NOW + timedelta(hours=offset))
        assert claimed is not None
        store.schedule_retry(item_id, error="retry", now=NOW + timedelta(hours=offset))
    fourth = store.claim_due(now=NOW + timedelta(hours=3))
    assert fourth is not None and fourth.attempt_count == 4

    recovered = WorkflowWorker(
        store, ResultResearch(ResearchStatus.SUCCESS)
    ).recover_interrupted(CompletionResult(None), now=NOW + timedelta(hours=3))

    assert recovered[0].status is WorkflowStatus.FAILED


def test_brand_conflict_never_undoes_completed_research(tmp_path: Path) -> None:
    store = WorkflowStateStore(tmp_path / "workflow.db")
    enqueue_one(store)
    updater = RecordingBrandUpdater(SheetRecordConflict("human value exists"))
    worker = WorkflowWorker(
        store,
        ResultResearch(ResearchStatus.PARTIAL_SUCCESS, resolved_brand="Resolved"),
        brand_updater=updater,
    )

    result = worker.process_due_one(now=NOW)

    assert result is not None
    assert result.status is WorkflowStatus.COMPLETED
    assert result.brand_update_status == "CONFLICT"
    assert updater.calls[0][0] == result.record_identity


def test_safe_brand_adapter_passes_opaque_identity_to_sheets_relocation() -> None:
    record = pending(row_number=4)
    moved = WorksheetRow(
        9,
        {"A": "未发", "C": " A ", "E": "MPN-1", "F": None, "G": 10},
    )

    class SequencedReader:
        def __init__(self) -> None:
            self.reads = 0

        def read_rows(self, worksheet: WorksheetIdentity) -> tuple[WorksheetRow, ...]:
            assert worksheet == record.record_identity.worksheet
            self.reads += 1
            return (moved,)

    class TargetedWriter:
        def __init__(self) -> None:
            self.calls: list[tuple[WorksheetIdentity, int, str]] = []

        def write_brand(
            self, worksheet: WorksheetIdentity, row_position: int, brand: str
        ) -> None:
            self.calls.append((worksheet, row_position, brand))

    reader = SequencedReader()
    writer = TargetedWriter()

    SheetsSafeBrandUpdater(reader, writer).update_brand(
        record.record_identity, "Resolved"
    )

    assert reader.reads == 2
    assert writer.calls == [(record.record_identity.worksheet, 9, "Resolved")]


def test_runtime_defaults_to_fifteen_minute_polling(tmp_path: Path) -> None:
    store = WorkflowStateStore(tmp_path / "workflow.db")
    reader = MappingReader({})
    runtime = WorkflowRuntime(
        WorkflowPoller(store, reader),
        WorkflowWorker(store, ResultResearch(ResearchStatus.SUCCESS)),
        (),
    )

    assert runtime.poll_interval == timedelta(minutes=15)


def test_runtime_runs_poller_and_worker_independently() -> None:
    poll_entered = threading.Event()
    worker_entered = threading.Event()
    stop = threading.Event()

    class BlockingPoller:
        def poll(
            self,
            worksheets: Iterable[WorksheetIdentity],
            *,
            now: datetime | None = None,
        ) -> int:
            poll_entered.set()
            assert worker_entered.wait(1)
            stop.set()
            return 0

    class SignalingWorker:
        def process_due_one(self, *, now: datetime | None = None) -> None:
            assert poll_entered.wait(1)
            worker_entered.set()

    runtime = WorkflowRuntime(
        BlockingPoller(),
        SignalingWorker(),
        (),
        worker_idle_interval=timedelta(milliseconds=1),
    )

    runtime.run_forever(stop, clock=lambda: NOW)

    assert poll_entered.is_set()
    assert worker_entered.is_set()


def test_workflow_state_catalog_is_exact() -> None:
    assert {status.value for status in WorkflowStatus} == {
        "QUEUED",
        "RESEARCHING",
        "RETRY_WAIT",
        "COMPLETED",
        "MANUAL_REVIEW",
        "FAILED",
    }
