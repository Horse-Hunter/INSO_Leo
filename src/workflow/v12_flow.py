"""Small fake-capable V1.2 coordinator around the unchanged V1.1 worker."""

from __future__ import annotations

import hashlib
import html
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from src.research import ResearchInput, ResearchResult, ResearchStatus
from src.sheets import (
    PendingSheetRecord,
    WorksheetIdentity,
    WorksheetRowReader,
    query_pending_records,
)

from .service import ResearchExecutor, WorkflowWorker
from .store import WorkflowStateStore
from .v12_contracts import (
    BusinessState,
    DuplicateCheckResult,
    DuplicateOutcome,
    EventType,
    NotificationCommand,
    NotificationKind,
    NotificationRecipient,
    PurchaseDraftCommand,
    PurchaseDraftResult,
    PurchaseOutcome,
    ReasonCode,
    WorkflowEvent,
)
from .v12_notifications import V12NotificationWorker
from .v12_rules import (
    PostResearchRoute,
    PurchaseRoutingOutcome,
    build_ai_input,
    purchase_routing_decision,
    route_after_research,
    should_send_important_order_notification,
    validate_ai_recognition,
)
from .v12_store import V12Store


@dataclass(frozen=True, slots=True)
class ResearchBusinessFacts:
    """Canonical V1.1 Research values needed by V1.2 decisions."""

    inventory_status: str
    estimated_total: Decimal | None
    market_minimum_reference_price: Decimal | None


class DuplicateChecker(Protocol):
    def check(
        self, inquiry_id: str, mpn: str, quantity: int, *, at: datetime
    ) -> DuplicateCheckResult: ...


class ResearchFactsProvider(Protocol):
    def get(self, inquiry_id: str) -> ResearchBusinessFacts | None: ...


class PurchaseDraftWriter(Protocol):
    """Prepare/recognize a draft only; there is deliberately no save method."""

    def prepare(self, command: PurchaseDraftCommand) -> PurchaseDraftResult: ...


@dataclass(frozen=True, slots=True)
class V12FlowResult:
    inquiry_id: str
    business_state: BusinessState
    route: PostResearchRoute | None = None
    routing_outcome: PurchaseRoutingOutcome | None = None
    purchase_outcome: PurchaseOutcome | None = None
    waiting_reason: str | None = None


class FakePurchaseDraftWriter:
    """Pure fake AI recognition adapter. It cannot dispatch any INSO action."""

    def __init__(
        self,
        *,
        recognized_mpn: str | None = None,
        recognized_brand: str | None = None,
        recognized_quantity: int | None = None,
        completed_at: datetime,
    ) -> None:
        self._recognized = (recognized_mpn, recognized_brand, recognized_quantity)
        self._completed_at = completed_at
        self.commands: list[PurchaseDraftCommand] = []

    def prepare(self, command: PurchaseDraftCommand) -> PurchaseDraftResult:
        self.commands.append(command)
        mpn, brand, quantity = self._recognized
        if mpn is None and brand is None and quantity is None:
            mpn, brand, quantity = command.mpn, command.brand, command.quantity
        return validate_ai_recognition(
            command_id=command.command_id,
            completed_at=self._completed_at,
            expected_mpn=command.mpn,
            expected_brand=command.brand,
            expected_quantity=command.quantity,
            recognized_mpn=mpn,
            recognized_brand=brand,
            recognized_quantity=quantity,
        )


