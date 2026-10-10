"""V1.4 assembly reuses canonical CDP and authentication on one owned tab."""
from __future__ import annotations

import json
from pathlib import Path

from src.core import get_login
from src.research.cdp_pages import new_background_page, page_owner
from src.research.runtime import load_runtime_config

from .browser_bootstrap import acquire_cdp_browser
from .inso_session import InsoAuthenticationError, InsoSessionGuard, InsoSessionOutcome

SALES_OWNER = "v14-sales"


def sales_config(config_path, production_path):
    config = load_runtime_config(config_path)
    if config.cdp.cdp_url.rstrip("/") != "http://127.0.0.1:9222":
        raise ValueError("CANONICAL_CDP_REQUIRED")
    production = json.loads(Path(production_path).read_text(encoding="utf8"))
    bootstrap = production.get("browser_bootstrap", {})
    if (bootstrap.get("persistent_session") is not True
            or str(bootstrap.get("profile_dir", "")).replace("\\", "/").casefold()
            != "d:/program_leo/inso_cdp/chrome-profile"
            or bootstrap.get("debug_port") != 9222):
        raise ValueError("CANONICAL_CDP_REQUIRED")
    return config, production


def acquire_sales_tab(*, config_path, production_path, root, handle=None):
    config, production = sales_config(config_path, production_path)
    handle = handle or acquire_cdp_browser(config.cdp.cdp_url, root, production)
    try:
        if handle.owned or len(handle.browser.contexts) != 1:
            raise ValueError("SHARED_CONTEXT_REQUIRED")
        context, = handle.browser.contexts
        candidates = [p for p in context.pages if not p.is_closed() and page_owner(p) == SALES_OWNER]
        if len(candidates) > 1:
            raise ValueError("SALES_TAB_AMBIGUOUS")
        if candidates:
            return handle, candidates[0], True
        page = new_background_page(handle.browser, context, timeout_ms=10000, owner=SALES_OWNER)
        login = get_login("yingsuo.alperp.cn")
        try:
            guard = InsoSessionGuard(login=login, context=lambda: context, page=lambda: page)
            status = guard.ensure_authenticated()
        finally:
            del login
        if status.outcome is InsoSessionOutcome.DEAD:
            raise InsoAuthenticationError(status.reason_code or "AUTHENTICATION_REQUIRED")
        if page_owner(page) != SALES_OWNER:
            raise ValueError("SALES_TAB_OWNERSHIP_LOST")
        return handle, page, False
    except Exception:
        handle.disconnect()
        raise


def prepare_sales_rows(order, client):
    """Serial first20 package queries, cache exact duplicate models per order."""
    from src.order_mail.contracts import OrderError
    from src.research.icnet import select_icnet_package
    cache, rows = {}, []
    for line in order.lines:
        if line.part_number not in cache:
            try:
                cache[line.part_number] = select_icnet_package(client.fetch_first_page(line.part_number))
            except Exception:  # noqa: BLE001 - provider text never enters notification
                raise OrderError("ICNET", pi_no=order.pi_no, part_number=line.part_number) from None
        rows.append({"model": line.part_number, "quantity": str(line.quantity),
            "price": format(line.unit_price, "f"), "brand": line.brand, "dc": line.dc,
            "package": cache[line.part_number], "due": line.delivery_date,
            "packing": "全新拆封", "developer": "无", "moisture": "1", "unpack": "是"})
    return tuple(rows)


