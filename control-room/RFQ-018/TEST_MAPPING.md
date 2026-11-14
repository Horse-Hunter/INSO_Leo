# RFQ-018 — RFQ-017 的 26 项测试意图映射

**原则：** 26 个原始 nodeid 全部保留并最终通过；没有删除、skip 或静默排除。
- **未改动（6）：** #8 owner adoption、#13/#14 未确认写、#15 busy close、#21 order-mail、#26 sales no-admission。代码修复后这些原始测试直接通过。
- **改写（20）：** 去掉对从未实现的 `_document_barrier` / `_GoogleDocumentBarrier` / `google_resource_barrier` / `google_resource_holds` 的引用，改为当前 `PageResourceAdmission` 文档 hold、retained identity、持久 V13 hold 或 sales admission 的等价/更严格断言。
- **新增（28，含 CEO Review 补 12）：** 共享页面安全负向回归、admission 单元、API、浏览器 fallback，以及 P0-A/P0-B/P1-C 的页面关闭保留 hold、无/失效 admission、原子在途写竞争测试。

| # | 原始 nodeid（tests/launcher/...） | 原安全意图 | 处理 | 当前机制 / 新断言 |
|---|---|---|---|---|
| 1 | `test_backend.py::test_google_resource_startup_failure_permanently_blocks_writer` | 启动资源失败后写者永久被阻断 | 改写 | `PageResourceAdmission.invalidate` 后 `require_open` 连续 3 次仍失败；不通过“重试”恢复 |
| 2 | `test_backend.py::test_google_resource_startup_restores_existing_hold_and_reuses_store` | 已存在 hold 在新客户端/启动时恢复并复用 | 改写 | 同一 root 的多个 child 都看到 root document hold；不是第二套 store |
| 3 | `test_google_quote_update.py::test_confirming_refresh_never_releases_other_unknown_or_read_hold` | 结算 refresh 不得清掉其他 unknown/read hold | 改写 | 多 owner hold：release refresh owner 后 unknown owner 仍阻断 |
| 4 | `test_google_quote_update.py::test_document_write_admission_serializes_threads_but_allows_same_owner_nesting` | 同文档写者串行；同 owner 嵌套允许 | 改写（CEO P1-C 恢复真实两线程） | `begin_document_write` 原子 lease：同 owner 重入；竞争线程在 `DocumentWriteBusy` 被拒；结束后另一 owner 可获取 |
| 5 | `test_google_quote_update.py::test_failed_busy_read_with_unchanged_markers_does_not_prove_owner_abandoned_it` | 失败读 + 未变 marker 不能证明 owner 放弃 | 改写 | 旧 unresolved 页面保留；允许一次隔离恢复；写者绝不复用旧页面 |
| 6 | `test_google_quote_update.py::test_failed_owned_read_navigated_to_error_page_recovers_in_same_scope` | 错误页读失败不得给写权限 | 改写 | 错误页保留；reader/writer 都不得复用该页 |
| 7 | `test_google_quote_update.py::test_nested_clients_share_document_barrier` | 嵌套客户端共享同一 document barrier | 改写 | root/child 双向可见 hold |
| 8 | `test_google_quote_update.py::test_owner_adoption_at_refresh_close_retains_shared_hold` | owner 接管后保留 shared hold | **未改** | 关闭/接管后的新输入被 `QuotationInputBusy`/`V12Fault` 阻断；代码修复后通过 |
| 9 | `test_google_quote_update.py::test_read_only_history_survives_protected_scope_reattachment` | 只读保护历史跨 scope 保留 | 改写 | 隔离恢复后旧 protected 记录仍在 quarantine slot；旧页不关闭 |
| 10 | `test_google_quote_update.py::test_recovery_lease_excludes_all_writers_until_recovery_finishes` | recovery 期间排斥所有 writer | 改写 | recovery owner hold 阻断 writer；release 后才允许 |
| 11 | `test_google_quote_update.py::test_recovery_waits_for_inflight_writer_and_then_blocks_new_writers` | 等 in-flight writer，之后阻断新 writer | 改写 | 读恢复不关闭 in-flight writer 页；后续 writer 得到新页，不复用 unresolved 页 |
| 12 | `test_google_quote_update.py::test_refresh_settlement_does_not_clear_separate_identity_uncertainty` | refresh 结算不得清掉独立身份不确定 | 改写 | `_protected`/protected surface 阻断新 input；不确定点击证据保留 |
| 13 | `test_google_quote_update.py::test_unconfirmed_write_keeps_cross_service_barrier_after_close[protected]` | 未确认写关闭后跨服务 barrier | **未改** | 新增 document hold；新客户端同文档写入被 `QuotationInputBusy` 阻断 |
| 14 | `test_google_quote_update.py::test_unconfirmed_write_keeps_cross_service_barrier_after_close[script]` | 未确认脚本关闭后跨服务 barrier | **未改** | 同上；`_script_pending` 关闭时落 shared hold |
| 15 | `test_google_quote_update.py::test_write_surface_becoming_busy_during_close_blocks_another_client` | 关闭时页面变 busy，阻塞另一客户端 | **未改** | 关闭时检测 protected entry 并落 shared hold |
| 16 | `test_google_web.py::test_cross_scope_recovery_preserves_page_and_blocks_writes[2026]` | 失败读页保留，写者不得复用 | 改写 | 失败读页不作写页；写使用独立新页；不把 read quarantine 当 write unknown |
| 17 | `test_google_web.py::test_cross_scope_recovery_preserves_page_and_blocks_writes[SHAHAB]` | 同上，SHAHAB | 改写 | 同上 |
| 18 | `test_google_web.py::test_fallback_connection_inherits_shared_root_barrier` | fallback 连接继承 root barrier | 改写 | child admission 继承 root hold；写前被 `QuotationInputBusy` 阻断 |
| 19 | `test_google_web.py::test_quarantined_read_blocks_write_from_another_service` | 隔离读不得被另一服务当写页 | 改写 | 另一 service 使用独立新页；绝不复用 failed read page；共享 hold 时阻断 |
| 20 | `test_google_web.py::test_retained_protected_read_allows_only_one_isolated_recovery` | 受保护读只允许一次隔离恢复 | 改写 | 失败读页可退役，但 replacement 页数有界（不复利累积），不触碰 human 页 |
| 21 | `test_order_mail.py::test_order_mail_worker_passes_shared_runtime_admission` | order-mail 必须传共享 admission | **未改** | backend 显式传 `self._page_admission`；代码修复后通过 |
| 22 | `test_read_page_recovery.py::test_closed_read_target_never_clears_separate_unknown_write` | 关闭读 target 不得清掉独立 unknown write | 改写 | document hold 独立于页面生命周期；关闭读页不影响 hold |
| 23 | `test_read_page_recovery.py::test_failed_target_proof_never_releases_read_quarantine` | target proof 失败不得释放 quarantine | 改写 | hold 在 proof 失败后仍存在；写被 `QuotationInputBusy` 阻断 |
| 24 | `test_sales_order_preflight.py::test_sales_browser_binds_shared_admission_before_creating_page` | 销售建页前绑定共享 admission | 改写 | `run_sales_header_check` 先 `bind_page_admission`，`new_background_page` 看到同一对象 |
| 25 | `test_sales_order_preflight.py::test_sales_stops_before_browser_when_resource_ledger_unready` | ledger 未就绪时在浏览器前停止 | 改写 | admission `invalidate` 后 `run_sales_header_check` 返回 `STOPPED`，`acquire_cdp_browser` 不被调用 |
| 26 | `test_sales_order_preflight.py::test_sales_without_admission_stops_before_browser_acquisition` | 无 admission 不得取浏览器 | **未改** | 无 admission 直接 `STOPPED`；代码修复后通过 |

