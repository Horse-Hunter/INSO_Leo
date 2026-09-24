# Task: V1 Business Result Fix

status: complete
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
- `docs/modules/RESEARCH.md`（本轮业务规则澄清）
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
- [x] Excel 所有业务价格显示 `ROUND_HALF_UP` 到 2 位小数，计算仍用原始 Decimal 精度。
- [x] HQEW：修复 `今天`/`昨天`/`前天`/`1周内`/`YYYY-MM` 日期解析；真实 CDP
  验证 STM32F103C8T6 / MAX232CPE / LM358N 全部解析出 40 条报价。
- [x] INSO：CDP 复用 + `Stock_VenQuote` POST；删废弃 selector；新写 11 个 INSO
  测试与所有 `tests/research/` 183 用例全过；CDP 真实拉数验证 STM32F103C8T6 / MAX232CPE / LM358N。
- [x] Bom.Ai：真实 Chrome 页面没有可见挑战；改用实际 `/components-price/{mpn}.html`，只解析目标型号报价行；真实验证 STM32F103C8T6 可读 50 条记录。运行配置已在本 worktree 的 Git-ignored `runtime/research.json` 更新。
- [x] 真实运行复跑 `2026 + shahab` → Workflow → Research → Excel；7 条入队，二次 poll 0 重复，6 条有效记录落盘，2026 第 91 行型号和数量为空，未写入 Excel。
- [x] `调研价格.xlsx` 业务结果改善：INSO/HQEW/Findchips 价格可用；Bom.Ai/LCSC/Findchips 的真实无报价与技术失败区分；IC.net 搜索限流/人工验证写入备注。
- [x] 全部确定性测试、Ruff、secret scan 通过：Research 193、Workflow 23、full pytest 294 passed/10 skipped，Ruff 与项目 secret scan PASS。
- [x] commit + push 到当前 branch。

## Execution

diagnose → fix → real run → fix → rerun → verify → commit → push。
普通 bug 自主解决；仅人工登录 / CAPTCHA / OTP / device verification /
业务字段真实歧义时暂停 Owner。

## Final Result

- `2026` 扫描 4 条 `未发`，`shahab` 扫描 3 条；合计入队 7，二次 poll duplicate 0。`shahab` 3 条全部进入 Workflow，最终为 `MANUAL_REVIEW`。
- 有效业务记录 6 条，Excel 业务行 6 条；`2026` 第 91 行型号和数量均为空，处于 `RETRY_WAIT`，不作为业务记录写入 Excel。Brand 回写保持禁用。
- 五价格源：Findchips 四条有效无库存参考价；HQEW 一条有效价；INSO 两条有效价；LCSC 和 Bom.Ai 在这 6 条型号中无有效报价。无技术失败被写成业务无结果。IC.net 经 Owner 手动完成站点验证后，有 4 条严格匹配并给出货量，2 条无严格型号匹配；已有 Brand 原样保留。
- 市场参考价与订单估值可用于业务参考；无库存兜底的两条明确标注需人工介入，完全无报价的两条进入 `MANUAL_REVIEW`。价格显示为 2 位半升舍入，内部 Decimal 未降精度。

## Verification

- 真实 Google Sheet → Workflow → Research → `runtime/调研价格.xlsx`，`WORKSHEET_TITLES=2026,shahab`，CDP `127.0.0.1:9222`，二次 poll 新增 0。对 shahab 第 110、111 行按原 inquiry ID 补跑并确认 Excel 仍为 6 条业务行。
- Research tests 193 passed；Workflow tests 23 passed；full pytest 294 passed / 10 skipped；Ruff PASS；项目 secret scan `SECRET_SCAN_OK`；`git diff --check` PASS。
- 未跟踪的 `v1-business-result-fix-report.md` 为接管前已有内容，未修改或纳入提交。运行配置和 Excel、SQLite 位于 Git-ignored `runtime/`。

## Remaining Gap

代码与 V1 运行链路：NONE。源 Sheet `2026` 第 91 行为空型号、空数量，保持 `RETRY_WAIT`，不推断其业务内容。

## Owner 复核修正（同一 V1 Task）

- IC.net 仅将实际认证标识计入 SSCP/ICCP 货量，供应商说明文字不计；无合格库存或无严格型号匹配时显示 `货少`。技术失败显示 `待验证` 并保留原因，货量格不再空白。同站 CDP 查询间隔设为至少 90 秒。`BCM957504-N425G` 实测合格库存 0、货量 `货少`；`GT17V-10DP-DS-SB(70)` 合格库存 0、货量 `货少`；`HD1x03-HH-CN` 无严格型号匹配、货量 `货少`。
- Findchips 改读 Owner Chrome 实际渲染结果，识别 HKD 和带千位逗号的价格，并通过 ECB 同日参考汇率换算。`FDA801B-VYT` 实际为 HK$94.7456、无库存，换算后业务展示 ¥81.02；先前 ¥68.95 来源于与 Chrome 不一致的 HTTP 响应及 USD-only 解析。`GT17V-10DP-DS-SB(70)` 找到有库存美元报价，业务展示 ¥39.51。`BCM957504-N425G` 可解析带千位逗号的报价，技术失败备注消失。
- Bom.Ai 已在当前 Chrome 使用 Core 密码箱正常登录并检查云价格；没有可见 CAPTCHA/OTP。目标型号与报价型号、自然月日期均严格核验：`HW8076502639302S` 页面云价格记录型号为 `HW8076502639302 SR388`，不可当成目标报价；其余目标在本轮没有有效月内目标报价。
- 立创账号从 Owner 提供的 `password.txt` 写入 Core 密码箱；Owner 手动完成登录页滑块验证后，程序复用已登录 Chrome。`FDA801B-VYT` 合作库存 208，更新日期 2026-09-24，页面 1+ ¥747.019462、10+ ¥622.516219；按既定最低展示 tier 规则写入 ¥622.52。普通商品列表为空不再掩盖合作库存结果。
- 真实扫描 `2026` 4 条 pending、`shahab` 3 条 pending，入队 7，二次 poll duplicate 0；6 条有效业务记录在 Excel，货量标识均非空。对受真实会话失效影响的 3 条使用原 inquiry ID 幂等补跑，Excel 保持 6 条业务行。Brand 写回禁用。
- Research 198 passed、Workflow 23 passed、full pytest 299 passed / 10 skipped、Ruff PASS、项目 secret scan `SECRET_SCAN_OK`、`git diff --check` PASS。`runtime/` 的 Excel/SQLite 为 Git-ignored；接管前未跟踪的报告文件保持不动。
