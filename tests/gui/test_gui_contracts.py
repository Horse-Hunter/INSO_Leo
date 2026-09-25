from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Thread, get_ident
from typing import get_type_hints

from src.gui.app import (
    _ERROR_BG,
    _ERROR_TEXT,
    _HISTORY_WHITE,
    _RECENT_BLUE,
    _WARNING_BG,
    InsoDashboardApp,
    _countdown_text,
    _order_row_style,
)
from src.gui.contracts import LogEntry, Order, OrderStatus, RunState, SourceDetail
from src.gui.mock_backend import MockBackend
from src.gui.resources import BackendEvent, MainThreadEventQueue
from src.gui.state import make_empty_session, utc_now
from src.launcher.backend import ProductionBackend
from src.research.excel_output import ResearchExcelOutput


def test_mock_amounts_are_decimal_and_stock_is_a_label():
    order_annotations = get_type_hints(Order)
    assert order_annotations["min_reference_price"] == Decimal | None
    assert order_annotations["total_price"] == Decimal | None
    backend = MockBackend()
    try:
        order = backend._generate_order()
        assert isinstance(order.min_reference_price, Decimal)
        assert isinstance(order.total_price, Decimal)
        assert order.stock_label in {"货多", "货少", "待验证"}
        assert all(isinstance(source.display_value, str) for source in order.sources)
    finally:
        backend.shutdown()


def test_source_detail_is_display_only():
    detail = SourceDetail("Findchips", "1513.86（无库存）")
    assert detail.display_value == "1513.86（无库存）"
    assert not hasattr(detail, "unit_price")
    assert not hasattr(detail, "stock")


def test_backend_event_queue_accepts_cross_thread_snapshots():
    event_queue = MainThreadEventQueue()
    event = BackendEvent("log", LogEntry(utc_now(), "INFO", "worker event"))
    thread = Thread(target=lambda: event_queue.publish(event))
    thread.start()
    thread.join()
    assert event_queue.drain() == (event,)
    assert event_queue.drain() == ()


def test_backend_callbacks_only_enqueue_events_from_worker_thread():
    class _Backend:
        def on_status_change(self, callback):
            self.status_callback = callback

        def on_log(self, callback):
            self.log_callback = callback

    app = InsoDashboardApp.__new__(InsoDashboardApp)
    app._events = MainThreadEventQueue()
    app._backend = _Backend()
    app._wire_backend()
    event_data = make_empty_session()
    worker = Thread(target=lambda: app._status_callback(event_data))
    worker.start()
    worker.join()

    assert app._events.drain() == (BackendEvent("status", event_data),)


class _Tree:
    def __init__(self):
        self.rows = {}
        self.tags = {}
        self.mutations = []

    def exists(self, iid):
        return iid in self.rows

    def delete(self, iid):
        self.rows.pop(iid)
        self.tags.pop(iid, None)
        self.mutations.append(("delete", iid))

    def item(self, iid, **kwargs):
        if "values" in kwargs:
            self.rows[iid] = kwargs["values"]
        if "tags" in kwargs:
            self.tags[iid] = kwargs["tags"]
        self.mutations.append(("update" if "values" in kwargs else "tag", iid))

    def insert(self, _parent, _index, *, iid, values, tags):
        self.rows[iid] = values
        self.tags[iid] = tags
        self.mutations.append(("insert", iid))


