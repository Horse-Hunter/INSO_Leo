"""Pure task-center presentation regression: no windows, browser or network."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace

from src.gui.contracts import Order, OrderStatus
from src.gui.state import newest_orders
from src.gui.workbench import WorkbenchView

NOW = datetime(2026, 10, 29, tzinfo=UTC)


def order(key, **fields):
    return Order(key, key, None, 1, "待验证", None, None, OrderStatus.PENDING, **fields)


def test_intake_not_recent_rerun_defines_new_order_and_unknowns_are_last():
    old = order("old", received_at=NOW-timedelta(days=4), processed_at=NOW+timedelta(days=1))
    new = order("new", received_at=NOW, processed_at=None)
    history = order("legacy", processed_at=NOW+timedelta(days=2))
    tp = order("independent-tp", module_id="tp")
    assert newest_orders((tp, old, history, new)) == (new, old, history, tp)
    assert newest_orders((replace(old, status=OrderStatus.COMPLETED), new))[0] == new


def test_equal_instants_across_timezones_and_missing_dates_are_deterministic():
    a = order("a", received_at=NOW)
    b = order("b", received_at=NOW.astimezone(timezone(timedelta(hours=8))))
    x, y = order("x"), order("y")
    assert newest_orders((y, b, x, a)) == newest_orders((a, x, b, y)) == (a, b, x, y)


class Tree:
    def __init__(self):
        self.rows, self.positions = {}, {}
    def exists(self, key): return key in self.rows
    def insert(self, _parent, _position, *, iid, values, tags): self.rows[iid] = values
    def item(self, key, *, values, tags): self.rows[key] = values
    def delete(self, key): self.rows.pop(key); self.positions.pop(key, None)
    def move(self, key, _parent, position): self.positions[key] = position


def view():
    v = object.__new__(WorkbenchView)
    v.app = SimpleNamespace(_tree=Tree())
    v.orders, v.states, v.page = (), {}, "总览"
    v._row_values, v.filters = {}, {}
    v.search = SimpleNamespace(get=lambda: "")
    v.page_index, v.page_size, v.sort_desc = 0, 2, False
    v.pager_text = object()
    v.configure = lambda *_a, **_k: None
    return v


def shown(v):
    return tuple(sorted(v.app._tree.positions, key=v.app._tree.positions.get))


def test_real_render_filter_pages_refresh_and_manual_heading_sort():
    v = view()
    rows = tuple(order(str(i), received_at=NOW+timedelta(seconds=i)) for i in range(5))
    v.set_orders(rows)
    v.render_orders()
    assert shown(v) == ("4", "3")
    v.page_by(1)
    assert shown(v) == ("2", "1")
    v.page_index = 0
    v.search = SimpleNamespace(get=lambda: "1")
    v.render_orders()
    assert shown(v) == ("1",)
    v.search = SimpleNamespace(get=lambda: "")
    v.sort("model")  # existing user-selected heading still overrides default
    assert shown(v) == ("4", "3")
    v.sort("model")
    assert shown(v) == ("0", "1")
    del v.sort_key
    v.set_orders(tuple(reversed(rows)))
    v.render_orders()
    assert shown(v) == ("4", "3")


def test_sort_before_display_cap_keeps_newest_across_modules():
    rows = tuple(order(str(i), received_at=NOW+timedelta(seconds=i),
                       module_id=("inquiry", "quotation", "tp")[i % 3]) for i in range(1005))
    v = view()
    v.set_orders(rows)
    assert len(v.orders) == 1000
    assert v.orders[0].inquiry_id == "1004"
    assert v.orders[-1].inquiry_id == "5"
