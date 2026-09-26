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
            cdp_url="http://127.0.0.1:9222",
            pagesize=30,
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
            "cdp_url": cfg.inso.cdp_url,
            "pagesize": cfg.inso.pagesize,
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
