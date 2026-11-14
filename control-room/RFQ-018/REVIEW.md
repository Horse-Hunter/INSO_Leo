# RFQ-018 — CEO 第一轮独立 Review（2026-11-14）

**Review 结论：`CHANGES_REQUESTED / P0-A_P0-B_P1-C / NOT_DEPLOYED / NO_VERSION_PROMOTION`.**

本次 **GitHub 源码静态审核** 针对 Executor 在 `workbuddy/v16-rfq016-stabilization` 提交的 `446d090998e8e2845aae2b23d9cae59f465a789c`；参考 [任务说明](TASK_SPEC.md)、[执行检查点](EXECUTION_LOG.md)、[原 26 用例映射](TEST_MAPPING.md)、[执行者报告](FINAL_REPORT.md)、[机器可读证据](../../docs/evidence/rfq018/rfq018-test-audit-2026-11-14.json)。CEO **没有**在 Executor Windows 上独立运行 pytest、操作受保护 Chrome、连接 Google/INSO/SMTP 或检查生产现场。本轮审核后仍不可宣称实机验收或批准部署。

## 认可的实际工作（请保留，不重新大改）

- `src/research/cdp_pages.py` 确实新增 root/child 文档级 hold 机制；`google_quote_update.py`、`google_web.py` 和 `google_api_service.py` 接入共享保护；`sales_header.py` 增加缺失/失效准入时在 browser acquisition 前 STOPPED，`backend.py` 显式传递 `page_admission`。不是只修改文档。
- RFQ-017 原 **26 个 nodeid** 与 RFQ-018 证据中 `original_26[].nodeid` 已由 CEO 逐项比较，**完全相同、同序**：6 项未改，20 项改写；`TEST_MAPPING.md` 有逐项去向。
- Executor 报告了新 16 项、部分先红后绿、相关 426 项通过，以及全树 `4176 collected / 4175 passed / 1 skipped / 0 failed`；源码和 JSON 数据相符。**执行者报告的测试全绿不等于 CEO 独立运行，更不能覆盖下面未被测试到的危险条件。**
- 原 RFQ-016 的指定自动结案/来源身份/告警修复仍为 `PASS_SOURCE_SAFETY_SCOPE`；RFQ-018 本次问题只针对新增共享安全逻辑，不重新开启 RFQ-016。

## 必须定点修复的源码问题

### P0-A — 已关闭页面会自动清除尚未确认写入的共享 hold

**实际代码**：`src/research/cdp_pages.py:143-155,169-197` 的 `hold_document(...,page=page)` 保存 page；`document_hold` 执行 `if callable(is_closed) and is_closed() is True: holds.pop(owner, None)`。与此同时 `src/launcher/google_quote_update.py:369-385,1061-1066` 的未确认点击/结果/受保护写入会用当前页面发布同文档 hold。

**可成立的危险序列**：报价点击已经发出但结果 UNKNOWN → hold 记录仍开启的 page → Owner/Chrome/异常关闭该页面 → 新客户端查询 `require_document_writable` → `document_hold` 仅因 `page.is_closed()==True` 清掉 hold → 新写入被允许。**“页面关闭”不是“外部 Google 写入已证实结算/未发生”。** 原 V13 per-order 持久 hold 不能代替同文档跨服务 hold，其他订单/其他写入仍可能被放行。这与 RFQ-018 的“不确定写入不得被其他客户端绕过”合同冲突。

**最低修复要求**：任何由可能已发出写入/结果未确认/受保护页面产生的 hold **绝不能仅因 `page.is_closed()` 而自动解除**；必须通过明确、有来源身份及写入结算证据的路径仅解除该 owner 的 hold。区分纯只读页面清理和已派发写入，不能把页面生命周期当业务结算收据。新增至少一条真实 root/child + quote writer/页面关闭后的否定回归，断言保留 hold、第二客户端对同文档及另一 sheet 的写入均被阻止，同时不误伤其他文档的读取；禁止清真实 V13 hold。

### P0-B — Sheets API 写入未通过全局失效准入；无共享根会自动创建私有根

**实际代码**：`src/sheets/google_api_service.py:211-218` 在 `page_admission=None` 时使用 `PageResourceAdmission()`，包括可写的 `build_service_account_sheets_service(..., scope=READ_WRITE_SCOPE, page_admission=None)`（`164-203`）；`_write_range:347-389` 写前仅调用 `self._page_admission.require_document_writable(document)`，但 `src/research/cdp_pages.py:193-197` 该方法 **没有 `require_open()`**。因此一个 admission 已 `invalidate()` 但没有同文档 hold 时，仍可发起 Google API update；未注入共享根的可写 API 构造还会用独立根绕过别的客户端 hold。

