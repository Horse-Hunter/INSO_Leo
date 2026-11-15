# INSO LEO — CEO/Executor 接管入口（2026-11-15 上午）

**先访问 `develop`，不要默认 `main`**：[AI_START_HERE](../AI_START_HERE.md)、[AGENTS](../AGENTS.md)、[BRANCH_POLICY](../docs/BRANCH_POLICY.md)、[COORDINATION](COORDINATION.md)、[RFQ-021 REVIEW_FOLLOWUP](RFQ-021/REVIEW_FOLLOWUP.md)、[INC-20261115](INCIDENT-20261115.md)、[安装与回滚](RFQ-021/INSTALL_AND_ROLLBACK.md)。新窗口先 fetch 最新 develop，再核对本地 git HEAD/status/worktree 与运行中的进程。**只保留一个 Executor 工作树，不得关闭正在运行的生产程序。**

**最新结论：`RFQ-021-R2 PASS_SOURCE_SCOPE / RELEASE_HOLD / NOT_DEPLOYED`；`INC-20261115 ROOT_CAUSE_CONFIRMED`。** 源码 `1314da5d`（基线 `8cded532` + 三个 P0 修复），候选 EXE `74586eb29ed19e037e2045f481d4ed2226aa555a8f6ef7951028c873fa68d0ed`（8,457,679 B，2,872 文件），清单 `74ae29c7…` 已逐文件复算 2,872/2,872。上一版 `63bcd6ce…` 已归档为 r1，不再代表当前源码。

**三个 P0 已修**：范围真正绑定到业务编排（此前 `inquiry_ids=None`＝全量处理）；邮件服务改由 `may_start_process_services()` 把关（预览恒不启动，受控模式需 notification+smtp 同时授权）；订单邮件、一键登录、单笔动作在预览与越界订单上双层拒绝。**代价**：报价/TP/通知没有按订单过滤能力，现在被直接拒绝而不是假装受控；`smtp` 也不能作为写入目标。受控试运行目前只支持 `inquiry` + 指定订单。

**今早发生了什么**：运行的是旧 EXE `E9E3DA33…`（PID 38948 + watcher 34304，11-14 13:47 启动）。06:06:49 报价模块读取 Google Sheets 时 `SSLEOFError` → `SHEETS_READ_UNAVAILABLE` → `MODULE_PAUSED`。不是崩溃（fatal.log 空、无 Windows 应用错误事件），没有产生未确认外部效果（故障后 0 条业务事件、采购状态/3 条 hold/告警均未变）。界面四行提示是同一故障的连带展示。**是否重启旧程序属业务动作，需 Owner 单独授权；重启前先确认到 Google 的连通性。**

**仍未做**：未安装、未停机、未重启、未碰生产 SQLite/Chrome9222、未合并或晋升。B3/B4 仍需维护窗口。**可用性问题**：一次 TLS 抖动就停到人工介入（`SSLEOFError` 未被当作可恢复读），建议另开有界任务，本轮按"不扩大范围"未改。

## RFQ-021-R1 首次交付（保留记录，2026-11-15 凌晨）

**结论：`RFQ-021 READY_FOR_CEO_RELEASE_REVIEW / NOT_DEPLOYED / NOT_MERGED`**。源码 `8cded532`，候选 EXE `63bcd6ce…`（8,455,788 B，2,872 文件），清单 `d5cc3d4c…`；`--self-check` / `--idle-self-check` / `--preview-self-check` 全 0。完整套件 4,223 → 4,220 通过 / 2 失败 / 1 跳过，两处失败与父提交基线相同。**未安装、未停机、未启用业务。**

## RFQ-020 CEO Review（保留记录，2026-11-14）

**结论：`RFQ-020 PASS_BUILD_AND_ISOLATED_SELF_CHECK / RELEASE_HOLD`**。使用 `workbuddy/v16-rfq016-stabilization` 原工作树，固定源码 `25894eface6ea622153d1573c19d0ca6b9ad72aa`（RFQ-018 PASS），PyInstaller BuildOnly 候选 EXE `b358f68715f9e1dadeae19d5ad5b0f517664756105ebf1fcea1b843dc482d29c`（8,436,056 B，2,872 文件，无 runtime），manifest `c8806aea…`。CEO 已从 GitHub 独立重算清单哈希并接受，但未验证 Windows EXE 实物字节、未实机执行自检。**未安装、未停机、未合并。**

**生产不变的时间边界**：22:38–22:45 自检窗口内旧 EXE/SHA/PID/SQLite/Chrome 15 页未变；之后运行中的旧版继续处理业务，DB mtime 与页数自行变化。原记录中的「23:00 观测」已在本轮更正为约 22:47（早于其提交），属记录时序错误，不涉及未授权动作。CEO 未实机归因。

**保留旧业务**：221 行 INSO SAVED `rec_440fafd372440ecf9dacabf660dd155d` 不重放；SHAHAB/115 `MANUAL_REVIEW/RECONCILIATION_UNREADABLE` 原生 INSO `NOT_VERIFIED` 不冒称成功；3 个旧 V13 quote holds 不清。最近 Executor 报告旧 EXE SHA `E9E3DA33…` app PID38948/watch34304，Chrome9222 PID24164，生产 SQLite `dist/INSO_V1.2/runtime/production/workflow.sqlite3`；均需现场重新只读确认。**不允许**无授权停旧 EXE、生产数据库备份/修改、接管 Chrome、正常 GUI、业务 Start、真实 Google/INSO/SMTP 写入、合入 develop/晋升 main 或 release。
