# RFQ-016 — 安全修复交付（第二轮，2026-11-14）

正在实现什么：

按 CEO 第二次复核 `c5d3ea50` 修复 P0-A/B/C/P1-D 四个剩余安全缺口；不重跑第 221 行、不做新的真实业务、不部署。

理想变化是什么：

手工改表格状态不能替程序确认未完成的外部操作；自动结案不能因空型号、数量/重要度变化或历史错配状态误结案；右键恢复必须把未确认的状态写入和可能已发送的采购挡住；任务中心显示「来源待核对」时，行颜色和筛选必须一致。

以前是什么：

- 采购守卫只对 `PURCHASE_EXCEPTION` 生效；`SOURCE_CHANGED`、`RESEARCH_FAILED` 等状态若历史上带着 `MANUAL_REVIEW` / `UNKNOWN_WRITE_OUTCOME`，仍可能被手工表格状态结案。
- 自动结案最后一层只按型号子串匹配，不校验数量/重要度；空型号会因 `"" in stored_model` 误通过。
- 右键恢复在采购 `SAVED` 时放行 `STATUS_WRITE_PENDING` 和 `INTERRUPTED_POSSIBLY_SENT`，但保存采购不等于 Google 状态写入/可能已发送的结果已确认。
- Workbench 实际行渲染用 `_calm`，它不看 `source_link_unproven`：筛选算「需核对」，行却画成灰色。

现在是什么：

- **所有结案路径统一检查**：durable purchase 的未确认结果、派发事件（armed/clicked/unknown/saved）和 V13 报价挂起；任何一项未结算就不结案。`SOURCE_CHANGED + MANUAL_REVIEW`、`RESEARCH_FAILED + armed event` 均有回归测试。
- **自动结案更严格**：空型号、数量变化、重要度变化不再自动结案；型号补全（`N6210`→`CELERON-N6210`）仍可自动结案。数量修正保留给显式右键恢复。
- **右键恢复**：`STATUS_WRITE_PENDING` / `INTERRUPTED_POSSIBLY_SENT` 即使采购 `SAVED` 也拒绝；`PURCHASE_RECORDED + SAVED` 等已核对状态可以通过；显式数量修正仍可完成。
- **Workbench 实际渲染**：`source_link_unproven` 现在使行 tag 为 `warning`，与「需核对」筛选一致；已确认的结案行保持 `legacy` 灰色。
- 代码已提交到原 Executor 分支（代码提交 `4b227ba67ac22a018c432d17a4fa4706844314e0`）；**未部署**。正式 EXE `E9E3DA33…`、PID `38948` 未动；第 221 行采购记录 `rec_440fafd372440ecf9dacabf660dd155d` 保留。

做完了什么：

1. **P0-A**：`_owner_completion_is_safe` 对所有可自动结案状态统一检查 durable purchase + 派发事件 + 报价 hold；台账不可信时 fail closed。头表处置路径也走同一守卫。
2. **P0-B**：`owner_resolved_status` 最后一层增加非空型号、数量、重要度校验；自动数量修正改为拒绝。显式 `resync` 保留人工数量/重要度修正能力，并仍要求唯一型号行。
3. **P0-C**：`_resync_effects_settled` 无条件拒绝 `STATUS_WRITE_PENDING` / `INTERRUPTED_POSSIBLY_SENT`（即使采购 `SAVED`）；预保存投影若存在派发事件也拒绝；`PURCHASE_RECORDED + SAVED` 可正常恢复。
4. **P1-D**：`_settled`/`_calm` 排除 `source_link_unproven`，Workbench 真实渲染 tag 改为 `warning`，新增真实 tag 路径测试；已确认结案行仍为灰色。
5. **只读核对**：用只读 Service Account 读取 SHAHAB 第 115 行，并核对 SQLite 事件/告警/V13/SMTP；未改任何数据。原生 INSO 采购回执因受保护 Chrome 会话由运行中程序持有，标记 `NOT_VERIFIED`。
6. **现场保留**：没有停止正式程序、强杀 Chrome、清 UNKNOWN/hold、恢复旧数据库、覆盖正式 EXE 或重下第 221 行。

测试结果：