**最低修复要求**：所有**真实可写 API 写入**必须先验证和使用统一共享 admission，且 `require_open()` 失效时在 `values().update` 前停止；缺失共享根时 **fail closed**，不得自动把私有 admission 当成生产写入许可。允许明确只读客户端和隔离 fake 测试用受控构造方案，但不能让真实可写构造落到 private-root 兜底。补负向测试：失效 admission 时 update fake 调用次数为 0；A 在 root 挂起后 B 未注入共享 root 不能绕过写入；同一 root 挂起正常生效；正常已批准共享 root 的写入仍能成功。不要误把“一个独立新 root”当有效恢复。

### P1-C — 同文档在途并发写入没有原子准入/占用证明，旧线程测试被减弱

**实际代码**：`src/research/cdp_pages.py:193-197` 的 `require_document_writable` 只检查当前 hold、不原子地登记一个在途 writer；`src/sheets/google_api_service.py:361-389` 先查 hold 再调用 `values().update().execute()`，只有出错/收据不符才登记 hold。**两个线程/服务可在第一笔 API 请求仍在途、尚未设 hold 时都通过检查并启动同一文档写入**。原 RFQ-017 的 `tests/launcher/test_google_quote_update.py::test_document_write_admission_serializes_threads_but_allows_same_owner_nesting` 曾真正启动竞争线程；RFQ-018 改写后的同名用例 `1017-1029` 仅手工 `hold_document` 再测试一次拒绝，**没有线程或在途写入**。这不能证明“并发写串行化”，也不满足“等价或更严格测试”的承诺。

**最低修复要求**：明确并实现根 admission 下按文档的**原子写前获取/写后有证据释放**或等价的写入占用机制，至少覆盖 API write 与浏览器 fallback / quote 同文档竞争的共同入口；in-flight 的另一写者应在实际 dispatch 前停止或等待，UNKNOWN 必须转换为不可自行释放的 hold。复核同 owner 重入语义，不要单纯把 busy 当 UNKNOWN。把原同名测试恢复为真正两线程有界同步验证（非 sleep/flaky），新增 API fake 在途写与另一客户端竞争的否定测试，证明第二请求未发出；其他文档允许执行、确认结束后恢复可写，异常未确认仍阻断。不能通过简单删测、改名称或模拟预先放置 hold 达成全绿。

## 其余测试契约及证据

- `TEST_MAPPING.md` 中 #11 原“在途 writer 下读恢复及新 writer 拦截”现在变为“后续 writer 可打开新页、但不复用旧页”；#16/#17/#19 原读隔离时全局写拦截被改为“独立新页可写”。这未必全是错误（纯只读失败未必应冻结无关写），但**不能仅凭 test name/原 nodeid 保留就断言安全强度不减**。请提供最简解释及一两条真实整合负向测试，证明**未确认写入**仍严格阻断、**纯只读失败**仅进行有界隔离，不会误把写入历史当纯读。不要扩大到重做全部 20 项。
- `docs/evidence/rfq018/rfq018-test-audit-2026-11-14.json` 是 Executor 的有结构测试结论，不包含 CEO 亲自执行记录；本轮仅在源代码、测试覆盖及其承诺之间做独立静态审查。

## 现场和下一步

**`CHANGES_REQUESTED`，仅需原 Executor 在现有工作树做上述三项最小补修和明确的负向回归，不重写整体架构。** 代码及新测试先红后绿；重跑 RFQ-017 原 26 项、RFQ-018 原 16 项和全量 `tests`，提供新增/失败/跳过完整对照。完成后请求 `Review RFQ-018`，不要开始另一个 RFQ 逃避本轮安全审查。

**严格保留**最近 Executor 报告的旧 EXE `E9E3DA33…` app PID38948/watch34304、受保护 Chrome9222/PID24164（都是执行者历史快照，CEO 未实时核实）；221 行 INSO `rec_440fafd372440ecf9dacabf660dd155d` 不重放；SHAHAB/115 的 `MANUAL_REVIEW/RECONCILIATION_UNREADABLE` 仍为 UNKNOWN、原生 INSO `NOT_VERIFIED`；3 条 V13 报价挂起不清；不改生产 SQLite/WAL/SHM、不发送邮件、不点击报价、不做 Google/INSO 写入、不停止/覆盖 EXE、不合并 `develop`、不晋升 `main` 或 `release/previous`。任何真实试运行须 Owner 另行授权。

[Task Spec](TASK_SPEC.md) · [Execution Log](EXECUTION_LOG.md) · [Test Mapping](TEST_MAPPING.md) · [Final Report](FINAL_REPORT.md)。
