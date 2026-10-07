"""Translate persisted Workflow V1.2 state into the GUI's public DTOs."""
import json
import sqlite3
from pathlib import Path

from src.gui.contracts import (
    OrderAlertDTO,
    V12AlertCode,
    V12BusinessLabel,
    V12EventCode,
    V12OrderStateDTO,
    V12ReasonCode,
    WorkflowEventDTO,
)
from src.workflow.v12_contracts import (
    BusinessState,
    PurchaseOutcome,
    business_label_for_state,
    interrupted_business_state,
)
from src.workflow.v12_store import V12Store


def read_startup_interruptions(database_path: Path) -> dict:
    """Idle startup projection, strictly read-only; quarantine writes wait for Start."""
    if not database_path.is_file():
        return {}
    with sqlite3.connect(database_path.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        if connection.execute("PRAGMA user_version").fetchone()[0] == 0:
            return {}  # Existing V1 DB is migrated only through the normal Start boundary.
        rows = connection.execute("SELECT w.inquiry_id,w.mpn_json,w.brand_json,w.quantity_json,w.last_error,"
            "s.business_state,p.outcome,EXISTS(SELECT 1 FROM workflow_v12_events e "
            "WHERE e.inquiry_id=w.inquiry_id AND e.event_type='SAVE_DISPATCH_ARMED') AS armed "
            "FROM workflow_items w LEFT JOIN workflow_v12_inquiry_state s USING(inquiry_id) "
            "LEFT JOIN workflow_v12_purchase_state p USING(inquiry_id)").fetchall()
    result = {}
    for row in rows:
        current = BusinessState(row["business_state"]) if row["business_state"] else None
        state = interrupted_business_state(current,
            PurchaseOutcome(row["outcome"]) if row["outcome"] else None, bool(row["armed"]))
        state = state or current
        label = V12BusinessLabel(business_label_for_state(state).value)
        waiting = "调研无报价（未发采购）" if state is BusinessState.RESEARCH_FAILED and row["last_error"] == "NO_MATCHING_PRODUCT" else label.value
        dto = V12OrderStateDTO(row["inquiry_id"], label, None, waiting_label=waiting)
        result[row["inquiry_id"]] = (dto, json.loads(row["mpn_json"]),
            json.loads(row["brand_json"]), json.loads(row["quantity_json"]))
    return result


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
    if summary.business_state.value in {
        "INTERRUPTED_UNSENT", "INTERRUPTED_POSSIBLY_SENT", "HUMAN_COMPLETED",
        "SOURCE_CHANGED", "SUBMIT_UNCONFIRMED", "STATUS_WRITE_PENDING", "INVALID_INPUT_SKIPPED",
    }:
        waiting_label = summary.business_label.value
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
