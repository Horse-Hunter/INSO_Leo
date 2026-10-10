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


def acquire_sales_tab(*, config_path, production_path, root):
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
    handle = acquire_cdp_browser(config.cdp.cdp_url, root, production)
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


def run_sales_header_check(*, sample_number=1, config_path, production_path, root):
    """Independent one-shot worker result; never changes inquiry state."""
    from src.inso.sales_header import (
        FIELD_LABELS,
        PlaywrightSalesHeaderPage,
        fill_sales_header,
    )
    from src.order_mail.pi_orders import PiError, read_sample_pi_orders
    handle = None
    try:
        if sample_number not in (1, 2):
            return "STOPPED", "订单邮件选择无效；未进入 INSO。"
        orders = read_sample_pi_orders()
        handle, page, _reused = acquire_sales_tab(
            config_path=config_path, production_path=production_path, root=root,
        )
        adapter = PlaywrightSalesHeaderPage(page, owns_page=lambda p: page_owner(p) == SALES_OWNER)
        result = fill_sales_header(adapter, orders[sample_number - 1].pi_no)
        if result.status == "WAITING_OWNER":
            return result.status, (
                f"样本{sample_number}：Excel PI No. 唯一有效（已脱敏）。\n"
                "客户名称、RMB、款到发货、卖方付/国内交货、快递发货、广东惠州、客户订单号全部读回一致。\n"
                "等待 Owner 复核。V1.4 本次执行已结束，不影响询价业务状态。\n"
                "销售订单标签页已保留；复核结束后请返回销售订单列表，再检查另一份样本。\n"
                "没有填写明细、上传附件、保存或提交审核。"
            )
        if result.reason == "OWNER_RETURN_REQUIRED":
            return "WAITING_OWNER", "等待 Owner 复核；请先在 V1.4 标签页返回销售订单列表，再启动下一次检查。"
        label = FIELD_LABELS.get(result.field, "销售订单页面")
        return "STOPPED", f"{label}检查未通过，本张订单已停止。原因：{result.reason}。页面保留供 Owner 查看；未保存或提交。"
    except PiError:
        return "STOPPED", "Excel PI No. 缺失、重复或结构无法确认，本张订单已停止；未进入 INSO。"
    except Exception:  # noqa: BLE001 - never output page/credential/customer values
        return "STOPPED", "INSO 会话或头部控件无法确认，本张订单已停止。现有页面保留；未保存或提交。"
    finally:
        if handle is not None:
            handle.disconnect()  # Same worker thread; never close browser or retained tab.
