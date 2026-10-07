"""Explicit production wiring for the additive V1.2 workflow seams."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Protocol

from src.core import CredentialProvider
from src.inso import AiRecognitionResult, InsoOperationAccess, ParentProductFields
from src.inso.duplicate_history import (
    DETAIL_LINK_SELECTOR_TEMPLATE,
    PlaywrightDuplicateHistoryPage,
    parse_inso_timestamp,
)
from src.inso.session import SecurityViolation
from src.launcher.diagnostics import log_step
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
from src.workflow.v12_safety import MpnPolicy, mpn_matches
from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
from src.workflow.v12_store import (
    ReadOnlySaveReconciler,
    V12Store,
)

#: How long the ERP's own grid reload (``ai_appendRow``) may take before the
#: handed-back row counts as absent. The read-back that follows is the authority;
#: this only bounds the wait.
_PARENT_ROW_WAIT_SECONDS = 20.0


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

    def commit_ai_entry(self) -> None: ...


@dataclass(frozen=True, slots=True)
class SaveReconciliationTarget:
    """The exact fields a read-only saved-record lookup must prove."""

    mpn: str
    brand: str
    quantity: int
    submitted_at: datetime | None = None
    baseline_bill_ids: frozenset[str] | None = None


@dataclass(frozen=True, slots=True)
class _SavedDetail:
    bill_id: str
    peno: str
    mpn: str
    brand: str
    quantity: int


class PlaywrightReadOnlySaveReconciler(ReadOnlySaveReconciler):
    """Reconcile an UNKNOWN Save outcome with one settled, exact history query.

    It never clicks Save/Send.  A zero- or one-row result is authoritative only
    because ``PlaywrightDuplicateHistoryPage`` proves the native exact query
    settled against the complete INSO history scope; any failure to establish
    that scope is returned as UNKNOWN.
    """

    def __init__(
        self,
        *,
        operation_access: InsoOperationAccess | Callable[[], InsoOperationAccess],
        target_for_inquiry: Callable[[str], SaveReconciliationTarget | None],
        clock: Callable[[], datetime] | None = None,
        timeout_ms: int = 45_000,
    ) -> None:
        self._operation_access = operation_access
        self._target_for_inquiry = target_for_inquiry
        self._clock = clock or (lambda: datetime.now(UTC))
        self._timeout_ms = timeout_ms

    @staticmethod
    def submission_baseline(frame: object, mpn: str) -> frozenset[str]:
        """Remember the upper latest row before the draft; Owner confirms newest first."""
        history = PlaywrightDuplicateHistoryPage(frame, first_page_only=True)
        payload = history.query_exact_response(mpn)
        rows = payload.get("rows")
        if (not isinstance(rows, list) or not history.last_exact_request_matched
                or not history.last_first_page_settled):
            raise SecurityViolation("submission baseline is not authoritative")
        return frozenset(str(row["BillID"]).strip() for row in rows[:1])

    def reconcile(self, inquiry_id: str) -> ReconciliationResult:
        now = self._clock()
        target = self._target_for_inquiry(inquiry_id)
        if not _valid_reconciliation_target(target):
            return _unreadable_reconciliation(now)
        try:
            access = (
                self._operation_access()
                if callable(self._operation_access)
                else self._operation_access
            )
            with access.operation_page() as operation:
                frame = operation.shell_frame
                history = PlaywrightDuplicateHistoryPage(
                    frame, timeout_ms=self._timeout_ms,
                    first_page_only=target.submitted_at is not None,
                )
                payload = history.query_exact_response(target.mpn)
                rows = payload.get("rows")
                if (
                    not isinstance(rows, list)
                    or not history.last_exact_request_matched
                    or not (history.last_first_page_settled if target.submitted_at is not None
                            else history.last_exact_result_set_complete)
                ):
                    return _unreadable_reconciliation(now)
                if target.submitted_at is not None:
                    # Owner rule: the upper new record's model and current time,
                    # not lower procurement history and not an old matching row.
                    if target.baseline_bill_ids is None:
                        return _unreadable_reconciliation(now)
                    if not rows or str(rows[0]["BillID"]).strip() in target.baseline_bill_ids:
                        return _unreadable_reconciliation(now)
                    row = rows[0]
                    created = parse_inso_timestamp(str(row.get("PEDate", "")))
                    observed_at = self._clock()
                    # Owner 2026-10-06: tolerate up to 30 minutes of clock skew.
                    if abs(created - target.submitted_at.astimezone(UTC)) > timedelta(minutes=30):
                        return _unreadable_reconciliation(now)
                    if not mpn_matches(target.mpn, str(row.get("PartNo", "")),
                                       policy=MpnPolicy.AI_MPN_V1):
                        return _unreadable_reconciliation(now)
                    return ReconciliationResult(
                        ReconciliationOutcome.CONFIRMED_SAVED, observed_at,
                        saved_record_ref=_saved_record_ref(str(row["BillID"]).strip()),
                        candidate_count=1, authoritative=True,
                        verified_fields=("mpn", "submission_time", "new_record"),
                    )
                if len(rows) == 0:
                    return ReconciliationResult(
                        ReconciliationOutcome.CONFIRMED_NOT_SAVED,
                        now,
                        candidate_count=0,
                        authoritative=True,
                    )
                if len(rows) != 1:
                    return ReconciliationResult(
                        ReconciliationOutcome.AMBIGUOUS,
                        now,
                        reason_code=ReasonCode.RECONCILIATION_AMBIGUOUS,
                        candidate_count=len(rows),
                        authoritative=True,
                    )
                bill_id = str(rows[0].get("BillID", "")).strip()
                if not bill_id.isdecimal() or int(bill_id) <= 0:
                    return _unreadable_reconciliation(now)
                detail = self._read_detail(history, frame, bill_id)
        except Exception:  # noqa: BLE001 - any browser/identity failure is UNKNOWN
            return _unreadable_reconciliation(now)

        if detail is None:
            return _unreadable_reconciliation(now)
        if not (
            mpn_matches(target.mpn, detail.mpn, policy=MpnPolicy.AI_MPN_V1)
            and target.brand.strip() == detail.brand.strip()
            and target.quantity == detail.quantity
        ):
            return ReconciliationResult(
                ReconciliationOutcome.UNKNOWN,
                now,
                reason_code=ReasonCode.RECONCILIATION_UNREADABLE,
                candidate_count=1,
                authoritative=True,
            )
        return ReconciliationResult(
            ReconciliationOutcome.CONFIRMED_SAVED,
            now,
            saved_record_ref=_saved_record_ref(detail.bill_id),
            candidate_count=1,
            verified_fields=("mpn", "brand", "quantity"),
            authoritative=True,
        )

    def _read_detail(
        self, history: PlaywrightDuplicateHistoryPage, frame: object, bill_id: str
    ) -> _SavedDetail | None:
        history.click(DETAIL_LINK_SELECTOR_TEMPLATE.format(argument=bill_id))
        fields = {
            "bill_id": "#BillID",
            "peno": "#PENO",
            "mpn": '#_id_dg td[data-field="PartNo"]',
            "brand": '#_id_dg td[data-field="Brand"]',
            "quantity": '#_id_dg td[data-field="Qty"]',
        }
        values: dict[str, str] = {}
        for name, selector in fields.items():
            locator = frame.locator(selector)
            if locator.count() != 1 or not locator.is_visible():
                return None
            try:
                value = locator.input_value()
            except Exception:  # noqa: BLE001 - detail cells are text, inputs use value
                value = locator.inner_text()
            if not isinstance(value, str) or not value.strip():
                return None
            values[name] = value.strip()
        if values["bill_id"] != bill_id or not values["peno"]:
            return None
        if not values["quantity"].isdecimal() or int(values["quantity"]) <= 0:
            return None
        return _SavedDetail(
            values["bill_id"], values["peno"], values["mpn"], values["brand"],
            int(values["quantity"]),
        )


def _saved_record_ref(bill_id: str) -> str:
    """Keep the store's opaque rec_ contract; never persist a raw ERP identifier."""
    return "rec_" + hashlib.sha256(f"inso:BillID:{bill_id}".encode()).hexdigest()[:32]


