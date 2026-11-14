# RFQ-017 — 26 项历史失败测试审计与发布风险评估

**审计对象：** `workbuddy/v16-rfq016-stabilization` @ `95e9b186`，被审源码 `b45e870e`（RFQ-016 最终 P1-E 补丁）。

**审计方式：** 只读、离线；未修改 `src/` 或 `tests/`，未部署、未重启、未合并，未产生任何真实采购/Google 写入/报价/SMTP。

**最终结论：** **26/26 可稳定复现，0 项环境原因；21 项属于测试基线债务，5 项属于未实现的防御纵深缺口，未发现由 RFQ-016 修复引入的功能回归。整体发布风险 `MEDIUM`：不阻断一次受控试运行，但阻断“全量测试通过/无条件生产发布”的结论。**

---

## 1. 结论先行

1. **26 项不是 26 个独立缺陷，而是一个“从未落地”的共享 Google 文档 barrier / 持久 resource hold 设计的测试簇。** 全部 26 个测试函数由同一个提交 `d244241e`（2026-11-12）引入。
2. **26 项所引用的核心符号从未在任何已提交源码中存在：** `google_resource_barrier`、`_document_barrier`、`_GoogleDocumentBarrier`、`src.workflow.google_resource_holds`、`ProductionBackend._prepare_google_resource_store`。生产 `src/` 没有任何文件 import 它们；只有测试引用。
3. **11 项在 import/attribute 阶段即失败；10 项在当前 API 上运行但断言的是已废弃的全局 barrier 语义；5 项指出真实存在的防御纵深缺口**（跨服务 barrier、order-mail/sales 共享准入未传播）。
4. **没有环境原因。** 26 项在 4.76 秒内确定性失败，只使用本地 fake，不依赖网络、Chrome、SMTP、生产数据库、时钟或文件系统。
5. **其余测试全绿。** 全 `tests` 树 4160 项：排除 26 项后 **4133 passed / 1 skipped / 0 failed / 332.76s**。RFQ-016 的 3408 项是其五目录子集，数字差异来自本次多跑了 `core/research/order_mail` 等 752 项。
6. **发布判断：** 这 26 项不构成“RFQ-016 修复导致功能回归”的证据，也不证明 221 行、SHAHAB/115、UNKNOWN/hold 有任何变化；但它们使“全量回归 PASS”不成立。**受控试运行可在明确冻结已知红名单的前提下讨论；无条件生产发布/晋升现版不应在此状态下放行。**

---

## 2. 审计范围与方法

### 2.1 固定输入

| 项目 | 值 |
|---|---|
| 工作树 | `D:\Program_Leo\INSO_Leo\.worktrees\v16-rfq016-stabilization`（复用，未新建） |
| 分支 / HEAD | `workbuddy/v16-rfq016-stabilization` / `95e9b186de83741d34c6f7527e6b12d3acadff92` |
| 被审源码 | `b45e870e328bab1183ae0a5478911d6c4575641f` |
| 基线证据 | `docs/evidence/v16/rfq016-ceo-third-review-2026-11-14.json` |
| Python / pytest | 3.12.10 / 9.1.1 |
| 生产配置 | `google_api.enabled=true`（Sheets 读写走 API；CDP 保留报价按钮/legacy fallback） |

### 2.2 方法

1. 从 RFQ-016 已提交的机器可读证据中读取 26 个 nodeid，逐字使用，不重新挑选。
2. 在隔离 fake 环境中运行 26 个 nodeid，记录失败类型、完整错误行与耗时。
3. 运行 `tests` 全树并显式 `--deselect` 26 个 nodeid，确认其余测试是否全绿。
4. 用 `git blame` 定位每个测试函数首次出现的提交；用 `git log --all -S` / 路径历史确认所引用符号是否在任何提交中存在；用源码检索确认生产代码是否引用。
5. 只读核对当前运行进程、EXE 哈希、Chrome 9222、SQLite 聚合状态、221 行与 SHAHAB/115；不写、不清、不重放。
6. 按“旧测试不适用 / 环境问题 / 真实代码缺陷”三类逐项判定，并给出风险与发布含义。

### 2.3 证据文件

