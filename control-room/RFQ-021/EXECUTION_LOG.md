# RFQ-021 — execution log (final release candidate)

## RFQ-021-R5 — 部署完成（2026-11-16 07:57–08:1x +08:00，唯一 Executor）

- **结论：`INSTALLED_PREVIEW_PASS / ORDER_NOT_DONE`。** V1.6 已覆盖安装并通过安全预览自检；真实订单因**当前没有任何 `未发` 订单**而无法执行（两个工作表的 `未发` 行数均为 0）。
- **Owner 本次授权（2026-11-16 07:57）：** "授权，我要看到覆盖的新版程序，SHAHAB/115 不用管了是旧询价" —— 即授权处置上一轮报告的第 1 项阻断，并明确 SHAHAB/115 为旧询价、不再要求保护。据此对门禁做**定点修正 + 具名豁免**，其余安全门禁一律保留。

### 1. 门禁修正（只改 `scripts/verify_database_backup.ps1`，安装器与候选均未改动）

上一轮的 FAIL 来自一处已被实证的误判：26 单的 `SAVE_OUTCOME_UNKNOWN` 都在该单确认 `SAVED` 之前约 6 秒（派发未确认→重试→确认保存），但旧判定只认"活动告警或 hold 挂靠"，因此把已解决的历史当成未解决。现在 legacy 判定新增两类**显式、可审计**的解决方式：

| 解决方式 | 判据（全部满足才算） |
|---|---|
| `resolved_by_confirmed_save` | `outcome = SAVED` **且** `saved_record_ref` 非空 **且** `updated_at` **不早于**该单最后一笔 `SAVE_OUTCOME_UNKNOWN`（时间戳用 `datetime.fromisoformat` 解析，无法解析即视为未证明） |
| `owner_exempt_orders` | 必须同时给 `-OwnerExemptInquiry`（`^inq_[0-9a-f]{24}$`，逐个具名）与 `-OwnerExemptAuthority`；缺任一项直接拒绝 |

其余规则不变：缺表/查询失败/NULL 仍拒绝、hold 只读不清、`unattributed_holds` 必须为 0、未命中保护且不属于上述两类的单仍然拦。报告新增 `resolved_by_confirmed_save_orders`、`owner_exempted_orders`、`owner_exempt_authority`、`owner_exempt_unmatched`，并在 PASS 输出里逐项打印——豁免不会静默发生。

**门禁自测：** `scripts/test_install_gates.ps1` 扩到 **182 项，`GATE_TEST_RESULT = PASS`**（原 156 项无回归）。新增负向用例均按预期拒绝：SAVED 但无回执引用、SAVED 但时间早于不确定事件、豁免缺授权串、豁免 id 格式非法、未豁免的 `MANUAL_REVIEW` 仍拦；新增正向：确认保存后解决可装、具名豁免可装且报告记录授权与单号。

### 2. 数据库门禁（真实账本，PASS）

```
unknown_orders_considered      = 27
resolved_by_confirmed_save     = 26
owner_exempted_orders          = inq_99275e8e72b43fd6616fd686
owner_exempt_authority         = OWNER-APPROVED:SHAHAB-115-IS-OLD-INQUIRY-20261116
DB_VERIFY_RESULT = PASS     (database_sha256 = c50c3636…, source 同哈希)
purchase_rows = 37, max_event_at = 2026-11-14T21:51:31Z, event_age_hours = 26.16
```

### 3. 安装（PASS）

`install_release_candidate.ps1`：`INSTALL_RESULT = PASS`，`installed_exe_sha256 = f1a0351dd9837239043250fa86b9d8c921620d151eef660529d85eaecca020e2`，`installed_files_verified = 2872`。回滚材料：`INSO_V1.6.exe.prev-20261116T000225Z`（`e9e3da33…`）、`_internal.prev-20261116T000225Z`，快照与数据库备份仍在 `dist\release-backups\RFQ-021-pre-switch-20261115T164102Z`。安装后独立复核：EXE `f1a0351d…`、8,461,034 B、`_internal` 2871 文件、`runtime` junction 未改。

### 4. 安全预览自检（PASS）

`INSO_V1.6.exe --preview-self-check` → `runtime\logs\v16-preview-self-check.json`：`ok: true`，两轮均 `acquired: true`，标题 `INSO LEO V1.6 — Procurement Automation Control Center`，`start_button = 安全预览（不启动业务）`、`start_state = disabled`、`business_thread_started = false`、`order_thread_started = false`、`mail_service_started = false`、`process_services_consumed = false`、`state = 已停止`。退出码 0；控制台 `invalid command name …update` 属窗口销毁后的 after 回调噪声。自检后无 `INSO_V1.6` 残留进程（全量 380 进程，0 命中）。

### 5. 真实订单：未执行（`ORDER_NOT_DONE`，业务事实而非程序阻断）

- 原目标第 221 行 `FT2232H-56Q-REEL` 已 `SAVED`（`rec_440fafd…`），不得重复采购。
- 现场只读扫描：`2026` 221 行状态分布 `已报价给客户 84 / STATUS 73 / 空 39 / 采购已报价 13 / 成交 7 / 收到报价 1 / 发给采购 1`，**`未发` = 0**；`SHAHAB` 140 行 `已报价给客户 89 / 空 45 / 意向订单 3 / 成交 2`，**`未发` = 0**。
- `src/sheets/pending.py::discover_pending` 要求状态**恰好**为 `未发`，采购重跑亦要求 `未发`（`backend.py:2548`）。故当前没有可被合法领取的询价单，自动受控试运行无输入。把任何一行改回 `未发` 属篡改业务状态，不做。

**未发生的外部效果：** 无 Google 写入、无 INSO 采购、无 SMTP、未接管 Chrome 9222、未改生产库。**程序当前状态：** 新版已安装、未运行（预览自检已退出）。

## RFQ-021-R5 — 现场部署被门禁拒绝（2026-11-16 00:39，历史，已被上节取代）

- **结论：`DEPLOYMENT_FAILED / NOT_INSTALLED / NO_BUSINESS_ACTION`。** 依 Owner 2026-11-16 最终授权执行到第 3 步；自有数据库门禁在真实生产账本上 FAIL，安装器按设计只接受已证明状态，未绕过、未改库、未启程序、未产生任何外部效果。旧版 `e9e3da33…` 完好如初。
- **接管基线：** 分支 `workbuddy/v16-rfq016-stabilization`，文档 HEAD `f6096138`，冻结源码 `6a75cc93`，候选未变。

### 1. 旧程序停机（PASS，由程序自身记录证明）

`runtime\logs\runtime-86030824867e430d81c366c4e6a9f60a.{state,exit}.json`：PID `38948`，`exit_requested` 与 `app_finished` 同刻 `2026-11-15T16:28:58Z`（本地 `2026-11-16 00:28:58`），`exit_reason = owner_exit`，`application_exit_code = 0`，`exit.json` 判 `classification = normal`。进程枚举（`Get-Process` 全量 365 个，查询成功）中 `INSO_V1.6` 进程数 **0**；校验脚本判 `process_state = stopped (proven; 0 other INSO_V1.6 process(es), none under this install)`。无 `taskkill`、无强杀。

