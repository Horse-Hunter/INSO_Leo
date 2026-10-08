"""GUI handlers submit commands only; no Tk window or external I/O."""
from types import SimpleNamespace

import pytest

from src.gui import app
from src.gui.contracts import Order, OrderStatus


@pytest.mark.parametrize("column,field,value", [("#1", "model", "FIXED"),
    ("#2", "brand", "NEW"), ("#3", "quantity", "11"), ("#4", "importance", "B")])
def test_double_click_edits_only_selected_field(monkeypatch, column, field, value):
    gui = object.__new__(app.InsoDashboardApp)
    gui._root = object()
    gui._tree = SimpleNamespace(identify_row=lambda y: "id", identify_column=lambda x: column)
    gui._displayed_orders = {"id": Order("id", "OLD", "BR", 7, "", None, None, OrderStatus.PENDING, importance="A")}
    calls = []
    gui._backend = SimpleNamespace(can_order_action=lambda *a: True,
        request_order_action=lambda *a, **kw: calls.append((a, kw)))
    monkeypatch.setattr(app.simpledialog, "askstring", lambda *a, **kw: value)
    gui._on_order_edit(SimpleNamespace(x=0, y=0))
    assert calls == [(("id", "edit"), {"field": field, "value": value})]


def test_cancel_editor_never_submits(monkeypatch):
    gui = object.__new__(app.InsoDashboardApp)
    gui._root = object()
    gui._tree = SimpleNamespace(identify_row=lambda y: "id", identify_column=lambda x: "#1")
    gui._displayed_orders = {"id": SimpleNamespace(model="OLD")}
    gui._backend = SimpleNamespace(can_order_action=lambda *a: True,
        request_order_action=lambda *a, **kw: pytest.fail("cancel must not submit"))
    monkeypatch.setattr(app.simpledialog, "askstring", lambda *a, **kw: None)
    gui._on_order_edit(SimpleNamespace(x=0, y=0))


def test_context_menu_uses_backend_eligibility_and_selected_row(monkeypatch):
    gui = object.__new__(app.InsoDashboardApp)
    selected, commands, requests = [], [], []
    gui._tree = SimpleNamespace(identify_row=lambda y: "id", selection_set=selected.append)
    gui._backend = SimpleNamespace(can_order_action=lambda i, a: a == "quotation",
        request_order_action=lambda *a, **kw: requests.append(a))
    class Menu:
        def __init__(self, *a, **kw): pass
        def add_command(self, **kw): commands.append(kw)
        def tk_popup(self, *a): pass
        def grab_release(self): pass
    monkeypatch.setattr(app, "Menu", Menu)
    gui._on_order_context(SimpleNamespace(y=0, x_root=0, y_root=0))
    assert selected == ["id"]
    assert [(c["label"], c["state"]) for c in commands] == [
        ("重跑采购流程", "disabled"), ("重跑报价流程", "normal")]
    commands[1]["command"]()
    assert requests == [("id", "quotation")]