## 新增负向回归

| 文件 | 覆盖 |
|---|---|
| `tests/research/test_shared_document_admission.py` | root/child hold、双向继承、按 owner release、其他文档/读不受影响、document key 规范化、页面关闭不解除未确认写 hold、原子 in-flight lease（同 owner 重入/竞争线程 busy） |
| `tests/launcher/test_rfq018_shared_safety.py` | 未确认写关闭后跨客户端/跨 sheet、缺 admission 的 quote 写入 fail-closed、sales 无/失效/有效 admission、backend 传参、页面关闭后 root/child 仍阻断、quote dispatch lease |
| `tests/sheets/test_google_api_service.py` | API 写在 hold 下被阻断；UNKNOWN API 写落 shared hold；无/失效 admission 时 fake API 调用 0；在途 API 写阻断第二客户端 |
| `tests/launcher/test_google_web.py` | 浏览器 fallback 写在 shared hold 下被阻断；在途浏览器 fallback 写阻断第二客户端 |

## CEO 第一轮 Review 补修说明（P0-A / P0-B / P1-C）

- **P0-A**：#9/#13/#14/#15 的 hold 不再因 `page.is_closed()` 自动清除；新增“页面关闭后仍阻断 root/child 同文档及另一 sheet 写入”的测试。只有 `settlement + close` 证据路径（`allow_closed=True`）或显式 owner release 可解除。
- **P0-B**：API 写入无共享 admission 时在 `values().update` 前 fail closed；失效 admission 时 fake API 调用 0；共享 root 的 hold/正常写入仍生效。生产 backend 注入 `self._page_admission`。
- **P1-C**：#4 已恢复为真实两线程（Event 同步、无 sleep）验证原子 lease；新增 API fake 在途写、浏览器 fallback 在途写、quote dispatch lease 测试。`DocumentWriteBusy` 是“忙”而非 UNKNOWN；UNKNOWN 在释放 lease 前落 hold。
- **测试等价性解释**：#11/#16/#17/#19 的纯只读失败仍只做有界隔离，不会因页面关闭/新页而被当作写 unknown；未确认**写**由新增 shared hold + P0-A 保留规则严格阻断。没有把写入历史降级为纯读。
