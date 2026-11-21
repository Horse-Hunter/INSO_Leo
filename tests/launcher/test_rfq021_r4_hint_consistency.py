"""RFQ-021-R4 P1: the hint must not advertise what the guard will refuse.

`order_action_hint()` is display-only, but a hint that ignores the scope turns
into a clickable button that the backend rejects -- the Owner sees an action
offered and then refused. The execution guard stays canonical; the hint now
consults the same `_action_in_scope()`.
"""

from __future__ import annotations

from types import SimpleNamespace

from src.launcher.backend import ProductionBackend
from src.launcher.run_scope import parse_run_scope

ORDER = "inq_" + "a" * 24


def scoped(writes: str = ""):
    return parse_run_scope(
        inquiry_ids=ORDER,
        modules="inquiry",
        write_targets=writes,
        approval="OWNER-APPROVED:RFQ-021-R4" if writes else "",
    )


def _idle_backend(tmp_path, *, writes: str = ""):
    backend = ProductionBackend(root=tmp_path, run_scope=scoped(writes), enforce_scope=True)
    # Everything except the new scope check is satisfied, so a False result can
    # only come from the guard this test is about.
    backend._manual_idle = lambda: True
    backend._manual_reader = object()
    backend._store = object()
    backend._view_snapshot = SimpleNamespace(orders=(
        SimpleNamespace(inquiry_id=ORDER, module_id="inquiry", delivery_status="SENT",
                        tp_task_id=None),
    ))
    return backend


def test_hint_follows_the_write_targets_of_the_run(tmp_path):
    read_only = _idle_backend(tmp_path)
    # `edit` writes a Google cell, so a read-only scope must not offer it ...
    assert read_only._action_in_scope("edit") is False
    assert read_only.order_action_hint(ORDER, "edit") is False
    # ... while a purely local action is still offered.
    assert read_only.order_action_hint(ORDER, "resync") is True

    google_ok = _idle_backend(tmp_path, writes="google")
    assert google_ok.order_action_hint(ORDER, "edit") is True


def test_hint_refuses_an_action_outside_its_module(tmp_path):
    backend = _idle_backend(tmp_path, writes="google")
    # Quotation cannot be scoped to one order, so it is refused by module even
    # when the Google target is allowed.
    assert backend._action_in_scope("quotation") is False
    assert backend.order_action_hint(ORDER, "quotation") is False
