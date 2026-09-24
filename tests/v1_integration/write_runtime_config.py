"""Generate the Git-ignored runtime/research.json for the V1 live smoke."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.research.runtime import (
    BomAiBrowserConfig,
    BrowserRuntimeConfig,
    CdpRuntimeConfig,
    IcNetRuntimeConfig,
    InsoBrowserConfig,
    ResearchRuntimeConfig,
)


def build() -> ResearchRuntimeConfig:
    return ResearchRuntimeConfig(
        excel_output_path=Path("runtime") / "调研价格.xlsx",
        bom_ai=BomAiBrowserConfig(
            login_url="https://www.bom.ai/",
            result_url_template="https://www.bom.ai/parts/{mpn}",
            username_selector='input[name="username"], input[name="email"], input[type="text"]',
            password_selector='input[name="password"], input[type="password"]',
            login_button_selector='button[type="submit"], input[type="submit"], button',
            company_selector=None,
            post_login_ready_selector=None,
        ),
        inso=InsoBrowserConfig(
            login_url="https://yingsuo.alperp.cn/",
            username_selector='input[name="username"], input[name="userName"], input[type="text"]',
            password_selector='input[name="password"], input[type="password"]',
            login_button_selector='button[type="submit"], input[type="submit"], button',
            mpn_selector='input[name="mpn"], input[name="model"], input[placeholder*="型号"], input[placeholder*="MPN"]',
            query_button_selector='button[type="submit"], button',
            company_selector=None,
            date_headers=(
                "询价时间",
                "报价时间",
                "更新时间",
                "创建时间",
                "日期",
            ),
        ),
        browser=BrowserRuntimeConfig(
            channel="chrome",
            headless=False,
            timeout_ms=45_000,
            settle_ms=3_000,
        ),
        cdp=CdpRuntimeConfig(cdp_url="http://127.0.0.1:9222"),
        icnet=IcNetRuntimeConfig(mode="cdp"),
    )


def main() -> int:
    cfg = build()
    runtime_dir = ROOT / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "excel_output_path": str(cfg.excel_output_path),
        "browser": {
            "channel": cfg.browser.channel,
            "headless": cfg.browser.headless,
            "timeout_ms": cfg.browser.timeout_ms,
            "settle_ms": cfg.browser.settle_ms,
        },
        "cdp": {"cdp_url": cfg.cdp.cdp_url},
        "icnet": {"mode": cfg.icnet.mode},
        "bom_ai": {
            "login_url": cfg.bom_ai.login_url,
            "result_url_template": cfg.bom_ai.result_url_template,
            "username_selector": cfg.bom_ai.username_selector,
            "password_selector": cfg.bom_ai.password_selector,
            "login_button_selector": cfg.bom_ai.login_button_selector,
            "company_selector": cfg.bom_ai.company_selector,
            "post_login_ready_selector": cfg.bom_ai.post_login_ready_selector,
        },
        "inso": {
            "login_url": cfg.inso.login_url,
            "username_selector": cfg.inso.username_selector,
            "password_selector": cfg.inso.password_selector,
            "login_button_selector": cfg.inso.login_button_selector,
            "mpn_selector": cfg.inso.mpn_selector,
            "query_button_selector": cfg.inso.query_button_selector,
            "company_selector": cfg.inso.company_selector,
            "date_headers": list(cfg.inso.date_headers),
        },
    }
    path = runtime_dir / "research.json"
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"runtime config written to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