def test_results_are_not_redrawn_when_snapshot_is_unchanged():
    order = Order(
        inquiry_id="inq-1",
        model="ABC-123",
        brand="Acme",
        quantity=2,
        importance="B",
        stock_label="待验证",
        min_reference_price=Decimal("1586.74"),
        total_price=Decimal("3173.48"),
        status=OrderStatus.COMPLETED,
        sources=(SourceDetail("INSO", "1800（ABC-123-T）"),),
        processed_at=utc_now(),
    )

    class _Backend:
        def get_result_history(self):
            return (order,)

    app = InsoDashboardApp.__new__(InsoDashboardApp)
    app._main_thread_id = get_ident()
    app._backend = _Backend()
    app._tree = _Tree()
    app._displayed_orders = {}
    app._displayed_order_styles = {}
    app._displayed_order_ids = ()
    app._refresh_results()
    first_mutations = tuple(app._tree.mutations)
    app._refresh_results()

    assert first_mutations == (("insert", "inq-1"),)
    assert tuple(app._tree.mutations) == first_mutations
    assert app._tree.rows["inq-1"][3] == "B"
    assert app._tree.rows["inq-1"][4] == "待验证"
    assert app._tree.rows["inq-1"][5] == "¥1586.74"
    assert app._tree.tags["inq-1"] == ("recent",)
    assert _RECENT_BLUE == "#93C5FD"
    assert _HISTORY_WHITE == "#FFFFFF"
    assert _WARNING_BG != _ERROR_BG


def test_unchanged_history_order_expires_to_legacy_without_excel_reload(
    tmp_path, monkeypatch
):
    processed_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    path = tmp_path / "history.xlsx"
    ResearchExcelOutput(path).upsert(
        "inq-aging",
        importance_raw=None,
        mpn="ABC-123",
        quantity=2,
        research_status="SUCCESS",
        processed_at=processed_at,
    )
    backend = ProductionBackend(
        config_path=tmp_path / "missing-research.json",
        production_config_path=tmp_path / "missing-production.json",
    )
    backend._excel = path
    reads = 0
    read_history = ResearchExcelOutput.read_history

    def count_reads(self):
        nonlocal reads
        reads += 1
        return read_history(self)

    monkeypatch.setattr(ResearchExcelOutput, "read_history", count_reads)
    backend._refresh_history(force=True)
    original_snapshot = backend.get_result_history()
    assert reads == 1

    app = InsoDashboardApp.__new__(InsoDashboardApp)
    app._main_thread_id = get_ident()
    app._backend = backend
    app._tree = _Tree()
    app._displayed_orders = {}
    app._displayed_order_styles = {}
    app._displayed_order_ids = ()
    row_values: dict[str, tuple[object, ...]] = {}

    app._refresh_results(now=processed_at + timedelta(hours=23, minutes=59))
    row_values["recent"] = app._tree.rows["inq-aging"]
    assert app._tree.tags["inq-aging"] == ("recent",)

    app._refresh_results(now=processed_at + timedelta(hours=24, minutes=1))

    assert backend.get_result_history() == original_snapshot
    assert reads == 1
    assert app._tree.tags["inq-aging"] == ("legacy",)
    assert app._tree.rows["inq-aging"] == row_values["recent"]
    assert app._tree.mutations == [
        ("insert", "inq-aging"),
        ("tag", "inq-aging"),
    ]


def test_history_row_color_window_and_warning_override():
    now = datetime(2026, 5, 1, tzinfo=timezone.utc)
    base = Order("inq", "MPN", None, 1, "货多", None, None, OrderStatus.COMPLETED)
    assert _order_row_style(base, now) == "legacy"
    assert _order_row_style(
        replace(base, processed_at=now - timedelta(hours=24)), now
    ) == "recent"
    assert _order_row_style(
        replace(base, processed_at=now - timedelta(hours=24, seconds=1)), now
    ) == "legacy"
    exception_order = Order(
        "inq", "MPN", None, 1, "货多", None, None, OrderStatus.ERROR,
        processed_at=now,
    )
    partial = Order(
        "inq", "MPN", None, 1, "货多", None, None, OrderStatus.PARTIAL,
        processed_at=now,
    )
    assert _order_row_style(exception_order, now) == "error"
    assert _order_row_style(partial, now) == "recent"
    error = replace(base, status=OrderStatus.ERROR, processed_at=now)
    assert _order_row_style(error, now) == "error"
    assert error.status.value == "异常"
    assert _ERROR_TEXT == "#B91C1C"


