# Task: V1 Research + Sheets Contract Update

status: complete
actor_role: Architecture Codex
executor_tool: CODEX
module: architecture
reports_to: CEO / Architecture Chat
execution_mode: FAST_V1
architecture_impact: REQUIRED

## Goal

以 canonical replacement 同步 Research 五价格源、Excel、SHAHAB mapping/provenance，以及 Research read-only INSO 与 Future INSO Module 边界。

## Final Result

- Research 改为 IC.net Brand/货量 + 五价格源，并固化新型号、时间、选价、status、Excel 规则。
- Sheets 增加 SHAHAB B/D/E/F mapping、默认 `importance_raw = "A"`、来源 provenance 和 B/D/F Brand relocation。
- Product、Module Registry、Workflow 已区分 V1 INSO read-only Research source 与 Future 主动采购模块。
- 被替代的四源、通用 STRICT、Qty-tier、Bom 7 天优先、importance 转换和旧 NO_MATCH 语义已删除。

## Owner Decisions

- Research 直接使用获批 INSO read-only adapter，不依赖 `inso` 模块。
- 下游只透传 opaque record reference；worksheet mapping 和 safe writer 始终归 Sheets。
- Future 主动采购不得从 `MANUAL_REVIEW` 自动发布采购需求。

## Verification

- 逐项 Contract 断言、obsolete 规则扫描、跨文档范围检查通过；STRICT MPN 仅保留于 IC.net。
- `git diff --check`、Secret scan clean；业务代码未修改。
- 五份目标文档 diff 净减少 8 行；字符约 `9,492 -> 10,128`（新增事实 +6.7%）。

## Commit

- `docs: update v1 research and sheet contracts`（本 Task 所在提交）

## Remaining Gap

- 业务代码尚未实现本次新 Contract；按本 Task scope 留待对应模块 Implementation Task。
