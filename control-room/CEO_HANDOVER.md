# INSO LEO — CEO/Executor 接管入口（2026-11-14）

**先明确选 `develop`**，再读 [AI_START_HERE](../AI_START_HERE.md)、[AGENTS](../AGENTS.md)、[BRANCH_POLICY](../docs/BRANCH_POLICY.md)、[COORDINATION](COORDINATION.md)、[RFQ-017 CEO Review](RFQ-017/REVIEW.md)、[RFQ-017 审计](RFQ-017/AUDIT_REPORT.md)、[RFQ-016 PASS](RFQ-016/REVIEW.md)。GitHub 默认 `main` 为历史 V1.1、不是现行安全源码。新窗口须检查原工作树/HEAD/未提交改动及实时进程；旧模型窗口消失≠程序停止。

**最新 CEO 裁决：`RFQ-017 PASS_AUDIT_SCOPE / RELEASE_HOLD`**。Executor 在原 `workbuddy/v16-rfq016-stabilization` 工作树完成 26 项失败的只读归因，提交 `f790d5ad` + `38e482f9` 文档及 [JSON](../docs/evidence/rfq017/rfq017-test-audit-2026-11-14.json)。执行者报告 26 failed（4.76s）、另 4133 passed/1skip/26 deselected 的完整树对照。CEO 检查 GitHub 源码和测试、未在 Windows 亲跑。报告“21 旧测试、5 防御纵深缺口，MEDIUM 不阻断受控试运行”**没有全部获批**：11 个 API 不存在仅证明测试引用失效；另 10 个旧行为测试是否被等价保护替代 **NOT_VERIFIED**；5 个确认的 Google 跨客户端隔离/销售订单共享准入缺口必须在有真实外部效果前治理。发布仍 **HOLD**；不能偷偷排除 26 项宣称全绿。

**RFQ-016 已通过专项源码审计**（最后补丁 `b45e870e`）；新源码未合入 `develop`、未部署到 EXE。下一技术任务建议 RFQ-018：离线制定两类 fail-closed 契约 + 保护性负向回归 + 最小源码修复/测试等价审计，然后向 CEO 申请 Review。**不得把 RFQ-017 PASS 当作部署授权。**

**最近 Executor 生产只读快照（非 CEO 实时核查）**：EXE `D:\\Program_Leo\\INSO_Leo\\dist\\INSO_V1.6\\INSO_V1.6.exe` SHA `E9E3DA33…` app PID38948/watcher34304；Chrome 9222 owner24164；SQLite `dist/INSO_V1.2/runtime/production/workflow.sqlite3`，221 行 SAVED `rec_440fafd372440ecf9dacabf660dd155d`，不能重下；SHAHAB/115 采购 `MANUAL_REVIEW/RECONCILIATION_UNREADABLE` 无 saved receipt，原生 INSO `NOT_VERIFIED`，保持 UNKNOWN；3 条旧 V13 quote hold 不清。其他报价循环失败、GUI 停刷、关闭卡死、残留页另列风险，不在 RFQ-017 执行范围内。

**下一 Owner 动作**：若同意，单独授权下一 RFQ-018 的**离线源码/测试修复**。授权前只能做原已允许的只读盘点；不自动部署、重启、抢占共享 Chrome、动 SQLite/WAL/SHM、进行真实 Sheets/INSO/SMTP 操作，或晋升 `main`。固定源码/EXE/回滚对照和真实试运行另开发布审批。
