# RFQ-019 — 快速发布准备方案

**状态：`BLOCKED`（正常 GUI / 业务试运行）；可继续的仅是候选构建、`--self-check`/`--idle-self-check` 与完整回滚快照。**

本报告只做准备评估，不授权部署、停止旧程序、正常 GUI 启动、业务 Start、真实 Google/INSO/SMTP 写入、SQLite 修改或分支合并。

## 1. 固定源码与已审证据

- 固定源码：`25894eface6ea622153d1573c19d0ca6b9ad72aa`（RFQ-018 最终 PASS）。
- 文档 HEAD：`45621923`（CEO RFQ-018 最终 Review；只含管理文档）。
- `git diff --name-only 25894efa..HEAD -- src tests` = 空，未改业务源码/测试。
- 复用 RFQ-018 CEO 已核对的测试证据：**4188 collected / 4187 passed / 1 skipped / 0 failed / 341.54s**，原 26 nodeid 保留，28 项新回归；本 RFQ 不重跑全套。
- 本次只读现场快照与风险证据见 [EXECUTION_LOG.md](EXECUTION_LOG.md)、[RISK_REGISTER.md](RISK_REGISTER.md)。

## 2. 当前旧 EXE 与现场

| 项目 | 只读观察 |
|---|---|
| 旧 EXE | `dist/INSO_V1.6/INSO_V1.6.exe`，8,422,619 bytes，SHA256 `E9E3DA33417414ABAC53F8A88A67D9F053BCDAEAB9730EAE9AD8BD7870DFFAD0` |
| 进程 | app PID 38948 `--start-inquiry`；watcher PID 34304 |
| 运行状态 | `phase=gui` / `gui_ready`，但日志显示 21:34 仍有 quotation/tp/inquiry 模块完成——**是运行中的业务程序，不是空闲仪表盘** |
| Chrome | `127.0.0.1:9222` owner PID 24164，未触碰 |
| SQLite | 1,191,936 bytes，`quick_check=ok`；0 active V12 alerts；3 active V13 holds；26 SAVED / 7 VALIDATION_FAILED / 3 AI_RECOGNIZED / 1 MANUAL_REVIEW |
| 221 | `PURCHASE_RECORDED` / `SAVED` / `rec_440fafd372440ecf9dacabf660dd155d`，不得重下 |
| SHAHAB/115 | `HUMAN_COMPLETED` / `MANUAL_REVIEW` / `RECONCILIATION_UNREADABLE`，无 saved receipt；原生 `NOT_VERIFIED` |
| 配置 | `dist/INSO_V1.4/runtime/production.json`，`google_api.enabled=true`，v13/tp/v16 均 true |

## 3. 三个发布问题的结论

### 3.1 重启后 UNKNOWN 写入如何隔离

**结论：不能靠“重启清内存 hold”视为结算；必须用“干净停机 + 零在途证明 + 禁止 Start”的运营闸门。**

- 新共享 document hold/lease 是进程内状态（CEO RFQ-018 Review 明确），重启后消失；只有 per-order V13 hold 持久。
- 当前 3 条 V13 hold：`inq_71f4a2f5…`（UPDATE_RESULT_UNCONFIRMED）、`inq_d65be9df…`（QUOTE_INPUT_WRITE_FAILED）、`unresolved:0ca37229…`（SOURCE_IDENTITY_UNRESOLVED）。
- **Stop 前清单**（只读生成，保留在 RFQ 执行记录）：
  - PID/进程/watcher、GUI 状态、是否有 manual/quote/purchase 在途；
  - 3 条 V13 hold 与原因；
  - purchase states、active V12 alerts、row221、SHAHAB/115；
  - 最近模块周期是否完成、日志是否仍有写操作；
  - SQLite/WAL/SHM 状态。