class V12WorkflowCoordinator:
    """Run V1.2 decisions while delegating Research execution to V1.1."""

    def __init__(
        self,
        workflow_store: WorkflowStateStore,
        v12_store: V12Store,
        research: ResearchExecutor,
        duplicate_checker: DuplicateChecker,
        research_facts: ResearchFactsProvider,
        purchase_writer: PurchaseDraftWriter,
        notification_worker: V12NotificationWorker,
        recipients: tuple[NotificationRecipient, ...],
    ) -> None:
        self._workflow_store = workflow_store
        self._v12_store = v12_store
        self._research = research
        self._duplicate_checker = duplicate_checker
        self._research_facts = research_facts
        self._purchase_writer = purchase_writer
        self._notification_worker = notification_worker
        self._recipients = recipients
        self._records: dict[str, PendingSheetRecord] = {}
        self._duplicate_results: dict[str, DuplicateCheckResult] = {}
        self._research_results: dict[str, ResearchResult] = {}
        self._last_inquiry_id: str | None = None

    def run_notifications(self, *, now: datetime) -> int:
        """Deliver due commands independently of the purchase workflow."""

        return self._notification_worker.run_due(now=now)

    def poll_and_process(
        self,
        reader: WorksheetRowReader,
        worksheet: WorksheetIdentity,
        *,
        now: datetime,
    ) -> tuple[V12FlowResult, ...]:
        """Read pending rows through the existing Sheets schema and process fakes."""

        return self.process_pending(query_pending_records(reader, worksheet), now=now)

    def process_pending(
        self, records: tuple[PendingSheetRecord, ...], *, now: datetime
    ) -> tuple[V12FlowResult, ...]:
        new_ids: list[str] = []
        for record in records:
            if not self._workflow_store.enqueue(record, now=now):
                continue
            item = next(
                item
                for item in self._workflow_store.all_items()
                if item.record_identity == record.record_identity
            )
            self._records[item.inquiry_id] = record
            new_ids.append(item.inquiry_id)
            self._set_state(
                item.inquiry_id,
                BusinessState.DUPLICATE_CHECK_PENDING,
                EventType.DUPLICATE_CHECK_STARTED,
                now,
            )
            self._v12_store.record_customer_snapshot(
                item.inquiry_id,
                record.customer_name,
                record.customer_name_source,
                at=now,
            )

        wrapped_research = _DuplicateThenResearch(self, now)
        worker = WorkflowWorker(self._workflow_store, wrapped_research)
        results: list[V12FlowResult] = []
        remaining = set(new_ids)
        while remaining:
            item = worker.process_due_one(now=now)
            if item is None:
                break
            inquiry_id = wrapped_research.last_inquiry_id
            if inquiry_id is None or inquiry_id not in remaining:
                break
            remaining.remove(inquiry_id)
            research_result = self._research_results.get(inquiry_id)
            if item.status.value in {"RETRY_WAIT", "RESEARCHING", "QUEUED"}:
                self._set_state(
                    inquiry_id,
                    BusinessState.RESEARCH_RETRY_WAIT,
                    EventType.RESEARCH_RETRY_SCHEDULED,
                    now,
                )
                results.append(
                    self._result(
                        inquiry_id,
                        waiting_reason="RESEARCH_RETRY_WAIT",
                    )
                )
            elif research_result is not None:
                results.append(self._route_after_research(inquiry_id, research_result, now))
        return tuple(results)

    def confirm_duplicate_and_route(
        self,
        inquiry_id: str,
        result: DuplicateCheckResult,
        *,
        now: datetime,
        record: PendingSheetRecord | None = None,
        research_result: ResearchResult | None = None,
    ) -> V12FlowResult:
        """Resume a persisted route without executing Research a second time."""

        if result.inquiry_id != inquiry_id or result.outcome is not DuplicateOutcome.CONFIRMED:
            raise ValueError("routing requires a matching confirmed duplicate result")
        if self._v12_store.business_state(inquiry_id) is not BusinessState.ROUTING:
            raise ValueError("inquiry is not waiting for post-Research routing")
        record = record or self._records.get(inquiry_id) or self._pending_record(inquiry_id)
        research_result = research_result or self._research_results.get(inquiry_id)
        if research_result is None:
            item = self._workflow_store.get_by_inquiry_id(inquiry_id)
            if item.research_status is None:
                raise ValueError("completed Research result is not available")
            try:
                status = ResearchStatus(item.research_status)
            except ValueError as exc:
                raise ValueError("completed Research result is invalid") from exc
            research_result = ResearchResult(
                inquiry_id, status, resolved_brand=item.resolved_brand
            )
        self._records[inquiry_id] = record
        self._research_results[inquiry_id] = research_result
        self._duplicate_results[inquiry_id] = result
        self._v12_store.record_duplicate_result(result)
        return self._route_after_research(inquiry_id, research_result, now)

    def _pending_record(self, inquiry_id: str) -> PendingSheetRecord:
        item = self._workflow_store.get_by_inquiry_id(inquiry_id)
        customer_name, customer_source = self._v12_store.customer_snapshot(inquiry_id)
        snapshot = item.record_identity.identifying_snapshot
        return PendingSheetRecord(
            status=snapshot.status,
            importance_raw=item.importance_raw,
            model=item.mpn,
            brand=item.brand,
            quantity=item.quantity,
            row_position=item.record_identity.row_position,
            record_identity=item.record_identity,
            customer_name=customer_name,
            customer_name_source=customer_source,
        )

    def _check_duplicate(self, research_input: ResearchInput, *, at: datetime) -> None:
        inquiry_id = research_input.inquiry_id
        self._last_inquiry_id = inquiry_id
        self._set_state(
            inquiry_id,
            BusinessState.DUPLICATE_CHECKING,
            EventType.DUPLICATE_CHECK_STARTED,
            at,
        )
        try:
            result = self._duplicate_checker.check(
                inquiry_id,
                research_input.mpn,
                int(research_input.quantity),
                at=at,
            )
            if (
                not isinstance(result, DuplicateCheckResult)
                or result.inquiry_id != inquiry_id
            ):
                raise ValueError("duplicate result identity is invalid")
        except Exception:  # noqa: BLE001 - no lookup error becomes a negative result
            result = DuplicateCheckResult(
                inquiry_id,
                DuplicateOutcome.UNAVAILABLE,
                str(research_input.mpn),
                at,
                reason_code=ReasonCode.DUPLICATE_LOOKUP_UNAVAILABLE,
            )
        self._duplicate_results[inquiry_id] = result
        self._v12_store.record_duplicate_result(result)
        self._set_state(
            inquiry_id,
            BusinessState.RESEARCHING,
            EventType.RESEARCH_STARTED,
            at,
        )

    def _route_after_research(
        self, inquiry_id: str, research_result: ResearchResult, now: datetime
    ) -> V12FlowResult:
        duplicate_result = self._duplicate_results[inquiry_id]
        route = route_after_research(duplicate_result)
        if route is PostResearchRoute.DUPLICATE_CONFIRMATION_REQUIRED:
            self._set_state(
                inquiry_id,
                BusinessState.ROUTING,
                EventType.DUPLICATE_CHECK_FAILED,
                now,
                duplicate_result.reason_code or ReasonCode.DUPLICATE_LOOKUP_UNAVAILABLE,
            )
            return self._result(inquiry_id, route=route, waiting_reason="DUPLICATE_CONFIRMATION_REQUIRED")
        if route is PostResearchRoute.DUPLICATE_STOP:
            self._set_state(inquiry_id, BusinessState.DUPLICATE_STOPPED, EventType.DUPLICATE_ORDER_DETECTED, now, ReasonCode.DUPLICATE_ORDER_DETECTED)
            self._enqueue_notification(
                inquiry_id,
                NotificationKind.DUPLICATE_ORDER,
                research_result,
                now,
                duplicate_result=duplicate_result,
            )
            return self._result(inquiry_id, route=route)
        if research_result.status not in {ResearchStatus.SUCCESS, ResearchStatus.PARTIAL_SUCCESS}:
            self._set_state(inquiry_id, BusinessState.ROUTING, EventType.IMPORTANT_ORDER_DECIDED, now)
            return self._result(inquiry_id, route=route, waiting_reason="RESEARCH_NOT_SUCCESSFUL")

        record = self._records[inquiry_id]
        facts = self._research_facts.get(inquiry_id)
        tier = _tier(record.importance_raw)
        if facts is None or tier not in {"A", "B", "C"}:
            self._set_state(inquiry_id, BusinessState.ROUTING, EventType.IMPORTANT_ORDER_DECIDED, now)
            return self._result(inquiry_id, route=route, waiting_reason="RESEARCH_FACTS_OR_TIER_UNKNOWN")

        if should_send_important_order_notification(
            tier=tier,
            estimated_total=facts.estimated_total,
            inventory_status=facts.inventory_status,
        ):
            self._enqueue_notification(
                inquiry_id,
                NotificationKind.IMPORTANT_ORDER,
                research_result,
                now,
                facts=facts,
                tier=tier,
            )

        purchase_decision = purchase_routing_decision(
            tier=tier, estimated_total=facts.estimated_total
        )
        if purchase_decision.outcome is PurchaseRoutingOutcome.INDETERMINATE:
            self._set_state(inquiry_id, BusinessState.ROUTING, EventType.IMPORTANT_ORDER_DECIDED, now)
            return self._result(
                inquiry_id,
                route=route,
                routing_outcome=PurchaseRoutingOutcome.INDETERMINATE,
                waiting_reason="PURCHASE_ROUTING_INDETERMINATE",
            )

        quantity = _quantity(record.quantity)
        mpn = record.model.strip() if isinstance(record.model, str) else ""
        brand = research_result.resolved_brand or (record.brand if isinstance(record.brand, str) else "")
        if quantity is None or not mpn or not brand.strip():
            self._set_state(inquiry_id, BusinessState.PURCHASE_EXCEPTION, EventType.SECURITY_CHECK_FAILED, now, ReasonCode.AI_RECOGNITION_MISMATCH)
            return self._result(inquiry_id, route=route, waiting_reason="PURCHASE_INPUT_INVALID")

        command_id = _command_id(inquiry_id, "purchase")
        command = PurchaseDraftCommand(
            command_id=command_id,
            inquiry_id=inquiry_id,
            customer_name=record.customer_name,
            customer_tier=tier,
            mpn=mpn,
            brand=brand.strip(),
            quantity=quantity,
            inventory_status=facts.inventory_status,
            estimated_total=facts.estimated_total,
            market_minimum_reference_price=facts.market_minimum_reference_price,
            quotation_type=purchase_decision.quotation_type.value,
            purchaser=purchase_decision.purchaser.value,
            ai_input=build_ai_input(mpn, brand.strip(), quantity),
        )
        self._set_state(inquiry_id, BusinessState.PURCHASE_DRAFT_PENDING, EventType.PURCHASE_DRAFT_STARTED, now)
        self._set_state(inquiry_id, BusinessState.PURCHASE_DRAFTING, EventType.PURCHASE_DRAFT_STARTED, now)
        self._v12_store.set_purchase_state(
            inquiry_id, command_id, PurchaseOutcome.PRE_SAVE_READY, at=now
        )
        result = self._purchase_writer.prepare(command)
        if result.command_id != command_id or result.outcome not in {
            PurchaseOutcome.AI_RECOGNIZED,
            PurchaseOutcome.VALIDATION_FAILED,
        }:
            result = PurchaseDraftResult(
                command_id, PurchaseOutcome.VALIDATION_FAILED, now,
                reason_code=ReasonCode.AI_RECOGNITION_MISMATCH,
            )
        self._v12_store.set_purchase_state(
            inquiry_id,
            command_id,
            result.outcome,
            at=result.completed_at,
            reason_code=result.reason_code,
        )
        if result.outcome is PurchaseOutcome.VALIDATION_FAILED:
            self._set_state(
                inquiry_id,
                BusinessState.PURCHASE_EXCEPTION,
                EventType.AI_RECOGNITION_MISMATCH,
                result.completed_at,
                ReasonCode.AI_RECOGNITION_MISMATCH,
            )
        return self._result(
            inquiry_id,
            route=route,
            routing_outcome=PurchaseRoutingOutcome.READY,
            purchase_outcome=result.outcome,
        )

    def _enqueue_notification(
        self,
        inquiry_id: str,
        kind: NotificationKind,
        research_result: ResearchResult,
        now: datetime,
        *,
        facts: ResearchBusinessFacts | None = None,
        tier: str | None = None,
        duplicate_result: DuplicateCheckResult | None = None,
    ) -> None:
        record = self._records[inquiry_id]
        if facts is None:
            facts = self._research_facts.get(inquiry_id)
        subject, body = _notification_content(
            kind, record, research_result, facts, tier, duplicate_result
        )
        command = NotificationCommand(
            _command_id(inquiry_id, kind.value.lower()),
            inquiry_id,
            kind,
            self._recipients,
            subject,
            body,
            f"<html><body><pre>{html.escape(body)}</pre></body></html>",
            now,
        )
        self._v12_store.enqueue_notification(command)

    def _set_state(
        self,
        inquiry_id: str,
        state: BusinessState,
        event_type: EventType,
        at: datetime,
        reason_code: ReasonCode | None = None,
    ) -> None:
        self._v12_store.set_business_state(
            inquiry_id,
            state,
            WorkflowEvent(
                f"evt_{uuid.uuid4().hex}",
                inquiry_id,
                event_type,
                at,
                "workflow",
                reason_code,
            ),
        )

    def _result(
        self,
        inquiry_id: str,
        *,
        route: PostResearchRoute | None = None,
        routing_outcome: PurchaseRoutingOutcome | None = None,
        purchase_outcome: PurchaseOutcome | None = None,
        waiting_reason: str | None = None,
    ) -> V12FlowResult:
        return V12FlowResult(
            inquiry_id,
            self._v12_store.business_state(inquiry_id),
            route,
            routing_outcome,
            purchase_outcome,
            waiting_reason,
        )


