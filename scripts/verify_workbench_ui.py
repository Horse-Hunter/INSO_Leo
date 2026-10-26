"""Manual offline UI verification; captures ONLY its own synthetic Tk window.

Widget scaling exercises layout, not OS DPI certification. No production backend.
"""

import argparse
import ctypes
import json
import socket
import struct
import sys
import time
import zlib
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path


def capture(root, path):
    """PrintWindow on our own HWND, never a desktop/screen grab."""
    from ctypes import wintypes as w

    u, g = ctypes.WinDLL("user32"), ctypes.WinDLL("gdi32")
    for lib, name in (
        (u, "GetAncestor"),
        (u, "GetDC"),
        (g, "CreateCompatibleDC"),
        (g, "CreateCompatibleBitmap"),
        (g, "SelectObject"),
    ):
        getattr(lib, name).restype = w.HANDLE
    u.GetAncestor.argtypes = [w.HWND, w.UINT]
    u.GetDC.argtypes = [w.HWND]
    u.PrintWindow.argtypes = [w.HWND, w.HDC, w.UINT]
    u.ReleaseDC.argtypes = [w.HWND, w.HDC]
    g.CreateCompatibleDC.argtypes = [w.HDC]
    g.CreateCompatibleBitmap.argtypes = [w.HDC, ctypes.c_int, ctypes.c_int]
    g.SelectObject.argtypes = [w.HDC, w.HGDIOBJ]
    g.GetDIBits.argtypes = [
        w.HDC,
        w.HBITMAP,
        w.UINT,
        w.UINT,
        ctypes.c_void_p,
        ctypes.c_void_p,
        w.UINT,
    ]
    g.DeleteObject.argtypes = [w.HGDIOBJ]
    g.DeleteDC.argtypes = [w.HDC]
    hwnd = u.GetAncestor(root.winfo_id(), 2)
    rect = w.RECT()
    assert u.GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top
    dc = u.GetDC(hwnd)
    memory = g.CreateCompatibleDC(dc)
    bitmap = g.CreateCompatibleBitmap(dc, width, height)
    old = g.SelectObject(memory, bitmap)
    try:
        assert u.PrintWindow(hwnd, memory, 2)
        header = ctypes.create_string_buffer(
            struct.pack(
                "<IiiHHIIiiII",
                40,
                width,
                -height,
                1,
                32,
                0,
                width * height * 4,
                0,
                0,
                0,
                0,
            )
        )
        data = ctypes.create_string_buffer(width * height * 4)
        assert g.GetDIBits(memory, bitmap, 0, height, data, header, 0) == height
        raw = data.raw
        scan = bytearray()
        for y in range(height):
            scan.append(0)
            row = raw[y * width * 4 : (y + 1) * width * 4]
            rgb = bytearray(width * 3)
            rgb[0::3], rgb[1::3], rgb[2::3] = row[2::4], row[1::4], row[0::4]
            scan.extend(rgb)

        def chunk(kind, data):
            return (
                struct.pack(">I", len(data))
                + kind
                + data
                + struct.pack(">I", zlib.crc32(kind + data))
            )

        path.write_bytes(
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(scan))
            + chunk(b"IEND", b"")
        )
    finally:
        g.SelectObject(memory, old)
        g.DeleteObject(bitmap)
        g.DeleteDC(memory)
        u.ReleaseDC(hwnd, dc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    def deny(*a, **kw):
        raise AssertionError("SYNTHETIC_UI_NETWORK_FORBIDDEN")

    socket.socket.connect = deny
    import customtkinter as ctk

    from src.gui.app import InsoDashboardApp
    from src.gui.contracts import (
        LogEntry,
        Order,
        OrderStatus,
        RunState,
        WorkbenchSnapshot,
    )
    from src.gui.mock_backend import MockBackend
    from src.launcher.workbench_snapshot import RuntimeObservation

    backend, obs = MockBackend(), RuntimeObservation()
    obs.enable(quotation=True)
    obs.begin_cycle()
    obs.stage("inquiry", "六源价格查询", site="findchips", order_ref="synthetic-0000")
    orders = tuple(
        Order(
            f"synthetic-{i:04}",
            f"DEMO-LONG-COMPONENT-{i:04}-0123456789",
            "DEMO",
            i + 1,
            "待验证",
            None,
            None,
            OrderStatus.ERROR if i % 3 == 0 else OrderStatus.PENDING,
            source_sheet=("2026", "SHAHAB")[i % 2],
            source_row=i + 2,
            delivery_status="UNKNOWN" if i == 0 else None,
        )
        for i in range(1000)
    )
    revision, modules, started, tick, finished, timings, durations, plan, site = obs.snapshot()
    snapshot = WorkbenchSnapshot(
        revision,
        replace(backend.get_status(), state=RunState.RUNNING),
        backend.get_health(),
        orders,
        modules,
        logs=(LogEntry(datetime.now(UTC), "INFO", "合成任务进入查询阶段"),),
        cycle_started_at=started,
        cycle_started_monotonic=tick,
        cycle_finished_at=finished,
        timings=timings,
        cycle_durations=durations,
        planned_check_at=plan,
        recovery_site=site,
    )
    backend.get_workbench_snapshot = lambda: snapshot
    app = InsoDashboardApp(backend)
    failures, checks = [], []
    app._root.report_callback_exception = lambda *error: failures.append(str(error[0]))
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        for scale, width, height in (
            (s, w, h)
            for s in (1, 1.25, 1.5)
            for w, h in ((1280, 720), (1920, 1080), (2560, 1440))
        ):
            ctk.set_widget_scaling(scale)
            # CTk temporarily pins native min/max for 1s after scaling.
            for _ in range(12):
                app._root.update()
                time.sleep(0.1)
            # CTk stores logical size; convert the desired client pixels once.
            window_scale = ctk.ScalingTracker.get_window_scaling(app._root)
            app._root.geometry(
                f"{int(width / window_scale)}x{int(height / window_scale)}+10+10"
            )
            for _ in range(5):
                app._root.update()
                time.sleep(0.1)
            app._view.render(snapshot, force=True)
            actual_scale = ctk.ScalingTracker.get_widget_scaling(app._root)
            assert int(app._view.active_panel.grid_info()["row"]) == int(
                app._root.winfo_height() / actual_scale >= 600
            )
            expected_wrap = max(
                100, (app._root.winfo_width() / actual_scale - 230) // 3 - 40
            )
            assert all(
                label.cget("wraplength") == expected_wrap
                for _, label in app._view.cards.values()
            )
            for page in app._view.pages:
                app._view.show_page(page)
                app._root.update()
                assert app._action_button.winfo_ismapped(), (
                    scale,
                    width,
                    page,
                    app._root.state(),
                    app._root.winfo_ismapped(),
                    app._root.geometry(),
                )
                controls = [app._action_button]
                if page == "任务中心":
                    controls += list(app._view.filters.values())
                for control in controls:
                    assert (
                        control.winfo_rootx() + control.winfo_width()
                        <= app._root.winfo_rootx() + app._root.winfo_width()
                    ), (scale, width, page, "horizontal overflow")
                    assert (
                        control.winfo_rooty() + control.winfo_height()
                        <= app._root.winfo_rooty() + app._root.winfo_height()
                    ), (scale, height, page, "vertical overflow")
                checks.append(
                    {
                        "scale": scale,
                        "client_pixels": [
                            app._root.winfo_width(),
                            app._root.winfo_height(),
                        ],
                        "page": page,
                    }
                )
            app._view.show_page("总览")
            app._root.update()
            if width == 1280:
                capture(app._root, args.output / f"overview-{scale}.png")
        ctk.set_widget_scaling(1)
        app._root.geometry("1280x720+10+10")
        app._view.show_page("任务中心")
        app._view.render_detail(orders[0])
        app._root.update()
        capture(app._root, args.output / "task-unknown.png")
        from measure_workbench import process_sample

        app._on_window_close()
        app._on_tray_command("show")
        app._root.update()
        resources = [
            {
                "cycle": 0,
                "after_callbacks": len(app._root.tk.call("after", "info")),
                **process_sample(),
            }
        ]
        for i in range(90):
            obs.stage(
                "inquiry", "合成查询", site="hqew", order_ref=orders[i].inquiry_id
            )
            if i % 3 == 0:
                obs.pause("inquiry", "合成网络异常：等待人工核对")
            else:
                obs.enable(quotation=True)
            r, m, _s, _t, _f, ts, ds, plan, site = obs.snapshot()
            snapshot = replace(
                snapshot,
                revision=r,
                modules=m,
                timings=ts,
                cycle_durations=ds,
                planned_check_at=plan,
                recovery_site=site,
                logs=(
                    snapshot.logs
                    + (
                        LogEntry(
                            datetime.now(UTC),
                            "WARNING" if i % 3 == 0 else "INFO",
                            "合成异常等待核对" if i % 3 == 0 else "合成任务恢复",
                        ),
                    )
                )[-300:],
            )
            app._view.render(snapshot)
            app._view.render_detail(orders[i])
            app._view.hide_detail()
            app._on_window_close()
            app._on_tray_command("show")
            app._root.update()
            if i % 30 == 29:
                resources.append(
                    {
                        "cycle": i + 1,
                        "after_callbacks": len(app._root.tk.call("after", "info")),
                        **process_sample(),
                    }
                )
        workloads = []
        for count in (100, 500, 1000):
            snapshot = replace(
                snapshot, revision=snapshot.revision + 1, orders=orders[:count]
            )
            app._view.render(snapshot, force=True)
            app._view.show_page("任务中心")
            started = time.perf_counter()
            app._view.search.insert(0, "DEMO-LONG-COMPONENT-0000")
            app._view._apply_filter()
            assert app._tree.get_children() == (orders[0].inquiry_id,)
            app._view.search.delete(0, "end")
            app._view.filters["source"].set("SHAHAB")
            app._view._apply_filter()
            assert all(
                o.source_sheet == "SHAHAB" for o in app._displayed_orders.values()
            )
            app._view.filters["source"].set("全部来源")
            app._view.filters["status"].set("需核对")
            app._view._apply_filter()
            assert all(
                o.status is OrderStatus.ERROR for o in app._displayed_orders.values()
            )
            app._view.filters["status"].set("全部状态")
            app._view._apply_filter()
            for fraction in (0, 1, 0):
                app._tree.yview_moveto(fraction)
                app._tree.xview_moveto(fraction)
                app._root.update_idletasks()
            app._view.render_detail(orders[count - 1])
            app._root.update()
            app._view.hide_detail()
            assert len(app._tree.get_children()) == min(count, 200)
            workloads.append(
                {
                    "orders": count,
                    "visible_rows": len(app._tree.get_children()),
                    "search_filter_scroll_detail_ms": 1000
                    * (time.perf_counter() - started),
                }
            )
        app._view.show_page("运行记录")
        app._root.update()
        assert "合成任务恢复" in app._view.logs.get("1.0", "end")
        assert not failures, failures
        (args.output / "checks.json").write_text(
            json.dumps(
                {
                    "layout": checks,
                    "cycles": 90,
                    "resources": resources,
                    "table_workloads": workloads,
                    "callbacks_failed": failures,
                    "os_dpi": "NOT_VERIFIED; widget scaling only",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    finally:
        app._on_close()
        for _ in range(50):
            if app._close_finalized:
                break
            app._root.update()
            time.sleep(0.02)


if __name__ == "__main__":
    main()
