# RFQ-019 — 发布风险清单

**分类规则：**
- **阻断项（B）**：未解决前，不得开始对应阶段的试运行；不是“观察后再说”。
- **非阻断观察项（N）**：不阻止 Phase 0（仅候选构建/安装、`--self-check`/`--idle-self-check`，无正常 GUI/业务 Start），但必须记录；触发升级条件时立即停止并转为阻断。
- **理由必须指向证据**；不得以“历史没出事”“测试全绿”降级。

## 阻断项 — 必须在对应试运行前解决

| ID | 阻断内容 | 证据 | 为什么阻断 | 最小解决动作 | 适用阶段 |
|---|---|---|---|---|---|
| **B1** | 无法用规范脚本构建候选 EXE：`.venv-release` 缺失，全局 Python 无 PyInstaller | `scripts/build_windows_release.ps1` 首段要求 `.venv-release/Scripts/python.exe`；`Test-Path` false；`python -c import PyInstaller` 失败 | 没有候选构建就无法建立源码↔EXE↔安装追溯，不能进入任何候选试运行 | 用 Python 3.12.10 创建 `.venv-release`，按 `requirements-windows-release.lock` 安装；验证 `pyinstaller 6.16.0`、Tcl/Tk | Phase 0 |
| **B2** | 固定源码 `25894efa` 没有对应候选 EXE/hash；当前旧 EXE `E9E3DA33…` 早于修复，且与 `V16_RELEASE_REPORT` 的 formal `b357889d…`/source `24b73be7` 不一致 | 固定源码 `git diff 25894efa..HEAD -- src tests` 为空；旧 EXE 8,422,619 bytes / E9E3DA33；旧报告 formal b357889d/source 24b73be7；候选 staging 8,414,556 且来源未证明 | 不能证明“试运行的就是已 PASS 的源码”，也无法回滚到可复现版本 | 从固定 SHA 构建 `BuildOnly` 候选；记录源码 SHA、build script/lock hash、EXE SHA、文件清单、`--self-check`/`--idle-self-check`/`--api-self-check`/scan 结果 | Phase 0 |
| **B3** | 没有当前运行版本 `E9E3DA33…` 的完整、可校验回滚快照（程序+配置+数据库一致性备份） | 最新 full backup 是 10:15 的旧 `header-block`（`_internal`+EXE，8,414,556）；最新 customer backup 只有 EXE；当前 EXE 8,422,619；`_internal.prev-*` 不是完整回滚集；`production.json` 只有 10:30 的 bak | 回滚不能只靠零散 `_internal.prev`；若新 EXE 失败，无法证明能恢复旧程序/配置/数据 | 停机前创建 `RFQ-019-pre-switch` 完整快照：当前 EXE+`_internal`+`production.json`/`research.json`+一致 SQLite 备份+WAL/SHM 状态+清单 SHA；验证恢复路径（不回写新业务数据） | Phase 0（停机/安装前） |
| **B4** | 旧 EXE 正在运行真实业务模块；尚无经授权的干净 Stop/无在途效果证明 | PID 38948 `--start-inquiry`；watcher 34304；日志 21:34 仍有 quotation/tp/inquiry 模块完成；3 条 V13 hold；0 active V12 alerts | 覆盖运行中 EXE 或在有在途写入时切换，会把一次未确认外部效果变成 UNKNOWN；重启后内存 document hold 消失 | Owner 授权维护窗口；GUI 正常 Stop/Exit，等待 app+watcher 退出；确认无 manual/quote/purchase 在途、模块周期完成；若 Stop 卡住或无法证明，停止安装，不强制杀进程 | Phase 0（安装前） |
| **B5** | 没有安全的“单笔/有限业务 Start”模式：full Start 会运行 inquiry/quotation/TP；manual 操作需要 RUNNING；`inquiry_ids` 只限制 inquiry，不限制 quotation/TP/通知；配置无全局写禁用开关 | `RFQ-016/TASK_SPEC.md` 明确 `inquiry_ids` 不限制 quotation/TP；`ProductionBackend` 只有完整 `start()`；`_manual_idle` 要求 `RUNNING`；`v13_enabled/tp_enabled/v16_enabled` 不能关闭 inquiry 的自动采购路径 | 任何业务 Start 都可能处理非目标行/历史 UNKNOWN，无法承诺“只试一单” | 二选一，由 Owner 决定：①另开最小代码任务增加受控单笔/写入禁用 Start；②明确接受 full Start 的范围风险并列出可能受影响的订单；本 RFQ 不修改源码 | Phase 1（业务 Start） |
| **B6** | 新进程无法继承旧的跨服务 document hold；历史 UNKNOWN 不能靠重启清内存保护 | `PageResourceAdmission` 的 document hold/lease 是进程内（CEO RFQ-018 Review 明确）；持久只有 per-order V13 hold；当前 3 条 hold，SHAHAB/115 `MANUAL_REVIEW`，无 saved receipt | 重启后新进程不会自动知道旧进程某文档曾 UNKNOWN；若此时 Start，可能对同文档/其他单发起写入 | Phase 0/1 都不得把重启当作结算；Start 前必须干净停机且无 UNKNOWN；若停机时存在任何在途/未知，禁止业务 Start，只允许 idle/self-check；历史 3 hold 与 SHAHAB/115 保持隔离 | Phase 1（更严格：任何 Start 前） |
| **B7** | 正常 GUI 启动不是“无副作用”：`gui/main.py` 在 `--start-inquiry` 之前就调用 `backend.start_process_services()`；该路径执行 `migrate_v12`、`V13HoldStore.migrate`、`MailResearchStore.migrate`、`recover_abandoned_notification_attempts`，并启动 IMAP 接收 + SMTP outbox worker | `src/gui/main.py:195-196`；`src/launcher/backend.py:733-758`；`src/launcher/mail_research_composition.py` `build_mail_research`；`src/workflow/mail_research.py:467-495` | 正常 GUI 启动可能读 IMAP、发送已排队 SMTP、改生产 SQLite；当前禁止 SMTP/生产 DB 写入。没有“仅 GUI、不启邮件/不迁移 DB”的正式开关 | 现有安全替代是 `--self-check` + `--idle-self-check`（不调用 process services/不 Start）；正常 GUI 需 Owner 明确接受副作用，或另开最小代码任务增加无邮件/无迁移启动开关 | 正常 GUI / Phase 0 GUI 验证 |