def _valid_reconciliation_target(value: SaveReconciliationTarget | None) -> bool:
    return bool(
        value
        and isinstance(value.mpn, str)
        and value.mpn.strip()
        and isinstance(value.brand, str)
        and value.brand.strip()
        and isinstance(value.quantity, int)
        and not isinstance(value.quantity, bool)
        and value.quantity > 0
        and (value.submitted_at is None or (
            value.submitted_at.tzinfo is not None
            and isinstance(value.baseline_bill_ids, frozenset)
        ))
    )


def _unreadable_reconciliation(at: datetime) -> ReconciliationResult:
    return ReconciliationResult(
        ReconciliationOutcome.UNKNOWN,
        at,
        reason_code=ReasonCode.RECONCILIATION_UNREADABLE,
    )


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
        except Exception as exc:  # noqa: BLE001 - every control failure maps to an explicit reason code
            return self._failed(command, ReasonCode.CONTROL_NOT_FOUND, step="prepare", error=exc)

        try:
            preview = self._actions.read_ai_result()
        except Exception as exc:  # noqa: BLE001 - recognition must settle before any commit
            return self._failed(command, ReasonCode.CONTROL_NOT_FOUND, step="ai-result-read", error=exc)

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

        # Let the ERP fill its own bill row. The 采购临时询价 form is the
        # operator's surface: its 编码/型号/品牌/数量 are not ours to type into.
        # 保存数据 on the AI录单 dialog runs ``pasteImport()`` -- literally
        # ``AiImport.doImport()`` -- which is ``returnSet(buildResult())`` plus
        # ``windowsClose()``, and that close callback is
        # ``alertboxs[1].closeMtd = function(){ ai_appendRow() }``: the row is
        # handed back and ``layui`` reloads the bill grid with it. Nothing here
        # writes a cell, and the click is not a Save -- ``bill_save_auto`` stays
        # behind the closed ``ProductionWriteGate``.
        try:
            self._actions.commit_ai_entry()
        except Exception as exc:  # noqa: BLE001 - every control failure maps to an explicit reason code
            return self._failed(
                command, ReasonCode.CONTROL_NOT_FOUND, step="commit-ai-entry", error=exc
            )

        try:
            # ERP generates its code on import. Wait for the model row, then
            # validate only Owner's three business fields below.
            rendered = self._parent_fields.wait_for_model(
                preview.model, _PARENT_ROW_WAIT_SECONDS
            )
            parent_model = self._parent_fields.read_model()
            parent_brand = self._parent_fields.read_brand()
            parent_quantity = self._parent_fields.read_quantity()
        except Exception as exc:  # noqa: BLE001 - every control failure maps to an explicit reason code
            return self._failed(
                command, ReasonCode.CONTROL_NOT_FOUND, step="parent-read", error=exc
            )

        if not rendered:
            return self._failed(
                command, ReasonCode.CONTROL_NOT_FOUND, step="parent-row-missing"
            )

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
        self,
        command: PurchaseDraftCommand,
        reason: ReasonCode,
        *,
        step: str | None = None,
        error: BaseException | None = None,
    ) -> PurchaseDraftResult:
        if step is not None:
            # The run log carries no ERP detail by design, so the step label is
            # the whole diagnosis: without it a draft that never reached the
            # AI录单 panel and one that died after the ERP handed its row back
            # are the same one-line failure. Only our own labels travel; the
            # runtime filter in ``src/gui/main.py`` rebuilds the file line from
            # exactly ``step`` and the cause's class name.
            log_step(step, cause=error)
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
    save_reconciler: ReadOnlySaveReconciler

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
        save_reconciler: ReadOnlySaveReconciler,
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
        # The production seam is ``_LivePurchaseDraftWriter``, which owns the
        # leased INSO page and builds the ``CoordinatorPurchaseDraftWriter`` (with
        # its parent product fields) per call. An isinstance check against the
        # coordinator therefore rejected the real composition and would have
        # forced the packaged app to fall back to V1.1-only behaviour. The seam is
        # recognised by the prepare capability it must expose instead.
        if not callable(getattr(self.purchase_writer, "prepare", None)):
            raise TypeError(
                "V1.2 purchase writer requires parent product fields"
            )
        required = (
            self.duplicate_checker,
            self.research_facts,
            self.purchase_writer,
            self.notification_transport,
        )
        if any(adapter is None for adapter in required) or not self.recipients:
            raise ValueError("V1.2 production adapters are incomplete")
        if not isinstance(self.save_reconciler, ReadOnlySaveReconciler):
            raise TypeError("V1.2 production requires a read-only save reconciler")


@dataclass(frozen=True, slots=True)
class V12ProductionComposition:
    coordinator: V12WorkflowCoordinator
    notification_worker: V12NotificationWorker
    save_reconciler: ReadOnlySaveReconciler


def compose_v12_production(
    *,
    workflow_store,
    v12_store: V12Store,
    research,
    adapters: V12ProductionAdapters,
    stop_requested=None,
    on_result=None,
    inquiry_ids=None,
    row_wait=None,
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
        stop_requested=stop_requested,
        on_result=on_result,
        inquiry_ids=inquiry_ids,
        row_wait=row_wait,
    )
    return V12ProductionComposition(
        coordinator,
        notification_worker,
        adapters.save_reconciler,
    )