def test_countdown_uses_backend_deadline_and_stopped_states_are_zero():
    from src.gui.contracts import RunSession

    now = datetime(2026, 5, 1, tzinfo=timezone.utc)
    running = RunSession(None, RunState.RUNNING, None, None, next_poll_at=now + timedelta(minutes=14, seconds=59))
    reset_after_poll = RunSession(None, RunState.RUNNING, None, None, next_poll_at=now + timedelta(minutes=15))
    first_poll = RunSession(None, RunState.RUNNING, None, None)
    stopping = RunSession(None, RunState.STOPPING_AFTER_CYCLE, None, None, next_poll_at=now + timedelta(minutes=1))
    stopped = RunSession(None, RunState.STOPPED, None, None)
    assert _countdown_text(running, now) == "14:59"
    assert _countdown_text(reset_after_poll, now) == "15:00"
    assert _countdown_text(reset_after_poll, now + timedelta(seconds=1)) == "14:59"
    assert _countdown_text(first_poll, now) == "即将轮询"
    assert _countdown_text(stopping, now) == "00:00"
    assert _countdown_text(stopped, now) == "00:00"


def test_stopping_state_keeps_action_disabled_until_backend_stopped():
    from src.gui.contracts import HealthReport, RunSession

    class _Widget:
        def __init__(self):
            self.values = {}

        def configure(self, **kwargs):
            self.values.update(kwargs)

    class _Backend:
        def get_health(self):
            return HealthReport((), "正常")

    app = InsoDashboardApp.__new__(InsoDashboardApp)
    app._main_thread_id = get_ident()
    app._status_badge = _Widget()
    app._action_button = _Widget()
    app._run_info_labels = {key: _Widget() for key in (
        "本轮发现订单", "已完成", "正在处理", "下轮询价倒计时"
    )}
    app._health_labels = {}
    app._backend = _Backend()
    app._refresh_results = lambda: None

    app._update_status(RunSession(None, RunState.STOPPING_AFTER_CYCLE, None, None))
    assert app._action_button.values == {
        "text": "本轮订单处理中，正在安全结束…",
        "fg_color": "#6B7280",
        "state": "disabled",
    }
    assert app._run_info_labels["下轮询价倒计时"].values["text"] == "00:00"

    app._update_status(RunSession(None, RunState.STOPPED, None, None))
    assert app._action_button.values["text"] == "开始询价"
    assert app._action_button.values["state"] == "normal"


def test_stop_button_requests_backend_and_applies_stopping_snapshot_immediately():
    from src.gui.contracts import RunSession

    class _Backend:
        def __init__(self):
            self.stop_calls = 0

        def request_stop_after_cycle(self):
            self.stop_calls += 1

        def get_status(self):
            return RunSession(None, RunState.STOPPING_AFTER_CYCLE, None, None)

    backend = _Backend()
    app = InsoDashboardApp.__new__(InsoDashboardApp)
    app._backend = backend
    app._status = RunSession(None, RunState.RUNNING, None, None)
    applied = []
    app._update_status = applied.append
    app._on_action()
    assert backend.stop_calls == 1
    assert applied == [backend.get_status()]


class _CloseRoot:
    def __init__(self, events):
        self.events = events
        self.callbacks = {}
        self.next_id = 0

    def after_cancel(self, callback_id):
        self.events.append(("cancel", callback_id))
        self.callbacks.pop(callback_id, None)

    def after(self, _delay, callback):
        self.next_id += 1
        callback_id = f"close-{self.next_id}"
        self.callbacks[callback_id] = callback
        self.events.append(("after", callback_id))
        return callback_id

    def run_next(self):
        callback_id, callback = next(iter(self.callbacks.items()))
        self.callbacks.pop(callback_id)
        callback()

    def destroy(self):
        self.events.append(("destroy",))


