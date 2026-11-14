# RFQ-016 — CEO 第三轮独立 Review（2026-11-14）

**结论：`CHANGES_REQUESTED_ONE_ALERT_GAP / P0-A,B,C,P1-D_ACCEPTED / NOT_DEPLOYED / NO_VERSION_PROMOTION`.**

独立复核对象：实际源码提交 `4b227ba67ac22a018c432d17a4fa4706844314e0`，提交报告和测试证据 `dbe71772358a849a67275d239f5dadc6a89e4d24`。复核方式为 **GitHub 源码/测试代码/证据 JSON 只读检查**；CEO **未**在 Windows 现场运行 pytest、读取实时 INSO，也未执行任何 Google/INSO/SMTP 写操作。此前 Review 固定于 [`c5d3ea50`](https://github.com/Horse-Hunter/INSO_Leo/blob/c5d3ea50b127f248f5ad7f42334aff497195d5f4/control-room/RFQ-016/REVIEW.md)。

## 四项指定问题：代码复核接受

1. **P0-A 已落实**：`src/workflow/v12_flow.py:342-381` 对各类自动结案先核对 durable purchase、保存/派发事件和 V13 hold；异常投影 `SOURCE_CHANGED + MANUAL_REVIEW`、`RESEARCH_FAILED + SAVE_DISPATCH_ARMED` 的测试成立。原本 `STATUS_WRITE_PENDING`、`INTERRUPTED_POSSIBLY_SENT` 仍拒绝靠表格状态结案。
2. **P0-B 已落实**：`src/sheets/purchase_status.py:92-112` 的自动物理行兜底拒绝空型号，并核对数量、重要度；空型号/数量改变/重要度改变新增负向测试。`N6210 → CELERON-N6210` 这类经限定的型号补全保持可自动认领，但没有稳定 Sheet 行 ID 的同物料替换风险仍需记为技术限制。
3. **P0-C 已落实**：`src/launcher/backend.py:2180-2211` 中右键恢复对 `STATUS_WRITE_PENDING`、`INTERRUPTED_POSSIBLY_SENT`、`SUBMIT_UNCONFIRMED` 无条件阻止；未确认采购 / 派发事件阻止；已确认 `PURCHASE_RECORDED + SAVED` 有正向测试。人工明确右键动作仍允许数量/重要度修正，**这并非自动结案许可**。
4. **P1-D 已落实**：`src/gui/workbench.py:129-138,794-803` 的 `_calm/_settled` 已排除 `source_link_unproven`，`tests/gui/test_newest_orders.py:96-114` 测试真实 `render_orders` tag，来源不明显示 `warning`，可靠的已结案显示 `legacy`。

**测试证据核对**：机器可读 `docs/evidence/v16/rfq016-ceo-second-review-2026-11-14.json` 中，前后 26 个失败 nodeid **顺序及内容完全一致**，基线 3397=3370pass+26fail+1skip → 最终 3407=3380pass+26fail+1skip。新增 10 个具名用例、一个旧数量修正测试收紧，无删除的 nodeid。执行者报告 `ruff`、`git diff --check` 通过；CEO **未独立执行**套件。26 个 launcher/共享页面准入相关失败仍是**真实未关闭的测试基线，不得称全绿**；是否因历史接口而过时须另行以源码与用例核实，不能仅凭“与本次无关”就认定生产安全。

## 唯一剩余本轮告警闭环缺口（定点补修，不扩大范围）

**P1-E — 表头脏行处置仍有不受限的“全告警恢复”。** 在 `src/workflow/v12_flow.py:410-417`，`_SOURCE_HEADER_WORDS` 路径已调用 `_owner_completion_is_safe`，这点本轮修复是正确的；但进入 `INVALID_INPUT_SKIPPED` 后仍调用 `self._v12_store.recover_stale_alerts(item.inquiry_id, at=now)`，没有传 `alert_types`。`src/workflow/v12_store.py:504-536` 说明缺省时会恢复该订单**全部活跃告警**，包括 `NOTIFICATION_FAILED`、`SECURITY_EVENT`，即使它们并未被表头脏行结案证明已经解决。这一历史路径与当前“只清实际已经解答的数据质量告警”制度不一致；不应靠零告警证明零风险。

**最小变更要求**：此分支只把表头处置所清的告警收窄到有证据表明已处理的 `DATA_QUALITY`（必要时进一步限定 scope），保留任何邮件、安全、UNKNOWN 类真实告警；新增至少 1 个模拟表头输入 + `NOTIFICATION_FAILED` + `SECURITY_EVENT` 的确定性测试，证明只恢复允许的类别、事件与 recipient `SENT/UNKNOWN` 不变。若需要其他变更，应先更新 Review 解释原因。**不需重新安排第 221 行实单、Chrome 操作或生产部署。**

## SHAHAB/115：业务核实仍未完成，禁止擅自更改历史

对 `inq_99275e8e72b43fd6616fd686`，已核对 Executor 提供的只读 Google Sheet 与 SQLite 证据：`SHAHAB` 115 行 `550BG125M000DG` qty8，表格状态 `已报价给客户`，身份与存档一致；但采购 `MANUAL_REVIEW / RECONCILIATION_UNREADABLE`、无 `saved_record_ref`，`SAVE_DISPATCH_ARMED` 与后续 `SAVE_OUTCOME_UNKNOWN` 存在。**`HUMAN_COMPLETED` 状态是 2026-10-07 的历史状态，`SAVE_OUTCOME_UNKNOWN` 等告警于 2026-11-14 04:39:40Z 才被旧版恢复；这两次事件不是同一天。** 已发送两份 IMPORTANT_ORDER 通知、无 V13 hold，并不能证明采购保存。Native INSO 收据 **`NOT_VERIFIED`**，真实采购效果必须继续按 UNKNOWN 对待。

**CEO 决策**：允许继续收集不抢占 Chrome 9222 的只读凭据/后台记录，但**不授权**更新业务状态、重开/补发、重做采购、修复 SQLite、恢复历史告警、重新发送邮件或关闭受保护 Chrome 会话。待原生 INSO 采购结果可证明后，提交单独 Owner 决议，不让此次源码 Review 隐式改变业务现场。

## 部署/版本/交接

- 运行中 EXE 的最近一次 **Executor 报告**：`E9E3DA33417414ABAC53F8A88A67D9F053BCDAEAB9730EAE9AD8BD7870DFFAD0`，PID38948（watcher34304）；**仍是修复前的试运行代码**，CEO 未重新观测现场。221 行 `rec_440fafd372440ecf9dacabf660dd155d` 保持；未重发。V13 三条 hold 及报价失败、GUI 停刷、退出卡住、遗留空白页继续保留。
- **不合并代码、不部署 EXE、不修改 `main` / `release/previous`**。原 Executor 先提交 P1-E 单项最小修复、针对性测试、原 26-nodeid 比对，回复 `Review RFQ-016`。之后 CEO 可以就**本轮专项源码/离线测试**给出 PASS 或 FAIL，生产试运行及 Git 现版晋升是不同的 Owner 审批关口。
- GitHub `develop` 为管理/前瞻集成线，业务修复暂在 `workbuddy/v16-rfq016-stabilization` 工作分支。按 [三分支制度](https://github.com/Horse-Hunter/INSO_Leo/blob/develop/docs/BRANCH_POLICY.md)：即使编译覆盖并长期运行，也不自动晋升现版。
