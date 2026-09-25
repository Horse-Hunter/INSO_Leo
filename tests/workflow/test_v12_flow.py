from __future__ import annotations

import sqlite3
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from src.launcher.v12_gui import read_v12_order_state
from src.research import ResearchInput, ResearchResult, ResearchStatus
from src.sheets import WorksheetIdentity, WorksheetRow
from src.workflow import WorkflowStateStore
from src.workflow.v12_contracts import (
    BusinessState,
    DeliveryOutcome,
    DuplicateCheckResult,
    DuplicateOutcome,
    NotificationRecipient,
    NotificationTransportResult,
    ReasonCode,
)
from src.workflow.v12_flow import (
    FakePurchaseDraftWriter,
    ResearchBusinessFacts,
    V12WorkflowCoordinator,
)
from src.workflow.v12_notifications import (
    FakeNotificationTransport,
    V12NotificationWorker,
)
from src.workflow.v12_rules import PurchaseRoutingOutcome
from src.workflow.v12_store import V12Store, migrate_v12

NOW = datetime(2026, 9, 26, 1, tzinfo=UTC)
SHEET = WorksheetIdentity("synthetic-sheet", "2026")


class FakeSheetsReader:
    def __init__(self, *, tier: str = "A", quantity: int = 7) -> None:
        self.row = WorksheetRow(
            3,
            {
                "A": "未发",
                "C": tier,
                "D": "Synthetic Customer",
                "E": "Mpn-1",
                "F": "Brand-X",
                "G": quantity,
            },
        )

    def read_rows(self, worksheet: WorksheetIdentity):
        assert worksheet == SHEET
        return (self.row,)


class FakeResearch:
    def __init__(self) -> None:
        self.inputs: list[ResearchInput] = []

    def execute(self, item: ResearchInput) -> ResearchResult:
        self.inputs.append(item)
        return ResearchResult(item.inquiry_id, ResearchStatus.SUCCESS, resolved_brand="Brand-X")


class FakeDuplicateChecker:
    def __init__(self, result: DuplicateCheckResult | None = None, *, failure: bool = False):
        self.result = result
        self.failure = failure
        self.calls: list[tuple[str, str, int]] = []

    def check(self, inquiry_id, mpn, quantity, *, at):
        self.calls.append((inquiry_id, mpn, quantity))
        if self.failure:
            raise RuntimeError("fake lookup is unavailable")
        return self.result or DuplicateCheckResult(
            inquiry_id, DuplicateOutcome.CONFIRMED, "MPN-1", at, repeated=False
        )


class MutableFacts:
    def __init__(self, facts: ResearchBusinessFacts | None) -> None:
        self.facts = facts

    def get(self, _inquiry_id: str):
        return self.facts


def _make_flow(
    tmp_path: Path,
    *,
    tier: str = "A",
    duplicate: DuplicateCheckResult | None = None,
    duplicate_failure: bool = False,
    facts: ResearchBusinessFacts | None = None,
    notification_transport: FakeNotificationTransport | None = None,
):
    database = tmp_path / "workflow.sqlite3"
    workflow_store = WorkflowStateStore(database)
    migrate_v12(
        database,
        tmp_path / "backups",
        quiesce=lambda: nullcontext(),
        clock=lambda: NOW,
    )
    v12_store = V12Store(database)
    research = FakeResearch()
    checker = FakeDuplicateChecker(duplicate, failure=duplicate_failure)
    provider = MutableFacts(facts)
    transport = notification_transport or FakeNotificationTransport()
    notification_worker = V12NotificationWorker(v12_store, transport)
    writer = FakePurchaseDraftWriter(completed_at=NOW)
    coordinator = V12WorkflowCoordinator(
        workflow_store,
        v12_store,
        research,
        checker,
        provider,
        writer,
        notification_worker,
        (NotificationRecipient("synthetic-recipient", "fake@example.invalid"),),
    )
    return coordinator, workflow_store, v12_store, research, checker, provider, writer, notification_worker


def _confirmed_duplicate(inquiry_id: str, *, at: datetime, repeated: bool) -> DuplicateCheckResult:
    if not repeated:
        return DuplicateCheckResult(
            inquiry_id, DuplicateOutcome.CONFIRMED, "MPN-1", at, repeated=False
        )
    return DuplicateCheckResult(
        inquiry_id,
        DuplicateOutcome.CONFIRMED,
        "MPN-1",
        at,
        repeated=True,
        historical_date=at - timedelta(days=2),
        historical_mpn="mpn-1",
        historical_quantity=8,
        quantity_equal=False,
        creator="synthetic creator",
        inso_quote=Decimal("10.50"),
        currency="CNY",
    )


