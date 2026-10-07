"""Production composition over existing config, browser and notification capability."""

from src.gui.contracts import V12BusinessLabel, V12OrderStateDTO
from src.sheets import WorksheetIdentity
from src.sheets.quotation_input import QuotationInputLocation, QuotationInputUnavailable
from src.workflow.v12_contracts import (
    NotificationCommand,
    NotificationKind,
    NotificationRecipient,
)
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_quotation import QuotationOutcome


def quotation_location(cfg):
    geometry = cfg.get("quotation_input")
    if not isinstance(geometry, dict):
        raise V12Fault(FaultScope.GLOBAL_STOP, "QUOTE_INPUT_CONFIGURATION_REQUIRED")
    try:
        return QuotationInputLocation(
            WorksheetIdentity(cfg["spreadsheet_id"], "报价输入"),
            geometry["input_row"],
            geometry["first_column"],
            geometry["gid"],
        )
    except (KeyError, TypeError, QuotationInputUnavailable):
        raise V12Fault(
            FaultScope.GLOBAL_STOP, "QUOTE_INPUT_CONFIGURATION_REQUIRED"
        ) from None


def quotation_gui(result, key):
    label = {
        QuotationOutcome.NO_RECENT_QUOTE: V12BusinessLabel.QUOTATION_WAITING,
        QuotationOutcome.ROW_FAILED: V12BusinessLabel.QUOTATION_FAILED,
        QuotationOutcome.UPDATED_INSERTED: V12BusinessLabel.QUOTATION_COMPLETED,
        QuotationOutcome.UPDATED_ALREADY_EXISTS: V12BusinessLabel.QUOTATION_COMPLETED,
    }.get(result.outcome)
    if result.row_error_reason is not None and result.row_error_reason.value == "SOURCE_STATUS_NOT_UPDATED":
        label = V12BusinessLabel.QUOTATION_STATUS_PENDING
    waiting = ("已有报价，已跳过" if result.outcome is QuotationOutcome.UPDATED_ALREADY_EXISTS
               else label.value if label else None)
    return V12OrderStateDTO(key, label, None, waiting_label=waiting) if label else None


def notify_quotation(store, result, key, episode, *, at):
    reason = result.row_error_reason.value
    command_id = f"v13:{key}:{episode}:{reason}"
    owner = (NotificationRecipient("owner", "linan229@qq.com"),)
    if store.notification_already_created(
        command_id, result.inquiry_id, NotificationKind.PURCHASE_EXCEPTION, owner
    ):
        return
    action = {
        "SOURCE_STATUS_NOT_UPDATED": "报价脚本已确认成功，但30秒内源表状态仍未变成采购已报价。请人工核对并更新状态；程序不会重复执行更新报价。",
        "UPDATE_RESULT_UNCONFIRMED": "更新报价多次无法确认，请人工检查该订单；程序已跳过并继续其他订单。",
    }.get(reason, "请人工核对该订单及报价输入；处理完成后将源订单改为采购已报价。")
    # Only explicit business identity/location and a closed reason, never provider exceptions.
    body = (
        f"模块：V1.3报价\ninquiry_id：{result.inquiry_id or 'UNKNOWN'}\n"
        f"worksheet：{result.source_worksheet.worksheet if result.source_worksheet else 'UNKNOWN'}\n"
        f"source row（定位信息）：{result.source_row_position}\nMPN：{result.queried_mpn or 'UNKNOWN'}\n"
        f"reason：{reason}\n{action}"
    )
    store.enqueue_notification(
        NotificationCommand(
            command_id,
            result.inquiry_id,
            NotificationKind.PURCHASE_EXCEPTION,
            owner,
            "V1.3报价处理异常",
            body,
            None,
            at,
        )
    )


def notify_runtime_fault(store, key, reason, *, at):
    """Operational notification in the same durable mailbox, with no business identity."""
    import re

    if not re.fullmatch(r"[A-Z_]{1,64}", reason):
        reason = "SHARED_INFRASTRUCTURE_UNAVAILABLE"
    owner = (NotificationRecipient("owner", "linan229@qq.com"),)
    command_id = f"runtime:{key}:{reason}"
    if store.notification_already_created(
        command_id, None, NotificationKind.PURCHASE_EXCEPTION, owner
    ):
        return
    store.enqueue_notification(
        NotificationCommand(
            command_id,
            None,
            NotificationKind.PURCHASE_EXCEPTION,
            owner,
            "询价程序运行异常",
            f"模块：V1.2 / V1.3\nreason：{reason}\n请检查对应网站登录、表格配置或本机运行状态。",
            None,
            at,
        )
    )


def notify_website_issue(store, inquiry_id, site, code, *, mpn=None, at):
    """Closed failure categories only; durable dedup across poll cycles and restarts."""
    # Provider text is used only to choose a fixed reason, never copied into mail/key.
    upper = code.upper()
    reason = (
        "AUTHENTICATION_REQUIRED"
        if any(t in upper for t in ("LOGIN", "CREDENTIAL", "AUTHENTICATION", "VERIFICATION", "CHALLENGE", "SESSION_STALE"))
        else "QUERY_TIMEOUT" if "TIMEOUT" in upper
        else "RESULT_UNAVAILABLE" if any(t in upper for t in ("PARSE", "MISSING", "EMPTY"))
        else "SOURCE_UNAVAILABLE"
    )
    owner = (NotificationRecipient("owner", "linan229@qq.com"),)
    command_id = f"website:{inquiry_id}:{site.value}:{reason}"
    if store.notification_already_created(command_id, inquiry_id, NotificationKind.PURCHASE_EXCEPTION, owner):
        return
    store.enqueue_notification(NotificationCommand(
        command_id, inquiry_id, NotificationKind.PURCHASE_EXCEPTION, owner,
        "询价网站不可用",
        f"网站：{site.value}\ninquiry_id：{inquiry_id}\nMPN：{mpn or 'UNKNOWN'}\nreason：{reason}\n请人工检查网站登录/可用性。",
        None, at,
    ))