- 机器可读：[`docs/evidence/rfq017/rfq017-test-audit-2026-11-14.json`](../../docs/evidence/rfq017/rfq017-test-audit-2026-11-14.json)
- 执行记录：[EXECUTION_LOG.md](EXECUTION_LOG.md)
- 任务说明：[TASK_SPEC.md](TASK_SPEC.md)

---

## 3. 复现结果

### 3.1 26 项本身

```text
python -m pytest <26 nodeids> -q --tb=short -p no:cacheprovider
26 failed in 4.76s
```

- collected 26 / failed 26 / passed 0 / skipped 0。
- 失败类型分布：`ImportError` 7、`ModuleNotFoundError` 1、`AttributeError` 3、行为断言 15。
- 重复运行与 RFQ-016 上一轮证据的 nodeid 完全一致；没有 flaky、超时、端口、网络或并发时序差异。
- 所有测试使用本地 fake/SimpleNamespace；没有真实 Chrome/CDP、Google、INSO、SMTP 或生产 SQLite 调用。

### 3.2 全量对照

```text
python -m pytest tests -q --tb=short -p no:cacheprovider --deselect <26 nodeids>
4133 passed, 1 skipped, 26 deselected in 332.76s
```

- 全树 collected 4160；排除的 26 项全部命中，无额外失败。
- 唯一 skipped 是既有的 Windows symlink 权限限制，与本审计无关。
- RFQ-016 的 3408 项是 `tests/workflow tests/sheets tests/inso tests/launcher tests/gui` 子集；本次全树多出的 752 项也全部通过，说明 26 项之外没有隐藏失败。

### 3.3 结论

26 项是**孤立失败簇**，不是散落在全仓的普遍失败；排除它们后，当前源码树的全量测试是绿的。

---

## 4. 共同根因（Git 证据）

### 4.1 26 项由同一提交引入

对每个测试函数定义行做 `git blame`，26/26 均指向：

```text
d244241eafe564c79812f860b2491c903a4cee1e
2026-11-12
fix(rfq016): capture installed V1.6 candidate source and handover records
```

该提交的说明明确写道：

> “Preserve the exact working-tree source of the formally installed V1.6 build … Tests are not part of the build copy, so test-tree correspondence to the built binary is not proven.”

也就是说：**提交保存的是“已安装 EXE 的源码快照”，但测试树不是该构建的一部分，测试与源码的对应关系未被证明。** 26 项正是这次“源代码快照 + 另一份测试树”拼接的产物。

### 4.2 被引用符号从未存在

| 符号/模块 | 是否存在 | 证据 |
|---|---|---|
| `google_resource_barrier` | 从未定义 | `git log --all -S "def google_resource_barrier" -- src` 为空 |
| `_document_barrier` | 从未定义 | `git log --all -S "def _document_barrier" -- src` 为空 |
| `_GoogleDocumentBarrier` | 从未定义 | `git log --all -S "class _GoogleDocumentBarrier" -- src` 为空 |
| `src.workflow.google_resource_holds` | 从未存在 | `git log --all -- src/workflow/google_resource_holds.py` 为空 |
| `ProductionBackend._prepare_google_resource_store` | 从未存在 | 源码检索无匹配 |

同时，`src/` 中没有任何文件 import 上述符号；检索结果只出现在 `tests/launcher/`。这证明：

- 这 26 项**不可能在任何已提交源码上通过**；
- 它们不是“旧测试曾经通过、后来被代码改坏”的回归；
- 它们是**从未落地的设计所对应的测试**，属于测试基线债务。

### 4.3 为什么多轮 nodeid 完全一致

RFQ-016 多轮修复只改了 `src/workflow/v12_flow.py`、`src/launcher/backend.py`、`src/launcher/source_status.py`、`src/gui/*` 等与这 26 项无关的文件；这 26 项依赖的 barrier 模块从未被实现。因此每轮全量运行都会得到**同一组 26 个 nodeid**。这不是“稳定的已知 flaky”，而是“稳定的从未满足”。

### 4.4 该提交自带测试报告的可信度

`d244241e` 提交的 `control-room/RFQ-016/TEST_REPORT.json` 声称 `final_full: 3629 tests / 0 failures`，但提交后的测试树实际存在 26 项确定性失败，且提交说明已承认测试树与构建源码的对应关系未被证明。**该报告不能作为这 26 项通过的证据**；本次审计以实际运行结果为准。

