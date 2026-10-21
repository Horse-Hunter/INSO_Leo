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
    if (result.outcome is QuotationOutcome.BASELINE_RECORDED
            and result.row_error_reason is not None):
        return V12OrderStateDTO(key, V12BusinessLabel.QUOTATION_STATUS_PENDING, None,
            waiting_label="Google写入结果不确定，已提醒229；后续降价继续检查")
    if result.source_status in {"采购已报价", "已报价给客户"}:
        detail = {
            QuotationOutcome.BASELINE_RECORDED: "首次已记录采购价",
            QuotationOutcome.PRICE_UNCHANGED: "采购价未降低",
            QuotationOutcome.NO_RECENT_QUOTE: "近三天暂无新采购报价",
            QuotationOutcome.UPDATED_INSERTED: "采购报价已更新",
        }.get(result.outcome)
        if detail is not None:
            return V12OrderStateDTO(key, V12BusinessLabel.QUOTATION_COMPLETED, None,
                                   waiting_label=f"{result.source_status}（{detail}）")
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


def notify_refresh_uncertain(store, result, old_price, new_price, *, at):
    """Reuse the durable quotation mailbox and price-transition deduplication."""
    episode = f"price-{format(old_price.normalize(), 'f')}-to-{format(new_price.normalize(), 'f')}"
    notify_quotation(store, result, result.inquiry_id, episode, at=at,
                     old_price=old_price, new_price=new_price)