- **干净 Stop 条件**：GUI 正常 Stop/Exit；app+watcher 都退出；无 manual/quote/purchase 在途；模块周期结束；没有“刚发出但未确认”的点击/请求。Stop 卡住或无法证明，**中止安装**，不强制杀进程。
- **新 EXE 隔离规则**：
  1. 新 EXE 从 **无 `--start-inquiry`、无 Start** 开始；只允许 `--self-check` / `--idle-self-check`（不调用 `start_process_services`）。
  2. 不把重启当作结算；3 条 V13 hold、SHAHAB/115、221 继续保持原状。
  3. 若停机时存在任何在途/UNKNOWN，**禁止任何 Start**；只能 idle/自检，等待 Owner 对历史效果单独核实。
  4. 若停机干净且无 UNKNOWN，仍需 Owner 明确批准后才能进入业务 Start；新进程的 document hold 不继承，不能用它证明旧效果已结算。

**B6 阻断：** 当前没有持久化跨服务 document hold；重启会丢。因此“干净 Stop”是业务 Start 的必要不充分条件，不能作为自动恢复机制。

### 3.2 旧/新 EXE 切换与回滚

**结论：当前没有可追溯候选/完整回滚快照，必须先补齐。**

- 旧 EXE `E9E3DA33…` 与 `V16_RELEASE_REPORT` 报告的正式 `b357889d…` / source `24b73be7` 不一致；当前 EXE 来源 `NOT_VERIFIED`。
- 最新 full backup `INSO_V1.6-header-block-20261114T021508Z` 是 10:15 的旧版本（8,414,556）；最新 customer backup 只有 EXE；`_internal.prev-*` 是零散程序目录，不是完整回滚集。
- 规范构建环境 `.venv-release` 不存在；全局 Python 无 PyInstaller；无法按 `build_windows_release.ps1` 生成固定 `25894efa` 候选。
- 因此 **B1/B2/B3** 阻断；不能声称“可回滚”或“已可部署”。

**最小构建/回滚流程（需 Owner 授权后才执行）：**

1. 创建隔离构建环境：
   - `python -m venv .venv-release`
   - `.\.venv-release\Scripts\python.exe -m pip install -r requirements-windows-release.lock`
   - 验证 `pyinstaller==6.16.0`、Tcl/Tk。
2. 从固定源码构建 staging（不覆盖 `dist/INSO_V1.6`）：
   - `powershell -ExecutionPolicy Bypass -File scripts\build_windows_release.ps1 -BuildOnly -Version 1.6 -PythonExecutable .\.venv-release\Scripts\python.exe`
   - 产物在 `build/windows-release-stage-1.6/dist/INSO_V1.6/`。
3. 记录并归档：
   - `git rev-parse 25894efa`、build script/lock hash、候选 EXE SHA256、文件清单、`--self-check`/`--idle-self-check`/`--api-self-check`/scan 结果。
   - 候选与生产 `dist/INSO_V1.6` 分开；不覆盖运行目录。
4. 完整回滚快照 `dist/release-backups/RFQ-019-pre-switch-<UTC>`：
   - 当前 `INSO_V1.6.exe`、`_internal`（完整程序）；
   - `dist/INSO_V1.4/runtime/production.json`、`research.json`、`.bak`；
   - 停机后的 `sqlite3 .backup` 一致性 DB 副本；WAL/SHM 状态记录；
   - 若 junction 存在，记录 target，不复制/替换链接本身；
   - 清单 SHA256，验证文件数。
5. 回滚演练（离线比较/恢复路径确认，不覆盖新业务数据）：
   - 旧 EXE + `_internal` 恢复后 hash/文件数一致；
   - 配置同 hash；
   - DB 只有在“无更新业务数据 + Owner 批准”时才恢复；否则保留新 DB，只回程序/配置；
   - 恢复后 `--self-check`；不启动业务。

### 3.3 GUI 停刷、退出卡住、Chrome 残留页面

**结论：这些是观察项，不是当前“不能构建”的理由；但它们使正常 GUI 试运行不能被当作无风险。尤其正常 GUI 启动本身会启动邮件/IMAP/SMTP 与 DB migration（B7），所以不能在无授权下做正常 GUI 启动。**

