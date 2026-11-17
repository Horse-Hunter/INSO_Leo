# RFQ-022 — 执行记录（CEO 可复算部分）

需求见 [TASK_SPEC.md](TASK_SPEC.md)。完整时间线、逐条日志与命令输出在
[RFQ-021/EXECUTION_LOG.md 首节](../RFQ-021/EXECUTION_LOG.md)；本文件只列**能在 git 里复算**的内容，以及现场声明与不可复算部分的边界。

## 1. 提交

| 提交 | 内容 |
|---|---|
| `aaac8c75` | 修复：TLS 断链回归瞬时读 + 故障诊断投影 + 「异常与通知」改造 + 18 项定向测试 |
| `f4190cf8` | 记录：安装闸门结果与现场状态 |
| `849ed5d7` | 记录：982/983 真实业务结果 |
| `95669170` | 记录：CEO 同步报告与交接入口 |

分支：`workbuddy/v16-rfq016-stabilization`（接管时本地落后远端 3 个文档提交，已快进到 `cda61456`）。

## 2. CEO 可复算项

```bash
# 改动清单与规模
git show --stat aaac8c75

# 分类器边界（本轮最需要判断的一处）
git show aaac8c75 -- src/sheets/google_reader.py src/workflow/v13_integration.py src/launcher/backend.py

# 新增测试及其断言
git show aaac8c75 -- tests

# 候选文件清单（2,872 行）与自身哈希
git show aaac8c75:docs/evidence/rfq021/INSO_V1.6-artifact-manifest-rfq022.sha256 | wc -l
git show aaac8c75:docs/evidence/rfq021/INSO_V1.6-artifact-manifest-rfq022.sha256 | sha256sum
# 期望：2872 行 / 08b0e9f618ba9c504f573b918c67ce2a18c74f32817790fca153cec69c138684
```

候选 EXE 记录值：`f2ffa44f7f31d373ac010116a0bbcb240297341948fb86b567c7e7bd94b3728c`，
8,476,327 B，2,872 文件，无 `runtime/`。**PyInstaller 输出不是逐字节可复现**，该哈希只标识这一次构建；文件集合的证明是上面的清单，不是哈希。

测试与静态检查（当时在同一工作树执行）：

```bash
python -m pytest tests/gui -q                      # 123 passed
python -m pytest tests/launcher tests/gui -q       # 1843 passed / 1 failed（见下）
python -m pytest tests/workflow/test_source_order_date.py -q   # 22 passed
python -m ruff check src tests                     # All checks passed
git diff --check                                   # 无输出
```

唯一失败：`tests/launcher/test_backend.py::test_empty_poll_defers_browser_bootstrap_until_an_inquiry_is_due[False]`，
捕获原因为"测试临时库只读"，**单跑 2/2 通过**，与 RFQ-021 R3/R4 记录的同类偶发一致，本轮的 15 个文件改动均不涉及该用例路径。未删除、未跳过任何用例。

## 3. 安装闸门（记录值，非 git 可复算）

| 闸门 | 结果 |
|---|---|
| `backup_running_release.ps1` | `BACKUP_RESULT = PASS`（2,871 internal + EXE + runtime 指向的配置），快照 `dist/release-backups/RFQ-022-pre-switch-20261117T112320Z` |
| 库副本 | `workflow.sqlite3`，SHA256 `76bfdfd0c3af5b249e7ead53ec7ba8772acf97488cf68e5ab544291e05e9eaef`，与生产库逐字节一致 |
| `verify_database_backup.ps1` | `DB_VERIFY_RESULT = PASS`；`process_state = stopped (proven)`；`write_intent_state = NONE_PROVEN`；`purchase_rows = 37` |
| `install_release_candidate.ps1` | `VERIFY_RESULT = PASS`（0 missing / 0 mismatch / 0 unexpected）→ `INSTALL_RESULT = PASS`，`installed_files_verified = 2872` |
| 旧版保留 | `INSO_V1.6.exe.prev-20261117T112542Z` + `_internal.prev-20261117T112542Z` |

停机方式：终止旧 PID 42876 / 41784（该版本已知缺陷：关窗后进程不退），因此本次运行没有 `exit.json`，下次启动记为 `previous_abnormal_exit`。

## 4. 现场声明（git 无法验证，如需独立核实请在现场执行）

在 2026-11-17 19:26–19:37（+08）于 Owner 机器上观测到：

- 新版进程 PID 62628（界面）+ 59704（watcher），`gui_ready`，`fatal.log` 0 字节；
- `inq_895ed99a1ec48c7d95735db8`（2026 行 982）与 `inq_f39d38e94aa183a6d6676a16`（行 983）均
  `PURCHASE_DATA_SAVED`、purchase `SAVED`、源表 `未发 → 发给采购`；
- `workflow_write_intents` 全部 `SETTLED`；`workflow_v12_active_alerts` 中 `active=1` 为 0 行。

