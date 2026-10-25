"""Pure local projection, bounded handoff and real synthetic Tk checks."""

import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from customtkinter import CTkLabel

from src.gui.app import InsoDashboardApp
from src.gui.contracts import (
    HealthReport,
    ModuleSnapshot,
    Order,
    OrderStatus,
    RunSession,
    RunState,
    WorkbenchSnapshot,
)
from src.gui.mock_backend import MockBackend
from src.gui.resources import BackendEvent, MainThreadEventQueue
from src.gui.workbench import (
    elapsed,
    order_status,
    scheduling,
    select_orders,
    sort_orders,
)


def snapshot(**kwargs):
    return WorkbenchSnapshot(
        1,
        RunSession(None, RunState.RUNNING, None, None),
        HealthReport((), "未核验"),
        **kwargs,
    )


def order(key="independent-tp-id", **kwargs):
    return Order(
        key,
        "DEMO-MPN",
        "DEMO",
        2,
        "待验证",
        None,
        None,
        OrderStatus.COMPLETED,
        **kwargs,
    )


def test_round_suppresses_early_deadline_and_stop_has_no_countdown():
    now = datetime.now(UTC)
    view = replace(
        snapshot(cycle_started_monotonic=20),
        session=RunSession(
            None, RunState.RUNNING, None, None, next_poll_at=now + timedelta(minutes=15)
        ),
    )
    assert scheduling(view, now=now, tick=110) == "本轮进行中 · 已耗时 01:30"
    view = replace(view, cycle_finished_at=now)
    assert scheduling(view, now=now) == "下次检查 15:00"
    assert (
        scheduling(
            replace(view, session=RunSession(None, RunState.MODULE_PAUSED, None, None))
        )
        == "已暂停 · 请检查异常与通知"
    )
    assert "倒计时" not in scheduling(snapshot())
    assert (
        elapsed(
            ModuleSnapshot("tp", "目标价调研", "等待执行", started_monotonic=0), now=65
        )
        == "00:01:05"
    )


def test_identity_filters_and_unknown_are_not_success():
    tp = order(
        module_id="tp", source_sheet="2026", source_row=43, delivery_status="UNKNOWN"
    )
    ordinary = order(
        "legacy-id", module_id="inquiry", source_sheet="SHAHAB", source_row=44
    )
    assert order_status(tp) == "邮件结果待核对"
    assert select_orders((tp, ordinary), status="已完成") == (ordinary,)
    assert select_orders((tp, ordinary), module="目标价调研", query="mpn") == (tp,)
    assert select_orders((tp, ordinary), source="SHAHAB") == (ordinary,)
    assert tp.inquiry_id != ordinary.inquiry_id  # same MPN never merges identities


def test_sort_missing_price_zero_quantity_and_real_years():
    missing = order("missing")
    low = replace(
        order("low"),
        min_reference_price=Decimal("1.5"),
        quantity=0,
        processed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    high = replace(
        order("high"),
        min_reference_price=Decimal(3),
        processed_at=datetime(2025, 12, 31, tzinfo=UTC),
    )
    assert sort_orders((missing, high, low), "price") == (low, high, missing)
    assert sort_orders((missing, low, high), "price", reverse=True) == (
        high,
        low,
        missing,
    )
    assert sort_orders((missing, high, low), "quantity")[0] == low
    assert sort_orders((missing, low, high), "processed") == (high, low, missing)


def test_event_queue_is_bounded_latest_status_and_exit_not_lost():
    queue = MainThreadEventQueue()
    for i in range(10000):
        queue.publish(BackendEvent("log", i))
        queue.publish(BackendEvent("status", i))
    queue.publish(BackendEvent("tray", "exit"))
    queue.publish(BackendEvent("tray", "show"))
    events = queue.drain()
    assert len(events) == 258
    assert [e.payload for e in events if e.kind == "status"] == [9999]
    assert [e.payload for e in events if e.kind == "tray"] == ["exit"]
    assert not queue.drain()


def test_real_workbench_cached_ticks_filters_details_and_pages():
    # Tk owns process-global native state. Give this extra real-window test a
    # fresh interpreter rather than inheriting other GUI test interpreters.
    code = """
import socket, pytest
def no_network(*args, **kwargs):
    raise AssertionError('SYNTHETIC_GUI_NETWORK_FORBIDDEN')
socket.socket.connect = no_network
from tests.gui.test_workbench import _check_cached_tk_workbench
with pytest.MonkeyPatch.context() as patch:
    _check_cached_tk_workbench(patch)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[2],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout


def _check_cached_tk_workbench(monkeypatch):
    backend = MockBackend()
    orders = tuple(
        order(
            str(i),
            module_id=("inquiry", "quotation", "tp")[i % 3],
            source_sheet="2026",
            source_row=i + 2,
            delivery_status="UNKNOWN" if i == 0 else None,
        )
        for i in range(1000)
    )
    view = replace(
        snapshot(orders=orders), session=RunSession(None, RunState.STOPPED, None, None)
    )
    backend.get_workbench_snapshot = lambda: view
    calls = []
    backend.can_order_action = lambda iid, action: calls.append((iid, action)) or False

    def forbidden(*a, **kw):
        raise AssertionError("cached tick must not query old history/state/status")

    for name in ("get_status", "get_result_history", "get_v12_order_state"):
        monkeypatch.setattr(backend, name, forbidden)
    app = InsoDashboardApp(backend)
    try:
        starts = []
        backend.start = lambda: starts.append(True)
        app._start_on_ready = True
        app._view.show_page("任务中心")
        app._root.update_idletasks()
        assert len(app._tree.get_children()) == 200
        app._tree.selection_set("0")

        def unchanged(*a, **kw):
            raise AssertionError("unchanged tick must not recreate table rows")

        monkeypatch.setattr(app._tree, "insert", unchanged)
        for _ in range(30):
            app._root.after_cancel(app._after_id)
            app._tick_workbench()
        assert app._tree.selection() == ("0",)
        assert starts == [True]
        app._view.render_detail(orders[0])
        detail_text = "\n".join(
            str(w.cget("text"))
            for w in app._detail_container.winfo_children()
            if isinstance(w, CTkLabel)
        )
        assert "库存判断" in detail_text and "预计总价" in detail_text
        assert {a for _, a in calls} == {"purchase", "quotation", "tp", "edit"}
        assert all(iid == "0" for iid, _ in calls)
        count = len(calls)
        app._view.render_detail(orders[0])
        assert len(calls) == count
        for page in app._view.pages * 3:
            app._view.show_page(page)
        app._hidden = True
        monkeypatch.setattr(app._view, "render", unchanged)
        app._root.after_cancel(app._after_id)
        app._tick_workbench()  # no hidden visual repaint
    finally:
        app._view.close()
        app._root.after_cancel(app._after_id)
        app._root.destroy()
        monkeypatch.undo()
        backend.shutdown()
