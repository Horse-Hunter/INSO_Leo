"""Explicit production wiring for the additive V1.2 workflow seams."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from src.workflow.v12_contracts import (
    NotificationRecipient,
    ReasonCode,
    ReconciliationOutcome,
    ReconciliationResult,
)
from src.workflow.v12_flow import (
    DuplicateChecker,
    PurchaseDraftWriter,
    ResearchFactsProvider,
    V12WorkflowCoordinator,
)
from src.workflow.v12_notifications import (
    NotificationTransport,
    V12NotificationWorker,
)
from src.workflow.v12_store import (
    ReadOnlySaveReconciler,
    V12Store,
)


@dataclass(frozen=True, slots=True)
class V12ProductionAdapters:
    """Live adapters required before the launcher can compose a V1.2 flow."""

    duplicate_checker: DuplicateChecker
    research_facts: ResearchFactsProvider
    purchase_writer: PurchaseDraftWriter
    notification_transport: NotificationTransport
    recipients: tuple[NotificationRecipient, ...]
    save_reconciler: ReadOnlySaveReconciler | None = None

    def __post_init__(self) -> None:
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