def test_pending_to_research_to_nonblocking_notification_and_purchase_draft(tmp_path: Path) -> None:
    transport = FakeNotificationTransport(
        {
            "synthetic-recipient": (
                NotificationTransportResult(
                    DeliveryOutcome.RETRYABLE_FAILURE,
                    ReasonCode.NOTIFICATION_TRANSIENT,
                ),
                NotificationTransportResult(
                    DeliveryOutcome.SENT,
                    ReasonCode.NOTIFICATION_SENT,
                ),
            )
        }
    )
    flow, _v1, store, research, _checker, _facts, writer, _notification_worker = _make_flow(
        tmp_path,
        facts=ResearchBusinessFacts("货足", Decimal(60001), Decimal("2.00")),
        notification_transport=transport,
    )

    result = flow.poll_and_process(FakeSheetsReader(), SHEET, now=NOW)

    assert len(research.inputs) == 1
    assert result[0].business_state is BusinessState.PURCHASE_DRAFTING
    assert result[0].purchase_outcome.value == "AI_RECOGNIZED"
    assert len(writer.commands) == 1
    assert writer.commands[0].purchaser == "颜浩坚"
    assert writer.commands[0].quotation_type == "需要问全价格"
    assert store.purchase_state(result[0].inquiry_id).value == "AI_RECOGNIZED"

    flow.run_notifications(now=NOW)
    assert store.purchase_state(result[0].inquiry_id).value == "AI_RECOGNIZED"
    assert store.active_alerts(result[0].inquiry_id)
    flow.run_notifications(now=NOW + timedelta(minutes=1))
    assert not store.active_alerts(result[0].inquiry_id)
    event_types = [event.event_type.value for event in store.event_history(result[0].inquiry_id)]
    assert "NOTIFICATION_RETRY_SCHEDULED" in event_types
    assert "ALERT_RECOVERED" in event_types


def test_duplicate_runs_research_stops_purchase_and_notifies_with_history(tmp_path: Path) -> None:
    facts = ResearchBusinessFacts("货足", Decimal(100), Decimal("2.00"))
    flow, _v1, store, research, _checker, _facts, writer, _notify = _make_flow(
        tmp_path, tier="C", duplicate=None, facts=facts
    )
    class RepeatedChecker:
        def check(self, inquiry_id, _mpn, _quantity, *, at):
            return _confirmed_duplicate(inquiry_id, at=at, repeated=True)

    flow._duplicate_checker = RepeatedChecker()
    result = flow.poll_and_process(FakeSheetsReader(tier="C"), SHEET, now=NOW)[0]

    assert research.inputs
    assert result.business_state is BusinessState.DUPLICATE_STOPPED
    assert not writer.commands
    assert store.active_alerts(result.inquiry_id)[0].alert_type.value == "DUPLICATE_ORDER"
    gui_state = read_v12_order_state(store, result.inquiry_id)
    assert gui_state.business_label.value == "重复订单"
    assert gui_state.latest_active_alert is not None
    assert any(event.event_type.value == "RESEARCH_STARTED" for event in gui_state.event_history)
    with sqlite3.connect(store.database_path) as connection:
        row = connection.execute(
            "SELECT subject, text_body FROM workflow_v12_notification_commands WHERE inquiry_id=?",
            (result.inquiry_id,),
        ).fetchone()
    assert row is not None
    assert "历史数量=8" in row[1]
    assert "数量不相等" in row[1]
    assert "本次数量 × INSO报价 = 73.50" in row[1]


def test_duplicate_unavailable_still_researches_then_waits_for_confirmation(tmp_path: Path) -> None:
    facts = ResearchBusinessFacts("货少", None, Decimal("1.00"))
    flow, _v1, store, research, _checker, _facts, writer, _notify = _make_flow(
        tmp_path, tier="B", duplicate_failure=True, facts=facts
    )
    pending = flow.poll_and_process(FakeSheetsReader(tier="B"), SHEET, now=NOW)[0]

    assert len(research.inputs) == 1
    assert pending.business_state is BusinessState.ROUTING
    assert pending.waiting_reason == "DUPLICATE_CONFIRMATION_REQUIRED"
    assert not writer.commands

    confirmed = _confirmed_duplicate(pending.inquiry_id, at=NOW + timedelta(minutes=1), repeated=False)
    restarted = V12WorkflowCoordinator(
        _v1,
        store,
        FakeResearch(),
        FakeDuplicateChecker(),
        _facts,
        FakePurchaseDraftWriter(completed_at=NOW + timedelta(minutes=1)),
        _notify,
        (NotificationRecipient("synthetic-recipient", "fake@example.invalid"),),
    )
    resumed = restarted.confirm_duplicate_and_route(
        pending.inquiry_id, confirmed, now=NOW + timedelta(minutes=1)
    )
    assert len(research.inputs) == 1
    assert resumed.routing_outcome is PurchaseRoutingOutcome.INDETERMINATE
    assert resumed.waiting_reason == "PURCHASE_ROUTING_INDETERMINATE"
    assert not writer.commands
    assert store.business_state(pending.inquiry_id) is BusinessState.ROUTING
