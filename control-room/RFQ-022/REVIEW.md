# RFQ-022 — CEO Independent Review（2026-11-17）

**独立结论：`CHANGES_REQUESTED_UI_DIAGNOSTICS / SOURCE_TLS_FIX_ACCEPTED / PRODUCTION_ALREADY_INSTALLED_EXECUTOR_REPORTED / BUSINESS_DONE_EXECUTOR_REPORTED / NO_NEW_PRODUCTION_ACTION`.**

本轮的**TLS 有界读取恢复修复可以接受**；982/983 的原始未处理原因与 17:55 共享停止事件在 Executor 保存的现场记录中有明确的分类及时间线。但是 **Owner 明确要求“异常与通知直接看清故障，不再每次找 Agent”仍未达到完整验收条件**：以下两个可直接从已提交源码证明的缺口必须在 RFQ-022 内闭环。**这不是撤销已经发生的安装/采购，也不是要求马上停机、回滚或重复执行订单。** 仅为 CEO 的产品/代码/证据验收结论。

## 1. 固定审核对象与证据边界

- 仓库 `Horse-Hunter/INSO_Leo`，执行分支 `workbuddy/v16-rfq016-stabilization`；本次代码提交 **`aaac8c75`**（后续至交付 HEAD `263e15b7094ef1b1646970b59ee199ba62e29906` 为任务文档和交接）。CEO 实际读取：`TASK_SPEC.md`、`EXECUTION_LOG.md`、`RFQ-021/EXECUTION_LOG.md` / `CEO_SYNC_20261117.md`、`COORDINATION.md`、`AGENTS.md`，并检查本轮源代码及新增/变更测试。
- GitHub 保存的候选清单 `docs/evidence/rfq021/INSO_V1.6-artifact-manifest-rfq022.sha256`：CEO **独立重新计算文本 SHA256** 为 **`08b0e9f618ba9c504f573b918c67ce2a18c74f32817790fca153cec69c138684`**，与报告吻合；2,872 条、2,872 个不重复路径、无 `runtime/`；EXE 清单项为 **`f2ffa44f7f31d373ac010116a0bbcb240297341948fb86b567c7e7bd94b3728c`**。该核验**不能**代替现场 Windows 已安装 EXE 及其 2,872 文件的独立实物哈希；Executor 报告 8,476,327 B、安装逐文件 PASS。
- **现场事实仅为 Executor 的留痕报告而非 CEO 实机复测**：新 EXE 据报已安装运行；行 983 于 19:30:57、行 982 于 19:35:55 各有 `PURCHASE_DATA_SAVED / SAVED`，两行 `未发→发给采购`，两笔通知每笔两名收件人 `SENT`，三条 Google 写入意图 `SETTLED`，无活动告警。不能据此指挥再次采购，也不能说 CEO 独立打开了 Google/INSO/SQLite 验证。
- 已报告测试：`tests/gui` **123 PASS**，`tests/launcher + tests/gui` **1843 PASS / 1 FAIL**，`test_source_order_date.py` **22 PASS**，`ruff` PASS。失败节点 **`tests/launcher/test_backend.py::test_empty_poll_defers_browser_bootstrap_until_an_inquiry_is_due[False]`**，Executor 归因为只读临时库、单测 2/2 PASS；**根因缺乏足以排除源码问题的可复现环境证据**。本轮也没有提交源冻结后的全量 4k+ suite 0 FAIL 的报告，不得称全部测试全绿。

## 2. 接受的内容（无需再重复开发）

