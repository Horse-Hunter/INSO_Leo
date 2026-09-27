"""One-run, read-only V1.2 Phase A discovery for the Owner's Chrome session.

Run only from the normal Owner Windows session. It uses the configured Chrome
profile and existing lease/bootstrap code, never reads or writes credentials,
and writes a schema-only report under ignored runtime evidence.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from src.core.app_paths import resolve_app_path, runtime_config_path
from src.inso.duplicate_history import (
    DETAIL_BILL_ID_SELECTOR,
    DETAIL_LINK_CALL,
    DETAIL_LINK_SELECTOR_TEMPLATE,
    RESULT_ROW_SELECTOR,
    DuplicateHistoryFailure,
    InsoDuplicateHistoryError,
    PlaywrightDuplicateHistoryPage,
)
from src.launcher.browser_bootstrap import (
    BrowserBootstrapError,
    BrowserHandle,
    acquire_cdp_browser,
)
from src.launcher.inso_session import attach_inso_research_session
from src.research.runtime import ResearchRuntimeConfigError, load_runtime_config

_REPORT_RELATIVE_PATH = Path("runtime/evidence/v12-phase-a-final/report.json")
_TARGET_MPN = "LM358"  # Public commodity part; never included in the report.
_SAFE_SCHEMA_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_SENSITIVE_SCHEMA_KEY = re.compile(
    r"password|passwd|secret|token|cookie|authorization|email|phone|address",
    re.IGNORECASE,
)
_CREATOR_NAMES = frozenset(
    {
        "制单人",
        "创建人",
        "创建用户",
        "creator",
        "createuser",
        "adduser",
        "adduserid",
        "userid",
        "entryuser",
    }
)
_SAFE_LABELS = frozenset(
    {
        "型号",
        "品牌",
        "数量",
        "报价",
        "报价币种",
        "制单人",
        "创建人",
        "创建用户",
        "采购人员",
        "业务员",
    }
)
_WRITE_WORDS = re.compile(
    r"\b(fetch|XMLHttpRequest|axios|bill_save|save_and_send)\b|"
    r"\.(?:ajax|get|post)\s*\(|form\.submit|submit\s*\(",
    re.IGNORECASE,
)
_SAFE_BLANK_FORM_BACK = re.compile(
    r"^function\s+goback\s*\(\s*\)\s*\{\s*"
    r"parent\.main_alertbox_close\(\s*(['\"])alert_enquiry\1\s*\)\s*;?\s*\}$",
    re.DOTALL,
)
_CURRENCY_DISPLAY = frozenset(
    {"CNY", "RMB", "人民币", "USD", "美元", "HKD", "港币", "HKD港币", "CNY人民币"}
)


def _empty_report() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "phase": "V1.2_PHASE_A_FINAL",
        "generated_at": datetime.now(UTC).isoformat(),
        "side_effects": {
            "save": False,
            "send": False,
            "smtp": False,
            "sheets_write": False,
        },
        "browser": {
            "channel": "chrome",
            "cdp": "UNKNOWN",
            "context_count": None,
            "shell_frame_count": 0,
            "existing_verified_shell_pages": 0,
            "login_state": "UNKNOWN",
        },
        "query": {
            "status": "UNKNOWN",
            "exact_request_matched": False,
            "response_schema_fields": [],
            "response_rows": [],
            "grid_columns": [],
            "billid_identity": "UNKNOWN",
            "grid_detail_identity": "UNKNOWN",
            "detail_readback_fields": [],
        },
        "creator": {"status": "UNKNOWN", "field": None},
        "inso_quote": {
            "status": "UNKNOWN",
            "field": None,
            "currency_field": None,
            "decimal_readable": None,
        },
        "history_tie_break": "AMBIGUOUS",
        "ai": {
            "panel": "UNKNOWN",
            "recognition_executed": False,
            "recognition_readback": "UNKNOWN",
            "safe_to_execute_recognition": False,
            "input_candidates": [],
            "recognition_selector": None,
            "ready_signal": "UNKNOWN",
            "result_fields": [],
            "recognition_handler_present": False,
            "recognition_handler_direct_save_call_absent": False,
            "callback_fields": [],
        },
        "parent_writer": {"status": "UNKNOWN", "fields": []},
        "save": {
            "button_semantics": "UNKNOWN",
            "save_and_send_semantics": "UNKNOWN",
            "send_semantics": "UNKNOWN",
            "success_billid_contract": "UNKNOWN",
            "handler_contract": "UNKNOWN",
            "reconciliation": "UNKNOWN",
            "save_and_send_hard_forbidden": True,
        },
        "reason_codes": [],
    }


def _safe_keys(value: object) -> list[str]:
    if not isinstance(value, dict):
        return []
    return sorted(
        key
        for key in value
        if isinstance(key, str)
        and _SAFE_SCHEMA_KEY.fullmatch(key)
        and not _SENSITIVE_SCHEMA_KEY.search(key)
    )


def _schema_summary(payload: object) -> tuple[list[str], list[dict[str, Any]]]:
    """Return key names and array-row shapes only; never return response values."""

    top_level = _safe_keys(payload)
    row_shapes: list[dict[str, Any]] = []

    def visit(value: object, path: str, depth: int) -> None:
        if depth > 3:
            return
        if isinstance(value, list):
            dict_rows = [row for row in value if isinstance(row, dict)]
            if dict_rows:
                row_shapes.append(
                    {
                        "path": path,
                        "fields": _safe_keys(dict_rows[0]),
                    }
                )
            return
        if isinstance(value, dict):
            for key, child in value.items():
                if isinstance(key, str) and _SAFE_SCHEMA_KEY.fullmatch(key):
                    visit(child, f"{path}.{key}" if path else key, depth + 1)

    visit(payload, "", 0)
    return top_level, row_shapes


def _field_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _confirmed_duplicate_fields(
    row_fields: set[str],
    columns: list[dict[str, str]],
    detail_fields: list[dict[str, str]],
) -> tuple[str | None, str | None, str | None]:
    """Confirm fields only when response, grid mapping, and detail agree."""

    column_map = {_field_key(item["field"]): item["label"] for item in columns}
    detail_map = {_field_key(item["field"]): item["label"] for item in detail_fields}
    schema_map = {_field_key(key): key for key in row_fields}

    creator_matches = []
    for normalized, key in schema_map.items():
        if normalized in {"username", "ownerid", "username_text", "ownerid_text"}:
            continue
        if normalized not in {_field_key(name) for name in _CREATOR_NAMES}:
            continue
        if column_map.get(normalized) in {
            "制单人",
            "创建人",
            "创建用户",
        } and detail_map.get(normalized) in {"制单人", "创建人", "创建用户"}:
            creator_matches.append(key)
    creator = creator_matches[0] if len(creator_matches) == 1 else None

    price_key = schema_map.get("offerprice")
    currency_key = schema_map.get("offercurrencyid")
    quote = (
        price_key
        if price_key
        and column_map.get("offerprice") == "报价"
        and detail_map.get("offerprice") == "报价"
        else None
    )
    currency_detail = next(
        (
            item
            for item in detail_fields
            if _field_key(item["field"]) == "offercurrencyid"
        ),
        None,
    )
    currency = (
        currency_key
        if currency_key
        and detail_map.get("offercurrencyid") == "报价币种"
        and currency_detail
        and currency_detail.get("currency_display_readable") is True
        else None
    )
    return creator, quote, currency


def _decimal_is_readable(value: object) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        return Decimal(str(value).replace(",", "")).is_finite()
    except (InvalidOperation, ValueError):
        return False


def _decimal_values_equal(left: object, right: object) -> bool:
    try:
        return Decimal(str(left).replace(",", "")) == Decimal(
            str(right).replace(",", "")
        )
    except (InvalidOperation, ValueError):
        return False


def _label_is_allowed(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    label = " ".join(value.split())
    return label if label in _SAFE_LABELS else None


def _function_source(frame: object, expression: str) -> str:
    try:
        value = frame.evaluate(expression)
    except Exception:  # noqa: BLE001 - source is inspected in memory only
        return ""
    return value if isinstance(value, str) else ""


def _grid_columns(frame: object) -> list[dict[str, str]]:
    try:
        columns = frame.locator("#_id_dg thead th").evaluate_all(
            "els => els.map(el => ({field: el.getAttribute('data-field') || '', "
            "label: (el.innerText || el.textContent || '').trim()}))"
        )
    except Exception:  # noqa: BLE001 - page metadata is best effort
        return []
    if not isinstance(columns, list):
        return []
    result = []
    for item in columns:
        if not isinstance(item, dict):
            continue
        field, label = item.get("field"), _label_is_allowed(item.get("label"))
        if isinstance(field, str) and field and label:
            result.append({"field": field[:64], "label": label})
    return result[:80]


def _detail_fields(frame: object) -> list[dict[str, Any]]:
    try:
        fields = frame.locator("input,select,textarea").evaluate_all(
            "els => els.map(el => { const cell=el.closest('td'); "
            "const label=cell && cell.previousElementSibling; "
            "const id=el.id || el.getAttribute('name') || ''; "
            "const option=el.tagName === 'SELECT' ? el.selectedOptions[0] : null; "
            "return {id, label:label ? (label.innerText || label.textContent || '').trim() : '', "
            "value:['OfferPrice','OfferCurrencyID'].includes(id) ? "
            "(option ? option.value : el.value) : '', "
            "currencyLabel:id === 'OfferCurrencyID' && option ? "
            "(option.innerText || option.textContent || '').trim() : '', "
            "creatorValue:/^(Creator|CreateUser|AddUser|AddUserID|UserID|EntryUser)$/i.test(id) ? "
            "(option ? (option.innerText || option.textContent || '') : el.value) : ''}; })"
        )
    except Exception:  # noqa: BLE001 - field values are never read
        return []
    if not isinstance(fields, list):
        return []
    result: list[dict[str, Any]] = []
    for item in fields:
        if not isinstance(item, dict):
            continue
        field_id = item.get("id") or item.get("name")
        label = _label_is_allowed(item.get("label"))
        if isinstance(field_id, str) and field_id and label:
            currency_label = " ".join(
                str(item.get("currencyLabel", "")).split()
            ).upper()
            result.append(
                {
                    "field": field_id[:64],
                    "label": label,
                    "value": item.get("value")
                    if field_id in {"OfferPrice", "OfferCurrencyID"}
                    else None,
                    "currency_display_readable": currency_label in _CURRENCY_DISPLAY,
                    "creator_nonempty": bool(str(item.get("creatorValue", "")).strip()),
                }
            )
    return result[:120]


def _query_shell(page: object, report: dict[str, Any]) -> object | None:
    frames = [
        frame
        for frame in page.frames
        if urlsplit(frame.url).scheme == "https"
        and urlsplit(frame.url).hostname == "yingsuo.alperp.cn"
        and urlsplit(frame.url)
        .path.casefold()
        .endswith("/innerenquiry/yewuxj/list.aspx")
    ]
    report["browser"]["shell_frame_count"] = len(frames)
    if len(frames) != 1:
        return None
    frame = frames[0]
    if (
        page.main_frame is not frame
        and sum(
            1
            for candidate in page.frames
            if candidate.name == frame.name and candidate.url == frame.url
        )
        != 1
    ):
        return None
    return frame


def _top_level_login_redirect(page: object) -> bool:
    """An embedded login iframe alone does not mean the authenticated shell expired."""

    try:
        return urlsplit(page.main_frame.url).path.casefold().endswith("/login.aspx")
    except Exception:  # noqa: BLE001 - uncertain identity is not treated as login
        return False


def _existing_verified_shell_pages(browser: object) -> int:
    """Count only pages with one expected list frame and visible shell controls."""

    try:
        contexts = tuple(browser.contexts)
    except Exception:  # noqa: BLE001 - identity failure remains zero
        return 0
    if len(contexts) != 1:
        return 0
    context = contexts[0]
    matched = 0
    for page in tuple(context.pages):
        try:
            if page.is_closed() or page.context is not context:
                continue
            frame = _query_shell(page, _empty_report())
            if frame is None:
                continue
            if (
                frame.locator("#DetailFieldValue").count() == 1
                and frame.locator("#DetailFieldValue").is_visible()
                and frame.locator("button#select_btns").count() == 1
                and frame.locator("button#select_btns").is_visible()
                and frame.locator("#_id_dg").count() == 1
            ):
                matched += 1
        except Exception:  # noqa: BLE001 - uncertain page is not a match
            return 0
    return matched


def _inspect_history(
    page: object,
    frame: object,
    report: dict[str, Any],
    *,
    verify_identity: Callable[[], None],
) -> None:
    adapter = PlaywrightDuplicateHistoryPage(frame)
    try:
        verify_identity()
        payload = adapter.query_exact_response(_TARGET_MPN)
        report["query"]["status"] = "SETTLED"
        report["query"]["exact_request_matched"] = True
        report["query"]["grid_columns"] = _grid_columns(frame)
        top_level, row_shapes = _schema_summary(payload)
        report["query"]["response_schema_fields"] = top_level
        report["query"]["response_rows"] = row_shapes
        response_rows = [
            row for row in payload["rows"] if isinstance(row, dict)
        ]
        row_fields = set(_safe_keys(response_rows[0])) if response_rows else set()
        report["query"]["billid_identity"] = "UNKNOWN"
        report["query"]["grid_detail_identity"] = "UNKNOWN"
        row_ids = _billid_rows(adapter)
        response_bill_ids = {
            str(row.get("BillID", "")).strip()
            for row in response_rows
            if str(row.get("BillID", "")).strip().isdecimal()
        }
        report["query"]["billid_identity"] = (
            "CONFIRMED"
            if len(response_bill_ids) == len(response_rows)
            else "UNKNOWN"
        )
        matching_links: list[tuple[str, str]] = []
        for row_id in row_ids:
            html = adapter.html(f"#{row_id}") or ""
            bill_arguments = set(DETAIL_LINK_CALL.findall(html))
            values = adapter.read_row_values(row_id)
            if (
                values is not None
                and values.model == _TARGET_MPN
                and len(bill_arguments) == 1
                and next(iter(bill_arguments)) in response_bill_ids
            ):
                matching_links.append((row_id, next(iter(bill_arguments)))
                )
        if len(matching_links) == 1:
            _row_id, bill_id = matching_links[0]
            selector = DETAIL_LINK_SELECTOR_TEMPLATE.format(argument=bill_id)
            verify_identity()
            adapter.click(selector)
            detail = _find_bill_detail_frame(page)
            if detail is not None:
                detail_bill_id = _billid_value(detail)
                report["query"]["grid_detail_identity"] = (
                    "CONFIRMED" if detail_bill_id == bill_id else "UNKNOWN"
                )
                report["query"]["billid_identity"] = report["query"][
                    "grid_detail_identity"
                ]
                fields = _detail_fields(detail)
                report["query"]["detail_readback_fields"] = (
                    _confirmed_detail_readback_fields(detail)
                )
                _classify_duplicate_fields(
                    report,
                    fields,
                    row_fields=row_fields,
                    columns=report["query"]["grid_columns"],
                    bill_id=bill_id,
                    rows=response_rows,
                )
        elif response_rows:
            report["reason_codes"].append("GRID_RESPONSE_IDENTITY_UNCONFIRMED")
    except InsoDuplicateHistoryError as exc:
        report["query"]["status"] = "UNAVAILABLE"
        report["reason_codes"].append(exc.code.value)
    except Exception:  # noqa: BLE001 - only stable reason codes are reported
        report["query"]["status"] = "UNAVAILABLE"
        report["reason_codes"].append("READ_ONLY_QUERY_INSPECTION_FAILED")


def _billid_rows(adapter: PlaywrightDuplicateHistoryPage) -> list[str]:
    values = adapter.attributes(RESULT_ROW_SELECTOR, "id")
    return [
        value for value in values if isinstance(value, str) and value.endswith("_Main")
    ]


def _find_bill_detail_frame(page: object) -> object | None:
    matches = []
    for frame in page.frames:
        try:
            if frame.locator(DETAIL_BILL_ID_SELECTOR).count() == 1:
                matches.append(frame)
        except Exception:  # noqa: BLE001 - stale frame makes identity uncertain
            return None
    return matches[0] if len(matches) == 1 else None


def _billid_value(frame: object) -> str | None:
    try:
        value = frame.locator(DETAIL_BILL_ID_SELECTOR).get_attribute("value")
    except Exception:  # noqa: BLE001
        return None
    return value if isinstance(value, str) else None


def _confirmed_detail_readback_fields(frame: object) -> list[str]:
    selectors = {
        "bill_id": "#BillID",
        "peno": "#PENO",
        "model": '#_id_dg td[data-field="PartNo"]',
        "brand": '#_id_dg td[data-field="Brand"]',
        "quantity": '#_id_dg td[data-field="Qty"]',
    }
    confirmed = []
    try:
        for name, selector in selectors.items():
            locator = frame.locator(selector)
            count = locator.count()
            if count == 1 and locator.is_visible():
                value = locator.get_attribute("value")
                if value is None:
                    value = locator.inner_text()
                if isinstance(value, str) and value.strip():
                    confirmed.append(name)
    except Exception:  # noqa: BLE001 - uncertain detail readback is omitted
        return []
    return confirmed


def _classify_duplicate_fields(
    report: dict[str, Any],
    fields: list[dict[str, Any]],
    *,
    row_fields: set[str],
    columns: list[dict[str, str]],
    bill_id: str,
    rows: list[dict[str, Any]],
) -> None:
    creator, quote, currency = _confirmed_duplicate_fields(row_fields, columns, fields)
    if creator and any(
        _field_key(item["field"]) == _field_key(creator)
        and item.get("creator_nonempty") is True
        for item in fields
    ):
        report["creator"] = {"status": "CONFIRMED", "field": creator}
    matching_rows = [
        row for row in rows if str(row.get("BillID", "")).strip() == bill_id
    ]
    if quote and currency and len(matching_rows) == 1:
        row = matching_rows[0]
        detail_values = {
            _field_key(item["field"]): item.get("value") for item in fields
        }
        row_quote = row.get(quote)
        detail_quote = detail_values.get("offerprice")
        row_currency = row.get(currency)
        detail_currency = detail_values.get("offercurrencyid")
        decimal_readable = _decimal_is_readable(row_quote) and _decimal_is_readable(
            detail_quote
        )
        values_match = (
            decimal_readable
            and _decimal_values_equal(row_quote, detail_quote)
            and row_currency is not None
            and str(row_currency).strip() == str(detail_currency).strip()
        )
        report["inso_quote"] = {
            "status": "CONFIRMED" if values_match else "UNKNOWN",
            "field": quote,
            "currency_field": currency,
            "decimal_readable": decimal_readable,
            "currency_display_readable": True,
            "row_detail_values_match": values_match,
        }


def _close_frame_dialog(
    frame: object, verify_identity: Callable[[], None]
) -> bool:
    """Close only the unique Layui dialog containing this exact child frame."""

    try:
        parent = frame.parent_frame
        child_element = frame.frame_element()
        dialogs = parent.locator(".layui-layer").filter(has=child_element)
        if dialogs.count() != 1:
            return False
        close = dialogs.locator(".layui-layer-close")
        if close.count() != 1 or not close.is_visible() or not close.is_enabled():
            return False
        classes = (close.get_attribute("class") or "").split()
        if "layui-layer-close" not in classes:
            return False
        verify_identity()
        close.click(timeout=10_000)
        return frame.is_detached()
    except Exception:  # noqa: BLE001 - uncertain close control stays untouched
        return False


def _close_blank_inquiry_form(
    frame: object, verify_identity: Callable[[], None]
) -> bool:
    """Use the observed Back handler, which only hides the blank-form dialog."""

    try:
        iframe = frame.frame_element()
        if not iframe.is_visible():
            return True
        back = frame.locator("button#btnBack")
        if (
            back.count() != 1
            or not back.is_visible()
            or not back.is_enabled()
            or back.get_attribute("title") != "返回列表"
            or back.get_attribute("onclick") != "goback()"
        ):
            return False
        handler = frame.evaluate(
            "() => typeof goback === 'function' ? Function.prototype.toString.call(goback) : ''"
        )
        if not _SAFE_BLANK_FORM_BACK.fullmatch(handler.strip()):
            return False
        verify_identity()
        try:
            back.click(timeout=10_000, no_wait_after=True)
        except Exception:  # noqa: BLE001 - confirm the actual form state below
            if frame.is_detached() or not iframe.is_visible():
                return True
        try:
            iframe.wait_for(state="hidden", timeout=10_000)
        except Exception:  # noqa: BLE001 - inspect the actual final frame state below
            return frame.is_detached() or not iframe.is_visible()
        return frame.is_detached() or not iframe.is_visible()
    except Exception:  # noqa: BLE001 - uncertain close control stays untouched
        return False


def _inspect_blank_form(
    page: object,
    frame: object,
    report: dict[str, Any],
    *,
    verify_identity: Callable[[], None],
) -> None:
    form_frame = None
    ai_frame = None
    try:
        add = frame.locator("button#product_add_")
        if add.count() != 1 or not add.is_visible() or not add.is_enabled():
            report["reason_codes"].append("BLANK_DRAFT_ENTRY_UNCONFIRMED")
            return
        verify_identity()
        add.click(timeout=10_000)
        form_frames = [
            candidate
            for candidate in page.frames
            if urlsplit(candidate.url).scheme == "https"
            and urlsplit(candidate.url).hostname == "yingsuo.alperp.cn"
            and urlsplit(candidate.url).path.casefold().endswith(
                "/sale/enquiry/bill.aspx"
            )
        ]
        if len(form_frames) != 1:
            report["reason_codes"].append("BLANK_DRAFT_FRAME_UNCONFIRMED")
            return
        form_frame = form_frames[0]
        save_button = form_frame.locator("button#btnSave")
        save_send = form_frame.locator("#btnSave2")
        send = form_frame.locator("#bcSend")
        report["save"]["button_semantics"] = (
            "CONFIRMED"
            if save_button.count() == 1
            and save_button.is_visible()
            and save_button.is_enabled()
            and save_button.inner_text().strip() == "保存"
            and save_button.get_attribute("id") == "btnSave"
            and save_send.count() == 1
            and save_send.is_visible()
            and save_send.inner_text().strip() == "保存并发送"
            else "UNKNOWN"
        )
        report["save"]["save_and_send_semantics"] = (
            "HARD_FORBIDDEN_CONFIRMED"
            if save_send.count() == 1 and save_send.inner_text().strip() == "保存并发送"
            else "UNKNOWN"
        )
        report["save"]["send_semantics"] = (
            "HARD_FORBIDDEN_CONFIRMED"
            if send.count() == 1 and send.inner_text().strip() == "发送"
            else "ABSENT"
            if send.count() == 0
            else "UNKNOWN"
        )
        report["save"]["save_and_send_hard_forbidden"] = True
        save_auto_source = _function_source(
            form_frame,
            "() => typeof bill_save_auto === 'function' ? "
            "Function.prototype.toString.call(bill_save_auto) : ''",
        )
        save_source = _function_source(
            form_frame,
            "() => typeof bill_save === 'function' ? "
            "Function.prototype.toString.call(bill_save) : ''",
        )
        save_handlers_confirmed = (
            "bill_save(" in save_auto_source
            and "bill_save_send" not in save_auto_source
            and "BillID" in save_source
            and "PENO" in save_source
            and "bill_save_send" not in save_source
        )
        report["save"]["handler_contract"] = (
            "SAVE_RESPONSE_BILLID_PENO_CONFIRMED"
            if save_handlers_confirmed
            else "UNKNOWN"
        )
        role_save = form_frame.get_by_role("button", name="保存", exact=True)
        if role_save.count() != 1:
            report["save"]["button_semantics"] = "UNKNOWN"
        ai_entry = form_frame.locator("#ai_import_")
        if (
            ai_entry.count() != 1
            or not ai_entry.is_visible()
            or not ai_entry.is_enabled()
        ):
            report["ai"]["panel"] = "UNKNOWN"
            return
        ai_source = _function_source(
            form_frame,
            "() => typeof ai_import === 'function' ? Function.prototype.toString.call(ai_import) : ''",
        )
        wrapper_source = _function_source(
            form_frame,
            "() => typeof windows === 'function' ? Function.prototype.toString.call(windows) : ''",
        )
        static_open_only = (
            "Import_ai.aspx" in ai_source
            and "windows(" in ai_source
            and bool(wrapper_source)
            and not _WRITE_WORDS.search(ai_source)
            and not _WRITE_WORDS.search(wrapper_source)
        )
        if not static_open_only:
            report["ai"]["panel"] = "OPEN_SEMANTICS_UNKNOWN"
            return
        report["ai"]["panel"] = "OPENING_READ_ONLY"
        verify_identity()
        ai_entry.click(timeout=10_000, no_wait_after=True)
        ai_frames = [
            candidate
            for candidate in page.frames
            if urlsplit(candidate.url)
            .path.casefold()
            .endswith("/product/import_ai.aspx")
        ]
        if len(ai_frames) != 1:
            report["ai"]["panel"] = "OPEN_FAILED_OR_AMBIGUOUS"
            return
        ai_frame = ai_frames[0]
        report["ai"]["panel"] = "OPENED_READ_ONLY"
        recognize = ai_frame.locator("button#ai-recognize")
        report["ai"]["input_candidates"] = _visible_control_candidates(
            ai_frame, "input,textarea"
        )
        if recognize.count() == 1 and recognize.is_visible() and recognize.is_enabled():
            report["ai"]["recognition_selector"] = "button#ai-recognize"
            label = recognize.inner_text().strip()
            report["ai"]["ready_signal"] = (
                label if label in {"AI智能识别", "重新识别"} else "UNKNOWN"
            )
        preview_fields = ai_frame.locator(
            "#preview-body > tr input[data-f]"
        ).evaluate_all(
            "els => els.map(el => { const r=el.getBoundingClientRect(); "
            "return {field:el.getAttribute('data-f') || '', visible:!!(r.width && r.height), "
            "enabled:!el.disabled}; })"
        )
        if isinstance(preview_fields, list):
            for field in ("PartNo", "Brand", "Qty"):
                matches = [
                    item
                    for item in preview_fields
                    if isinstance(item, dict) and item.get("field") == field
                ]
                if (
                    len(matches) == 1
                    and matches[0].get("visible")
                    and matches[0].get("enabled")
                ):
                    report["ai"]["result_fields"].append(
                        f'#preview-body > tr input[data-f="{field}"]'
                    )
        recognize_source = _function_source(
            ai_frame,
            "() => { const el=document.querySelector('button#ai-recognize'); "
            "return el && typeof el.onclick === 'function' ? "
            "Function.prototype.toString.call(el.onclick) : ''; }",
        )
        report["ai"]["recognition_handler_present"] = bool(recognize_source)
        report["ai"]["recognition_handler_direct_save_call_absent"] = bool(
            recognize_source
        ) and not bool(
            re.search(
                r"bill_save|save_and_send|(?:^|\W)save\s*\(|form\.submit|submit\s*\(",
                recognize_source,
                re.IGNORECASE,
            )
        )
        report["ai"]["recognition_readback"] = "UNKNOWN"
        report["ai"]["safe_to_execute_recognition"] = False
        report["reason_codes"].append("RECOGNITION_SIDE_EFFECT_NOT_PROVEN")
        # Recognition and Import-to-parent are intentionally not triggered. The
        # loaded client handler cannot prove what the server-side AI endpoint does.
        paste_source = _function_source(
            ai_frame,
            "() => typeof pasteImport === 'function' ? Function.prototype.toString.call(pasteImport) : ''",
        )
        do_import_source = _function_source(
            ai_frame,
            "() => window.AiImport && typeof AiImport.doImport === 'function' ? "
            "Function.prototype.toString.call(AiImport.doImport) : ''",
        )
        append_source = _function_source(
            form_frame,
            "() => typeof ai_appendRow === 'function' ? Function.prototype.toString.call(ai_appendRow) : ''",
        )
        callback_pure = all(
            source and not _WRITE_WORDS.search(source)
            for source in (paste_source, do_import_source, append_source)
        )
        report["parent_writer"]["callback_static_client_only"] = callback_pure
        report["ai"]["callback_fields"] = sorted(
            field
            for field in ("PartNo", "Brand", "Qty")
            if any(
                re.search(rf"\b{field}\b", source)
                for source in (paste_source, do_import_source, append_source)
            )
        )
        report["parent_writer"]["status"] = "UNKNOWN"
    except Exception:  # noqa: BLE001 - reason code only; no page text is persisted
        if report["ai"]["panel"] == "OPENING_READ_ONLY":
            report["ai"]["panel"] = "OPEN_FAILED_OR_AMBIGUOUS"
        report["reason_codes"].append("BLANK_DRAFT_INSPECTION_FAILED")
    finally:
        ai_closed = ai_frame is None or ai_frame.is_detached()
        if ai_frame is not None and not ai_closed:
            ai_closed = _close_frame_dialog(ai_frame, verify_identity)
        form_open = form_frame is not None and not form_frame.is_detached()
        if form_open and not _close_blank_inquiry_form(form_frame, verify_identity):
            report["reason_codes"].append("BLANK_FORM_CLOSE_UNCONFIRMED")
        if ai_frame is not None and not ai_closed and not ai_frame.is_detached():
            try:
                ai_closed = not ai_frame.frame_element().is_visible()
            except Exception:  # noqa: BLE001 - detached frame means closed
                ai_closed = True
        if not ai_closed:
            report["reason_codes"].append("AI_PANEL_CLOSE_UNCONFIRMED")


def _chrome_product(cdp_url: str) -> str | None:
    try:
        with urlopen(cdp_url.rstrip("/") + "/json/version", timeout=2) as response:
            payload = json.load(response)
    except (OSError, URLError, ValueError, TypeError):
        return None
    product = payload.get("Browser") if isinstance(payload, dict) else None
    return product if isinstance(product, str) else None


def _visible_control_candidates(frame: object, selector: str) -> list[dict[str, str]]:
    try:
        elements = frame.locator(selector).evaluate_all(
            "els => els.filter(el => { const r=el.getBoundingClientRect(); "
            "return !!(r.width && r.height) && !el.disabled; }).map(el => "
            "({tag: el.tagName.toLowerCase(), id: el.id || '', "
            "name: el.getAttribute('name') || '', type: el.getAttribute('type') || ''}))"
        )
    except Exception:  # noqa: BLE001 - absence is reported as UNKNOWN
        return []
    if not isinstance(elements, list):
        return []
    candidates = []
    for item in elements:
        if not isinstance(item, dict):
            continue
        safe = {
            key: value[:64]
            for key, value in item.items()
            if key in {"tag", "id", "name", "type"}
            and isinstance(value, str)
            and _SAFE_SCHEMA_KEY.fullmatch(value)
            and not _SENSITIVE_SCHEMA_KEY.search(value)
        }
        if safe:
            candidates.append(safe)
    return candidates[:40]


def run_phase_a_final(root: str | Path | None = None) -> Path:
    """Run one bounded Owner-session inspection and save a sanitized report."""

    project_root = (
        Path(root) if root is not None else Path(__file__).resolve().parents[2]
    )
    report_path = project_root / _REPORT_RELATIVE_PATH
    report = _empty_report()
    handle: BrowserHandle | None = None
    session = None
    keep_chrome_open = False
    drained = {"value": False}
    try:
        runtime = load_runtime_config(
            runtime_config_path("research.json", root=project_root)
        )
        if runtime.browser.channel.casefold() != "chrome":
            report["reason_codes"].append("CANONICAL_BROWSER_NOT_CHROME")
        else:
            production_path = runtime_config_path("production.json", root=project_root)
            config = json.loads(production_path.read_text(encoding="utf-8"))
            bootstrap = (
                config.get("browser_bootstrap") if isinstance(config, dict) else None
            )
            if not isinstance(bootstrap, dict):
                report["reason_codes"].append("CHROME_BOOTSTRAP_CONFIG_UNAVAILABLE")
            else:
                executable = resolve_app_path(
                    str(bootstrap.get("executable", "")), root=project_root
                )
                profile = resolve_app_path(
                    str(bootstrap.get("profile_dir", "")), root=project_root
                )
                cdp_url = runtime.cdp.cdp_url
                if (
                    executable.name.casefold() != "chrome.exe"
                    or not executable.is_file()
                    or profile.name.casefold() != "cdp"
                    or profile.parent.name.casefold() != ".browser-profile"
                    or not profile.is_dir()
                    or int(bootstrap.get("debug_port", 0)) != 9222
                    or urlsplit(cdp_url).hostname != "127.0.0.1"
                    or urlsplit(cdp_url).port != 9222
                ):
                    report["reason_codes"].append("CHROME_RUNTIME_CONFIG_NOT_CANONICAL")
                else:
                    product = _chrome_product(cdp_url)
                    if product and not product.casefold().startswith("chrome/"):
                        report["reason_codes"].append("CDP_ENDPOINT_IS_NOT_CHROME")
                    else:
                        try:
                            handle = acquire_cdp_browser(cdp_url, project_root, config)
                        except BrowserBootstrapError:
                            report["reason_codes"].append("CHROME_CDP_UNAVAILABLE")
                        else:
                            product = _chrome_product(cdp_url)
                            if not product or not product.casefold().startswith(
                                "chrome/"
                            ):
                                report["reason_codes"].append(
                                    "CDP_ENDPOINT_IS_NOT_CHROME"
                                )
                            else:
                                report["browser"]["cdp"] = "READY"
                                report["browser"]["ownership"] = (
                                    "APP_OWNED" if handle.owned else "REUSED"
                                )
                                report["browser"]["existing_verified_shell_pages"] = (
                                    _existing_verified_shell_pages(handle.browser)
                                )
                                session = attach_inso_research_session(
                                    cdp_url,
                                    handle,
                                    cycle_id="v12-phase-a-final",
                                    cycle_is_drained=lambda _cycle: drained["value"],
                                )
                                report["browser"]["context_count"] = len(
                                    handle.browser.contexts
                                )
                                with session.operation_access().operation_page() as operation:
                                    page = operation.page
                                    page.set_default_timeout(10_000)
                                    frame = operation.shell_frame
                                    if _query_shell(page, report) is not frame:
                                        report["reason_codes"].append(
                                            "VERIFIED_INSO_SHELL_NOT_UNIQUE"
                                        )
                                    else:
                                        report["browser"]["login_state"] = (
                                            "AUTHENTICATED_SHELL"
                                        )
                                        def verify_identity() -> None:
                                            with session.operation_access().operation_page() as current:
                                                if (
                                                    current.page is not page
                                                    or current.shell_frame is not frame
                                                ):
                                                    raise InsoDuplicateHistoryError(
                                                        DuplicateHistoryFailure.HISTORY_LIST_UNAVAILABLE
                                                    )

                                        _inspect_history(
                                            page,
                                            frame,
                                            report,
                                            verify_identity=verify_identity,
                                        )
                                if report["browser"]["login_state"] == "AUTHENTICATED_SHELL":
                                    with session.operation_access().operation_page() as operation:
                                        page = operation.page
                                        frame = operation.shell_frame
                                        def verify_blank_identity() -> None:
                                            with session.operation_access().operation_page() as current:
                                                if (
                                                    current.page is not page
                                                    or current.shell_frame is not frame
                                                ):
                                                    raise InsoDuplicateHistoryError(
                                                        DuplicateHistoryFailure.HISTORY_LIST_UNAVAILABLE
                                                    )

                                        _inspect_blank_form(
                                            page,
                                            frame,
                                            report,
                                            verify_identity=verify_blank_identity,
                                        )
                                report["save"]["success_billid_contract"] = (
                                    "CONFIRMED_STATIC"
                                    if report["save"]["handler_contract"]
                                    == "SAVE_RESPONSE_BILLID_PENO_CONFIRMED"
                                    else "UNKNOWN"
                                )
                                report["save"]["reconciliation"] = (
                                    "PARTIAL_READ_ONLY_BILLID_CONTRACT"
                                    if report["save"]["success_billid_contract"]
                                    == "CONFIRMED_STATIC"
                                    else "UNKNOWN"
                                )
    except ResearchRuntimeConfigError:
        report["reason_codes"].append("RESEARCH_RUNTIME_CONFIG_INVALID")
    except Exception:  # noqa: BLE001 - never persist raw exception or page text
        report["reason_codes"].append("PHASE_A_RUNNER_FAILED")
    finally:
        drained["value"] = True
        if session is not None and not keep_chrome_open:
            try:
                session.close_after_drain()
            except Exception:  # noqa: BLE001 - cleanup is best effort and sanitized
                report["reason_codes"].append("SESSION_CLEANUP_UNCONFIRMED")
        elif handle is not None:
            if handle.owned and not keep_chrome_open:
                try:
                    handle.close()
                except Exception:  # noqa: BLE001
                    report["reason_codes"].append("OWNED_CHROME_CLEANUP_UNCONFIRMED")
            else:
                handle.disconnect()
    return _write_report(report_path, report)


def _write_report(path: Path, report: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return path


def main() -> int:
    try:
        path = run_phase_a_final()
        print(f"Phase A read-only report written: {path}")
        return 0
    except Exception:  # noqa: BLE001 - console output remains generic
        print("Phase A read-only runner failed; see the sanitized runtime report.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
