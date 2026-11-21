# RFQ-021-R3 — 定点补修与独立复核记录

**状态：`PASS_SOURCE_SCOPE`（R3 指出的 P0-A / P0-C 已修）／`RELEASE_HOLD`（B3、B4 未满足）／`NOT_DEPLOYED`。**

这是执行方对本轮改动的**独立记录**，与 CEO 的 Review 分开：只陈述源码、测试、候选与证据，不复述结论。

## 1. 基线与被审对象

| 项目 | 值 |
|---|---|
| 被审基线（CEO 指定） | `1314da5d`（R2 修复） |
| 本轮修复提交 | `1ef20c81` |
| 分支 / 工作树 | `workbuddy/v16-rfq016-stabilization` / `.worktrees/v16-rfq016-stabilization`（复用，未新建） |
| 工作树状态 | 干净；无 stash；仅此一个执行工作树 |

## 2. R3 第 1 条：P0-A 背景效果

**发现（属实，且范围比反馈更宽）**：`PurchaseCompletionActions.retry_saved_statuses` 遍历 `workflow_store.all_items()`，对每个 `SAVED` 订单调用 `_write_back` → Google 状态写入 + 本地业务状态变更。范围只约束了 `compose_v12_production`，没有约束这条后台路径。

**修复**：

1. `PurchaseCompletionActions` 接受 `inquiry_ids`，`retry_saved_statuses` 与 `process()` 都按范围过滤；`process()` 对范围外结果直接返回（不写、不发、不改状态）。
2. 后端构造时传入 `self._inquiry_scope`。
3. 显式 `inquiry_ids` 与 `RunScope` 不一致时直接拒绝（`SCOPE_INQUIRY_IDS_CONFLICT`），不再"以谁为准"含糊处理。

**审计的其余自动/后台路径**：

| 路径 | 是否受范围约束 | 依据 |
|---|---|---|
| `retry_saved_statuses`（两处循环 + market-actor 分支共用同一实例） | 是（本轮修复） | 同一 `PurchaseCompletionActions` 实例 |
| `compose_v12_production` 的采购/调研 | 是（R2） | `inquiry_ids=` |
| 报价 / TP 周期 | 是（R2，直接拒绝模块） | `SCOPE_MODULE_NOT_ISOLATABLE` |
| 通知派发（SMTP） | 是（R2） | `_run_notifications` 单一收口 |
| 品牌自动更新（coordinator 内） | 是 | 仅在已限定范围的行上触发 |
| `_refresh_history` / 仪表盘计数 | 只读 | 无外部写入 |
| 手动动作（edit/purchase/quotation/tp） | 是（本轮补审计） | `_action_in_scope` |

**负向/集成测试**（`tests/launcher/test_rfq021_r3_scope_effects.py`）：

- `test_saved_order_outside_the_scope_never_reaches_a_google_write`：两个 SAVED（一个在范围、一个不在），只有范围内那个产生写入；
- `test_unscoped_run_keeps_reconciling_every_saved_order`：对照组，未启用范围时两个都写（证明过滤没有误伤）；
- `test_background_status_reconciliation_is_blocked_even_when_google_is_allowed`：**google 是已授权目标**时，范围外订单仍不写入；
- `test_a_completion_result_from_another_order_is_ignored`；
- `test_conflicting_explicit_ids_and_scope_are_refused` / `test_matching_explicit_ids_and_scope_are_accepted`；
- `test_the_backend_hands_the_scope_to_the_completion_actions`：真实 `_run` 后检查 `_purchase_completion._inquiry_ids`。

## 3. R3 第 2 条：P0-C 登录巡检与手动动作

**发现（属实）**：R2 把 `start_login_all_sites` 挂在 `_external_action_allowed("google", …)` 上——当 `google` 是允许目标时它会被放行，而登录巡检没有任何订单过滤。

**修复**：

1. `start_login_all_sites` 在 `preview` **或** `enforce_scope` 一律拒绝，与写入许可无关。
2. 新增 `_action_in_scope(action)`：按动作所需模块与**每一个**外部写入族判断。
   - 审计中发现补丁不完整：`edit` 会写 Google 单元格、`purchase` 重跑最终会写状态，因此两者都需要 `google`；
   - `quotation` / `tp` 因模块无法按订单隔离，永远拒绝；
   - `resync` 只读+本地台账，允许。
3. `can_order_action` / `request_order_action` 使用该审计；后者给出明确拒绝理由。

**测试**：`test_login_sweep_is_refused_in_a_scoped_run_even_with_google_allowed`、`test_login_sweep_is_refused_in_preview`、`test_manual_action_audit_follows_modules_and_write_targets`（覆盖只读 / 仅 google / google+inso 三种范围）、`test_manual_purchase_request_is_refused_without_the_inso_target`。这些直接调用真实方法，不依赖按钮状态。

