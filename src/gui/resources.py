"""Resource management utilities for the long-running GUI.

Includes a fixed-size log ring buffer and a small helper to track worker/timer
lifetimes so the GUI can shut down without leaking processes.
"""

from __future__ import annotations

import logging
import queue
import sys
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .contracts import LogEntry, RunSession


@dataclass(frozen=True, slots=True)
class BackendEvent:
    """Immutable backend notification queued for main-thread UI handling."""

    kind: str
    payload: RunSession | LogEntry


class MainThreadEventQueue:
    """Thread-safe handoff from backend callbacks to the Tk event loop."""

    def __init__(self) -> None:
        self._queue: queue.SimpleQueue[BackendEvent] = queue.SimpleQueue()

    def publish(self, event: BackendEvent) -> None:
        self._queue.put(event)

    def drain(self) -> tuple[BackendEvent, ...]:
        events: list[BackendEvent] = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                return tuple(events)


class RingBufferLog(logging.Handler):
    """Logging handler that keeps only the most recent N entries."""

    def __init__(self, capacity: int = 1000) -> None:
        super().__init__()
        self._capacity = max(1, capacity)
        self._buffer: deque[LogEntry] = deque(maxlen=self._capacity)
        self._lock = threading.Lock()
        self._listeners: list[Callable[[LogEntry], Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created, tz=timezone.utc),
            level=record.levelname,
            message=self.format(record),
        )
        with self._lock:
            self._buffer.append(entry)
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(entry)
            except Exception:  # noqa: BLE001,S110 - listener must not break logging
                pass

    def snapshot(self) -> tuple[LogEntry, ...]:
        with self._lock:
            return tuple(self._buffer)

    def add_listener(self, callback: Callable[[LogEntry], Any]) -> None:
        with self._lock:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[LogEntry], Any]) -> None:
        with self._lock:
            try:
                self._listeners.remove(callback)
            except ValueError:
                pass

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()


@dataclass(frozen=True, slots=True)
class _Closable:
    name: str
    close: Callable[[], None]


class ResourceManager:
    """Track threads, timers, and callbacks that must be released on shutdown."""

    def __init__(self) -> None:
        self._resources: list[_Closable] = []
        self._lock = threading.Lock()
        self._closed = False

    def add_thread(self, thread: threading.Thread, name: str | None = None) -> None:
        def _join() -> None:
            if thread.is_alive():
                thread.join(timeout=5.0)

        self.add(_join, name or f"thread-{thread.ident}")

    def add_timer(self, timer: threading.Timer) -> None:
        def _cancel() -> None:
            timer.cancel()
            if timer.is_alive():
                timer.join(timeout=1.0)

        self.add(_cancel, f"timer-{id(timer)}")

    def add(self, close_fn: Callable[[], None], name: str) -> None:
        with self._lock:
            if not self._closed:
                self._resources.append(_Closable(name, close_fn))

    def close_all(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            resources = list(reversed(self._resources))
            self._resources.clear()

        errors: list[str] = []
        for resource in resources:
            try:
                resource.close()
            except Exception as exc:  # pragma: no cover - defensive  # noqa: BLE001
                errors.append(f"{resource.name}: {exc}")

        if errors:
            logging.getLogger(__name__).warning(
                "Resource cleanup had issues: %s", "; ".join(errors)
            )


def get_process_memory_mb() -> float:
    """Return the current process working-set size in MB, or 0.0 if unavailable."""
    if sys.platform != "win32":
        return 0.0

    try:
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010

        pid = kernel32.GetCurrentProcessId()
        h = kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid
        )
        if not h:
            return 0.0
        try:
            pmc = PROCESS_MEMORY_COUNTERS()
            pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            if ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
                return round(pmc.WorkingSetSize / (1024 * 1024), 2)
        finally:
            kernel32.CloseHandle(h)
    except Exception:  # noqa: BLE001,S110 - best-effort memory probe
        pass
    return 0.0