现场复算命令（只读，勿在业务运行时重复执行）：

```powershell
Get-FileHash 'D:\Program_Leo\INSO_Leo\dist\INSO_V1.6\INSO_V1.6.exe' -Algorithm SHA256
```

```python
# 只读打开，勿写
import sqlite3
c = sqlite3.connect('file:dist/INSO_V1.2/runtime/production/workflow.sqlite3?mode=ro', uri=True)
print(c.execute("select inquiry_id,business_state from workflow_v12_inquiry_state"
                " where inquiry_id in ('inq_895ed99a1ec48c7d95735db8',"
                " 'inq_f39d38e94aa183a6d6676a16')").fetchall())
print(c.execute("select count(*) from workflow_v12_active_alerts where active=1").fetchone())
print(c.execute("select state,count(*) from workflow_write_intents group by 1").fetchall())
```

## 5. 未做（明确边界）

- 未修改 `2026`/`SHAHAB` 任何单元格（仅程序自身按业务写入状态列与品牌列）。
- 未填 `RFQ_BRIEF.target_price`，因此 TP 未对这两笔建任务（见 TASK_SPEC 第 8 节）。
- 未处理 3 条遗留 hold；未执行冷回滚；未合并 `develop`、未晋升 `main`。
- 未对"重启后纯读阶段残留转人工"的规则做任何放宽。

---

# CEO 收尾补修（2026-11-17 23:0x，回应 REVIEW.md 的 P1-A / P1-B / P2）

**状态：`UI_DIAGNOSTICS_CLOSED / TESTS_GREEN / CANDIDATE_REBUILT / NOT_INSTALLED`（生产仍是已运行的上一版，未动）。**

## 6. 三个缺口怎么闭的

### P1-A：读失败被推迟时，GUI 也要看到真实原因

- `_defer_website_poll` 原先只在"要发通知/告警"时才留痕，`notify=False, recoverable_read=True` 这条**最常见的路径什么都不记**。现在同一条入口无论发不发邮件都记录一份脱敏诊断：故障码、首次/最近时间、次数、异常类、**下一轮预计**、外部写入、建议操作；不发邮件、不告警、不停模块、不产生订单错误。
- `FaultDiagnostic` 新增 `next_retry_at`；`build_diagnostic(deferred=True)` 让"被推迟"与"被停止"在措辞上分开：推迟写"本轮只推迟了这一步，没有停止任何模块"，绝不写"已停止三个模块"。
- 页面新增 **`业务影响：`** 行（此前 `impact` 只算不显示），这就是 CEO 要求的"不要误报为整站中断"的可见保证。
- 恢复时 `_site_recovered` 清掉该故障并把 `next_retry_at` 归零，页面转为【已恢复】。

### P1-B：恢复要落库，重启不能复活旧故障

- `_resolve_faults` 之前只改内存。现在解析完成后调用既有 `V12Store.resolve_incidents(module, at, diagnostic_code=...)`，把**同一条 incident** 的 `active/recovered_at` 写回库；`resolve_incidents` 只新增一个 `diagnostic_code` 过滤参数，未新建表、未建第二套状态。
- 只动 `command_id LIKE 'incident:%'` 的行；`workflow_v12_active_alerts`（订单告警）、`workflow_v13_holds`、`UNKNOWN/SENT`、写意图账本一律不碰（有专门断言）。
- 覆盖 CEO 点名的两种情形：`_site_recovered(site)`（站点恢复）与 `_resolve_faults_after_success(module)`（**仅 inquiry/TP 恢复、quotation 仍关闭**）都会持久化 `business_runtime` 的解决状态。

### P2：单笔异常不再给泛化文案

- 新增 `order_exception_block()` + 22 条原因目录：每笔给 **原因 / 建议 / 位置（工作表+行号+任务号）**，末尾统一"本页不会重新发送或提交"。
- 未分类代码直写"该代码没有已确认的中文说明，原因尚未确认"，不给猜测；没有告警的订单不下"原因"结论。
- 全局故障原因**不会**被投射成某笔订单"写入失败"：单笔段只读该单自己的 `reason_code`。

### 顺带修掉一个会误导读者的真 bug

`_external_effect_state()` 之前 import 了不存在的 `WriteLedger`，于是**每一次共享停止都会显示"写入台账不可读，外部写入结果尚未确认"**——即使账本干净。改为 `SqliteWriteIntentJournal`，并加两条回归：账本干净时显示"没有未结清的外部写入意图"，账本缺失时才显示"不可读"。

## 7. 负向证据（先失败，后通过）

在**未修复**源码上跑本轮新增用例：

```
git stash push -- src/         # 只回退源码，保留新测试
pytest tests/launcher/test_fault_diagnostics.py -q -k "reaches_the_gui or counts_up_and_clears or durable_incident or leaves_order_alerts or next_step or unconfirmed or invented_cause"
→ 7 failed, 1 passed
git stash pop
```