def run_sales_header_check(*, sample_number=1, config_path, production_path, root, notify=None):
    """One selected mail; complete preflight before header/detail mutation."""
    from datetime import UTC, datetime
    from uuid import uuid4
    from zoneinfo import ZoneInfo

    from src.inso.sales_details import (
        DETAIL_FIELDS,
        DetailStop,
        PlaywrightSalesDetailsPage,
        fill_sales_details,
    )
    from src.inso.sales_header import (
        FIELD_LABELS,
        PlaywrightSalesHeaderPage,
        fill_sales_header,
    )
    from src.order_mail.contracts import OrderError, read_selected_contract
    from src.research.cdp_pages import shared_playwright_factory
    from src.research.credentials import CoreResearchCredentials
    from src.research.icnet import CdpIcNetClient

    invocation = uuid4().hex
    handle, order = None, None
    try:
        today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
        order = read_selected_contract(sample_number, today=today)
        config, production = sales_config(config_path, production_path)
        # Attach canonical browser for ICNET without entering/navigating sales.
        handle = acquire_cdp_browser(config.cdp.cdp_url, root, production)
        owned = [p for p in handle.browser.contexts[0].pages if page_owner(p) == SALES_OWNER]
        if len(owned) == 1 and owned[0].evaluate("() => window.__INSO_sales_owner_review === true"):
            header_probe = PlaywrightSalesHeaderPage(owned[0], owns_page=lambda p: page_owner(p) == SALES_OWNER)
            if header_probe.waiting_for_owner():
                return "WAITING_OWNER", "等待 Owner 复核；请先返回销售订单列表。没有修改当前订单。"
        client = CdpIcNetClient(cdp_url=config.cdp.cdp_url, timeout_ms=config.browser.timeout_ms,
            login_provider=CoreResearchCredentials().icnet, tab_owner="v14-icnet",
            playwright_factory=shared_playwright_factory(lambda: (handle.playwright, handle.browser)))
        expected = prepare_sales_rows(order, client)
        handle, page, _reused = acquire_sales_tab(config_path=config_path,
            production_path=production_path, root=root, handle=handle)
        adapter = PlaywrightSalesHeaderPage(page, owns_page=lambda p: page_owner(p) == SALES_OWNER)
        result = fill_sales_header(adapter, order.pi_no)
        if result.reason == "OWNER_RETURN_REQUIRED":
            return "WAITING_OWNER", "等待 Owner 复核；请先返回销售订单列表。"
        if result.status != "WAITING_OWNER":
            raise OrderError("INSO", pi_no=order.pi_no, field=FIELD_LABELS.get(result.field, "订单头部"))
        header_values = {field: adapter.read(field) for field in FIELD_LABELS}
        try:
            count = fill_sales_details(PlaywrightSalesDetailsPage(adapter), expected)
        except DetailStop as exc:
            part = order.lines[exc.row].part_number if exc.row is not None else None
            label = DETAIL_FIELDS.get(exc.field, (None, "明细行数"))[1]
            raise OrderError("INSO", pi_no=order.pi_no, part_number=part, field=label) from None
        for field, value in header_values.items():
            if adapter.read(field) != value:
                raise OrderError("INSO", pi_no=order.pi_no, field=FIELD_LABELS[field])
        return "WAITING_OWNER", (f"样本{sample_number}：合同{count}行已完成解析和 ICNET 封装查询（已脱敏）。\n"
            "头部及全部明细字段最终读回一致，等待 Owner 复核。\n"
            "V1.4 worker 已结束，不影响询价；销售订单页面保留。\n"
            "没有填写总金额/CONDITION，没有上传附件、保存或提交审核。")
    except Exception as exc:  # noqa: BLE001 - closed human text only, no source errors/values
        error = exc if isinstance(exc, OrderError) else OrderError("INSO", pi_no=getattr(order, "pi_no", None))
        if error.code == "ICNET":
            situation = "ICNET 查询或前20条封装读取未成功，自动录单已停止。"
            treatment = "请人工确认网站登录及封装后重新处理。"
        elif error.code == "LEAD_TIME":
            situation = "合同交期格式不支持，自动录单已停止。"
            treatment = "请确认合同交期规则后重新处理。"
        elif error.code == "INSO":
            situation = f"INSO“{error.field or '页面'}”控件或读回未通过，自动录单已停止。"
            treatment = "请人工检查当前未保存销售订单页面。"
        else:
            situation = f"合同或邮件中的{error.field or '必要信息'}缺失、无效或无法唯一确认，自动录单已停止。"
            treatment = "请补充或确认合同信息后重新处理。"
        notified = False
        if notify is not None:
            try:
                notify(invocation_id=invocation, pi_no=error.pi_no, part_number=error.part_number,
                    situation=situation, treatment=treatment, at=datetime.now(UTC))
                notified = True
            except Exception:  # noqa: BLE001, S110 - retain safe report if SMTP/outbox unavailable
                pass
        return "STOPPED", situation + ("异常通知已交给现有发件队列。" if notified else "异常通知不可用，请人工联系 Owner。") + "现有页面保留；未保存或提交。"
    finally:
        if handle is not None:
            handle.disconnect()  # Same thread, never close sales tab or browser.
