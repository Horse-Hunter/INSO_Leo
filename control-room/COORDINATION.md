# INSO LEO — RFQ-020 隔离候选构建与自检（2026-11-14）

**最新状态：`RFQ020_PASS_BUILD_AND_SELF_CHECK / INSTALL_NOT_AUTHORIZED / NOT_DEPLOYED / NOT_MERGED / B5-B7_BLOCKED`。** [RFQ-020 FINAL_REPORT](RFQ-020/FINAL_REPORT.md)、[EXECUTION_LOG](RFQ-020/EXECUTION_LOG.md) 为本轮证据；[RFQ-019 CEO Review](RFQ-019/REVIEW.md) 仍是发布判断依据。

- **RFQ-020 结果（本轮授权范围内 PASS）**：固定源码 `25894efa`（HEAD 现为 `64dba150`，`src tests scripts packaging requirements-windows-release.lock` 与固定源码零差异）；隔离 `.venv-release`（Python 3.12.10 / Tk 8.6.15 / PyInstaller 6.16.0，锁定依赖未改）执行 `-BuildOnly`，候选 EXE **8,436,056 B / `b358f687…`**，2,872 文件、261 MB、无 `runtime/`，完整清单 `c8806aea…`。`--self-check` 0、`--idle-self-check` 0（3 s，无业务线程，状态“已停止”）、`RELEASE_SCAN_OK`。
- **生产零变化**：PID 38948/34304 未动，`dist/INSO_V1.6/INSO_V1.6.exe` 仍 `E9E3DA33…`，生产 SQLite 大小/mtime 未变、无 WAL/SHM，Chrome 9222 仍 15 页。未安装、未停机、未正常 GUI、未业务 Start。
- **仍未解决**：B3 完整回滚快照未生成（需停机窗口 + Owner 授权）；B5/B6/B7 仍阻断业务试运行；候选未做安装后验证；旧运行 EXE `E9E3DA33…` 源码血缘仍 `NOT_VERIFIED`。

## RFQ-019 CEO Review（保留记录，2026-11-14）

**最新状态：`RFQ019_PASS_RELEASE_PREP_AUDIT / NORMAL_GUI_BUSINESS_BLOCKED / RFQ018_SOURCE_PASS / RFQ017_AUDIT_PASS / RFQ016_SOURCE_PASS / NOT_DEPLOYED / NOT_MERGED`。** [RFQ-019 CEO Review](RFQ-019/REVIEW.md) 为当前发布判断，[EXECUTION_LOG](RFQ-019/EXECUTION_LOG.md) 和 [RISK_REGISTER](RFQ-019/RISK_REGISTER.md) 为原 Executor 证据。

- **RFQ-019 只读风险评估 PASS**：`505d9590` 仅添加控制室文档/JSON，固定已审源码 `25894efa` 未变。按 Executor 的只读现场：release 环境缺失、未有该源码候选 EXE、当前运行旧 EXE `E9E3DA33…` 与旧报告不一致、无完整哈希回滚备份，旧业务运行/Chrome9222 仍保护中。
- **B7 有源码支持**：正常 GUI 开始时会调用 `start_process_services`，并可能触发本地 DB migration/recovery + IMAP/SMTP 后台线程，**不能把 GUI 启动当成无业务副作用**。B5 没有完全单笔/无额外模块的 Start；B6 重启丢 process-local document hold。B1-B4 是构建、备份、停止和证据的发布前置条件。
- **只能申请推进**：下一任务可在 Owner 明确新授权后做 `25894efa` 的 **隔离 staging 候选构建 + 无生产资源的 self-check/idle-self-check + hash/manifest/只读回滚盘点**。**无授权不得**安装、停旧 EXE、normal GUI、处理 live SQLite、接触 Chrome、开启真实 Google/INSO/SMTP。
- **现行业务**：221 SAVED `rec_440fafd372440ecf9dacabf660dd155d` 不重下；SHAHAB/115 `MANUAL_REVIEW/RECONCILIATION_UNREADABLE` 无原生收据保持 UNKNOWN；3 V13 quote holds 不清。GUI 冻结/退出卡住/Chrome 残留仍待现场验收，不可称问题消失。
- **分支**：源码仍在 `workbuddy/v16-rfq016-stabilization`；`develop` 只管理文档、`main` 历史 V1.1、`release/previous` 不动；无源码合并、真实部署或版本晋升。

**下一步：CEO 复核 RFQ-020。** 之后由 Owner 决定 B7（仅自检安装，或明确接受正常 GUI 的邮件/DB 副作用）并单独批准停机窗口；B5/B6 未解决前不做业务 Start。RFQ-019 建议的「小范围 RFQ-020 离线候选构建」已在本轮完成，该建议不再作为待办。
