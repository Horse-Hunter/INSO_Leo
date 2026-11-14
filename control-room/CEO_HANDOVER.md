# INSO LEO — CEO/Executor 接管入口（2026-11-14）

**强制入口**：从 `develop` 的 [AI_START_HERE](../AI_START_HERE.md) → [AGENTS](../AGENTS.md) → [BRANCH_POLICY](../docs/BRANCH_POLICY.md) → [COORDINATION](COORDINATION.md) → [RFQ-016 REVIEW](RFQ-016/REVIEW.md) → [EXECUTION_LOG](RFQ-016/EXECUTION_LOG.md) 阅读。GitHub 默认 `main` 是历史 V1.1，**不要当作最新开发或已批准现版**。

**当前唯一任务：RFQ-016 的 P1-E 告警恢复边界。** Executor 原工作树在 `D:\\Program_Leo\\INSO_Leo\\.worktrees\\v16-rfq016-stabilization`，代码 `4b227ba6`、报告 `dbe71772`，分支 `workbuddy/v16-rfq016-stabilization`，**未部署、未合并**。CEO 第三轮 Review 接受前四项 P0-A/B/C/P1-D；只剩表头脏行路径的 `recover_stale_alerts` 缺少 `alert_types`，可能错误恢复真实邮件/安全告警；[审核说明和回归门槛](RFQ-016/REVIEW.md)。请原 Executor 单独最小修复，不扩大任务。

**最近 Executor 只读生产快照（不是 CEO 实机观察）**：EXE `D:\\Program_Leo\\INSO_Leo\\dist\\INSO_V1.6\\INSO_V1.6.exe` SHA256 `E9E3DA33…`；app PID38948/watch PID34304；Chrome 9222 PID24164；SQLite `INSO_V1.2/runtime/production/workflow.sqlite3`；221 行 SAVED receipt `rec_440fafd372440ecf9dacabf660dd155d`，不能再下单。3 条 V13 quote hold 未清。运行程序仍是修复前代码；会话退出不证明程序停。

**SHAHAB/115 必须独立记风险**：`inq_99275e8e72b43fd6616fd686` 表格 `已报价给客户`、型号/数量匹配，SQLite 却 `MANUAL_REVIEW / RECONCILIATION_UNREADABLE` 无 saved receipt。业务 `HUMAN_COMPLETED` 发生于 2026-10-07，告警消失发生于 2026-11-14；**原生 INSO 收据 NOT_VERIFIED**。仅允许不破坏原 Chrome/业务现场的只读检查；任何重开、重发、SQL 修复、改告警都需单独 Owner 决策。不要误报已经结案成功。

**测试**：Executor 报告 3407 collected / 3380 pass /26 legacy fail /1skip，新增 10；CEO 核对了 JSON 中完全相同的 26 failed nodeid，但没有在 Windows 运行 pytest。补修后继续提供原 26 个失败项比较，别删除/跳过安全测试。

下一步：只读检查 `git status`/worktree/真实进程，P1-E 最小源码+单项负向回归，离线测试，更新原报告并请求 `Review RFQ-016`。不重下 221、不改 SQLite、不中断 Chrome、不安装 EXE、不合并代码、不晋升 `main`。
