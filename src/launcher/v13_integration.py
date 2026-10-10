"""Production composition over existing config, browser and notification capability."""

import json
from hashlib import sha256

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
        "SOURCE_STATUS_NOT_UPDATED": "核对源表状态，确认后改为“采购已报价”；无需重复更新报价。",
        "UPDATE_RESULT_UNCONFIRMED": "本单已跳过，其他订单继续；请核对报价结果后再决定是否重试。",
    }.get(reason, "核对订单及报价输入，确认报价完成后再更新源表状态。")
    # Only explicit business identity/location and a closed reason, never provider exceptions.
    reason_text = {
        "SOURCE_STATUS_NOT_UPDATED": "报价更新已确认，源表状态未更新。",
        "UPDATE_RESULT_UNCONFIRMED": "报价更新结果无法确认。",
    }.get(reason, "报价处理未完成。")
    body = (f"型号：{result.queried_mpn or '未能确认'}\n"
        f"位置：{result.source_worksheet.worksheet if result.source_worksheet else '未能确认'}"
        f"，行号{result.source_row_position}（定位参考）\n"
        f"情况：{reason_text}\n处理：{action}")
    store.enqueue_notification(
        NotificationCommand(
            command_id,
            result.inquiry_id,
            NotificationKind.PURCHASE_EXCEPTION,
            owner,
            "【INSO】报价处理异常",
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
    treatment = {
        "GOOGLE_SHEETS_UNAVAILABLE": "检查VPN网络及Google表格授权，恢复后继续。",
        "SHEETS_AUTH_UNAVAILABLE": "检查Google表格授权，恢复后继续。",
        "WORKFLOW_LEDGER_UNAVAILABLE": "检查本机订单台账，恢复后继续。",
        "CDP_RECONNECT_EXHAUSTED": "检查程序使用的Chrome是否正常，恢复连接后继续。",
        "INSO_AUTHENTICATION_REQUIRED": "在程序使用的Chrome中完成INSO登录或人工验证后继续。",
        "QUOTE_INPUT_CONFIGURATION_REQUIRED": "核对报价输入配置，修正后继续。",
    }.get(reason, "查看程序订单详情及本机运行状态，确认后继续。")
    store.enqueue_notification(
        NotificationCommand(
            command_id,
            None,
            NotificationKind.PURCHASE_EXCEPTION,
            owner,
            "【INSO】询价运行异常",
            "情况：" + {
                "GOOGLE_SHEETS_UNAVAILABLE": "Google表格读取或授权不可用。",
                "SHEETS_AUTH_UNAVAILABLE": "Google表格授权不可用。",
                "WORKFLOW_LEDGER_UNAVAILABLE": "本机订单台账不可用。",
                "CDP_RECONNECT_EXHAUSTED": "Chrome连接恢复失败。",
                "INSO_AUTHENTICATION_REQUIRED": "INSO需要登录或人工验证。",
                "QUOTE_INPUT_CONFIGURATION_REQUIRED": "报价输入配置缺失或不明确。",
            }.get(reason, "询价运行出现异常。") + f"\n处理：{treatment}不要直接重发采购单。",
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
        "【INSO】询价网站异常",
        f"网站：{site.value}\n" + (f"型号：{mpn}\n" if mpn else "")
        + "情况：" + {"AUTHENTICATION_REQUIRED": "需要登录或人工验证。",
            "QUERY_TIMEOUT": "查询超时。", "RESULT_UNAVAILABLE": "查询结果未能确认。"
            }.get(reason, "网站暂不可用。") + "\n处理：请人工检查网站登录/可用性。",
        None, at,
    ))


def notify_quotation_model_difference(store, result, source_model, *, at):
    """Enqueue a durable two-recipient reminder before preparing a differing model.

    Original raw quote identity and exact source B determine dedup; row movement,
    write retries, another poll or process restart never create another command.
    Existing recipient worker owns independent retries, not the quote engine.
    """
    if result.inquiry_id is None or result.quotation is None:
        raise ValueError("model reminder requires a bound quotation")
    actual_model = result.quotation.payload[1]
    if actual_model == source_model:
        return
    fingerprint = sha256(json.dumps(
        [source_model, result.quotation.payload], ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    command_id = f"v13:model-difference:{result.inquiry_id}:{fingerprint}"
    recipients = (NotificationRecipient("owner", "linan229@qq.com"),
                  NotificationRecipient("ops", "shawn@inso-hk.com"))
    if store.notification_already_created(
        command_id, result.inquiry_id, NotificationKind.PURCHASE_EXCEPTION, recipients,
    ):
        return
    body = (
        f"原表型号：{source_model}\n报价实际型号：{actual_model}\n"
        f"位置：{result.source_worksheet.worksheet if result.source_worksheet else '未能确认'}"
        f"，行号{result.source_row_position}（定位参考）\n"
        "情况：匹配到的报价型号与原表不同，报价更新尚未确认。\n"
        "处理：请核对型号差异；原表型号保留，实际报价型号会追加到备注。"
    )
    store.enqueue_notification(NotificationCommand(
        command_id, result.inquiry_id, NotificationKind.PURCHASE_EXCEPTION,
        recipients, "【INSO】报价型号差异", body, None, at,
    ))
