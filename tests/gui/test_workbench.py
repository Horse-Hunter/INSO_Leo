"""Pure local projection, bounded handoff and real synthetic Tk checks."""

import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from customtkinter import CTkButton, CTkLabel

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
        [sys.executable, "-X", "utf8", "-c", code],
        cwd=Path(__file__).resolve().parents[2],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout
    print(result.stdout, end="")


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
    orders = (replace(orders[0], min_reference_price=Decimal("12.50"),
                      total_price=Decimal("25.00")),) + orders[1:]
    view = replace(
        snapshot(orders=orders), session=RunSession(None, RunState.STOPPED, None, None)
    )
    backend.get_workbench_snapshot = lambda: view
    calls = []
    backend.order_action_hint = lambda iid, action: calls.append((iid, action)) or False
    backend.can_order_action = lambda *_: (_ for _ in ()).throw(AssertionError("detail queried durable permissions"))

    def forbidden(*a, **kw):
        raise AssertionError("cached tick must not query old history/state/status")

    for name in ("get_status", "get_result_history", "get_v12_order_state"):
        monkeypatch.setattr(backend, name, forbidden)
    app = InsoDashboardApp(backend)
    try:
        starts = []
        def start_after_busy():
            starts.append(True)
            return len(starts) > 1
        backend.start = start_after_busy
        app._start_on_ready = True
        app._view.show_page("任务中心")
        app._root.update_idletasks()
        assert "V1.6" in app._root.title()
        assert app._view.pages == ("总览", "任务中心", "异常与通知", "运行记录", "设置")
        assert tuple(app._view.nav_buttons) == app._view.pages
        assert "调研结果" not in app._view.frames
        displayed = tuple(app._tree.cget("displaycolumns"))
        assert displayed.index("price") < displayed.index("status")
        assert len(app._tree.get_children()) == 200
        assert str(app._tree.set("0", "price")) == "12.50"
        app._tree.selection_set("0")

        def unchanged(*a, **kw):
            raise AssertionError("unchanged tick must not recreate table rows")

        monkeypatch.setattr(app._tree, "insert", unchanged)
        for _ in range(30):
            app._root.after_cancel(app._after_id)
            app._tick_workbench()
        assert app._tree.selection() == ("0",)
        assert starts == [True, True]  # Busy startup remains pending for the next tick.
        app._view.render_detail(orders[0])
        detail_text = "\n".join(
            str(w.cget("text"))
            for w in app._detail_container.winfo_children()
            if isinstance(w, CTkLabel)
        )
        assert "库存判断" in detail_text and "预计总价" in detail_text
        assert "调研结果" in detail_text and "12.50" in detail_text
        assert {a for _, a in calls} == {"purchase", "quotation", "tp", "edit"}
        assert all(iid == "0" for iid, _ in calls)
        detail_widgets = tuple(w.winfo_id() for w in app._detail_container.winfo_children())
        app._view.render_detail(orders[0])
        assert tuple(w.winfo_id() for w in app._detail_container.winfo_children()) == detail_widgets
        # A linked TP changes its delivery while the ordinary selected row stays
        # identical. Pure hints must invalidate detail buttons, without SQL.
        for allowed in (True, False):
            backend.order_action_hint = lambda _key, action, allowed=allowed: action == "tp" and allowed
            app._view.render_detail(orders[1])
            tp_button = next(w for w in app._detail_container.winfo_children()
                             if isinstance(w, CTkButton) and w.cget("text") == "重跑 TP 价格")
            assert tp_button.cget("state") == ("normal" if allowed else "disabled")
        _check_detail_contention(app, backend, orders[0])
        for page in app._view.pages * 3:
            app._view.show_page(page)
        now = datetime(2026, 1, 1, tzinfo=UTC)
        nested_view = replace(view, modules=(
            ModuleSnapshot("inquiry", "询价采购", status="等待执行", stage="订单间安全等待",
                           cycle_started_at=now, cycle_elapsed_seconds=120),
            ModuleSnapshot("quotation", "报价跟进", status="运行中", stage="合成只读查询",
                           cycle_started_at=now+timedelta(seconds=2), cycle_elapsed_seconds=10)))
        app._view.show_page("总览")
        app._view.render(nested_view, force=True)
        assert "订单间安全等待" in app._view.cards["inquiry"][1].cget("text")
        assert "本轮耗时 120 秒" in app._view.cards["inquiry"][1].cget("text")
        assert "本轮耗时 10 秒" in app._view.cards["quotation"][1].cget("text")
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


