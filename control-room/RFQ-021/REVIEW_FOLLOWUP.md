# RFQ-021 — CEO Review 定点补修（REVIEW_FOLLOWUP）

**结论：`PASS_SOURCE_SCOPE`（三个 P0 已修复并有负向与集成测试）／`RELEASE_HOLD`（B3、B4 仍需维护窗口）／`NOT_DEPLOYED`。**

基线：`8cded532221571e99697af7668634afab3ea07af`（RFQ-021 首轮）。本轮修复提交：`1314da5d`。

## 1. CEO 指出的三个 P0：是否属实

**全部属实，且比描述的更严重一点。**

### P0-A — 范围没有传到业务编排

- 事实：`src/gui/main.py` 用 `ProductionBackend(run_scope=scope, ...)` 构造，但 `_inquiry_scope` 只从 `inquiry_ids` 参数赋值。两条赋值路径互不相通，于是 `compose_v12_production(inquiry_ids=None)` —— **"受控试运行"实际会处理全部订单**。
- 修复：
  1. 构造器在 `inquiry_ids` 缺省时从 `run_scope.inquiry_ids` 绑定；显式 `inquiry_ids` 仍然优先。
  2. 逐个核对模块是否真的能按订单隔离：`inquiry` 通过 `compose_v12_production(inquiry_ids=…)` 有过滤（`v12_flow.py:546,645`）；**quotation、TP、notification 的循环里没有任何按订单过滤的入口**。因此 `RunScope` 现在直接拒绝这三个模块（`SCOPE_MODULE_NOT_ISOLATABLE`），而不是让它们带着"范围"标签跑全表。
  3. 同理，`smtp` 作为写入目标也拒绝（`SCOPE_SMTP_NOT_ISOLATABLE`）：邮件队列没有按订单过滤的能力。
- 测试：
  - `test_composition_receives_the_scoped_orders` 走**真实 `_run`**，断言 `compose_v12_production` 收到的 `inquiry_ids` 就是范围里的那一个；
  - `test_a_module_without_order_isolation_is_refused` 覆盖 quotation/TP/notification 三种拒绝；
  - `test_mail_cannot_be_named_as_a_write_target`。

### P0-B — 邮件服务绕过范围

- 事实：`main()` 在非预览模式无条件 `start_process_services()`；该函数会构建邮件研究服务并打开 IMAP、可发 SMTP。范围里没有 notification 也照开。
- 修复：新增 `may_start_process_services()`——预览恒 False；受控模式要求"notification 模块 + smtp 目标"同时成立；旧路径（未启用范围）保持 True。`main()` 先问它；`start_process_services()` 与 `retry_failed_process_service()` 各自再拒一次（双层）。
- 测试：`test_preview_never_may_start_process_services`、`test_scoped_run_without_mail_scope_never_starts_process_services`、`test_legacy_composition_is_unchanged`、以及 launcher 级 `test_launcher_does_not_start_mail_when_the_backend_refuses`。

### P0-C — 其他入口没有预览防护

- 事实：只禁了主 Start 按钮。`start_order_mail_check()`（读信+录单）、`start_login_all_sites()`（驱动 Chrome 登录）、`request_order_action()`（单笔重试/编辑）都还能点、还能执行。
- 修复：
  - 后端：`start_order_mail_check`、`start_login_all_sites` 经 `_external_action_allowed()`；`can_order_action`、`order_action_hint`、`request_order_action` 在预览下一律拒绝，受控模式下只放行范围内的订单；
  - 新增 `effect_actions_blocked()` 供 UI 判断；两个按钮在预览/受控模式下置灰；
  - 点击时给明确提示（"安全预览模式不执行订单录单/一键登录"），不再"点了没反应"。
- 测试：`test_preview_refuses_order_mail_and_login_sweep`、`test_scoped_run_refuses_order_actions_outside_the_named_orders`、两个 UI 处理器级测试（不构造窗口，直接验证提前返回与提示）。

## 2. 原有两项全量测试失败的复核

**结论：与代码无关，也与今早故障无关；不删除、不跳过。**

- 失败用例：`tests/launcher/test_release_infrastructure.py::test_backend_closes_only_owned_browser_after_runtime_thread_exits[False]/[True]`。
- 真实异常（用离线插件捕获 `_runtime_error` 得到）：
  `V12Fault(WORKFLOW_LEDGER_UNAVAILABLE) <- sqlite3.OperationalError: attempt to write a readonly database`，发生在测试库的 `defer_notification_review` 写事务上。
- 归因证据：
  1. 同一对用例在允许写入的终端里连续通过；在受限沙箱里必现；
  2. **未修改的父提交 `e59ce62f` 在同一环境跑出完全相同的两个失败**（连同 4 个只属于"解包树"的 error）；
  3. 失败现象是"测试临时目录写不进去"，与本轮三条 P0 的代码路径无关。
- 处置：测试原样保留。发布判据改为"**失败集合是否与基线一致**"，而不是"数量是否为 0"。
- 与今早事件的区分：今早是 `SSLEOFError → SHEETS_READ_UNAVAILABLE`（网络 TLS），此处是 `OperationalError(readonly) → WORKFLOW_LEDGER_UNAVAILABLE`（测试环境写权限）。**只有"状态叫 MODULE_PAUSED"这一点相同，不构成关联。**

## 3. 本轮测试结果

- 新增 `tests/launcher/test_rfq021_p0_scope_binding.py`（15 项）+ 1 项 UI 拒绝测试。
- 受影响模块（launcher + gui + research + inso）：**2,653 passed / 0 failed**（203 s，修复过程中记录）。
- 完整套件：**4,237 项 / 4,235 通过 / 2 失败 / 1 跳过 / 424.76 s**。
- 两个失败就是第 2 节分析的那两个 nodeid，失败集合与未修改基线一致；新代码没有引入新的失败。

## 4. 最终候选（重建）

| 项目 | 值 |
|---|---|
| 源码提交 | `1314da5d`（基线 `8cded532` + 三个 P0 修复） |
| EXE | 8,457,679 B / `74586eb29ed19e037e2045f481d4ed2226aa555a8f6ef7951028c873fa68d0ed` |
| 文件数 | 2,872 |
| 清单 | `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256`（`74ae29c7…`） |
| 上一版候选 | `63bcd6ce…`，清单已归档为 `…-manifest-r1.sha256`，不再代表当前源码 |
| 自检 | `--self-check` 0 / `--idle-self-check` 0 / `--preview-self-check` 0（两轮） |
| 逐文件复算 | `verify_release_candidate.ps1`：2,872/2,872，0 缺失 / 0 不一致 / 0 多余 |

## 5. 仍未解决（不隐藏）

1. **报价 / TP / 通知无法按订单隔离**：现在被明确拒绝而不是假装受控。若 Owner 需要"单笔报价试运行"，需要另开一个有界任务给这三个模块加订单过滤。
2. **B3 完整回滚快照、B4 干净停机**：仍需维护窗口与 Owner 授权。
3. **SSLEOFError 的可用性**：一次 TLS 抖动就停到人工介入（今早事件），属可用性问题，本轮按 Owner"不扩大范围"未改。
4. **未在真实业务上跑过一次受控启动**；范围行为由单元/集成/负向测试证明。
5. 候选未安装、未作为正式程序运行；构建不可位级复现。

## 6. 判据

- 三个 P0：**PASS**（每条都有失败前置的负向测试与跨入口集成测试）。
- 发布：**仍 HOLD**，原因不再是源码缺陷，而是 B3/B4 的现场条件未满足。