---

## 5. 逐项判定

**分类规则：**

- **旧测试不适用（不存在 API）：** 测试 import/attribute 即失败，所引用符号从未在源码中存在；不改变任何运行行为。
- **旧测试不适用（废弃设计）：** 测试能在当前 API 上运行，但断言的是未实现的“全局 document barrier / 跨服务 hold”语义；当前架构用更窄的页面身份、per-order 持久 hold 等替代。
- **真实代码缺口（防御纵深）：** 当前代码确实缺少测试所要求的共享准入/跨服务 barrier；这不等于已发生外部重复效果，但属于需要单独决定是否补的防御纵深。
- **环境问题：** 由 OS、网络、端口、时钟、权限、依赖或并发时序导致。本次 **0 项**。

> 下表的“测试”列使用 pytest 文件形式（`tests/launcher/*.py::...`），便于阅读；机器可读证据中的 `nodeid` 使用 RFQ-016 证据的 dotted 形式（`tests.launcher.*::...`），两者是同一测试，`nodeid` 与 RFQ-016 逐字一致，顺序也一致。

| # | 测试（文件::名称） | 类别 | 失败点/证据 | 风险 | 发布含义 |
|---|---|---|---|---|---|
| 1 | `test_backend.py::test_google_resource_startup_failure_permanently_blocks_writer` | 旧测试不适用（不存在 API） | ImportError: google_resource_barrier；同时 backend._prepare_google_resource_store 不存在。 | none | 不阻断 |
| 2 | `test_backend.py::test_google_resource_startup_restores_existing_hold_and_reuses_store` | 旧测试不适用（不存在 API） | ModuleNotFoundError: src.workflow.google_resource_holds；辅助测试模块也不存在。 | none | 不阻断 |
| 3 | `test_google_quote_update.py::test_confirming_refresh_never_releases_other_unknown_or_read_hold` | 旧测试不适用（不存在 API） | ImportError: _GoogleDocumentBarrier。 | none | 不阻断 |
| 4 | `test_google_quote_update.py::test_document_write_admission_serializes_threads_but_allows_same_owner_nesting` | 旧测试不适用（不存在 API） | ImportError: _GoogleDocumentBarrier。 | none | 不阻断 |
| 5 | `test_google_quote_update.py::test_failed_busy_read_with_unchanged_markers_does_not_prove_owner_abandoned_it` | 旧测试不适用（废弃设计） | 恢复一次只读页面后，写者未被 QuotationInputBusy 阻断；当前设计允许一次隔离恢复。 | low | 不阻断 |
| 6 | `test_google_quote_update.py::test_failed_owned_read_navigated_to_error_page_recovers_in_same_scope` | 旧测试不适用（废弃设计） | Chrome error page 读失败后，新写者未被阻断；当前允许新开写页面并保留旧页面。 | low | 不阻断 |
| 7 | `test_google_quote_update.py::test_nested_clients_share_document_barrier` | 旧测试不适用（不存在 API） | ImportError: _document_barrier。 | none | 不阻断 |
| 8 | `test_google_quote_update.py::test_owner_adoption_at_refresh_close_retains_shared_hold` | 旧测试不适用（废弃设计） | open_quote_input 已以 V12Fault 阻断；测试额外要求 open_sheet 抛 QuotationInputBusy，当前未实现。 | low | 不阻断 |
| 9 | `test_google_quote_update.py::test_read_only_history_survives_protected_scope_reattachment` | 旧测试不适用（废弃设计） | 带弹窗的受保护只读页面未阻断下一次只读；当前允许一次隔离恢复。 | low | 不阻断 |
| 10 | `test_google_quote_update.py::test_recovery_lease_excludes_all_writers_until_recovery_finishes` | 旧测试不适用（不存在 API） | ImportError: _GoogleDocumentBarrier。 | none | 不阻断 |
| 11 | `test_google_quote_update.py::test_recovery_waits_for_inflight_writer_and_then_blocks_new_writers` | 旧测试不适用（废弃设计） | 在途写者未阻断只读恢复；当前按精确 target identity 允许隔离读。 | low | 不阻断 |
| 12 | `test_google_quote_update.py::test_refresh_settlement_does_not_clear_separate_identity_uncertainty` | 旧测试不适用（废弃设计） | 内存 _protected 在 close 后未形成跨客户端页面 barrier；生产以持久 V13 hold 为主。 | low | 不阻断 |
| 13 | `test_google_quote_update.py::test_unconfirmed_write_keeps_cross_service_barrier_after_close[protected]` | 真实代码缺口（防御纵深） | 无跨服务 document barrier；关闭后新写者可以打开同文档新页面。持久 hold 仅覆盖同一报价单，不是全局 barrier。 | medium | 不阻断受控试运行；阻断全绿声明 |
| 14 | `test_google_quote_update.py::test_unconfirmed_write_keeps_cross_service_barrier_after_close[script]` | 真实代码缺口（防御纵深） | 同上；_script_pending 只存在于 action 对象，关闭后新客户端不可见。 | medium | 不阻断受控试运行；阻断全绿声明 |
| 15 | `test_google_quote_update.py::test_write_surface_becoming_busy_during_close_blocks_another_client` | 真实代码缺口（防御纵深） | 关闭时页面变 busy，但另一个 sheet 的写者仍可打开新页面；无跨 sheet/文档 barrier。 | medium | 不阻断受控试运行；阻断全绿声明 |
| 16 | `test_google_web.py::test_cross_scope_recovery_preserves_page_and_blocks_writes[2026]` | 旧测试不适用（废弃设计） | 浏览器 fallback 路径：一次失败读页面保留后，写操作未被阻断；生产已启用 API 读写（google_api.enabled=true），该路径为 fallback。 | low | 不阻断 |
| 17 | `test_google_web.py::test_cross_scope_recovery_preserves_page_and_blocks_writes[SHAHAB]` | 旧测试不适用（废弃设计） | 同上，SHAHAB 工作表。 | low | 不阻断 |
| 18 | `test_google_web.py::test_fallback_connection_inherits_shared_root_barrier` | 旧测试不适用（不存在 API） | ImportError: _document_barrier / google_resource_barrier。 | none | 不阻断 |
| 19 | `test_google_web.py::test_quarantined_read_blocks_write_from_another_service` | 旧测试不适用（废弃设计） | fallback 路径：隔离读页面未阻断另一服务写；生产 API 路径不使用该浏览器写。 | low | 不阻断 |
| 20 | `test_google_web.py::test_retained_protected_read_allows_only_one_isolated_recovery` | 旧测试不适用（废弃设计） | fallback 路径：页面保留/隔离恢复数量与测试期望不同；当前按 close/retire 规则处理。 | low | 不阻断 |
| 21 | `test_order_mail.py::test_order_mail_worker_passes_shared_runtime_admission` | 真实代码缺口（防御纵深） | backend._order_mail_worker 未向 run_sales_header_check 传 page_admission；该函数也没有该参数。 | medium | 不阻断受控试运行；阻断全绿声明 |
| 22 | `test_read_page_recovery.py::test_closed_read_target_never_clears_separate_unknown_write` | 旧测试不适用（不存在 API） | ImportError: _document_barrier。 | none | 不阻断 |
| 23 | `test_read_page_recovery.py::test_failed_target_proof_never_releases_read_quarantine` | 旧测试不适用（不存在 API） | AttributeError: module has no attribute _document_barrier。 | none | 不阻断 |
| 24 | `test_sales_order_preflight.py::test_sales_browser_binds_shared_admission_before_creating_page` | 旧测试不适用（不存在 API） | AttributeError: sales_header.google_resource_barrier 不存在。 | none | 不阻断 |
| 25 | `test_sales_order_preflight.py::test_sales_stops_before_browser_when_resource_ledger_unready` | 旧测试不适用（不存在 API） | AttributeError: sales_header.google_resource_barrier 不存在。 | none | 不阻断 |
| 26 | `test_sales_order_preflight.py::test_sales_without_admission_stops_before_browser_acquisition` | 真实代码缺口（防御纵深） | run_sales_header_check 无 page_admission 参数；无准入时仍会 acquire_cdp_browser。 | medium | 不阻断受控试运行；阻断全绿声明 |

