# RFQ-021 — 安装、首次启动与回滚操作手册（R5）

**本手册只准备、未执行。** 本轮没有停旧程序、没有备份生产 SQLite、没有覆盖安装、没有启动新程序。

适用对象：Owner 在批准维护窗口后按顺序执行的人。每一步都有"中止条件"；任一条件不满足就**停在这一步**。

固定对象（**整套证据只对应这一个候选**；r1–r4 与本轮 P0 补丁前的 R5 产物均已归档为 `-r1…-r4`、`-r5-pre-p0`，不得混用）：

| 项目 | 值 |
|---|---|
| 源码提交 | `6a75cc93130c8b7805569edfc3131f82032e22c4` |
| 候选 EXE | `build/windows-release-stage-1.6/dist/INSO_V1.6/INSO_V1.6.exe` |
| 候选 EXE SHA256 | `f1a0351dd9837239043250fa86b9d8c921620d151eef660529d85eaecca020e2` |
| 候选 EXE 字节数 | 8,461,034 |
| 文件数 | 2,872 |
| 清单 | `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256`（自身 SHA256 `5dfce4c17e1583f401d78123d17378a527aeca78df356222e4d22ec954c33a64`） |
| 当前运行版本 | `dist/INSO_V1.6/INSO_V1.6.exe`，SHA256 `e9e3da33417414abac53f8a88a67d9f053bcdaeab9730eae9ad8bd7870dffad0`（8,422,619 B；源码血缘 `NOT_VERIFIED`） |
| 配置树 | `dist/INSO_V1.6/runtime` → junction → `dist/INSO_V1.4/runtime`（`production.json` / `research.json` 在这里） |
| 生产数据库 | 以配置里的 `sqlite_path` 为准：`dist/INSO_V1.2/runtime/production/workflow.sqlite3`（`dist/INSO_V1.2/runtime` 本身是另一个 junction，指向 `.worktrees/v1-2-design/dist/INSO_V1.1/runtime`） |

> **两个版本的能力差异（重要）：** `--safe-preview` 只存在于 RFQ-021 这条发行线。**当前运行的旧 EXE 没有这个参数**，回滚后只能靠哈希核对，不能靠它验证界面；把旧程序"启动看看"属于业务动作，要另批。

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
  -Destination D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-<UTC>
```

配置**不再由你指定**：脚本从 `dist\INSO_V1.6\runtime` 这个 junction 的目标里取 `production.json` / `research.json`。你指错了目录它就直接失败——那正是"用别处的配置回滚"这种事故的来源。

**验收：** `VERIFY_RESULT = PASS`；`runtime_junction_target` 打印出的路径就是 `dist\INSO_V1.4\runtime`；`payload_files_verified` 等于源 `_internal` 文件数；快照含 `INSO_V1.6.exe`、`_internal\`、`config\production.json`、`config\research.json`、`PROGRAM-MANIFEST.sha256`、`database-state.json`，且 `BACKUP_RESULT = PASS`。
**中止：** 任何一项不满足。不要重新构建"凑一致"。

快照不是"复制完就写个清单"：脚本会逐文件把复制件和**正在运行的** `_internal` 对比哈希，并且 `robocopy` 退出码 ≥4（有文件没对齐）直接拒绝——"自洽但残缺"的快照会完美通过它自己的清单，那正是回滚时把坏版本装回去的原因。

---

## 第 2 步：停机（维护窗口内唯一会中断业务的一步）

正常停止（二选一）：界面点「安全停止」等本轮结束，或点窗口关闭让程序走安全退出。
**不做：** `taskkill`、任务管理器强杀、关闭 Chrome 9222。

```powershell
Get-Process -Name INSO_V1.6 -ErrorAction SilentlyContinue | Select-Object Id, StartTime
```

**验收（全部满足才继续）：** 主程序与 watcher 两个进程都消失；界面无"正在处理订单/报价"；最近一轮模块周期已结束；没有刚发出未确认的点击/请求。
**中止条件：** 120 秒内未退出或只退一个；停在「正在安全结束」；日志显示未确认的在途操作；存在未结算的 `UNKNOWN`/`SENT`。
**中止后：** 保留现场，不安装、不强杀、不重启。

---

## 第 3 步：数据库备份 + 来源校验（停机后、安装前，**必做**）

```powershell
# 库的位置由"当前生效的配置"决定，不要凭目录猜。
$prod = Get-Content "D:\Program_Leo\INSO_Leo\dist\INSO_V1.6\runtime\production.json" -Raw | ConvertFrom-Json
$src = [string]$prod.sqlite_path
if (-not (Test-Path -LiteralPath $src -PathType Leaf)) { throw "配置指向的库不存在：$src" }
$src   # 第 1 步的 database-state.json 里 resolved_path 应该就是这个文件