修复后同一批：`24 passed`（`tests/launcher/test_fault_diagnostics.py` 全文件），其中 `test_the_page_block_separates_a_deferral_from_a_shared_stop`、`test_the_write_ledger_statement_is_proven_not_guessed` 是新增的反证。

## 8. Owner 会看到的实际字段（合成故障，非生产故障）

完整样本见 [`docs/evidence/rfq022/ui-sample.txt`](../../docs/evidence/rfq022/ui-sample.txt)，四段分别为：推迟中、推迟后恢复、共享停止、停止后恢复，每段附"重启后的库内活动故障"。

推迟（无邮件/无告警/不停止）：

```
【故障】Google 表格等待恢复
故障代码：GOOGLE_WAITING_RECOVERY
发生时间：… （首次 … · 最近 … · 共 1 次）
影响模块：Google Sheets
业务影响：本轮只推迟了这一步，没有停止任何模块；其他任务照常运行。
具体原因：表格读取失败，程序等待下一轮自动重试。（异常类型 SSLEOFError）
恢复过程：已自动推迟到下一轮，业务未停止；本次不发邮件提醒
下一轮预计：…
外部写入：本次仅记录读取/连接重试，未新增外部写入意图
建议操作：若持续失败，检查网络/VPN 与表格访问权限。
诊断位置：runtime/logs/INSO_V1.3.log
重启后的库内活动故障：()          ← 推迟不制造持久故障
```

共享停止 → 重启视图 `('SHEETS_READ_UNAVAILABLE',)`；真实恢复后 → 重启视图 `()`（页面显示【已恢复】）。这是 P1-B 的核心证据。

## 9. 全量回归与机器可读结果

源码冻结后一次全量（本工作树，`pytest tests`）：

```
tests 4309 · failures 0 · errors 0 · skipped 1 · 596.6s
```

- junit：`docs/evidence/rfq022/pytest-full.xml`（唯一 skip 是 `test_existing_path_rejects_symlink_escape_when_supported`，原因 `symlink creation not available in this test environment`，平台条件跳过）。
- `ruff check src tests` → `All checks passed!`；`git diff --check` 干净。
- 另一次全量（同一冻结源码的前一版，仅多一个重复定义的测试）同样 0 失败。

**关于上一轮合跑的那 1 项失败**（`test_empty_poll_defers_browser_bootstrap_until_an_inquiry_is_due[False]`，`OperationalError: attempt to write a readonly database`）：

- 该项在**本轮两次全量、以及隔离单跑 6/6 全部通过**，无法复现；
- 失败形态是 SQLite **写**被拒（`SQLITE_READONLY`），而 `tmp_path` 下只有预存的 V1/V12 账本写入；本轮 diff 在该路径**没有新增写**（新增的 V12 读取被 `except Exception` 包住，失败也只会退化为空列表）；
- 同一轮测试里反复出现 `[SAFE_DELETE_FAIL_CLOSED] … trash-failed … 找不到网络路径`，即宿主临时目录被外部进程/过滤器干扰的痕迹；
- 结论：**指向宿主临时目录写入被拒，不是源码**；但我没有复刻到那一刻的 ACL 状态，因此把它记为"未复现、有机制证据的环境类偶发"，不写成"已排除"。若再次出现，请在失败瞬间保留 `%TEMP%\pytest-of-*` 的权限快照。

## 10. 新候选（旧 `f2ffa44f…` 仅作已安装历史）

源码冻结后重建，**未安装**（生产仍在跑已安装的上一版，未停机、未覆盖）：

| 项 | 值 |
|---|---|
| EXE SHA256 | `119163b545aa9b9b2a935738fa0ac96ea12e0d2cdb4e2a7d0ca5872002161cb0` |
| EXE 大小 | 8,480,578 B |
| 文件数 | 2,872（无 `runtime/`） |
| 清单 | `docs/evidence/rfq022/INSO_V1.6-artifact-manifest-rfq022b.sha256`，自身 SHA256 `bd81bdd4aafda0fbf8851b78ba76c1653418af10a9cb7e2c27443ba1730ccc82`，2,872 行 |
| `--preview-self-check` | `ok: true` |
| `--idle-self-check` | `gui_rendered: true`，无业务线程，`start_action = 开始运行` |
| 构建扫描 | `RELEASE_SCAN_OK` |

旧的 `f2ffa44f…` 只能证明「已安装的那一版」，不能再用来代表 P1-A/P1-B/P2 的功能；安装需按现有发布闸门另起维护窗口。

## 11. 未做（延续 CEO 指令）

- 未再次处理 982/983（两笔均 `SAVED`，重发有重复采购风险）；未停止/覆盖运行中的生产程序；未清任何 `UNKNOWN/hold`；未改 TP 取价规则；未动 `main`/`release`／未合并 `develop`。
- 真实故障态的现场界面证据仍缺（本轮用同一 backend 的合成故障跑通 backend → snapshot → Tk；不制造生产故障）。

