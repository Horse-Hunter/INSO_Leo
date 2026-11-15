# RFQ-021 — 安装、首次启动与回滚操作手册

**本手册只准备、未执行。** 本轮没有停旧程序、没有备份生产 SQLite、没有覆盖安装、没有启动新程序。

适用对象：Owner 在批准维护窗口后，按顺序执行的人。每一步都有"中止条件"；任一条件不满足就**停在这一步**，不要继续。

固定对象：

| 项目 | 值 |
|---|---|
| 源码提交 | `8cded532221571e99697af7668634afab3ea07af` |
| 候选 EXE | `build/windows-release-stage-1.6/dist/INSO_V1.6/INSO_V1.6.exe` |
| 候选 EXE SHA256 | `74586eb29ed19e037e2045f481d4ed2226aa555a8f6ef7951028c873fa68d0ed` |
| 候选 EXE 字节数 | 8,457,679 |
| 文件数 | 2,872 |
| 清单 | `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256`（清单自身 SHA256 `74ae29c793fb759e84a7c9bc450c77e75cf56df948ed778af67a0dcecbe77118`） |
| 当前运行版本 | `dist/INSO_V1.6/INSO_V1.6.exe`，SHA256 `E9E3DA33…`（源码血缘 `NOT_VERIFIED`） |
| 生产数据库 | `dist/INSO_V1.2/runtime/production/workflow.sqlite3`（经 `dist/INSO_V1.6/runtime` junction 指向 `dist/INSO_V1.4/runtime`） |

> 候选 EXE 完整哈希：`74586eb29ed19e037e2045f481d4ed2226aa555a8f6ef7951028c873fa68d0ed`

---

## 第 1 步：离线准备（不需要停机）

```powershell
cd D:\Program_Leo\INSO_Leo\.worktrees\v16-rfq016-stabilization

# 1.1 复算整个候选目录，必须 PASS 才继续
powershell -ExecutionPolicy Bypass -File scripts\verify_release_candidate.ps1 `
  -CandidateDir build\windows-release-stage-1.6\dist\INSO_V1.6 `
  -Manifest docs\evidence\rfq021\INSO_V1.6-artifact-manifest.sha256
```

**验收：** `missing = 0`、`hash_mismatch = 0`、`unexpected = 0`、`VERIFY_RESULT = PASS`。
**中止：** 任何一项非 0。不要重新构建"凑一致"；先查为什么变了。

```powershell
# 1.2 快照当前运行版本（只读，不停程序、不碰数据库、不复制 junction）
powershell -ExecutionPolicy Bypass -File scripts\backup_running_release.ps1 `
  -SourceDir D:\Program_Leo\INSO_Leo\dist\INSO_V1.6 `
  -RuntimeConfigDir D:\Program_Leo\INSO_Leo\dist\INSO_V1.4\runtime `
  -Destination D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-20261115T020000Z
