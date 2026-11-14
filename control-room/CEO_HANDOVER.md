# INSO LEO — CEO/Executor 接管入口（2026-11-14）

**入口：** 必须先显式打开 `develop` 的 [AI_START_HERE](../AI_START_HERE.md)、[AGENTS](../AGENTS.md)、[BRANCH_POLICY](../docs/BRANCH_POLICY.md)、[COORDINATION](COORDINATION.md)，再看 [RFQ-016 CEO 最终专项 Review](RFQ-016/REVIEW.md) 与 [执行检查点](RFQ-016/EXECUTION_LOG.md)。GitHub 默认 `main` 仍是旧 V1.1 代码，不能当作最新版本。旧 Agent 窗口关闭不意味着 Windows 业务进程停止。

**当前 RFQ-016 结果：`PASS_SOURCE_SAFETY_SCOPE / RELEASE_HOLD`。** P0-A/B/C、P1-D、P1-E 指定漏洞源码静态审核全部完成，不再做同一 RFQ 的循环补丁。最后源码补丁 `b45e870e328bab1183ae0a5478911d6c4575641f`；报告和比较证据 `95e9b186de83741d34c6f7527e6b12d3acadff92`，原分支 `workbuddy/v16-rfq016-stabilization`（工作树 `D:\\Program_Leo\\INSO_Leo\\.worktrees\\v16-rfq016-stabilization`）。**业务源码未合并至 `develop`，正式 EXE 未部署修复。** 上次 CEO Review 仅查看 GitHub，并非 Windows / 真实采购重验。

**测试/下一工作流**：Executor 报告 3408 tests：3381 PASS /1 SKIP /26 FAIL，26 个失败 nodeid 与上版完全一致；CEO 查验了已提交 JSON 与修复代码，未重跑测试。26 个旧失败集中在 launcher Google 共享准入 / barrier / hold，可能涉及保护要求，**不能因为是基线就忽略**。先单独做离线诊断与发布评估，明确修复或 Owner 对具体残余风险的决定。仅有本 RFQ 源码 PASS 不能直接覆盖运行中 EXE。

**最近 Executor 只读 Windows 快照（非 CEO 当前观察）**：`D:\\Program_Leo\\INSO_Leo\\dist\\INSO_V1.6\\INSO_V1.6.exe` SHA256 `E9E3DA33…`，app PID38948 / watcher34304；Chrome CDP 9222 owner PID24164；SQLite `D:\\Program_Leo\\INSO_Leo\\dist\\INSO_V1.2\\runtime\\production\\workflow.sqlite3`。221 行报告 INSO SAVED receipt `rec_440fafd372440ecf9dacabf660dd155d`，不可重复下单；3 条 V13 quote hold 均保留，`inq_d65be9df…` 失败未处理。没有任何版本晋升或生产部署授权。

**独立历史真实订单风险 SHAHAB/115：** `inq_99275e8e72b43fd6616fd686`，料号 `550BG125M000DG`，qty8；Google 已报价给客户，与台账身份一致；SQLite purchase `MANUAL_REVIEW / RECONCILIATION_UNREADABLE`，无 saved receipt，`SAVE_DISPATCH_ARMED` + `SAVE_OUTCOME_UNKNOWN` 存在；旧版于 2026-11-14 恢复告警。原生 INSO 收据 `NOT_VERIFIED`。**保持真实业务 UNKNOWN**，仅可做不抢占原 Chrome 的只读收证，不得自动修历史数据库、重开/重下单、清保护或发信。未来需单独 Owner 决定。

**下一步：** 在原工作树只读核对 `git status` / HEAD / worktrees、真实 Windows 进程/SQLite/WAL/SHM/Chrome；提出 26 失败逐项归因及安全发布候选计划。**任何生产停机、部署、合入修复源码至 `develop`、真实外部效果或晋升 `main` 都必须有另行授权。** `develop` 前瞻试运行≠ Owner 已批准现版；`release/previous` 仍是待核实旧版候选。