$dir = "D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-<UTC>"
$dst = Join-Path $dir "workflow.sqlite3"

# 停机后没有任何连接，直接逐字节复制：这份副本与源文件哈希相同，可被证明"就是它"。
Copy-Item -LiteralPath $src -Destination $dst

powershell -ExecutionPolicy Bypass -File scripts\verify_database_backup.ps1 `
  -DatabaseBackup $dst `
  -SourceDatabase $src `
  -InstallDir     D:\Program_Leo\INSO_Leo\dist\INSO_V1.6
```

> **本机现状（2026-11-15 实测，不要按旧手册的路径抄）：** `dist\INSO_V1.6\runtime` 是指向 `dist\INSO_V1.4\runtime` 的 junction；`dist\INSO_V1.4\runtime` 里**没有** `production\` 子目录。正在使用的库由 `production.json` 的 `sqlite_path` 指向 `dist\INSO_V1.2\runtime\production\workflow.sqlite3`，而 `dist\INSO_V1.2\runtime` 本身又是一个指向 `.worktrees\v1-2-design\dist\INSO_V1.1\runtime` 的 junction。也就是说**配置树与账本树是两个不同的 junction**，所以第 3 步必须以配置里的路径为准；`backup_running_release.ps1` 也从配置里读这个路径，不再拼 `runtime\production\workflow.sqlite3`。

**为什么不是 `sqlite3 .backup`：** `.backup` 写出的是重新打包的数据库，字节与源文件不同，于是"这份备份确实来自当前这台机器的这一份库"就无法用哈希证明。停机之后库是静止的，逐字节复制既一致又可证明。**如果停机后仍有非空 `-wal`，说明停机不干净，直接中止**（校验脚本也会拒绝）。

**验收：** `DB_VERIFY_RESULT = PASS`；同目录出现 `workflow.sqlite3.verify.json`，其中 `database_sha256 == source_sha256`、`integrity_check = ok`、`purchase_rows >= 1`、`event_age_hours` 在限值内、`program_stopped = true`、`process_state` 非空、`wal_clean = true`、`quiescence` 非空、`open_write_intents = 0`，且 `write_intent_state` 是下列之一：

- `NONE_PROVEN`：写入意图台账存在，查询成功，未结算数为 **0**（真 0，不是未知）。
- `LEGACY_NO_JOURNAL_PROVEN`：台账表**确实不存在**（旧版库），并且旧状态已逐项核实：`legacy_unknown_write.unprotected_unknown_rows = 0`、`unattributed_holds = 0`。也就是说，旧库记录到的每一笔 UNKNOWN/SENT 写入都仍被活动告警或 V13 hold 保护着——**只读核实，不清除任何 hold**。

校验脚本的"停机一致性"不是靠你口头确认，而是四道实测：

1. **进程查询本身必须成功**，且每个 `INSO_V1.6.exe` 进程的可执行路径**都读得到**，且没有任何一个从 `-InstallDir` 运行。查询失败、权限不足、读不到路径，一律判为"无法证明已停机"并拒绝——**"查不到"不等于"没在跑"**（暂停中的程序可能已关闭数据库句柄，所以只靠文件句柄证明不够）。
2. **没有任何进程仍打开这个库**：脚本以只读、`FileShare.None` 独占方式打开源文件再立即释放。只要还有别的连接（包括另一份安装、或残留的 watcher）持有它，就会拒绝。这一步同时排除了"另一份安装共用同一个 junction 库"这种最危险的情况。
3. **两侧 `-wal` 都为空**（复制件和源件都必须如此），证明没有未 checkpoint 的提交。
4. **写入意图必须被证明**（见上面的 `write_intent_state`）：台账缺表、查询报错、计数为 NULL 或非数字，都不会被当成 0。

**中止：** 没有 Python 解释器、`integrity_check` 不是 `ok`、表缺失、备份与源哈希不同或源路径对不上、最后一条业务事件过旧（默认 72 小时）、任一 `-wal` 非空、**源库仍被某个进程占用**、**进程状态无法证明**、`write_intent_state` 不是上面两种已证明状态、或旧库里存在未被保护的 UNKNOWN/SENT（那意味着上一次外部写入结果未确认，换版会丢失或重放真实订单，必须先人工核对；**禁止清表、禁止清 hold**）。

---

## 第 4 步：安装候选（失败关闭，改动前校验全部条件）

```powershell
$dir = "D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-<UTC>"
$old = "e9e3da33417414abac53f8a88a67d9f053bcdaeab9730eae9ad8bd7870dffad0"  # 当前已安装 EXE 的哈希