**汇总：** 旧测试不适用 21 项（不存在 API 11 + 废弃设计 10）；真实代码缺口 5 项；环境问题 0 项。

---

## 6. 当前实际保护与残余缺口

### 6.1 当前已有的保护（不是“没有保护”）

- **页面资源准入：** `PageResourceAdmission` 的 `require_open` / `invalidate` / 父子继承，`bind_page_admission` 在浏览器句柄上绑定；多数后台/前台路径在创建页面前调用 `require_open()`。
- **页面身份与保留：** `google_operation_scope()` 只保存 target ID；`_retained_google_matches` / `_google_target_id` 要求精确原生 target 证明；受保护/未知页面不会被静默关闭或复用。
- **报价输入 busy：** `QuotationInputBusy` 在已有脚本、刷新未结算、受保护条目的路径上抛出；`UpdateAttemptUnconfirmed` / `UpdateClickUnconfirmed` 区分钟结果不确定性。
- **持久业务 hold：** V13 报价未确认写入会落持久 hold；同一报价单的后续输入/点击被阻断，`UNKNOWN` 不会被人工表格状态清除。
- **传输分工：** 生产 `google_api.enabled=true`，Sheets 读写走 API；CDP 只保留报价按钮和 legacy fallback。4 个 `test_google_web` 失败测试针对的是 fallback 浏览器读写，不是当前生产读写主路径。

