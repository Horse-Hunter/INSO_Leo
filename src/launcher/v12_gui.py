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
    )
