"""Finite Windows synthetic acceptance. Never imported by the application.

Reuses the existing resource sampler and own-HWND capture. Real OS DPI only;
no display-setting changes, production composition, SQL, network or foreground.
"""

import argparse
import ctypes
import hashlib
import importlib.abc
import importlib.util
import json
import logging
import os
import platform
import smtplib
import socket
import sqlite3
import subprocess
import sys
import time
import traceback
from collections import deque
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from measure_workbench import process_sample
from verify_workbench_ui import capture


def hashes(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (root / "src").rglob("*.py")
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=86400)
    parser.add_argument("--sample-seconds", type=int, default=60)
    parser.add_argument("--exercise-seconds", type=int, default=300)
    args = parser.parse_args()
    assert (
        args.seconds > 0 and args.sample_seconds >= 10 and args.exercise_seconds >= 10
    )
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    args.output.mkdir(parents=True, exist_ok=False)
    source_sha = (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip()
    )
    source_hashes = hashes(root)
    platform.uname()  # cache OS version before blocking child process creation
    # A non-input Win32 desktop prevents Tk activation from touching Owner's
    # foreground. Never switch desktops or start a shell on this desktop.
    desktop_user = ctypes.WinDLL("user32", use_last_error=True)
    desktop_user.CreateDesktopW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
    ]
    desktop_user.CreateDesktopW.restype = ctypes.c_void_p
    desktop_user.SetThreadDesktop.argtypes = [ctypes.c_void_p]
    desktop = desktop_user.CreateDesktopW(
        f"INSO-synthetic-{os.getpid()}", None, None, 0, 0x01FF, None
    )
    assert desktop and desktop_user.SetThreadDesktop(desktop), (
        "ISOLATED_DESKTOP_UNAVAILABLE"
    )
    guard_attempts = []

    def deny(*_a, **_kw):
        guard_attempts.append("FORBIDDEN_EXTERNAL_OR_DB_CALL")
        raise AssertionError(guard_attempts[-1])

    class NoBusiness(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.startswith(
                (
                    "src.launcher",
                    "src.workflow",
                    "src.research",
                    "src.sheets",
                    "src.inso",
                    "src.order_mail",
                )
            ):
                deny()

    sys.meta_path.insert(0, NoBusiness())
    socket.socket.connect = socket.socket.connect_ex = deny
    socket.create_connection = deny
    smtplib.SMTP = smtplib.SMTP_SSL = deny
    sqlite3.connect = deny
    subprocess.Popen = deny

    import customtkinter as ctk

    from src.gui import app as gui_app
    from src.gui.contracts import (
        LogEntry,
        Order,
        OrderStatus,
        RunState,
        SourceDetail,
        WorkbenchSnapshot,
    )
    from src.gui.mock_backend import MockBackend

    # Load the existing pure observer file without importing production composition.
    spec = importlib.util.spec_from_file_location(
        "acceptance_observation", root / "src/launcher/workbench_snapshot.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    obs = module.RuntimeObservation()
    obs.enable(
        quotation=True, tp=True
    )  # pure synthetic observation; no business backend
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
            sources=(SourceDetail("Findchips", "合成展示，无真实报价"),),
            remark="合成 UI 验收，不是业务订单",
            processed_at=now,
            source_sheet=("2026", "SHAHAB")[i % 2],
            source_row=i + 2,
            module_id=("inquiry", "quotation", "tp")[i % 3],
            business_status="MAIL_QUEUED" if i % 3 == 2 else None,
            delivery_status="UNKNOWN" if i == 2 else "SENT" if i % 3 == 2 else None,
        )
        for i in range(1000)
    )
    log = deque(maxlen=300)
    log.extend(LogEntry(now, "INFO", f"合成验收初始化事件 {i}") for i in range(10))
    feedback = []
    gui_app.messagebox.showwarning = lambda *_a, **_kw: feedback.append(
        "SYNTHETIC_REQUEST_REJECTED"
    )
    gui_app.messagebox.askyesno = lambda *_a, **_kw: False
    session = replace(
        backend.get_status(),
        state=RunState.RUNNING,
        next_poll_at=now + timedelta(minutes=15),
    )
    view = WorkbenchSnapshot(
        1, session, backend.get_health(), orders[:100], total_orders=100
    )
    backend.get_status = lambda: view.session
    backend.get_workbench_snapshot = lambda: view
    backend.order_action_hint = lambda key, action: (
        view.session.next_poll_at is not None
        and (
            (key == orders[0].inquiry_id and action in {"purchase", "quotation"})
            or (key == orders[5].inquiry_id and action == "tp")
        )
    )
    backend.request_order_action = lambda *_a, **_kw: (
        "合成验收：请求已安全拒绝，未接入生产操作。"
    )
    app = gui_app.InsoDashboardApp(backend)
    app._root.withdraw()
    app._root.update_idletasks()
    u = ctypes.WinDLL("user32", use_last_error=True)
    from ctypes import wintypes as w

    u.GetAncestor.argtypes = [w.HWND, w.UINT]
    u.GetAncestor.restype = w.HWND
    u.GetForegroundWindow.restype = w.HWND
    u.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
    u.SetWindowPos.argtypes = [
        w.HWND,
        w.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        w.UINT,
    ]
    hwnd = u.GetAncestor(app._root.winfo_id(), 2)
    get_style = u.GetWindowLongPtrW
    get_style.argtypes = [w.HWND, ctypes.c_int]
    get_style.restype = ctypes.c_ssize_t
    set_style = u.SetWindowLongPtrW
    set_style.argtypes = [w.HWND, ctypes.c_int, ctypes.c_ssize_t]
    set_style(
        hwnd, -20, get_style(hwnd, -20) | 0x08000000
    )  # WS_EX_NOACTIVATE, own window only

    def behind():
        u.SetWindowPos(
            hwnd, w.HWND(1), 0, 0, 0, 0, 0x0013
        )  # BOTTOM + NOMOVE/NOSIZE/NOACTIVATE

    # Preserve tray show/render code, suppress only its foreground raise in this diagnostic.
    app._root.lift = behind
    app._root.deiconify()
    behind()
    failures, layouts, timings = [], [], deque(maxlen=1000)
    app._root.report_callback_exception = lambda kind, _value, _tb: failures.append(
        kind.__name__
    )
    u.GetDpiForWindow.argtypes = [w.HWND]
    actual_dpi = u.GetDpiForWindow(hwnd)
    monitor = u.MonitorFromWindow
    monitor.argtypes = [w.HWND, w.DWORD]
    monitor.restype = w.HANDLE

    class Info(ctypes.Structure):
        _fields_ = [
            ("cbSize", w.DWORD),
            ("rect", w.RECT),
            ("work", w.RECT),
            ("flags", w.DWORD),
        ]

    info = Info()
    info.cbSize = ctypes.sizeof(info)
    u.GetMonitorInfoW.argtypes = [w.HANDLE, ctypes.POINTER(Info)]
    assert u.GetMonitorInfoW(monitor(hwnd, 2), ctypes.byref(info))
    metadata = {
        "source_sha": source_sha,
        "source_sha256": source_hashes,
        "synthetic_only": True,
        "python": sys.version,
        "logical_cpus": os.cpu_count(),
        "pid": os.getpid(),
        "started_at": datetime.now(UTC).isoformat(),
        "requested_seconds": args.seconds,
        "sample_seconds": args.sample_seconds,
        "exercise_seconds": args.exercise_seconds,
        "actual_window_dpi": actual_dpi,
        "os_scaling_percent": actual_dpi / 96 * 100,
        "other_dpi": "NOT_VERIFIED; no Owner display settings changed",
        "foreground_policy": "Non-input Win32 desktop; never switched; NOACTIVATE + bottom",
        "shell_tray": "NOT_VERIFIED: isolated desktop has no Explorer shell",
    }

    def save(name, value):
        (args.output / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    save("environment.json", metadata)
    sample_file = (args.output / "samples.jsonl").open(
        "a", encoding="utf-8", buffering=1
    )
    tick_times = deque(maxlen=5000)
    original_tick = app._tick_workbench

    def measured_tick():
        started = time.perf_counter()
        original_tick()
        tick_times.append((time.perf_counter() - started) * 1000)

    app._tick_workbench = measured_tick
    begin, cpu, last = time.monotonic(), time.process_time(), time.monotonic()
    phase, cycle, max_gap, stopping = "startup", 0, 0.0, False

    def foreground_check():
        pid = w.DWORD()
        u.GetWindowThreadProcessId(u.GetForegroundWindow(), ctypes.byref(pid))
        if pid.value == os.getpid():
            app._root.withdraw()
            raise AssertionError("SYNTHETIC_WINDOW_BECAME_FOREGROUND")

    def publish(count=1000, recovery=False):
        nonlocal view
        obs.begin_cycle()
        obs.stage(
            ("inquiry", "quotation", "tp")[cycle % 3],
            "合成查询阶段",
            site="findchips",
            order_ref=orders[0].inquiry_id,
        )
        if recovery:
            obs.end_cycle(
                datetime.now(UTC) + timedelta(minutes=15), recovery_site="合成网站"
            )
        revision, modules, started, tick, ended, stages, durations, plan, site = (
            obs.snapshot()
        )
        view = replace(
            view,
            revision=view.revision + revision + 1,
            orders=orders[:count],
            total_orders=count,
            modules=modules,
            cycle_started_at=started,
            cycle_started_monotonic=tick,
            cycle_finished_at=ended,
            timings=stages,
            cycle_durations=durations,
            planned_check_at=plan,
            recovery_site=site,
            logs=tuple(log),
            session=replace(view.session, next_poll_at=plan),
        )
        app._view.render(view, force=True)

    def sample():
        nonlocal cpu, last, max_gap
        stamp, proc = time.monotonic(), time.process_time()
        gap = stamp - last
        max_gap = max(max_gap, gap)
        row = dict(
            seconds=stamp - begin,
            phase=phase,
            cpu_one_core_percent=100 * (proc - cpu) / max(gap, 0.001),
            cpu_host_percent=100
            * (proc - cpu)
            / max(gap, 0.001)
            / (os.cpu_count() or 1),
            after_callbacks=len(app._root.tk.call("after", "info")),
            event_queue=len(app._events._queue) + len(app._events._latest),
            displayed_rows=len(app._tree.get_children()),
            loaded_orders=len(app._view.orders),
            view_rows_cache=len(app._view._row_values),
            view_value_cache=len(app._view._values),
            snapshot_logs=len(log),
            backend_log_ring=len(backend.get_logs()),
            tick_max_ms=max(tick_times, default=0),
            **process_sample(),
        )
        sample_file.write(json.dumps(row) + "\n")
        save(
            "heartbeat.json",
            {
                "seconds": row["seconds"],
                "phase": phase,
                "cycle": cycle,
                "callback_errors": failures,
                "guard_attempts": guard_attempts,
                "max_sample_gap_seconds": max_gap,
                "sampled_at": datetime.now(UTC).isoformat(),
            },
        )
        cpu, last = proc, stamp

    def exercise():
        nonlocal cycle, phase
        cycle += 1
        count = (100, 500, 1000)[cycle % 3]
        for i in range(300):
            entry = LogEntry(datetime.now(UTC), "INFO", f"合成验收事件 {cycle}-{i}")
            backend._ring_log.emit(
                logging.LogRecord("synthetic", 20, "", 0, entry.message, (), None)
            )
            backend._notify_log(entry)
            log.append(entry)
        phase = "exercise"
        publish(count, recovery=cycle % 2 == 0)
        started = time.perf_counter()
        for page in app._view.pages:
            app._view.show_page(page)
        app._view.show_page("任务中心")
        app._view.search.insert(0, "0000")
        app._view._apply_filter()
        assert app._tree.get_children() == (orders[0].inquiry_id,)
        app._view.search.delete(0, "end")
        app._view._apply_filter()
        app._view.filters["source"].set("SHAHAB")
        app._view._apply_filter()
        assert all(int(key.rsplit("-", 1)[1]) % 2 for key in app._tree.get_children())
        app._view.filters["source"].set("全部来源")
        app._view.filters["status"].set("需核对")
        app._view._apply_filter()
        assert app._tree.get_children()
        app._view.filters["status"].set("全部状态")
        app._view._apply_filter()
        app._view.sort("model")
        app._view.page_by(1)
        app._view.page_by(-1)
        app._view.render_detail(orders[5])
        sample()
        app._view.hide_detail()
        if cycle % 2:
            app._root.withdraw()
            app._hidden = True
            phase = "withdrawn_idle_no_shell_tray"
        else:
            app._on_tray_command("show")
            behind()
            phase = "visible_idle"
        foreground_check()
        timings.append(
            {
                "cycle": cycle,
                "orders": count,
                "milliseconds": 1000 * (time.perf_counter() - started),
            }
        )
        sample()

    def finish(error=None):
        nonlocal view, stopping
        if stopping:
            return
        stopping = True
        if error:
            (args.output / "diagnostic-error.txt").write_text(
                traceback.format_exc(), encoding="utf-8"
            )
        sample()
        elapsed = time.monotonic() - begin
        complete = (
            not error
            and not failures
            and not guard_attempts
            and elapsed >= args.seconds
        )
        same_source = source_hashes == hashes(root)
        save(
            "complete.json",
            {
                "completed": complete,
                "elapsed_seconds": elapsed,
                "requested_seconds": args.seconds,
                "continuous_24h_verified": complete
                and elapsed >= 86400
                and max_gap <= args.sample_seconds * 3
                and same_source,
                "max_sample_gap_seconds": max_gap,
                "source_unchanged": same_source,
                "error": error,
                "callback_errors": failures,
                "guard_attempts": guard_attempts,
                "cycles": cycle,
                "closed_at": datetime.now(UTC).isoformat(),
                "operation_timings": list(timings),
            },
        )
        sample_file.close()
        view = replace(view, session=replace(view.session, state=RunState.STOPPED))
        app._on_close()

    def drive():
        try:
            foreground_check()
            if failures or guard_attempts:
                finish("CALLBACK_OR_SAFETY_GUARD_FAILURE")
                return
            if time.monotonic() - begin >= args.seconds:
                finish()
                return
            sample()
            app._root.after(args.sample_seconds * 1000, drive)
        except Exception as exc:  # noqa: BLE001 - diagnostic must persist any failure
            finish(type(exc).__name__)

    def repeat():
        try:
            if not stopping:
                exercise()
                app._root.after(args.exercise_seconds * 1000, repeat)
        except Exception as exc:  # noqa: BLE001 - finite diagnostic failure boundary
            finish(type(exc).__name__)

    try:
        publish(1000)
        for width, height, label in (
            (1280, 720, "1280x720"),
            (1920, 1080, "1920x1080"),
            (
                info.work.right - info.work.left - 24,
                info.work.bottom - info.work.top - 64,
                "workarea",
            ),
        ):
            scale = ctk.ScalingTracker.get_window_scaling(app._root)
            app._root.geometry(f"{int(width / scale)}x{int(height / scale)}+10+10")
            for _ in range(5):
                app._root.update()
                behind()
                time.sleep(0.1)
            for page in app._view.pages:
                app._view.show_page(page)
                app._root.update()
                foreground_check()
                controls = [app._action_button] + (
                    list(app._view.filters.values())
                    if page in {"任务中心", "调研结果"}
                    else []
                )
                visible = all(
                    c.winfo_ismapped()
                    and c.winfo_rootx() + c.winfo_width()
                    <= app._root.winfo_rootx() + app._root.winfo_width()
                    and c.winfo_rooty() + c.winfo_height()
                    <= app._root.winfo_rooty() + app._root.winfo_height()
                    for c in controls
                )
                layouts.append(
                    {
                        "page": page,
                        "viewport": label,
                        "client": [app._root.winfo_width(), app._root.winfo_height()],
                        "important_controls_fit": visible,
                        "actual_os_dpi": u.GetDpiForWindow(hwnd),
                    }
                )
                if label != "workarea":
                    capture(
                        app._root,
                        args.output / f"page-{label}-{app._view.pages.index(page)}.png",
                    )
        publish(1000, recovery=True)
        button_checks = []
        for index in (0, 2, 5):
            app._view.render_detail(orders[index])
            for widget in app._detail_container.winfo_children():
                if isinstance(widget, ctk.CTkButton) and str(
                    widget.cget("text")
                ).startswith("重跑"):
                    enabled = widget.cget("state") == "normal"
                    button_checks.append(
                        {
                            "sample": index,
                            "title": widget.cget("text"),
                            "enabled": enabled,
                        }
                    )
                    if enabled:
                        widget.invoke()
        assert len(feedback) == 3
        save(
            "ui-checks.json",
            {
                "layouts": layouts,
                "mock_feedback_count": len(feedback),
                "actual_os_dpi": actual_dpi,
                "important_controls_fit": all(
                    c["important_controls_fit"] for c in layouts
                ),
                "foreground_violations": 0,
                "button_checks": button_checks,
                "not_verified_dpi": [
                    p for p in (100, 125, 150) if p != actual_dpi / 96 * 100
                ],
            },
        )
        # Finalize initial visual checks; baseline idle precedes repeated workloads.
        app._view.show_page("总览")
        phase = "visible_idle"
        sample()
        app._root.after(args.sample_seconds * 1000, drive)
        app._root.after(
            (600 if args.seconds >= 86400 else args.exercise_seconds) * 1000, repeat
        )
        app.run()
    except Exception as exc:  # noqa: BLE001 - close owned window on diagnostic failure
        finish(type(exc).__name__)
    finally:
        if not stopping:
            finish("UNEXPECTED_MAINLOOP_EXIT")
        backend.shutdown()


if __name__ == "__main__":
    main()
