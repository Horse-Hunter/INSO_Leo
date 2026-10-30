"""Composition only; reuse the existing scheduler, browser, outbox and sender."""
from src.gui.contracts import Order, OrderStatus
from src.sheets.tp_brief import BriefReader
from src.workflow.tp_research import TpCycle, TpStore, load_order
from src.workflow.v13_integration import V13HoldStore


def build_tp_cycle(*, path, web, reader, research, outbox, worker, now, prepare,
                   stop_requested, retry_wait):
    V13HoldStore(path).migrate()  # existing nullable-inquiry outbox upgrade
    store = TpStore(path)
    store.migrate()
    outbox.recover_abandoned_notification_attempts(at=now)
    store.recover(now)
    from datetime import UTC, datetime
    return TpCycle(clock=lambda: datetime.now(UTC), store=store, brief=BriefReader(web, retry_wait=retry_wait),
                   reader=reader, research=research, outbox=outbox, worker=worker,
                   prepare=prepare, stop_requested=stop_requested)


def tp_display_orders(cycle):
    if cycle is None:
        return ()
    orders = []
    for row in cycle.store.rows():
        order = load_order(row["order_json"])
        delivery = cycle.store.delivery(row["task_id"])
        # Legacy display DTO field is a UI row key, never a fake persisted inquiry.
        status = (OrderStatus.COMPLETED if delivery == "SENT" else OrderStatus.ERROR
                  if delivery in {"UNKNOWN", "PERMANENT_FAILURE"} or row["state"] == "FAILED"
                  else OrderStatus.PENDING)
        orders.append(Order(row["task_id"], order.mpn, order.brand, order.quantity,
            "待验证", None, None, status, remark=(
                f"TP 专项｜{order.sheet} 第{order.row}行｜{order.target_raw}｜"
                f"{delivery or row['state']}"), source_sheet=order.sheet, source_row=order.row,
                module_id="tp", delivery_status=delivery, business_status=row['state']))
    return tuple(orders)
