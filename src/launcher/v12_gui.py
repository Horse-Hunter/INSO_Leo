"""Translate persisted Workflow V1.2 state into the GUI's public DTOs."""

from src.gui.contracts import (
    OrderAlertDTO,
    V12AlertCode,
    V12BusinessLabel,
    V12EventCode,
    V12OrderStateDTO,
    V12ReasonCode,
    WorkflowEventDTO,
)
from src.workflow.v12_store import V12Store


def read_v12_order_state(store: V12Store, inquiry_id: str) -> V12OrderStateDTO:
    summary = store.order_summary(inquiry_id)
    alerts = tuple(
        OrderAlertDTO(
            alert.alert_id,
            V12AlertCode(alert.alert_type.value),
            V12ReasonCode(alert.reason_code.value),
            alert.raised_at,
            alert.active,
        )
        for alert in store.active_alerts(inquiry_id)
    )
    latest = alerts[0] if alerts else None
    waiting_label = None
    failure = store.research_failure_reason(inquiry_id)
    if failure is not None and summary.business_state.value in {"ROUTING", "RESEARCH_FAILED"}:
        waiting_label = ("调研无报价（未发采购）" if failure == "NO_MATCHING_PRODUCT"
                         else "调研异常（未发采购）")
    elif summary.business_state.value == "RESEARCH_RETRY_WAIT":
        waiting_label = "等待重试调研"
    elif store.duplicate_confirmation_pending(inquiry_id):
        waiting_label = "重复查询待确认（未提交）"
    history = tuple(
        WorkflowEventDTO(
            event.event_id,
            V12EventCode(event.event_type.value),
            V12ReasonCode(event.reason_code.value) if event.reason_code else None,
            event.occurred_at,
            recovered=event.event_type.value == "ALERT_RECOVERED",
        )
        for event in store.event_history(inquiry_id)
    )
    return V12OrderStateDTO(
        inquiry_id,
        V12BusinessLabel(summary.business_label.value),
        latest,
        alerts,
        history,
        waiting_label,
    )