def _check_detail_contention(app, backend, selected):
    # Earlier assertions build several un-timed detail trees. Drain their idle
    # redraw backlog before measuring this single lock-contended detail update.
    app._root.update()
    import sqlite3
    import tempfile
    from contextlib import closing
    from threading import Event, Thread
    from time import perf_counter, sleep

    from src.launcher.backend import ProductionBackend

    with tempfile.TemporaryDirectory() as folder:
        real = ProductionBackend(root=folder)
        real._state = RunState.RUNNING
        real._next_poll_at = datetime.now(UTC) + timedelta(minutes=15)
        real._manual_reader = object()
        real._view_snapshot = replace(real._view_snapshot, orders=(selected,))
        db = str(Path(folder) / "synthetic.sqlite3")
        with closing(sqlite3.connect(db)) as conn, conn:
            conn.execute("CREATE TABLE synthetic (value TEXT)")

        class SlowStore:
            def get_by_inquiry_id(self, _):
                with closing(sqlite3.connect(db, timeout=2)) as conn:
                    conn.execute("SELECT * FROM synthetic").fetchall()

        real._store = SlowStore()
        entered, release = Event(), Event()

        def busy_database():
            with closing(sqlite3.connect(db)) as conn, conn, real._lock:
                conn.execute("BEGIN EXCLUSIVE")
                entered.set()
                release.wait(10)

        backend.order_action_hint = real.order_action_hint
        backend.can_order_action = real.can_order_action
        # Warm the native widget/layout transition to these display-only hints.
        # The timed render below has a different model and still rebuilds detail
        # while SQL is locked; both the1s bound and forbidden slow-call check stay.
        app._view.render_detail(replace(selected, model="WARMUP"))
        app._root.update()
        worker = Thread(target=busy_database)
        worker.start()
        assert entered.wait(2)
        try:
            for mode in ("SQL_LOCK", "DELAYED_PERMISSION"):
                queried = []
                if mode == "DELAYED_PERMISSION":
                    def slow(*_, queried=queried):
                        queried.append(True)
                        sleep(2)
                        return False
                    backend.can_order_action = slow
                painted = []
                started = perf_counter()
                app._view.render_detail(replace(selected, model=mode))
                app._root.after(0, lambda painted=painted: painted.append(True))
                app._root.update()
                elapsed_ms = (perf_counter() - started) * 1000
                assert painted and elapsed_ms < 1000, (mode, elapsed_ms)
                assert not queried
                print("SYNTHETIC_DETAIL_RESPONSE_MS", mode, round(elapsed_ms, 3))
        finally:
            release.set()
            worker.join(5)
            assert not worker.is_alive()
            real._store = None
            real.shutdown()


def test_compact_order_status_keeps_source_and_unconfirmed_write_visible():
    from src.gui.contracts import V12BusinessLabel, V12OrderStateDTO

    item = order("synthetic-inquiry", business_status="冗长的来源和历史记录")
    fresh = V12OrderStateDTO(item.inquiry_id, V12BusinessLabel.PURCHASE_SENT, None,
        waiting_label="已报价给客户；采购/处理历史：已发采购单",
        source_status="已报价给客户", source_fresh=True, source_verified_at=datetime.now(UTC))
    assert order_status(item, fresh) == "已报价给客户"
    held = replace(fresh, business_label=V12BusinessLabel.INTERRUPTED_POSSIBLY_SENT,
                   waiting_label="已报价给客户；原写入待人工核对，不会自动重做")
    assert order_status(item, held) == "已报价给客户 · 待核对"
    stale = replace(held, source_fresh=False)
    # Owner 2026-11-14: the column must show the sheet's own status. An old read no
    # longer replaces it with a staleness hint; the "待核对" issue stays visible.
    assert order_status(item, stale) == "已报价给客户 · 待核对"
    assert held.waiting_label.endswith("不会自动重做")


