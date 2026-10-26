"""Second review: idle safety and TP hints use synthetic stores/snapshots only."""

from contextlib import closing
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace

import pytest

from src.gui.contracts import Order, OrderStatus, RunState
from src.launcher import backend as launcher
from src.launcher.backend import ProductionBackend
from src.workflow.v12_contracts import DeliveryOutcome
from tests.launcher.test_workbench_review import (
    VirtualCondition,
    VirtualTime,
    virtual_backend,
)
from tests.research.test_tp import NOW
from tests.workflow.test_tp_research import build


@pytest.mark.parametrize("barrier", ["tp", "cleanup", "manual", "queued", "stop", "stopping", "paused"])
def test_future_wait_deadline_never_bypasses_existing_safety_flags(tmp_path, monkeypatch, barrier):
    backend, _ = virtual_backend(tmp_path, monkeypatch)
    backend._store = SimpleNamespace(get_by_inquiry_id=lambda _: object(), all_items=lambda: ())
    backend._manual_reader = object()
    backend._publish_poll_wait(900)
    assert backend.can_order_action("synthetic", "edit")
    if barrier in {"tp", "cleanup"}:
        backend._poll_idle.clear()
    elif barrier == "manual":
        backend._manual_busy = True
    elif barrier == "queued":
        backend._manual_request = ("synthetic", "synthetic", "edit", None, None)
    elif barrier == "stop":
        backend._stop.set()
    else:
        backend._state = RunState.STOPPING_AFTER_CYCLE if barrier == "stopping" else RunState.MODULE_PAUSED
    assert not backend._manual_idle()
    assert not backend.can_order_action("synthetic", "edit")
    assert backend.request_order_action("synthetic", "edit") is not None


def test_wait_publication_lock_delay_does_not_extend_real_deadline(tmp_path, monkeypatch):
    backend, clock = virtual_backend(tmp_path, monkeypatch)
    backend._observation.begin_cycle()
    def forbidden(*_, **__):
        raise AssertionError("wait deadline publication must not scan durable state")

    monkeypatch.setattr(backend, "_notify", forbidden)
    monkeypatch.setattr(backend, "_cache_workbench", forbidden)
    real_lock = backend._lock
    delayed = []

    class DelayedLock:
        def __enter__(self):
            if not delayed:
                clock.tick += 30
                delayed.append(True)
            return real_lock.__enter__()

        def __exit__(self, *args):
            return real_lock.__exit__(*args)

    backend._lock = DelayedLock()
    expected = clock.wall() + timedelta(minutes=15)

    def check():
        assert backend._next_poll_at == expected
        assert backend.get_workbench_snapshot().planned_check_at == expected

    backend._manual_condition = VirtualCondition(clock, check)
    assert backend._wait_between_polls(900) is False
    assert clock.tick == 900 and backend._manual_condition.waited == 870


def prepared_tp_view(tmp_path, monkeypatch, outcome=DeliveryOutcome.SENT):
    cycle, _, _, _, _ = build(tmp_path, (outcome,))
    cycle.run("synthetic", now=NOW)
    row = cycle.store.rows()[0]
    key = row["task_id"]
    from src.workflow.tp_research import load_order

    tp = load_order(row["order_json"])
    identity = SimpleNamespace(worksheet=SimpleNamespace(spreadsheet=tp.spreadsheet, worksheet=tp.sheet),
                               row_position=tp.row)
    item = SimpleNamespace(record_identity=identity)
    backend = ProductionBackend(root=tmp_path)
    backend._store = SimpleNamespace(all_items=lambda: (), get_by_inquiry_id=lambda _: item)
    backend._tp, backend._manual_reader = cycle, object()
    backend._state = RunState.RUNNING
    backend._next_poll_at = NOW + timedelta(minutes=15)
    monkeypatch.setattr(launcher, "utc_now", lambda: NOW)
    ordinary = Order("synthetic-ordinary", tp.mpn, tp.brand, tp.quantity, "待验证", None, None, OrderStatus.PENDING)
    backend._history = (ordinary, replace(ordinary, inquiry_id="unlinked"))
    backend._cache_workbench(force=True, items={ordinary.inquiry_id: item})
    return backend, cycle, key, ordinary, item


@pytest.mark.parametrize("tp_minutes", [0, 5, 10, 20])
def test_real_tp_rerun_permission_stays_available_through_actual_idle_window(tmp_path, monkeypatch, tp_minutes):
    backend, _, key, ordinary, _ = prepared_tp_view(tmp_path, monkeypatch)
    clock = VirtualTime()
    clock.base = NOW
    monkeypatch.setattr(launcher, "monotonic", lambda: clock.tick)
    monkeypatch.setattr(launcher, "utc_now", clock.wall)
    monkeypatch.setattr(backend, "_release_idle_browser", lambda: None)
    backend._poll_idle.clear()
    backend._next_poll_at = None
    clock.tick += tp_minutes * 60
    assert not backend.can_order_action(key, "tp")
    backend._poll_idle.set()  # source/TP and owned-page cleanup complete
    assert not backend.can_order_action(key, "tp")
    start = clock.tick
    checked = []

    def check():
        if clock.tick - start in {0, 300, 600, 899.75}:
            for row_key in (key, ordinary.inquiry_id):
                assert backend.can_order_action(row_key, "tp")  # actual TpStore/SQLite gate
                assert backend.order_action_hint(row_key, "tp")
            checked.append(clock.tick - start)

    backend._manual_condition = VirtualCondition(clock, check)
    assert backend._wait_between_polls(900) is False
    assert checked == [0, 300, 600, 899.75]
    assert backend._manual_condition.waited == 900
    assert not backend.can_order_action(key, "tp")
    assert backend.request_order_action(key, "tp") is not None