## 非阻断观察项 — Phase 0 可记录，触发条件即升级

| ID | 观察项 | 证据/边界 | 为什么暂不阻断 Phase 0 | 观察/验收方式 | 升级为阻断的条件 |
|---|---|---|---|---|---|
| **N1** | GUI 停刷/刷新不更新 | 历史 CEO/RFQ 记录列为独立风险；当前旧程序日志无当前 GUI 错误，但不能据此证明新候选 | Phase 0 只用 `--idle-self-check` 构造/渲染空闲 GUI，不启动正常 GUI（B7）、不 Start；不处理业务刷新 | `--idle-self-check` 观察渲染/退出；记录是否空白/卡死；不点 Start、不启 normal GUI | 空闲 GUI 无法初始化、渲染卡死、无法退出 |
| **N2** | 退出卡住/进程不退出 | 历史记录；当前旧程序 watcher/app 双进程存在，正常 Stop 的耗时未在本任务实测 | Phase 0 的 `--idle-self-check` 退出验收会直接验证；若卡住则 Phase 0 失败 | 记录 `--idle-self-check` 退出时间/退出码；不强制杀进程；若超时保留现场 | 自检进程超过 120 秒未退出、或留下 app/watcher |
| **N3** | Chrome 残留页面/所有权不明 | 历史记录；当前 9222 owner 24164，存在业务运行页；不得清理 | Phase 0 不 Start、不启 normal GUI，不操作 Chrome；`--idle-self-check` 不 acquire CDP | 自检前后只读记录 9222 owner、页面数/标题；新 EXE 不得新建/关闭页 | 自检/安装过程关闭/抢占人工页、创建未归属页、或需要重置 9222 |
| **N4** | `inq_d65be9df…` 报价循环失败、拒绝原因未记录 | 当前 V13 hold `QUOTE_INPUT_WRITE_FAILED`；日志显示该单 quotation 失败；历史独立风险 | Phase 0 不启动 quotation/业务；不影响安装验收 | 保持 hold；不在 Phase 0 触发报价；在后续业务试运行中单独观察 | 若 Owner 要求业务 Start，该单被自动尝试或 hold 被清除时 |
| **N5** | 历史 SHAHAB/115 采购 UNKNOWN/告警曾被旧版清除 | SQLite `MANUAL_REVIEW / RECONCILIATION_UNREADABLE`，无 saved record；原生 INSO `NOT_VERIFIED`；0 active V12 alerts | Phase 0 不 Start、不触碰该单；历史状态已持久隔离 | 快照/保持；不修库、不补告警、不重开、不发信 | 任何 Start/操作可能重试或“恢复”该单时 |
| **N6** | 旧 EXE 版本与正式 receipt 不一致（E9E3DA33 vs b357889d） | 见 B2/B3；当前旧 EXE 来源未证明 | 已在 B2/B3 作为阻断；Phase 0 必须用当前运行 EXE 的实测 hash 做回滚快照，不靠旧报告 | 快照当前 hash+文件清单；候选另行构建 | 无法区分旧/新程序或回滚包不匹配 |

## 结论

- **Phase 0（构建/回滚快照/干净停机/安装/`--self-check` + `--idle-self-check`）**：B1–B4、B7 必须先解决或明确选择安全替代；完成后可在 Owner 单独授权的维护窗口执行。
- **Phase 1（正常 GUI / 业务 Start）**：B5/B6/B7 未解决，**BLOCKED**；不得用“无重复事故”或“测试全绿”降级。
- N1–N6 不阻止“仅自检”的 Phase 0，但必须记录；任一触发升级条件即停止并回到阻断状态。
