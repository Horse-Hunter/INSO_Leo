# RFQ-019 — CEO 独立发布准备 Review（2026-11-14）

**结论：`PASS_RELEASE_PREP_AUDIT / NORMAL_GUI_AND_BUSINESS_TRIAL_BLOCKED / STAGING_BUILD_NOT_YET_AUTHORIZED / NOT_DEPLOYED / NOT_MERGED`。** 本结论**认可只读发布风险评估的完整性及实质性阻断判断**，不批准现阶段真实 GUI/业务启动、旧 EXE 停机安装或版本晋升。

## Review 结论

- Executor `505d9590a2726c0ec27f2c090d28616e528a6470` 相对上一轮 CEO `45621923` **只添加/修改 RFQ-019 文档和 JSON**；GitHub diff 无源码、测试、生产配置改动。固定 RFQ-018 已通过的源码为 `25894eface6ea622153d1573c19d0ca6b9ad72aa`。
- CEO **直接读取**本次 [RELEASE_PREP_REPORT](RELEASE_PREP_REPORT.md)、[RISK_REGISTER](RISK_REGISTER.md)、[EXECUTION_LOG](EXECUTION_LOG.md)、[RELEASE_READINESS](RELEASE_READINESS.md)、[FINAL_REPORT](FINAL_REPORT.md) 和 [JSON](../../docs/evidence/rfq019/rfq019-release-prep-2026-11-14.json)，并抽查 GitHub 固定源码 `src/gui/main.py:169-207`、`src/launcher/backend.py:733-758`、`src/launcher/mail_research_composition.py:40-58`、`src/workflow/mail_research.py:467-485`、`scripts/build_windows_release.ps1`。
- **B7 证实**：正常 GUI 非 mock 启动在显示应用前调用 `backend.start_process_services()`；实际邮件服务准备可能执行数据库迁移/未结通知恢复并启动 IMAP worker。因此默认 GUI **不是**安全的“只显示界面”入口。不能先运行再看。现有 `--self-check`/`--idle-self-check` 是候选非业务效果验证路径（仍需 staging 验证）；`--mock` 不是正式 backend。
- **B1–B2 构建证据成立（基于 Executor 现场报告）**：规范构建脚本需 release Python，Builder 没有独立 release venv / PyInstaller，固定 `25894efa` 不存在可追溯 EXE。**B3 完整备份和 B4 干净 Stop 都还没有实际完成**。当前旧 EXE `E9E3DA33…` 未被可靠映射到源代码；不能拿旧旧版 backup 当可验证完整回滚。
- **B5–B6 为真实业务启动阻断**：无法以 `inquiry_ids` 隔离 quote/TP/通知范围；跨服务 document hold/lease 为进程内状态，重启消失，3 条 V13 持久 hold 不能代替全局未结算跨服务写入的恢复证明。**即使完成干净停机，也只是必要条件，不等于自动业务 Start 安全。**
- GUI 停刷、退出挂起、Chrome 残留页、`inq_d65be9df…` 报价异常可在仅 staging/self-check 的阶段作为观察项，但进入真实 GUI/业务 Start 前必须按风险清单升级判定；不是已修复。

## CEO 修订的执行边界（防止把“可准备”误读为“已授权”）

1. **审计 PASS，不是安装 PASS。** 尚未授权创建 release venv/联网安装依赖、候选打包、停止旧 EXE、写/备份生产 SQLite、运行正常 GUI、实效业务或合并代码。Owner 可在下一独立指令中明确批准 **仅离线 staging 构建及 staging self-check**。此前“可继续”均为**具备申请资格**，非已完成/已授权。
2. 当前旧 EXE 在 RFQ-019 Executor 21:28–21:35 只读报告中仍有 business module 活动（app PID38948、watcher34304），Chrome9222 owner24164。**CEO 没有当前实机重新核验**，下一窗口需先刷新 PID/HEAD/status/运行现场，不接触 Chrome/CDP，不影响生产。
3. **拆分前置准备与现场切换。** 可先独立 staging `--BuildOnly` 和在无生产配置/不连接生产资源的隔离路径运行 `--self-check`/`--idle-self-check`，并只读盘点正在运行的 EXE/程序目录/配置及可逆回滚路径。实际备份生产 SQLite（哪怕 online backup）、有界 GUI Stop、程序覆盖、正常 GUI 启动和 Start **均需 Owner 单独批准**，不可由本 RFQ 自动连锁。尤其不可直接复制 live SQLite 单文件冒充一致快照。
4. **重启 UNKNOWN 风险仍在。** 不能通过重启清空内存 hold 来解除未知结果；旧 V13 持久 hold、SHAHAB/115 未知收据和第221行原生 SAVED receipt 都必须保留；如果新业务启动前证据无法证明完整隔离，应继续 HOLD。执行者的“无 UNKNOWN 才 Start”必须区分**新增在途 UNKNOWN**与必须长期保留、人工隔离的**历史 V13/SH AHAB UNKNOWN**；不能因为历史挂起存在而清除或重放它们来试图满足“零 UNKNOWN”字面条件。
5. **加速路径**：下一窗口先完成一个阶段性的、不会影响旧版生产的**候选构建+离线自检+追溯清单**（建议 RFQ-020，只在 Owner 发出新指令授权后启动）。不需要重做 RFQ-018 已通过的 4188 项源码测试。若构建依赖不可用，准确报告并停止，不能未经批准另行更换依赖/影响旧环境。然后把 B5/B6/B7 的最小业务试运行隔离入口单独评估，不在 staging 阶段做生产动作。**避免先覆盖 EXE 再发现 B7。**

## 证据可信范围与未解决资产

- Executor 只读报告旧 EXE `D:\\Program_Leo\\INSO_Leo\\dist\\INSO_V1.6\\INSO_V1.6.exe` SHA `E9E3DA33417414ABAC53F8A88A67D9F053BCDAEAB9730EAE9AD8BD7870DFFAD0`，`gui_ready` 但仍在执行 quotation/tp/inquiry；SQLite `quick_check=ok`；3 条 V13 hold、0 active V12 alerts。以上是 Executor 报告，非 CEO 实机核验。旧 EXE↔源码关系 `NOT_VERIFIED`。
- 第 221 行 INSO SAVED 收据 `rec_440fafd372440ecf9dacabf660dd155d` **禁止重下**；SHAHAB/115 `inq_99275e8e72b43fd6616fd686` 仍 `MANUAL_REVIEW / RECONCILIATION_UNREADABLE`，原生 INSO `NOT_VERIFIED`，不能冒称已购或重试；3 条历史 V13 quote holds 不清。
- RFQ-018 执行者的 **4188 collected / 4187 passed / 1 skipped / 0 failed** 离线测试证据在本任务**未重跑**。不能据此证明打包、安装、真实 GUI、邮件或 Excel/Sheets/INSO 的生产动作完成。
- `develop` 只同步管理文档；`main` 是历史 V1.1，`release/previous` 候选未验收；没有业务源码合入、部署或晋升。

**下一 Owner 授权建议**：新 DeepSeek **窗口**、同一现有 Executor worktree、独立阶段 RFQ-020 的离线 release staging 构建与自检；操作范围仅候选、锁定哈希和只读检查，**不停止/覆盖旧版**。本次 CEO Review 的 `PASS_RELEASE_PREP_AUDIT` 与 `RELEASE_HOLD` 同时成立。
