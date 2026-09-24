from decimal import Decimal
from threading import Thread, get_ident
from typing import get_type_hints

from src.gui.app import InsoDashboardApp
from src.gui.contracts import LogEntry, Order, OrderStatus, RunState, SourceDetail
from src.gui.mock_backend import MockBackend
from src.gui.resources import BackendEvent, MainThreadEventQueue
from src.gui.state import make_empty_session, utc_now


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
        self.mutations = []

    def exists(self, iid):
        return iid in self.rows

    def delete(self, iid):
        self.rows.pop(iid)
        self.mutations.append(("delete", iid))

    def item(self, iid, **kwargs):
        self.rows[iid] = kwargs["values"]
        self.mutations.append(("update", iid))

    def insert(self, _parent, _index, *, iid, values, tags):
        self.rows[iid] = values
        self.mutations.append(("insert", iid))


def test_results_are_not_redrawn_when_snapshot_is_unchanged():
    order = Order(
        inquiry_id="inq-1",
        model="ABC-123",
        brand="Acme",
        quantity=2,
        stock_label="待验证",
        min_reference_price=Decimal("1586.74"),
        total_price=Decimal("3173.48"),
        status=OrderStatus.COMPLETED,
        sources=(SourceDetail("INSO", "1800（ABC-123-T）"),),
    )

    class _Backend:
        def get_current_run_results(self):
            return (order,)

    app = InsoDashboardApp.__new__(InsoDashboardApp)
    app._main_thread_id = get_ident()
    app._backend = _Backend()
    app._tree = _Tree()
    app._displayed_orders = {}
    app._refresh_results()
    first_mutations = tuple(app._tree.mutations)
    app._refresh_results()

    assert first_mutations == (("insert", "inq-1"),)
    assert tuple(app._tree.mutations) == first_mutations
    assert app._tree.rows["inq-1"][3] == "待验证"
    assert app._tree.rows["inq-1"][4] == "¥1586.74"


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
