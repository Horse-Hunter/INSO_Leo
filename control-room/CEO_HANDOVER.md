# INSO LEO — CEO/Executor 接管入口（2026-11-15）

**先访问 `develop`，不要默认 `main`**：[AI_START_HERE](../AI_START_HERE.md)、[AGENTS](../AGENTS.md)、[BRANCH_POLICY](../docs/BRANCH_POLICY.md)、[COORDINATION](COORDINATION.md)、[RFQ-021 最终报告](RFQ-021/FINAL_REPORT.md)、[RFQ-021 执行记录](RFQ-021/EXECUTION_LOG.md)、[安装与回滚](RFQ-021/INSTALL_AND_ROLLBACK.md)、[RFQ-020 CEO Review](RFQ-020/REVIEW.md)。`docs/BRANCH_POLICY.md` 在 **develop** 有，在 Executor 分支没有；`control-room/RFQ-019/REVIEW.md` 由 CEO `64dba150` 加入，两分支均存在。新窗口先 fetch 最新 develop 再读取、核对本地 git HEAD/status/worktree。只保留一个正在操作的 Executor/工作树，不得关闭正在运行的 Windows 生产程序。

**最新结论：`RFQ-021 READY_FOR_CEO_RELEASE_REVIEW / NOT_DEPLOYED / NOT_MERGED`**。原工作树 `D:\\Program_Leo\\INSO_Leo\\.worktrees\\v16-rfq016-stabilization`，源码提交 `8cded532221571e99697af7668634afab3ea07af`（基线 `25894efa` + RFQ-021 改动），候选 EXE `63bcd6cea66003f84ce016cfa8742dc479a9d67ce3f579a92b5b7c398bf4465b`（8,455,788 B，2,872 文件，无 `runtime/`），清单 `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256`（`d5cc3d4c…`）已由 `verify_release_candidate.ps1` 在本地逐文件复算 2,872/2,872 一致。**RFQ-020 的 `b358f687…` 只代表旧源码，不要再引用。**

**B5/B6/B7 已在源码与测试层面关闭**：普通启动＝安全预览（无 process services / 无迁移 / 无 IMAP / 无 SMTP / 无 CDP，Start 禁用）；业务必须 `--scoped-start` 且写明订单、模块、写入目标与 `OWNER-APPROVED:` 审批串；Google 写入意图在请求前落盘，崩溃或超时留下的 UNKNOWN 会阻断同一文档后续写入，账本损坏一律 fail closed。真实候选上 `--self-check` / `--idle-self-check` / `--preview-self-check`（两轮）均 0，扫描 `RELEASE_SCAN_OK`。

**仍未做、也不得自动做**：未安装、未停机、未正常 GUI、未业务 Start、未碰生产 SQLite/Chrome9222。B3 完整回滚快照与 B4 干净停机仍需 Owner 单独批准的维护窗口；安装与业务启用各自再单独授权。`INSTALL_AND_ROLLBACK.md` 已给出步骤与中止条件，其中「默认不回滚数据库」必须遵守。

**测试如实**：完整套件 4,223 项 → 4,220 通过 / 2 失败 / 1 跳过；两处失败与未修改的父提交基线完全相同（同一 nodeid、同一现象），非本轮引入；未删除或跳过任何测试。新增 35 项负向测试全绿，受影响模块 2,886 项全绿。

**生产保护不变**：旧 V1.6 `E9E3DA33…` 与 PID 38948/34304 未动；第 221 行 SAVED `rec_440fafd372440ecf9dacabf660dd155d` 不重下；SHAHAB/115 `MANUAL_REVIEW/RECONCILIATION_UNREADABLE` 未证真实采购；3 条 V13 hold 保留；Chrome 9222、生产 SQLite/WAL/SHM、真实 Google/INSO/SMTP 一律不碰；`main`、`release/previous` 不晋升，`develop` 只同步管理文档。

## RFQ-020 CEO Review（保留记录，2026-11-14）

**结论：`RFQ-020 PASS_BUILD_AND_ISOLATED_SELF_CHECK / RELEASE_HOLD`**。使用 `workbuddy/v16-rfq016-stabilization` 原工作树，固定源码 `25894eface6ea622153d1573c19d0ca6b9ad72aa`（RFQ-018 PASS），PyInstaller BuildOnly 候选 EXE `b358f68715f9e1dadeae19d5ad5b0f517664756105ebf1fcea1b843dc482d29c`（8,436,056 B，2,872 文件，无 runtime），manifest `c8806aea…`。CEO 已从 GitHub 独立重算清单哈希并接受，但未验证 Windows EXE 实物字节、未实机执行自检。**未安装、未停机、未合并。**

**生产不变的时间边界**：22:38–22:45 自检窗口内旧 EXE/SHA/PID/SQLite/Chrome 15 页未变；之后运行中的旧版继续处理业务，DB mtime 与页数自行变化。原记录中的「23:00 观测」已在本轮更正为约 22:47（早于其提交），属记录时序错误，不涉及未授权动作。CEO 未实机归因。

**保留旧业务**：221 行 INSO SAVED `rec_440fafd372440ecf9dacabf660dd155d` 不重放；SHAHAB/115 `MANUAL_REVIEW/RECONCILIATION_UNREADABLE` 原生 INSO `NOT_VERIFIED` 不冒称成功；3 个旧 V13 quote holds 不清。最近 Executor 报告旧 EXE SHA `E9E3DA33…` app PID38948/watch34304，Chrome9222 PID24164，生产 SQLite `dist/INSO_V1.2/runtime/production/workflow.sqlite3`；均需现场重新只读确认。**不允许**无授权停旧 EXE、生产数据库备份/修改、接管 Chrome、正常 GUI、业务 Start、真实 Google/INSO/SMTP 写入、合入 develop/晋升 main 或 release。