powershell -ExecutionPolicy Bypass -File scripts\install_release_candidate.ps1 `
  -CandidateDir    build\windows-release-stage-1.6\dist\INSO_V1.6 `
  -Manifest        docs\evidence\rfq021\INSO_V1.6-artifact-manifest.sha256 `
  -TargetDir       D:\Program_Leo\INSO_Leo\dist\INSO_V1.6 `
  -RuntimeTarget   D:\Program_Leo\INSO_Leo\dist\INSO_V1.4\runtime `
  -RollbackDir     $dir `
  -DatabaseBackup  (Join-Path $dir "workflow.sqlite3") `
  -DatabaseReport  (Join-Path $dir "workflow.sqlite3.verify.json") `
  -ExpectedPreviousExeSha256 $old `
  -ConfirmDatabaseBackupVerified `
  -ConfirmSwitch
```

脚本在改动任何文件**之前**依次核验，任一不满足即抛错退出：

1. 授权开关齐全，`-ExpectedPreviousExeSha256` 是 64 位十六进制。
2. 回滚快照存在，`PROGRAM-MANIFEST.sha256` 里每个文件都重算一致。
3. **快照就是当前安装的这一版**：快照 EXE 哈希 = 声明的旧版哈希 = 目标 EXE 实际哈希；`_internal` 文件数与清单条目一致、逐文件一致；快照里没有目标不存在的程序文件。
4. `runtime` 必须是 **Junction**（symlink 等其他 reparse point 会被拒绝）且指向 `-RuntimeTarget`；**缺失或目标不存在也失败**。
5. 快照里的 `config\production.json` / `research.json` 与 **junction 后面那份实时配置**逐字节一致；且 `production.json` 的 `sqlite_path` 仍指向报告覆盖的那个库。
6. 数据库报告：`PASS`、`schema_version >= 4`、`quiescence` 非空、`process_state` 非空、`integrity_check=ok`、三张必需表、`purchase_rows>=1`、`program_stopped`、`wal_clean`、事件未过期；报告哈希 = 备份实际哈希 = 源哈希；**报告的 `install_dir` 必须就是本次 `-TargetDir`、报告的 `source_database` 必须就是当前配置指向的库**（防止拿另一台/另一份安装的有效报告来授权切换）。
7. **写入意图必须是"确认的 0"，不是"未知"**：`write_intent_state` 只能是 `NONE_PROVEN`（台账存在且未结算数确为 0）或 `LEGACY_NO_JOURNAL_PROVEN`（旧库无台账，且 `unprotected_unknown_rows = unattributed_holds = 0`）；计数为 NULL/非数字、台账缺表或查询失败、旧库存在未受保护的 UNKNOWN/SENT，一律拒绝。
8. 候选按清单逐文件复算 PASS。
9. 最后一步才检查**是否有进程从 `-TargetDir` 运行**（按路径判定，不只是进程名），且**进程查询本身必须成功、每个 `INSO_V1.6.exe` 的 EXE 路径都读得到**；无法证明即拒绝。**第一次移动文件之前再查一次**，同样的失败关闭规则——查不到不等于没在跑，那一步拒绝时目标目录还没有任何改动。

**安装后**：对安装目录里的**每一个程序文件**按候选清单重新算哈希，并核对 `_internal` 文件总数。数量相同但内容不同（同数量损坏）会被判为失败。

**它会做的：** 旧 `_internal` → `_internal.prev-<UTC>`，旧 EXE → `INSO_V1.6.exe.prev-<UTC>`，复制候选，逐文件复算。
**它不会做的：** 不碰 `runtime` junction、不启动程序、不写数据库、不迁移。

**验收：** `INSTALL_RESULT = PASS`，`installed_exe_sha256 = f1a0351dd9837239043250fa86b9d8c921620d151eef660529d85eaecca020e2`，`installed_files_verified = 2,872`。

**如果中途失败（重要）：**

| 脚本输出 | 含义 | 你要做什么 |
|---|---|---|
| `INSTALL_RESULT = FAIL_RESTORED` | 复制/校验失败，脚本已把旧程序和旧 `_internal` 放回，并**按快照逐文件复算**通过（输出 `restored_files_verified`） | 目标目录已回到旧版；**不要启动任何程序**，先上报 |
| `INSTALL_RESULT = ROLLBACK_REQUIRED` | 自动恢复没做完或没通过校验（`restore_problem = …` 会写明是哪一条） | 按 `restore_from` / `restore_exe` 手工换回（快照 `snapshot_dir` 是参考副本），再用**旧清单**跑 `-VerifyInstalledOnly` 确认 |
| `INSTALL_RESULT = FAIL` | 在校验阶段就拒绝，目标目录**未被改动** | 按报错修材料，重来 |

任何时候都不要"再装一次试试"：先确认目标目录里是哪个版本（`Get-FileHash dist\INSO_V1.6\INSO_V1.6.exe`）。

复检（只读，可随时跑）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_release_candidate.ps1 `
  -TargetDir D:\Program_Leo\INSO_Leo\dist\INSO_V1.6 `
  -Manifest  docs\evidence\rfq021\INSO_V1.6-artifact-manifest.sha256 `
  -VerifyInstalledOnly