- GUI 停刷/刷新：历史记录；当前旧程序没有当前复现，但旧程序处于业务运行态。候选正常 GUI 未验证。
- 退出卡住：历史记录；Stop/Exit 的耗时/是否留 watcher 未在本任务实测。安装前必须做有界 Stop。
- Chrome 残留页：历史记录；当前 9222 owner 24164。不得清理/关闭；新程序若创建未归属页面即阻断。
- **B7（新增阻断）**：`gui/main.py` 在 Start 之前调用 `backend.start_process_services()`；该路径执行 DB migration/recovery 并启动 IMAP 接收 + SMTP outbox worker。没有“仅 GUI、不启邮件/不迁移 DB”的正式开关。`--self-check`/`--idle-self-check` 是现有安全替代；`--mock` 不是真实后端。

## 4. 推荐试运行范围

### Phase 0 — 仅构建/安装/自检（可申请 Owner 批准，不产生业务写入）

1. 完成 B1/B2/B3（构建环境、候选、回滚快照）。
2. 有界维护窗口完成 B4（干净 Stop）。
3. 用候选替换程序文件前，先备份当前完整程序/配置/DB；不覆盖 `runtime` junction。
4. 安装候选后，只运行：
   - `INSO_V1.6.exe --self-check`
   - `INSO_V1.6.exe --idle-self-check`
   - 需要时 `--api-self-check`（仅构造 transport，不做 Google 读写）
   - 不运行正常 GUI（B7）；不 Start；不连接/关闭 Chrome。
5. 验收：hash/清单一致；两个 self-check 0；扫描通过；回滚快照可校验；无业务线程/Chrome/DB 写入；退出成功。

### Phase 1 — 正常 GUI / 业务 Start（当前 BLOCKED）

- 需要先解决 B5/B6/B7：受控单笔/写入禁用 Start，或 Owner 明确接受 full Start + 正常 GUI 的邮件/DB 副作用。
- 本 RFQ 不修改源码，不在本阶段启动。

## 5. 验收条件（Phase 0）

- 候选 EXE 的源码 SHA = `25894efa`；build/lock/EXE/文件清单 hash 全部记录且一致。
- `--self-check`、`--idle-self-check` 均 exit 0；artifact scan PASS。
- 当前旧 EXE/配置/DB 的完整回滚快照存在且可校验；程序文件数/SHA 与清单一致。
- 安装后不产生业务线程、不连接/关闭 Chrome 9222、不读写生产 SQLite、不发送 SMTP/不读 IMAP。
- Stop/Exit 在约定 120 秒内完成，app+watcher 均退出；否则回滚并停止。
- 任何一项不满足：立即用回滚快照恢复程序/配置，保留现场，不进入业务 Start。

## 6. Owner 需要单独授权的动作

1. **构建/回滚准备**：允许创建 `.venv-release`、构建候选、创建完整回滚快照、运行 `--self-check`/`--idle-self-check`。
2. **维护窗口**：允许有界停止旧 EXE（正常 GUI Stop/Exit；不强杀 Chrome/进程），并安装候选程序文件。
3. **正常 GUI 的副作用选择**（B7）：仅自检 / 明确接受 IMAP+SMTP+DB migration / 另开最小启动开关。
4. **业务 Start 范围**（B5/B6）：受控单笔/写入禁用方案，或明确接受 full Start；未决定前不 Start。

## 7. NOT_VERIFIED / 限制

- 没有在真实候选 EXE 上运行 self-check/idle self-check；没有部署。
- 没有实测旧 EXE 的 Stop/Exit 时间、GUI 停刷复现、Chrome 残留页清单。
- 没有读取真实 Google/INSO/SMTP；没有生产 SQLite 写入。
- 旧 EXE 的源码对应关系仍 `NOT_VERIFIED`；只能以当前实测 hash 做回滚快照，不能声称它是某个已审源码构建。
- 历史 3 V13 hold、SHAHAB/115、221 保持原状；重启/新进程不改变这些业务状态。
