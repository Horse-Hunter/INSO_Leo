"""Explicit production wiring for the additive V1.2 workflow seams."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from src.core import CredentialProvider
from src.research.excel_output import ResearchExcelOutput
from src.workflow.v12_contracts import (
    NotificationRecipient,
    ReasonCode,
    ReconciliationOutcome,
    ReconciliationResult,
)
from src.workflow.v12_flow import (
    DuplicateChecker,
    PurchaseDraftWriter,
    ResearchBusinessFacts,
    ResearchFactsProvider,
    V12WorkflowCoordinator,
)
from src.workflow.v12_notifications import (
    NotificationTransport,
    V12NotificationWorker,
)
from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
from src.workflow.v12_store import (
    ReadOnlySaveReconciler,
    V12Store,
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
    purchase_writer: PurchaseDraftWriter
    notification_transport: NotificationTransport
    recipients: tuple[NotificationRecipient, ...]
    save_reconciler: ReadOnlySaveReconciler | None = None

    @classmethod
    def with_qq_smtp(
        cls,
        *,
        duplicate_checker: DuplicateChecker,
        research_facts: ResearchFactsProvider,
        purchase_writer: PurchaseDraftWriter,
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
