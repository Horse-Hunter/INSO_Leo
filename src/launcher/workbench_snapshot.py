"""Bounded observation of existing boundaries; no I/O, threads or scheduling."""

from collections import deque
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
from threading import RLock
from time import monotonic

from src.gui.contracts import ModuleSnapshot, StageTiming

MODULES = (("inquiry", "询价采购"), ("quotation", "报价跟进"), ("tp", "目标价调研"))


class RuntimeObservation:
    def __init__(self, *, clock=lambda: datetime.now(UTC), timer=monotonic):
        self.clock, self.timer, self.lock = clock, timer, RLock()
        self.modules = {
            key: ModuleSnapshot(
                key, name, status="空闲" if key == "inquiry" else "未启用"
            )
            for key, name in MODULES
        }
        self.cycle_started_at = self.cycle_started_monotonic = (
            self.cycle_finished_at
        ) = None
        self.revision = 0
        self.timings = deque(maxlen=200)
        self.durations = dict.fromkeys(self.modules, 0.0)
        self.pauses = {}
        self.planned_check_at = None
        self.recovery_site = None
        self._module_scopes = []

    @contextmanager
    def module_scope(self, module):
        """Restore only caller observation, never an inner module's new result."""
        with self.lock:
            saved = (self.cycle_started_at, self.cycle_started_monotonic,
                     self.cycle_finished_at, self.planned_check_at, self.recovery_site)
            nested = bool(self._module_scopes)
            self._module_scopes.append(module)
        try:
            yield
        finally:
            with self.lock:
                self._module_scopes.pop()
                if nested:
                    (self.cycle_started_at, self.cycle_started_monotonic,
                     self.cycle_finished_at, self.planned_check_at, self.recovery_site) = saved
                self.revision += 1

    def _close_pause(self, key):
        paused = self.pauses.pop(key, None)
        if paused:
            wall, tick, reason = paused
            self.timings.append(
                StageTiming(
                    key,
                    reason,
                    None,
                    self.modules[key].order_ref,
                    wall,
                    self.clock(),
                    max(0, self.timer() - tick),
                )
            )

    def enable(self, *, quotation=False, tp=False):
        with self.lock:
            for key, enabled in (
                ("inquiry", True),
                ("quotation", quotation),
                ("tp", tp),
            ):
                self._close_pause(key)
                self._close(key)
                self.modules[key] = replace(
                    self.modules[key],
                    status="空闲" if enabled else "未启用",
                    waiting_reason=None,
                )
            self.revision += 1

    def _close(self, module):
        old = self.modules[module]
        if old.started_monotonic is None:
            return old
        duration = max(0, self.timer() - old.started_monotonic)
        finished = self.clock()
        self.timings.append(
            StageTiming(
                module,
                old.stage,
                old.site,
                old.order_ref,
                old.started_at,
                finished,
                duration,
            )
        )
        self.durations[module] += duration
        old = replace(
            old,
            elapsed_seconds=duration,
            started_monotonic=None,
            last_finished_at=finished,
            changed_at=finished,
        )
        self.modules[module] = old
        return old

    def begin_cycle(self):
        with self.lock:
            self.planned_check_at = self.recovery_site = None
            for key in self.modules:
                self._close(key)
            self.durations = dict.fromkeys(self.modules, 0.0)
            self.cycle_started_at, self.cycle_started_monotonic = (
                self.clock(),
                self.timer(),
            )
            self.cycle_finished_at = None
            for key, old in self.modules.items():
                if old.status not in {"未启用", "已暂停"}:
                    self.modules[key] = replace(
                        old,
                        status="等待执行",
                        site=None,
                        started_monotonic=None,
                        next_check_at=None,
                        waiting_reason="等待共享工作流串行执行",
                    )
        if self.modules["inquiry"].status != "已暂停":
            self.stage("inquiry", "读取询价与采购状态")

    def begin_module(self, module):
        with self.lock:
            self.cycle_started_at, self.cycle_started_monotonic = self.clock(), self.timer()
            self.cycle_finished_at = None
            self.durations[module] = 0.0
            self.modules[module] = replace(self.modules[module],
                cycle_started_at=self.clock(), cycle_started_monotonic=self.timer(),
                cycle_finished_at=None, cycle_elapsed_seconds=0)
        self.stage(module, "检查模块待办")

    def module_plan(self, module, next_check, *, paused=False, reason=None):
        with self.lock:
            old = self._close(module)
            self.modules[module] = replace(old,
                status="已暂停" if paused else "等待执行", next_check_at=next_check,
                stage=reason or "等待独立检查周期", waiting_reason=reason)
            self.revision += 1

    def finish_module(self, module=None):
        with self.lock:
            self.cycle_finished_at = self.clock()
            if module is not None:
                old = self.modules[module]
                self.modules[module] = replace(old, cycle_finished_at=self.clock(),
                    cycle_elapsed_seconds=max(0, self.timer()-old.cycle_started_monotonic)
                    if old.cycle_started_monotonic is not None else 0)

    def stage(self, module, stage, *, site=None, order_ref=None):
        with self.lock:
            self.planned_check_at = None
            if self.modules[module].status == "未启用":
                return
            old = self.modules[module]
            self._close_pause(module)
            if old.status == "运行中" and (old.stage, old.site, old.order_ref) == (
                stage,
                site,
                order_ref,
            ):
                return
            for key, other in tuple(self.modules.items()):
                if other.started_monotonic is not None and key not in self._module_scopes[:-1]:
                    other = self._close(key)
                    self.modules[key] = replace(
                        other,
                        status="等待执行",
                        site=None,
                        waiting_reason="等待共享工作流串行执行",
                    )
            now = self.clock()
            self.modules[module] = replace(
                self.modules[module],
                status="运行中",
                stage=stage,
                site=site,
                order_ref=order_ref,
                started_at=now,
                started_monotonic=self.timer(),
                elapsed_seconds=0,
                changed_at=now,
                next_check_at=None,
                waiting_reason=None,
            )
            self.revision += 1

    def finish_stage(self, module):
        with self.lock:
            if self.modules[module].started_monotonic is None:
                return
            old = self._close(module)
            self.modules[module] = replace(
                old, status="等待执行", site=None, waiting_reason="等待本轮后续阶段"
            )
            self.revision += 1

    def wait(self, module, reason, *, site=None):
        with self.lock:
            old = self._close(module)
            if old.status == "未启用":
                return
            now = self.clock()
            self.modules[module] = replace(
                old,
                status="等待执行",
                stage=reason,
                site=site,
                waiting_reason=reason,
                started_at=now,
                started_monotonic=self.timer(),
                elapsed_seconds=0,
                changed_at=now,
            )
            self.revision += 1

    def pause(self, module, reason):
        with self.lock:
            old = self._close(module)
            self.pauses.setdefault(module, (self.clock(), self.timer(), reason))
            self.modules[module] = replace(
                old,
                status="已暂停",
                site=None,
                waiting_reason=reason,
                changed_at=self.clock(),
                next_check_at=None,
            )
            self.revision += 1

    def end_cycle(
        self, next_check=None, *, stopped=False, reason=None, close_round=True,
        recovery_site=None
    ):
        with self.lock:
            self.planned_check_at = None if stopped or reason else next_check
            self.recovery_site = None if stopped or reason else recovery_site
            if close_round and self.cycle_finished_at is None:
                self.cycle_finished_at = self.clock() if self.cycle_started_at else None
            for key, old in tuple(self.modules.items()):
                if self._module_scopes and not stopped and not reason and key != self._module_scopes[-1]:
                    continue
                if old.status == "未启用":
                    continue
                old = self._close(key)
                if reason:
                    self.pauses.setdefault(key, (self.clock(), self.timer(), reason))
                elif stopped:
                    self._close_pause(key)
                self.modules[key] = replace(
                    old,
                    status="需要人工处理"
                    if reason
                    else "空闲"
                    if stopped
                    else "已暂停"
                    if old.status == "已暂停"
                    else "等待执行",
                    next_check_at=None
                    if stopped or reason or old.status == "已暂停"
                    else next_check,
                    waiting_reason=reason or (f"等待{recovery_site}恢复" if recovery_site else None)
                    or (
                        "已停止"
                        if stopped
                        else old.waiting_reason
                        if old.status == "已暂停"
                        else "等待下一轮计划检查"
                    ),
                    site=None,
                    changed_at=self.clock(),
                )
            self.revision += 1

    def snapshot(self):
        with self.lock:
            return (
                self.revision,
                tuple(
                    replace(
                        m, elapsed_seconds=max(0, self.timer() - self.pauses[key][1])
                    )
                    if key in self.pauses
                    else replace(m, cycle_elapsed_seconds=max(0, self.timer()-m.cycle_started_monotonic))
                    if m.cycle_started_monotonic is not None and m.cycle_finished_at is None else m
                    for key, m in self.modules.items()
                ),
                self.cycle_started_at,
                self.cycle_started_monotonic,
                self.cycle_finished_at,
                tuple(self.timings),
                tuple(self.durations.items()),
                self.planned_check_at,
                self.recovery_site,
            )
