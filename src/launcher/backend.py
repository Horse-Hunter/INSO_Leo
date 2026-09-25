"""Production GUI adapter over the canonical Workflow and Research runtimes."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import uuid
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.core.app_paths import app_root, resolve_app_path, runtime_config_path
from src.gui.contracts import (
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
from src.gui.state import utc_now
from src.research import ResearchInput, ResearchResult
from src.research.excel_output import ResearchExcelOutput
from src.research.runtime import (
    ResearchRuntimeConfigError,
    assess_readiness,
    build_production_research_service,
    load_runtime_config,
    probe_loopback_endpoint,
)
from src.sheets import WorksheetIdentity
from src.sheets.google_oauth import build_read_only_google_sheets_service
from src.sheets.google_reader import GoogleSheetsRowReader
from src.workflow import (
    WorkflowPoller,
    WorkflowRuntime,
    WorkflowStateStore,
    WorkflowStatus,
    WorkflowWorker,
)

from .browser_bootstrap import BrowserHandle, acquire_cdp_browser

log = logging.getLogger(__name__)


class _Observer:
    """Track actual Research attempts and surface interactive challenges."""

    _HUMAN_ACTION_MARKERS = (
        "需要人工验证",
        "captcha",
        "otp",
        "设备验证",
        "登录不可用",
    )

    def __init__(self, service, seen, manual_review):
        self.service = service
        self.seen = seen
        self.manual_review = manual_review

    def execute(self, item: ResearchInput) -> ResearchResult:
        self.seen(item.inquiry_id)
        result = self.service.execute(item)
        remarks = (result.remarks or "").casefold()
        if any(marker in remarks for marker in self._HUMAN_ACTION_MARKERS):
            self.manual_review(item.inquiry_id)
        return result


class ProductionBackend(GuiBackend):
    """Own one GUI run session and stop it only at safe Workflow boundaries."""

    def __init__(
        self, config_path=None, production_config_path=None, *, cdp_probe=None,
        root=None, browser_acquirer=acquire_cdp_browser,
    ):
        self.root = Path(root) if root is not None else app_root()
        self.config_path = Path(config_path) if config_path is not None else runtime_config_path("research.json", root=self.root)
        self.production_path = Path(production_config_path) if production_config_path is not None else runtime_config_path("production.json", root=self.root)
        self.cdp_probe = cdp_probe
        self._browser_acquirer = browser_acquirer
        self._browser_handle: BrowserHandle | None = None
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._drain_due_on_stop = threading.Event()
        self._poll_gate = threading.Lock()
        self._poll_idle = threading.Event()
        self._poll_idle.set()
        self._thread = None
        self._closed = False
        self._run_id = None
        self._state = RunState.STOPPED
        self._started = self._stopped = self._last_poll = None
        self._next_poll_at = None
        self._inquiries = []
        self._results = ()
        self._history = ()
        self._history_fingerprint = None
        self._store = None
        self._excel = None
        self._manual_inquiries = set()
        try:
            configured_excel = load_runtime_config(self.config_path).excel_output_path
            self._excel = (
                configured_excel
                if configured_excel.is_absolute()
                else resolve_app_path(configured_excel, root=self.root)
            )
        except ResearchRuntimeConfigError as exc:
            log.debug("Research output path unavailable (%s)", type(exc).__name__)
        self._refresh_history(force=True)
        self._logs = []
        self._status_callbacks = []
        self._log_callbacks = []
        self._health = HealthReport(
            tuple(HealthItem(n, "未知", "尚未检查") for n in self._components()),
            "需要人工处理",
        )

    @staticmethod
    def _components():
        return ("Google Sheets", "Browser/CDP", "Credential", "Research")

    @property
    def run_id(self):
        with self._lock:
            return self._run_id

    def start(self):
        with self._lock:
            if (
                self._closed
                or self._state in (RunState.RUNNING, RunState.STOPPING_AFTER_CYCLE)
                or (self._thread is not None and self._thread.is_alive())
            ):
                return
            self._run_id = "run_" + str(uuid.uuid4())
            self._started = utc_now()
            self._stopped = None
            self._inquiries = []
            self._manual_inquiries.clear()
            self._results = ()
            self._last_poll = None
            self._next_poll_at = None
            self._stop.clear()
            self._drain_due_on_stop.clear()
            self._poll_idle.set()
            self._state = RunState.RUNNING
            self._thread = threading.Thread(
                target=self._run, name="production-launcher", daemon=False
            )
            self._thread.start()
            self._notify()

    def request_stop_after_cycle(self):
        with self._lock:
            if self._state is RunState.RUNNING:
                self._state = RunState.STOPPING_AFTER_CYCLE
                self._next_poll_at = None
                with self._poll_gate:
                    self._drain_due_on_stop.set()
                    self._stop.set()
                self._notify()

    def _run(self):
        try:
            cfg = json.loads(self.production_path.read_text(encoding="utf-8"))
            if (
                not cfg.get("spreadsheet_id")
                or not cfg.get("worksheet_titles")
                or not cfg.get("client_secret_file")
            ):
                raise ValueError(
                    "production.json requires spreadsheet_id, worksheet_titles and client_secret_file"
                )
            rc = load_runtime_config(self.config_path)
            if not rc.excel_output_path.is_absolute():
                rc = replace(rc, excel_output_path=resolve_app_path(rc.excel_output_path, root=self.root))
            probe = self.cdp_probe or probe_loopback_endpoint
            try:
                self._browser_handle = self._browser_acquirer(
                    rc.cdp.cdp_url, self.root, cfg, probe=probe
                )
            except Exception as exc:
                raise RuntimeError("CDP browser requires manual handling") from exc
            readiness = assess_readiness(rc.cdp.cdp_url, cdp_probe=probe)
            if not readiness.ready:
                raise RuntimeError("Research readiness requires manual handling")
            client = Path(cfg["client_secret_file"])
            client = resolve_app_path(client, root=self.root)
            reader = GoogleSheetsRowReader(
                build_read_only_google_sheets_service(client)
            )
            worksheets = tuple(
                WorksheetIdentity(cfg["spreadsheet_id"], title)
                for title in cfg["worksheet_titles"]
            )
            db = Path(cfg.get("sqlite_path", "runtime/production/workflow.sqlite3"))
            db = resolve_app_path(db, root=self.root)
            self._excel = (
                rc.excel_output_path
                if rc.excel_output_path.is_absolute()
                else resolve_app_path(rc.excel_output_path, root=self.root)
            )
            self._store = WorkflowStateStore(db)
            research = build_production_research_service(rc, cdp_probe=self.cdp_probe)
            worker = WorkflowWorker(
                self._store,
                _Observer(research, self._seen, self._manual_review),
                brand_updater=None,
            )
            runtime = WorkflowRuntime(
                WorkflowPoller(self._store, reader), worker, worksheets
            )
            self._refresh_history(force=True)
            self._set_health(("正常", "已连接", "正常", "正常"), "正常")

            def poll_loop():
                try:
                    while True:
                        with self._poll_gate:
                            if self._stop.is_set():
                                return
                            self._poll_idle.clear()
                        try:
                            self._last_poll = utc_now()
                            runtime.run_poll(now=self._last_poll)
                            with self._lock:
                                if self._state is RunState.RUNNING:
                                    self._next_poll_at = utc_now() + runtime.poll_interval
                            self._set_health(("正常", "已连接", "正常", "正常"), "正常")
                        finally:
                            self._poll_idle.set()
                        if self._stop.wait(runtime.poll_interval.total_seconds()):
                            return
                except Exception as exc:  # noqa: BLE001 - fail closed at runtime boundary
                    self._runtime_error(exc)

            def worker_loop():
                try:
                    while True:
                        if self._stop.is_set() and not self._drain_due_on_stop.is_set():
                            return
                        processed = runtime.worker.process_due_one()
                        self._refresh()
                        if processed is not None:
                            continue
                        if self._stop.is_set() and self._drain_due_on_stop.is_set():
                            if self._poll_idle.is_set():
                                return
                            self._poll_idle.wait(
                                timeout=runtime.worker_idle_interval.total_seconds()
                            )
                            continue
                        self._stop.wait(runtime.worker_idle_interval.total_seconds())
                except Exception as exc:  # noqa: BLE001 - fail closed at runtime boundary
                    self._runtime_error(exc)

            poll_thread = threading.Thread(
                target=poll_loop, name="production-sheets-poller"
            )
            worker_thread = threading.Thread(
                target=worker_loop, name="production-research-worker"
            )
            poll_thread.start()
            worker_thread.start()
            while poll_thread.is_alive() or worker_thread.is_alive():
                self._refresh()
                poll_thread.join(timeout=0.1)
                worker_thread.join(timeout=0.1)
        except Exception as exc:  # noqa: BLE001 - fail closed at runtime boundary
            log.warning("Production runtime stopped (%s)", type(exc).__name__)
            self._append_log(
                "ERROR",
                f"需要人工处理：{type(exc).__name__}；请检查本地配置、授权、CDP 与人工验证状态",
            )
            self._set_health(("异常", "异常", "异常", "需要人工处理"), "需要人工处理")
            with self._lock:
                self._state = RunState.MANUAL_REVIEW
        finally:
            self._refresh()
            if self._browser_handle is not None:
                try:
                    self._browser_handle.close()
                except Exception as exc:  # noqa: BLE001 - cleanup boundary
                    log.warning("Owned browser shutdown failed (%s)", type(exc).__name__)
                self._browser_handle = None
            with self._lock:
                if self._state is not RunState.MANUAL_REVIEW:
                    self._state = RunState.STOPPED
                self._stopped = utc_now()
                self._notify()

    def _seen(self, inquiry):
        with self._lock:
            if inquiry not in self._inquiries:
                self._inquiries.append(inquiry)

    def _runtime_error(self, exc):
        log.warning("Production runtime worker failed (%s)", type(exc).__name__)
        with self._lock:
            self._state = RunState.MANUAL_REVIEW
            self._next_poll_at = None
            self._drain_due_on_stop.clear()
            with self._poll_gate:
                self._stop.set()
            self._health = HealthReport(
                tuple(
                    HealthItem(name, "需要人工处理", "运行组件停止")
                    for name in self._components()
                ),
                "需要人工处理",
            )
        self._append_log(
            "ERROR", f"需要人工处理：{type(exc).__name__}；检查本地运行状态"
        )
        self._notify()

    def _manual_review(self, inquiry_id):
        with self._lock:
            self._manual_inquiries.add(inquiry_id)
            self._state = RunState.MANUAL_REVIEW
            self._next_poll_at = None
            self._drain_due_on_stop.clear()
            with self._poll_gate:
                self._stop.set()
            self._health = HealthReport(
                tuple(
                    HealthItem(
                        name,
                        "需要人工处理" if name == "Research" else "已停止",
                        "采集遇到需要人工介入的登录或安全验证",
                    )
                    for name in self._components()
                ),
                "需要人工处理",
            )
        self._append_log("WARNING", "采集需要人工处理；请完成允许的验证后重新启动")
        self._refresh()
        self._notify()

    def _refresh(self):
        if not self._store:
            return
        self._refresh_history()
        items = {i.inquiry_id: i for i in self._store.all_items()}
        ids = [i for i in self._inquiries if i in items]
        history_by_id = {order.inquiry_id: order for order in self._history}
        results = []
        for key in ids:
            item = items[key]
            historical = history_by_id.get(key)
            status = {
                WorkflowStatus.COMPLETED: (
                    OrderStatus.PARTIAL
                    if item.research_status == "PARTIAL_SUCCESS"
                    else OrderStatus.COMPLETED
                ),
                WorkflowStatus.MANUAL_REVIEW: OrderStatus.ERROR,
                WorkflowStatus.FAILED: OrderStatus.ERROR,
            }.get(item.status, OrderStatus.PENDING)
            if key in self._manual_inquiries:
                status = OrderStatus.ERROR
            results.append(
                Order(
                    key,
                    historical.model if historical else item.mpn,
                    historical.brand if historical else item.brand,
                    historical.quantity if historical else item.quantity,
                    historical.stock_label if historical else "待验证",
                    historical.min_reference_price if historical else None,
                    historical.total_price if historical else None,
                    status,
                    historical.sources if historical else (),
                    historical.remark if historical else (item.last_error or ""),
                    self._run_id or "",
                    historical.importance if historical else item.importance_raw,
                    historical.processed_at if historical else None,
                )
            )
        with self._lock:
            self._results = tuple(results)

    def _refresh_history(self, *, force=False):
        if not self._excel:
            return
        try:
            stat = self._excel.stat() if self._excel.is_file() else None
            fingerprint = (stat.st_mtime_ns, stat.st_size) if stat else None
        except OSError:
            fingerprint = None
        with self._lock:
            if not force and fingerprint == self._history_fingerprint:
                return
        try:
            records = ResearchExcelOutput(self._excel).read_history()
        except Exception as exc:  # noqa: BLE001 - history display must not stop runtime
            log.warning("Research history unavailable (%s)", type(exc).__name__)
            with self._lock:
                self._history_fingerprint = fingerprint
            return
        status_map = {
            "SUCCESS": OrderStatus.COMPLETED,
            "PARTIAL_SUCCESS": OrderStatus.PARTIAL,
            "EXCEPTION": OrderStatus.ERROR,
            "MANUAL_REVIEW_REQUIRED": OrderStatus.ERROR,
            "RETRYABLE_FAILURE": OrderStatus.ERROR,
        }
        orders = tuple(
            Order(
                inquiry_id=record.inquiry_id,
                model=record.mpn or "",
                brand=record.brand,
                quantity=_integer(record.quantity, 0),
                stock_label=record.stock_label or "待验证",
                min_reference_price=_decimal(record.market_reference),
                total_price=_decimal(record.estimated_total),
                status=status_map.get(record.research_status, OrderStatus.UNKNOWN),
                sources=tuple(SourceDetail(name, value) for name, value in record.source_values),
                remark=record.remarks or "",
                importance=record.importance_raw,
                processed_at=record.processed_at,
            )
            for record in records
        )
        with self._lock:
            self._history = orders
            self._history_fingerprint = fingerprint

    def get_status(self):
        with self._lock:
            items = self._store.all_items() if self._store else ()
            return RunSession(
                self._run_id,
                self._state,
                self._started,
                self._stopped,
                len(self._results),
                sum(
                    i.status is WorkflowStatus.COMPLETED
                    and i.inquiry_id in self._inquiries
                    for i in items
                ),
                sum(i.status is WorkflowStatus.RESEARCHING for i in items),
                sum(
                    i.status in (WorkflowStatus.QUEUED, WorkflowStatus.RETRY_WAIT)
                    for i in items
                ),
                self._next_poll_at if self._state is RunState.RUNNING else None,
            )

    def get_current_run_results(self):
        with self._lock:
            return self._results

    def get_result_history(self):
        with self._lock:
            return self._history

    def get_health(self):
        return self._health

    def get_logs(self):
        with self._lock:
            return tuple(self._logs)

    def get_diagnostics(self):
        with self._lock:
            return DiagnosticSnapshot(
                self._run_id,
                max(0, (utc_now() - self._started).total_seconds())
                if self._started
                else 0,
                0,
                "running" if self._thread and self._thread.is_alive() else "stopped",
                self._last_poll,
            )

    def open_excel(self):
        if self._excel and self._excel.exists():
            os.startfile(self._excel)

    def open_results_dir(self):
        path = self._excel.parent if self._excel else self.root / "runtime"
        if sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def on_status_change(self, callback):
        with self._lock:
            if callback is None:
                self._status_callbacks.clear()
            elif callback not in self._status_callbacks:
                self._status_callbacks.append(callback)

    def on_log(self, callback):
        with self._lock:
            if callback is None:
                self._log_callbacks.clear()
            elif callback not in self._log_callbacks:
                self._log_callbacks.append(callback)

    def shutdown(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            with self._poll_gate:
                self._stop.set()
            thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join()
        with self._lock:
            self._status_callbacks.clear()
            self._log_callbacks.clear()

    def _notify(self):
        status = self.get_status()
        for cb in tuple(self._status_callbacks):
            cb(status)

    def _append_log(self, level, message):
        entry = LogEntry(utc_now(), level, message)
        with self._lock:
            self._logs = (self._logs + [entry])[-1000:]
            callbacks = tuple(self._log_callbacks)
        for cb in callbacks:
            cb(entry)

    def _set_health(self, statuses, overall):
        self._health = HealthReport(
            tuple(
                HealthItem(n, s)
                for n, s in zip(self._components(), statuses, strict=True)
            ),
            overall,
        )


def _integer(value, fallback):
    try:
        return int(value)
    except (ValueError, TypeError):
        return fallback if isinstance(fallback, int) else 0


def _decimal(value):
    if value is None:
        return None
    text = str(value).strip().splitlines()[0].replace("¥", "").replace(",", "")
    try:
        return Decimal(text) if text else None
    except InvalidOperation:
        return None
