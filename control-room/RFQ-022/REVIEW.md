# RFQ-022 — CEO 最终收尾独立核验（2026-11-18；Executor 5cb23619）

**最新唯一有效结论：`RFQ022_FINAL_SOURCE_AND_OFFLINE_ACCEPTED / REVIEW_CLOSED / NEW_CANDIDATE_NOT_INSTALLED / PRODUCTION_UNCHANGED_EXECUTOR_REPORTED`.**

**决议：RFQ-022 P1-A、P1-B、P2 及此前唯一遗留的受控订单范围隔离回归已按本 RFQ 契约完成源码级和提交证据验收；本轮代码审核结束。** 无须新开 RFQ 或再进行一次重复源码审查。**不等于已安装最新 EXE 或现场生产版已更新**。这份 REVIEW 本身不授权停机、换版、重发真实订单或清理历史 hold。

## 核验事实与复核范围

- GitHub 执行分支 `workbuddy/v16-rfq016-stabilization`，核验对象 SHA：**`5cb23619c98256bfaebad2384d9710112258cb71`**。与上一 CEO REVIEW 提交 `5245eefa45f17dcebc0b7b88764ad46495a26642` 相比，源码仅改 `src/launcher/backend.py`（11 增/1 删）；测试仅改 `tests/launcher/test_fault_diagnostics.py`（新增范围负测）。余下提交为执行日志/任务状态和候选证据，不存在额外业务模块改动。
- `backend.py:_persist_fault_recovery` 实际读取：`_enforce_scope=True` 时将 `within=frozenset(scope.inquiry_ids)` 传给 `store.resolve_incidents(..., diagnostic_code=…, within=within)`；scope 缺失时为空集合（不是全量）；不受控模式 `within=None` 保留旧逻辑。与已存在的 `_site_recovered` 范围规则一致。
- 测试 `test_a_scoped_recovery_never_settles_another_orders_incident` 构造 A（授权）、B（非授权）、程序级和 B 的站点 incident，均为相同诊断码 `SHEETS_READ_UNAVAILABLE`；调用真正的 `backend._resolve_faults(site="Google Sheets")` 后断言：A/程序级变 inactive，B 的两条仍 active，活动告警/hold 表行数不变。另测 `test_an_unscoped_backend_keeps_the_historical_settlement` 验证无范围旧行为。Executor 提供修复前 `1 failed / 1 passed`、修复后 `2 passed` 的红→绿记录；CEO 审阅了用例源码和断言，未自行在 Windows 运行。
- 机器可读 `docs/evidence/rfq022/pytest-full-scope-fix.xml` 直接检查：**`4311 testcase / failures=0 / errors=0 / skipped=1`**，即 **4310 passed**。Skip 为既有 Windows symlink 权限条件。前次偶发 `SQLITE_READONLY` 本次未复现，但缺少当时进程/ACL 实证，不能由全绿倒推出其历史根因已彻底证明。
- GitHub `docs/evidence/rfq022/INSO_V1.6-artifact-manifest-rfq022c.sha256` 文本 SHA256 **已独立重算并匹配**：**`58c933b73a4b6bd6441efe3c8ceb9a7c7343ba500ca4c2fa8469d0c189883a97`**；2,872 条均格式正确、路径唯一，无 `runtime/`；EXE 清单项 **`0e7a985bd61e5abdcabb011c7de2999ac3fd038ec5b2d1cdf45d4cf58c8ef488`**。报告中的 EXE 8,480,855 B、运行 `--preview-self-check`/`--idle-self-check` 与 `RELEASE_SCAN_OK` 为 Executor 提交的 Windows 构建证据；CEO **没有读取/哈希 Windows 实物 EXE**。
- 此次未重复调查已接受的 TLS 故障分类、故障页面 P1-A/P2、故障持久化主体 P1-B，也未对真实 Google/INSO/SMTP、已安装程序、生产 SQLite、PID、982/983 订单进行现场操作。历史两笔 `SAVED` 仅为 Executor 提交的先前现场证据，禁止再次采购来“验收”。
- **非阻断已知剩余行为**：若持久化恢复写库发生 SQLite 错误，当前会记录警告而本会话内存已显示【已恢复】；重启后可能重新显示活动 incident。这是已披露的保守/可见性不一致，不等于未知采购写入自动恢复，亦不影响本次明确的订单范围补丁验收。后续若有实际重现，可另作为稳定性问题处理，**不再反复要求 RFQ-022 补丁迭代**。

## 后续界限