class _DuplicateThenResearch:
    def __init__(self, coordinator: V12WorkflowCoordinator, at: datetime) -> None:
        self.coordinator = coordinator
        self.at = at
        self.last_inquiry_id: str | None = None

    def execute(self, research_input: ResearchInput) -> ResearchResult:
        self.last_inquiry_id = research_input.inquiry_id
        self.coordinator._check_duplicate(research_input, at=self.at)
        result = self.coordinator._research.execute(research_input)
        self.coordinator._research_results[research_input.inquiry_id] = result
        return result


def _tier(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    return normalized if normalized in {"A", "B", "C"} else None


def _quantity(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.strip().isdecimal():
        parsed = int(value.strip())
        return parsed if parsed > 0 else None
    return None


def _command_id(inquiry_id: str, purpose: str) -> str:
    digest = hashlib.sha256(f"{inquiry_id}:{purpose}".encode()).hexdigest()[:32]
    return f"v12_{digest}"


def _notification_content(
    kind: NotificationKind,
    record: PendingSheetRecord,
    research_result: ResearchResult,
    facts: ResearchBusinessFacts | None,
    tier: str | None,
    duplicate_result: DuplicateCheckResult | None,
) -> tuple[str, str]:
    model = record.model if isinstance(record.model, str) else "--"
    brand = research_result.resolved_brand or (record.brand if isinstance(record.brand, str) else "--")
    quantity = _quantity(record.quantity)
    customer = record.customer_name or "客户名称缺失"
    stock = facts.inventory_status if facts is not None else "待验证"
    market_price = _money(facts.market_minimum_reference_price) if facts else "--"
    total = _money(facts.estimated_total) if facts else "--"
    if kind is NotificationKind.IMPORTANT_ORDER:
        subject = f"【重要订单】【{tier}】{customer}｜{model}｜¥{total}｜{stock}"
        body = "\n".join((
            f"客户名称：{customer}", f"客户等级：{tier}", f"型号：{model}",
            f"品牌：{brand}", f"数量：{quantity if quantity is not None else '--'}",
            f"库存状态：{stock}", f"市场最低参考价：{market_price}",
            f"预估订单总价：{total}", "触发原因：重要订单规则命中", "请及时人工跟进该订单",
        ))
        return subject, body

    duplicate_details = "历史记录：待核对"
    if duplicate_result is not None:
        historical_date = (
            duplicate_result.historical_date.isoformat()
            if duplicate_result.historical_date is not None
            else "--"
        )
        history_quantity = duplicate_result.historical_quantity
        quantity_match = {
            True: "数量相等",
            False: "数量不相等",
            None: "数量关系待核对",
        }[duplicate_result.quantity_equal]
        quote = duplicate_result.inso_quote
        order_total = (
            _money(quote * quantity)
            if quote is not None and quantity is not None
            else "--"
        )
        duplicate_details = "\n".join((
            f"最近一笔 INSO 历史：日期={historical_date}；历史数量={history_quantity if history_quantity is not None else '--'}；{quantity_match}",
            f"制单人：{duplicate_result.creator or '--'}；INSO报价：{_money(quote)} {duplicate_result.currency or ''}".rstrip(),
            f"本次数量 × INSO报价 = {order_total}",
        ))
    duplicate_details += f"\nResearch库存：{stock}；市场参考价：{market_price}；预估总价：{total}"
    subject = f"【INSO重复订单】{customer}｜{model}"
    body = "\n".join((
        f"本次订单：客户={customer}；型号={model}；品牌={brand}；数量={quantity if quantity is not None else '--'}",
        duplicate_details,
        "请及时人工跟进该订单。",
    ))
    return subject, body


def _money(value: Decimal | None) -> str:
    return "--" if value is None else f"{value:,.2f}"
