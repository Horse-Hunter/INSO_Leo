# INSO LEO — CEO/Executor 接管入口（2026-11-14）

先显式打开 `develop` 的 [AI_START_HERE](../AI_START_HERE.md)、[AGENTS](../AGENTS.md)、[BRANCH_POLICY](../docs/BRANCH_POLICY.md)、[COORDINATION](COORDINATION.md)，再看 [RFQ-018 CEO 最终 Review](RFQ-018/REVIEW.md)、[执行证据](RFQ-018/EXECUTION_LOG.md) 和 [测试映射](RFQ-018/TEST_MAPPING.md)。**默认 `main` 是历史 V1.1，不是安全新源码。** 旧 Executor 窗口结束不表示 Windows 程序已经停止。

**RFQ-018 当前结论：`PASS_SOURCE_SAFETY_SCOPE / RELEASE_HOLD`。** 最新原 Executor 分支 `workbuddy/v16-rfq016-stabilization` 固定代码 `25894eface6ea622153d1573c19d0ca6b9ad72aa`；CEO 已独立 GitHub 审核 P0-A、P0-B、P1-C 的真实修复与负向测试，不再要求为同三项继续补丁。Executor 报告原 RFQ-017 26 失败 nodeid 全通过、总 28 项保护新测试全绿、全树 4187 PASS/1 SKIP/0 FAIL；CEO 未独立运行 Windows pytest，也未做真实生产验证。代码**未合入 `develop`，未部署新 EXE**。

**发布额外安全门槛：** 共享 Google document hold / 原子在途 lease **只在进程内**，重启会清除；不要据此宣称旧 UNKNOWN 已结算。per-order V13 持久 hold 保留但不是覆盖所有跨服务 Google 写入的保证。发布准备须先制定**重启/崩溃后的未知效果恢复与隔离策略**，锁定源码 SHA↔候选 build/EXE SHA↔配置↔回滚↔真实启动证据；GUI 停刷/退出卡住/残留 Chrome 页与报价重试拒绝同属独立发布风险。下一个任务建议 RFQ-019 先**只读/离线发布准备审计**，不是自动部署。

**最近 Executor 现场只读快照（非 CEO 当前观察）**：旧 EXE `D:\\Program_Leo\\INSO_Leo\\dist\\INSO_V1.6\\INSO_V1.6.exe` SHA `E9E3DA33…`、app PID38948/watch34304；Chrome9222 owner24164；生产 SQLite `dist/INSO_V1.2/runtime/production/workflow.sqlite3`；221 行原采购 SAVED `rec_440fafd372440ecf9dacabf660dd155d` 不重下；SHAHAB/115 `MANUAL_REVIEW/RECONCILIATION_UNREADABLE` 无收据、原生 INSO `NOT_VERIFIED`，真实采购未知；3 条 V13 quote hold 不清。以上必须在下一次操作前由 Executor 只读刷新核对。

**不允许无授权**修改真实 Sheets/INSO/SMTP、停旧 EXE/覆盖安装、占用/关闭受保护 Chrome CDP9222、写 SQLite/WAL/SHM、清 UNKNOWN/SENT/hold、修改 `main`/`release/previous`、或合入业务源码到 `develop`。只有 Owner 明确批准具体集成/试运行部署/现版晋升后才可操作。更换窗口需复用原工作树，先检查 HEAD/status/worktrees/现场运行中的进程并完成交接。