def test_task_filters_use_fresh_source_status_and_preserve_holds():
    from src.gui.contracts import V12BusinessLabel, V12OrderStateDTO

    pending = order("pending")
    quoted = order("quoted")
    held = order("held")
    stale = order("stale")
    unproven = order("unproven")
    states = {
        "pending": V12OrderStateDTO("pending", V12BusinessLabel.PURCHASE_SENT, None,
                                    source_status="发给采购", source_fresh=True, source_verified_at=datetime.now(UTC)),
        "quoted": V12OrderStateDTO("quoted", V12BusinessLabel.PURCHASE_SENT, None,
                                   source_status="已报价给客户", source_fresh=True, source_verified_at=datetime.now(UTC)),
        "held": V12OrderStateDTO("held", V12BusinessLabel.INTERRUPTED_POSSIBLY_SENT, None,
                                 source_status="已报价给客户", source_fresh=True, source_verified_at=datetime.now(UTC)),
        "stale": V12OrderStateDTO("stale", V12BusinessLabel.PURCHASE_SENT, None,
                                  source_status="已报价给客户", source_fresh=False),
        "unproven": V12OrderStateDTO("unproven", V12BusinessLabel.HUMAN_COMPLETED, None,
                                     source_status=None, source_link_unproven=True),
    }
    items = (pending, quoted, held, stale, unproven)
    assert select_orders(items, status="待处理", states=states) == (pending,)
    # A calm order's source can be older than 15 minutes between cycles; it is not
    # a review item merely because the last successful read aged. An unproven
    # source link still is.
    assert select_orders(items, status="已完成", states=states) == (quoted, stale)
    assert select_orders(items, status="需核对", states=states) == (held, unproven)
    assert sort_orders(items, "status", states=states)[0] is pending


def test_status_expires_without_snapshot_change_and_preserves_issue(monkeypatch):
    """Expiry must not hide the sheet status or the issue (Owner 2026-11-14)."""
    from src.gui import workbench
    from src.gui.contracts import V12BusinessLabel, V12OrderStateDTO

    now = datetime.now(UTC)
    item = order("synthetic")
    state = V12OrderStateDTO(item.inquiry_id, V12BusinessLabel.DUPLICATE_ORDER, None,
        source_status="未发", source_fresh=True, source_verified_at=now)
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now + timedelta(minutes=16)
    monkeypatch.setattr(workbench, "datetime", Clock)
    assert order_status(item, state) == "未发 · 重复订单"
    assert select_orders((item,), status="需核对", states={item.inquiry_id: state}) == (item,)


def test_unknown_mail_does_not_hide_an_uncertain_purchase_or_quote_write():
    from src.gui.contracts import V12BusinessLabel, V12OrderStateDTO

    item = order("synthetic", delivery_status="UNKNOWN")
    state = V12OrderStateDTO(item.inquiry_id, V12BusinessLabel.INTERRUPTED_POSSIBLY_SENT, None)
    assert order_status(item, state) == "邮件及写入待核对"
    quoted = replace(state, business_label=V12BusinessLabel.PURCHASE_SENT,
                     waiting_label="原报价写入待人工核对，不会自动重做")
    assert order_status(item, quoted) == "邮件及写入待核对"
    mail_only = replace(state, business_label=V12BusinessLabel.PURCHASE_SENT)
    assert order_status(item, mail_only) == "邮件结果待核对"


def test_unknown_mail_does_not_hide_durable_purchase_alert_under_quotation_state():
    from src.gui.contracts import (
        OrderAlertDTO,
        V12AlertCode,
        V12BusinessLabel,
        V12OrderStateDTO,
        V12ReasonCode,
    )

    item = order("synthetic", delivery_status="UNKNOWN")
    alert = OrderAlertDTO("synthetic-alert", V12AlertCode.PURCHASE_EXCEPTION,
                          V12ReasonCode.SAVE_OUTCOME_UNKNOWN, datetime.now(UTC), True)
    state = V12OrderStateDTO(item.inquiry_id, V12BusinessLabel.QUOTATION_COMPLETED,
                             alert, active_alerts=(alert,))
    assert order_status(item, state) == "邮件及写入待核对"
