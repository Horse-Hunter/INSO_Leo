# RFQ-021 — 安装、首次启动与回滚操作手册（R3）

**本手册只准备、未执行。** 本轮没有停旧程序、没有备份生产 SQLite、没有覆盖安装、没有启动新程序。

适用对象：Owner 在批准维护窗口后，按顺序执行的人。每一步都有"中止条件"；任一条件不满足就**停在这一步**，不要继续。

固定对象（**整套证据只对应这一个候选**；r1/r2 的产物已归档，不得混用）：

| 项目 | 值 |
|---|---|
| 源码提交 | `1ef20c81`（R3 修复；基线 `8cded532`） |
| 候选 EXE | `build/windows-release-stage-1.6/dist/INSO_V1.6/INSO_V1.6.exe` |
| 候选 EXE SHA256 | `faa3166d41db5a738348dc57f6adebbfcda0b3dbf29eb99f3549cf0d0d2596c1` |
| 候选 EXE 字节数 | 8,459,010 |
| 文件数 | 2,872 |
| 清单 | `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256`（自身 SHA256 `accd463a78c23d5739d298a0ea6d2735ab1f51af051aad13900697ca406455ae`） |
| 当前运行版本 | `dist/INSO_V1.6/INSO_V1.6.exe`，SHA256 `e9e3da33417414abac53f8a88a67d9f053bcdaeab9730eae9ad8bd7870dffad0`（源码血缘 `NOT_VERIFIED`） |
| 生产数据库 | `dist/INSO_V1.2/runtime/production/workflow.sqlite3`（经 `dist/INSO_V1.6/runtime` junction 指向 `dist/INSO_V1.4/runtime`） |

> **两个版本的能力差异（重要）：** `--safe-preview` 只存在于 RFQ-021 这条发行线。**当前运行的旧 EXE 没有这个参数**，所以回滚后不能靠它验证界面，只能靠哈希核对；把旧程序"启动看看"属于业务动作，要另批。

---

## 第 1 步：离线准备（不需要停机）

```powershell
cd D:\Program_Leo\INSO_Leo\.worktrees\v16-rfq016-stabilization

# 1.1 复算整个候选目录，必须 PASS 才继续
powershell -ExecutionPolicy Bypass -File scripts\verify_release_candidate.ps1 `
  -CandidateDir build\windows-release-stage-1.6\dist\INSO_V1.6 `
  -Manifest docs\evidence\rfq021\INSO_V1.6-artifact-manifest.sha256

# 1.2 快照当前运行版本（只读；不停程序、不碰数据库、不复制 junction）
powershell -ExecutionPolicy Bypass -File scripts\backup_running_release.ps1 `
  -SourceDir D:\Program_Leo\INSO_Leo\dist\INSO_V1.6 `
  -RuntimeConfigDir D:\Program_Leo\INSO_Leo\dist\INSO_V1.4\runtime `
  -Destination D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-20261115T120000Z
```

**验收：** `VERIFY_RESULT = PASS`；快照目录含 `INSO_V1.6.exe`、`_internal\`、`config\`、`PROGRAM-MANIFEST.sha256`、`database-state.json`，且 `BACKUP_RESULT = PASS`。
**中止：** 任何一项不满足。不要重新构建"凑一致"。

---

## 第 2 步：停机（维护窗口内唯一会中断业务的一步）

正常停止（二选一）：界面点「安全停止」等本轮结束，或点窗口关闭让程序走安全退出。
**不做：** `taskkill`、任务管理器强杀、关闭 Chrome 9222。

**无在途效果检查（停机后立刻做）：**

```powershell
Get-Process -Name INSO_V1.6 -ErrorAction SilentlyContinue | Select-Object Id, StartTime
Get-Process chrome | Where-Object { $_.Id -eq 24164 }   # 受保护会话应仍在，不要动
```

**验收（全部满足才继续）：** 主程序与 watcher 两个进程都消失；界面无"正在处理订单/报价"；最近一轮模块周期已结束；没有刚发出未确认的点击/请求。

**中止条件：** 120 秒内未退出或只退一个；停在「正在安全结束」；日志显示未确认的在途操作；存在未结算的 `UNKNOWN`/`SENT`。
**中止后：** 保留现场，不安装、不强杀、不重启。

---

## 第 3 步：数据库一致性备份（停机后、安装前，**必做**）

```powershell
$src = "D:\Program_Leo\INSO_Leo\dist\INSO_V1.4\runtime\production\workflow.sqlite3"
$dir = "D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-20261115T120000Z"
$dst = Join-Path $dir "workflow.sqlite3"

