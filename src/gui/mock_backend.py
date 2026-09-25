"""Mock backend used to demonstrate the INSO_V1.0 GUI before the production launcher exists.

The mock simulates a 15-minute research loop in compressed time so a human can
watch a full cycle in a few seconds. It never touches real browsers, Excel, or
external APIs.
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from random import choice, randint, uniform
from time import sleep
from typing import Any

from .contracts import (
    DiagnosticSnapshot,
    GuiBackend,
    HealthItem,
    HealthReport,
    LogEntry,
    Order,
    OrderStatus,
    RunSession,
    RunState,
    SourceDetail,
)
from .resources import ResourceManager, RingBufferLog, get_process_memory_mb
from .state import utc_now

logger = logging.getLogger(__name__)


_MOCK_MODELS = (
    "STM32F103C8T6",
    "ESP32-WROOM-32",
    "ATmega328P-AU",
    "TPS5430DDAR",
    "LM358DR",
    "BSS138",
    "MCP23017-E/SP",
    "ADS1115IDGSR",
)

_MOCK_BRANDS = ("TI", "ST", "Espressif", "Microchip", "ADI", "ON", "Nexperia", None)

_SOURCE_NAMES = ("INSO", "Findchips", "华强", "立创", "正能量")


class MockBackend(GuiBackend):
    """Thread-safe mock backend that emits realistic-looking orders."""

    def __init__(self, cycle_seconds: float = 12.0) -> None:
        self._cycle_seconds = max(3.0, cycle_seconds)
        self._lock = threading.Lock()

        # Runtime state
        self._run_id: str | None = None
        self._state = RunState.STOPPED
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None
        self._last_poll_at: datetime | None = None
        self._next_poll_at: datetime | None = None
        self._orders: list[Order] = []
        self._history: list[Order] = [
            Order(
                inquiry_id="mock-legacy-history",
                model="LEGACY-DEMO-001",
                brand="演示历史品牌",
                quantity=100,
                stock_label="货多",
                min_reference_price=Decimal("12.50"),
                total_price=Decimal("1250.00"),
                status=OrderStatus.UNKNOWN,
                sources=tuple(
                    SourceDetail(source, "无结果") for source in _SOURCE_NAMES
                ),
                remark="仅用于界面演示，无处理时间的历史记录",
                importance="C",
                processed_at=None,
            )
        ]
        self._stop_requested = False
        self._stop_event = threading.Event()
        self._cycle_active = False
        self._worker: threading.Thread | None = None
        self._worker_active = False
        self._memory_mb = 0.0
        self._shutdown = False

        # Logging and callbacks
        self._ring_log = RingBufferLog(capacity=1000)
        self._ring_log.setLevel(logging.INFO)
        logger.addHandler(self._ring_log)
        self._status_callbacks: list[Callable[[RunSession], Any]] = []
        self._log_callbacks: list[Callable[[LogEntry], Any]] = []

        self._resources = ResourceManager()
        self._log("Mock backend 已初始化")

    @property
    def run_id(self) -> str | None:
        with self._lock:
            return self._run_id

    def _log(self, message: str, level: str = "INFO") -> None:
        getattr(logger, level.lower(), logger.info)(message)

    def _notify_status(self) -> None:
        snapshot = self.get_status()
        with self._lock:
            callbacks = tuple(self._status_callbacks)
        for callback in callbacks:
            try:
                callback(snapshot)
            except Exception:  # noqa: BLE001,S110 - callback must not break backend
                pass

    def _notify_log(self, entry: LogEntry) -> None:
        with self._lock:
            callbacks = tuple(self._log_callbacks)
        for callback in callbacks:
            try:
                callback(entry)
            except Exception:  # noqa: BLE001,S110 - callback must not break backend
                pass

    def _spawn_worker(self) -> None:
        self._worker_active = True
        self._worker = threading.Thread(
            target=self._worker_loop, name="MockBackendWorker", daemon=True
        )
        self._worker.start()
        self._resources.add_thread(self._worker, "mock-backend-worker")

    def start(self) -> None:
        already_running = False
        with self._lock:
            if self._shutdown:
                return
            if self._state in {RunState.RUNNING, RunState.STOPPING_AFTER_CYCLE} or (
                self._worker is not None and self._worker.is_alive()
            ):
                already_running = True
            else:
                self._run_id = f"run_{uuid.uuid4().hex[:8]}"
                self._state = RunState.RUNNING
                self._started_at = utc_now()
                self._stopped_at = None
                self._orders = []
                self._stop_requested = False
                self._stop_event.clear()
                self._cycle_active = False
                self._memory_mb = get_process_memory_mb()
                self._next_poll_at = None
                run_id = self._run_id

        if already_running:
            self._log("已经在运行中，忽略重复启动")
            return
        self._log(f"启动新运行会话: {run_id}")

        self._notify_status()
        self._spawn_worker()

    def request_stop_after_cycle(self) -> None:
        with self._lock:
            if self._state == RunState.STOPPED:
                return
            if self._state == RunState.STOPPING_AFTER_CYCLE:
                return
            self._stop_requested = True
            self._state = RunState.STOPPING_AFTER_CYCLE

        self._stop_event.set()
        self._log("已请求本轮结束后停止")

        self._notify_status()

    def _worker_loop(self) -> None:
        self._log("后台 worker 启动")
        while True:
            stop_before_cycle = False
            with self._lock:
                active = self._state in {
                    RunState.RUNNING,
                    RunState.STOPPING_AFTER_CYCLE,
                }
                if active and self._stop_requested and not self._cycle_active:
                    self._state = RunState.STOPPED
                    self._stopped_at = utc_now()
                    self._next_poll_at = None
                    self._worker_active = False
                    stop_before_cycle = True
                elif active:
                    self._cycle_active = True

            if not active:
                break
            if stop_before_cycle:
                self._log("等待期间收到停止请求，未启动下一轮")
                self._notify_status()
                break

            self._run_cycle()

            with self._lock:
                self._cycle_active = False
                stop_after_cycle = self._stop_requested
                if stop_after_cycle:
                    self._state = RunState.STOPPED
                    self._stopped_at = utc_now()
                    self._next_poll_at = None
                    self._worker_active = False
                else:
                    self._next_poll_at = utc_now() + timedelta(
                        seconds=self._cycle_seconds
                    )

            self._notify_status()

            if stop_after_cycle:
                self._log("本轮完成，安全停止")
                break

            # A stop request wakes an idle worker immediately. The next loop
            # observes it before marking a new cycle active.
            self._stop_event.wait(timeout=self._cycle_seconds)

        self._log("后台 worker 退出")

    def _run_cycle(self) -> None:
        now = utc_now()
        self._last_poll_at = now
        self._log("开始轮询 Google Sheets")
        sleep(0.3)
        self._log("发现 1 条未发订单")
        sleep(0.3)
        self._log("开始市场调研")
        sleep(0.5)

        order = self._generate_order()
        with self._lock:
            self._orders.append(order)
            self._history.append(order)
            self._memory_mb = get_process_memory_mb()

        self._log(f"订单 {order.inquiry_id} 处理完成: {order.status.value}")

    def _generate_order(self) -> Order:
        model = choice(_MOCK_MODELS)
        brand = choice(_MOCK_BRANDS)
        quantity = randint(100, 5000)
        source_details: list[SourceDetail] = []

        for source in _SOURCE_NAMES:
            if uniform(0, 1) < 0.15:
                source_details.append(
                    SourceDetail(source=source, display_value="无结果")
                )
                continue
            display_amount = Decimal(randint(10_000, 200_000)) / Decimal(100)
            source_details.append(
                SourceDetail(source=source, display_value=f"{display_amount:.2f}")
            )

        min_price = Decimal(randint(50, 5_000)) / Decimal(100)
        total = (min_price * quantity).quantize(Decimal("0.01"))
        status = choice(
            (OrderStatus.COMPLETED, OrderStatus.PARTIAL, OrderStatus.ERROR)
        )
        remark = "模拟结果，供界面演示" if status == OrderStatus.ERROR else ""

        with self._lock:
            run_id = self._run_id or ""

        return Order(
            inquiry_id=f"inq_{uuid.uuid4().hex[:8]}",
            model=model,
            brand=brand,
            quantity=quantity,
            stock_label=choice(("货多", "货少", "待验证")),
            min_reference_price=min_price,
            total_price=total,
            status=status,
            sources=tuple(source_details),
            remark=remark,
            run_id=run_id,
            importance=choice(("A", "B", "C", "D")),
            processed_at=datetime.now(timezone.utc),
        )

    def get_status(self) -> RunSession:
        with self._lock:
            orders = self._orders
            completed = sum(1 for o in orders if o.status == OrderStatus.COMPLETED)
            partial = sum(1 for o in orders if o.status == OrderStatus.PARTIAL)
            errors = sum(1 for o in orders if o.status == OrderStatus.ERROR)
            pending = len(orders) - completed - partial - errors

            return RunSession(
                run_id=self._run_id,
                state=self._state,
                started_at=self._started_at,
                stopped_at=self._stopped_at,
                orders_found=len(orders),
                completed=completed,
                in_progress=1
                if self._worker_active and self._state == RunState.RUNNING
                else 0,
                pending=pending,
                next_poll_at=self._next_poll_at,
            )

    def get_current_run_results(self) -> tuple[Order, ...]:
        with self._lock:
            return tuple(self._orders)

    def get_result_history(self) -> tuple[Order, ...]:
        with self._lock:
            return tuple(sorted(
                self._history,
                key=lambda order: order.processed_at or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            ))

    def get_health(self) -> HealthReport:
        with self._lock:
            running = self._state == RunState.RUNNING

        active_status = "正在运行" if running else "正常"
        items = (
            HealthItem(component="Google Sheets", status=active_status),
            HealthItem(component="Browser/CDP", status=active_status),
            HealthItem(component="Credential", status="正常"),
            HealthItem(component="Research", status=active_status),
        )
        return HealthReport(items=items, overall="正常")

    def get_logs(self) -> tuple[LogEntry, ...]:
        return self._ring_log.snapshot()

    def get_diagnostics(self) -> DiagnosticSnapshot:
        with self._lock:
            return DiagnosticSnapshot(
                run_id=self._run_id,
                uptime_seconds=(
                    (utc_now() - self._started_at).total_seconds()
                    if self._started_at
                    else 0.0
                ),
                gui_memory_mb=self._memory_mb or get_process_memory_mb(),
                worker_state="running" if self._worker_active else "stopped",
                last_poll_at=self._last_poll_at,
            )

    def open_excel(self) -> None:
        path = os.path.abspath("调研价格.xlsx")
        self._log(f"打开 Excel: {path}")
        try:
            if os.path.exists(path):
                subprocess.run(["start", "", path], shell=True, check=False)
            else:
                self._log(f"Excel 文件不存在: {path}", level="WARNING")
        except Exception as exc:  # noqa: BLE001 - OS open failures are non-fatal
            self._log(f"打开 Excel 失败: {exc}", level="ERROR")

    def open_results_dir(self) -> None:
        path = os.path.abspath("data/results")
        self._log(f"打开结果目录: {path}")
        try:
            os.makedirs(path, exist_ok=True)
            subprocess.run(["start", "", path], shell=True, check=False)
        except Exception as exc:  # noqa: BLE001 - OS open failures are non-fatal
            self._log(f"打开结果目录失败: {exc}", level="ERROR")

    def on_status_change(self, callback: Callable[[RunSession], Any] | None) -> None:
        with self._lock:
            if callback is None:
                self._status_callbacks.clear()
            elif callback not in self._status_callbacks:
                self._status_callbacks.append(callback)

    def on_log(self, callback: Callable[[LogEntry], Any] | None) -> None:
        with self._lock:
            if callback is None:
                self._log_callbacks.clear()
                self._ring_log.remove_listener(self._notify_log)
            elif callback not in self._log_callbacks:
                self._log_callbacks.append(callback)
                self._ring_log.add_listener(self._notify_log)

    def shutdown(self) -> None:
        with self._lock:
            if self._shutdown:
                return
            self._shutdown = True
            self._stop_requested = True
            if self._state != RunState.STOPPED:
                self._state = RunState.STOPPING_AFTER_CYCLE

        self._stop_event.set()
        self._notify_status()

        if self._worker is not None and self._worker.is_alive():
            self._worker.join()

        with self._lock:
            self._state = RunState.STOPPED
            self._stopped_at = utc_now()
            self._worker_active = False
            self._next_poll_at = None

        self._resources.close_all()
        self.on_status_change(None)
        self.on_log(None)
        self._notify_status()
        self._log("Mock backend 已关闭")

        logger.removeHandler(self._ring_log)
        self._status_callbacks.clear()
        self._ring_log.clear()
