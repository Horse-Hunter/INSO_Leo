# INSO LEO — CEO/Executor 接管入口（2026-11-15 R4）

**当前唯一 CEO 结论：`RFQ-021-R3 CHANGES_REQUESTED / RELEASE_HOLD / NOT_DEPLOYED`；R4 执行结果待独立复核。** [独立审核及 R4 验收范围](RFQ-021/REVIEW.md)；[当前指挥状态](COORDINATION.md)。R3 Executor 的 `PASS_SOURCE_SCOPE` 是历史自测记录，R4 的执行记录同样是自测，二者都不是发布许可。

**R4 已提交待审：`2ad471e7` → 候选 `19918185…`（8,459,710 B / 2,872 文件 / 清单 `2de4df2f…`，逐文件 2,872/2,872 PASS），三种自检 0，安装门禁离线 13 项 PASS。**差异、审计矩阵与失败 nodeid 见 [EXECUTION_LOG](RFQ-021/EXECUTION_LOG.md) 的 R4 段。**R4 自测 PASS 不等于 CEO 通过，也不构成部署授权。**

**高效接管顺序：** 先显式读 **`develop`** 的 [AI_START_HERE](https://github.com/Horse-Hunter/INSO_Leo/blob/develop/AI_START_HERE.md)、[AGENTS（Lean Review）](https://github.com/Horse-Hunter/INSO_Leo/blob/develop/AGENTS.md) 和 [BRANCH_POLICY](https://github.com/Horse-Hunter/INSO_Leo/blob/develop/docs/BRANCH_POLICY.md)；再读本分支本文件、`COORDINATION.md`、`RFQ-021/REVIEW.md` 和执行日志最新 R3 记录。先比对固定源码 `1ef20c81` 的差异与关键效果路径，不重复通读历史文件。恢复原 Executor 工作树前核实本地 HEAD/status/diff/worktree，不清理未知改动。

**R4 仅允许离线修改和测试：** 集中修复协调器启动/轮询对范围外订单的本地状态、事件、告警影响；强制旧版回滚快照完整与有效 runtime junction；同步 `order_action_hint`。迭代时定向测试，冻结代码后一次完整测试及一次最终构建，真实结果写原 `EXECUTION_LOG.md`。任何源码变更须重建候选，不可沿用 R3 EXE 哈希。

**事故和生产：** 06:06 `SSLEOFError` → `SHEETS_READ_UNAVAILABLE` → `MODULE_PAUSED` 为确认故障类别，底层网络原因未知。10:40 旧 EXE `e9e3da33…` 与 PID 38948/34304 的读取证据有时间边界，不能宣称此刻仍然运行。B3/B4 未完成，未经 Owner 另行授权不得停机、重启、安装、真实订单/写入、碰 Chrome9222/生产 DB、清理 hold/UNKNOWN 或移动 `develop/main/release`。

## R3 Executor 历史交接（保留证据，非最新 CEO 决定）

**先访问 `develop`，不要默认 `main`**：[AI_START_HERE](../AI_START_HERE.md)、[AGENTS](../AGENTS.md)、[BRANCH_POLICY](../docs/BRANCH_POLICY.md)、[COORDINATION](COORDINATION.md)、[RFQ-021 REVIEW_R3](RFQ-021/REVIEW_R3.md)、[INC-20261115](INCIDENT-20261115.md)、[安装与回滚](RFQ-021/INSTALL_AND_ROLLBACK.md)。新窗口先 fetch 最新 develop，再核对本地 git HEAD/status/worktree 与运行中的进程。**只保留一个 Executor 工作树，不得关闭正在运行的生产程序。**

**最新结论：`RFQ-021-R3 PASS_SOURCE_SCOPE / RELEASE_HOLD / NOT_DEPLOYED`；`INC-20261115 FAULT_CLASS_CONFIRMED / UNDERLYING_CAUSE_NOT_VERIFIED`。**
源码 `1ef20c81`，候选 EXE `faa3166d41db5a738348dc57f6adebbfcda0b3dbf29eb99f3549cf0d0d2596c1`（8,459,010 B，2,872 文件），清单 `accd463a…` 已逐文件复算 2,872/2,872。**只以这一个候选为准**；r1（`63bcd6ce…`）、r2（`74586eb2…`）与各自清单已归档为历史。

**R3 修了什么**：①后台 `retry_saved_statuses`/`process()` 按范围过滤——范围外 SAVED 订单即使 google 授权也不会写 Google 或改状态；显式 `inquiry_ids` 与范围冲突直接拒绝。②一键登录在预览/受控范围下无条件拒绝（与写入权限无关）；手动动作按模块与写入族逐个审计，`edit` 需 google、`purchase` 需 inso+google。③手册源码 SHA、单一候选、R2 计数更正；安装脚本失败关闭（回滚快照复算 + DB 备份文件头 + 显式确认），不再假设旧 EXE 支持 `--safe-preview`；冷回滚与回滚后业务重启分两次审批。

**今早事件**：旧 EXE `e9e3da33417414abac53f8a88a67d9f053bcdaeab9730eae9ad8bd7870dffad0` 仍在运行（PID 38948 + 34304，11-14 13:47 启动）。06:06:49 `SSLEOFError` → `SHEETS_READ_UNAVAILABLE` → `MODULE_PAUSED`；非崩溃、无未确认外部效果。10:40 复核：日志停在 06:06:49、无 443 外连、Google 现在可建连、3 条 hold 与 0 活动告警未变、故障后 0 条业务事件。**重启旧程序属业务动作，需 Owner 单独授权。**

**测试**：4,248 项 → 4,245 通过 / 2 失败 / 1 跳过；两处失败与未修改父提交基线相同（测试临时目录只读），未删除未跳过。

**仍未做**：未安装、未停机、未重启、未碰生产 SQLite/Chrome9222、未合并或晋升。B3 完整回滚快照、B4 干净停机仍需维护窗口。

## RFQ-021-R2 定点补修（保留记录，2026-11-15 上午）

## RFQ-021-R1 首次交付（保留记录，2026-11-15 凌晨）

**结论：`RFQ-021 READY_FOR_CEO_RELEASE_REVIEW / NOT_DEPLOYED / NOT_MERGED`**。源码 `8cded532`，候选 EXE `63bcd6ce…`（8,455,788 B，2,872 文件），清单 `d5cc3d4c…`；`--self-check` / `--idle-self-check` / `--preview-self-check` 全 0。完整套件 4,223 → 4,220 通过 / 2 失败 / 1 跳过，两处失败与父提交基线相同。**未安装、未停机、未启用业务。**

## RFQ-020 CEO Review（保留记录，2026-11-14）

**结论：`RFQ-020 PASS_BUILD_AND_ISOLATED_SELF_CHECK / RELEASE_HOLD`**。使用 `workbuddy/v16-rfq016-stabilization` 原工作树，固定源码 `25894eface6ea622153d1573c19d0ca6b9ad72aa`（RFQ-018 PASS），PyInstaller BuildOnly 候选 EXE `b358f68715f9e1dadeae19d5ad5b0f517664756105ebf1fcea1b843dc482d29c`（8,436,056 B，2,872 文件，无 runtime），manifest `c8806aea…`。CEO 已从 GitHub 独立重算清单哈希并接受，但未验证 Windows EXE 实物字节、未实机执行自检。**未安装、未停机、未合并。**

**生产不变的时间边界**：22:38–22:45 自检窗口内旧 EXE/SHA/PID/SQLite/Chrome 15 页未变；之后运行中的旧版继续处理业务，DB mtime 与页数自行变化。原记录中的「23:00 观测」已在本轮更正为约 22:47（早于其提交），属记录时序错误，不涉及未授权动作。CEO 未实机归因。

**保留旧业务**：221 行 INSO SAVED `rec_440fafd372440ecf9dacabf660dd155d` 不重放；SHAHAB/115 `MANUAL_REVIEW/RECONCILIATION_UNREADABLE` 原生 INSO `NOT_VERIFIED` 不冒称成功；3 个旧 V13 quote holds 不清。最近 Executor 报告旧 EXE SHA `E9E3DA33…` app PID38948/watch34304，Chrome9222 PID24164，生产 SQLite `dist/INSO_V1.2/runtime/production/workflow.sqlite3`；均需现场重新只读确认。**不允许**无授权停旧 EXE、生产数据库备份/修改、接管 Chrome、正常 GUI、业务 Start、真实 Google/INSO/SMTP 写入、合入 develop/晋升 main 或 release。
