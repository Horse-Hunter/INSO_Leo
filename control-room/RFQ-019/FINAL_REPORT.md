# RFQ-019 — Executor final report

**RFQ 状态：`BLOCKED_FOR_NORMAL_GUI_AND_BUSINESS_TRIAL / SAFE_PREP_CONTINUE / NOT_DEPLOYED / NOT_MERGED`。**

## 正在实现什么

只读、离线评估 RFQ-018 固定源码 `25894efa` 的发布准备，重点回答重启 UNKNOWN 隔离、旧/新 EXE 切换与回滚、GUI/退出/Chrome 历史风险三类问题，并给出是否可以进入安全试运行的结论。

## 理想变化是什么

在不产生真实外部效果的前提下，给 Owner 一份可执行的发布准备方案：源码↔候选 EXE↔配置↔回滚可追溯；停机/重启不会把 UNKNOWN 当结算；GUI/退出/残留页风险有明确阻断或观察边界；然后尽快进入有界试运行。

## 以前是什么

RFQ-018 源码/离线测试已 PASS，但：没有固定源码对应的候选 EXE；旧 EXE `E9E3DA33…` 与旧报告 formal `b357889d…`/source `24b73be7` 不一致；没有当前运行版本的完整回滚快照；没有重启 UNKNOWN 隔离方案；正常 GUI 启动会启动独立邮件/IMAP/SMTP 与 DB migration。

## 现在是什么

**结论 `BLOCKED`（正常 GUI / 业务试运行）。** 阻断项：

- **B1** `.venv-release` 缺失、全局无 PyInstaller，规范构建无法运行；
- **B2** `25894efa` 无候选 EXE/hash 链，旧 EXE 来源未证明；
- **B3** 当前 `E9E3DA33…` 无完整程序+配置+DB 回滚快照；
- **B4** 旧 EXE 正在运行真实模块，尚无授权的干净 Stop/无在途证明；
- **B5** 没有受控单笔/写入禁用 Start；full Start 会影响其他模块/行；
- **B6** 新进程不继承跨服务 document hold，重启不能当结算；
- **B7** 正常 GUI 启动即 `start_process_services()`：DB migration/recovery + IMAP + SMTP outbox；没有“仅 GUI、不启邮件/不改 DB”的正式开关。

**可安全继续：** 仅候选构建 + `--self-check`/`--idle-self-check` + 完整回滚快照 + 只读现场核对；不启动正常 GUI、不 Start、不读写真实业务。

## 做完了什么

- 固定源码 `25894efa` 核对；`git diff 25894efa..HEAD -- src tests` 为空。
- 只读现场快照：旧 EXE `E9E3DA33…` 8,422,619 bytes、PID 38948/34304、Chrome 9222 PID24164、SQLite `quick_check=ok`、3 条 V13 hold、0 active alerts、221 SAVED、SHAHAB/115 UNKNOWN。
- 识别并分级 7 个阻断项、6 个观察项；给出构建、回滚快照、干净 Stop、重启 UNKNOWN 隔离、Phase 0 验收与 Owner 授权清单。
- 未重跑 4188 项；复用 RFQ-018 CEO 已审证据 **4188 collected / 4187 passed / 1 skipped / 0 failed / 341.54s**。
- 未修改业务源码/测试/生产配置；未部署、未停旧 EXE、未操作 Chrome、未写生产 SQLite、未做真实 Google/INSO/SMTP、未合并分支。

## 测试结果

- **未新增测试、未重跑全套**：RFQ-019 只读评估，复用 RFQ-018 的 4188/4187/1/0 证据。
- **只读检查：** 固定源码 vs HEAD 无源码/测试差异；SQLite `PRAGMA quick_check` = `ok`；当前进程/EXE/Chrome/durable holds 已记录。
- **未做真实环境验证：** 没有候选 EXE、没有安装/启动、没有 Stop/Exit、没有 IMAP/SMTP/Google/INSO 操作；相关项为 `NOT_VERIFIED`。

## 你接下来需要做什么

Review RFQ-019

（CEO 审核后，由 Owner 先决策：只做 `--self-check`/`--idle-self-check` 的安装验证，还是明确接受正常 GUI 的 IMAP/SMTP/DB migration 副作用；业务 Start 需另行决定受控单笔/写入禁用方案。任何构建、停机、安装、正常 GUI 或 Start 均需单独授权。）

---

**最小下一步：**
1. Owner 决策 B7（仅自检 / 接受副作用 / 另开启动开关）。
2. 批准创建 `.venv-release` 并从 `25894efa` 构建候选。
3. 批准创建当前旧版本完整回滚快照。
4. 批准有界维护窗口做干净 Stop；Stop 异常即中止。
5. 业务 Start（B5/B6）另行决定；本 RFQ 不修改源码、不部署。