```

---

## 第 5 步：首次启动 —— 只允许安全预览（**新** EXE）

```powershell
Start-Process "D:\Program_Leo\INSO_Leo\dist\INSO_V1.6\INSO_V1.6.exe"
```

**应当看到：** 界面正常；开始按钮显示「安全预览（不启动业务）」且不可点；`runtime\logs` 没有新的 IMAP/SMTP 与迁移记录。
**应当没有：** 业务线程、邮件连接、Chrome 被接管、任何外部写入、后台登录巡检、站点级告警结算。

**验收：** 界面能刷新不卡死；关闭后 120 秒内两个进程都消失；再启动一次仍是预览态。
硬证据：`INSO_V1.6.exe --preview-self-check` 会自己开两次界面并写 `runtime\logs\v16-preview-self-check.json`（`ok: true`）。

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
- **范围覆盖启动、轮询、后台、自动恢复与手动入口**：范围外订单不会被判中断/判完成/判跳过、告警不会被清；跨站点登录巡检（含 `check_only`）整体拒绝；站点级历史告警不结算。

---

## 第 7 步：冷回滚（**单独审批**的一步）

触发条件：第 5 步验收失败，或新版本出现不可接受的问题。

1. **停机**：按第 2 步正常停止新程序；不强杀。无法正常退出 → 停止回滚并上报。
2. **先证明快照本身完好，再用它换回程序**（目标目录必须是停止状态）：

```powershell
$t = "D:\Program_Leo\INSO_Leo\dist\INSO_V1.6"
$snapshot = "D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-<UTC>"
$prevInternal = "<第4步打印的 previous_internal>"
$prevExe      = "<第4步打印的 previous_exe>"

# 0) 快照副本逐文件自检；必须 INSTALLED_VERIFY = PASS 才继续
powershell -ExecutionPolicy Bypass -File scripts\install_release_candidate.ps1 `
  -TargetDir $snapshot -Manifest (Join-Path $snapshot "PROGRAM-MANIFEST.sha256") -VerifyInstalledOnly

# 1) 换回（用第 4 步打印的两个 .prev 路径，不要自己拼时间戳）
Remove-Item "$t\_internal" -Recurse -Force
Move-Item -LiteralPath $prevInternal -Destination "$t\_internal"
Remove-Item "$t\INSO_V1.6.exe" -Force
Move-Item -LiteralPath $prevExe -Destination "$t\INSO_V1.6.exe"
Get-FileHash "$t\INSO_V1.6.exe" -Algorithm SHA256   # 必须等于 e9e3da33…

# 2) 换回后再用同一份快照清单逐文件核对
powershell -ExecutionPolicy Bypass -File scripts\install_release_candidate.ps1 `
  -TargetDir $t -Manifest (Join-Path $snapshot "PROGRAM-MANIFEST.sha256") -VerifyInstalledOnly
