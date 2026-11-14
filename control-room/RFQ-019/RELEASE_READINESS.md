# RFQ-019 — 发布准备结论（2026-11-14）

**结论：`BLOCKED`（正常 GUI / 业务试运行）；仅候选构建 + `--self-check`/`--idle-self-check` + 完整回滚快照可作为准备工作继续。**

这不是 RFQ-018 源码质量问题。RFQ-018 仍然 `PASS_SOURCE_SAFETY_SCOPE`；本轮发现的是**发布执行前置条件**不满足：当前没有可用的候选 EXE，没有当前运行版本的完整回滚快照，且正常 GUI 启动会启动独立邮件/IMAP/SMTP 与数据库迁移，无法在不产生外部效果的前提下做“安装后 GUI 试运行”；业务 Start 也没有受控单笔范围。

## 为什么是 BLOCKED

| 阻断 | 事实 | 影响 |
|---|---|---|
| **B1** | `.venv-release` 不存在；全局 Python 无 PyInstaller；规范构建脚本无法启动 | 无法生成固定 `25894efa` 的候选 EXE |
| **B2** | 旧 EXE `E9E3DA33…` 早于 RFQ-018 修复，且与旧报告 formal `b357889d…`/`source 24b73be7` 不一致；无 `25894efa` 对应构建 | 没有源码↔EXE↔安装追溯，不能证明试运行的是已 PASS 源码 |
| **B3** | 最新完整 backup 是 10:15 旧版本；最新 customer backup 只有 EXE；当前 `E9E3DA33` 无完整程序+配置+DB 回滚快照 | 新 EXE 失败时不能证明可回退到当前运行版本 |
| **B4** | 旧 EXE PID 38948/watcher 34304 正在运行，日志显示 21:34 仍有 quotation/tp/inquiry 模块活动；尚无授权的干净 Stop/无在途证明 | 覆盖运行中 EXE 可能把在途外部效果变成 UNKNOWN；重启后内存 document hold 消失 |
| **B5** | 没有受控单笔/写入禁用 Start：full Start 会运行 inquiry/quotation/TP；manual 操作要求 RUNNING；`inquiry_ids` 不限制 quotation/TP/通知 | 任何业务 Start 都可能处理非目标行/历史 UNKNOWN，不能承诺“只试一单” |
| **B6** | 重启后新进程不继承跨服务 document hold/lease；持久仅 per-order V13 hold | 若停机时存在未知 Google 写入，重启后不能靠内存保护阻断同文档其他写者 |
| **B7** | 正常 GUI 启动即调用 `start_process_services()`：`migrate_v12`/`V13HoldStore.migrate`/`MailResearchStore.migrate`、`recover_abandoned_notification_attempts`，并启动 IMAP 接收 + SMTP outbox worker；没有“仅 GUI、不启邮件/不改 DB”的正式启动开关 | 不能在不读 IMAP、不发 SMTP、不迁移生产 DB 的前提下做正常 GUI 试运行；`--idle-self-check` 是唯一现有安全替代，`--mock` 不是真实后端 |

## 可以安全继续的部分

- 使用现有 `--self-check` 验证冻结 GUI 依赖。
- 使用 `--idle-self-check` 构造真实 GUI 空闲态并渲染/退出；它不调用 `start_process_services`、不 Start、不读 IMAP/不发 SMTP。
- 从固定 `25894efa` 构建候选（需先 B1）。
- 为当前旧版本创建完整、可校验回滚快照（B3）。
- 只读刷新现场/durable holds；不启动业务。

## 必须先做的下一步（最小）

1. **Owner 决定正常 GUI 启动的副作用范围**（B7）：
   - 选项 A：仅批准 `--self-check` + `--idle-self-check` 的安装验证；不启动正常 GUI；或
   - 选项 B：另行批准一次正常 GUI 启动，明确接受 IMAP 读、SMTP outbox 发送、生产 DB migration/recovery 的副作用；或
   - 选项 C：另开最小代码任务，增加“无邮件/无 DB 迁移的 GUI 启动”开关（不属本 RFQ）。
2. **批准创建 `.venv-release` 并构建候选**（B1/B2）；记录源码/依赖/构建/EXE/hash/scan。
3. **批准创建完整回滚快照**（B3）；先快照程序/配置，停机后再做一致 SQLite backup。
4. **批准一次有界维护窗口做干净 Stop**（B4）；Stop 卡住/有在途即中止，不强杀。
5. **业务 Start 另行决定**（B5/B6）：需要受控单笔/写入禁用模式，或 Owner 明确接受 full Start 范围；本 RFQ 不改源码。

## 非阻断但必须观察

GUI 停刷、退出卡住、Chrome 残留页、`inq_d65be9df` 报价失败原因、SHAHAB/115/221 历史状态：Phase 0 不触发业务，可记录；一旦开始正常 GUI/业务试运行，按 [RISK_REGISTER.md](RISK_REGISTER.md) 的升级条件处理。不得把“历史没出事”当作已解决。

## 最终判定

- **正常 GUI / 业务试运行：`BLOCKED`**。
- **候选构建 + 自检 + 回滚快照：可继续**，但需 Owner 对 B1/B3/B4 的单独操作授权。
- **不授权部署、停止旧 EXE、正常 GUI 启动、业务 Start、真实外部写入或分支晋升。**