### 6.2 5 项真实缺口（防御纵深，非已证外部效果）

1. **跨服务 Google 文档 barrier 缺失**（第 13、14 项）：一个客户端的报价脚本/写入处于未确认状态后，另一个客户端仍可打开同文档新页面写入。当前持久 hold 按“同一报价单”阻断，不是按“同一 Google 文档”全局阻断。
2. **关闭时页面变 busy 的跨 sheet 阻断缺失**（第 15 项）：另一个 sheet 的写者仍可打开新页面。
3. **order-mail 未传播共享准入**（第 21 项）：`_order_mail_worker` 调用 `run_sales_header_check` 时不传 `page_admission`，该函数也没有该参数。
4. **sales preflight 无准入门**（第 26 项）：`run_sales_header_check` 在没有 admission 时仍会 `acquire_cdp_browser`。
5. 上述缺口共同意味着：**“页面资源已失败/不确定”这一状态不会自动阻止所有后续浏览器写者**；它依赖各调用点自行检查，而不是统一的文档级 barrier。

### 6.3 为什么不是高风险

- 没有复现出重复采购、重复报价、重复邮件、数据覆盖或 221 行/其他订单的外部效果。
- 这些缺口位于“页面资源/并发写者”层，不是业务效果层；业务效果仍有 per-order 持久 hold、精确 target identity、单 Executor 和模块串行化约束。
- 生产主读写走 API；fallback 浏览器路径的 4 项失败不覆盖当前主路径。
- 真正运行中的 EXE 是修复前代码，本次未部署任何新代码；26 项失败不会因本审计改变现场行为。

---

## 7. 发布风险与门槛

| 问题 | 结论 |
|---|---|
| 是否存在由 RFQ-016 修复引入的功能回归？ | **没有证据。** 26 项全部早于修复，且不 touch 修复文件。 |
| 是否存在真实代码缺陷？ | **有 5 项防御纵深缺口；没有已证的外部重复效果。** |
| 是否环境问题？ | **0 项。** |
| 是否阻断受控试运行？ | **不因这 26 项本身阻断**，前提是：已知红名单冻结、不得删除/跳过、不得宣称全绿、保留现有 hold/UNKNOWN、另行批准部署。 |
| 是否阻断“全量回归通过”？ | **是。** 26 项 red 使全量绿不成立。 |
| 是否阻断无条件生产发布/晋升现版？ | **是。** 在 26 项未修复/未获 Owner 明确接受前，不应给出无条件发布结论。 |
| 如果 CEO/Owner 要求“零失败才能部署”？ | **是硬阻断。** |
| 风险等级 | **MEDIUM**（测试基线债务 + 5 项防御纵深缺口；无已证功能回归）。 |

