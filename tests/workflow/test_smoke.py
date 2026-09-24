"""Side-effect-free Workflow V1 mainline smoke test."""

from datetime import datetime, timezone
from pathlib import Path

from src.research import ResearchInput, ResearchResult, ResearchStatus
from src.sheets import WorksheetIdentity, WorksheetRow
from src.workflow import (
    SheetsSafeBrandUpdater,
    WorkflowPoller,
    WorkflowRuntime,
    WorkflowStateStore,
    WorkflowStatus,
    WorkflowWorker,
)


def test_fake_sheets_to_research_to_safe_brand_mainline(tmp_path: Path) -> None:
    worksheet = WorksheetIdentity("fake-book", "requests")
    rows = (
        WorksheetRow(
            2,
            {"A": "未发", "C": "A", "E": "MPN-1", "F": None, "G": 5},
        ),
        WorksheetRow(
            3,
            {"A": "未发", "C": "B", "E": "MPN-2", "F": None, "G": 7},
        ),
    )

    class FakeSheets:
        def __init__(self) -> None:
            self.writes: list[tuple[WorksheetIdentity, int, str]] = []

        def read_rows(self, target: WorksheetIdentity) -> tuple[WorksheetRow, ...]:
            assert target == worksheet
            return rows

        def write_brand(
            self, target: WorksheetIdentity, row_position: int, brand: str
        ) -> None:
            self.writes.append((target, row_position, brand))

    class FakeResearch:
        def __init__(self) -> None:
            self.inputs: list[ResearchInput] = []

        def execute(self, value: ResearchInput) -> ResearchResult:
            self.inputs.append(value)
            return ResearchResult(
                value.inquiry_id,
                ResearchStatus.SUCCESS,
                resolved_brand=f"Brand-{value.mpn}",
            )

    sheets = FakeSheets()
    research = FakeResearch()
    store = WorkflowStateStore(tmp_path / "workflow-smoke.sqlite3")
    runtime = WorkflowRuntime(
        WorkflowPoller(store, sheets),
        WorkflowWorker(
            store,
            research,
            brand_updater=SheetsSafeBrandUpdater(sheets, sheets),
        ),
        (worksheet,),
    )
    now = datetime(2026, 9, 24, tzinfo=timezone.utc)

    assert runtime.run_poll(now=now) == 2
    assert runtime.drain_due(now=now) == 2

    assert [item.status for item in store.all_items()] == [
        WorkflowStatus.COMPLETED,
        WorkflowStatus.COMPLETED,
    ]
    assert [value.importance_raw for value in research.inputs] == ["A", "B"]
    assert sheets.writes == [
        (worksheet, 2, "Brand-MPN-1"),
        (worksheet, 3, "Brand-MPN-2"),
    ]