- 上一轮基线：`3397` 项，`3370` 通过 / `1` 跳过 / `26` 失败。
- 本轮：`3407` 项，`3380` 通过 / `1` 跳过 / `26` 失败；26 个失败 nodeid 与基线完全一致，没有新增失败。
- 这 26 项仍是既有 launcher 共享页/已移除符号基线（`_document_barrier`、`_GoogleDocumentBarrier`、`google_resource_barrier`、`google_resource_holds`、shared admission），与本次改动无关。
- 新增 **10 项**回归，另有 1 项旧测试按新契约收紧（自动数量修正由接受改为拒绝）；`ruff check` 与 `git diff --check` 干净。
- 本轮只做只读 Google 表读取和 SQLite 只读核对，没有 INSO/SMTP 写入、没有部署、没有真实业务操作。

你接下来需要做什么：

Review RFQ-016 — 安全修复完成，请 CEO 独立复核

## 复核证据与风险

### 代码与测试

- 分支：`workbuddy/v16-rfq016-stabilization`
- 修复提交：`4b227ba67ac22a018c432d17a4fa4706844314e0`
- 改动文件：`src/workflow/v12_flow.py`、`src/sheets/purchase_status.py`、`src/launcher/backend.py`、`src/gui/workbench.py` 及对应测试。
- 机器可读证据：`docs/evidence/v16/rfq016-ceo-second-review-2026-11-14.json`（前后测试计数、26 个失败 nodeid 对比、10 个新增用例、SHAHAB/115 只读快照、EXE/PID/SQLite/Chrome 快照）。

### 只读现场

- 正式 EXE：`E9E3DA33417414ABAC53F8A88A67D9F053BCDAEAB9730EAE9AD8BD7870DFFAD0`，PID `38948`（外加 watcher `34304`）。
- 台账：60 单 = 35 人工处理完成 + 24 已发采购单 + 1 表头脏行跳过；未关闭 V12 告警 0；历史报价保护 3 条仍在。
- Chrome：仅 `127.0.0.1:9222`，PID `24164`；未操作。
- 第 221 行：采购记录 `rec_440fafd372440ecf9dacabf660dd155d` 保持，未重跑。

### SHAHAB 第 115 行只读核对（未改数据）

- 当前表格：日期 `2026-10-06`，状态 `已报价给客户`，型号 `550BG125M000DG`，品牌 `SILICON LABS / Skyworks`，数量 `8`，单位 `Pcs`。
- SQLite：采购 `MANUAL_REVIEW / RECONCILIATION_UNREADABLE`，无 `saved_record_ref`；事件包含 `SAVE_DISPATCH_ARMED`、`SAVE_OUTCOME_UNKNOWN`、`RECONCILIATION_AMBIGUOUS`；业务状态 `HUMAN_COMPLETED`（2026-10-07）；两条采购告警在 `2026-11-14T04:39:40Z` 被上一版清除；无 V13 hold；两封 `IMPORTANT_ORDER` 邮件 `SENT`。
- **原生 INSO 采购回执：`NOT_VERIFIED`**。受保护的 Chrome 9222 会话由运行中程序持有，本轮未做独立 INSO 原生读取；没有改数据、没有重放采购、没有清告警/hold。
- 结论：表格身份与台账一致、表格显示已完成，但 durable purchase 从未被证明保存；这不是成功采购的证据。是否需要单独重开/核对，请 CEO/Owner 决定。

### 保留风险

- 3 条历史 V13 报价挂起（`inq_d65be9df…`、`inq_71f4a2f5…`、`unresolved:0ca37229…`）保持；旧 `inq_d65be9df…` 报价输入失败仍在循环重试。
- 其他已知问题保持记录、未扩大修复范围：报价重跑拒绝原因未落库、GUI 停刷、暂停时退出卡住、浏览器残留空白页。
- 当前运行的正式 EXE 仍是修复前代码；源码修复、测试和部署是四件事，部署/晋升须另行批准。
- **残余限制**：Google 表格没有稳定的行 ID。若旧行被另一笔“完全相同物料/数量/重要度”的订单原地替换，单凭单元格无法区分；本轮未观察到这种情况。

### 技术定位

[Task Spec](TASK_SPEC.md) · [执行检查点](EXECUTION_LOG.md) · [CEO Review](REVIEW.md) · [历史报告](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/FINAL_REPORT.md)