sqlite3 $src ".backup '$dst'"
sqlite3 $dst "PRAGMA quick_check;"
Get-FileHash $dst -Algorithm SHA256
```

**验收：** `quick_check` 返回 `ok`；把哈希写进本次维护记录；备份文件应大于 4 KB 且以 `SQLite format 3` 开头。

**中止：** 本机没有 `sqlite3.exe`、`quick_check` 不是 `ok`、或备份文件头不对 → **停在这里**。不要用 `Copy-Item` 复制运行中的 SQLite 冒充一致备份，也不要删 `-wal`/`-shm`。

> 安装脚本会强制要求你提供这个备份路径并显式确认已校验；没有它，脚本直接失败退出。

---

## 第 4 步：安装候选（失败关闭）

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_release_candidate.ps1 `
  -CandidateDir    build\windows-release-stage-1.6\dist\INSO_V1.6 `
  -Manifest        docs\evidence\rfq021\INSO_V1.6-artifact-manifest.sha256 `
  -TargetDir       D:\Program_Leo\INSO_Leo\dist\INSO_V1.6 `
  -RollbackDir     D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-20261115T120000Z `
  -DatabaseBackup  D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-20261115T120000Z\workflow.sqlite3 `
  -ConfirmDatabaseBackupVerified `
  -ConfirmSwitch
```

脚本在改动任何文件**之前**依次核验，任一不满足即抛错退出：

1. 没有 `INSO_V1.6` 进程在运行；
2. 回滚快照存在，且 `PROGRAM-MANIFEST.sha256` 里每个文件都重算一致（≥2 项，不空）；
3. 数据库备份存在、>4 KB、文件头是 `SQLite format 3`，且操作者用 `-ConfirmDatabaseBackupVerified` 明确确认已跑过 `quick_check`；
4. 候选按清单逐文件复算 PASS；
5. `runtime` 仍是 junction（绝不被替换）。

**它会做的：** 旧 `_internal` → `_internal.prev-<UTC>`，旧 EXE → `INSO_V1.6.exe.prev-<UTC>`，复制候选，回读安装后 EXE 哈希。
**它不会做的：** 不碰 `runtime` junction、不启动程序、不写数据库、不迁移。

**验收：** `INSTALL_RESULT = PASS` 且 `installed_exe_sha256` = 候选哈希。

---

## 第 5 步：首次启动 —— 只允许安全预览（**新** EXE）

```powershell
Start-Process "D:\Program_Leo\INSO_Leo\dist\INSO_V1.6\INSO_V1.6.exe"
```

**应当看到：** 界面正常；开始按钮显示「安全预览（不启动业务）」且不可点；`runtime\logs` 没有新的 IMAP/SMTP 与迁移记录。
**应当没有：** 业务线程、邮件连接、Chrome 被接管、任何外部写入。

**验收：** 界面能刷新不卡死；关闭后 120 秒内两个进程都消失；再启动一次仍是预览态。
另有硬证据：`INSO_V1.6.exe --preview-self-check` 会自己开两次界面并写 `runtime\logs\v16-preview-self-check.json`（`ok: true`）。

**中止：** 界面空白/卡死、关不掉、退出后留进程 → 进第 7 步。

---

## 第 6 步：启用业务（**必须 Owner 单独确认**，本轮未授权）

前提：第 5 步全部通过；Owner 书面确认目标订单、允许模块、允许写入、时间窗口；3 条历史 hold、SHAHAB/115、221 行的处置方式已明确（默认保持原状）。

```powershell
INSO_V1.6.exe --scoped-start `
  --scope-inquiries inq_xxxxxxxxxxxxxxxxxxxxxxxx `
  --scope-modules inquiry `
  --scope-writes "" `
  --start-inquiry
