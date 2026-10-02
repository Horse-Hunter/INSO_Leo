from datetime import UTC, datetime
from decimal import Decimal

from src.gui.app import _order_row_style, _v12_status_text
from src.gui.contracts import (
    Order,
    OrderAlertDTO,
    OrderStatus,
    V12AlertCode,
    V12BusinessLabel,
    V12OrderStateDTO,
    V12ReasonCode,
)


def test_latest_active_alert_is_red_status_and_business_label_returns_after_recovery():
    now = datetime(2026, 9, 26, tzinfo=UTC)
    order = Order(
        "inq_test",
        "MPN-1",
        "Brand",
        5,
        "货足",
        Decimal("2.00"),
        Decimal("10.00"),
        OrderStatus.COMPLETED,
        processed_at=now,
    )
    failed = V12OrderStateDTO(
        "inq_test",
        V12BusinessLabel.PROCESSING,
        OrderAlertDTO(
            "alert-1",
            V12AlertCode.NOTIFICATION_FAILED,
            V12ReasonCode.NOTIFICATION_TRANSIENT,
            now,
            True,
        ),
    )
    assert _v12_status_text(failed, order.status.value) == "通知失败"
    assert _order_row_style(order, now, failed) == "error"

    recovered = V12OrderStateDTO("inq_test", V12BusinessLabel.DUPLICATE_ORDER, None)
    assert _v12_status_text(recovered, order.status.value) == "重复订单"


def test_safe_pre_save_success_is_not_displayed_as_sent_or_still_processing():
    from src.gui.contracts import V12EventCode, WorkflowEventDTO

    now = datetime(2026, 10, 2, tzinfo=UTC)
    ready = WorkflowEventDTO("ready", V12EventCode.AI_RECOGNITION_READY, None, now)
    state = V12OrderStateDTO("inq", V12BusinessLabel.PROCESSING, None, event_history=(ready,))
    assert _v12_status_text(state, "部分成功") == "采购草稿校验通过（未保存）"
    started = WorkflowEventDTO("new", V12EventCode.PURCHASE_DRAFT_STARTED, None, now)
    pending = V12OrderStateDTO("inq", V12BusinessLabel.PROCESSING, None, event_history=(ready, started))
    assert _v12_status_text(pending, "部分成功") == "处理中"


def test_purchase_failure_does_not_push_research_sources_below_event_history(monkeypatch):
    from types import SimpleNamespace

    from src.gui import app
    from src.gui.contracts import SourceDetail, V12EventCode, WorkflowEventDTO

    texts = []

    class Widget:
        def __init__(self, *_args, **kwargs):
            if "text" in kwargs:
                texts.append(kwargs["text"])

        def pack(self, **_kwargs):
            pass

    now = datetime(2026, 10, 1, tzinfo=UTC)
    alert = OrderAlertDTO("alert", V12AlertCode.PURCHASE_EXCEPTION,
                         V12ReasonCode.CONTROL_NOT_FOUND, now, True)
    state = V12OrderStateDTO(
        "inq", V12BusinessLabel.PROCESSING, alert,
        event_history=tuple(WorkflowEventDTO(str(i), V12EventCode.AI_RECOGNITION_MISMATCH,
                                           V12ReasonCode.CONTROL_NOT_FOUND, now)
                            for i in range(40)),
    )
    monkeypatch.setattr(app, "ctk", SimpleNamespace(CTkLabel=Widget, CTkFrame=Widget), raising=False)
    view = app.InsoDashboardApp.__new__(app.InsoDashboardApp)
    view._detail_container = SimpleNamespace(winfo_children=list)
    view._backend = SimpleNamespace(get_v12_order_state=lambda _id: state)
    order = Order("inq", "MPN", "Brand", 5, "货少", Decimal(2), Decimal(10),
                  OrderStatus.COMPLETED, sources=(SourceDetail("Findchips", "2.00"),))
    view._render_detail(order)
    assert texts.index("Findchips") < texts.index("流程记录（不影响上方调研结果）")
    assert any("调研结果" in text and "总价" in text for text in texts)
    assert any("采购录单异常" in text for text in texts)
    assert not any("CONTROL_NOT_FOUND" in text or "AI_RECOGNITION_MISMATCH" in text for text in texts)