```

**验收：** 目录里出现 `INSO_V1.6.exe`、`_internal\`、`config\`、`PROGRAM-MANIFEST.sha256`、`database-state.json`；`BACKUP_RESULT = PASS`。
**说明：** 此时数据库**没有**被复制，`database-state.json` 只记录大小与 WAL/SHM 是否存在。这是刻意的：运行中复制 SQLite 单文件可能得到不一致快照。

---

## 第 2 步：停机（唯一需要维护窗口的一步）

正常停止方式（二选一，按现有习惯）：

1. 界面点「安全停止」，等待本轮到结束；
2. 或点窗口关闭按钮，让程序跑安全退出流程。

**不做的：** 不 `taskkill`、不在任务管理器强杀、不关闭 Chrome 9222。

**无在途效果检查（停机后立刻做）：**

```powershell
Get-Process -Name INSO_V1.6 -ErrorAction SilentlyContinue | Select-Object Id,StartTime
Get-Process chrome | Where-Object { $_.Id -eq 24164 }   # 受保护会话应仍在，不要动
```

**验收（全部满足才继续）：**

- 两个 `INSO_V1.6` 进程（主程序 + watcher）都消失；
- 界面里没有"正在处理订单/报价"的在途提示；
- 最近一轮模块周期已结束（日志最后一条不是 begin）。

**中止条件（任一命中就停，不进第 3 步）：**

- 120 秒内进程未退出，或只退了一个；
- 程序停在「正在安全结束」；
- 日志显示刚发出但未确认的点击/请求；
- 有任何 `UNKNOWN` / `SENT` 未结算。

**中止后怎么办：** 保留现场，联系 Owner。**不要**强杀后继续安装，也不要用"再看一眼"的方式重启旧程序。

---

## 第 3 步：数据库一致性备份（停机后、安装前）

只在第 2 步完全通过后执行：

```powershell
$src = "D:\Program_Leo\INSO_Leo\dist\INSO_V1.4\runtime\production\workflow.sqlite3"
$dst = "D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-20261115T020000Z\workflow.sqlite3"
# 使用 sqlite3.exe；没有就跳过并在报告里写 NOT_VERIFIED，不要用复制粘贴代替
sqlite3 $src ".backup '$dst'"
sqlite3 $dst "PRAGMA quick_check;"
Get-FileHash $dst -Algorithm SHA256
```

**验收：** `quick_check` = `ok`；把备份哈希写进本次维护记录。
**禁止：** 用 `Copy-Item` 复制 SQLite 文件冒充一致备份；删除 `-wal` / `-shm`。

---

## 第 4 步：安装候选

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_release_candidate.ps1 `
  -CandidateDir build\windows-release-stage-1.6\dist\INSO_V1.6 `
  -Manifest docs\evidence\rfq021\INSO_V1.6-artifact-manifest.sha256 `
  -TargetDir D:\Program_Leo\INSO_Leo\dist\INSO_V1.6 `
  -BackupDir D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-20261115T020000Z `
  -ConfirmSwitch
```

脚本会自己再做一次：进程是否真的停了 → 备份是否带 `PROGRAM-MANIFEST.sha256` → 候选是否 PASS → `runtime` 是否仍是 junction。任一不满足就**在改动任何文件之前**抛出。

**它会做的：** 旧 `_internal` 改名 `_internal.prev-<UTC>`；旧 EXE 改名 `INSO_V1.6.exe.prev-<UTC>`；复制候选；比对安装后 EXE 哈希。
**它不会做的：** 不碰 `runtime` junction、不启动程序、不写数据库。

**验收：** `INSTALL_RESULT = PASS` 且 `installed_exe_sha256` 等于候选哈希。

---

## 第 5 步：首次启动 —— 只允许安全预览

双击启动，或：

```powershell
Start-Process "D:\Program_Leo\INSO_Leo\dist\INSO_V1.6\INSO_V1.6.exe"
```

**应当看到：**

- 界面正常显示、有历史列表与状态；
- 开始按钮显示 **「安全预览（不启动业务）」且为灰色不可点**；
- `runtime\logs` 里没有新的 IMAP/SMTP 活动、没有 DB migration 记录。

**应当没有：** 业务线程、邮件连接、Chrome 被接管、任何外部写入。

**验收：**

1. 界面能正常刷新（不空白、不卡死）；
2. 关闭窗口能在 120 秒内退出，任务管理器里 `INSO_V1.6` 两个进程都消失；
3. 再启动一次，仍然显示预览态（证明单实例锁与退出都干净）。

**中止：** 界面空白/卡死、关不掉、退出后仍留进程 → 执行第 7 步回滚。

> 想要更硬的证据：`INSO_V1.6.exe --preview-self-check` 会自己开两次界面并写 `runtime\logs\v16-preview-self-check.json`，其中 `ok: true` 表示两轮都没有业务线程、没有邮件服务、按钮是禁用的。

---

## 第 6 步：真正启用业务（必须 Owner 单独确认）

本轮**不授权**，且以下条件缺一不可：

1. 第 5 步全部通过，且预览模式跑过至少一次完整退出/再启动；
2. Owner 书面确认：目标订单、允许模块、允许的外部写入、时间窗口；
3. 3 条历史 V13 hold、SHAHAB/115、221 行的处置方式已明确（默认：保持原状，不重放、不清除）；
4. 启动命令写清楚范围，例如：

```powershell
INSO_V1.6.exe --scoped-start `
  --scope-inquiries inq_xxxxxxxxxxxxxxxxxxxxxxxx `
  --scope-modules inquiry `
  --scope-writes "" `
  --start-inquiry