```

第 2 步的第二次核对同样必须 `INSTALLED_VERIFY = PASS`；只要有一项不符，就说明换回的旧版不完整，停止并向 Owner 上报，不要"再试一次"。

3. **配置**：与快照 `config\` 同名文件逐个比对哈希，不一致才回填；回填后再用旧版哈希确认。
4. **只做哈希核对，不启动旧程序**。旧 EXE 没有 `--safe-preview`，"启动看看界面"属于业务动作，要再批。
5. **数据库：默认不动。** 只有在 Owner 明确同意丢弃新版写入、且已确认没有需要保留的 SAVED 记录/未结算写入意图时，才用第 3 步的备份恢复；恢复前先把当前库另存一份，禁止覆盖后无法回退。
6. **回滚后的业务重启是第三步，单独审批。** 启动前先确认到 Google 的连通性（见 `INCIDENT-20261115.md` 的可用性观察项）。

**回滚证据：** 记下回滚时间、当时 EXE 哈希、配置是否回填、数据库是否恢复、恢复前后业务状态。

---

## 第 8 节：会遇到的状态

| 现象 | 含义 | 该怎么做 |
|---|---|---|
| 按钮「未配置受控试运行范围」 | 受控模式但缺范围参数 | 关掉，按第 6 步补参数 |
| `EXTERNAL_WRITE_NOT_IN_SCOPE` | 范围内没有该写入目标 | 正常拒绝；需要写入就重新审批范围 |
| `SCOPE_MODULE_NOT_ISOLATABLE` | 点名了无法按订单隔离的模块 | 只保留 `inquiry`；报价/TP 需另开任务 |
| `SCOPE_INQUIRY_IDS_CONFLICT` | 显式订单集与范围不一致 | 正常拒绝；两组必须一致 |
| `WRITE_INTENT_PENDING` | 有写入已登记未结算 | **不要清**；先核对真实结果再人工结算 |
| `WRITE_LEDGER_UNAVAILABLE` | 写入账本不可读/不可写（重试后仍失败） | 全站禁止外部写入；查库与磁盘权限后重启 |
| 安装报 `snapshot does not reproduce the installed program` | 快照与当前安装不是同一版 | 重做第 1 步；不要手工改清单 |
| 安装报 `not the live configuration behind runtime` | 快照配置不是 junction 后面那份 | 重做第 1 步；不要手工拼配置 |
| 安装报 `runtime points at …` / `not a Junction` | junction 指向或类型不对 | 停下核对布局；不要重建 junction 来"通过检查" |
| 安装报 `the configured ledger … is not the database this report covers` | 配置指向的库与备份报告不是一个 | 重做第 3 步 |
| 安装报 `the database report belongs to …` | 报告是另一份安装生成的 | 重做第 3 步，不要改报告 |
| 安装报 `unresolved write intent(s) were in the ledger` | 停机时仍有未确认的外部写入 | **不许换版**；先按真实结果人工核对并结算，禁止清表 |
| 校验/安装报 `write-intent count is not a number / not a proven number` | 意图台账缺表、查询失败或计数为 NULL | 未知不是 0：旧库按 `LEGACY_NO_JOURNAL_PROVEN` 逐项核实；否则停下核对 |
| 校验报 `holds N unprotected_unknown_rows` | 旧库有 UNKNOWN/SENT 写入没有任何告警/hold 保护 | 先人工核对该订单真实结果；禁止清 hold、禁止把未知改成已结算 |
| 校验/安装报 `cannot prove INSO_V1.6 is stopped` | 进程查询失败、权限不足、或读不到某个进程的 EXE 路径 | 不要当成"没在跑"；用有权限的会话重查，必要时上报，禁止强杀后硬装 |
| 校验报 `another process still holds the live ledger open` | 停机不干净，或另一份安装还连着这个库 | 不要强杀、不要复制"凑一份"；先查清是谁还连着 |

---

## 本轮未验证（如实记录）

- 本手册任何一步都没有在生产上执行（第 1 步的只读校验除外）。
- 安装脚本的通过路径与失败恢复路径是在**隔离的合成安装目录**里验证的（`scripts\test_install_gates.ps1`：156 项检查全通过，含完整成功路径与上面列出的每一条拒绝路径），不是真实装机；生产程序在跑，安装脚本按设计拒绝同一路径。
- 最终候选的自检：`--self-check` / `--idle-self-check` / `--preview-self-check` 均 0；预览自检两轮 `ok: true`、开始按钮禁用、无业务线程/邮件服务。
- `sqlite3.exe` 是否存在：`NOT_VERIFIED`（第 3 步已改为停机后逐字节复制，不再依赖它）。
- 旧程序 Stop 耗时、GUI 停刷、Chrome 残留页：历史观察项，未测。
- 新旧程序同时连同一套生产资源：明令禁止，未测。
- 真实账本里是否还有未结算写入意图：**未读生产库**，未知；第 3 步会在维护窗口内直接判定并拒绝。
