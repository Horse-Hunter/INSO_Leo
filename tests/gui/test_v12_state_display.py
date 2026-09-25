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