1. **982、983 的最初故障归因有明确的现有现场记录链：** 14:37:21 已读取、入库，`2026` 第 981 行重复表头是受支持结构；日期当日准入通过；982 `DUPLICATE_CHECKING`、983 `DUPLICATE_CHECK_PENDING`，浏览器/登录巡检 `BrowserBootstrapError` 阻止重复检查。与 17:55 另一次 TLS 读取停止**分开解释**。这些属于 Executor 的生产只读取证结论；本次 CEO 未复查生产数据库原件。
2. **17:55 的 `ssl.SSLEOFError` 与“三小时机制”边界合理：** `src/sheets/google_reader.py:28-34,53-74` 将仅 `SSLEOFError/SSLZeroReturnError/SSLSyscallError` 计为有界重试的瞬时只读断链；`src/workflow/v13_integration.py:is_isolated_source_read_error` 的异常链仍拒绝证书、DB、鉴权、未知网页/资源所有权故障；`src/launcher/backend.py:_website_failure` 保留证书类 fail-closed。该变更没有授权外部写入自动重放。11-17 的 `PROGRAM_INTERNAL_STOP` 不是经确认的 `*_OUTAGE_THREE_HOURS`；是否根源来自网络/VPN 仍未证明，不能称网络根因已查明。
3. **异常 UI 基础结构已实现：** `FaultDiagnostic` 有故障码、时间、模块、异常类、恢复过程、外部效果及建议操作；不读取自由格式异常 message，规避原始 Token/URL 泄漏；`WorkbenchSnapshot.faults` 向 `src/gui/workbench.py:fault_block` 提供显示；部分停机事件将 `diagnostic` 存入现有 incident `review_json`，`V12Store.recent_fault_diagnostics` 能读取历史活动故障。新增测试验证了静态投影与部分临时 SQLite 读回。
4. 既有采购去重、`SENT/UNKNOWN`、write-intent、hold 及正常启动策略没有在本轮差异中被刻意禁用。TP 的 `RFQ_BRIEF.target_price` 与 `Remark` 取价口径、`CLASS=A` 的路由耦合、982 的纯读中断需人工恢复属于记录清楚的**现有功能/产品待决项**，本次不允许拿它们掩盖 UI 缺口或擅自改业务规则。

## 3. 必须闭环的缺口（仅定点修，不增开 RFQ）

### P1-A：读失败的实时异常不会进入“异常与通知”

- **已直接证明的代码路径：** `backend.py:_run_independent_job_scoped`（约 1988–1995）对恢复性 Google 只读故障调用 `_defer_website_poll(..., notify=False, recoverable_read=True)`；`_defer_website_poll`（约 3260–3275）只在 `notify and not recoverable_read` 时调用故障通知，而 **从未调用 `_record_fault_diagnostic`**；`_record_fault_diagnostic` 现仅在停机或符合通知路径时调用。对这种常见故障，内存 `_faults` 为空，用户只能看到模块“等待重试”/旧笼统提示，而“异常与通知”没有真实异常类、首次时间、次数和下一步建议。
- 这恰恰是本轮把 TLS 断链改成“不再全停”之后**最常发生的故障路径**。测试 `test_tls_eof_mid_read_is_a_bounded_isolated_retry` 只断言无通知/邮件、保持运行，没有断言 GUI 故障摘要。**不发烦人的通知邮件 ≠ 不在本地 GUI 记录异常**。
- **验收补修：** 在统一的只读故障分类/延期入口为本地 GUI 建立脱敏诊断，不误报为整站中断、不扩散 SMTP、不触发订单错误/UNKNOWN、不停止健康模块；记录最初/最近时间、次数、下一轮时间、已恢复。增加真实 backend → `WorkbenchSnapshot` → Tk“异常与通知”集成测试，及恢复时清理测试。

### P1-B：恢复状态只改内存，数据库活动 incident 可能在重启后重新显示为未恢复

