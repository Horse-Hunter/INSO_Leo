"""Public backend contract consumed by the INSO_V1.0 GUI.

The GUI imports only this module (and state/resources utilities). It must never
import research, sheets, workflow, inso, or quotation internals directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum, StrEnum
from typing import Any


class RunState(str, Enum):
    """Coarse-grained dashboard states shown to the operator."""

    STOPPED = "已停止"
    RUNNING = "运行中"
    STOPPING_AFTER_CYCLE = "本轮结束后停止"
    MANUAL_REVIEW = "需要人工处理"
    MODULE_PAUSED = "采购模块暂停"
    QUOTATION_RUNNING = "V1.2暂停 / V1.3正常"
    GLOBAL_STOP = "全局基础设施故障"


class OrderStatus(str, Enum):
    """Per-order outcome as understood by the GUI."""

    COMPLETED = "成功"
    PARTIAL = "部分成功"
    PENDING = "待处理"
    ERROR = "异常"
    UNKNOWN = "--"


class V12BusinessLabel(StrEnum):
    QUOTATION_WAITING = "等待采购报价"
    QUOTATION_COMPLETED = "采购已报价"
    QUOTATION_FAILED = "报价处理异常，需人工处理"
    QUOTATION_STATUS_PENDING = "报价已处理，表格状态待人工更新"
    INTERRUPTED_UNSENT = "处理中断（未发送）"
    INTERRUPTED_POSSIBLY_SENT = "处理中断（可能已发送，请先核对）"
    HUMAN_COMPLETED = "人工处理完成"
    SOURCE_CHANGED = "源订单已变更"
    SUBMIT_UNCONFIRMED = "已发采购（待确认）"
    STATUS_WRITE_PENDING = "采购已处理，表格状态待人工更新"
    RESEARCH_EXCEPTION = "调研异常"
    PROCESSING = "处理中"
    DUPLICATE_ORDER = "重复订单"
    PURCHASE_SENT = "已发采购单"
    PURCHASE_EXCEPTION = "采购录单异常"
    SKIPPED_INVALID_INPUT = "已跳过（数据异常）"


class V12AlertCode(StrEnum):
    DUPLICATE_ORDER = "DUPLICATE_ORDER"
    NOTIFICATION_FAILED = "NOTIFICATION_FAILED"
    PURCHASE_EXCEPTION = "PURCHASE_EXCEPTION"
    DATA_QUALITY = "DATA_QUALITY"
    SECURITY_EVENT = "SECURITY_EVENT"


class V12ReasonCode(StrEnum):
    INQUIRY_INPUT_INVALID = "INQUIRY_INPUT_INVALID"
    UNKNOWN_EXTERNAL_FAILURE = "UNKNOWN_EXTERNAL_FAILURE"
    DUPLICATE_ORDER_DETECTED = "DUPLICATE_ORDER_DETECTED"
    DUPLICATE_LOOKUP_UNAVAILABLE = "DUPLICATE_LOOKUP_UNAVAILABLE"
    DUPLICATE_LOOKUP_AMBIGUOUS = "DUPLICATE_LOOKUP_AMBIGUOUS"
    DUPLICATE_HISTORY_INVALID = "DUPLICATE_HISTORY_INVALID"
    SESSION_IDENTITY_UNVERIFIED = "SESSION_IDENTITY_UNVERIFIED"
    SESSION_STALE = "SESSION_STALE"
    CONTROL_NOT_FOUND = "CONTROL_NOT_FOUND"
    CONTROL_AMBIGUOUS = "CONTROL_AMBIGUOUS"
    CONTROL_DENIED = "CONTROL_DENIED"
    ACTION_NOT_ALLOWED = "ACTION_NOT_ALLOWED"
    PAGE_NOT_FOUND = "PAGE_NOT_FOUND"
    WRITE_GATE_DISABLED = "WRITE_GATE_DISABLED"
    AI_RECOGNITION_MISMATCH = "AI_RECOGNITION_MISMATCH"
    SAVE_OUTCOME_UNKNOWN = "SAVE_OUTCOME_UNKNOWN"
    RECONCILIATION_AMBIGUOUS = "RECONCILIATION_AMBIGUOUS"
    RECONCILIATION_UNREADABLE = "RECONCILIATION_UNREADABLE"
    NOTIFICATION_TRANSIENT = "NOTIFICATION_TRANSIENT"
    NOTIFICATION_PERMANENT = "NOTIFICATION_PERMANENT"
    NOTIFICATION_SENT = "NOTIFICATION_SENT"
    NOTIFICATION_UNKNOWN = "NOTIFICATION_UNKNOWN"
    CUSTOMER_NAME_MISSING = "CUSTOMER_NAME_MISSING"
    INQUIRY_QUANTITY_INVALID = "INQUIRY_QUANTITY_INVALID"
    EVIDENCE_PATH_UNSAFE = "EVIDENCE_PATH_UNSAFE"
    SQLITE_BACKUP_INVALID = "SQLITE_BACKUP_INVALID"
    SQLITE_BACKUP_COLLISION = "SQLITE_BACKUP_COLLISION"
    SQLITE_MIGRATION_INVALID = "SQLITE_MIGRATION_INVALID"


class V12EventCode(StrEnum):
    DATA_QUALITY_INVALID_INPUT = "DATA_QUALITY_INVALID_INPUT"
    SAVE_CLICK_COMPLETED = "SAVE_CLICK_COMPLETED"
    DUPLICATE_CHECK_STARTED = "DUPLICATE_CHECK_STARTED"
    DUPLICATE_CHECK_CONFIRMED = "DUPLICATE_CHECK_CONFIRMED"
    DUPLICATE_CHECK_FAILED = "DUPLICATE_CHECK_FAILED"
    RESEARCH_STARTED = "RESEARCH_STARTED"
    RESEARCH_RETRY_SCHEDULED = "RESEARCH_RETRY_SCHEDULED"
    RESEARCH_FAILED = "RESEARCH_FAILED"
    DUPLICATE_ORDER_DETECTED = "DUPLICATE_ORDER_DETECTED"
    IMPORTANT_ORDER_DECIDED = "IMPORTANT_ORDER_DECIDED"
    NOTIFICATION_COMMAND_CREATED = "NOTIFICATION_COMMAND_CREATED"
    NOTIFICATION_DELIVERY_FAILED = "NOTIFICATION_DELIVERY_FAILED"
    NOTIFICATION_RETRY_SCHEDULED = "NOTIFICATION_RETRY_SCHEDULED"
    NOTIFICATION_DELIVERY_SUCCEEDED = "NOTIFICATION_DELIVERY_SUCCEEDED"
    ALERT_RECOVERED = "ALERT_RECOVERED"
    PURCHASE_DRAFT_STARTED = "PURCHASE_DRAFT_STARTED"
    AI_RECOGNITION_READY = "AI_RECOGNITION_READY"
    AI_RECOGNITION_MISMATCH = "AI_RECOGNITION_MISMATCH"
    SAVE_DISPATCH_ARMED = "SAVE_DISPATCH_ARMED"
    SAVE_OUTCOME_UNKNOWN = "SAVE_OUTCOME_UNKNOWN"
    RECONCILIATION_STARTED = "RECONCILIATION_STARTED"
    RECONCILIATION_CONFIRMED_SAVED = "RECONCILIATION_CONFIRMED_SAVED"
    RECONCILIATION_CONFIRMED_NOT_SAVED = "RECONCILIATION_CONFIRMED_NOT_SAVED"
    RECONCILIATION_AMBIGUOUS = "RECONCILIATION_AMBIGUOUS"
    PURCHASE_DATA_SAVED = "PURCHASE_DATA_SAVED"
    SECURITY_CHECK_FAILED = "SECURITY_CHECK_FAILED"
    DATA_QUALITY_MISSING_CUSTOMER = "DATA_QUALITY_MISSING_CUSTOMER"
    DATA_QUALITY_INVALID_QUANTITY = "DATA_QUALITY_INVALID_QUANTITY"
    HUMAN_RESOLUTION_RECORDED = "HUMAN_RESOLUTION_RECORDED"


class SiteLoginOutcome(StrEnum):
    """What one site's turn in the login sweep achieved.

    These are the only verdicts the dashboard reports. They are deliberately
    coarser than the internal reason codes: the operator's decision is "does
    this site need me?" and nothing finer changes what they do next.
    """

    ALREADY_SIGNED_IN = "已在登录状态"
    SIGNED_IN = "登录成功"
    NEEDS_HUMAN = "需要人工登录"
    REJECTED = "账号或密码被拒绝"
    NO_CREDENTIAL = "缺少登录凭据"
    UNAVAILABLE = "登录失败"


@dataclass(frozen=True, slots=True)
class SiteLoginResult:
    """One site's verdict, safe to render: a label and a closed outcome."""

    site: str
    outcome: SiteLoginOutcome
    detail: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, SiteLoginOutcome):
            raise TypeError("GUI login outcomes must be allowlisted enums")