```

- `--scope-modules` **只能写 `inquiry`**；报价 / TP / 通知没有按订单过滤的入口，写进去会被拒绝（`SCOPE_MODULE_NOT_ISOLATABLE`）。
- `--scope-writes` 为空 = 只读试运行；可用目标是 `google` 与 `inso`（`smtp` 同样无过滤能力，会被拒绝）。
- 要写入必须同时给 `--scope-writes` 与 `--scope-approval OWNER-APPROVED:<审批编号>`。
- **不会隐式升级：** 只写 `--start-inquiry` 不给 `--scoped-start` 会被拒绝并弹窗。

---

## 第 7 步：冷回滚（**单独审批**的一步）

触发条件：第 5 步验收失败，或新版本出现不可接受的问题。

**这是"冷回滚"：先停程序、再换回文件、不启动，三步分离。** 回滚本身不包含"把业务跑起来"。

1. **停机**：按第 2 步的标准正常停止新程序；不强杀。若新程序无法正常退出 → 停止回滚并上报，不要强杀后继续。
2. **换回程序与配置**（此时目标目录必须是停止状态）：

```powershell
$t = "D:\Program_Leo\INSO_Leo\dist\INSO_V1.6"
$stamp = "<第4步打印的后缀>"
Remove-Item "$t\_internal" -Recurse -Force
Rename-Item "$t\_internal.prev-$stamp" "_internal"
Remove-Item "$t\INSO_V1.6.exe" -Force
Rename-Item "$t\INSO_V1.6.exe.prev-$stamp" "INSO_V1.6.exe"
# 配置：与快照 config\ 里同名文件逐个比对哈希，不一致才回填
Get-FileHash "$t\INSO_V1.6.exe" -Algorithm SHA256   # 必须等于 e9e3da33…
```

3. **只做哈希核对，不启动旧程序**。旧 EXE 没有 `--safe-preview`，"启动看看界面"属于业务动作，要再批。
4. **数据库：默认不动。** 只有同时满足以下条件才用第 3 步备份恢复：Owner 明确同意丢弃新版写入的数据；已确认没有需要保留的 SAVED 记录/邮件；已确认没有未结算的写入意图。恢复前先把当前库另存一份，禁止直接覆盖后无法回退。
5. **回滚后的业务重启是第三步，单独审批。** 它意味着旧程序重新连 Google/INSO/邮件；启动前先确认到 Google 的连通性（见 `INCIDENT-20261115.md` 的可用性观察项）。

**回滚证据：** 记下回滚时间、当时 EXE 哈希、配置是否回填、数据库是否恢复、恢复前后业务状态。

---

## 第 8 节：会遇到的状态

| 现象 | 含义 | 该怎么做 |
|---|---|---|
| 按钮「未配置受控试运行范围」 | 受控模式但缺范围参数 | 关掉，按第 6 步补参数 |
| `EXTERNAL_WRITE_NOT_IN_SCOPE` | 范围内没有该写入目标 | 正常拒绝；需要写入就重新审批范围 |
| `SCOPE_MODULE_NOT_ISOLATABLE` | 点名了无法按订单隔离的模块 | 只保留 `inquiry`；报价/TP 需另开任务 |
| `WRITE_INTENT_PENDING` | 有写入已登记未结算 | **不要清**；先核对真实结果再人工结算 |
| `WRITE_LEDGER_UNAVAILABLE` | 写入账本不可读/不可写 | 全站禁止外部写入；查库与磁盘权限后重启 |
| 预览关闭后日志有 `invalid command name ...` | Tk 内部回调提示，无功能影响 | 记录即可；若导致退出卡住则回滚 |

---

## 本轮未验证（如实记录）

- 本手册任何一步都没有在生产上执行（第 1 步的只读校验除外）。
- `sqlite3.exe` 是否存在、`.backup` 实际耗时：`NOT_VERIFIED`。
- 旧程序 Stop 耗时、GUI 停刷、Chrome 残留页：历史观察项，未测。
- 新旧程序同时连同一套生产资源：明令禁止，未测。
