"""Explicit production wiring for the additive V1.2 workflow seams."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

from src.core import CredentialProvider
from src.inso import AiRecognitionResult, ParentProductFields
from src.research.excel_output import ResearchExcelOutput
from src.workflow.v12_contracts import (
    NotificationRecipient,
    PurchaseDraftCommand,
    PurchaseDraftResult,
    PurchaseOutcome,
    ReasonCode,
    ReconciliationOutcome,
    ReconciliationResult,
)
from src.workflow.v12_flow import (
    DuplicateChecker,
    ResearchBusinessFacts,
    ResearchFactsProvider,
    V12WorkflowCoordinator,
)
from src.workflow.v12_notifications import (
    NotificationTransport,
    V12NotificationWorker,
)
from src.workflow.v12_rules import validate_ai_recognition
from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
from src.workflow.v12_store import (
    ReadOnlySaveReconciler,
    V12Store,
)


class _PurchasePrepareActions(Protocol):
    """Only the prepare actions needed here; Save is deliberately absent."""

    def new_draft(self) -> None: ...

    def set_customer(self, value: str) -> None: ...

    def set_quotation_type(self, value: str) -> None: ...

    def set_purchaser(self, value: str) -> None: ...

    def open_ai_entry(self) -> None: ...

    def set_ai_input(self, value: str) -> None: ...

    def run_ai_recognition(self) -> None: ...

    def read_ai_result(self) -> AiRecognitionResult: ...


class CoordinatorPurchaseDraftWriter:
    """Workflow-facing prepare sequence; it has no Save or Send capability."""

    def __init__(
        self,
        *,
        actions: _PurchasePrepareActions,
        parent_fields: ParentProductFields,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if parent_fields is None:
            raise ValueError("verified parent product fields are required")
        self._actions = actions
        self._parent_fields = parent_fields
        self._clock = clock or (lambda: datetime.now(UTC))

    def prepare(self, command: PurchaseDraftCommand) -> PurchaseDraftResult:
        try:
            self._actions.new_draft()
            self._actions.set_customer("Win Source Elec. Tech. Ltd")
            self._actions.set_quotation_type(command.quotation_type)
            self._actions.set_purchaser(command.purchaser)
            self._actions.open_ai_entry()
            self._actions.set_ai_input(command.ai_input)
            self._actions.run_ai_recognition()
            preview = self._actions.read_ai_result()
        except Exception:  # noqa: BLE001 - return only a typed safe failure
            return self._failed(command, ReasonCode.CONTROL_NOT_FOUND)

        preview_check = validate_ai_recognition(
            command_id=command.command_id,
            completed_at=self._clock(),
            expected_mpn=command.mpn,
            expected_brand=command.brand,
            expected_quantity=command.quantity,
            recognized_mpn=preview.model if preview.ready else None,
            recognized_brand=preview.brand if preview.ready else None,
            recognized_quantity=preview.quantity if preview.ready else None,
        )
        if preview_check.outcome is not PurchaseOutcome.AI_RECOGNIZED:
            return preview_check

        try:
            self._parent_fields.set_model(preview.model)
            self._parent_fields.set_brand(preview.brand)
            self._parent_fields.set_quantity(preview.quantity)
            parent_model = self._parent_fields.read_model()
            parent_brand = self._parent_fields.read_brand()
            parent_quantity = self._parent_fields.read_quantity()
        except Exception:  # noqa: BLE001 - no raw adapter error crosses contract
            return self._failed(command, ReasonCode.CONTROL_NOT_FOUND)

        return validate_ai_recognition(
            command_id=command.command_id,
            completed_at=self._clock(),
            expected_mpn=command.mpn,
            expected_brand=command.brand,
            expected_quantity=command.quantity,
            recognized_mpn=parent_model,
            recognized_brand=parent_brand,
            recognized_quantity=parent_quantity,
        )

    def _failed(
        self, command: PurchaseDraftCommand, reason: ReasonCode
    ) -> PurchaseDraftResult:
        return PurchaseDraftResult(
            command_id=command.command_id,
            outcome=PurchaseOutcome.VALIDATION_FAILED,
            completed_at=self._clock(),
            reason_code=reason,
        )


class ResearchExcelFactsProvider:
    """Read the already-persisted canonical Research snapshot for V1.2."""

    def __init__(self, output: ResearchExcelOutput) -> None:
        self._output = output

    def get(self, inquiry_id: str) -> ResearchBusinessFacts | None:
        try:
            matches = tuple(
                row for row in self._output.read_history()
                if row.inquiry_id == inquiry_id
            )
        except Exception:  # noqa: BLE001 - unavailable facts fail closed
            return None
        if len(matches) != 1:
            return None
        row = matches[0]
        if not row.stock_label:
            return None
        return ResearchBusinessFacts(
            inventory_status=row.stock_label,
            estimated_total=_stored_decimal(row.estimated_total),
            market_minimum_reference_price=_market_minimum(row.market_reference),
        )


def _stored_decimal(value: object | None) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = Decimal(str(value).strip().replace(",", "").removeprefix("¥"))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _market_minimum(value: str | None) -> Decimal | None:
    if value is None:
        return None
    # Research serializes its canonical minimum on line one; an optional
    # comparison price/source follows on line two.
    return _stored_decimal(value.splitlines()[0] if value.splitlines() else None)


@dataclass(frozen=True, slots=True)
class V12ProductionAdapters:
    """Live adapters required before the launcher can compose a V1.2 flow."""

    duplicate_checker: DuplicateChecker
    research_facts: ResearchFactsProvider
    purchase_writer: CoordinatorPurchaseDraftWriter
    notification_transport: NotificationTransport
    recipients: tuple[NotificationRecipient, ...]
    save_reconciler: ReadOnlySaveReconciler | None = None

    @classmethod
    def with_qq_smtp(
        cls,
        *,
        duplicate_checker: DuplicateChecker,
        research_facts: ResearchFactsProvider,
        purchase_writer: CoordinatorPurchaseDraftWriter,
        smtp_config: QQSMTPConfig,
        recipients: tuple[NotificationRecipient, ...],
        credentials: CredentialProvider | None = None,
        save_reconciler: ReadOnlySaveReconciler | None = None,
    ) -> V12ProductionAdapters:
        """Bind the existing QQ transport to the explicit sender config."""

        return cls(
            duplicate_checker=duplicate_checker,
            research_facts=research_facts,
            purchase_writer=purchase_writer,
            notification_transport=QQSMTPTransport(
                config=smtp_config, credentials=credentials
            ),
            recipients=recipients,
            save_reconciler=save_reconciler,
        )

    def __post_init__(self) -> None:
        if not isinstance(self.purchase_writer, CoordinatorPurchaseDraftWriter):
            raise TypeError("V1.2 purchase writer requires parent product fields")
        required = (
            self.duplicate_checker,
            self.research_facts,
            self.purchase_writer,
            self.notification_transport,
        )
        if any(adapter is None for adapter in required) or not self.recipients:
            raise ValueError("V1.2 production adapters are incomplete")


@dataclass(frozen=True, slots=True)
class V12ProductionComposition:
    coordinator: V12WorkflowCoordinator
    notification_worker: V12NotificationWorker
    save_reconciler: ReadOnlySaveReconciler


class UnavailableReadOnlySaveReconciler(ReadOnlySaveReconciler):
    """Fail-closed result until a verified saved-record reader exists."""

    def reconcile(self, inquiry_id: str) -> ReconciliationResult:
        del inquiry_id
        return ReconciliationResult(
            ReconciliationOutcome.UNKNOWN,
            datetime.now(UTC),
            reason_code=ReasonCode.RECONCILIATION_UNREADABLE,
        )


def compose_v12_production(
    *,
    workflow_store,
    v12_store: V12Store,
    research,
    adapters: V12ProductionAdapters,
) -> V12ProductionComposition:
    """Build the real seams only when every required adapter is explicit."""

    notification_worker = V12NotificationWorker(
        v12_store, adapters.notification_transport
    )
    coordinator = V12WorkflowCoordinator(
        workflow_store,
        v12_store,
        research,
        adapters.duplicate_checker,
        adapters.research_facts,
        adapters.purchase_writer,
        notification_worker,
        adapters.recipients,
    )
    return V12ProductionComposition(
        coordinator,
        notification_worker,
        adapters.save_reconciler or UnavailableReadOnlySaveReconciler(),
    )