@dataclass(frozen=True, slots=True)
class SiteLoginReport:
    """The finished sequential login sweep, in the order the sites were tried."""

    results: tuple[SiteLoginResult, ...]
    started_at: datetime
    finished_at: datetime

    @property
    def all_signed_in(self) -> bool:
        """True only when every site is genuinely usable without a human."""

        return bool(self.results) and all(
            result.outcome
            in {SiteLoginOutcome.ALREADY_SIGNED_IN, SiteLoginOutcome.SIGNED_IN}
            for result in self.results
        )

    @property
    def needing_attention(self) -> tuple[SiteLoginResult, ...]:
        """The sites the operator has to look at, in sweep order."""

        return tuple(result for result in self.results if not _is_signed_in(result))


def _is_signed_in(result: SiteLoginResult) -> bool:
    return result.outcome in {
        SiteLoginOutcome.ALREADY_SIGNED_IN,
        SiteLoginOutcome.SIGNED_IN,
    }


@dataclass(frozen=True, slots=True)
class OrderAlertDTO:
    """Only closed codes and safe timestamps cross into the GUI."""

    alert_id: str
    alert_type: V12AlertCode
    reason_code: V12ReasonCode
    raised_at: datetime
    active: bool

    def __post_init__(self) -> None:
        if not isinstance(self.alert_type, V12AlertCode) or not isinstance(
            self.reason_code, V12ReasonCode
        ):
            raise TypeError("GUI alert codes must be allowlisted enums")


