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
from datetime import datetime, timedelta
from random import choice, randint, uniform
from time import monotonic, sleep
from typing import Any

from .contracts import (
    DiagnosticSnapshot,
    GuiBackend,
    HealthItem,
    HealthReport,
    LogEntry,
    Order,
    OrderStatus,
    PriceEvidence,
    RunSession,
    RunState,
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

_SOURCE_STATUSES = {
    "INSO": "正常",
    "Findchips": "正常",
    "华强": "正常",
    "立创": "正常",
    "正能量": "需要登录",
}


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
        self._stop_requested = False
        self._worker: threading.Thread | None = None
        self._worker_active = False
        self._memory_mb = 0.0

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
        for callback in self._status_callbacks:
            try:
                callback(snapshot)
            except Exception:  # noqa: BLE001,S110 - callback must not break backend
                pass

    def _notify_log(self, entry: LogEntry) -> None:
        for callback in self._log_callbacks:
            try:
                callback(entry)
            except Exception:  # noqa: BLE001,S110 - callback must not break backend
                pass

    def _spawn_worker(self) -> None:
        self._worker_active = True
        self._worker = threading.Thread(target=self._worker_loop, name="MockBackendWorker", daemon=True)
        self._worker.start()
        self._resources.add_thread(self._worker, "mock-backend-worker")

    def start(self) -> None:
        with self._lock:
            if self._state in {RunState.RUNNING, RunState.STOPPING_AFTER_CYCLE}:
                self._log("已经在运行中，忽略重复启动")
                return
            self._run_id = f"run_{uuid.uuid4().hex[:8]}"
            self._state = RunState.RUNNING
            self._started_at = utc_now()
            self._stopped_at = None
            self._orders = []
            self._stop_requested = False
            self._memory_mb = get_process_memory_mb()
            self._next_poll_at = utc_now() + timedelta(seconds=self._cycle_seconds)
            self._log(f"启动新运行会话: {self._run_id}")

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
            self._log("已请求本轮结束后停止")

        self._notify_status()

    def _worker_loop(self) -> None:
        self._log("后台 worker 启动")
        while True:
            with self._lock:
                should_stop = self._stop_requested
                active = self._state in {RunState.RUNNING, RunState.STOPPING_AFTER_CYCLE}

            if not active:
                break

            if should_stop:
                with self._lock:
                    self._state = RunState.STOPPED
                    self._stopped_at = utc_now()
                    self._next_poll_at = None
                    self._worker_active = False
                self._log("本轮完成，安全停止")
                self._notify_status()
                break

            self._run_cycle()

            with self._lock:
                if self._stop_requested:
                    self._state = RunState.STOPPED
                    self._stopped_at = utc_now()
                    self._next_poll_at = None
                    self._worker_active = False
                    self._log("本轮完成，安全停止")
                else:
                    self._next_poll_at = utc_now() + timedelta(seconds=self._cycle_seconds)

            self._notify_status()

            if self._stop_requested:
                break

            # Sleep in small increments so shutdown is responsive.
            deadline = monotonic() + self._cycle_seconds
            while monotonic() < deadline:
                sleep(0.2)
                with self._lock:
                    if self._stop_requested:
                        break

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
            self._memory_mb = get_process_memory_mb()

        self._log(f"订单 {order.inquiry_id} 处理完成: {order.status.value}")

    def _generate_order(self) -> Order:
        model = choice(_MOCK_MODELS)
        brand = choice(_MOCK_BRANDS)
        quantity = randint(100, 5000)
        evidence_list: list[PriceEvidence] = []
        prices: list[float] = []

        for source in _SOURCE_NAMES:
            if uniform(0, 1) < 0.15:
                # Randomly mark one source as unavailable for variety.
                evidence_list.append(
                    PriceEvidence(source=source, unit_price=None, stock=None, remark="源不可用")
                )
                continue
            unit_price = round(uniform(0.5, 50.0), 2)
            stock = randint(0, 10000)
            evidence_list.append(
                PriceEvidence(source=source, unit_price=unit_price, stock=stock)
            )
            if stock > 0:
                prices.append(unit_price)

        if not prices:
            status = OrderStatus.MANUAL_REVIEW
            min_price = None
            total = None
            remark = "全部货源无库存，需人工处理"
        elif len(prices) < 3:
            status = OrderStatus.PARTIAL
            min_price = min(prices)
            total = round(min_price * quantity, 2)
            remark = "仅部分来源有报价"
        else:
            status = OrderStatus.COMPLETED
            min_price = min(prices)
            total = round(min_price * quantity, 2)
            remark = ""

        with self._lock:
            run_id = self._run_id or ""

        return Order(
            inquiry_id=f"inq_{uuid.uuid4().hex[:8]}",
            model=model,
            brand=brand,
            quantity=quantity,
            stock=sum(e.stock or 0 for e in evidence_list),
            min_reference_price=min_price,
            total_price=total,
            status=status,
            evidence=tuple(evidence_list),
            remark=remark,
            run_id=run_id,
        )

    def get_status(self) -> RunSession:
        with self._lock:
            orders = self._orders
            completed = sum(1 for o in orders if o.status == OrderStatus.COMPLETED)
            partial = sum(1 for o in orders if o.status == OrderStatus.PARTIAL)
            manual = sum(1 for o in orders if o.status == OrderStatus.MANUAL_REVIEW)
            pending = len(orders) - completed - partial - manual

            return RunSession(
                run_id=self._run_id,
                state=self._state,
                started_at=self._started_at,
                stopped_at=self._stopped_at,
                orders_found=len(orders),
                completed=completed,
                in_progress=1 if self._worker_active and self._state == RunState.RUNNING else 0,
                pending=pending,
                next_poll_at=self._next_poll_at,
            )

    def get_current_run_results(self) -> tuple[Order, ...]:
        with self._lock:
            return tuple(self._orders)

    def get_health(self) -> HealthReport:
        with self._lock:
            running = self._state == RunState.RUNNING

        items = []
        overall = "正常"
        for component, base_status in _SOURCE_STATUSES.items():
            if running and base_status == "正常":
                status = "正在运行"
            elif base_status == "需要登录":
                status = "需要登录"
                if overall == "正常":
                    overall = "需要登录"
            else:
                status = base_status
            items.append(HealthItem(component=component, status=status))

        # Map GUI-level health names requested by the product spec.
        mapped_items = [
            HealthItem(component="Google Sheets", status=items[0].status),
            HealthItem(component="Browser/CDP", status=items[1].status),
            HealthItem(component="Credential", status="正常"),
            HealthItem(component="Research", status=items[4].status),
        ]
        if any(item.status == "异常" for item in mapped_items):
            overall = "异常"
        elif any(item.status == "需要登录" for item in mapped_items):
            overall = "需要登录"
        else:
            overall = "正常"

        return HealthReport(items=tuple(mapped_items), overall=overall)

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
            if self._state == RunState.STOPPED:
                self._resources.close_all()
                return
            self._stop_requested = True
            self._state = RunState.STOPPING_AFTER_CYCLE

        self._notify_status()

        # Join worker with a short timeout; if it is stuck, the resource manager
        # will try again during close_all.
        if self._worker is not None and self._worker.is_alive():
            self._worker.join(timeout=3.0)

        with self._lock:
            self._state = RunState.STOPPED
            self._stopped_at = utc_now()
            self._worker_active = False
            self._next_poll_at = None

        self._resources.close_all()
        self._notify_status()
        self._log("Mock backend 已关闭")

        logger.removeHandler(self._ring_log)
        self._status_callbacks.clear()
        self._ring_log.clear()
