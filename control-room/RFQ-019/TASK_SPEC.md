# RFQ-019 — 快速发布准备与最终风险评估（2026-11-14）

**状态：`REVIEW_REQUIRED / BLOCKED_FOR_NORMAL_GUI_AND_BUSINESS_TRIAL / SAFE_PREP_CONTINUE / NOT_DEPLOYED / NOT_MERGED`。**

## Owner 目标

在 RFQ-018 源码安全已 PASS 的前提下，以**尽快进入安全试运行**为目标，只读、离线完成发布准备评估，不再重审或修改已 PASS 的 RFQ-018 功能，也不无限扩展任务。

本阶段固定源码 `25894efa`，集中回答三个发布问题：

1. 重启/崩溃后，未确认/UNKNOWN 的外部效果如何安全隔离，避免把“重启清内存 hold”误当作已结算；
2. 旧 EXE 与新候选 EXE 的切换、配置/数据库保护与回滚如何做到可追溯；
3. GUI 停刷、退出卡住、Chrome 残留页面等历史风险应作为阻断项还是试运行观察项。

## 固定对象

- 工作树：`D:\Program_Leo\INSO_Leo\.worktrees\v16-rfq016-stabilization`（复用，不新建）。
- 分支：`workbuddy/v16-rfq016-stabilization`。
- 固定源码：`25894eface6ea622153d1573c19d0ca6b9ad72aa`（RFQ-018 最终 PASS）。
- 当前文档 HEAD：`45621923`（CEO RFQ-018 最终 Review；只含管理文档，不含新业务源码）。
- 旧 EXE：`dist/INSO_V1.6/INSO_V1.6.exe`，SHA256 `E9E3DA33…`（最近只读快照；非本任务部署）。
- 生产数据库：`dist/INSO_V1.2/runtime/production/workflow.sqlite3`（`runtime` junction 指向 `dist/INSO_V1.4/runtime`）。
- Chrome/CDP：`127.0.0.1:9222`，owner PID 24164（历史快照，须在下一次操作前重查）。

## 允许 / 禁止

**允许：** 读 Git/文档/证据；只读进程/文件/SQLite 聚合查询；离线检查构建脚本、环境、备份、哈希；写 RFQ-019 文档与证据；本地提交/推送原分支。

**禁止：** 部署、停止/覆盖生产 EXE、操作受保护 Chrome、修改生产 SQLite/WAL/SHM、清 UNKNOWN/SENT/hold、真实采购/Google 写入/报价/SMTP、重下第 221 行、处理 SHAHAB/115、合并 `develop` 或晋升 `main`/`release/previous`；不修改业务源码或测试。

## 必须交付

1. **发布准备报告**：固定源码/测试证据、旧 EXE/现场、候选构建、备份/回滚、重启 UNKNOWN 隔离、试运行范围、验收条件、Owner 下一步。
2. **风险清单**：分为“试运行前必须解决的阻断项”和“允许记录并观察的非阻断项”，每项有理由、证据、缓解、升级条件。
3. **发布准备结论**：`READY_FOR_OWNER_APPROVAL` 或 `BLOCKED`，并给出最少必要下一步操作。
4. **执行记录**：只读取证、未执行的外部动作、现场快照、`NOT_VERIFIED` 项。

## 完成标准

- 不重跑全部 4188 项测试；复用 RFQ-018 已审证据，只在发现新增风险时做必要离线验证。
- 三类发布问题均有明确结论；阻断/非阻断分类不是简单风险降级。
- 发布方案不引入新架构；回滚与重启 UNKNOWN 保护可执行、可验证。
- 未产生任何真实外部效果；未改业务源码/测试/生产配置。

## 证据与下一步

- 执行记录：[EXECUTION_LOG.md](EXECUTION_LOG.md)
- 风险清单：[RISK_REGISTER.md](RISK_REGISTER.md)
- 发布准备报告：[RELEASE_PREP_REPORT.md](RELEASE_PREP_REPORT.md)
- 发布结论：[RELEASE_READINESS.md](RELEASE_READINESS.md)
- 机器可读证据：`docs/evidence/rfq019/rfq019-release-prep-2026-11-14.json`
- 下一步：CEO 最终审核；任何构建、停止旧 EXE、安装或业务 Start 均需 Owner 单独授权。

## 完成结果（2026-11-14）

- 固定源码 `25894efa`；`git diff 25894efa..HEAD -- src tests` 为空；RFQ-018 旧证据复用，未重跑。
- 结论：**`BLOCKED`（正常 GUI / 业务试运行）**；仅候选构建、`--self-check`/`--idle-self-check`、完整回滚快照可继续。
- 阻断：B1 构建环境缺失、B2 无候选 EXE/hash、B3 无完整回滚快照、B4 旧 EXE 运行中且无干净 Stop 证明、B5 无受控单笔 Start、B6 重启不继承 document hold、B7 正常 GUI 启动含 IMAP/SMTP/DB migration。
- 观察项：GUI 停刷/退出卡住/Chrome 残留页、`inq_d65be9df` 报价失败、SHAHAB/115/221 历史状态。
- 未修改业务源码/测试/生产配置；未部署、未停旧 EXE、未操作 Chrome、未写生产 SQLite、未做真实 Google/INSO/SMTP。