1. **RFQ-022 源码与离线发布候选通过，审核结束。** 最终尚未安装的候选是 EXE SHA256 **`0e7a985bd61e5abdcabb011c7de2999ac3fd038ec5b2d1cdf45d4cf58c8ef488`**，清单 SHA256 **`58c933b73a4b6bd6441efe3c8ceb9a7c7343ba500ca4c2fa8469d0c189883a97`**。此前 `119163b5…` 和已安装 `f2ffa44f…` 均是不同历史版本。
2. **生产部署未验收：** Executor 报告现行生产仍是 `f2ffa44f…`；新 UI 诊断与范围补丁的真实机器上安装和运行结果为 **NOT_VERIFIED**。后续若需换版，必须对当前实物、备份、独占数据库/未结算写入和安装门禁作真实核验；不得覆盖活动程序；依 Owner 明确发布授权执行，不得把离线 PASS 当成现场安装 PASS。
3. **不授权重复 982/983**、更改采购回执、清除 `UNKNOWN/SENT/hold`，不改变 TP 口径或推送 main/release。正式生产版要保留正常 GUI 业务入口和功能，不能退回仅供安全预览的受限模式。

**Final: `RFQ022_FINAL_SOURCE_AND_OFFLINE_ACCEPTED / REVIEW_CLOSED / NEW_CANDIDATE_NOT_INSTALLED`.**

---

# RFQ-022 — CEO 收尾独立复核（2026-11-18，提交 9842eb8f）

**当前权威结论：`CHANGES_REQUESTED_SCOPE_REGRESSION_ONLY / P1-A_ACCEPTED / P1-B_PERSISTENCE_ACCEPTED_WITH_SCOPE_FIX / P2_ACCEPTED / SOURCE_CANDIDATE_NOT_INSTALLED`.**

三项原始 UI 缺口的主体修改已验证；测试与 manifest 证据成立。**只剩一个可直接由当前源码证明、且与此前 RFQ-021 P0 范围隔离规则冲突的收尾问题**。不重新开发模块、不重放真实订单、不触碰现有生产、不另开 RFQ，不把这个结果误读为已部署新诊断版本。

## 1. 独立复核已确认

- **审核基线**：`workbuddy/v16-rfq016-stabilization`，Executor 修复提交 **`9842eb8ffc1972db211dc008518de1f076b622c1`**。对比上轮 CEO REVIEW 后的提交：`src/gui/workbench.py`、`src/launcher/backend.py`、`src/launcher/fault_diagnostics.py`、`src/workflow/v12_store.py` 和相应测试/证据。
- **P1-A 基本闭环**：`backend.py:_defer_website_poll` 在 `recoverable_read=True` 或 `notify=False` 分支写内存故障投影；`FaultDiagnostic.next_retry_at`、`deferred=True` 及 UI“业务影响：本轮只推迟”区分瞬时只读失败与共享停止；不因该分支新增 SMTP、单笔采购事件、全局停机。backend→snapshot→真实 Tk 控件集成测试已添加。
- **P1-B 正常路径基本闭环**：`backend.py:_resolve_faults` 已改为调用 `_persist_fault_recovery`，经 `V12Store.resolve_incidents(diagnostic_code=…)` 将共享 incident 的 `active=False` 写入既有 ledger；新增站点恢复与仅 inquiry 恢复的重启读回测试。**但新增落库调用遗漏受控订单范围，见下方唯一必须修复项**。
- **P2 基本闭环**：`order_exception_block` 按订单独立 `reason_code` 提供原因/操作建议/来源行/任务号；未知时显式表示不能确定；不将全局故障臆断为单笔写入失败。部分邮件 UNKNOWN 仍由专用 `MAIL_UNKNOWN` 呈现，属于既有业务文案，不单列阻断。
- **原误报 bug 修复成立**：`_external_effect_state` 的错误 `WriteLedger` import 已替换为实际存在的 `SqliteWriteIntentJournal`；新测试覆盖空意图与无台账时不同的状态。
- **GitHub junit 独立查看**：`docs/evidence/rfq022/pytest-full.xml` 的 suite 标明 **4,309 tests / 0 failures / 0 errors / 1 skipped**，实际解析 **4,309 个 testcase**；唯一跳过据 Runner 是 Windows symlink 条件。CEO 未在 Executor 的 Windows 主机上自行运行 pytest；过去间歇性 SQLITE_READONLY 未在本次完整回归出现，原因仍不能称为百分之百排除。
- **GitHub 清单独立计算**：`docs/evidence/rfq022/INSO_V1.6-artifact-manifest-rfq022b.sha256` 文本 SHA256 **`bd81bdd4aafda0fbf8851b78ba76c1653418af10a9cb7e2c27443ba1730ccc82`**，与 Executor 报告相符；2,872 个唯一文件，无 `runtime/`；EXE 条目 **`119163b545aa9b9b2a935738fa0ac96ea12e0d2cdb4e2a7d0ca5872002161cb0`**。这验证仓库清单而**不等于 CEO 实测** Windows EXE 文件及 staging。Executor 明确说明新候选**未安装**；生产仍据其当时现场记录运行上一版 `f2ffa44f…`，此信息不是持续实时监控。
- `docs/evidence/rfq022/ui-sample.txt` 提供四种合成故障页面字段与重启投影，**不等于发生过真实故障时的生产界面截图**。真实业务 982/983 `SAVED` 属 Executor 历史现场证据，禁止重复下单验证。

