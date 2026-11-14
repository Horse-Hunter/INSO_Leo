# RFQ-017 — 26 项历史失败测试审计与发布风险评估（2026-11-14）

**状态：`REVIEW_REQUIRED / READ_ONLY_AUDIT / NO_SOURCE_OR_TEST_CHANGE / NOT_DEPLOYED / NOT_MERGED`。**

## Owner 目标

在 RFQ-016 源码安全 PASS、但全量测试仍有 26 项固定失败的情况下，独立、只读、离线地判断：

1. 26 项失败逐项属于**旧测试不适用、环境问题，还是真实代码缺陷**；
2. 是否存在共同根因；
3. 风险等级是多少；
4. 是否阻碍新版部署或“全量回归通过”的发布结论。

本任务不修改业务源码或测试、不部署、不重启、不合并分支、不操作真实采购/Google 写入/报价/SMTP、不清除任何 `UNKNOWN`/hold。第 221 行已完成的真实订单不得重复下单。

## 当前固定对象

- 工作树：`D:\Program_Leo\INSO_Leo\.worktrees\v16-rfq016-stabilization`（复用，不新建）。
- 分支：`workbuddy/v16-rfq016-stabilization`。
- HEAD：`95e9b186de83741d34c6f7527e6b12d3acadff92`。
- 被审源码：`b45e870e328bab1183ae0a5478911d6c4575641f`（RFQ-016 最终 P1-E 补丁）。
- 基线证据：`docs/evidence/v16/rfq016-ceo-third-review-2026-11-14.json`（3408 collected / 3381 passed / 1 skipped / 26 failed）。
- 现场：`dist/INSO_V1.6/INSO_V1.6.exe` SHA256 `E9E3DA33…`，app PID 38948 / watcher 34304；Chrome CDP 9222 owner PID 24164；SQLite `dist/INSO_V1.2/runtime/production/workflow.sqlite3`。

## 必须完成的取证顺序

1. **接管核对（只读）**：Git 分支/HEAD/status/worktree；运行中进程、EXE 哈希、Chrome 9222、SQLite/WAL/SHM 聚合状态、221 行与 SHAHAB/115 状态；确认没有新的外部效果。
2. **复现 26 项**：用仓库现有 Python/pytest 在隔离 fake 环境运行 26 个 nodeid；记录 collected/failed/duration、失败类型与完整文本。
3. **全量对照**：运行 `tests` 全树，显式排除 26 个已知失败，确认其余测试是否全绿；不得用排除后的结果冒充 26 项通过。
4. **逐项归因**：每项给出失败点、类别（旧测试不适用 / 环境 / 真实代码缺陷）、风险、是否阻断发布。
5. **共同根因**：用 Git 历史证明 26 项由哪个提交引入、所引用符号是否在任何提交中存在、生产源码是否引用、是否可能曾经通过。
6. **发布风险评估**：区分“功能回归”“测试基线债务”“未实现的防御纵深”；给出是否阻碍受控试运行、是否阻碍全量绿/无条件生产发布的明确结论。
7. **交付**：建立 `TASK_SPEC.md`、`EXECUTION_LOG.md`、`AUDIT_REPORT.md`、`FINAL_REPORT.md` 和机器可读证据 JSON，供 CEO 独立复核。

## 允许 / 禁止

**允许：** 读代码/Git/文档/证据；只读进程/文件/SQLite 聚合查询；运行隔离的 fake/synthetic pytest；写本 RFQ 的文档与证据；本地提交/推送文档（不合并）。

**禁止：** 修改 `src/` 或 `tests/`；删除/跳过/弱化测试；部署、覆盖 EXE、重启/停止生产进程；合并到 `develop`/`main`/`release/previous`；真实采购、Google Editor/写入、报价按钮、SMTP；清除 `SENT`/`UNKNOWN`/hold；重放 221 行或 SHAHAB/115；创建第二个 Chrome/profile 或强杀 9222。

## 完成标准

- 26/26 均有逐项判断，且分类有可复核证据（不是“历史相同所以安全”）。
- 全量对照结果明确区分“26 项已知失败”和“其余全绿”。
- 共同根因有 Git 证据，能解释为何多轮 nodeid 完全一致。
- 给出明确的发布门槛结论和下一步唯一动作。
- 未产生任何真实外部效果；现场 221 行、3 条 V13 hold、SHAHAB/115 UNKNOWN 均保持不变。

## 证据与下一步

- 详细审计：[AUDIT_REPORT.md](AUDIT_REPORT.md)
- 执行记录：[EXECUTION_LOG.md](EXECUTION_LOG.md)
- 机器可读证据：[`docs/evidence/rfq017/rfq017-test-audit-2026-11-14.json`](../../docs/evidence/rfq017/rfq017-test-audit-2026-11-14.json)
- 下一步：CEO 独立复核本审计；是否修复/隔离 26 项测试、是否批准受控试运行，均需另行授权，不在本 RFQ 自动连锁。
