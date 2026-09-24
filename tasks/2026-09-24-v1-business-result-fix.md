# Task: V1 Business Result Fix

status: in_progress
actor_role: Production Runtime Codex (唯一执行器)
executor_tool: BUDDY
module: research_v1_final
reports_to: CEO / Architecture Chat
execution_mode: FAST_V1
architecture_impact: NONE

## Problem

V1 mainline 已真实跑通（Google Sheet → Workflow → Research → 调研价格.xlsx），
但真实运行暴露四个业务结果问题：

1. production live runner 只扫描 worksheet `2026`，漏掉 `shahab` 的 3 条 `未发`。
2. Research 业务结果质量不足：五个价格源大多数返回 `无结果` 或技术失败
   （华强：结果解析失败/暂时不可用；正能量、INSO：需要人工验证）。
3. Findchips 价格出现几十位 Decimal（如 `68.95194461484532468670581018`），
   Excel 展示不可接受。
4. HQEW / Bom.Ai / INSO 需要针对真实运行失败直接诊断，不重新设计询价逻辑。

## Goal

在不改变模块边界与 Public Contract 的前提下：

- live runner 扫描全部已配置目标 worksheets（`2026` + `shahab`）。
- Excel 所有价格展示使用人可读精度（不再出现几十位小数）。
- 基于真实页面诊断修复 HQEW / Bom.Ai / INSO 的失败（fail-closed 语义不变，
   不绕过任何 CAPTCHA / OTP / 设备验证）。
- 真实运行复跑验证业务结果改善。

## Current Facts

- worktree: `.worktrees/research-v1-production-runtime-buddy`，
  branch `buddy/research-v1-production-runtime` 与 origin 同步、clean。
- `tests/v1_integration/v1_live_smoke.py` 只接受单个 `WORKSHEET_TITLE` env，
  只构造一个 `WorksheetIdentity`；Workflow `WorkflowPoller` 本身支持多 worksheet。
- 真实运行 Excel 证据（`runtime/调研价格.xlsx`）：
  - Findchips 展示 `68.95194461484532468670581018（无库存）` 等 28 位小数；
    根因是 `money_text`/`_decimal_text` 直接 `format(Decimal, "f")`，
    而 `normalized_rmb_price = unit_price * fx_rate`（fx_rate 为 ECB 汇率相除结果）。
  - 华强 remarks：`结果解析失败`（parse error）/`暂时不可用`。
  - 正能量、INSO remarks：`需要人工验证`（`INTERACTIVE_CHALLENGE_REQUIRED`）；
    Bom.Ai/INSO 均为 fresh Playwright + Credential 登录路径，登录页 HTML 被
    `_reject_challenge` 的子串标记（captcha/验证码/otp 等）拒绝。
  - 立创完成但 `无结果`（无技术失败备注）。
- SHAHAB worksheet title 为 `shahab`（`src/sheets/worksheet_schema.py`）。
- INSO 真实修复后端到端验证（CDP 复用 Owner 会话 + `POST
  /services/stock/select.ashx?action=Stock_VenQuote`）：
  STM32F103C8T6 → `SUCCESS`（native 5.398230 RMB, 1-month window）；
  MAX232CPE / LM358N → `NO_VALID_PRICE`（数据样本 >3 个月或 InPrice=0）。

## Required Context

- `tasks/2026-09-24-v1-final-integration.md`
- `tasks/2026-09-24-research-v1-production-runtime.md`
- `docs/modules/RESEARCH.md`、`docs/modules/WORKFLOW.md`、`docs/modules/SHEETS.md`
- `src/research/**`、`src/sheets/**`、`src/workflow/**`、`tests/v1_integration/**`

## Write Scope

- `src/research/**`
- `tests/research/**`
- `tests/v1_integration/**`
- `runtime/`（Git-ignored 运行数据）
- 本 Task Packet

## Non-scope

- 不重新设计网站询价逻辑；不改 Research/Workflow/Sheets Public Contract。
- 不绕过 CAPTCHA / OTP / 设备验证；需要人工登录时按协议暂停 Owner。
- 不做 V2（UUID、Sheet 状态写回、主动采购、Quotation）。
- 不操作原始 dirty checkout，不新建 worktree。

## Requirements

- 所有价格源区分业务无结果与技术失败的语义不变。
- Excel `_inquiry_id` 幂等性不回退。
- 不打印、持久化任何 credential / cookie / token。
- 修复后真实运行复跑并检查 Excel 业务结果。

## Acceptance

- [x] live runner 扫描 `2026` + `shahab`：`WORKSHEET_TITLES` 支持逗号分隔多
  worksheet，保持 `WORKSHEET_TITLE` 向后兼容。
- [x] Excel 所有价格列最多展示 4 位小数（比较逻辑仍用原始精度）。
- [x] HQEW：修复 `今天`/`昨天`/`前天`/`1周内`/`YYYY-MM` 日期解析；真实 CDP
  验证 STM32F103C8T6 / MAX232CPE / LM358N 全部解析出 40 条报价。
- [x] INSO：CDP 复用 + `Stock_VenQuote` POST；删废弃 selector；新写 11 个 INSO
  测试与所有 `tests/research/` 183 用例全过；CDP 真实拉数验证 STM32F103C8T6 / MAX232CPE / LM358N。
- [ ] Bom.Ai：待真实运行后按需诊断（当前无技术失败根因证据）。
- [ ] 真实运行复跑 `2026 + shahab` → Workflow → Research → Excel。
- [ ] 真实运行复跑，`调研价格.xlsx` 业务结果改善或失败原因可观察。
- [ ] 全部确定性测试、Ruff、secret scan 通过。
- [ ] commit + push 到当前 branch。

## Execution

diagnose → fix → real run → fix → rerun → verify → commit → push。
普通 bug 自主解决；仅人工登录 / CAPTCHA / OTP / device verification /
业务字段真实歧义时暂停 Owner。
