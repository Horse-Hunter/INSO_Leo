# RFQ-016 — 安全修复交付（第三轮补修，2026-11-14）

正在实现什么：

按 CEO 第三轮 Review `57561e5b` 只补 P1-E：表头脏行处置不得顺手清掉邮件、安全或 UNKNOWN 类真实告警；不重跑第 221 行、不部署。

理想变化是什么：

表头脏行结案只清它真正解答的数据质量告警；邮件失败、安全事件、采购未知等告警继续留在任务中心，不能靠“零告警”证明零风险。

以前是什么：

表头脏行进入 `INVALID_INPUT_SKIPPED` 后调用 `recover_stale_alerts` 没有传 `alert_types`，缺省会恢复该订单**全部活跃告警**，包括 `NOTIFICATION_FAILED`、`SECURITY_EVENT`。这一历史路径与“只清实际已经解答的数据质量告警”的制度不一致。

现在是什么：

- 表头路径只恢复 `DATA_QUALITY` 告警；邮件、安全、采购未知类告警保留，recipient 的 `SENT`/`UNKNOWN` 不变。
- 表头路径仍先走 `_owner_completion_is_safe`；前两轮 P0-A/B/C/P1-D 的采购/派发/报价守卫、自动结案身份校验、右键恢复拦截、Workbench 行颜色都保持。
- 代码已提交到原 Executor 分支（代码提交 `b45e870e328bab1183ae0a5478911d6c4575641f`）；**未部署**。正式 EXE `E9E3DA33…`、PID `38948` 未动；第 221 行采购记录 `rec_440fafd372440ecf9dacabf660dd155d` 保留。
- SHAHAB 第 115 行只读结论不变：表格 `已报价给客户`、身份一致，但 durable purchase 仍是 `MANUAL_REVIEW`、无 saved receipt；原生 INSO `NOT_VERIFIED`。本轮没有改任何业务数据。

做完了什么：

1. **P1-E 最小修复**：`src/workflow/v12_flow.py` 表头处置改为 `recover_stale_alerts(..., alert_types={DATA_QUALITY})`；不动其他结案路径、不动 schema、不加依赖。
2. **确定性回归**：新增 `test_header_row_recovery_only_clears_data_quality_alerts`，模拟表头输入 + `DATA_QUALITY` + `NOTIFICATION_FAILED` + `SECURITY_EVENT` + 两个 recipient（`SENT`/`UNKNOWN`），证明只恢复 `DATA_QUALITY`，其余告警和 recipient 状态不变。修复前该测试失败（全部告警被清），修复后通过。
3. **全量比对**：重跑相关套件，26 个失败 nodeid 与基线完全一致，没有新增失败。
4. **现场保留**：没有停止正式程序、强杀 Chrome、清 UNKNOWN/hold、恢复旧数据库、覆盖正式 EXE、重下第 221 行或发邮件。
5. **历史风险不变**：SHAHAB/115 仍是未证明的采购结果；是否单独重开/核对，需 CEO/Owner 另行决定。

测试结果：

- 上一轮基线：`3407` 项，`3380` 通过 / `1` 跳过 / `26` 失败。
- 本轮：`3408` 项，`3381` 通过 / `1` 跳过 / `26` 失败；26 个失败 nodeid 与基线完全一致。
- 新增 **1 项**回归；没有删除、跳过或放宽任何保护性测试。`ruff check` 与 `git diff --check` 干净。
- 本轮只做源码/离线测试，没有 Google/INSO/SMTP 写入、没有部署、没有真实业务操作。

你接下来需要做什么：

Review RFQ-016 — 安全修复完成，请 CEO 独立复核

## 复核证据与风险

### 代码与测试

- 分支：`workbuddy/v16-rfq016-stabilization`
- P1-E 修复提交：`b45e870e328bab1183ae0a5478911d6c4575641f`
- 改动文件：`src/workflow/v12_flow.py`、`tests/workflow/test_v12_flow.py`
- 机器可读证据：`docs/evidence/v16/rfq016-ceo-third-review-2026-11-14.json`（前后计数、26 个失败 nodeid 对比、1 个新增用例、EXE/PID/SQLite/Chrome 快照）。

### 只读现场

- 正式 EXE：`E9E3DA33417414ABAC53F8A88A67D9F053BCDAEAB9730EAE9AD8BD7870DFFAD0`，PID `38948`（外加 watcher `34304`）。
- 台账：60 单 = 35 人工处理完成 + 24 已发采购单 + 1 表头脏行跳过；未关闭 V12 告警 0；历史报价保护 3 条仍在。
- Chrome：仅 `127.0.0.1:9222`，PID `24164`；未操作。
- 第 221 行：采购记录 `rec_440fafd372440ecf9dacabf660dd155d` 保持，未重跑。

### SHAHAB 第 115 行（沿用上一轮只读核对，本轮未改）

- 当前表格：日期 `2026-10-06`，状态 `已报价给客户`，型号 `550BG125M000DG`，品牌 `SILICON LABS / Skyworks`，数量 `8`，单位 `Pcs`。
- SQLite：采购 `MANUAL_REVIEW / RECONCILIATION_UNREADABLE`，无 `saved_record_ref`；事件包含 `SAVE_DISPATCH_ARMED`、`SAVE_OUTCOME_UNKNOWN`、`RECONCILIATION_AMBIGUOUS`；业务状态 `HUMAN_COMPLETED`（2026-10-07）；两条采购告警在 `2026-11-14T04:39:40Z` 被上一版清除；无 V13 hold；两封 `IMPORTANT_ORDER` 邮件 `SENT`。
- **原生 INSO 采购回执：`NOT_VERIFIED`**；没有改数据、没有重放采购、没有清告警/hold。表格已完成不等于采购已保存，真实采购效果继续按 UNKNOWN 对待。

### 保留风险

- 3 条历史 V13 报价挂起（`inq_d65be9df…`、`inq_71f4a2f5…`、`unresolved:0ca37229…`）保持；旧 `inq_d65be9df…` 报价输入失败仍在循环重试。
- 其他已知问题保持记录、未扩大修复范围：报价重跑拒绝原因未落库、GUI 停刷、暂停时退出卡住、浏览器残留空白页。
- 当前运行的正式 EXE 仍是修复前代码；源码修复、测试和部署是四件事，部署/晋升须另行批准。
- **残余限制**：Google 表格没有稳定的行 ID。若旧行被另一笔“完全相同物料/数量/重要度”的订单原地替换，单凭单元格无法区分；本轮未观察到这种情况。

### 技术定位

[Task Spec](TASK_SPEC.md) · [执行检查点](EXECUTION_LOG.md) · [CEO Review](REVIEW.md) · [历史报告](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/FINAL_REPORT.md)
