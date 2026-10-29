"""Offline observation tests; no sites, credentials or production paths."""

from datetime import UTC, datetime, timedelta
from threading import Event, Thread

import pytest

from src.gui.contracts import (
    Order,
    OrderAlertDTO,
    OrderStatus,
    V12AlertCode,
    V12BusinessLabel,
    V12OrderStateDTO,
    V12ReasonCode,
)
from src.gui.workbench import select_orders
from src.launcher.backend import ProductionBackend
from src.launcher.workbench_snapshot import RuntimeObservation


def test_real_boundaries_keep_tp_active_after_normal_deadline():
    wall = [datetime(2026, 1, 1, tzinfo=UTC)]
    tick = [100.0]
    obs = RuntimeObservation(clock=lambda: wall[0], timer=lambda: tick[0])
    obs.enable(quotation=True, tp=True)
    obs.begin_cycle()
    tick[0] += 12
    obs.stage("inquiry", "六源价格查询", site="findchips", order_ref="synthetic")
    # Wall clock jumps backwards: elapsed must still come from monotonic.
    wall[0] -= timedelta(hours=1)
    tick[0] += 8
    obs.stage("quotation", "检查采购报价", site="INSO")
    tick[0] += 3
    obs.stage("tp", "读取目标价并核验订单")
    snap = obs.snapshot()
    assert snap[4] is None
    assert [m.module_id for m in snap[1] if m.status == "运行中"] == ["tp"]
    assert [(t.stage, t.elapsed_seconds) for t in snap[5]] == [
        ("读取询价与采购状态", 12),
        ("六源价格查询", 8),
        ("检查采购报价", 3),
    ]
    assert dict(snap[6]) == {"inquiry": 20, "quotation": 3, "tp": 0}
    tick[0] += 9
    deadline = wall[0] + timedelta(minutes=15)
    obs.end_cycle(deadline)
    assert obs.snapshot()[4] == wall[0]
    assert dict(obs.snapshot()[6])["tp"] == 9
    assert all(m.next_check_at == deadline for m in obs.snapshot()[1])
    wall[0] += timedelta(minutes=5)
    obs.end_cycle(stopped=True)
    assert obs.snapshot()[4] != wall[0]  # idle Stop cannot rewrite the true round end


def test_disabled_and_paused_are_not_invented_running_and_history_bounded():
    tick = [0.0]
    obs = RuntimeObservation(timer=lambda: tick[0])
    obs.begin_cycle()
    obs.stage("tp", "not authorized")
    assert obs.snapshot()[1][2].status == "未启用"
    obs.pause("inquiry", "合成人工暂停")
    tick[0] += 10
    assert obs.snapshot()[1][0].elapsed_seconds == 10
    obs.begin_cycle()
    assert obs.snapshot()[1][0].status == "已暂停"
    obs.enable(tp=True)
    assert obs.snapshot()[5][-1].stage == "合成人工暂停"
    assert obs.snapshot()[5][-1].elapsed_seconds == 10
    for i in range(300):
        obs.stage("tp", str(i), site="hqew")
        tick[0] += 1
        obs.finish_stage("tp")
    assert len(obs.snapshot()[5]) == 200
    obs.wait("tp", "等待网站重试", site="hqew")
    tick[0] += 4
    obs.finish_stage("tp")
    assert obs.snapshot()[5][-1].elapsed_seconds == 4


def test_snapshot_reads_never_call_database_excel_or_old_status(tmp_path, monkeypatch):
    backend = ProductionBackend(root=tmp_path)
    backend._history = tuple(
        Order(str(i), "DEMO", None, 1, "待验证", None, None, OrderStatus.PENDING)
        for i in range(1100)
    )
    backend._cache_workbench(force=True)
    assert len(backend.get_workbench_snapshot().orders) == 1000
    assert len(backend._view_state_cache) == 1000

    def forbidden(*args, **kwargs):
        raise AssertionError("GUI must not perform local I/O")

    for name in (
        "get_status",
        "get_result_history",
        "get_v12_order_state",
        "_refresh_history",
    ):
        monkeypatch.setattr(backend, name, forbidden)
    for _ in range(2000):
        assert len(backend.get_workbench_snapshot().orders) == 1000
    # Observer display still reflects new real boundary without a cache reload.
    backend._observation.begin_cycle()
    assert backend.get_workbench_snapshot().modules[0].status == "运行中"