## 2. 唯一必须修复：受控运行的故障恢复可能误结算其他订单 incident

**证据，逐行可核：**
- `src/launcher/backend.py:_site_recovered`（约 3186–3193）已正确在 `_enforce_scope=True` 时传 `within=scope.inquiry_ids` 给 `V12Store.resolve_incidents`。
- 新增 `backend.py:_resolve_faults`→`_persist_fault_recovery`（约 3352–3394）会对 `business_runtime` 和 `diagnostic.site` 执行 `store.resolve_incidents(module, at=…, diagnostic_code=diagnostic.code)`，**遗漏 `within`**。
- `src/workflow/v12_store.py:resolve_incidents`（约 939–967）在 `within=None` 时会结算**所有**该 module/diagnostic_code 的活动 `incident:%`，即使 incident 证据里 `inquiry_id` 指向另一个未授权订单。这重新绕过了 RFQ-021 已审的范围保护；`tests/workflow/test_rfq021_r5_incident_scope.py` 证明该保护本来就存在且很重要。
- **实际风险是条件性源码风险，不声称已在生产发生：** 例如在仅授权订单 A 的受控运行里，订单 B 存有相同 site + diagnostic code 的活动 incident；订单 A 恢复时，这条新持久化路径可能把 B 的 incident 误标 `active=False`，影响 UI/下一次故障核对。全量绿灯未覆盖此交叉路径。

**最小修正要求：** `_persist_fault_recovery` 在受控模式下将 `within=当前 scope.inquiry_ids` 传给原有 `resolve_incidents`；不受控模式保留历史语义。加一条**真的构造 A、B 两笔相同模块/相同诊断码 active incident** 的定向负测，通过 `backend._resolve_faults(site=…)` 确认：程序级及 A 变 inactive，B 保持 active，且订单告警/hold/UNKNOWN/SENT 不变。可复用现有 `test_rfq021_r5_incident_scope.py` fixture，测试应先红后绿。**不扩展到新的诊断框架或产品需求**。

## 3. 处置边界和收尾条件

- **无需重新调查 982/983、TLS 或重做 GUI 设计；不强迫现在停止旧版生产。** 修复仅影响新候选源码，修复后重新跑定向与一次完整回归、更新唯一候选 EXE/manifest 的版本和证据即可。当前 `119163b5…` 候选在改源码后只能作为历史，不能冒充修复后的最终 EXE。
- 发布/替换仍依据原维护窗口授权、完整快照/停机/一致性门禁/安全预览与生产功能可用性。**不授权**擅自停机、覆盖当前 EXE、重放 982/983、清历史 UNKNOWN/hold、变更 TP 业务口径或 main/release 分支晋升。
- 完成这个**唯一**补丁后只请求一次简短的 RFQ-022 收尾核验，着重提交变更 SHA、新全量 JUnit、负向 A/B 证据、最终候选 SHA。若没有新实质问题，CEO 应即结束本 RFQ 的代码审核，避免无谓 R6 式回环。
- 额外的**非阻断注意**：内存故障若恢复落库时发生 SQLite 异常，当前实现会保留日志但已把内存标成已恢复；下次重启仍可能看到活动 incident。应优先保持诊断诚实/可见，不把写库失败当已证明持久恢复；本轮不扩大为第二个开发任务，若定向测试恰好覆盖，可一并加强。

**最终当前状态：`RFQ022_CHANGES_REQUESTED_SCOPE_REGRESSION_ONLY / NEW_CANDIDATE_NOT_INSTALLED`.**

---

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
