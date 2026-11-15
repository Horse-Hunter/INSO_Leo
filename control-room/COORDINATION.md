# INSO LEO — RFQ-021-R2 定点补修 + 早间事件（2026-11-15 上午）

**当前状态：`RFQ021_R2_PASS_SOURCE_SCOPE / RELEASE_HOLD / NOT_DEPLOYED`；事件 `INC-20261115 ROOT_CAUSE_CONFIRMED`。**

- **早间事件（只读取证，已结案为单一故障）**：正在跑的是旧 EXE `E9E3DA33…`（PID 38948 `--start-inquiry` + watcher 34304，2026-11-14 13:47 启动）。06:06:28 报价模块开始，06:06:48 失败（19.3 s），06:06:49 `SHEETS_READ_UNAVAILABLE / SSLEOFError` → `MODULE_PAUSED`。**不是崩溃**（fatal.log 为空、无 Windows 应用错误事件）。**无未确认外部效果**（失败在读取阶段；故障后 0 条业务事件；采购状态、3 条 V13 hold、0 活动告警均未变）。详见 [INCIDENT-20261115](INCIDENT-20261115.md)。
- **CEO 三个 P0 全部属实并已修复**：范围绑定到 `compose_v12_production`（此前传 None＝全量）；邮件服务改为 `may_start_process_services()` 双层把关；邮件/登录/单笔动作在预览与越界订单上双层拒绝。详见 [REVIEW_FOLLOWUP](RFQ-021/REVIEW_FOLLOWUP.md)。
- **能力收窄（刻意）**：报价/TP/通知无法按订单隔离，现在直接拒绝（`SCOPE_MODULE_NOT_ISOLATABLE`），`smtp` 也不能作为写入目标。受控试运行当前只支持 `inquiry` 模块 + 指定订单。
- **新候选**：源码 `1314da5d`，EXE 8,457,679 B / `74586eb2…`，2,872 文件，清单 `74ae29c7…`（旧候选 `63bcd6ce…` 与清单已归档为 `-r1`）；三种自检全 0，逐文件复算 2,872/2,872 PASS。
- **测试**：完整套件 4,237 项 → 4,235 通过 / 2 失败 / 1 跳过；两处失败与未修改的父提交基线相同（同一 nodeid），捕获原因为测试临时目录写入被拒，非本轮引入，未删除未跳过。
- **仍未做**：未安装、未停机、未重启旧程序、未碰生产 SQLite/Chrome9222、未合并或晋升。B3 完整回滚快照与 B4 干净停机仍需维护窗口。
- **下一步**：CEO 复核 RFQ-021-R2。旧程序当前仍处于"采购模块暂停"，是否重启恢复属业务动作，需 Owner 单独授权（建议先确认到 Google 的连通性）。

## RFQ-021-R1 首次交付（保留记录，2026-11-15 凌晨）

**当前状态：`RFQ021_READY_FOR_CEO_RELEASE_REVIEW / NOT_DEPLOYED / NOT_MERGED / B5-B6-B7_CLOSED_IN_SOURCE`。** 最新执行证据：[FINAL_REPORT](RFQ-021/FINAL_REPORT.md)、[EXECUTION_LOG](RFQ-021/EXECUTION_LOG.md)、[安装与回滚](RFQ-021/INSTALL_AND_ROLLBACK.md)、[JSON](../docs/evidence/rfq021/rfq021-final-candidate.json)、[候选清单](../docs/evidence/rfq021/INSO_V1.6-artifact-manifest-r1.sha256)、[JUnit](../docs/evidence/rfq021/pytest-report.xml)。