@dataclass(frozen=True, slots=True)
class WorkflowEventDTO:
    """Sanitized event-history row for an order detail view."""

    event_id: str
    event_type: V12EventCode
    reason_code: V12ReasonCode | None
    occurred_at: datetime
    recovered: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, V12EventCode):
            raise TypeError("GUI event type must be an allowlisted enum")
        if self.reason_code is not None and not isinstance(
            self.reason_code, V12ReasonCode
        ):
            raise TypeError("GUI reason code must be an allowlisted enum")


@dataclass(frozen=True, slots=True)
class V12OrderStateDTO:
    """Additive V1.2 state seam; V1 Order/history contracts remain unchanged."""

    inquiry_id: str
    business_label: V12BusinessLabel
    latest_active_alert: OrderAlertDTO | None
    active_alerts: tuple[OrderAlertDTO, ...] = ()
    event_history: tuple[WorkflowEventDTO, ...] = ()
    waiting_label: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.business_label, V12BusinessLabel):
            raise TypeError("GUI business label must be an allowlisted enum")


@dataclass(frozen=True, slots=True)
class SourceDetail:
    """Display-only value reported for one source; GUI applies no business rules."""

    source: str
    display_value: str
    remark: str | None = None
    url: str | None = None


@dataclass(frozen=True, slots=True)
class Order:
    """A single order displayed in the current-run results table."""

    inquiry_id: str
    model: str
    brand: str | None
    quantity: int
    stock_label: str
    min_reference_price: Decimal | None
    total_price: Decimal | None
    status: OrderStatus
    sources: tuple[SourceDetail, ...] = ()
    remark: str = ""
    run_id: str = ""
    importance: str | None = None
    processed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RunSession:
    """Runtime snapshot shown in the dashboard."""

    run_id: str | None
    state: RunState
    started_at: datetime | None
    stopped_at: datetime | None
    orders_found: int = 0
    completed: int = 0
    in_progress: int = 0
    pending: int = 0
    next_poll_at: datetime | None = None
    row_cooldown_until: datetime | None = None
    new_orders: int | None = None
    awaiting_quotation: int | None = None
    overdue_quotation: int | None = None


