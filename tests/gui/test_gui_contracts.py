from decimal import Decimal
from threading import Thread, get_ident
from typing import get_type_hints

from src.gui.app import InsoDashboardApp
from src.gui.contracts import LogEntry, Order, OrderStatus, SourceDetail
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


def test_close_cancels_after_and_unregisters_before_backend_shutdown():
    events = []

    class _Root:
        def after_cancel(self, callback_id):
            events.append(("cancel", callback_id))

        def destroy(self):
            events.append(("destroy",))

    class _Backend:
        def on_status_change(self, callback):
            events.append(("status_listener", callback))

        def on_log(self, callback):
            events.append(("log_listener", callback))

        def shutdown(self):
            events.append(("shutdown",))

    app = InsoDashboardApp.__new__(InsoDashboardApp)
    app._closing = False
    app._after_id = "after-1"
    app._root = _Root()
    app._backend = _Backend()
    app._on_close()

    assert events == [
        ("cancel", "after-1"),
        ("status_listener", None),
        ("log_listener", None),
        ("shutdown",),
        ("destroy",),
    ]
