"""Local purchase timestamps and follow-up through the existing durable mailbox."""
from datetime import datetime, time, timedelta, timezone
from hashlib import sha256

from .v12_contracts import (
    EventType,
    NotificationCommand,
    NotificationKind,
    NotificationRecipient,
)
from .v13_quotation import V13Candidate, read_v13_candidates

WORK_ZONE = timezone(timedelta(hours=8), "Asia/Shanghai")
WORK_WINDOWS = ((time(9), time(12, 30)), (time(13, 30), time(18)))
FOLLOW_UP_AFTER = timedelta(hours=3)
RECIPIENTS = (
    NotificationRecipient("owner", "linan229@qq.com"),
    NotificationRecipient("ops", "shawn@inso-hk.com"),
)


def elapsed_working_time(start: datetime, end: datetime) -> timedelta:
    """Intersect real instants with the Owner's weekday windows, including lunch."""
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("working-time endpoints must be timezone-aware")
    start, end = start.astimezone(WORK_ZONE), end.astimezone(WORK_ZONE)
    if end <= start:
        return timedelta()
    total = timedelta()
    day = start.date()
    while day <= end.date():
        if day.weekday() < 5:
            for opening, closing in WORK_WINDOWS:
                lower = max(start, datetime.combine(day, opening, WORK_ZONE))
                upper = min(end, datetime.combine(day, closing, WORK_ZONE))
                if upper > lower:
                    total += upper - lower
        day += timedelta(days=1)
    return total


class PurchaseFollowUp:
    """Observe all current candidates, including durable quotation holds; no CDP/write."""
    def __init__(self, *, reader, workflow_store, v12_store, clock):
        self.reader, self.workflow_store = reader, workflow_store
        self.v12_store, self.clock = v12_store, clock

    def run(self, worksheet):
        candidates = read_v13_candidates(self.reader, worksheet, self.workflow_store)
        now = self.clock()
        enqueued = 0
        for candidate in candidates:
            if not isinstance(candidate, V13Candidate):
                continue  # Never guess which local timestamp an ambiguous row belongs to.
            stamps = [event for event in self.v12_store.event_history(candidate.inquiry_id)
                      if event.event_type is EventType.PURCHASE_STATUS_RECORDED]
            if not stamps:
                continue  # Historical rows remain untimed.
            stamp = max(stamps, key=lambda event: event.occurred_at)
            if elapsed_working_time(stamp.occurred_at, now) <= FOLLOW_UP_AFTER:
                continue
            # Event identity is durable across polls/restart, and changes only on
            # another confirmed status-write episode. Worker owns delivery retries.
            command_id = "purchase-follow-up:" + sha256(stamp.event_id.encode()).hexdigest()
            if self.v12_store.notification_already_created(
                command_id, candidate.inquiry_id, NotificationKind.PURCHASE_FOLLOW_UP, RECIPIENTS,
            ):
                continue
            item = self.workflow_store.get_by_inquiry_id(candidate.inquiry_id)
            body = (
                "该订单发给采购后已超过3个工作小时，源表仍为‘发给采购’，请人工跟进采购报价。\n"
                f"工作时段：周一至周五09:00–12:30、13:30–18:00（北京时间）\n"
                f"订单：{candidate.inquiry_id}\n工作表：{worksheet.worksheet}\n"
                f"当前行：{candidate.source_row_position}\n型号：{candidate.queried_mpn}\n"
                f"品牌：{item.resolved_brand or item.brand}\n数量：{item.quantity}\n"
                f"发给采购时间：{stamp.occurred_at.astimezone(WORK_ZONE).isoformat()}\n"
                "程序不会因此重发采购单或阻止正常报价处理。"
            )
            self.v12_store.enqueue_notification(NotificationCommand(
                command_id, candidate.inquiry_id, NotificationKind.PURCHASE_FOLLOW_UP,
                RECIPIENTS, "采购报价待跟进：超过3个工作小时", body, None, now,
            ))
            enqueued += 1
        return enqueued