@dataclass(frozen=True, slots=True)
class HealthItem:
    """Health of one infrastructure component."""

    component: str
    status: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class HealthReport:
    """Aggregate health snapshot for the bottom bar."""

    items: tuple[HealthItem, ...]
    overall: str


@dataclass(frozen=True, slots=True)
class DiagnosticSnapshot:
    """Reserved diagnostic data for future troubleshooting."""

    run_id: str | None
    uptime_seconds: float
    gui_memory_mb: float
    worker_state: str
    last_poll_at: datetime | None


@dataclass(frozen=True, slots=True)
class LogEntry:
    """One line in the bounded backend log."""

    timestamp: datetime
    level: str
    message: str


@dataclass(frozen=True, slots=True)
class ManualOrderResult:
    request_id: str
    inquiry_id: str
    action: str
    success: bool
    message: str


class GuiBackend(ABC):
    """Abstract production/mock backend that the INSO_V1.0 GUI drives.

    Implementations are responsible for their own threading model; the GUI
    calls these methods from the UI thread and expects non-blocking behaviour.
    """

    @property
    @abstractmethod
    def run_id(self) -> str | None:
        """Current run identifier; None when stopped."""

    @abstractmethod
    def start(self) -> None:
        """Begin a new run session. Idempotent while already running."""

    @abstractmethod
    def request_stop_after_cycle(self) -> None:
        """Ask the backend to stop after the current cycle completes."""

    @abstractmethod
    def get_status(self) -> RunSession:
        """Return the latest dashboard status snapshot."""

    @abstractmethod
    def get_current_run_results(self) -> tuple[Order, ...]:
        """Return orders processed since the current GUI run started."""

    @abstractmethod
    def get_result_history(self) -> tuple[Order, ...]:
        """Return Research-owned persisted results, newest processed first."""

    def get_v12_order_state(self, inquiry_id: str) -> V12OrderStateDTO | None:
        """Return optional V1.2 state without changing the V1.1 dashboard contract."""

        return None

    def can_order_action(self, inquiry_id: str, action: str) -> bool:
        """Optional idle-only single-order capability."""
        return False

    def request_order_action(self, inquiry_id: str, action: str, *, field=None, value=None) -> str | None:
        """Queue one serial action; return a safe rejection message, or None."""
        return "当前后端不支持此操作。"

    def get_manual_order_result(self) -> ManualOrderResult | None:
        return None

    def start_login_all_sites(self) -> None:
        """Begin the sequential "sign in to every site" sweep.

        Optional capability: a backend that cannot do it stays silent, and the
        dashboard simply never reports a sweep. It must be non-blocking and
        idempotent while a sweep is already running.
        """

    def login_all_running(self) -> bool:
        """Whether a login sweep is in flight right now."""

        return False

    def get_login_all_report(self) -> SiteLoginReport | None:
        """Return the most recent finished sweep, or ``None`` if never run."""

        return None

    def on_login_all(
        self, callback: Callable[[SiteLoginReport], Any] | None
    ) -> None:
        """Register a callback invoked once per finished sweep."""

    @abstractmethod
    def get_health(self) -> HealthReport:
        """Return component health."""

    @abstractmethod
    def get_logs(self) -> tuple[LogEntry, ...]:
        """Return recent backend log entries."""

    @abstractmethod
    def get_diagnostics(self) -> DiagnosticSnapshot:
        """Return reserved diagnostic metrics."""

    @abstractmethod
    def open_excel(self) -> None:
        """Open the research Excel file with the default application."""

    @abstractmethod
    def open_results_dir(self) -> None:
        """Open the directory that holds research results."""

    @abstractmethod
    def on_status_change(self, callback: Callable[[RunSession], Any] | None) -> None:
        """Register a callback invoked whenever the status changes."""

    @abstractmethod
    def on_log(self, callback: Callable[[LogEntry], Any] | None) -> None:
        """Register a callback invoked for each new log entry."""

    @abstractmethod
    def shutdown(self) -> None:
        """Release all workers, timers, and listeners; no-op after first call."""
