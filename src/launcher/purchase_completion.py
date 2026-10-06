"""Completion side effects, separate from irreversible INSO dispatch."""
from src.sheets.purchase_status import write_purchase_status_safely
from src.workflow.v12_contracts import (
    BusinessState,
    NotificationCommand,
    NotificationKind,
    NotificationRecipient,
    PurchaseOutcome,
)

OWNER = NotificationRecipient("owner", "linan229@qq.com")


class PurchaseCompletionActions:
    def __init__(self, *, workflow_store, v12_store, reader, writer_factory):
        self.workflow_store = workflow_store
        self.v12_store = v12_store
        self.reader = reader
        self.writer_factory = writer_factory
        self._settled_status_ids: set[str] = set()

    def process(self, result, *, at):
        item = self.workflow_store.get_by_inquiry_id(result.inquiry_id)
        # Durable success, not merely the click or Research COMPLETED.
        if result.purchase_outcome is PurchaseOutcome.SAVED:
            if self.v12_store.purchase_state(item.inquiry_id) is not PurchaseOutcome.SAVED:
                raise ValueError("purchase success is not durable")
            self._write_back(item, at=at)
            return
        if result.business_state is BusinessState.PURCHASE_EXCEPTION:
            code = next((e.reason_code.value for e in reversed(self.v12_store.event_history(item.inquiry_id))
                         if e.reason_code is not None), "PURCHASE_EXCEPTION")
            self.notify(item.inquiry_id, "PURCHASE", code, at=at)
        elif item.status.value in {"FAILED", "MANUAL_REVIEW"} or result.waiting_reason == "RESEARCH_RETRY_WAIT":
            self.notify(item.inquiry_id, "RESEARCH", item.last_error or "RESEARCH_FAILED", at=at)
        elif result.waiting_reason == "DUPLICATE_CONFIRMATION_REQUIRED":
            self.notify(item.inquiry_id, "DUPLICATE_CHECK", "DUPLICATE_LOOKUP_UNAVAILABLE", at=at)

    def _write_back(self, item, *, at):
        if item.inquiry_id in self._settled_status_ids:
            return
        try:
            write_purchase_status_safely(self.reader, self.writer_factory(), item.record_identity)
            self._settled_status_ids.add(item.inquiry_id)
        except Exception as exc:  # noqa: BLE001 - retry only status, never purchase
            self.notify(item.inquiry_id, "SHEETS_WRITE_BACK", type(exc).__name__, at=at)

    def retry_saved_statuses(self, *, at):
        for item in self.workflow_store.all_items():
            if item.inquiry_id in self._settled_status_ids:
                continue
            try:
                saved = self.v12_store.purchase_state(item.inquiry_id) is PurchaseOutcome.SAVED
            except KeyError:
                continue
            if saved:
                self._write_back(item, at=at)

    def notify(self, inquiry_id, phase, reason, *, at):
        command_id = f"purchase-exception:{inquiry_id}:{phase}:{reason}"
        if self.v12_store.notification_already_created(
            command_id, inquiry_id, NotificationKind.PURCHASE_EXCEPTION, (OWNER,),
        ):
            return
        item = self.workflow_store.get_by_inquiry_id(inquiry_id)
        try:
            outcome = self.v12_store.purchase_state(inquiry_id)
        except KeyError:
            outcome = None
        uncertain = outcome in {
            PurchaseOutcome.UNKNOWN_WRITE_OUTCOME, PurchaseOutcome.MANUAL_REVIEW,
            PurchaseOutcome.READ_ONLY_RECONCILIATION_REQUIRED,
        }
        explanation = {
            "SHEETS_WRITE_BACK": "采购单已确认提交，但表格状态写回失败。不要重发采购单。",
            "RESEARCH": "调研异常，未完成采购提交。",
            "DUPLICATE_CHECK": "重复订单查询无法确认，采购提交未继续。",
            "SESSION": "网站登录不可用，订单处理已停止。",
            "PURCHASE": ("提交结果无法确认，可能已经发送。请查看 INSO，禁止直接重跑。"
                         if uncertain else "采购录单或校验失败，未完成采购提交。"),
        }[phase]
        reason_text = {
            "CONTROL_NOT_FOUND": "采购页面控件或 AI 结果未就绪，未能继续录单。",
            "AI_RECOGNITION_MISMATCH": "AI 录单的型号、品牌或数量与订单不符。",
            "RECONCILIATION_UNREADABLE": "无法读取并确认 INSO 订单记录。",
            "SAVE_OUTCOME_UNKNOWN": "提交后的记录未能确认，禁止直接重发。",
            "DUPLICATE_LOOKUP_UNAVAILABLE": "七天重复订单历史查询不可用。",
            "GoogleSheetsAuthorizationError": "Google 写入授权不可用，请检查原授权；程序不会重复弹出授权。",
            "SheetRecordConflict": "表格行移动、内容/状态变化或多个候选，已阻止写错行。",
            "GoogleSheetsReadError": "Google 表格重新读取或写回确认失败。",
            "GoogleSheetsWriteError": "Google 表格状态更新失败。",
        }.get(reason, "该阶段处理失败，请根据订单识别码查看程序订单详情。")
        body = (f"{explanation}\n订单识别码：{inquiry_id}\n型号：{item.mpn}\n"
                f"品牌：{item.resolved_brand or item.brand}\n数量：{item.quantity}\n"
                f"工作表：{item.record_identity.worksheet.worksheet}\n"
                f"原行号：{item.record_identity.row_position}\n"
                f"失败阶段：{phase}\n具体情况：{reason_text}\n原因代码：{reason}")
        self.v12_store.enqueue_notification(NotificationCommand(
            command_id=command_id,
            inquiry_id=inquiry_id, kind=NotificationKind.PURCHASE_EXCEPTION,
            recipients=(OWNER,), subject=f"【INSO】订单处理异常：{item.mpn}",
            text_body=body, html_body=None, created_at=at,
        ))
