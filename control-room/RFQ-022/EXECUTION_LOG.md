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
