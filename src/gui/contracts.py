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
from enum import Enum
from typing import Any


class RunState(str, Enum):
    """Coarse-grained dashboard states shown to the operator."""

    STOPPED = "已停止"
    RUNNING = "运行中"
    STOPPING_AFTER_CYCLE = "本轮结束后停止"
    MANUAL_REVIEW = "需要人工处理"


class OrderStatus(str, Enum):
    """Per-order outcome as understood by the GUI."""

    COMPLETED = "成功"
    PARTIAL = "部分成功"
    PENDING = "待处理"
    ERROR = "异常"
    UNKNOWN = "--"


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