## 4. R3 第 3 条：文档与证据一致性

| 问题 | 处理 |
|---|---|
| 手册源码 SHA 仍是 `8cded532` | 已改为 `1ef20c81`，候选哈希/字节数/清单同步更新 |
| R1 JSON 过期仍作"当前证据" | 改名为 `rfq021-final-candidate-r1.json`，本轮证据为 `rfq021-review-followup.json`（R3 内容），手册只引一个候选 |
| R2 通过数写错（4235） | 算术修正为 4234（4237 − 2 失败 − 1 跳过）；R3 记录为 4245（4248 − 2 − 1） |
| 旧候选清单 | r1/r2 清单分别归档为 `-r1` / `-r2`，`INSO_V1.6-artifact-manifest.sha256` 只对应当前候选 |

## 5. R3 第 4 条：安装脚本失败关闭

`scripts/install_release_candidate.ps1` 现在要求：

1. `-ConfirmSwitch`（维护窗口授权）；
2. `-RollbackDir` 里的 `PROGRAM-MANIFEST.sha256` **逐文件重算一致**（≥2 项）；
3. `-DatabaseBackup` 存在、>4 KB、文件头为 `SQLite format 3`，且必须显式 `-ConfirmDatabaseBackupVerified`（操作者声明已跑 `quick_check`）；
4. 候选本身按清单复算 PASS；
5. 目标目录的 `runtime` 仍是 junction。

任一项缺失即在改动文件之前抛错。**已移除**"回滚后用旧 EXE 跑 `--safe-preview`"的假设：旧 EXE 没有该参数，回滚只做哈希核对；冷回滚与"回滚后业务重启"在手册里是两个独立审批步骤。

## 6. 候选与自检

| 项目 | 值 |
|---|---|
| 源码 | `1ef20c81` |
| EXE | 8,459,010 B / `faa3166d41db5a738348dc57f6adebbfcda0b3dbf29eb99f3549cf0d0d2596c1` |
| 文件数 | 2,872（无 `runtime/`、无配置、无数据库、无密钥） |
| 清单 | `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256`（`accd463a78c23d5739d298a0ea6d2735ab1f51af051aad13900697ca406455ae`） |
| 逐文件复算 | 2,872/2,872，0 缺失 / 0 不一致 / 0 多余，`VERIFY_RESULT = PASS` |
| `--self-check` | 0 |
| `--idle-self-check` | 0 |
| `--preview-self-check` | 0（两轮，3 s，`ok: true`） |
| 产物扫描 | `RELEASE_SCAN_OK`（构建脚本内两次） |

报告：`docs/evidence/rfq021/v16-preview-self-check-r3.json`、`v13-idle-self-check-r3.json`。

## 7. 测试结果

- 新增：`tests/launcher/test_rfq021_r3_scope_effects.py`（11 项）。
- 修改（不是删除）：`test_explicit_inquiry_ids_still_win_over_the_scope` → `test_explicit_inquiry_ids_conflicting_with_the_scope_are_refused`，因为冲突现在应当被拒绝。
- 完整套件：**4,248 collected / 4,245 passed / 2 failed / 1 skipped / 661.77 s**（`pytest-report-r3.xml`）。
- 失败 nodeid（与基线完全相同）：
  - `tests/launcher/test_release_infrastructure.py::test_backend_closes_only_owned_browser_after_runtime_thread_exits[False]`
  - `tests/launcher/test_release_infrastructure.py::test_backend_closes_only_owned_browser_after_runtime_thread_exits[True]`
- 失败原因（离线插件捕获）：`V12Fault(WORKFLOW_LEDGER_UNAVAILABLE) <- sqlite3.OperationalError: attempt to write a readonly database`，发生在测试临时目录的写事务上；未修改的父提交 `e59ce62f` 在同一环境出现同样两项。未删除、未跳过、未 deselect。

## 8. NOT_VERIFIED

1. 未安装、未停机、未重启旧程序；候选只在 staging 自检。
2. 未做任何真实受控业务运行；范围行为全部由测试证明。
3. 报价 / TP / 通知的订单级隔离**不存在**，本轮只是拒绝它们。
4. `sqlite3.exe` 与 `.backup` 在本机的可用性未验证。
5. PyInstaller 输出不可位级复现；哈希只标识本次构建。
6. 旧运行 EXE `e9e3da33…` 的源码血缘仍未证明。
7. 早间事件的底层原因（为何那一刻 TLS 断）仍未确认，见 `INCIDENT-20261115.md`。
