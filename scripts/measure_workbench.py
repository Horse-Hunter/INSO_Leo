"""Manual synthetic GUI probe. No production backend, credentials or network.

python scripts/measure_workbench.py --output <ignored-dir> [--source-root <old-src>]
Default durations are real seconds: 10 minutes idle,30 minutes visible,2 minutes
tray. This diagnostic is never imported by the application or run at startup.
"""

import argparse
import ctypes
import hashlib
import json
import os
import socket
import sys
import threading
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path


def process_sample():
    from ctypes import wintypes as w

    class Memory(ctypes.Structure):
        _fields_ = [("cb", w.DWORD), ("faults", w.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "peak_rss",
                "rss",
                "peak_paged",
                "paged",
                "peak_nonpaged",
                "nonpaged",
                "pagefile",
                "peak_pagefile",
                "private",
            )
        ]

    class Thread(ctypes.Structure):
        _fields_ = [
            (n, t)
            for n, t in [
                ("size", w.DWORD),
                ("usage", w.DWORD),
                ("tid", w.DWORD),
                ("pid", w.DWORD),
                ("base", w.LONG),
                ("delta", w.LONG),
                ("flags", w.DWORD),
            ]
        ]

    k, u, p = ctypes.WinDLL("kernel32"), ctypes.WinDLL("user32"), ctypes.WinDLL("psapi")
    h = ctypes.c_void_p(-1)
    memory, handles = Memory(), w.DWORD()
    memory.cb = ctypes.sizeof(memory)
    assert p.GetProcessMemoryInfo(h, ctypes.byref(memory), memory.cb)
    assert k.GetProcessHandleCount(h, ctypes.byref(handles))
    k.CreateToolhelp32Snapshot.restype = w.HANDLE
    k.Thread32First.argtypes = k.Thread32Next.argtypes = [
        w.HANDLE,
        ctypes.POINTER(Thread),
    ]
    k.CloseHandle.argtypes = [w.HANDLE]
    snap = k.CreateToolhelp32Snapshot(4, 0)
    entry, threads = Thread(), 0
    entry.size = ctypes.sizeof(entry)
    try:
        more = k.Thread32First(snap, ctypes.byref(entry))
        while more:
            threads += entry.pid == os.getpid()
            more = k.Thread32Next(snap, ctypes.byref(entry))
    finally:
        k.CloseHandle(snap)
    return {
        "rss": memory.rss,
        "private": memory.private,
        "threads": threads,
        "python_threads": len(threading.enumerate()),
        "handles": handles.value,
        "gdi": u.GetGuiResources(h, 0),
        "user": u.GetGuiResources(h, 1),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--idle-seconds", type=int, default=600)
    parser.add_argument("--foreground-seconds", type=int, default=1800)
    parser.add_argument("--tray-seconds", type=int, default=120)
    args = parser.parse_args()
    sys.path.insert(0, str(args.source_root or Path(__file__).resolve().parents[1]))
    args.output.mkdir(parents=True, exist_ok=True)
    source = args.source_root or Path(__file__).resolve().parents[1]
    (args.output / "environment.json").write_text(
        json.dumps(
            {
                "python": sys.version,
                "logical_cpus": os.cpu_count(),
                "synthetic_only": True,
                "source_sha256": {
                    str(p.relative_to(source)): hashlib.sha256(
                        p.read_bytes()
                    ).hexdigest()
                    for folder in ("src/gui", "src/launcher")
                    for p in (source / folder).glob("*.py")
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    def deny(*a, **kw):
        raise AssertionError("SYNTHETIC_UI_NETWORK_FORBIDDEN")

    socket.socket.connect = deny
    from src.gui import contracts
    from src.gui.app import InsoDashboardApp
    from src.gui.contracts import Order, OrderStatus
    from src.gui.mock_backend import MockBackend

    backend = MockBackend()
    now = datetime.now(UTC)
    orders = tuple(
        Order(
            f"synthetic-{i:04}",
            f"DEMO-COMPONENT-{i:04}-LONG-MODEL",
            "SYNTHETIC",
            i + 1,
            "待验证",
            None,
            None,
            (OrderStatus.PENDING, OrderStatus.COMPLETED, OrderStatus.ERROR)[i % 3],
            remark="合成 UI 数据，无真实订单",
            processed_at=now,
        )
        for i in range(1000)
    )
    if hasattr(contracts, "WorkbenchSnapshot"):
        orders = tuple(
            replace(
                o,
                source_sheet=("2026", "SHAHAB")[i % 2],
                source_row=i + 2,
                module_id=("inquiry", "quotation", "tp")[i % 3],
            )
            for i, o in enumerate(orders)
        )
    backend._history = list(orders[:100])
    backend.get_result_history = lambda: tuple(backend._history)
    app = InsoDashboardApp(backend)
    app._root.geometry("1280x720+40+40")
    rows, timings = [], []
    ticks = []
    original_tick = app._schedule_tick

    def measured_tick():
        started = time.perf_counter()
        original_tick()
        ticks.append(1000 * (time.perf_counter() - started))
        del ticks[:-5000]

    app._schedule_tick = measured_tick
    begin, cpu, last, phase = (
        time.monotonic(),
        time.process_time(),
        time.monotonic(),
        "idle",
    )
    durations = [args.idle_seconds, args.foreground_seconds, args.tray_seconds]

    def sample():
        nonlocal cpu, last
        stamp, proc = time.monotonic(), time.process_time()
        row = dict(
            seconds=stamp - begin,
            phase=phase,
            cpu_one_core_percent=100 * (proc - cpu) / max(stamp - last, 0.001),
            cpu_host_percent=100
            * (proc - cpu)
            / max(stamp - last, 0.001)
            / (os.cpu_count() or 1),
            **process_sample(),
        )
        rows.append(row)
        (args.output / "samples.json").write_text(
            json.dumps(rows, indent=2), encoding="utf-8"
        )
        cpu, last = proc, stamp
        app._root.after(30000, sample)

    def foreground():
        nonlocal phase
        phase = "foreground"
        if hasattr(app, "_view"):
            app._view.show_page("任务中心")
        for count in (100, 500, 1000):
            backend._history = list(orders[:count])
            started = time.perf_counter()
            if hasattr(app, "_view"):
                app._view.set_orders(tuple(backend._history))
            else:
                app._refresh_results()
            app._root.update_idletasks()
            timings.append(
                {
                    "operation": "table",
                    "rows": count,
                    "ms": 1000 * (time.perf_counter() - started),
                }
            )
        if hasattr(app, "_view"):
            for _ in range(20):
                started = time.perf_counter()
                app._view.render_detail(orders[0])
                app._root.update_idletasks()
                app._view.hide_detail()
                timings.append(
                    {
                        "operation": "detail",
                        "ms": 1000 * (time.perf_counter() - started),
                    }
                )
            for text in ("0001", "COMPONENT", "absent", ""):
                started = time.perf_counter()
                app._view.search.delete(0, "end")
                app._view.search.insert(0, text)
                app._view._apply_filter()
                app._root.update_idletasks()
                timings.append(
                    {
                        "operation": "search",
                        "ms": 1000 * (time.perf_counter() - started),
                    }
                )
            for _ in range(30):
                for page in app._view.pages:
                    started = time.perf_counter()
                    app._view.show_page(page)
                    app._root.update_idletasks()
                    timings.append(
                        {
                            "operation": "page",
                            "ms": 1000 * (time.perf_counter() - started),
                        }
                    )
            app._view.show_page("总览")
        (args.output / "timings.json").write_text(json.dumps(timings), encoding="utf-8")
        app._root.after(args.foreground_seconds * 1000, tray)

    def tray():
        nonlocal phase
        phase = "tray"
        app._on_window_close()
        app._root.after(args.tray_seconds * 1000, finish)

    def finish():
        sample()
        app._on_tray_command("show")
        (args.output / "ticks.json").write_text(json.dumps(ticks), encoding="utf-8")
        (args.output / "complete.json").write_text(
            json.dumps(
                {
                    "completed": True,
                    "durations": durations,
                    "samples": len(rows),
                    "elapsed": time.monotonic() - begin,
                }
            ),
            encoding="utf-8",
        )
        app._on_close()

    app._root.after(1000, sample)
    app._root.after(args.idle_seconds * 1000, foreground)
    app.run()


if __name__ == "__main__":
    main()