- **已直接证明的代码路径：** `backend.py:_resolve_faults`（约 3341–3355）仅修改 `self._faults` 内存里的 `recovered_at`、`phase`；不更新它对应的 `workflow_v12_notification_commands.review_json`。`V12Store.recent_fault_diagnostics`（约 539–576）重启时仅查询 `proof.active is True` 的 incident。`_site_recovered` 调用 `resolve_incidents(site)`，但 `_notify_runtime_fault` 保存的共享停止 incident 使用 `module='business_runtime'`；`_resolve_faults_after_success` 并未总是配套持久化 `business_runtime` 的解决状态（业务运行也可能只恢复 inquiry/TP）。
- 因此存在**UI 曾提示“已恢复”→ 重开窗口从依旧活动的 incident 读到旧故障**的状态分裂。现有 `test_a_recovered_site_marks_the_fault_resolved` 只验证内存；`test_a_settled_incident_is_history` 是测试直接插入 `active=False`，并未验证真实成功恢复路径持久化。
- **验收补修：** 沿现有 incident API 和真实恢复凭据统一修改 `active/recovered_at`，不覆盖订单专属历史告警，不清 `UNKNOWN/SENT/hold`；建立“故障发生→真实成功恢复→关窗重启→旧故障不再显示为活动”的端到端持久化测试，包含 quotation 关闭/仅 inquiry 恢复情形。

### P2：单笔异常仍使用泛化文案

`src/gui/workbench.py`（约 1215–1230）对异常订单仍显示“本单停在已记录状态，需要人工确认”，活动 alert 只给 `alert_type/reason_code` 与“本单存在未结算异常”。这仍不能让 Owner 在“异常与通知”直接知道具体原因和可执行处理动作。复用现有订单级 `reason_code`、安全事件和原有字典，提供按原因的操作建议及证据定位；未知要明确标注尚未确认，且不要把全局故障原因投射为单笔写入已失败。

## 4. 测试与生产验收条件

- **不要求重做整个 RFQ-022，也不要求新一轮架构/通用日志系统。** 两个 P1 和一个同一页面的小 P2 作为**同一次 UI 诊断收尾补丁**；先写能失败的定向负测，最小修改后跑涉及 backend/UI/incident 的集成测试和一次全量回归，提交机器可读 junit（失败数真实为零或保留有根因和风险评估的明确阻断，不能仅用“单跑通过”宣称全绿），更新唯一候选 EXE/清单并重新验实物一致性。改源码意味着旧 `f2ffa44f…` 构建只能作为已安装历史，不能用旧哈希证明新功能。
- **不要求重放 982/983**：Executor 已报 `SAVED`，任何再次 Save-and-Send 都有重复采购风险；只可只读核对现在的 Sheet/INSO/SQLite 回执与通知状态。已部署进程和回滚材料需保留；新 EXE 不能直接覆盖活动进程；维护窗口操作依现有 Owner 权限及手册。不得为补测试去触碰生产订单。
- **真实故障 GUI 尚无现场验证**：截至本次提交，只有合成/快照 Tk 测试，未见新版本在现场真实 TLS/CDP 故障态的界面证据。可用受控故障注入/隔离环境展示“异常→恢复→重启”，避免为了测试制造生产故障。
- **遗留且须在 Owner 面前透明记录**：TP 目标价来源空缺，`CLASS=A` 连带采购路由，3 项历史 hold 和浏览器/登录稳定性；这些不构成本轮 TLS 安全修复的反证，也不授权强行清理。

## 5. 对 Executor 的一次性后续指令

在同一 RFQ-022 完成 **P1-A + P1-B + P2** 的最小集中补丁及负向集成测试；保留已经验证的 TLS 分类、生产 GUI 正常启动与采购保护，明确给 Owner 展示诊断页面可见的实际字段和重启后状态。处理合跑 1 项失败并给出可复现证据，不要凭“环境问题”直接排除；源码固定后提交实际测试统计与唯一新候选哈希。不要擅自再次处理 982/983、停止当前生产、覆盖安装、清 UNKNOWN/hold、改 TP 规则或移动 main/release。提交 RFQ-022 更新的 `EXECUTION_LOG.md` 后请求一次 CEO 收尾复核。

**Final CEO status：`RFQ022_CHANGES_REQUESTED_UI_DIAGNOSTICS`；已部署/已完成采购均为 Executor 已报告的现场事实，CEO 未独立实机重验。**