def notify_quotation(store, result, key, episode, *, at, old_price=None, new_price=None):
    reason = result.row_error_reason.value
    command_id = f"v13:{key}:{episode}:{reason}"
    owner = (NotificationRecipient("owner", "linan229@qq.com"),)
    if store.notification_already_created(
        command_id, result.inquiry_id, NotificationKind.PURCHASE_EXCEPTION, owner
    ):
        return
    if old_price is not None and new_price is not None:
        body = (f"询价：{result.queried_mpn}\n"
            f"位置：{result.source_worksheet.worksheet}，第{result.source_row_position}行\n"
            f"原采购价：{format(old_price, 'f')}元（人民币未税）\n"
            f"新采购价：{format(new_price, 'f')}元（人民币未税）\n"
            "情况：已尝试点击更新报价，Google写入结果不确定，请人工核对。\n"
            f"后续按{format(new_price, 'f')}元比较；本次不重复点击，相同或更高价跳过，再降价时继续更新。")
        store.enqueue_notification(NotificationCommand(command_id, result.inquiry_id,
            NotificationKind.PURCHASE_EXCEPTION, owner,
            f"【INSO】降价更新待核对：{result.queried_mpn}", body, None, at))
        return
    action = {
        "SOURCE_STATUS_NOT_UPDATED": "核对源表状态，确认后改为“采购已报价”；无需重复更新报价。",
        "UPDATE_RESULT_UNCONFIRMED": "本单已跳过，其他订单继续；请核对报价结果后再决定是否重试。",
        "SOURCE_IDENTITY_UNRESOLVED": "核对该行与原订单的型号、数量及品牌是否一致；本行报价已暂停，其他订单继续。不要重发采购单。",
        "SOURCE_IDENTITY_AMBIGUOUS": "源表有多个匹配候选，请核对重复行；本行报价已暂停，其他订单继续。不要重发采购单。",
        "SOURCE_CHANGED": "核对该行型号、数量及品牌的改动；本行报价已暂停，程序不会覆盖人工修改。不要重发采购单。",
    }.get(reason, "核对订单及报价输入，确认报价完成后再更新源表状态。")
    # Only explicit business identity/location and a closed reason, never provider exceptions.
    reason_text = {
        "SOURCE_STATUS_NOT_UPDATED": "报价更新已确认，源表状态未更新。",
        "UPDATE_RESULT_UNCONFIRMED": "报价更新结果无法确认。",
        "SOURCE_IDENTITY_UNRESOLVED": "该行无法与本机原订单安全匹配，未执行报价更新。",
        "SOURCE_IDENTITY_AMBIGUOUS": "该行匹配到多张原订单，未执行报价更新。",
        "SOURCE_CHANGED": "源表关键字段与原订单记录不一致，未执行报价更新。",
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
            ("【INSO】报价暂停：原订单匹配失败"
             if reason in {"SOURCE_IDENTITY_UNRESOLVED", "SOURCE_IDENTITY_AMBIGUOUS", "SOURCE_CHANGED"}
             else "【INSO】报价处理异常"),
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
    sites = {"INSO": "INSO", "GOOGLE": "Google表格", "IC_NET": "IC.net",
             "BROWSER": "Chrome连接", "FX": "汇率网站"}
    waiting = next((label for code, label in sites.items() if reason == code + "_WAITING_RECOVERY"), None)
    prolonged = next((label for code, label in sites.items() if reason == code + "_OUTAGE_THREE_HOURS"), None)
    treatment = {
        "GOOGLE_SHEETS_UNAVAILABLE": "检查VPN网络及Google表格授权，恢复后点击“重新开始询价”。",
        "SHEETS_READ_UNAVAILABLE": "检查VPN及Google表格是否能正常读取，恢复后点击“重新开始询价”。",
        "GOOGLE_READ_RETRY_EXHAUSTED": "本轮已跳过，15分钟后自动再试；恢复后继续原流程，无需手动重启。",
        "SHEETS_SCHEMA_UNAVAILABLE": "核对源表列结构，恢复后点击“重新开始询价”。",
        "SHEETS_WRITE_UNAVAILABLE": "核对Google表格写入权限与网络；先确认对应单元格现状，再恢复程序。",
        "SHEETS_AUTH_UNAVAILABLE": "检查Google表格授权，恢复后继续。",
        "WORKFLOW_LEDGER_UNAVAILABLE": "检查本机订单台账，恢复后继续。",
        "CDP_RECONNECT_EXHAUSTED": "检查程序使用的Chrome是否正常，恢复连接后继续。",
        "INSO_AUTHENTICATION_REQUIRED": "在程序使用的Chrome中完成INSO登录或人工验证后继续。",
        "QUOTE_INPUT_CONFIGURATION_REQUIRED": "核对报价输入配置，修正后继续。",
    }.get(reason, "查看程序订单详情及本机运行状态，确认后继续。")
    if waiting:
        treatment = "程序继续运行，15分钟后检查恢复；出现验证码时请在原Chrome完成。不会自动重复采购提交。"
    elif prolonged:
        treatment = "必要业务操作已连续三小时未恢复，现已停止共享业务；恢复后再启动，先核对未确认订单。"
    store.enqueue_notification(
        NotificationCommand(
            command_id,
            None,
            NotificationKind.PURCHASE_EXCEPTION,
            owner,
            (f"【INSO】{waiting}暂不可用，等待恢复" if waiting else
             f"【INSO】{prolonged}连续三小时未恢复" if prolonged else
             "【INSO】Google表格暂不可用，15分钟后重试"
             if reason == "GOOGLE_READ_RETRY_EXHAUSTED" else "【INSO】运行已停止：Google表格读取失败"
             if reason == "SHEETS_READ_UNAVAILABLE" else "【INSO】询价运行异常"),
            "情况：" + (f"{waiting}必要业务操作暂未成功，程序仍在运行。" if waiting else
                       f"{prolonged}必要业务操作已连续三小时未恢复。" if prolonged else {
                "GOOGLE_SHEETS_UNAVAILABLE": "Google表格读取或授权不可用，询价和采购报价流程已停止。",
                "SHEETS_READ_UNAVAILABLE": "Google表格读取失败，询价和采购报价流程已停止；尚不能确定是网络还是授权问题。",
                "GOOGLE_READ_RETRY_EXHAUSTED": "Google表格连续5次读取未成功，本轮已跳过。",
                "SHEETS_SCHEMA_UNAVAILABLE": "源表列结构未能确认，询价和采购报价流程已停止。",
                "SHEETS_WRITE_UNAVAILABLE": "Google表格写入未能确认，程序已停止。",
                "SHEETS_AUTH_UNAVAILABLE": "Google表格授权不可用。",
                "WORKFLOW_LEDGER_UNAVAILABLE": "本机订单台账不可用。",
                "CDP_RECONNECT_EXHAUSTED": "Chrome连接恢复失败。",
                "INSO_AUTHENTICATION_REQUIRED": "INSO需要登录或人工验证。",
                "QUOTE_INPUT_CONFIGURATION_REQUIRED": "报价输入配置缺失或不明确。",
            }.get(reason, "运行故障，相关业务已暂停；具体原因需查看本机安全日志。")) + f"\n处理：{treatment}\n不要直接重发采购单。",
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
        recipients, "【INSO】采购报价差异", body, None, at,
    ))