### 2. 候选与旧版核对（PASS）

`verify_release_candidate.ps1` → `VERIFY_RESULT = PASS`，`manifest_entries = 2872`、`files_on_disk = 2872`、`missing = 0`、`hash_mismatch = 0`、`unexpected = 0`、`candidate_exe_sha256 = f1a0351d…`。旧安装 `dist\INSO_V1.6\INSO_V1.6.exe` 实测 `e9e3da33…`、`_internal` 2870 文件，与手册预期一致。`runtime` 为真 Junction，目标 `D:\Program_Leo\INSO_Leo\dist\INSO_V1.4\runtime`。

### 3. 快照与数据库备份（PASS）

`backup_running_release.ps1` → `BACKUP_RESULT = PASS`，快照 `dist\release-backups\RFQ-021-pre-switch-20261115T164102Z`（`PROGRAM-MANIFEST.sha256` 2875 条目、`_internal` 2870 文件、`config\`、`database-state.json`、`runtime_junction_copied = FALSE`）。
生产库由实时 `production.json` 的 `sqlite_path` 定位：`dist\INSO_V1.2\runtime\production\workflow.sqlite3`，`1,204,224 B`，源无 `-wal`/`-shm`，停机后逐字节复制，**备份与源哈希同为 `c50c3636318a0de85acf3e14406e21a244468d4a8848239f1b6fa9fb1010dc03`**。`PRAGMA integrity_check = ok`。

### 4. 数据库门禁 —— FAIL（唯一阻断，且结构性）

```
process_state = stopped (proven; 0 other INSO_V1.6 process(es), none under this install)
DB_VERIFY_RESULT = FAIL
reason = the ledger predates the write-intent journal and its unknown-write state is
not proven: 27 unprotected unknown order(s), 0 unattributable hold(s).
```

账本为旧库：`workflow_v12_schema_migrations` 只有 `1201 / v1_2_additive_001`，无 `workflow_write_intents`。`legacy_unknown_write` 判定命中 27 单：

| 分类 | 数量 | 现场事实 |
|---|---|---|
| `SAVED` 且带真实 `saved_record_ref` | **26** | 每单的 `SAVE_OUTCOME_UNKNOWN` 事件都比该单 `purchase_state.outcome = SAVED` 早约 6 秒，即"派发未确认 → 重试后确认保存"，随后有 `PURCHASE_DATA_SAVED` / `HUMAN_RESOLUTION_RECORDED` / `NOTIFICATION_DELIVERY_SUCCEEDED` / `ALERT_RECOVERED`。写入结果已知，无重放风险，但**没有**活动告警或 hold 挂着它们，门禁因此计入未保护。 |
| `MANUAL_REVIEW`，无 `saved_record_ref` | **1** | `inq_99275e8e72b43fd6616fd686`（SHAHAB/115，MT7988A）：2026-10-06 `SAVE_DISPATCH_ARMED` 后 `SAVE_OUTCOME_UNKNOWN`，回读 `RECONCILIATION_AMBIGUOUS / RECONCILIATION_UNREADABLE`；2026-10-07 人工 `HUMAN_RESOLUTION_RECORDED`，`inquiry_state = HUMAN_COMPLETED`，但 `purchase_state` 仍停在 `MANUAL_REVIEW`；**无 hold、无活动告警**。 |

**为什么这构成结构性阻断、而不是一次误报：** 即使 26 单 SAVED 全部被正确排除，仅剩的 SHAHAB/115 仍使 `unprotected_unknown_rows = 1`，安装器第 7 条依旧拒绝。而让该单变成"已证明"只有两条路——把 `purchase_state` 改成已结算（伪造无回执的业务状态），或补一条活动 hold（自造保护）——两者都属于 Owner 明令禁止的"改数据库业务状态/清理 SHAHAB-115"。程序自身的人工处置流程（2026-10-07 那次）也**只**写了 `inquiry_state = HUMAN_COMPLETED`，不回填 `purchase_state`，所以不存在"按原机制走完就通过"的路径。清除 26 条历史 `SAVE_OUTCOME_UNKNOWN` 事件同样是篡改证据。

**因此没有执行第 4 步安装**：安装器在改动任何文件前即会以同一条件拒绝，失败关闭；主动跑一遍只会制造无谓的中间态。未安装、未启动新 EXE、未做 `--safe-preview`、未跑真实订单、未碰 Chrome 9222、未改生产库。

### 5. 只读现场核对（Read-only，Service Account）

- `INSO_QUOTE`，sheets：`2026`(gid 0) / `SHAHAB` / `报价输入`(489913321) 等 13 个；SA `rfq016-sheets-test@inso-509314.iam.gserviceaccount.com` 读取成功。
- **表头已移位，但源码已容错**：物理第 1 行是外来布局（`Model/Qty/Brand/Note/MPN/MFR/Qty/…`），真实契约表头在**物理第 5 行**（`STATUS/WHAT/CLASS/WHO/MPN/MFR/Qty/…`）。冻结源码 `src/sheets/worksheet_schema.py` 的 `SOURCE_HEADER_ANCHOR_ROW["2026"] = 0` + `SOURCE_HEADER_WINDOW = 10` 会在 1–10 行内有界扫描并命中第 5 行，故 `2026` 读取**不会**因表头下移而 `SHEETS_SCHEMA_UNAVAILABLE`。此前 2026-11-13 记录的"两种传输都要求第 1 行"在本冻结源码上已不成立。
- **原目标已完成，禁止重复采购**：物理第 221 行（也是最后一行）`STATUS = 发给采购`、`CLASS = C`、`MPN = FT2232H-56Q-REEL`、`MFR = FTDI`、`Qty = 105`、Brand 空；SQLite `inq_e15970df104e170d93b4169b` = `SAVED`，`saved_record_ref = rec_440fafd372440ecf9dacabf660dd155d`，`2026-11-14T03:59:17Z`。与历史回执一致 → 该单不得再次 Save/采购，Owner 指示的备选路径（另选一笔真实未发订单）因部署未成立而无法执行。

### 6. 现场状态

旧版在位且未变（`e9e3da33…`，2870 文件）；无 `INSO_V1.6` 进程；生产库哈希 `c50c3636…` 未变；worktree 干净；回滚材料为上述快照（本机 `_internal.prev-*` 目录均未被触碰）。**唯一需要的 Owner 决策：** 是否授权处置 SHAHAB/115（补证为已结算或补 hold），或授权对门禁做最小修正（需新构建，Owner 已声明不要 R6）。二者之外无合法通过路径。

## RFQ-021-R5 — closure round (2026-11-15 evening, Executor takeover)

- **Status:** `SOURCE_AND_OFFLINE_RELEASE_READY_FOR_CEO_REVIEW / RELEASE_HOLD / NOT_DEPLOYED` (R5 + its two-condition closure patch, submitted for the CEO's final R5 recheck)
- **Reviewed base:** CEO [REVIEW.md](REVIEW.md) R4 (`CHANGES_REQUESTED`, five consolidated blockers) and then R5 (`CHANGES_REQUESTED (2 fail-closed conditions only)`). R4 source `2ad471e7`, branch HEAD at takeover `c94d99ec`, R5 closure patch on source `2c58529d`.
- **Frozen source:** `6a75cc93130c8b7805569edfc3131f82032e22c4` (only documentation/evidence commits follow it; `src/` is unchanged since `2c58529d`, so the patch is in the scripts and their gate tests).
- **Candidate (one, final):** `build/windows-release-stage-1.6/dist/INSO_V1.6/INSO_V1.6.exe`, `8,461,034` B, SHA256 `f1a0351dd9837239043250fa86b9d8c921620d151eef660529d85eaecca020e2`, `2,872` files, no `runtime/`.
- **Manifest:** `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256`, self-SHA256 `5dfce4c17e1583f401d78123d17378a527aeca78df356222e4d22ec954c33a64`; r1–r4 and the pre-closure R5 manifest (`-r5-pre-p0`, `a969a9bf…`) are kept as history. **One candidate only.**
- **Superseded candidate (not evidence for this source):** `be7c0d3f…` / manifest `a969a9bf…` / gate count 107 — the R5 build before the closure patch. Preserved as `*-pre-p0`; never to be installed as this candidate.
- **Self-checks:** `--self-check` `0`, `--idle-self-check` `0`, `--preview-self-check` `0` (two real GUI rounds), `RELEASE_SCAN_OK`, `verify_release_candidate.ps1` `PASS（2,872/2,872，0 missing / 0 mismatch / 0 unexpected）`.

### 0. R5 closure patch — the CEO R5 review's two P0 gates

Only these two gates were touched; nothing else was reopened, and `src/` did not change.

**P0-1 — an unprovable write-intent count can no longer look like zero.**
Reproduced first: (`scripts/verify_database_backup.ps1`) caught every `sqlite3.Error` for `workflow_write_intents` into `open_write_intents = None`, and the PASS gate fired only when the value was non-null and `> 0`; `scripts/install_release_candidate.ps1` repeated the same nullable guard. On the pre-patch scripts the new harness cases failed exactly as the review predicted ("passed but should have refused").

Now the database gate answers one of three ways and refuses everything else:
- journal present and readable → the report carries a confirmed integer; a non-zero count refuses;
- journal absent → the ledger must **prove** it predates the journal: unknown purchase outcomes (`SUBMIT_UNCONFIRMED`, `UNKNOWN_WRITE_OUTCOME`, `READ_ONLY_RECONCILIATION_REQUIRED`, `MANUAL_REVIEW`), `SAVE_OUTCOME_UNKNOWN` events, active unknown-write alerts and active `UPDATE_RESULT_UNCONFIRMED` holds are enumerated; every unknown order must still be protected by an alert or by a hold that names it, and any hold whose evidence cannot be attributed refuses. Holds are **read, never cleared**;
- unreadable/wrong-schema journal, or a null/non-numeric count → `DETERMINATION_FAILED` → refuse.
The report (schema 4) carries `write_intent_state` (`NONE_PROVEN` / `LEGACY_NO_JOURNAL_PROVEN` / `LEGACY_NO_JOURNAL_UNPROVEN` / `DETERMINATION_FAILED`), `open_write_intents`, and the full `legacy_unknown_write` audit record. The installer accepts only the two proven states, requires `open_write_intents = 0`, and re-checks `unprotected_unknown_rows = unattributed_holds = 0` for the legacy state.

**P0-2 — an unqueryable or unidentifiable process can no longer read as "stopped".**
Reproduced first: `Get-CimInstance … -ErrorAction SilentlyContinue` plus a `$_.ExecutablePath` filter turned a failed query, a permission denial and an unreadable executable path into "not running". Both scripts now use one three-valued probe (`Get-StopState`): `-ErrorAction Stop`, any `INSO_V1.6.exe` process whose executable path cannot be read makes the state **unproven** (never "not running"), and an unproven state refuses. It is used at the database gate, at installer gate 7, and again immediately before the first `Move-Item`; the report carries `process_state`.

**Negative tests (red first, then green).** `scripts/test_install_gates.ps1` gained 11 cases. On the pre-patch scripts: 4 × "passed but should have refused" (unprotected legacy unknown, broken journal, null count, missing state) and 5 × "refused for the wrong reason" (the process faults did not even exist). After the patch: **156 checks, `GATE_TEST_RESULT = PASS`**, including the complete success path plus legacy-clean accepted with `LEGACY_NO_JOURNAL_PROVEN` and its audit record, legacy-protected accepted, legacy-unprotected refused, broken journal refused, null count refused, report without a proven state refused, verify refusing on a failed query and on an unreadable path, and the installer refusing at the gate and again at the pre-switch re-check — with the target EXE hash unchanged and no `PASS` printed.

### 1. B3 — rollback, backup and install (R4 blockers 1–3)

| Was | Now |
|---|---|
| backup took the configuration from `-RuntimeConfigDir` | it comes from the target of the install's own `runtime` junction; a `-RuntimeConfigDir` that disagrees is refused |
| backup copied `_internal` and wrote a manifest of whatever it copied | the copy is compared byte for byte with the running payload (count + every hash); `robocopy` exit ≥4 is refused, so a self-consistent partial snapshot cannot exist |
| backup described a *guessed* `runtime\production\workflow.sqlite3` | it reads `sqlite_path` from the live `production.json` and records `configured_path`/`resolved_path`. **This mattered on the real box:** the runtime junction points at `dist\INSO_V1.4\runtime`, which has no `production\` directory, while the live ledger is at `dist\INSO_V1.2\runtime\production\workflow.sqlite3` (itself a junction into the v1-2-design worktree). The old guessed path did not exist. |
| installer checked that the snapshot's config paths existed | it requires both mandatory configs and compares their bytes with the live config behind the junction |
| installer accepted any database report with `PASS` | the report must be schema ≥3, carry a quiescence proof, name **this** `install_dir`, name **this** ledger (`sqlite_path`, junction-normalised), bind copy hash = source hash = report hash, and have `open_write_intents = 0` |
| database `integrity_check` was the whole proof | `verify_database_backup.ps1` proves a clean stop three ways: no process from the install directory, **an exclusive handle can be taken on the ledger** (no other process still holds it), and **both** `-wal` sides are empty; plus required tables, non-empty purchase/event ledger, recency, purchase-outcome counts, active alerts and open write intents are recorded in the report |
| after a copy it counted `_internal` files | every program file is re-hashed against the candidate manifest, and the count must match |
| a failed switch only re-checked the EXE hash | the restore is exception-safe, then verified **file by file against the snapshot**; `FAIL_RESTORED` now means proven, otherwise `ROLLBACK_REQUIRED` names the exact things to restore by hand |
| — | a program starting during candidate verification is caught by a second path-based process check immediately before the first `Move-Item` |
| — | offline-gate fault injection (`-InjectSwitchFault`, `-InjectPostCopyCorruption`, `-InjectRestoreFault`) is honoured **only** when `RFQ021_OFFLINE_GATE_TESTS=1`, and each one can only force a failure |

Isolated synthetic-install harness (`scripts/test_install_gates.ps1`, production never touched because the process guard is path-based): **`156` checks, `GATE_TEST_RESULT = PASS`** — complete success path, then refusals for: missing authorisation switches, malformed expected hash, snapshot file changed/missing, wrong expected build, foreign/damaged/missing snapshot, foreign config directory, stale config, missing runtime junction, runtime that is a real directory, junction pointing elsewhere, report missing / from another install / naming another source, ledger still open, unresolved write intent, copy that is not the live ledger, stale ledger, uncheckpointed WAL, missing `-InstallDir`, post-copy mismatch, injected mid-switch failure (restored, verified file by file), corrupted post-copy bytes (count unchanged: caught), and an interrupted restore (`ROLLBACK_REQUIRED`, never `PASS`).

**Answer to "if the install fails halfway, how does the old program and config come back without losing or replaying a real order?"**
The old `INSO_V1.6.exe` and the old `_internal` are moved aside inside the target (`.prev-<UTC>`), never overwritten; the new payload is verified file by file; any failure restores both, re-verifies every program file against the snapshot, and reports `FAIL_RESTORED` (or `ROLLBACK_REQUIRED` with the exact paths). `runtime` (the config junction) is never moved or replaced. The database is not touched by the installer at all: the switch requires a proven, hash-identical, quiescent backup of the configured ledger taken after a clean stop, and refuses to run when any write intent is still unresolved — so a rollback cannot silently drop an unconfirmed external write, and nothing is replayed because every hold/UNKNOWN row stays in whichever ledger the operator chooses to keep.

### 2. B5/B6/B7 — effect-entry audit (R4 blocker 4 and the full-scope pass)

Every entrance that can produce an order state, event, alert, persisted write intent, Google/INSO/SMTP effect or Chrome/CDP operation was enumerated and traced to its **final executing function**:

| Entrance | Final gate |
|---|---|
| preview launch, `start()`, `start_process_services()`, `retry_failed_process_service()` | preview ⇒ no-op; scoped ⇒ needs `notification` module + `smtp` target |
| `initialize_run_state`, `discover_pending`, `prepare_pending`, `process_pending` | coordinator `_in_scope()` before any mutation (R4) |
| `PurchaseCompletionActions.retry_saved_statuses/process` | scope-filtered (R3) |
| notification dispatch | one choke point (`_run_notifications`), needs module + target |
| site recovery / incident settlement | **`resolve_incidents(..., within=<scope ids>)`**: settles program-level records and the run's own orders only; an out-of-scope order's incident evidence is left untouched (new in R5) |
| idle keep-alive login sweep, deferred-auth recovery sweep, login-all button | all three, plus `check_only=True`, refuse before touching Chrome (R4 + R5) |
| manual order actions (`request_order_action` → `_manual_request` → `_execute_order_action_impl`) | **the executor itself re-checks `_order_in_scope` + `_action_in_scope`** before the first effect (new in R5), so a direct/low-level call cannot bypass the button |
| order mail check, `reconcile_v12_save` | `_external_action_allowed("smtp", …)`; `reconcile_v12_save` has no caller |
| local DB writes / events / alerts / write intents | only inside the scoped loops; incident records stay program-level |
| external writes | one write lease + scope gate + durable write-intent journal (`WRITE_INTENT_PENDING`, `WRITE_LEDGER_UNAVAILABLE`) |
| purchase re-submission | `manual_purchase_retry_allowed` refuses `SUBMIT_UNCONFIRMED`, `INTERRUPTED_POSSIBLY_SENT`, `PURCHASE_RECORDED`, `STATUS_WRITE_PENDING`, `HUMAN_COMPLETED`, and refuses on **any** `SAVE_DISPATCH_ARMED` / `SAVE_CLICK_COMPLETED` / `SAVE_OUTCOME_UNKNOWN` / `PURCHASE_DATA_SAVED` event — UNKNOWN/SENT can never be retried automatically |
| operator diagnostics (`--cdp-self-check`, `--api-self-check`, `--diagnose-vault`) | explicit read-only probes: they attach/probe and read local config only; they start no business, write no order state and close nothing |
| GUI | only calls backend methods; no GUI module imports an adapter |

### 3. The six full-suite failures (R4 blocker 5)

- **Reproduction attempts (this host, unrestricted file access):** full suite twice — once with the R5 retry enabled, once with it **disabled** — plus `tests/gui tests/launcher` together. Result: `0 failures in the full suite; the six R4 nodeids passed in every attempt`; the only `BEGIN IMMEDIATE` refusal in a whole run was the deliberate lock test `test_supplement_scan_database` (`SQLITE_BUSY`, correctly refused), and **`SQLITE_READONLY` never occurred**. The six R4 nodeids passed every time.
- **Mechanism control (proved):** a WAL ledger whose `-wal`/`-shm` cannot be written fails `BEGIN IMMEDIATE` with exactly `sqlite3.OperationalError: attempt to write a readonly database` (`SQLITE_READONLY`, code 8) — measured directly, so that message identifies a write-denied ledger, not a changed code path. A denied *directory* gives `SQLITE_CANTOPEN` instead, which is why the ACL form matters.
- **Environment evidence:** the R4 runs were executed under a restricted file policy. The proof is still on disk: the pytest temporary trees that those runs created inside the repository (`D:\Program_Leo\INSO_Leo\.test_tmp_*`) are unreadable to the current user — even `Get-Acl` returns "unauthorised operation" — while the trees created by this round (`%TEMP%\pytest-of-Leo\pytest-94x`) are ordinary writable directories.
- **Conclusion:** the failures were an environment fault (a temporary tree the test process could not write), amplified by the launcher's correct fail-closed mapping `sqlite error → WORKFLOW_LEDGER_UNAVAILABLE → MODULE_PAUSED`. **Not proven:** which sandbox rule denied which file in that earlier session (that process's records are gone). **Not claimed:** that a source defect caused them.
- **Fix, without touching any test's intent:** `tests/conftest.py` now proves at session start that the session's temporary tree can hold a real WAL ledger (create, `BEGIN IMMEDIATE`, insert, commit, read back) and refuses the session with the path and the underlying error if it cannot. No test was deleted, skipped, deselected or loosened.
- **Hardening kept, honestly scoped:** `_transaction` retries a *contended* `BEGIN IMMEDIATE` (`SQLITE_BUSY`/`SQLITE_LOCKED`, measured in the suite) on a fresh connection — the body has not run, so no effect can be replayed. `SQLITE_READONLY` is **not** retried: it fails closed immediately, so the R4 symptom can never be masked. Pinned by `tests/workflow/test_rfq021_r5_ledger_retry.py`.

### 4. Tests (frozen source, one full run)

`docs/evidence/rfq021/pytest-report-r5.xml` — **`4,277 collected / 4,276 passed / 0 failed / 0 errors / 1 skipped in 328.56 s`** (run on frozen `6a75cc93`).

### 5. NOT_VERIFIED (unchanged business reality)

1. Nothing was installed, stopped, started or restarted against production; no Google/INSO/SMTP effect; production SQLite never opened for write; Chrome 9222 untouched.
2. The installer's success path is proven only in isolated synthetic installations, never against the real one (the real program is running, and the installer refuses by design).
3. Old-program Stop timing, GUI refresh stall and residual Chrome pages are unmeasured.
4. PyInstaller output is not bit-reproducible: `f1a0351dd9837239043250fa86b9d8c921620d151eef660529d85eaecca020e2` identifies this build only.
5. The running `E9E3DA33…` EXE still has no proven source lineage.
6. A real scoped business run was not executed; scope behaviour rests on negative/integration tests.
7. `sqlite3.exe` presence is irrelevant to the new runbook (the copy is byte-identical after a clean stop), but the actual duration of the maintenance window is unmeasured.
8. B4 clean stop and the real rollback remain `NOT_VERIFIED` until the Owner-authorized window.

---

## RFQ-021-R4 — Lean Review round (2026-11-15 afternoon)

- **Status:** `R4_SUBMITTED_FOR_CEO_REVIEW / RELEASE_HOLD / NOT_DEPLOYED`
- **Reviewed base:** CEO [REVIEW.md](REVIEW.md) (R3, `CHANGES_REQUESTED`); R3 source `1ef20c81`, Executor branch HEAD at review `cf592212` (docs only).
- **Source commits:** `557cde28` (scope + gates + hint) then `2ad471e7` (snapshot manifest BOM). **Final frozen source: `2ad471e7b3c0101f18f6edae05d77522c6f71d47`.**
- **Candidate (one, final):** `build/windows-release-stage-1.6/dist/INSO_V1.6/INSO_V1.6.exe`, **8,459,710 B**, SHA256 `199181856ac1430af5aa0bd0af37b6bf45a1bf17272413583b2bb6e27e679d32`, **2,872 files**, no `runtime/`.
- **Manifest:** `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256`, self-SHA256 `2de4df2f9f23fe56eea89633b25c46c941bbf9e7b35eae99bc855d2189c1e2e3`; r1/r2/r3 manifests kept as `-r1`/`-r2`/`-r3`. **One candidate only.**
- **Build inputs:** `scripts/build_windows_release.ps1` `ab35565a…`, `requirements-windows-release.lock` `3dc5d7a5…` (unmodified), `packaging/INSO_V1.1.spec` `d7574c20…`, `scripts/scan_release_artifact.py` `f2517340…`, `scripts/windows_release_entry.py` `ae4eafa5…`.
- **Manifest recomputation:** `verify_release_candidate.ps1` → 2,872 entries / 2,872 files, 0 missing, 0 mismatch, 0 unexpected, `VERIFY_RESULT = PASS`.
- **Self-checks on the candidate:** `--self-check` 0, `--idle-self-check` 0, `--preview-self-check` 0 (2 GUI rounds, 3 s, `"ok": true`), `RELEASE_SCAN_OK` ×2. Reports: `docs/evidence/rfq021/v16-preview-self-check-r4.json`, `v13-idle-self-check-r4.json`.

### Tests (frozen source, one full run)

`docs/evidence/rfq021/pytest-report-r4.xml` — **4,260 collected / 4,253 passed / 6 failed / 1 skipped in 387.78 s**.

Failed nodeids (all in `tests/launcher`, none in the new R4 suites):

1. `test_backend.py::test_empty_poll_defers_browser_bootstrap_until_an_inquiry_is_due[False]`
2. `test_backend.py::test_browser_bootstrap_failure_enters_manual_review_without_research_retry`
3. `test_backend.py::test_readiness_failure_closes_owned_browser_without_research_retry`
4. `test_backend.py::test_real_poll_seam_stops_batch_on_login_and_resumes_queued_inquiry`
5. `test_release_infrastructure.py::test_backend_closes_only_owned_browser_after_runtime_thread_exits[False]`
6. `test_release_infrastructure.py::test_backend_closes_only_owned_browser_after_runtime_thread_exits[True]`

Attribution, recorded as measured and not as a conclusion:

- Captured cause is uniform: `V12Fault(WORKFLOW_LEDGER_UNAVAILABLE) <- sqlite3.OperationalError(attempt to write a readonly database)` raised at `V12Store.resolve_incidents` → `BEGIN IMMEDIATE` on the test's temp database, after which the run state is `MODULE_PAUSED` instead of `STOPPED`.
- Each of these nodeids passes **5/5** when run alone, in this worktree and in archives of both `a577e94d` (pre-R4) and `2ad471e7`.
- Attempts to isolate an environment cause (fresh `--basetemp`, a short `D:\r4t` basetemp, removing the worktree's `runtime/` byproduct) changed *which* of the six failed but did not eliminate the set.
- Nodeids 5 and 6 are the same pair that failed on the untouched parent `e59ce62f` in earlier rounds and in the R3 run; the observed cause there was the identical readonly-temp-database fault.
- **No test was deleted, skipped, deselected or loosened.** The new R4 suites (20 tests) passed in this run.

### Install gates (offline, synthetic layout — never the production install)

`scripts/test_install_gates.ps1` → **`checks = 13`, `GATE_TEST_RESULT = PASS`**. Each case builds a throwaway install and asserts a refusal *and its reason*: missing `-ConfirmSwitch`, missing `-ConfirmDatabaseBackupVerified`, malformed expected hash, snapshot file changed, snapshot missing one `_internal` file, wrong expected EXE identity, missing runtime junction, junction pointing elsewhere, absent database report, report bound to different bytes — then the real `backup_running_release.ps1` output fed to the installer, which reaches the last gate (only possible if every material gate accepted it). The switch itself is `NOT_VERIFIED`: a real `INSO_V1.6` is running and the installer must refuse.

### What changed

| Area | Change |
|---|---|
| B5 history mutation | `V12WorkflowCoordinator._in_scope()` gates `initialize_run_state()` and `discover_pending()` before their quarantine / `HUMAN_COMPLETED` / `INVALID_INPUT_SKIPPED` / alert-recovery branches. `None` preserves legacy behaviour. |
| B3 rollback admission | Installer now proves the snapshot reproduces the installed build (EXE + every `_internal` file, no extra program file), requires `-ExpectedPreviousExeSha256` to match the live EXE, requires both mandatory configs, and requires `runtime` to *be* a junction pointing at exactly `-RuntimeTarget` (missing no longer passes). |
| B3 database proof | New `verify_database_backup.ps1`: read-only open, `PRAGMA integrity_check`, required tables, non-empty ledger, report bound to the file's SHA256. A magic header plus an acknowledgement is no longer accepted. |
| P1 UI | `order_action_hint()` consults `_order_in_scope()` and `_action_in_scope()`; three copies of the scope test collapsed into one definition. |
| Audit finding | The whole-browser login sweep was refused on the button but still reachable from three automatic paths (deferred-auth recovery, login-all worker, 30-minute idle keep-alive). All now refuse in preview and in any enforced scope; unscoped behaviour unchanged. |
| Audit finding | Runtime-fault evidence no longer attaches per-order proof to an out-of-scope order (program-level incident records are still written). |
| Snapshot format | `backup_running_release.ps1` wrote `PROGRAM-MANIFEST.sha256` with a BOM, which made a good snapshot unverifiable; it now writes without a BOM, refuses a missing/empty `_internal`, and refuses when a mandatory config is absent. |

### Bounded effect-path audit (one pass)

| Entrance | Verdict |
|---|---|
| Startup: `start_process_services`, `start()` | preview ⇒ no-op; scoped ⇒ needs notification+smtp (R2/R3) |
| Startup: `initialize_run_state` | **scoped now** (this round) |
| Poll: `discover_pending` | **scoped now**; `prepare_pending`/`process_pending` already filtered |
| Poll: `PurchaseCompletionActions.retry_saved_statuses/process` | scoped (R3) |
| Poll: notification dispatch | single choke point, needs notification+smtp (R2) |
| Poll: idle keep-alive login sweep | **refused in scope/preview** (this round) |
| Background: deferred-auth recovery sweep | **refused in scope/preview** (this round) |
| Manual: order mail / login-all / retry service / order actions / hint | gated (R2/R3) + hint aligned (this round) |
| Local DB: business state, events, alerts, snapshots | only inside the scoped loops; incident records remain program-level |
| External: Google / INSO / SMTP | one write lease + scoped INSO gate + write-intent ledger (R2/R3) |
| Installer / rollback | 8 gates before the first `Move-Item`, 13 offline negatives |

### NOT_VERIFIED

1. Nothing installed, stopped, started or restarted against production; no Google/INSO/SMTP effect; production SQLite not opened for write; Chrome 9222 untouched.
2. The installer's success path was never executed against a real install (production was running, so the last gate refused by design).
3. `sqlite3.exe` presence and `.backup` duration on this host.
4. Old-program Stop timing, GUI refresh stall, residual Chrome pages.
5. PyInstaller output is not bit-reproducible: `19918185…` identifies this build only.
6. The running `E9E3DA33…` EXE still has no proven source lineage.
7. A real scoped business run was not executed; scope behaviour rests on negative/integration tests.
8. The six flaky nodeids above are not explained to a root cause; they are recorded, not excused.

---

## RFQ-021-R3 — CHANGES_REQUESTED follow-up (2026-11-15 late morning)

- **Status:** `PASS_SOURCE_SCOPE / RELEASE_HOLD / NOT_DEPLOYED`
- **Reviewed base:** `1314da5d` → **source commit built:** `1ef20c81`
- **Candidate:** 8,459,010 B / `faa3166d41db5a738348dc57f6adebbfcda0b3dbf29eb99f3549cf0d0d2596c1`, 2,872 files
- **Manifest:** `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256` (`accd463a…`); r1 and r2 manifests kept as `-r1` / `-r2`. **One candidate only.**
- **Self-checks:** `--self-check` 0, `--idle-self-check` 0, `--preview-self-check` 0 (two rounds, 3 s, `ok: true`), `RELEASE_SCAN_OK` ×2
- **Manifest recomputation:** 2,872/2,872 matched, 0 missing / 0 mismatch / 0 unexpected, `VERIFY_RESULT = PASS`
- **Tests:** full suite **4,248 collected / 4,245 passed / 2 failed / 1 skipped in 661.77 s** (`pytest-report-r3.xml`).
  Failed nodeids (identical to the untouched parent baseline `e59ce62f`):
  `test_backend_closes_only_owned_browser_after_runtime_thread_exits[False]` and `[True]`.
  Captured cause: `V12Fault(WORKFLOW_LEDGER_UNAVAILABLE) <- sqlite3.OperationalError(attempt to write a readonly database)` on the pytest temp database. No test deleted, skipped or deselected.
- **New tests:** `tests/launcher/test_rfq021_r3_scope_effects.py` (11). One R2/R3 test was **rewritten** (same intent, new contract): explicit `inquiry_ids` conflicting with `RunScope` is now refused.
- **Fixed in this round:** background `retry_saved_statuses`/`process()` scoping; conflict rejection; login sweep refused in any enforced scope; per-action audit (`edit` and `purchase` need the google target; quotation/tp refused); installer fail-closed on rollback integrity + verified DB backup; manual corrected (source SHA, single candidate, removed the old-EXE `--safe-preview` assumption; cold rollback and post-rollback restart are separate approvals).
- **Incident verdict:** `FAULT_CLASS_CONFIRMED / UNDERLYING_CAUSE_NOT_VERIFIED`; 10:40 read-only re-collection recorded in `INCIDENT-20261115.md`.

---

## RFQ-021-R2 — CEO review follow-up (2026-11-15 morning)

- **Status:** `PASS_SOURCE_SCOPE / RELEASE_HOLD / NOT_DEPLOYED`
- **Source commit built:** `1314da5d` (base `8cded532` + three P0 fixes)
- **Candidate:** 8,457,679 B / `74586eb29ed19e037e2045f481d4ed2226aa555a8f6ef7951028c873fa68d0ed`, 2,872 files
- **Manifest:** `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256` (`74ae29c7…`); the r1 manifest is kept as `…-manifest-r1.sha256`
- **Self-checks:** `--self-check` 0, `--idle-self-check` 0, `--preview-self-check` 0 (two rounds, 4 s), `RELEASE_SCAN_OK`
- **Manifest recomputation:** `verify_release_candidate.ps1` → 2,872/2,872 matched, 0 missing / 0 mismatch / 0 unexpected, PASS
- **Tests:** full suite **4,237 collected / 4,234 passed / 2 failed / 1 skipped** in 424.76 s (`pytest-report-r2.xml`). The two failures are the same `test_backend_closes_only_owned_browser_after_runtime_thread_exits[False|True]` nodeids that fail on the untouched parent commit `e59ce62f`; captured cause is `V12Fault(WORKFLOW_LEDGER_UNAVAILABLE) <- OperationalError(attempt to write a readonly database)` in the pytest temp directory. Isolated reruns pass; no test was deleted or skipped.
- **New tests:** `tests/launcher/test_rfq021_p0_scope_binding.py` (15) plus one UI-refusal test in `test_rfq021_safe_preview.py`.
- **Capability reduction:** quotation / TP / notification and the `smtp` target are now refused by scope validation because none of them can prove per-order isolation. See `REVIEW_FOLLOWUP.md`.
- **Incident:** see `control-room/INCIDENT-20261115.md`. The running program was the old `E9E3DA33…` EXE; the morning stop was `SHEETS_READ_UNAVAILABLE` caused by `SSLEOFError`, not a crash and not these code paths.

---

## RFQ-021-R1 — first delivery (superseded)

- **Status:** `READY_FOR_CEO_RELEASE_REVIEW` (superseded by R2)
- **Window:** 2026-11-15 02:00–03:05 Shanghai
- **Worktree:** `D:\Program_Leo\INSO_Leo\.worktrees\v16-rfq016-stabilization` (reused; no second worktree)
- **Branch:** `workbuddy/v16-rfq016-stabilization`
- **Source base:** `25894eface6ea622153d1573c19d0ca6b9ad72aa` (RFQ-018 PASS) + RFQ-021 changes
- **Source commit built:** `8cded532221571e99697af7668634afab3ea07af`

## 1. Takeover audit (read-only)

- Read `AI_START_HERE.md`, `AGENTS.md`, `control-room/CEO_HANDOVER.md`, `control-room/COORDINATION.md`, `RFQ-020/REVIEW.md`, `RFQ-019/{REVIEW,RELEASE_READINESS,RISK_REGISTER,RELEASE_PREP_REPORT}.md`.
- **Correction to the RFQ-020 record (CEO review item 2):** `docs/BRANCH_POLICY.md` is absent **on this branch** but present on `develop`; `control-room/RFQ-019/REVIEW.md` does exist — the CEO added it in `64dba150`. RFQ-020's log and JSON are corrected in this commit.
- **Correction to the RFQ-020 record (CEO review item 1):** the "23:00" later-observation timestamp was written from memory and post-dated its own commit. Corrected to the actual read time (~22:47, before `6f1b1d25`); no unauthorized action is implied by the original text.
- `git status --porcelain` clean at takeover; `25894efa` is an ancestor of the branch; no stash; only the pre-existing worktrees.
- Production snapshot at takeover: `INSO_V1.6.exe` SHA256 `E9E3DA33…`, PIDs 38948 + 34304 alive since 13:47, SQLite `dist/INSO_V1.2/runtime/production/workflow.sqlite3` 1,196,032 B mtime `1794679195`, Chrome 9222 reachable, 15 pages.

## 2. What was wrong, and the smallest fix that closes it

### B7 — normal GUI start is not a "view"

`src/gui/main.py` called `backend.start_process_services()` unconditionally, which runs `migrate_v12` / `V13HoldStore.migrate` / `MailResearchStore.migrate` / `recover_abandoned_notification_attempts` and starts the IMAP receive + SMTP outbox worker.

Fix (no new architecture):

- `ProductionBackend(preview_mode=True)` refuses `start()` and returns immediately from `start_process_services()` (defence in depth, even if a caller tries).
- `main()` now treats a plain launch as a **preview**: no process services, no Start, Start button disabled with 「安全预览（不启动业务）」, and a separate `--preview-mutex` (`Local\INSO_V1.2-preview`) so a preview can coexist with the running business instance without fighting over the single-instance lock.
- `--scoped-start` is the only path to business. `--start-inquiry` without it is **refused with a dialog (exit 2)**, never silently downgraded.
- `--preview-self-check` opens and closes the real dashboard twice and records the result.

### B5 — "inquiry_ids" was not a scope

`inquiry_ids` limited row intake only; quotation/TP/notification and every write stayed live.

Fix:

- New `src/launcher/run_scope.py`: `RunScope(inquiry_ids, modules, write_targets, approval_reference)` with validation — non-empty order ids matching `inq_[a-f0-9]{24,32}`, modules ⊆ {inquiry, quotation, tp, notification} and **must include `inquiry`** (it is the poll driver), write targets ⊆ {google, inso, smtp}, and **any write target requires `OWNER-APPROVED:<reference>`**.
- `ExternalWritePolicy` is the one object every adapter asks. Enforced with no scope ⇒ deny everything. `block_all_writes()` is sticky.
- Google writes: the policy is checked inside `PageResourceAdmission.begin_document_write` — the single lease every writer already takes (Sheets API `google_api_service.py:370`, browser fallback `google_web.py:557`, native quote click `google_quote_update.py:1085`). A refusal raises `DocumentWriteBlocked`, a `DocumentWriteHeld` subclass, so existing callers keep their "do not dispatch, do not retry" behaviour.
- INSO writes: `ScopedInsoWriteGate` wraps the **existing** `OwnerAuthorizedSaveAndSendGate`. It only adds a refusal in front; `SAVE_DATA` stays closed exactly as before. `test_scoped_inso_gate_never_reopens_the_production_save_gate` pins that.
- Modules: `_module_allowed()` gates `_v13_enabled` (quotation), the TP cycle, and notification dispatch. `_run_notifications()` is now the single dispatch choke point and stays silent unless **notification module and `smtp` target** are both in scope. All seven previous `coordinator.run_notifications(...)` call sites go through it.

### B6 — the hold died with the process

`PageResourceAdmission` kept document holds in memory only; a restart forgot that a request might be in flight.

Fix:

- New `src/workflow/write_intents.py`: `workflow_write_intents` table (additive, same DB) with `PENDING / UNKNOWN / SETTLED`. `begin()` commits **before** the caller can dispatch; `settle()` only on evidence; `mark_unknown()` keeps it open.
- `PageResourceAdmission` takes an optional journal. `begin_document_write` asserts the scope, then checks `open_reason(document)`, then commits the intent, all before the caller touches the network. A document with an open intent raises `WRITE_INTENT_PENDING`; an unreadable/unwritable ledger raises `WRITE_LEDGER_UNAVAILABLE` — both block the write.
- `hold_document()` marks its own intent UNKNOWN and **pops** it, so a later `end_document_write` cannot settle what just became uncertain.
- `end_document_write` settles only when the document carries no hold; settlement failure is swallowed on purpose (the row stays open, which is the fail-closed state).
- `_attach_write_journal` runs **after** `V12Store(db)` and refuses a DB file that does not exist yet — the first attempt created an empty file before migration and every poll failed with `V12SchemaMismatch`; that regression was caught by the suite and fixed.

## 3. Files changed

| File | Change |
|---|---|
| `src/launcher/run_scope.py` (new) | scope validation, external write policy, INSO gate narrowing |
| `src/workflow/write_intents.py` (new) | durable write-intent journal |
| `src/research/cdp_pages.py` | policy + journal in the single write lease; `DocumentWriteBlocked` |
| `src/launcher/backend.py` | preview mode, scope enforcement, module gating, notification choke point, journal attach, INSO gate |
| `src/gui/main.py` | plain launch = preview; `--safe-preview` / `--scoped-start` / `--scope-*` |
| `src/gui/app.py` | disabled Start with a clear label when previewing or unscoped |
| `src/launcher/single_instance.py` | optional mutex name + preview mutex |
| `scripts/windows_release_entry.py` | `--preview-self-check` (two real GUI rounds) |
| `scripts/verify_release_candidate.ps1` (new) | recompute every manifest hash |
| `scripts/backup_running_release.ps1` (new) | program+config snapshot, junction-aware, DB recorded not copied |
| `scripts/install_release_candidate.ps1` (new) | guarded switch, never starts anything |
| `tests/launcher/test_rfq021_run_scope.py` (new) | 20 negatives |
| `tests/research/test_rfq021_write_intents.py` (new) | 9 negatives |
| `tests/gui/test_rfq021_safe_preview.py` (new) | 6 launch/button negatives |
| `tests/gui/test_startup.py` | existing start contract updated to require a scope |

## 4. Test evidence

- New negative suites: 35 tests, all pass. They cover: scope validation refusals; policy denial before any intent; scope refusal happening before a journal row; INSO scope narrowing; a crashed write blocking the next process; an unconfirmed hold not being settled by lease release; an unreadable ledger failing closed; preview launch never starting process services; `--start-inquiry` without a scope refused; button state.
- Existing `test_startup.py` was updated (not skipped): an explicit Start now needs `--scoped-start` + a scope. Its original intent is preserved.
- **Affected modules together** (`tests/launcher research sheets inso gui`): **2886 passed, 0 failed, 161.60 s**.

**Full suite, final run** (`pytest tests -q --tb=no`, JUnit in `docs/evidence/rfq021/pytest-report.xml`):

| Metric | Value |
|---|---|
| Collected | 4,223 |
| Passed | 4,220 |
| Failed | **2** |
| Skipped | 1 |
| Duration | 382.18 s |

Both failures are the same test:
`tests/launcher/test_release_infrastructure.py::test_backend_closes_only_owned_browser_after_runtime_thread_exits[False]` and `[True]` — the worker ends in `MODULE_PAUSED` instead of `STOPPED` after `request_stop_after_cycle()`.

**Control run on the unmodified parent commit** (`e59ce62f`, extracted with `git archive`, same interpreter, same command): **2 failed / 4 errors / 4,181 passed / 1 skipped in 388.23 s** — and the two failures are *exactly the same two nodeids*. The 4 extra errors (`tests/workflow/test_follow_up_rollback.py`) appear only in the extracted tree (it has no git or local runtime context) and are not present in the worktree run.

So the failure set **did not change** relative to the baseline; this is the known load-sensitive pair, not a regression from RFQ-021. The same two tests pass individually (repeated 6×) and pass as part of the 2,886-test module run.

Two transparency notes:

- An earlier full run under the sandbox produced 4 failures, all with `sqlite3.OperationalError: attempt to write a readonly database`; those tests pass when the run is allowed to write its temp directory, and the baseline shows the same class of instability. No test was deleted, skipped or deselected to improve the number.
- One intermediate full run was stopped by the operator after 16 minutes at ~20 % (it hung while showing clustered failures); it is not used as evidence.


## 5. Candidate build

- Environment: reused `.venv-release` (Python 3.12.10 / Tk 8.6.15 / PyInstaller 6.16.0); lock file unchanged (`3dc5d7a5…`).
- Command: `scripts/build_windows_release.ps1 -BuildOnly -Version 1.6`, exit 0, script-internal `--self-check` and `RELEASE_SCAN_OK` both passed.
- Output: `build/windows-release-stage-1.6/dist/INSO_V1.6/` — staging only; `dist/INSO_V1.6` untouched.

| Item | Value |
|---|---|
| Source commit | `8cded532221571e99697af7668634afab3ea07af` |
| EXE | 8,455,788 B, SHA256 `63bcd6cea66003f84ce016cfa8742dc479a9d67ce3f579a92b5b7c398bf4465b` |
| Files | 2,872 (EXE + 2,871 under `_internal`) |
| `runtime/` in artifact | absent |
| Manifest | `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256`, 2,872 lines, digest `d5cc3d4cc41fff16bf0316e0799305b31269201a5728bb7a207b8220d6a2aa7a` |

Build input hashes: build script `ab35565a…`, lock `3dc5d7a5…`, spec `d7574c20…`, icon `8f0e07dc…`, scanner `f2517340…`, entry `ae4eafa5…`.

**RFQ-020's `b358f687…` is not used as evidence for this source.** It was produced from `25894efa` and has been replaced in staging by this build.

## 6. Self-checks on the candidate

| Check | Result |
|---|---|
| `--self-check` | exit 0 |
| `--idle-self-check` | exit 0, state 已停止, no business/order thread |
| `--preview-self-check` (new) | exit 0, 3 s, **2 rounds**, both `blockers=["PREVIEW_ONLY"]`, Start disabled, `business_thread_started=false`, `mail_service_started=false`, `process_services_consumed=false` |
| `scan_release_artifact.py` | `RELEASE_SCAN_OK` (script-internal and standalone) |
| `verify_release_candidate.ps1` | 2,872/2,872 matched, `missing=0`, `hash_mismatch=0`, `unexpected=0`, `VERIFY_RESULT=PASS` |

Reports: `docs/evidence/rfq021/v16-preview-self-check.json`, `docs/evidence/rfq021/v13-idle-self-check.json`.

The self-check byproducts (`runtime/logs/*.json`) were removed from the staging artifact after their content was copied into evidence, so the manifest describes the build output exactly (2,872 files).

## 7. Production invariance

| Item | Before | After |
|---|---|---|
| Production EXE | `E9E3DA33…` | `E9E3DA33…` |
| Processes | PID 38948 + 34304 | same PIDs, never stopped |
| Production SQLite | 1,196,032 B, actively written by the running program | **not opened, not copied, not modified by this RFQ** |
| Chrome 9222 | reachable, 15 pages | never attached; page count changed by the running program itself |

The database size and mtime move on their own while the old program runs; this RFQ only ever read file metadata there.

## 8. Switch materials (prepared, not executed)

`control-room/RFQ-021/INSTALL_AND_ROLLBACK.md` covers: offline verification, program+config snapshot, bounded stop with abort conditions, post-stop consistent DB backup, guarded install, first launch as safe preview, business enablement conditions, rollback that never overwrites newer business data, and the failure states (`WRITE_INTENT_PENDING`, `WRITE_LEDGER_UNAVAILABLE`, `EXTERNAL_WRITE_NOT_IN_SCOPE`).

## 9. NOT_VERIFIED

1. Nothing was installed, stopped, or started against the production directory in this RFQ.
2. The candidate was never launched as the real product beyond the three self-check modes.
3. `sqlite3.exe` availability and `.backup` duration on this host are unverified (documented as a manual step).
4. Old-program Stop timing, GUI refresh stall and residual Chrome pages remain unmeasured.
5. PyInstaller output is not bit-reproducible: `63bcd6ce…` identifies this build only.
6. The running `E9E3DA33…` EXE still has no proven source lineage.
7. Business UNKNOWN state (221 / SHAHAB-115 / 3 V13 holds) untouched and unresolved.
8. A real scoped business run (even read-only) was not executed; scope behaviour is verified by unit/negative tests, not by a live run.