- **B7 关闭（源码+测试）**：普通双击＝安全预览，不调 `start_process_services`、不迁移、不读 IMAP、不发 SMTP、不连 CDP，开始按钮显示「安全预览（不启动业务）」且禁用；`--start-inquiry` 缺范围直接拒绝。候选 `--preview-self-check` 真机跑两轮全绿。
- **B5 关闭（源码+测试）**：`RunScope` 限制订单/模块/写入目标，写入需 `OWNER-APPROVED:` 审批串；Google 写入在唯一租约处拦截，INSO 写入在既有门外面加一层拒绝，范围只收窄不放宽；无范围不启动，不会退回 full Start。
- **B6 关闭（源码+测试）**：`workflow_write_intents` 在外部请求前落盘；进程崩溃后残留的 PENDING/UNKNOWN 会阻断同一文档的后续写入；账本不可读/不可写一律 fail closed；没有自动清理路径。
- **候选**：源码 `8cded532`，EXE 8,455,788 B / `63bcd6ce…`，2,872 文件、无 `runtime/`；清单 `d5cc3d4c…` 经脚本逐文件复算 2,872/2,872 一致。RFQ-020 的 `b358f687…` 不再作为本轮证据。
- **测试**：新增 35 项负向测试全绿；受影响模块 2,886 项全绿；完整套件 4,223 项中 4,220 通过、2 失败、1 跳过，两处失败与**未修改的父提交基线完全相同**（同一测试、同一现象），非本轮引入，未删除任何测试。
- **未做**：未安装、未停机、未正常 GUI、未业务 Start、未碰生产 SQLite/Chrome9222，未合并 `develop`、未晋升分支。B3 完整回滚快照与 B4 干净停机仍需 Owner 单独批准的维护窗口。
- **保护不变**：221 SAVED `rec_440fafd372440ecf9dacabf660dd155d` 不重下；SHAHAB/115 `MANUAL_REVIEW` 未证真实采购；3 条 V13 报价 hold 保留。
- **下一步**：CEO 复核 RFQ-021。通过后仍分三步，各自单独授权：①维护窗口内做停机+完整回滚快照；②安装候选并只做安全预览验收；③受控业务启用。

## RFQ-020 CEO Review（保留记录，2026-11-14）

**当前状态：`RFQ020_PASS_BUILD_AND_ISOLATED_SELF_CHECK / RELEASE_HOLD / NOT_INSTALLED / RFQ019_PREP_PASS / RFQ018_SOURCE_PASS`。** 最新审核：[RFQ-020 CEO Review](RFQ-020/REVIEW.md)，执行证据：[EXECUTION_LOG](RFQ-020/EXECUTION_LOG.md)、[JSON](../docs/evidence/rfq020/rfq020-build-2026-11-14.json)、[完整 SHA256 清单](../docs/evidence/rfq020/INSO_V1.6-artifact-manifest.sha256)。

- **候选存在且 staging 自检 PASS（仅按 Executor 实测）**：固定代码 `25894efa`，离线 Python3.12.10/Tk8.6.15/PyInstaller6.16.0，`-BuildOnly` 生成候选 `build/windows-release-stage-1.6/dist/INSO_V1.6`，EXE 8,436,056 B / `b358f687…`、2,872 文件、无 `runtime/`；`--self-check=0`、`--idle-self-check=0`（3秒/停止/无业务线程），扫描通过。CEO 从 GitHub 校验清单 2872 无重复文件路径，并独立重算 manifest SHA256 `c8806aea…` 匹配。**CEO 未验证 Windows EXE 实物字节，也未实机执行自检。**
- **现场不变要限时表达**：Executor 比对 22:38–22:45 自检窗口生产 EXE/PID/SQLite size+mtime/Chrome15页不变；稍后自报生产 DB mtime 和 Chrome 页数变化，属于继续运行环境的动态观察，**不能称整个 RFQ 全程无变化或独立证明变动原因**。记录中的 23:00 观测时间早于其 22:50 Git 提交不合时序，正式发布前澄清。
- **B1/B2 阶段性关闭，B3/B4/B5/B6/B7 仍发布阻断**。无完整当前旧版程序+配置+一致 DB 回滚备份、无授权干净 Stop；正常 GUI 启动带 DB/IMAP/SMTP 副作用，full Start 不限单笔，重启丢 process-local document hold，禁止安装/正常 GUI/真实业务 Start。当前旧 EXE `E9E3DA33…` 仍为旧生产候选；其源码血缘不可证。
- **保护**：221 SAVED `rec_440fafd372440ecf9dacabf660dd155d` 不重下；SHAHAB/115 `MANUAL_REVIEW/RECONCILIATION_UNREADABLE` 未证真实采购；3 条 V13 报价 hold 保留。不能操作 Chrome9222、生产 SQLite/WAL/SHM、外部 Google/INSO/SMTP 或晋升分支。
- **接管纠正**：RFQ019 REVIEW 在 Executor 分支和 develop 均存在；`docs/BRANCH_POLICY.md` 只在 develop 存在。下一个窗口明确逐分支读取，不据旧工作树缓存判断仓库全局文件缺失。候选 manifest 可检不代替真实 staging 文件 re-hash。
- **下一步建议**：一次性有界推进 B5/B6/B7 的离线受控启动保护设计与测试，**需 Owner 新授权才能改源码**；届时因源码新 SHA 需重新 build 候选。B3 回滚备份和 B4 停机另按 Owner 维护窗口批准，不自动连锁。