@pytest.mark.parametrize("state,delivery,allowed", [
    ("MAIL_QUEUED", "SENT", True),
    ("FAILED", None, True),
    ("FAILED", "PERMANENT_FAILURE", True),
    ("MAIL_QUEUED", "UNKNOWN", False),
    ("MAIL_QUEUED", "SENDING", False),
    ("MAIL_QUEUED", "PENDING", False),
    ("MAIL_QUEUED", "RETRYABLE_FAILURE", False),
    ("RESEARCHING", "SENT", False),
    ("PENDING", None, False),
    ("INVALID", "SENT", False),
])
def test_tp_hint_state_matrix_uses_memory_only(tmp_path, monkeypatch, state, delivery, allowed):
    backend, cycle, key, ordinary, _ = prepared_tp_view(tmp_path, monkeypatch)
    snap = backend._view_snapshot
    backend._view_snapshot = replace(snap, orders=tuple(
        replace(o, business_status=state, delivery_status=delivery) if o.inquiry_id == key else o
        for o in snap.orders))

    def forbidden(*_, **__):
        raise AssertionError("GUI hint queried database/authority")

    monkeypatch.setattr(cycle.store, "get", forbidden)
    monkeypatch.setattr(cycle.store, "delivery", forbidden)
    monkeypatch.setattr(cycle.store, "manual_allowed", forbidden)
    monkeypatch.setattr(backend, "can_order_action", forbidden)
    monkeypatch.setattr(backend, "_tp_key", forbidden)
    assert backend.order_action_hint(key, "tp") is allowed
    assert backend.order_action_hint(ordinary.inquiry_id, "tp") is allowed
    assert not backend.order_action_hint("unlinked", "tp")
    assert not backend.order_action_hint("missing", "tp")
    backend._manual_busy = True
    assert not backend.order_action_hint(key, "tp")


@pytest.mark.parametrize("change", ["model", "quantity", "sheet", "spreadsheet", "row"])
def test_ordinary_tp_link_requires_canonical_identity_and_matching_fields(tmp_path, monkeypatch, change):
    backend, _, _, ordinary, item = prepared_tp_view(tmp_path, monkeypatch)
    if change in {"model", "quantity"}:
        ordinary = replace(ordinary, **{change: "OTHER" if change == "model" else ordinary.quantity + 1})
    else:
        identity = item.record_identity
        item = SimpleNamespace(record_identity=SimpleNamespace(
            worksheet=SimpleNamespace(
                spreadsheet="other" if change == "spreadsheet" else identity.worksheet.spreadsheet,
                worksheet="SHAHAB" if change == "sheet" else identity.worksheet.worksheet),
            row_position=identity.row_position + (change == "row")))
    backend._history = (ordinary,)
    backend._cache_workbench(force=True, items={ordinary.inquiry_id: item})
    assert not backend.order_action_hint(ordinary.inquiry_id, "tp")


@pytest.mark.parametrize("outcome", [DeliveryOutcome.UNKNOWN, DeliveryOutcome.RETRYABLE_FAILURE])
def test_real_tp_pending_delivery_is_not_a_rerun_hint(tmp_path, monkeypatch, outcome):
    backend, _, key, ordinary, _ = prepared_tp_view(tmp_path, monkeypatch, outcome)
    assert not backend.order_action_hint(key, "tp")
    assert not backend.order_action_hint(ordinary.inquiry_id, "tp")
    assert not backend.can_order_action(key, "tp")


def test_stale_sent_tp_hint_cannot_authorize_new_researching_state(tmp_path, monkeypatch):
    backend, cycle, key, ordinary, item = prepared_tp_view(tmp_path, monkeypatch)
    assert backend.order_action_hint(key, "tp") and backend.order_action_hint(ordinary.inquiry_id, "tp")
    assert backend.can_order_action(key, "tp")
    cycle.store.finish(key, "RESEARCHING", NOW)
    assert backend.order_action_hint(key, "tp")  # old snapshot, never a grant
    assert backend.request_order_action(key, "tp") is not None
    assert backend.request_order_action(ordinary.inquiry_id, "tp") is not None
    assert backend._manual_request is None
    backend._cache_workbench(force=True, items={ordinary.inquiry_id: item})
    assert not backend.order_action_hint(key, "tp")


@pytest.mark.parametrize("outcome", ["UNKNOWN", "SENDING"])
def test_stale_sent_hint_still_rechecks_current_recipient_delivery(tmp_path, monkeypatch, outcome):
    backend, cycle, key, ordinary, item = prepared_tp_view(tmp_path, monkeypatch)
    assert backend.order_action_hint(ordinary.inquiry_id, "tp")
    with closing(cycle.store.connect()) as db, db:
        db.execute("UPDATE workflow_v12_notification_recipients SET outcome=?", (outcome,))
    assert backend.order_action_hint(key, "tp")  # unchanged display snapshot
    assert not backend.can_order_action(key, "tp")
    assert backend.request_order_action(ordinary.inquiry_id, "tp") is not None
    assert backend._manual_request is None
    backend._cache_workbench(force=True, items={ordinary.inquiry_id: item})
    assert not backend.order_action_hint(key, "tp")
    assert not backend.order_action_hint(ordinary.inquiry_id, "tp")