**建议的发布门槛（供 CEO 决定，不在本 RFQ 自动执行）：**

1. **冻结** 26 个 nodeid 为已知红名单；CI/回归必须显式比较，任何新增失败立即停止。
2. 另开一个**独立测试基线清理任务**（建议 RFQ-018），二选一：
   - 按原设计实现共享 document barrier / 持久 Google resource hold，并让 26 项转绿；或
   - 经 CEO 审核，把这 26 项改写为当前架构的等价保护测试，或明确标记为 retired，不得静默删除/skip。
3. 为 5 项真实缺口补最小回归：跨服务未确认写阻断、order-mail/sales admission 传播。
4. 在上述完成前，若 Owner 批准受控试运行，发布说明必须写明“26 项已知红、非全绿”，并保留现有 V13 hold、221 行 SAVED、SHAHAB/115 UNKNOWN 的隔离。

---

## 8. 限制与 UNKNOWN

- 本次是**源码/测试离线审计**，没有在已安装 EXE 上重跑 26 项，也没有反编译 EXE 证明其内部不含 barrier；结论基于已提交源码、测试树和 Git 历史。
- 没有证明“共享 document barrier”曾是 Owner 明确批准的需求；它可能只是某轮设计的测试先行产物。是否补实现属于 CEO/Owner 决策。
- 没有生产 CDP/INSO/SMTP/Google 写入；5 项缺口是静态/行为测试层面的判断，未复现外部效果。
- 没有读取或修改任何 `SENT/UNKNOWN`、V13 hold、221 行或 SHAHAB/115 的历史效果；现场只读快照见附录。
- 26 项中可能有一部分应被保留为“未来安全要求”；本次不替 CEO 决定删除或降级。

---

## 附录 A — 复现命令与结果

```text
# 26 项
python -m pytest <26 nodeids> -q --tb=short -p no:cacheprovider
26 failed in 4.76s

# 全树排除 26 项
python -m pytest tests -q --tb=short -p no:cacheprovider --deselect <26 nodeids>
4133 passed, 1 skipped, 26 deselected in 332.76s
```

RFQ-016 基线（上一轮已提交证据）：3408 collected / 3381 passed / 1 skipped / 26 failed / 312.2s。

## 附录 B — 26 个 nodeid

见 [`docs/evidence/rfq017/rfq017-test-audit-2026-11-14.json`](../../docs/evidence/rfq017/rfq017-test-audit-2026-11-14.json) 的 `reproduction.failed_nodeids` 与 `classification[].nodeid`。`nodeid` 使用 RFQ-016 证据的 dotted 形式，**逐字、同序等于** `final.failed_nodeids`；`classification[].file_nodeid` 是同一测试的 pytest 文件形式。

## 附录 C — 只读现场快照（2026-11-14 17:0x）

- EXE：`dist/INSO_V1.6/INSO_V1.6.exe`，SHA256 `E9E3DA33…`，8,422,619 bytes；app PID 38948（`--start-inquiry`），watcher PID 34304。
- Chrome CDP：`127.0.0.1:9222`，owner PID 24164；未连接、未点击、未关闭。
- SQLite：60 单 = 35 `HUMAN_COMPLETED` + 24 `PURCHASE_RECORDED` + 1 `INVALID_INPUT_SKIPPED`；0 条 active V12 alert；3 条 active V13 hold（`inq_71f4a2f5…`、`inq_d65be9df…`、`unresolved:0ca37229…`）。
- 221 行：`inq_e15970df104e170d93b4169b`，`PURCHASE_RECORDED`，`SAVED`，receipt `rec_440fafd372440ecf9dacabf660dd155d`；未重复下单。
- SHAHAB/115：`inq_99275e8e72b43fd6616fd686`，`HUMAN_COMPLETED`，purchase `MANUAL_REVIEW / RECONCILIATION_UNREADABLE`，无 saved receipt；保持 UNKNOWN/隔离，未修库、未重开、未补告警。

---

**审计裁决：** 26 项 = 21 项旧测试不适用 + 5 项真实防御纵深缺口 + 0 项环境问题；无 RFQ-016 功能回归；风险 `MEDIUM`；不阻断受控试运行，阻断全量绿/无条件生产发布。请 CEO 独立复核。