class _CloseWidget:
    def __init__(self, events, name):
        self.events, self.name = events, name

    def configure(self, **kwargs):
        self.events.append((self.name, kwargs))


class _CloseBackend:
    def __init__(self, events, state, due=0, worker_state="stopped"):
        self.events = events
        self.state = state
        self.due = due
        self.worker_state = worker_state
        self.stop_requests = 0

    def get_status(self):
        from src.gui.contracts import RunSession

        return RunSession(None, self.state, None, None)

    def get_diagnostics(self):
        from src.gui.contracts import DiagnosticSnapshot

        return DiagnosticSnapshot(None, 0, 0, self.worker_state, None)

    def request_stop_after_cycle(self):
        self.stop_requests += 1
        self.state = RunState.STOPPING_AFTER_CYCLE
        self.events.append(("stop_after_cycle",))

    def finish_one_due_item(self):
        assert self.due > 0
        self.due -= 1
        self.events.append(("due_completed", self.due))
        if self.due == 0:
            self.state = RunState.STOPPED

    def on_status_change(self, callback):
        self.events.append(("status_listener", callback))

    def on_log(self, callback):
        self.events.append(("log_listener", callback))

    def shutdown(self):
        assert self.due == 0
        assert self.worker_state == "stopped"
        self.events.append(("shutdown",))


def _close_test_app(backend, events):
    app = InsoDashboardApp.__new__(InsoDashboardApp)
    app._closing = False
    app._close_finalized = False
    app._after_id = "tick-1"
    app._close_after_id = None
    app._root = _CloseRoot(events)
    app._backend = backend
    app._status_badge = _CloseWidget(events, "badge")
    app._action_button = _CloseWidget(events, "action")
    app._main_thread_id = get_ident()
    return app


def test_close_running_drains_cycle_without_blocking_and_waits_for_threads():
    events = []
    backend = _CloseBackend(events, RunState.RUNNING, due=3, worker_state="running")
    app = _close_test_app(backend, events)

    app._on_close()

    assert backend.stop_requests == 1
    assert events[0] == ("cancel", "tick-1")
    assert not any(event[0] == "destroy" for event in events)
    assert not any(event[0] == "shutdown" for event in events)
    assert events[-1][0] == "after"

    # Each callback represents one Tk after() check while the active cycle drains.
    while backend.due:
        backend.finish_one_due_item()
        app._root.run_next()
        assert not any(event[0] == "destroy" for event in events)
        assert not any(event[0] == "shutdown" for event in events)

    # Workflow says STOPPED before the parent launcher thread has exited.
    app._root.run_next()
    assert not any(event[0] == "destroy" for event in events)

    backend.worker_state = "stopped"
    events.append(("worker_threads_exited",))
    app._root.run_next()
    assert events[-2:] == [("shutdown",), ("destroy",)]
    assert events.index(("worker_threads_exited",)) < events.index(("destroy",))
    assert backend.stop_requests == 1


def test_close_stopped_backend_exits_immediately():
    events = []
    backend = _CloseBackend(events, RunState.STOPPED)
    app = _close_test_app(backend, events)

    app._on_close()

    assert backend.stop_requests == 0
    assert events[-2:] == [("shutdown",), ("destroy",)]
    assert app._root.callbacks == {}


def test_close_cancels_after_and_unregisters_before_backend_shutdown():
    events = []
    backend = _CloseBackend(events, RunState.STOPPED)
    app = _close_test_app(backend, events)

    app._on_close()

    assert events == [
        ("cancel", "tick-1"),
        ("badge", {"text": "正在退出", "fg_color": "#F59E0B"}),
        ("action", {"text": "正在退出", "fg_color": "#6B7280", "state": "disabled"}),
        ("status_listener", None),
        ("log_listener", None),
        ("shutdown",),
        ("destroy",),
    ]