```

- `--scope-modules` **只能写 `inquiry`**。报价 / TP / 通知在当前代码里没有按订单过滤的入口，写入就会被拒绝（`SCOPE_MODULE_NOT_ISOLATABLE`），这是刻意的：宁可不让它跑，也不让它带着"范围"标签处理全部订单；
- `--scope-writes` 为空 = **只读试运行**，任何外部写入在发出前就被拒绝；
- 目前可用目标只有 `google` 与 `inso`（`smtp` 同样没有按订单过滤，会被拒绝）。
- 要写入必须同时写 `--scope-writes google`（或 `inso`）**和**
  `--scope-approval OWNER-APPROVED:<本次审批编号>`。

**不允许隐式升级：** 只写 `--start-inquiry` 而不给 `--scoped-start` 会被直接拒绝并弹窗，不会退回"全量启动"。

**首次受控运行还要盯：**

- 只处理 `--scope-inquiries` 里的订单；
- 未列入的模块不出现周期日志；
- 如出现 `WRITE_INTENT_PENDING` / `WRITE_INTENT_UNKNOWN` 或 `EXTERNAL_WRITE_NOT_IN_SCOPE`，按第 8 节处理。

---

## 第 7 步：回滚（新版本有问题时）

**原则：先回程序，不轻易回数据库。** 新版跑过之后数据库可能已有新业务数据，用旧库覆盖会丢掉真实记录。

1. 正常停止新程序（同第 2 步的标准，不强杀）；
2. 恢复程序：

```powershell
$t = "D:\Program_Leo\INSO_Leo\dist\INSO_V1.6"
$stamp = "<第4步打印的 _internal.prev 后缀>"
Remove-Item "$t\_internal" -Recurse -Force           # 只删刚装进去的新版
Rename-Item "$t\_internal.prev-$stamp" "_internal"
Remove-Item "$t\INSO_V1.6.exe" -Force
Rename-Item "$t\INSO_V1.6.exe.prev-$stamp" "INSO_V1.6.exe"
Get-FileHash "$t\INSO_V1.6.exe" -Algorithm SHA256     # 应等于 E9E3DA33…
```

3. **数据库：默认不动。** 只有同时满足以下条件才恢复第 3 步的备份：
   - Owner 明确同意丢弃新版本写入的业务数据；
   - 已确认新版本没有产生需要保留的 SAVED 记录 / 邮件；
   - 已确认没有未结算的写入意图。
4. 恢复后先 `--safe-preview` 验证界面，再按 Owner 指令决定是否恢复业务。

**回滚也要留证据：** 记录回滚时间、当时 EXE 哈希、数据库是否恢复、恢复前后的业务状态。

---

## 第 8 节：几个会遇到的状态

| 现象 | 含义 | 该怎么做 |
|---|---|---|
| 按钮显示「未配置受控试运行范围」 | 程序以受控模式启动但缺范围参数 | 关掉，按第 6 步补参数；不要试图点按钮 |
| `EXTERNAL_WRITE_NOT_IN_SCOPE` | 范围内没有这个写入目标 | 正常拒绝，不是故障；需要写入就重新审批范围 |
| `WRITE_INTENT_PENDING` | 有写入已登记但未结算（可能是上一次进程异常退出） | **不要清**；先核对那次写入的真实结果，再人工结算 |
| `WRITE_LEDGER_UNAVAILABLE` | 写入账本不可读/不可写 | 全站禁止外部写入；检查数据库与磁盘权限，修好后重启 |
| 预览界面关闭后日志有 `invalid command name ...` | Tk 关闭时的内部回调提示，无功能影响 | 记录即可；若导致退出卡住则按第 7 步 |

---

## 本轮未验证（如实记录）

- 没有在真实生产上执行本手册任何一步（除第 1 步的只读校验）。
- `sqlite3.exe` 是否存在于本机、`.backup` 的实际耗时为 `NOT_VERIFIED`。
- 旧程序的 Stop 实际耗时、GUI 停刷复现、Chrome 残留页清单仍为历史观察项，本轮未测。
- 新旧程序同时连接同一生产资源的场景被明令禁止，未做实测。
