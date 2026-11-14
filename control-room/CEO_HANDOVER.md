# INSO LEO — CEO/Executor 接管入口（2026-11-14）

**必须显式先看 `develop`：** [AI_START_HERE](../AI_START_HERE.md)、[AGENTS](../AGENTS.md)、[BRANCH_POLICY](../docs/BRANCH_POLICY.md)，再看 [COORDINATION](COORDINATION.md)、[RFQ-018 CEO Review](RFQ-018/REVIEW.md)、[RFQ-018 任务说明](RFQ-018/TASK_SPEC.md)、[执行记录](RFQ-018/EXECUTION_LOG.md)、[测试映射](RFQ-018/TEST_MAPPING.md)。默认 GitHub `main` 仍是历史 V1.1；不能拿它当新源码。新 Executor 接手先查本地 Git/进程/未提交内容，不创建多余工作树或重复业务进程。

**当前唯一任务：RFQ-018 第一轮 `CHANGES_REQUESTED` 定点补修。** 原 Executor 代码 `446d090998e8e2845aae2b23d9cae59f465a789c`，分支 `workbuddy/v16-rfq016-stabilization`，原工作树 `D:\\Program_Leo\\INSO_Leo\\.worktrees\\v16-rfq016-stabilization`。新增共享文档保护/销售准入、16 个测试；原 26 项据 Executor 全部 PASS，全树据 Executor 4175 pass/1 skip/0 fail。CEO GitHub 静态审查找到 **P0-A 页面关闭自动清掉未确认写 hold**、**P0-B API 失效准入仍可写/私有根绕过**、**P1-C 在途并发写未原子占用而旧串行线程测试被弱化**。细节、源码位置和具体负向测试写在 [REVIEW](RFQ-018/REVIEW.md)。仅修这三项及相邻测试意图，不扩大框架；测试先红后绿，重跑原 26、新 16、全树，再请求 `Review RFQ-018`。不得为了全绿删测/skip。

**业务资产不动（以下 PID 为之前 Executor 只读报告，不是 CEO 当前实时验证）**：旧 EXE SHA `E9E3DA33…` PID38948 + watcher34304，Chrome CDP9222 PID24164，SQLite `dist/INSO_V1.2/runtime/production/workflow.sqlite3`。221 行已 SAVED `rec_440fafd372440ecf9dacabf660dd155d` 禁止重下；SHAHAB/115 采购 `MANUAL_REVIEW/RECONCILIATION_UNREADABLE` 无收据，native INSO `NOT_VERIFIED`，不得冒称成功；3 条 V13 quote holds 保留。不重启/覆盖 EXE、不访问 Chrome、不可改 SQLite/WAL/SHM、不做真实 Google/INSO/SMTP 操作、不清 UNKNOWN 或 hold。源码未合并 `develop`，`main` 晋升仅 Owner 明确验收后可做。

**CEO 裁决范围**：RFQ-016 专项源码安全 PASS、RFQ-017 审计 PASS 不改变；RFQ-018 **尚未源码 PASS**，任何部署、真实效果试运行、代码合入及版本晋升都需独立 Owner 授权。本次 CEO 未独立运行 pytest。
