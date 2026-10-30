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
            waiting_label="Google写入结果不确定，待人工核对；原单保护保留，不会自动重做")
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


def notify_quotation(store, result, key, episode, *, at, old_price=None, new_price=None, evidence=None):
    if result.inquiry_id is None or result.row_error_reason.value not in {"UPDATE_RESULT_UNCONFIRMED", "SOURCE_STATUS_NOT_UPDATED"} or evidence is None:
        return
    if result.row_error_reason.value == "UPDATE_RESULT_UNCONFIRMED" and not getattr(result, "effect_uncertain", False):
        return  # A pre-click timeout cannot claim an unknown external write.
    status_pending = result.row_error_reason.value == "SOURCE_STATUS_NOT_UPDATED"
    command = NotificationCommand("review-pending", result.inquiry_id,
        NotificationKind.PURCHASE_EXCEPTION,
        (NotificationRecipient("owner", "linan229@qq.com"),),
        "【需要处理】报价源表状态待核对" if status_pending else "【需要处理】报价写入待人工核对",
        f"型号：{result.queried_mpn or '尚未核实'}\n"
        f"位置：{result.source_worksheet.worksheet if result.source_worksheet else '尚未核实'}，第{result.source_row_position}行\n"
        + ("情况：报价更新已确认，原表状态仍待核对；不要重复更新报价。\n" if status_pending else
         "情况：写入结果待人工核实；原订单被保护，不会自动重做。\n")
        + "处理：请在原Google表格核对报价结果，勿直接重发或重复更新。\n"
        + ("请保持已确认的报价结果，只核对原表状态。" if status_pending else "尚不能确认此次写入成功或失败。"), None, at)
    store.observe_incident(command, evidence, occurrence=evidence["original_event"])


def notify_runtime_fault(store, key, reason, *, at, evidence=None, occurrence=None):
    """Only verified actionable incidents enter the canonical outbox."""
    if evidence is None:
        return
    owner = (NotificationRecipient("owner", "linan229@qq.com"),)
    command = NotificationCommand("review-pending", evidence.get("inquiry_id"),
        NotificationKind.PURCHASE_EXCEPTION, owner,
        "【需要处理】" + evidence["module"] + "业务持续受阻",
        f"故障码：{evidence['reason_code']}\n模块：{evidence['module']}\n"
        f"情况：原程序业务操作尚未恢复，需人工处理。\n"
        f"最后成功：{evidence.get('last_success') or '尚未核实'}\n"
        f"处理：{evidence['action']}\n待核实：{evidence['uncertainty']}", None, at)
    store.observe_incident(command, evidence, occurrence=occurrence or key)


def notify_website_issue(store, inquiry_id, site, code, *, mpn=None, at, evidence=None):
    # A provider timeout or a substring resembling LOGIN is not proof that a
    # human action is necessary. The original owner supplies verified evidence.
    if evidence is not None:
        notify_runtime_fault(store, evidence["incident_key"], code, at=at,
                             evidence=evidence, occurrence=evidence["original_event"])


def notify_quotation_model_difference(store, result, source_model, *, at, evidence=None):
    """Enqueue a durable two-recipient reminder before preparing a differing model.

    Original raw quote identity and exact source B determine dedup; row movement,
    write retries, another poll or process restart never create another command.
    Existing recipient worker owns independent retries, not the quote engine.
    """
    if result.inquiry_id is None or result.quotation is None:
        raise ValueError("model reminder requires a bound quotation")
    if evidence is None:
        return
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
        recipients, "【INSO】采购报价差异", body, None, at, 2, json.dumps(evidence, sort_keys=True),
    ))
