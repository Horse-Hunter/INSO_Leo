from __future__ import annotations

import sqlite3
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from src.launcher.v12_gui import read_v12_order_state
from src.research import ResearchInput, ResearchResult, ResearchStatus
from src.sheets import WorksheetIdentity, WorksheetRow
from src.workflow import (
    ResearchPreparationError,
    WorkflowStateStore,
    WorkflowStatus,
)
from src.workflow.v12_contracts import (
    BusinessState,
    DeliveryOutcome,
    DuplicateCheckResult,
    DuplicateOutcome,
    NotificationKind,
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
    def __init__(self, *, tier: str = "A", quantity: int = 7, brand: str = "Brand-X") -> None:
        self.row = WorksheetRow(
            3,
            {
                "A": "未发",
                "C": tier,
                "D": "Synthetic Customer",
                "E": "Mpn-1",
                "F": brand,
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


class FlakyResearch:
    """Fail before Research until the Owner restores the INSO session."""

    def __init__(self) -> None:
        self.inputs: list[ResearchInput] = []
        self.available = False

    def execute(self, item: ResearchInput) -> ResearchResult:
        if not self.available:
            raise ResearchPreparationError("CDP browser requires manual handling")
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


def test_result_is_published_before_the_next_order_runs(tmp_path):
    from dataclasses import replace

    from src.sheets.pending import query_pending_records
    flow, ws, _vs, research, _checker, _provider, _writer, _worker = _make_flow(
        tmp_path, facts=ResearchBusinessFacts("货少", Decimal(10), Decimal(2)))
    first = query_pending_records(FakeSheetsReader(), SHEET)[0]
    second = replace(first, row_position=4,
                     record_identity=replace(first.record_identity, row_position=4))
    published = []
    flow._on_result = lambda result: published.append((result.inquiry_id, len(research.inputs)))
    flow.process_pending((first, second), now=NOW)
    assert [count for _, count in published] == [1, 2]
    assert [iid for iid, _ in published] == [ws.inquiry_id_for(r.record_identity) for r in (first, second)]


def test_all_no_prices_is_terminal_research_failure_and_never_purchase(tmp_path):
    from src.gui.app import _v12_status_text
    from src.gui.contracts import V12BusinessLabel
    from src.research import ResearchReasonCode

    flow, ws, store, research, _checker, _provider, writer, _worker = _make_flow(tmp_path)
    research.execute = lambda item: ResearchResult(item.inquiry_id, ResearchStatus.EXCEPTION,
        reason_code=ResearchReasonCode.NO_MATCHING_PRODUCT)
    result = flow.poll_and_process(FakeSheetsReader(), SHEET, now=NOW)[0]
    assert result.business_state is BusinessState.RESEARCH_FAILED
    assert ws.get_by_inquiry_id(result.inquiry_id).status is WorkflowStatus.FAILED
    assert writer.commands == []
    state = read_v12_order_state(store, result.inquiry_id)
    assert state.business_label is V12BusinessLabel.RESEARCH_EXCEPTION
    assert _v12_status_text(state, "失败") == "调研无报价（未发采购）"
    # Existing failed history needs display correction only, not DB rewrite/replay.
    from src.workflow.v12_contracts import EventType, WorkflowEvent
    store.set_business_state(result.inquiry_id, BusinessState.ROUTING,
        WorkflowEvent("evt_legacy", result.inquiry_id, EventType.IMPORTANT_ORDER_DECIDED, NOW, "workflow"))
    assert _v12_status_text(read_v12_order_state(store, result.inquiry_id), "失败") == "调研无报价（未发采购）"


def test_delivered_duplicate_is_not_recreated_from_changed_repeat_facts(tmp_path):
    from dataclasses import replace
    transport = FakeNotificationTransport({"synthetic-recipient": (DeliveryOutcome.SENT,)})
    flow, ws, _vs, _research, _checker, _provider, _writer, worker = _make_flow(
        tmp_path, notification_transport=transport)
    from src.sheets.pending import query_pending_records
    record = query_pending_records(FakeSheetsReader(), SHEET)[0]
    ws.enqueue(record, now=NOW)
    iid = ws.inquiry_id_for(record.record_identity)
    flow._records[iid] = record
    result = ResearchResult(iid, ResearchStatus.SUCCESS, resolved_brand="Brand-X")
    duplicate = _confirmed_duplicate(iid, at=NOW, repeated=True)
    flow._enqueue_notification(iid, NotificationKind.DUPLICATE_ORDER, result,
                               NOW, duplicate_result=duplicate)
    worker.run_due(now=NOW)
    flow._enqueue_notification(iid, NotificationKind.DUPLICATE_ORDER, result,
                               NOW + timedelta(hours=1),
                               duplicate_result=replace(duplicate, creator="Changed creator"))
    worker.run_due(now=NOW + timedelta(hours=1))
    assert len(transport.calls) == 1


@pytest.mark.parametrize("duplicate_failure", [False, True])
def test_a_notice_survives_research_retry_but_requires_confirmed_nonduplicate(
    tmp_path, duplicate_failure,
):
    transport = FakeNotificationTransport({"synthetic-recipient": (DeliveryOutcome.SENT,)})
    flow, _ws, _vs, research, _checker, _provider, _writer, worker = _make_flow(
        tmp_path, duplicate_failure=duplicate_failure, notification_transport=transport)
    research.execute = lambda item: ResearchResult(item.inquiry_id, ResearchStatus.RETRYABLE_FAILURE)
    result = flow.poll_and_process(FakeSheetsReader(tier="A"), SHEET, now=NOW)
    assert result[0].waiting_reason == "RESEARCH_NOT_SUCCESSFUL"
    worker.run_due(now=NOW)
    assert len(transport.calls) == (0 if duplicate_failure else 1)


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


def test_completed_research_duplicate_lookup_recovers_on_normal_poll(tmp_path: Path) -> None:
    flow, workflow, store, research, checker, facts, writer, notify = _make_flow(
        tmp_path, duplicate_failure=True,
        facts=ResearchBusinessFacts("货足", Decimal(10), Decimal("1.00")),
    )
    pending = flow.poll_and_process(FakeSheetsReader(), SHEET, now=NOW)[0]
    checker.failure = False
    restarted = V12WorkflowCoordinator(
        workflow, store, research, checker, facts, writer, notify,
        (NotificationRecipient("synthetic-recipient", "fake@example.invalid"),),
    )
    result = restarted.poll_and_process(
        FakeSheetsReader(), SHEET, now=NOW + timedelta(minutes=15)
    )[0]
    assert result.inquiry_id == pending.inquiry_id
    assert len(research.inputs) == 1
    assert len(writer.commands) == 1
    assert len(workflow.all_items()) == 1
    assert not store.duplicate_confirmation_pending(pending.inquiry_id)
    restarted.poll_and_process(FakeSheetsReader(), SHEET, now=NOW + timedelta(minutes=30))
    assert len(writer.commands) == 1


def test_duplicate_recovery_does_not_route_changed_or_removed_pending_row(tmp_path: Path) -> None:
    flow, workflow, store, research, checker, _facts, writer, _notify = _make_flow(
        tmp_path, duplicate_failure=True,
        facts=ResearchBusinessFacts("货足", Decimal(10), Decimal("1.00")),
    )
    pending = flow.poll_and_process(FakeSheetsReader(), SHEET, now=NOW)[0]
    checker.failure = False
    flow.process_pending((), now=NOW + timedelta(minutes=15))
    flow.poll_and_process(FakeSheetsReader(quantity=999), SHEET, now=NOW + timedelta(minutes=30))
    assert len(research.inputs) == 1
    assert not writer.commands
    assert store.business_state(pending.inquiry_id) is BusinessState.SOURCE_CHANGED
    assert len(workflow.all_items()) == 1


def test_duplicate_recovery_failure_stays_pending_without_research(tmp_path: Path) -> None:
    flow, _workflow, store, research, _checker, _facts, writer, _notify = _make_flow(
        tmp_path, duplicate_failure=True,
        facts=ResearchBusinessFacts("货足", Decimal(10), Decimal("1.00")),
    )
    pending = flow.poll_and_process(FakeSheetsReader(), SHEET, now=NOW)[0]
    flow.poll_and_process(FakeSheetsReader(), SHEET, now=NOW + timedelta(minutes=15))
    assert len(research.inputs) == 1
    assert not writer.commands
    assert store.duplicate_confirmation_pending(pending.inquiry_id)


def test_released_inquiry_is_resumed_by_the_next_poll(tmp_path: Path) -> None:
    """A poll that released an inquiry must not strand it in the durable queue.

    Live failure class (2026-09-29): INSO demanded a human SMS code, so Research
    preparation failed and ``WorkflowWorker.process_due_one`` released the
    inquiry back to ``QUEUED``. The next poll read the same pending row, found it
    already enqueued, and — because the drain was bounded to the rows that poll
    had inserted — never claimed the released inquiry again. Post-Research
    routing therefore could not run even after the Owner restored the session.
    """

    flow, workflow_store, _v12, _research, _checker, _facts, _writer, _notify = _make_flow(
        tmp_path,
        facts=ResearchBusinessFacts("货足", Decimal(60001), Decimal("2.00")),
    )
    flaky = FlakyResearch()
    flow._research = flaky

    with pytest.raises(ResearchPreparationError):
        flow.poll_and_process(FakeSheetsReader(), SHEET, now=NOW)

    (released,) = workflow_store.all_items()
    assert released.status is WorkflowStatus.QUEUED
    assert released.attempt_count == 0
    assert released.last_error == "Research preparation requires manual handling"
    assert not flaky.inputs

    flaky.available = True
    results = flow.poll_and_process(
        FakeSheetsReader(), SHEET, now=NOW + timedelta(minutes=15)
    )

    assert [item.inquiry_id for item in flaky.inputs] == [released.inquiry_id]
    assert [result.inquiry_id for result in results] == [released.inquiry_id]
    assert results[0].business_state is BusinessState.PURCHASE_DRAFTING
    assert results[0].purchase_outcome.value == "AI_RECOGNIZED"


def test_notification_resolves_the_row_without_this_polls_sheet_snapshot(
    tmp_path: Path,
) -> None:
    """A processed inquiry must still notify once its Sheet row is gone.

    Live failure class (2026-09-29): the durable queue, not this poll's Sheet
    snapshot, decides what is processed, so an inquiry can reach notification
    with no fresh row in ``_records``. Indexing that map directly raised
    ``KeyError`` out of the runtime *after* Research had already succeeded,
    which stopped the whole run instead of sending the notification.
    """

    (
        flow,
        _workflow_store,
        v12_store,
        _research,
        _checker,
        _facts,
        _writer,
        _notify,
    ) = _make_flow(
        tmp_path,
        facts=ResearchBusinessFacts("货足", Decimal(60001), Decimal("2.00")),
    )
    results = flow.poll_and_process(FakeSheetsReader(), SHEET, now=NOW)
    inquiry_id = results[0].inquiry_id
    assert v12_store.claim_due_notifications(now=NOW, limit=64)

    # The inquiry is still ours, but this poll read no row for it. A distinct
    # kind keeps the command id unique, so the enqueue is not idempotent-ignored.
    flow._records.clear()
    flow._enqueue_notification(
        inquiry_id,
        NotificationKind.DUPLICATE_ORDER,
        ResearchResult(inquiry_id, ResearchStatus.SUCCESS, resolved_brand="Brand-X"),
        NOW,
        facts=ResearchBusinessFacts("货足", Decimal(60001), Decimal("2.00")),
        tier="A",
    )
    assert v12_store.claim_due_notifications(now=NOW, limit=64), (
        "the notification must still be queued without a Sheet row"
    )


def test_row_with_non_numeric_quantity_is_skipped_with_a_reason(tmp_path: Path) -> None:
    flow, workflow_store, store, research, checker, _facts, writer, _notifications = _make_flow(
        tmp_path,
        facts=ResearchBusinessFacts("货足", Decimal(60001), Decimal("2.00")),
    )

    results = flow.poll_and_process(FakeSheetsReader(quantity="Qty"), SHEET, now=NOW)

    # A column legend is not an inquiry: no duplicate lookup, no Research, no draft.
    assert research.inputs == []
    assert checker.calls == []
    assert writer.commands == []

    assert len(results) == 1
    inquiry_id = results[0].inquiry_id
    assert results[0].business_state is BusinessState.INVALID_INPUT_SKIPPED
    assert results[0].waiting_reason == "INVALID_QUANTITY_SKIPPED"

    # The reason is recorded where the operator can see it.
    assert store.order_summary(inquiry_id).business_label.value == "已跳过（数据异常）"
    alerts = store.active_alerts(inquiry_id)
    assert [alert.alert_type.value for alert in alerts] == ["DATA_QUALITY"]
    assert alerts[0].reason_code is ReasonCode.INQUIRY_QUANTITY_INVALID
    assert [event.event_type.value for event in store.event_history(inquiry_id)] == [
        "DATA_QUALITY_INVALID_QUANTITY"
    ]

    # And the row is held out of the queue, so it can never be claimed.
    item = workflow_store.get_by_inquiry_id(inquiry_id)
    assert item.status is WorkflowStatus.MANUAL_REVIEW
    assert item.last_error == "INVALID_QUANTITY_INPUT"
    assert workflow_store.claim_due(now=NOW + timedelta(minutes=15)) is None


def test_a_held_back_row_records_its_reason_once(tmp_path: Path) -> None:
    flow, _workflow_store, store, _research, _checker, _facts, _writer, _notifications = _make_flow(
        tmp_path
    )

    first = flow.poll_and_process(FakeSheetsReader(quantity="Qty"), SHEET, now=NOW)
    flow.poll_and_process(FakeSheetsReader(quantity="Qty"), SHEET, now=NOW + timedelta(minutes=15))
    flow.poll_and_process(FakeSheetsReader(quantity="Qty"), SHEET, now=NOW + timedelta(minutes=30))

    inquiry_id = first[0].inquiry_id
    assert len(store.event_history(inquiry_id)) == 1
    assert len(store.active_alerts(inquiry_id)) == 1


def test_corrected_worksheet_row_resumes_the_normal_flow(tmp_path: Path) -> None:
    flow, _workflow_store, _store, research, _checker, _facts, writer, _notifications = _make_flow(
        tmp_path,
        facts=ResearchBusinessFacts("货足", Decimal(60001), Decimal("2.00")),
    )

    held = flow.poll_and_process(FakeSheetsReader(quantity="Qty"), SHEET, now=NOW)
    inquiry_id = held[0].inquiry_id
    assert research.inputs == []

    results = flow.poll_and_process(
        FakeSheetsReader(quantity=7), SHEET, now=NOW + timedelta(minutes=15)
    )

    assert [(item.inquiry_id, item.quantity) for item in research.inputs] == [(inquiry_id, 7)]
    assert results[0].business_state is BusinessState.PURCHASE_DRAFTING
    assert results[0].purchase_outcome.value == "AI_RECOGNIZED"
    assert len(writer.commands) == 1


class UnresolvedBrandResearch:
    """Research that found prices but could not resolve the missing brand."""

    def __init__(self) -> None:
        self.inputs: list[ResearchInput] = []

    def execute(self, item: ResearchInput) -> ResearchResult:
        self.inputs.append(item)
        return ResearchResult(item.inquiry_id, ResearchStatus.SUCCESS, resolved_brand=None)


@pytest.mark.parametrize("brand", ["UNKNOWN", "unknown", "  UnKnOwN  ", "", "   "])
def test_a_placeholder_sheet_brand_is_asked_for_rather_than_trusted(
    tmp_path: Path, brand: str,
) -> None:
    """Owner decision (2026-09-30): Brand ``unknown`` must be looked up.

    Both consumption points are checked at once: Research is handed no brand
    (so it resolves one), and the placeholder is never used as the expected
    brand for an INSO draft.
    """

    flow, _workflow_store, _store, _research, _checker, _facts, writer, _notifications = _make_flow(
        tmp_path,
        facts=ResearchBusinessFacts("货足", Decimal(60001), Decimal("2.00")),
    )
    unresolved = UnresolvedBrandResearch()
    flow._research = unresolved

    results = flow.poll_and_process(FakeSheetsReader(brand=brand), SHEET, now=NOW)

    assert len(unresolved.inputs) == 1
    assert unresolved.inputs[0].brand is None
    assert writer.commands == []
    assert results[0].business_state is BusinessState.PURCHASE_EXCEPTION
    assert results[0].waiting_reason == "PURCHASE_INPUT_INVALID"


@pytest.mark.parametrize("duplicate", [False, True])
def test_s_and_a_have_identical_business_routing_with_raw_s_preserved(tmp_path, duplicate):
    outcomes, commands, kinds = [], [], []
    for tier in ("S", "A"):
        facts = ResearchBusinessFacts("货足", Decimal(10), Decimal(2))
        flow, ws, vs, research, checker, _, writer, _ = _make_flow(tmp_path / tier, facts=facts)
        if duplicate:
            checker.check = lambda iid, *a, **k: _confirmed_duplicate(iid, at=NOW, repeated=True)
        result, = flow.poll_and_process(FakeSheetsReader(tier=tier), SHEET, now=NOW)
        item = ws.get_by_inquiry_id(result.inquiry_id)
        assert len(research.inputs) == 1 and result.business_state is not BusinessState.INVALID_INPUT_SKIPPED
        assert item.importance_raw == tier
        assert item.record_identity.identifying_snapshot.importance_raw == tier
        assert flow._records[result.inquiry_id].importance_raw == tier
        outcomes.append((result.business_state, result.routing_outcome, result.purchase_outcome))
        commands.append([(c.customer_tier, c.quotation_type, c.purchaser) for c in writer.commands])
        kinds.append([c.kind for c in vs.claim_due_notifications(now=NOW)])
    assert outcomes[0] == outcomes[1] and commands[0] == commands[1] and kinds[0] == kinds[1]
    if not duplicate:
        assert commands[0] == [("A", "需要问全价格", "颜浩坚")]
        assert NotificationKind.IMPORTANT_ORDER in kinds[0]


@pytest.mark.parametrize("tier", ["D", "", "UNKNOWN"])
def test_other_invalid_tiers_are_not_effective_a(tmp_path, tier):
    flow, _, vs, research, _, _, writer, _ = _make_flow(tmp_path)
    result, = flow.poll_and_process(FakeSheetsReader(tier=tier), SHEET, now=NOW)
    assert result.business_state is BusinessState.INVALID_INPUT_SKIPPED
    assert not research.inputs and not writer.commands and vs.active_alerts(result.inquiry_id)


@pytest.mark.parametrize("brand", ["UNKNOWN", ""])
def test_missing_brand_uses_research_resolution_for_procurement(tmp_path, brand):
    flow, _ws, _vs, research, _checker, _facts, writer, _notifications = _make_flow(
        tmp_path, facts=ResearchBusinessFacts("货足", Decimal(10), Decimal(2)),
    )
    result, = flow.poll_and_process(FakeSheetsReader(brand=brand), SHEET, now=NOW)
    assert len(research.inputs) == 1 and research.inputs[0].brand is None
    assert len(writer.commands) == 1
    assert writer.commands[0].brand == "Brand-X"
    assert result.business_state is BusinessState.PURCHASE_DRAFTING


def test_previously_skipped_unknown_brand_resumes_without_source_edit(tmp_path):
    flow, ws, vs, research, _checker, _facts, writer, _notifications = _make_flow(
        tmp_path, facts=ResearchBusinessFacts("货足", Decimal(10), Decimal(2)),
    )
    from src.sheets import query_pending_records

    reader = FakeSheetsReader(brand="UNKNOWN")
    record, = query_pending_records(reader, SHEET)
    ws.enqueue(record, now=NOW)
    iid = ws.inquiry_id_for(record.record_identity)
    ws.mark_skipped_input(ws.get_by_inquiry_id(iid).id, now=NOW)
    vs.skip_invalid_quantity(iid, at=NOW, reason_code=ReasonCode.INQUIRY_INPUT_INVALID)

    result, = flow.poll_and_process(reader, SHEET, now=NOW + timedelta(minutes=15))
    assert result.inquiry_id == iid
    assert len(ws.all_items()) == 1
    assert len(research.inputs) == 1 and research.inputs[0].brand is None
    assert len(writer.commands) == 1 and writer.commands[0].brand == "Brand-X"
    assert result.business_state is BusinessState.PURCHASE_DRAFTING
    assert not vs.active_alerts(iid)


@pytest.mark.parametrize("brand", ["UNKNOWN", ""])
def test_active_coordinator_writes_resolved_missing_brand(tmp_path, brand):
    from src.sheets import WorksheetRow
    from src.workflow import SheetsSafeBrandUpdater

    flow, ws, _vs, _research, _checker, _facts, writer, _notifications = _make_flow(
        tmp_path, facts=ResearchBusinessFacts("货足", Decimal(10), Decimal(2)),
    )
    class MutableSheet(FakeSheetsReader):
        def __init__(self):
            super().__init__(brand=brand)
            self.writes = []
        def write_brand(self, worksheet, row_position, value):
            self.writes.append((row_position, value))
            cells = dict(self.row.cells)
            cells["F"] = value
            self.row = WorksheetRow(row_position, cells)

    sheet = MutableSheet()
    flow._brand_updater = SheetsSafeBrandUpdater(sheet, sheet, verify_readback=True)
    result, = flow.poll_and_process(sheet, SHEET, now=NOW)
    assert sheet.writes == [(3, "Brand-X")]
    assert ws.get_by_inquiry_id(result.inquiry_id).brand_update_status == "UPDATED"
    assert writer.commands[0].brand == "Brand-X"


@pytest.mark.parametrize("total,high", [("19999.99", False), ("20000", True), ("20000.01", True)])
@pytest.mark.parametrize("legacy_a", [False, True])
def test_shahab_workflow_uses_independent_rule_and_retains_identity(tmp_path, total, high, legacy_a):
    from dataclasses import replace

    from src.sheets.pending import query_pending_records

    worksheet = WorksheetIdentity("synthetic-sheet", "SHAHAB")
    class Reader:
        def read_rows(self, target):
            assert target == worksheet
            return (WorksheetRow(3, {"B": "未发", "D": "Mpn-1", "E": "Brand-X", "F": 7}),)
    record = query_pending_records(Reader(), worksheet)[0]
    if legacy_a:
        record = replace(record, importance_raw="A")
    flow, ws, store, research, _checker, _provider, writer, _worker = _make_flow(
        tmp_path, facts=ResearchBusinessFacts("货足", Decimal(total), Decimal(1)))
    result = flow.process_pending((record,), now=NOW)[0]
    assert result.inquiry_id == ws.inquiry_id_for(record.record_identity)
    assert ws.get_by_inquiry_id(result.inquiry_id).record_identity.identifying_snapshot.importance_raw is None
    assert len(research.inputs) == len(writer.commands) == 1
    command = writer.commands[0]
    assert command.customer_tier == "SHAHAB"
    assert command.purchaser == ("颜浩坚" if high else "陈熙")
    assert command.quotation_type == ("需要问全价格" if high else "普通询价")
    notices = store.claim_due_notifications(now=NOW)
    assert len(notices) == int(high)
    if high:
        assert notices[0].kind is NotificationKind.IMPORTANT_ORDER
        assert notices[0].subject == "【重要询价】SHAHAB｜Mpn-1"
        assert "客户等级：SHAHAB" in notices[0].text_body
        assert "订单" not in notices[0].text_body


@pytest.mark.parametrize("tier", ["A", "S"])
def test_other_a_s_customers_still_full_price_and_always_notified(tmp_path, tier):
    flow, _ws, store, _research, _checker, _provider, writer, _worker = _make_flow(
        tmp_path, facts=ResearchBusinessFacts("货足", Decimal(1), Decimal(1)))
    flow.poll_and_process(FakeSheetsReader(tier=tier), SHEET, now=NOW)
    assert writer.commands[0].purchaser == "颜浩坚"
    assert writer.commands[0].quotation_type == "需要问全价格"
    notices = store.claim_due_notifications(now=NOW)
    assert len(notices) == 1
    assert notices[0].subject == "【重要询价】Synthetic Customer｜Mpn-1"


@pytest.mark.parametrize("failed_research", [False, True])
def test_shahab_missing_total_never_falls_back_to_a_or_low_amount(tmp_path, failed_research):
    reader = FakeSheetsReader(tier="A")
    reader.row.cells["D"] = "SHAHAB"
    flow, _ws, store, research, _checker, _provider, writer, _worker = _make_flow(
        tmp_path, facts=ResearchBusinessFacts("货少", None, None))
    if failed_research:
        research.execute = lambda item: ResearchResult(item.inquiry_id, ResearchStatus.EXCEPTION)
    result = flow.poll_and_process(reader, SHEET, now=NOW)[0]
    assert result.waiting_reason == ("RESEARCH_NOT_SUCCESSFUL" if failed_research else "PURCHASE_ROUTING_INDETERMINATE")
    assert not writer.commands
    assert not store.claim_due_notifications(now=NOW)


def test_shahab_duplicate_remains_stopped_with_only_duplicate_notice(tmp_path):
    reader = FakeSheetsReader(tier="A")
    reader.row.cells["D"] = "SHAHAB"
    flow, _ws, store, _research, checker, _provider, writer, _worker = _make_flow(
        tmp_path, facts=ResearchBusinessFacts("货少", Decimal(20000), Decimal(1)))
    checker.check = lambda iid, mpn, qty, at: _confirmed_duplicate(iid, at=at, repeated=True)
    result = flow.poll_and_process(reader, SHEET, now=NOW)[0]
    assert result.business_state is BusinessState.DUPLICATE_STOPPED
    assert not writer.commands
    notices = store.claim_due_notifications(now=NOW)
    assert len(notices) == 1 and notices[0].kind is NotificationKind.DUPLICATE_ORDER
    assert notices[0].subject == "【INSO重复询价】SHAHAB｜Mpn-1"
    assert "本次询价" in notices[0].text_body and "历史询价" in notices[0].text_body


@pytest.mark.parametrize("total,expected_purchaser", [("19999.99", "陈熙"), ("20000", "颜浩坚")])
def test_persisted_shahab_a_resumes_with_new_rule_after_restart(tmp_path, total, expected_purchaser):
    from dataclasses import replace

    from src.sheets.pending import query_pending_records

    reader = FakeSheetsReader(tier="A")
    reader.row.cells["D"] = "SHAHAB"
    record = replace(query_pending_records(reader, SHEET)[0], importance_raw="A")
    flow, ws, store, _research, _checker, provider, _writer, worker = _make_flow(
        tmp_path, duplicate_failure=True,
        facts=ResearchBusinessFacts("货足", Decimal(total), Decimal(1)))
    pending = flow.process_pending((record,), now=NOW)[0]
    assert pending.waiting_reason == "DUPLICATE_CONFIRMATION_REQUIRED"
    writer = FakePurchaseDraftWriter(completed_at=NOW)
    restarted = V12WorkflowCoordinator(ws, store, FakeResearch(), FakeDuplicateChecker(),
        provider, writer, worker, (NotificationRecipient("synthetic-recipient", "fake@example.invalid"),))
    result = restarted.confirm_duplicate_and_route(pending.inquiry_id,
        _confirmed_duplicate(pending.inquiry_id, at=NOW, repeated=False), now=NOW)
    assert result.inquiry_id == pending.inquiry_id
    assert len(writer.commands) == 1
    assert writer.commands[0].customer_tier == "SHAHAB"
    assert writer.commands[0].purchaser == expected_purchaser
    notices = store.claim_due_notifications(now=NOW)
    assert len(notices) == int(expected_purchaser == "颜浩坚")