def test_local_load_is_one_shot_and_does_not_block_gui_snapshot(tmp_path, monkeypatch):
    entered, release = Event(), Event()
    original = ProductionBackend._refresh_history

    def delayed(self, **kwargs):
        entered.set()
        assert release.wait(5)
        original(self, **kwargs)

    monkeypatch.setattr(ProductionBackend, "_refresh_history", delayed)
    backend = ProductionBackend(root=tmp_path, defer_local_view=True)
    try:
        assert entered.wait(2)
        assert backend.local_view_loading()
        assert backend.get_workbench_snapshot().local_loading
        assert backend._thread is None
        backend.start()
        assert backend._thread is None  # startup local load cannot race business start
    finally:
        release.set()
        backend._local_view_thread.join(5)
    assert not backend._local_view_thread.is_alive()
    assert not backend.local_view_loading()
    assert not backend.get_workbench_snapshot().local_loading


def test_display_failure_does_not_change_business_state(tmp_path, monkeypatch):
    backend = ProductionBackend(root=tmp_path)
    before = backend.get_workbench_snapshot()
    monkeypatch.setattr(
        backend, "get_status", lambda: (_ for _ in ()).throw(ValueError("synthetic"))
    )
    backend._cache_workbench(force=True)
    assert backend.get_workbench_snapshot() == before
    assert not backend._stop.is_set()


def test_gui_pure_reads_do_not_wait_on_sql_business_lock(tmp_path):
    backend = ProductionBackend(root=tmp_path)
    entered, release, returned = Event(), Event(), Event()

    def slow_business():
        with backend._lock:
            entered.set()
            release.wait(5)

    def gui_reads():
        backend.get_workbench_snapshot()
        backend.get_manual_order_result()
        backend.login_all_running()
        backend.get_login_all_report()
        backend.order_mail_running()
        backend.get_order_mail_report()
        backend.get_order_mail_stage()
        returned.set()

    worker, reader = Thread(target=slow_business), Thread(target=gui_reads)
    worker.start()
    try:
        assert entered.wait(2)
        reader.start()
        assert returned.wait(1)
    finally:
        release.set()
        worker.join(5)
        reader.join(5)


@pytest.mark.parametrize(
    "reason,label,alert_type",
    [
        (
            V12ReasonCode.NOTIFICATION_UNKNOWN,
            V12BusinessLabel.PURCHASE_SENT,
            V12AlertCode.NOTIFICATION_FAILED,
        ),
        (
            V12ReasonCode.SAVE_OUTCOME_UNKNOWN,
            V12BusinessLabel.SUBMIT_UNCONFIRMED,
            V12AlertCode.PURCHASE_EXCEPTION,
        ),
        (
            V12ReasonCode.RECONCILIATION_AMBIGUOUS,
            V12BusinessLabel.PURCHASE_EXCEPTION,
            V12AlertCode.PURCHASE_EXCEPTION,
        ),
    ],
)
def test_ordinary_unknown_notification_is_excluded_from_completed_filter(
    tmp_path, monkeypatch, reason, label, alert_type
):
    backend = ProductionBackend(root=tmp_path)
    backend._history = (
        Order(
            "synthetic", "DEMO", None, 1, "待验证", None, None, OrderStatus.COMPLETED
        ),
    )
    alert = OrderAlertDTO(
        "synthetic-alert", alert_type, reason, datetime.now(UTC), True
    )
    dto = V12OrderStateDTO("synthetic", label, alert, (alert,))
    monkeypatch.setattr(backend, "get_v12_order_state", lambda key: dto)
    backend._cache_workbench(force=True)
    orders = backend.get_workbench_snapshot().orders
    assert orders[0].delivery_status == (
        "UNKNOWN" if reason is V12ReasonCode.NOTIFICATION_UNKNOWN else None
    )
    assert orders[0].status is OrderStatus.ERROR
    assert not select_orders(orders, status="已完成")


def test_projection_selects_newest_before_cap_without_per_order_sql(tmp_path):
    from types import SimpleNamespace
    backend = ProductionBackend(root=tmp_path)
    now = datetime(2026, 10, 29, tzinfo=UTC)
    backend._history = tuple(
        Order(str(i), "DEMO", None, 1, "待验证", None, None, OrderStatus.PENDING)
        for i in range(1005)
    )
    items = {str(i): SimpleNamespace(created_at=now+timedelta(seconds=i)) for i in range(1005)}
    backend._cache_workbench(force=True, items=items)
    rows = backend.get_workbench_snapshot().orders
    assert len(rows) == 1000 and rows[0].inquiry_id == "1004" and rows[-1].inquiry_id == "5"
    assert rows[0].received_at == items["1004"].created_at
    # Idle startup uses the same immutable read-only date cache, no worker/store.
    backend._view_intake_times = {key: item.created_at for key, item in items.items()}
    backend._cache_workbench(force=True, items={})
    assert backend.get_workbench_snapshot().orders == rows
