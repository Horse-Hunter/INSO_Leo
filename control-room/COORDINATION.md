# Executor 2026-11-21：V1.7 粘贴录单已实现、实测并构建候选（待 CEO 审核）

**状态：`V1_7_IMPLEMENTED / LIVE_DRAFT_VERIFIED / RELEASE_CANDIDATE_READY / READY_FOR_CEO_REVIEW`**
（回归结果见本节末与 [RFQ-025/EXECUTION_LOG.md](RFQ-025/EXECUTION_LOG.md) 第 12 节。）

入口：[RFQ-025/TASK_SPEC.md](RFQ-025/TASK_SPEC.md) → [EXECUTION_LOG.md](RFQ-025/EXECUTION_LOG.md) →
[FINAL_REPORT.md](RFQ-025/FINAL_REPORT.md) → 证据 [`docs/evidence/rfq025/`](../docs/evidence/rfq025/)。

- **做了什么：** 把 `CoordinatorPurchaseDraftWriter.prepare()` 的五个 AI 步骤换成 INSO 原生粘贴：
  `open_paste_entry → assert_paste_preview_fresh → set_paste_data → run_paste_import →
  read_paste_preview → validate → commit_paste_entry`。输入改为 `型号|数量|品牌`。其余业务一律未动。
- **生产路径不再依赖 AI：** `src/inso/purchase_writer.py` 内已无 `Import_ai.aspx` / `#ai_import_` /
  `ai-recognize` 任何引用（有源码守卫测试）。真实运行中 AI 端点请求数为 **0**。
- **真实页面验证（生产代码路径，非探针）：** 一次单笔 + 一次同页连续两单，均 `AI_RECOGNIZED`；
  型号/品牌/数量回读一致；解析请求恰 1 次；`#BillID` 始终为空；两个真实缺陷在过程中被修掉
  （跨帧 `filter(has=…)`、旧的页面级关窗回退会误关单据）。
- **保留的历史标识：** `PurchaseOutcome.AI_RECOGNIZED`、`ReasonCode.AI_RECOGNITION_MISMATCH`、
  `EventType.AI_RECOGNITION_*` 是 SQLite/事件目录里的持久值，未改名（需数据迁移）；用户可见文案已改为"粘贴录单"。
- **未做：** 未安装、未覆盖 `dist/INSO_V1.6`、未重启生产、未发任何真实采购单、未点 `保存`/`保存并发送`。
  V1.7 仍是前瞻版本，未经 Owner 验收不得晋升 `main`。
- **回归：** 冻结后全量 `4359 collected / 4336 passed / 22 failed / 1 skipped`。22 条失败全在 TP 模块，
  同一根因（`TpCycle.read_orders('test')` 读不到订单），改动文件里没有一条 TP/Google 模块，
  且在未改动的 `develop` 上同样复现 —— 记为既存失败集合，未删未跳。
- **候选：** `INSO_V1.7.exe` 8,508,798 B / SHA256 `5707b9c5…f253` / 2,872 文件 / 清单 `27d46b1c…3f9a`；
  `RELEASE_SCAN_OK`、`--self-check` 0、`--idle-self-check` `gui_rendered: true`。**未安装。**
- **版本：** 标识已升到 1.7（`app_paths`、`backend` 的独立调度判定、spec、构建脚本）。
  候选 EXE 路径/哈希见 FINAL_REPORT 与 `docs/evidence/rfq025/`。

---

# 此前：V1.6 已晋升为现版；V1.7 基线就绪；粘贴录单嗅探完成（CEO 一阶段 PASS）

**状态：`V1_6_PROMOTED_TO_MAIN / V1_7_BASELINE_READY / PASTE_SNIFF_COMPLETE / NO_BUSINESS_EFFECT`。**
入口：[RFQ-025/TASK_SPEC.md](RFQ-025/TASK_SPEC.md) → [EXECUTION_LOG.md](RFQ-025/EXECUTION_LOG.md) →
[FINAL_REPORT.md](RFQ-025/FINAL_REPORT.md) → 脱敏页面证据 [`docs/evidence/rfq025/paste-import-sniff.md`](../docs/evidence/rfq025/paste-import-sniff.md)。

- **三条长期线（本轮实测）：** `main` = `d954e0a5`（Owner 验收的 V1.6，`be9d0a51..d954e0a5` 纯快进）；
  `develop`（**首次真正包含 V1.6 源码**的 V1.7 基线，合并提交 `d2473a2a`，tip 见 `git log develop`）；`release/previous` = `d244241e`
  （**故意未动**，仍 `NOT_VERIFIED` —— 本项目没有经 Owner 验收的上一正式版，用 V1.1 顶替即伪造回退关系）。
  晋升前指针全部冻结为 annotated tag：`release/v1.6-official-20261121`、`release/v1.1-main-superseded-20261121`、
  `release/previous-superseded-20261121`、`preserve/sheets-v1-local-main-c3a597d9`。
- **重要事实修正：** 晋升前的 `develop` 建于 `9ad9ccb8`（11-14），此后只有政策/文档 14 个提交，
  **不含 RFQ-017…024 的任何业务修复**。本轮以合并把 V1.6 源码带入；`src/`、`tests/` 合并后与 `d954e0a5` 逐字节相同。
- **V1.7 目标（Owner）：** 用 INSO 原生"粘贴"替换 AI 录单。已查清：`#product_import_`（粘贴）与
  `#ai_import_`（AI录单）是同一行兄弟按钮；粘贴页默认映射前三列即 `型号/数量/品牌`、分隔符默认 `竖线('|')`；
  "保存数据"=`pasteImport(1)` 为**纯客户端回填**（无 AJAX、无 BillID、不发采购），且被 `importPreviewReady` 强制"先预览后保存"。
  **必须避开**列表页批量导入弹窗（同名"粘贴导入"，其"保存数据"是 `Import()` → 服务端 `action=Import` 并建单）。
- **真实链路已跑通（Owner 停机授权后）：** 登录 → 业务询价 → `新增` → `粘贴` → 写 `型号|数量|品牌` →
  `导入` → 读预览 → `保存数据` → 父表单行写入 → `返回列表` 关闭。实测：`新增` 不建单（`#BillID` 为空）；
  `导入` 只发 1 次 `POST import.ashx?action=PasteImport`；**`保存数据` 零非 GET 请求**；型号逐字节保持；
  ERP 自动补 `ProductID=P1463619`；事后列表无 11-21 新单。**未点 `保存`/`保存并发送`。**
- **实现约束（实测得出）：** `Qty` 在缓存里是字符串 `"200"` → 必须转 `int` 并校验 `>0`；
  等待条件用"预览行数 + `#win_btn__dialog12` 解禁"，禁止固定睡眠；弹窗关闭是隐藏，判断看可见性。
- **下一轮（待 Owner 指令，不自动开工）：** `workbuddy/v17-native-paste` 从 `develop` 起；
  只改 `prepare()` 的 AI 五步为粘贴五步；`src/` 至今零改动。实现阶段如需现场跑通，仍须停机或维护窗口（登录改写共享 `erp_token`）。
- **生产未受影响：** 未停机、未重启、未覆盖 V1.6；采集期间 10:43:07–10:43:10 inquiry 轮次仍 completed，
  `fatal.log` 0 字节，PID 56032/75380 未变，唯一 `runtime fault` 仍是 2026-11-20 14:29 那条已结案的。
  真实链路实测（Owner 停机后）全程无新 cycle 行，脚本未与生产调度并行。

---

# 此前状态：RFQ-024 已审核结案（结论仍有效，非当前最新动作）


**结论：`RFQ024_SOURCE_AND_EVIDENCE_PASS / PRODUCTION_RUNNING_EXECUTOR_REPORTED / NO_PENDING_QUOTE_EXECUTOR_REPORTED / REVIEW_CLOSED`。** [CEO 最终 REVIEW](RFQ-024/REVIEW.md)；[现场摘要](RFQ-024/CEO_SYNC_20261121.md)。保留正常运行版本，无新开发、发布、停机或重放任务。历史 RFQ-021/022/023 审核状态不再是当前生产状态。

- **现行执行分支：** `workbuddy/v16-rfq016-stabilization`；审核输入 HEAD `b1b5b8151bc4468698dde93146f78a90322d32c3`；修复 `64d3ec2c`（Google API 系统代理）及 `89e931bf`（外部页面租约识别）。
- **现行正式 EXE（Executor 据报装机）：** `9a0cb3d3d2101745deb014d4fa0f4c66072dc0da295923aa927f0e0387db2710`；8,505,470 B / 2,872 files；清单 `5bd7d7a792d9e4c91f32058fd8ce3affb11a7c29d387168fee65294bf26263ff`，CEO 已独立复算。全量 JUnit 4332 项，4331 PASS / 0 failures / 0 errors / 1 skip。
- **两起独立故障已接受修复：** [11-19 事件](INCIDENT-20261119.md) 最终根因是 API 绕过 Windows 系统代理（不是 CDP 失聪；早先假设已推翻）；[11-20 事件](INCIDENT-20261120.md) 外部无租约页面误判归属冲突。保持 `google_api.proxy=auto` 的既有配置、一个 Chrome/profile/9222、不操作他人标签页，真实身份/写入不明仍 fail-closed。
- **截至 11-21 10:11（Executor 现场报告，非 CEO 实机核验）：** PID 56032/75380，11-20 14:50:55 启动，约 19 小时持续运行（同步报告约 19.5 h），当日 117 模块轮次全部 completed、0 runtime fault、fatal.log 空，SHAHAB 142/143 已报价给客户，2026 尾部行已退出采购已报价积压。无“采购已报价”滞留行不等于无其他待办或历史 hold；不应重新执行已完成订单或清理旧 hold。
- **唯一待 Owner 产品决策：** 重启时中断订单标记“人工处理完成”，213/215 已人工处置。是否允许确证无写入、无 hold 的中断任务自动重排暂不修改，非当前故障/发布阻断。代理覆盖面、同名重复测试属于未来正常维护项，详见 REVIEW。
- **交接入口：** [CEO_HANDOVER.md](CEO_HANDOVER.md) 最新顶部。保持完整生产 GUI 与可自解释异常页；无新任务时不擅自开发、改配置、停机、再发采购或切换分支。现场状态在下次实际维护前重新只读核验。

## 以下为历史事故记录及旧版结案（保留追溯）

# CEO 2026-11-18 独立事故复核：CDP 页面归属故障已接受修复（当前权威状态）

**最新 CEO 结论：`INC20261118_SOURCE_AND_OFFLINE_PASS / PRODUCTION_RESUMED_EXECUTOR_REPORTED / NO_FURTHER_DEVELOPMENT_REQUIRED`.** 详见 [INCIDENT-20261118-CEO-REVIEW.md](INCIDENT-20261118-CEO-REVIEW.md)；Executor 完整现场记录 [INCIDENT-20261118.md](INCIDENT-20261118.md)。此前“待现场取证”的状态为历史，不是目前产品状态。

- **当前源码/构建：** Executor 修复 `e2eb7cceaf9aae35a4ca78e398a0e25bb6c63563`；最终 EXE `7a1ff6a6578cb07ee75584795dfa7535ff5caf5258b4b434ca58c945313313f7`；清单 `a25ca50e599c736fc98d3782d1480bd2e98464dd2cab19cac11454d24b4cca49`（CEO 已独立复算），2,872 项；JUnit 4,320 / 0 fail / 0 error / 1 skip。
- **已核验源码：** CDP targetId 只读重证最多三次、真实错配立刻 fail-closed；诊断含中文/发生阶段/子原因；归属故障有 `Browser/CDP` site，真实恢复可结算历史 incident；不再以安全预览替代生产功能。
- **现场为 Executor 13:26 左右的时点报告：** 已过既有安装门禁，新 EXE 据报运行，询价/报价/TP 完成，4 Chrome targets、0 runtime fault、8 条 write-intent SETTLED；CEO 无法独立访问当前 Windows 的 PID/EXE/账本，不宣称长期 7×24 稳定。
- **仍未知：** 11:48 首个页面归属错误的底层触发是协议超时、会话回收还是页面关闭；旧 EXE 未记录，不可虚构。新代码今后会脱敏记录子原因。
- **不要再重复修改已通过的源码或重放 982/983**，仍保护 UNKNOWN/SENT/hold、历史台账及真实订单；本次 CEO Review 不授权额外生产停机、安装或分支晋升。

# Executor 2026-11-20 结案：外部页面被当成归属丢失导致停机（已修、已装、业务恢复）

**事件记录：[INCIDENT-20261120.md](INCIDENT-20261120.md)**（现场、根因、修复、测试、门禁、报价处理结果）。

**状态：`DEFECT_CONFIRMED_AND_FIXED / INSTALLED_RUNNING / BUSINESS_RESUMED`。**

- **根因：** 扫描共享 Chrome 标签页时，把**不是本程序创建的页面**（无租约）当成"归属丢失"，`NATIVE_PAGE_LEASE_MISSING` → `CDP_PAGE_OWNERSHIP_UNCONFIRMED` → 全局停机。外部页面在共享 Chrome 里是正常状态，不应停机。
- **修复：** 新增 `page_is_owned()`；错误页/空白页收口先判租约（无租约不关、不抛）；`_require_owned_page` 对无租约页面：**纯读**改为可重试（重建自有页面），**写**仍失败关闭。身份不匹配、写入不确定、hold 一律照旧。
- **测试：** 新增 3 项；全量回归见提交。
- **现场：** EXE `9a0cb3d3…` / 清单 `5bd7d7a7…`，14:50:55 启动（PID 56032 + 75380）；14:51–14:53 三个模块全部 completed，**0 条 runtime fault**。
- **报价跟进：** 142 `UPDATED_INSERTED`；143 采购 NO STOCK；217 已变"已报价给客户"；223/224 采购价未降低（按设计不重复报价）；**213/215 因重启被判人工、219 因活动 hold，保持人工**，可用"重跑报价流程"单笔恢复。

# CEO 同步 2026-11-21：[RFQ-024/CEO_SYNC_20261121.md](RFQ-024/CEO_SYNC_20261121.md)

**状态：`FIXED / INSTALLED_RUNNING / 19.5h_ZERO_FAULT / NO_PENDING_QUOTE`。** 两次停机（API 未走系统代理、外部页面误判归属丢失）均已修复装机；今日 117 轮业务全部 completed、0 条 runtime fault；滞留报价已全部处理到"已报价给客户"。

## 此前 Executor 现场结案及协同历史（保留）

# Executor 2026-11-19 结案：32 小时"表格不可用"实为 API 连接绕过了系统代理（已修、已装、业务已恢复）

**事件记录：[INCIDENT-20261119.md](INCIDENT-20261119.md)**（现场版本、实测证据、两次根因判定、修复、负向测试、三次门禁安装、新订单处理结果）。

**状态：`ROOT_CAUSE_CORRECTED_TO_PROXY_ROUTE / FIXED / INSTALLED_RUNNING / BUSINESS_VERIFIED`。**

- **不是表格问题，也不是"CDP 被关"：** 表格在浏览器里一直可读；真正失效的是**程序自己的 Google 接口连接**——`google_api.enabled=true` 时源表读取走 `sheets.googleapis.com`，`httplib2` **直连**，而本机直连 Google 被阻断（`curl code=000`、`WinError 10060`），经 Windows 系统代理 `127.0.0.1:7890` 才通。Chrome 用系统代理，所以 Owner 看到的是"表格好好的"。
- **为什么重启、换版本都没用：** 环境与路由问题，不是进程状态；11-18 17:36 前正常是因为当时 VPN 处于 TUN 模式。
- **修复：** API 客户端按 **Windows 系统代理**连接（`google_api.proxy` = `auto`/`none`/`http://host:port`），并补齐 `httplib2` 的 CONNECT 依赖 **PySocks**（打包 `hiddenimports += ["socks"]`，已核实 EXE 归档内含 `socks`）；`GOOGLE_WAITING_RECOVERY` 文案改为"浏览器能打开表格不等于本程序能连上"。
- **顺带补的真实缺口（非本次根因）：** 页面通道失聪时旧代码永远不重连（`is_connected()` 仍为 True），现改为一次轮询最多一次丢弃自有 client 并重新 attach，绝不 kill Chrome；INSO 单据面打开时不换。新增 `GOOGLE_PAGE_UNRESPONSIVE` + `stage=`/`chain=` 日志。
- **测试：** 新增 9 项；全量 `4328 passed / 1 skipped`。
- **现场：** 终版 EXE `fa7a8544…`（清单 `cc7f4868…`），22:29:57 启动；22:30 inquiry 13.5 s → quotation 74.8 s → tp 0.55 s 全部 completed，**0 条 runtime fault**。
- **新订单：** SHAHAB 142（IMS1141-02DB）六来源均无报价 → `NO_MATCHING_PRODUCT`，按设计不发采购并发邮件；SHAHAB 143（TRJC476K016RRJ）`PARTIAL_SUCCESS` → 采购 `SAVED`。

# Executor 2026-11-18 结案：CDP 页面归属停机已定位、修复、安装并恢复业务

**事件记录：[INCIDENT-20261118.md](INCIDENT-20261118.md)**（版本核验、时间线、证据链、根因、修复、负向测试、门禁、最终现场）。

**状态：`DEFECT_CONFIRMED_AND_FIXED / TRIGGER_NOT_PROVEN / INSTALLED_RUNNING / BUSINESS_RESUMED`。**

- **现场版本先核验：** 故障发生在 `f2ffa44f…`（11-17 19:11 由 `aaac8c75` 构建），**不是** RFQ-022 候选 `0e7a985b…`（从未安装）。
- **第一故障：** 11:48:45.390 `CDP_PAGE_OWNERSHIP_UNCONFIRMED / PageTargetOwnershipError`，由报价更新边界 `_boundary_safety_fault` 包成 `V12Fault(GLOBAL_STOP)` → 全局停机；不是崩溃、不是库损坏、不是三小时机制。具体子原因（超时/会话回收/页面关闭）旧版**未记录**，故不编造。
- **程序缺陷：** `_native_page_owner` 把"身份查询没回答"当成"归属丢失"，并**永久**作废共享页面资源，没有任何重新证明的机会——所以只能重启。
- **修复：** 身份查询改为有界重证（3 次，只读协议），`TAB_TARGET_ID_MISMATCH` 仍一次即判；页面在核对中关闭视为"不再归属"；只有三次都没回答或身份不匹配才作废并保留写入保护。另把 `CDP_PAGE_*` 归到 `Browser/CDP`、补齐中文目录与 **`发生阶段：`**、让子原因进异常链（界面可见 `ValueError(TAB_TARGET_ID_MISMATCH)`）、历史"未分类"记录按目录刷新措辞。
- **"写入台账不可读"是旧版误报：** 由 `aaac8c75` 的错误 import 造成，`9842eb8f` 已修；实测写意图 8 条全部 `SETTLED`、活动告警 0，账本无损。
- **测试：** 新增 9 项（5 项 CDP 归属 + 4 项诊断），未修复源码上 3 项先红；全量 **4320 / 0 failures / 0 errors / 1 skipped**，junit `docs/evidence/rfq023/pytest-full.xml`。
- **门禁安装：** 快照 + 停机 + 库副本/校验（一次因非空 `-wal` 被拒，停机 checkpoint 后复验 PASS）+ `INSTALL_RESULT = PASS`（2,872/2,872）。最终 EXE `7a1ff6a6…` / 清单 `a25ca50e…`；旧版保留 `.prev-20261118T045741Z`、`.prev-20261118T052322Z`。
- **现场：** PID 47040 + 71872（13:23:55），inquiry 6.0 s / quotation 93.3 s / tp 0.5 s 全部 completed，启动后 0 条 `runtime fault`；11:48 那条 incident 已 `active=false`；Chrome 4 个页面稳定、未关闭他人页面、未新建登录环境。

## 既往协调记录（历史）

# Owner 新生产故障：2026-11-18 11:48:45 CDP_PAGE_OWNERSHIP_UNCONFIRMED（待现场取证）

**Owner 当场截图，仅此能确认：** 在 INSO LEO V1.6 GUI “异常与通知”页面，11-18 11:48:45 首次、最近一次均报告 `CDP_PAGE_OWNERSHIP_UNCONFIRMED`，类型 `PageTargetOwnershipError`，顶部“全局基础设施故障”，正文“程序记录到故障代码 CDP_PAGE_OWNERSHIP_UNCONFIRMED，但该代码没有已确认的中文说明”；业务影响为已停止共享业务、未触发三小时门限；外部写入说明“写入台账不可读，外部写入结果尚未确认”，用户建议保留现场、不要重复提交。**截图证实业务已全局停止而不是 EXE 进程必然退出；没有提供可证明实际根因的底层 CDP 异常链。** 下方 GLH110 / ISL9440BIRZ / RC442-128-301-3900 / HI-15850 / 4210 / I7-12700TE / I7-6700TE / NEWPART12345 / CELERON-N6210 等是既存“人工处理/报价”状态，不能将列表误认为本次新故障造成的重复写入或失败。

**已知旧版误报要先排除：** RFQ-022 源码 review 曾确认 `_external_effect_state()` 把不存在的 `WriteLedger` 误当实际读取器，导致历史已安装 EXE 即使账本干净也可能显示“写入台账不可读”；新候选源代码已改 `SqliteWriteIntentJournal`，但该候选在最新报告中**尚未安装**。因此此处的“写入台账不可读”不能直接认作账本损坏，也不能直接认定安全无风险，须只读核对真实 write-intent/SQLite 证明。

**独立源码初步复核：** `src/research/cdp_pages.py:45-46` 定义 `PageTargetOwnershipError.reason`; `bind_page_admission` 可因 `CDP_ADMISSION_REBIND_REFUSED` 抛此错；`native_page_owner/_native_page_owner` 可能因 `NATIVE_PAGE_LEASE_MISSING`、`Target.getTargetInfo` 原生 CDP 异常、`TAB_TARGET_ID_MISMATCH` 抛此错；`new_background_page` 的 `MARKET_PAGE_ADMISSION_MISMATCH` 可抛此错。后端 `_run_independent_job_scoped` 和 `_runtime_error` 对真正归属未知 fail-closed 全局停机。此机制**不得通过删除/跳过归属验证解决**，应追底层失败原因，区分临时 CDP transport 故障与真实页面身份错配/泄漏，建立可验证、无重复写副作用的精确恢复。

**委派新 DeepSeek Executor 一次性处理同一现场事件：** 先只读核对最新进程、实际运行 EXE SHA 和启动参数、日志 `runtime/logs/INSO_V1.3.log`、fatal/退出、当前 Chrome 9222 的连接和页面信息（不关闭/接管未知人工作业页面）、事件及写意图/hold；围绕 11:48:45 ±30 分钟重建异常链、发生模块/阶段、资源 owner/target/session/admission 的生灭时序。查清为什么 GUI 只有通用故障码，补稳定的脱敏归属子原因、时间线、用户操作建议。最小修复确保独占页面、正确租约与身份以及页面资源关闭/重新绑定；可自动恢复的**纯读**任务在重新证明身份后重试，真实身份未知或写入效果未知仍阻断对应危险动作而不盲目重复采购。补有针对性的并发/超时/会话回收/负测，生产正常 GUI、询价报价 TP 不能被永久安全预览禁用；经完整回归、单一可核验候选构建后提交证据。现场替换遵循已有 B3/B4、备份、逐文件校验，不覆盖在运行的生产程序，不重做 982/983，不清原有 UNKNOWN/hold；无需增加重复 CEO Review 轮次。无法证明安全时如实报真实证据与阻断。

**当前任务状态：`INCIDENT_20261118_CDP_OWNERSHIP_DIAGNOSIS_REQUESTED / CAUSE_NOT_YET_VERIFIED / NO_NEW_PRODUCTION_ACTION`。** 先前 RFQ-022 源码验收结论仍成立；本次是之后发生的独立现场故障，严禁错误归因于 RFQ-022 未安装的 `0e7a985b…` 新候选，须先查实际运行版本。

## 既往协调记录（历史）

# Executor 2026-11-17 结案：982/983 已查明、根因已修、新版已装并跑通真实业务

**CEO 收尾核验入口：`Review RFQ-022` → [`RFQ-022/REVIEW.md`](RFQ-022/REVIEW.md)。你指出的唯一范围回归已修（`_persist_fault_recovery` 补回 `within`），证据在 [`RFQ-022/EXECUTION_LOG.md`](RFQ-022/EXECUTION_LOG.md) 第 12–16 节：A/B 两笔同码 incident 的负向测试（修复前 B 被误结算 → 修复后 B 保持 active）、全量 `4311 / 0 / 0 / 1` 的 junit、新候选 `0e7a985b…` / 清单 `58c933b7…`。**

**状态：`DELIVERED_FOR_CEO_FINAL_CHECK / SCOPE_REGRESSION_FIXED / CANDIDATE_REBUILT_NOT_INSTALLED / BUSINESS_VERIFIED`。** 详细证据见 [RFQ-021/EXECUTION_LOG.md](RFQ-021/EXECUTION_LOG.md) 首节。

## CEO 收尾复核后的唯一补丁（2026-11-18）

- **范围回归已修：** `_persist_fault_recovery` 在受控运行下补 `within=scope.inquiry_ids`（与 `_site_recovered` 同一规则），不受控保留历史语义；`resolve_incidents` 语义、订单告警、hold、`UNKNOWN/SENT` 均未改。
- **负向证明：** 构造 A（授权）/B（未授权）/程序级/站点模块四条同码 incident —— 修复前 `incident:b:0` 被误结算（`assert False is True`），修复后 B 与其站点 incident 保持 active，程序级与 A 正常结算，告警/hold 计数不变；不受控回归仍全部结算。
- **全量：** `4311 / 0 failures / 0 errors / 1 skipped`，junit `docs/evidence/rfq022/pytest-full-scope-fix.xml`。
- **新候选（未安装）：** EXE `0e7a985b…`（8,480,855 B / 2,872 文件），清单 `INSO_V1.6-artifact-manifest-rfq022c.sha256`（`58c933b7…`），`--preview-self-check ok:true`、`--idle-self-check gui_rendered:true`。生产未停机、未覆盖。

## CEO REVIEW 后的一次性补修（2026-11-17 23:0x）

- **P1-A 已闭：** 读失败被推迟（不发邮件/不告警/不停模块）时也记录 GUI 诊断，含首次/最近时间、次数、**下一轮预计**、异常类、外部写入与建议；页面新增 **`业务影响：`** 行，推迟明确写"没有停止任何模块"，不再可能误报为整站中断。
- **P1-B 已闭：** 恢复不再只改内存——通过既有 `resolve_incidents(..., diagnostic_code=…)` 把同一条 incident 的 `active/recovered_at` 落库；只动 `incident:` 行，订单告警/hold/UNKNOWN/SENT 一律不碰；覆盖"仅 inquiry 恢复、quotation 仍关闭"的情形。重启视图由 `('SHEETS_READ_UNAVAILABLE',)` 变为 `()`。
- **P2 已闭：** 单笔异常改为 `order_exception_block()` + 22 条原因目录（原因/建议/位置=工作表+行号+任务号）；未分类代码明确"原因尚未确认"。
- **顺带修真 bug：** `_external_effect_state()` 误 import 不存在的 `WriteLedger`，会让每次停止都显示"写入台账不可读"；已改 `SqliteWriteIntentJournal` 并加回归。
- **证据：** 未修复源码上 7 项新测失败 → 修复后 24 项通过；冻结源码全量 `4309 / 0 failures / 0 errors / 1 skipped`，junit 在 `docs/evidence/rfq022/pytest-full.xml`；页面四态样本在 `docs/evidence/rfq022/ui-sample.txt`。
- **新候选（未安装）：** EXE `119163b5…`（8,480,578 B / 2,872 文件），清单 `docs/evidence/rfq022/INSO_V1.6-artifact-manifest-rfq022b.sha256`（`bd81bdd4…`），`--preview-self-check ok:true`、`--idle-self-check gui_rendered:true`。生产仍运行已安装的上一版，未停机、未覆盖。

- **982 / 983 不是"没读取"，而是卡在重复检查。** 两笔在 **14:37:21 正常发现并入库**（`inq_895ed99a1ec48c7d95735db8` / `inq_f39d38e94aa183a6d6676a16`，状态 `DUPLICATE_CHECKING` / `DUPLICATE_CHECK_PENDING`）。`未发`、型号/数量/客户与截图一致，W 列 `quote_date`=2026-11-17，`RFQ_BRIEF` 已有同日原始日期，七天门限成立；981 行重复表头是允许结构。卡点是重复检查要用 INSO 浏览器，而 **14:05 起每次都在 CDP/登录巡检处失败**（`BrowserBootstrapError`），982 只在 14:37/14:53/15:24/16:25 留下四次 `STARTED`。两笔**无告警、无采购事件、`workflow_write_intents`=0**，没有任何外部写入。
- **17:55 的暂停与三小时机制无关。** 当日 `GOOGLE_OUTAGE_THREE_HOURS` 记录为 0（全库唯一三小时记录是 10-24 的 INSO）；incident 为 `PROGRAM_SAFETY_PAUSED / PROGRAM_INTERNAL_STOP / MODULE_PAUSED`。第一故障是报价读表时的 **`ssl.SSLEOFError`**（TLS 中途断链，已重试约 20 s 后耗尽）：因 `_website_failure` 与 `is_isolated_source_read_error` 都把 TLS 判为"不可隔离"，`_defer_website_poll` 拒绝推迟 → `_runtime_error` 停止全部业务且**无自动恢复路径**。同一签名 11-15 已出现过（INC-20261115），属**同一缺陷复发**。"隔三小时又崩"的观感来自退避 900→1800→3600→7200 s。**两起故障无因果关系。**
- **已修：** 瞬时 TLS 断链改为有界重试 + 隔离推迟（证书/鉴权/所有权/DB 仍失败关闭）；新增"异常与通知"结构化故障投影（故障码、首次/末次时间、影响模块与连带说明、异常类+稳定子原因、是否三小时、外部写入状态、建议操作、诊断位置），写入既有 incident 的 `review_json.diagnostic`，重启后仍可读回未结清故障，恢复后标记已恢复；邮件与界面复用同一份诊断。
- **测试：** 新增 18 项定向用例；`tests/gui` 123 PASS；`tests/launcher`+`tests/gui` 合跑 **1843 PASS / 1 失败**（`test_empty_poll_defers_browser_bootstrap_until_an_inquiry_is_due[False]`，捕获原因为测试临时库只读，**单跑 2/2 通过**，与 R3/R4 记录的同类偶发一致，非本轮引入）；`ruff`、`git diff --check` PASS。
- **候选：** EXE `f2ffa44f…`（8,476,327 B / 2,872 文件），清单 `INSO_V1.6-artifact-manifest-rfq022.sha256`（`08b0e9f6…`）；`--preview-self-check` `ok:true`×2、`--idle-self-check` `gui_rendered:true`。库备份 `dist/release-backups/RFQ-022-20261117T111417Z/workflow.sqlite3`（`76bfdfd0…`，与生产库逐字节一致）。
- **已安装：** 走完既有发布闸门 —— 程序快照 `RFQ-022-pre-switch-20261117T112320Z`（`BACKUP_RESULT = PASS`）、库副本 `76bfdfd0…` 逐字节一致、`DB_VERIFY_RESULT = PASS`（`process_state = stopped (proven)`、`write_intent_state = NONE_PROVEN`）、`INSTALL_RESULT = PASS`（2,872/2,872 逐文件复算）。旧版保留为 `INSO_V1.6.exe.prev-20261117T112542Z`。
- **真实业务已跑通（19:29–19:37）：** 983 于 19:30:57、982（人工重跑后）于 19:35:55 均 `PURCHASE_DATA_SAVED`，源表 `未发 → 发给采购`，两笔邮件 SENT×2；3 条写意图全部 `SETTLED`，活动告警 0，无 runtime fault / deferred。982 在重启时被判 `INTERRUPTED_UNSENT`（停在重复检查、无派发证据）属既定安全行为，人工点「重跑采购流程」后正常完成。
- **遗留（非本轮产生、受保护不自动重试）：** `inq_71f4a2f5`（2026 行 219 GLH110）`UPDATE_RESULT_UNCONFIRMED`、`inq_d65be9df`（SHAHAB 行 137 HMC941A）`QUOTE_INPUT_WRITE_FAILED`、`unresolved:0ca37…` `SOURCE_IDENTITY_UNRESOLVED`。
- **已知功能缺口待 Owner 决定：** 两笔客户 TP 只写在 `2026` 的 `Remark`，`RFQ_BRIEF.target_price` 为空，TP 只认该列 → 不建 TP 任务。填列（金额取 `2026` 的 Remark）或改 TP 取价口径，二者选一。

## Owner 原始要求（已由上面的改造满足，保留原文）

# Owner 新增要求：异常与通知必须直接显示可诊断原因（2026-11-17）

**Owner 原话：** “顺便让程序在异常和通知那里写清楚报错原因，别每次都得用agent查”。本要求并入上面的 982/983 未处理 + 三小时暂停故障同轮执行，**不另开任务或推迟修复**。

**现有缺陷源码证据：** `src/gui/workbench.py` “异常与通知”页面目前只拼模块 `waiting_reason`，多数订单错误显示“请按已记录状态人工核对”，活动告警也只输出 `alert_type/reason_code` 并提示“请核对已记录异常”；`backend.py:_runtime_error` 即使识别故障分类，也经常把具体时间、站点、最初错误、是否三小时升级、接下来如何处理隐藏在日志中。这对 Owner 不可接受。

**正式 UI 产品验收要求（和恢复任务一起交付）：** 在“异常与通知”中按故障展示真实可用信息：首次/最近发生时间、影响模块和站点、故障分类及稳定 `reason_code`、最初可确认的异常类/安全摘要、运行到哪个阶段、受影响订单标识/来源行（仅在可证实且必要时）、本次是否属重试等待/三小时升级/停止、实际已发生/未知的外部写入和回执状态、**用户能直接执行的排查或恢复建议**、日志/事件定位标识；短句中文可读，必要时展开技术详情或复制诊断摘要。对于只是连带“已暂停”的 CDP/Credential/Research，**明确标注连带影响，而非误报独立故障**。根因无法确认时直写“尚未确认”，不编造结论。关窗重开后，未结算故障仍应可在界面看见，不得仅凭内存丢失。

**技术要求：** 复用现有 `HealthReport`、模块观察/运行日志、SQLite 告警/事件、workbench snapshot，不建第二套易漂移真相；专门设计脱敏后的 `FaultDiagnostic` 或等效结构化投影，避免将原始异常文字、凭据、Token、Cookie、客户数据、完整外部 URL 泄漏 GUI/日志。为已确认源故障和三小时升级给出前后时间线；补真实 GUI 回归和重启/恢复测试；不得以“安全模式、禁用运行按钮、暂停模块”当作解决该 UI 缺陷。原有合法写入及 `UNKNOWN/SENT` 去重保护仍在。

## 较早 Owner 现场问题及协调历史（以下仍有效）

# 2026-11-17 Owner 现场新问题：两笔“未发”未处理，GUI 显示业务暂停（待独立取证）

**当前尚未确认根因，不得以历史故障代替当前证据。** Owner 新截图：`2026` 源表 981 行为重复 RFQ 表头，982 行 `未发` 型号 `ADS1115IDGSR` Qty 1500、983 行 `未发` 型号 `G60N100BNTD` Qty 400。截图没有展示 W 列 `quote_date` 或订单创建时间。Owner 表示两笔未处理，程序约隔三小时后又“崩溃”。GUI 第二截图仍在运行/可显示：采购和报价为“需要人工处理”，总览“已暂停”，健康区 `Google Sheets 需要人工处理 / Browser/CDP 已暂停 / Credential 未核验 / Research 已暂停`；采购最近轮次 11-17 16:25:33–16:26:37，报价 17:54:45–17:55:05，TP 17:39:59–17:40:00，屏幕显示“新订单 0”。**这些是截图观察，不等于对故障原因、当前进程或外部结果的实机确认。**

**源码可核验的排查方向：** `src/sheets/worksheet_schema.py` 明确 2026 工作表允许重复块表头；`src/sheets/google_api_service.py` 源读取为 `'2026'!A1:W`（包含 982/983 行，不是固定到 980），但 `automatic_admission.py` 的 7 日原始日期准入依赖 `RFQ_BRIEF` 或已校验 W 列 `quote_date` / 历史来源证据；`backend.py:_defer_website_poll` 包含真实的连续三小时非浏览器网站故障升级为共享业务停止机制。**重复表头本身不构成已证实的异常；三小时门限是重要线索，仍须逐行对照运行日志。**

**交给唯一新 Executor：** 优先只读取证（完整 PID/启动/退出、EXE SHA、fatal/event/INSO_V1.3 日志和 GUI 运行记录），定位第一处故障时间、异常类型/站点及三小时计时；用正式 Google Sheets API **只读**核对 `2026!A975:W985`、982/983 行的精确身份和 W 日期/来源资格，查 SQLite queue/admission/UNKNOWN/hold 及已写效果。分别给出“未领取订单原因”和“共享业务暂停原因”，证明因果后做**定点修复**，保持双击即正常生产运行、全部既有功能及订单去重保障；不要用安全预览、禁用模块或强行更改表格来冒充修复。若真实安全状态未知，不盲目重复采购。执行步骤须纳入原 `EXECUTION_LOG.md`，有证据才能报告已恢复。

## 历史协调记录（按原顺序保留）

# Owner 产品红线：不可交付无法正常启动业务的“生产版”（2026-11-16）

**最新 Owner 要求：** “以后再也不许给我这种限制功能的程序”。永久执行规则已同时写入 **`develop/AGENTS.md`** 与本执行分支 **`AGENTS.md`** 的《生产版本必须可用、功能完整》。此要求优先于历史“预览 PASS 即可交付”的表述。

**目前按最新已知 Executor 报告：** V1.6 EXE 已安装且 `INSTALLED_PREVIEW_PASS`，但打开后默认处于**安全预览、业务启动按钮禁用**，没有完成真实订单（`ORDER_NOT_DONE`）。这是安装/预览通过，**不是 Owner 所要求的生产功能验收通过**。正式产品必须有 GUI 可达的正常业务模式与完整应有模块，受控单笔命令行只用于试运行，不能成为用户唯一实际操作路径。安全去重、UNKNOWN/hold、授权仍保留，但不应以全局禁用替代安全实现。

**后续 CEO/Executor：** 先遵守 `AGENTS.md` 新规则。该产品缺陷应如实记录并修复，验证 GUI 正常业务入口、功能和真实业务结果；若当前 Google Sheet 确实无合法 `未发` 订单，不得伪造订单或重复采购历史 221，也不得因此把 `PREVIEW_PASS` 写成 `PRODUCTION_ACCEPTED`。Owner 无须反复提醒同一产品要求。

## 执行现场与之前协调记录（历史详情仍保留）

# INSO LEO — Owner 最终授权：发布 V1.6 并执行真实单笔订单（2026-11-16）

## Executor 当前状态（2026-11-16 15:30 +08:00）：`FULL_BUILD_INSTALLED / RUNNING`

**Owner 指令 15:13："B，赶紧的给我完全版"** —— 撤销 RFQ-021 B7（普通启动＝安全预览），要求双击即可运行的完整生产版。已按此重建并覆盖安装。

- **新 EXE：** `1b3f3eeb58930ce0f31931cfd67865fbe4863010a5762fe09652c7a8b73d0a97`（8,461,095 B / 2,872 文件），清单 `docs/evidence/rfq021/INSO_V1.6-artifact-manifest-fullstart.sha256`（`80ddee28…`）。**这份产物不是 CEO 验收的 R5 哈希**（R5 为 `f1a0351d…`），已归档于 `build/windows-release-stage-1.6-r5`。
- **行为变更：** `src/gui/main.py` 两处——`preview = bool(args.safe_preview)`、`enforce_scope = bool(args.scoped_start)` 并把它传入 `ProductionBackend`。普通启动＝完整生产（开始按钮可用、启动即拉起邮件调研服务、所有模块按配置启用）；`--safe-preview` 仍为只读；`--scoped-start` 仍按单收窄。**B5 按单写入收窄与 B7 预览防误触随此撤销，系 Owner 明确取舍。**
- **测试：** 旧契约用例改写为 `test_a_plain_launch_is_the_full_production_program` 等 4 个；`tests/gui` + `tests/launcher` **1,826 项 PASS**；`ruff check src tests` PASS。
- **回滚材料：** `dist\release-backups\RFQ-021-fullstart-20261116T071958Z`（程序快照 `BACKUP_RESULT = PASS` + 库 `c50c3636…` + `DB_VERIFY_RESULT = PASS`）；上一版 `f1a0351d…` 保留为 `.prev-20261116T072210Z`。
- **运行中：** PID 42876（界面）+ 41784（watcher）。生产库未变、`-wal` 0 字节（未点开始，尚无业务写入）。真实订单仍未执行：`2026`/`SHAHAB` 的 `未发` 行数均为 0。
- **两个既有缺陷（非本次引入）：** ①关窗后窗口销毁但进程不退、无 `exit_requested`（Tk 主循环结束后仍有非守护线程）；②从工具会话 `Start-Process` 启动的 GUI 会随会话被回收，需用 `explorer.exe` 启动。
- 详见 [RFQ-021 EXECUTION_LOG](RFQ-021/EXECUTION_LOG.md)。

## Executor 历史状态（2026-11-16 08:1x，已被上节取代）：`INSTALLED_PREVIEW_PASS / ORDER_NOT_DONE`

**V1.6 已覆盖安装并完成安全预览验收。** Owner 于 07:57 授权"我要看到覆盖的新版程序，SHAHAB/115 不用管了是旧询价"，据此上一轮的数据库门禁阻断已解除。

- **已安装：** EXE `f1a0351dd9837239043250fa86b9d8c921620d151eef660529d85eaecca020e2`（8,461,034 B，`installed_files_verified = 2872`），旧版 `e9e3da33…` 保留为 `.prev-20261116T000225Z`；`runtime` junction 未动，生产库未动（`c50c3636…`）。
- **预览验收：** `--preview-self-check` → `ok: true`，两轮均 acquired，开始按钮「安全预览（不启动业务）」禁用，无业务/订单/邮件线程，未消费进程服务，`state = 已停止`；自检后 0 个 `INSO_V1.6` 残留进程。
- **门禁修正（已自测）：** 只改 `scripts/verify_database_backup.ps1`，新增两类显式解决方式——① `resolved_by_confirmed_save`（`SAVED` + 非空 `saved_record_ref` + 时间不早于最后一笔 `SAVE_OUTCOME_UNKNOWN`），命中 26 单；② `owner_exempt_orders`（必须同时给具名单号与 `-OwnerExemptAuthority`），本机用于 `inq_99275e8e72b43fd6616fd686`（SHAHAB/115，Owner 判定为旧询价）。缺表/查询失败/NULL、hold 只读不清、未保护的 `MANUAL_REVIEW` 等原有拒绝规则全部保留。`test_install_gates.ps1` **182 项 PASS**（原 156 项无回归）。
- **真实订单未执行（业务事实）：** 原 221 行 `FT2232H-56Q-REEL` 已 `SAVED`（`rec_440fafd…`），不得重采；现场只读扫描 `2026` 与 `SHAHAB` 的 `未发` 行数**均为 0**（现存状态只有 `已报价给客户 / 采购已报价 / 成交 / 发给采购 / 空`），而 `discover_pending` 只领取状态恰为 `未发` 的单，故当前无合法可执行的真实询价单。未伪造、未把任何行改回 `未发`。
- **未发生的外部效果：** 无 Google 写入、无 INSO 采购、无 SMTP、未接管 Chrome 9222。详见 [RFQ-021 EXECUTION_LOG](RFQ-021/EXECUTION_LOG.md)。
- **下一步（等新单）：** 新询价行以 `未发` 进入 `2026` 后，按 `--scoped-start --scope-inquiries <新单> --scope-modules inquiry --scope-writes google,inso --scope-approval OWNER-APPROVED:RFQ016-REAL-20261116 --start-inquiry` 执行单笔。

## Executor 现场执行结果（2026-11-16 01:0x，历史，已被上节取代）：`DEPLOYMENT_FAILED / NOT_INSTALLED / NO_BUSINESS_ACTION`

依本页 Owner 授权连续执行到安装前一步，**自有数据库门禁在真实生产账本上 FAIL**，安装器按设计只接受已证明状态，故未安装、未启动、未做真实订单、未产生任何外部效果。旧版 `e9e3da33…` 在位未变。

- **已实证 PASS：** 旧程序由自身运行记录证明干净退出（PID 38948，`exit_reason=owner_exit`，code 0，`2026-11-16 00:28:58` 本地）；候选逐文件复算 `2,872/2,872`、EXE `f1a0351d…`；旧程序/配置快照 `BACKUP_RESULT = PASS`；停机后生产库逐字节备份，哈希与源同为 `c50c3636…`，`integrity_check = ok`，源无 `WAL/SHM`。
- **唯一阻断（结构性）：** `DB_VERIFY_RESULT = FAIL` —— 账本无 `workflow_write_intents`（旧库，迁移仅 `1201`），`27 unprotected unknown order(s)`。其中 26 单实为 `SAVED` 且带真实 `saved_record_ref`（`SAVE_OUTCOME_UNKNOWN` 均早于 `SAVED` 约 6 秒，属重试后确认成功），但无活动告警/hold 挂靠；剩 1 单 `inq_99275e8e72b43fd6616fd686`（SHAHAB/115）为 `MANUAL_REVIEW`、`RECONCILIATION_UNREADABLE`、无回执、无 hold。**即使排除 26 单，SHAHAB/115 一单仍使门禁拒绝**；而把它变成"已证明"只能靠改 `purchase_state` 或补 hold，两者均为 Owner 明令禁止。
- **不触碰：** 未安装、未启新 EXE、未 `--safe-preview`、未跑真实订单、未动 Chrome 9222、未改生产库、未清理 SHAHAB/115 或任何 hold。详见 [RFQ-021 EXECUTION_LOG](RFQ-021/EXECUTION_LOG.md#rfq-021-r5--现场部署执行2026-11-16-0039010x-0800唯一-executor)。
- **待 Owner 决策：** ①授权处置 SHAHAB/115（补证为已结算，或补一条活动 hold）；②授权对安装门禁做最小修正（需新构建，Owner 已声明不要 R6）。二者之外无合法通过路径。
- **顺带更正：** 物理第 1 行外来表头 + 第 5 行真实契约表头的布局，在本冻结源码上**不会**导致 `SHEETS_SCHEMA_UNAVAILABLE`（`SOURCE_HEADER_ANCHOR_ROW=0` + `SOURCE_HEADER_WINDOW=10` 已容错）；2026-11-13 的"两种传输都要求第 1 行"结论对 `6a75cc93` 不成立。原目标第 221 行 `FT2232H-56Q-REEL` 现场为 `发给采购`，SQLite 为 `SAVED / rec_440fafd…`，已完成，不得重复采购。

**Owner 最新明确纠正：** “就是要跑真实订单啊，禁止再加阻断”。此授权**取代**此前只允许安装与 `--safe-preview` 的业务范围限制。Owner 已另行声明旧程序退出；Executor 必须以现场核实为准。**本次无需分阶段重复请求 CEO/Owner 批准**：在现有产品安全门禁真实通过后，唯一新 Executor 可连续执行：旧程序停机核验 → 真实配置/账本备份及校验 → 安装冻结 V1.6 → 新版安全预览 → **一笔真实且符合准入条件的 inquiry 订单**（Google Sheets API 读取及必要的 brand/status 写入、现有 INSO Save-and-Send 采购动作及回执核对）→ 证据归档。不得无故停在安全预览或增加额外 CEO Review。

- **授权范围：** `OWNER_AUTHORIZED_GATED_INSTALL_AND_ONE_REAL_INQUIRY / NOT_YET_VERIFIED`；`--scoped-start --scope-modules inquiry --scope-writes google,inso --scope-approval OWNER-APPROVED:RFQ016-REAL-20261116 --start-inquiry`；`--scope-inquiries` **只能是现场核准的一笔真实订单 inquiry_id**（不得使用占位符）。正常业务需要的真实 API/INSO 写入已经获得此处 Owner 一次性明确授权。
- **目标订单准则：** 先读 `control-room/RFQ-016/TASK_SPEC.md`、`EXECUTION_LOG.md`，通过真实 Sheets API + SQLite/INSO 核对。历史 `INSO_QUOTE/2026` 物理 221 行 `inq_e15970df104e170d93b4169b` 已据上一轮现场报告 `SAVED`、回执 `rec_440fafd372440ecf9dacabf660dd155d`；如最新事实仍证实保存，不得重复 Save/购买。若原目标已完成，**直接选择一笔真实、未发、来源身份唯一、当下符合准入且无历史发出/未知效果的新 inquiry**，无需额外请示；最多处理一笔。SHAHAB/115 `MANUAL_REVIEW` 与历史 hold 保持原样。
- **固定安装候选：** 源码 `6a75cc93130c8b7805569edfc3131f82032e22c4`，EXE SHA256 `f1a0351dd9837239043250fa86b9d8c921620d151eef660529d85eaecca020e2`，清单 `5dfce4c17e1583f401d78123d17378a527aeca78df356222e4d22ec954c33a64`，旧版预期 `e9e3da33417414abac53f8a88a67d9f053bcdaeab9730eae9ad8bd7870dffad0`；必须现场复核。不得新建候选或降级/绕过既有安装安全门禁。
- **业务路径：** 使用现有 Google Sheets Service Account API（实际确认 enabled、权限和唯一行身份），保留现有 INSO 业务保护及已授权 CDP 连接，不强夺/重置 Chrome9222，不启用未按订单隔离的 quotation/TP/notification/smtp 批处理。记录每次实际外部效果前/后证据、去重与 durable write intent、Google/INSO/SQLite 实际回执。一个 API 请求或按钮点击不等于 DONE。
- **自然失败而非“新增审批关卡”：** 已有安装 B3/B4、写入意图、源行身份、真实权限、采购去重、UNKNOWN/SENT 和 holds 等硬安全门禁仍按源码运行；有实质 FAIL/UNKNOWN 即停止该效果并上报可验证原因，不擅自删除或伪造业务状态。**没有问题时无需返回 CEO、无需多轮确认，直接完成单笔业务。**
- **完成定义：** 安装后真实 `INSTALLED_PREVIEW_PASS` 加 **ONE_REAL_INQUIRY_DONE**（Sheet API 写入回读/INSO 原生确认/SQLite 回执一致）；若业务确实无法完成则据实标 `NOT_DONE` / `UNKNOWN` 而非伪造完成。提交原有 `EXECUTION_LOG.md`、`COORDINATION.md`，记录唯一订单、证据与现场最后程序状态；无须再开 R6。
- **不授权：** 批量处理、重复采购历史 221、任意其他订单、自动清除 SHAHAB/115/UNKNOWN/hold、跨订单报价/邮件模块、修改安装源码规避门禁、强杀进程、任意回滚覆盖生产库、合并/晋升 `develop`/`main`/`release`。原有条款中的“禁止真实订单”仅在本次**单笔 inquiry 明确授权的范围内**被更新。

## 之前仅授权安装与安全预览的协调记录（历史；业务范围已被本次 Owner 明确更新）

# INSO LEO — RFQ-021 Owner 授权发布准备（2026-11-16）

**Owner 最新指令（聊天确认）：** “程序已退出，指挥新窗口发布吧”。Owner 自述旧程序已退出，**CEO/Executor 尚未独立验证 B4**。本条授权仅覆盖**本次**按 RFQ-021 手册执行现场核验、完整程序/配置快照、停机后当前账本一致性备份与只读校验、全部门禁 PASS 后安装固定 R5 候选，以及**新 EXE 的 `--safe-preview` 首次验收**；**不代表无条件通过、也不是实际部署已完成。**

- **当前工作状态：** `OWNER_AUTHORIZED_GATED_INSTALL_AND_SAFE_PREVIEW / RELEASE_HOLD / INSTALL_NOT_VERIFIED`。待 Executor 根据真实现场证据更新 `EXECUTION_LOG.md` 和本页；所有门禁有一项 FAIL / UNKNOWN，立即 `DEPLOYMENT_BLOCKED` 并报告，不得跳过、修改数据库业务状态、篡改报告或为达成 PASS 临时改代码。
- **固定候选，不准换版：** 冻结源码 `6a75cc93130c8b7805569edfc3131f82032e22c4`；EXE `f1a0351dd9837239043250fa86b9d8c921620d151eef660529d85eaecca020e2`；清单 `5dfce4c17e1583f401d78123d17378a527aeca78df356222e4d22ec954c33a64`；旧安装预期 `e9e3da33417414abac53f8a88a67d9f053bcdaeab9730eae9ad8bd7870dffad0`（须现场复核）。
- **执行入口：** `develop/AGENTS.md` 和 `AI_START_HERE.md`；本分支 `control-room/RFQ-021/REVIEW.md` 顶部 CEO R5 Final 与 `INSTALL_AND_ROLLBACK.md`。只允许**唯一新 DeepSeek Executor**接管；确认无旧窗口并行。检查 Git HEAD/worktree/status，核验安装来源、旧 EXE、watcher、进程、`runtime` junction、真实配置指向的 SQLite、WAL/SHM/打开句柄，任何不明即停。
- **必须保留的最终门禁：** 真实候选 2,872 文件哈希 PASS；旧程序及 watcher 均已退出且状态可证；备份旧程序/配置与账本身份一致；数据库报告 schema ≥4、业务不变量/意图/UNKNOWN 保护全部通过；安装器安装后逐文件校验；首次启动只能用 `INSO_V1.6.exe --safe-preview`，禁止任何真实业务启动。
- **此次明确未授权：** `--scoped-start`、`--start-inquiry`、任何真实订单、Google/INSO/SMTP 写入、Chrome9222 接管、UNKNOWN/hold/221/SHAHAB-115 的结算或清理、发生故障后冷回滚/回滚后重启、合并 `develop`、晋升 `main/release`。冷回滚（即使手册有步骤）及业务重启仍需 Owner 单独确认。脚本自动 `FAIL_RESTORED` 的安全恢复例外按原手册允许；若 `ROLLBACK_REQUIRED`，停工上报。
- **反馈：** 新窗口在每个实际动作后记录时间、路径、SHA、PASS/FAIL、生产副作用和日志路径；仅当现场安装与安全预览均有实证 PASS，才报告 `INSTALLED_PREVIEW_PASS / BUSINESS_HOLD`，否则说明真实阻断，禁止宣称发布成功。

## 先前 CEO R5 离线验收及历史状态（仍然有效，但已获得上述有限现场授权）

# INSO LEO — RFQ-021-R5 CEO 最终独立验收（2026-11-15 21:30+08:00）

**最新权威结论：`PASS_SOURCE_AND_OFFLINE_RELEASE_READY / RELEASE_HOLD / NOT_DEPLOYED`。** R5 两个 P0 的 fail-closed 源码及负向案例通过独立检查。**RFQ-021 离线开发阶段可以关闭；本结论不授予生产维护、安装、业务动作、分支晋升许可。**

- **唯一固定来源：** 冻结源码 `6a75cc93130c8b7805569edfc3131f82032e22c4`；候选 EXE SHA256 `f1a0351dd9837239043250fa86b9d8c921620d151eef660529d85eaecca020e2`；清单 SHA256 `5dfce4c17e1583f401d78123d17378a527aeca78df356222e4d22ec954c33a64`（CEO 对 GitHub 清单独立复算一致）。预补丁 R5 候选 `be7c0d3…` 已归档禁止安装。
- **测试证据：** GitHub JUnit 4,277 / 4,276 pass / 0 fail / 0 error / 1 conditional skip；Executor 报告隔离 PowerShell 门禁 156 项 PASS，CEO 检查了脚本和测试，但未实际运行 Windows 现场。
- **仍待 Owner：** B4 正常停止、实际备份与来源验证、真实安装/安全预览和冷回滚均 `NOT_VERIFIED`。维护窗口前先重新核对实时进程及本机真实 EXE/SQLite/junction，任何不满足停止。真实订单和所有外部写入仍不授权。详见 [CEO REVIEW 最新章节](RFQ-021/REVIEW.md)。
- **禁止动作保持：** 未经 Owner 分别确认，不得停/启程序、安装、改变生产 SQLite/WAL/SHM、接管 Chrome9222、真实 Google/INSO/SMTP、清理 221/SHAHAB-115/hold/UNKNOWN、合并 develop 或晋升 main/release。

## 以往 Executor 状态与 CEO 阻断（历史，已被上方新结论替代）

# INSO LEO — RFQ-021-R5 CEO 独立 Review（2026-11-15 晚）

**最新权威状态：`RFQ021_R5_CLOSURE_SUBMITTED / RELEASE_HOLD / NOT_DEPLOYED`（Executor 已闭环两处 P0，待 CEO 最终复核；CEO 上一次结论仍是 `R5 CHANGES_REQUESTED`）。** 两处安装安全失败关闭条件已按 R5 内定点修补完成：① 数据库缺表/查询失败/NULL 不再被当成 0——改为"确认的 0，或逐项核实过的旧库状态（UNKNOWN/SENT 仍被告警或 hold 保护），hold 只读不清"；② 进程枚举失败/权限不足/EXE 路径不可读一律拒绝，安装前最终复检同样适用。先补负测（旧脚本下红），再修复；冻结后全量 4,277 / 4,276 PASS / 0 FAIL / 1 SKIP，离线安装门禁 **156** 项 PASS。完整依据：[CEO REVIEW 顶部](RFQ-021/REVIEW.md)。**严禁自行停机、安装或真实业务。**

## R5 Executor 自测及历史状态（CEO 已复核，结论以顶部为准）

# INSO LEO — RFQ-021-R5 Executor 交付（2026-11-15 晚，含两处 P0 闭环补丁）

**最新权威状态（Executor 自报，不是发布许可）：`RFQ021_R5_SOURCE_AND_OFFLINE_RELEASE_READY / RELEASE_HOLD / NOT_DEPLOYED`。** R4 的五个集中阻断与 CEO R5 指出的两个 fail-closed 条件均已在 R5 内处理；CEO 独立结论仍以 [REVIEW.md](RFQ-021/REVIEW.md) 为准。

- **冻结源码：** `6a75cc93130c8b7805569edfc3131f82032e22c4`（其后的提交只含文档与证据；`src/` 自 `2c58529d` 起未变，补丁在脚本与门禁测试）。
- **唯一候选：** EXE `f1a0351dd9837239043250fa86b9d8c921620d151eef660529d85eaecca020e2`，`8,461,034` B，`2,872` 文件；清单自身 `5dfce4c17e1583f401d78123d17378a527aeca78df356222e4d22ec954c33a64`；逐文件复算 `PASS（2,872/2,872，0 missing / 0 mismatch / 0 unexpected）`。补丁前那版（`be7c0d3f…` / 清单 `a969a9bf…` / 门禁 107 项）只作历史证据，保留为 `*-pre-p0`，不得作为候选安装。
- **R4/R5 阻断处理：** ①快照配置绑定真实 runtime junction，并新增"账本路径取自实时配置"（本机实测：junction 指向的 `dist\INSO_V1.4\runtime` 里没有 `production\`，真实库在 `dist\INSO_V1.2\runtime\production\workflow.sqlite3`）；②切换后逐文件复算，回滚按快照逐文件恢复并验证，恢复中断报 `ROLLBACK_REQUIRED`；③数据库证明=源路径/进程状态/独占句柄/业务不变式/报告与安装目录及账本互绑；④**写入意图必须是确认的 0 或已证明的旧库状态**，缺表/查询失败/NULL 一律拒绝；⑤`_run_login_sweep(check_only=True)` 在预览与受控范围一律拒绝（断言未获取 Chrome）；⑥六项失败已定性为环境（测试临时树不可写）并给出可复现机制证据，全量 `4,277 collected / 4,276 passed / 0 failed / 0 errors / 1 skipped in 328.56 s`。
- **仍未验证：** 安装、停机、真实业务试运行、B4 干净停机均需 Owner 维护窗口；旧 EXE 血缘仍 `NOT_VERIFIED`。
- **继续禁止：** 停机/重启、生产安装、真实订单和外部写入、修改/备份生产 SQLite、接管 Chrome9222、清理 UNKNOWN/hold、合并 develop、晋升 main/release。

## R4 Executor 交付前历史协调记录

# INSO LEO — RFQ-021-R4 CEO 决定（2026-11-15）

**当前唯一有效 CEO 状态：`RFQ021_R3_CHANGES_REQUESTED / RELEASE_HOLD / NOT_DEPLOYED`。R4 仅授权离线补修与测试，未获部署或真实业务授权。**

- **独立 CEO 结论：** [RFQ-021/REVIEW.md](RFQ-021/REVIEW.md)（R3）。R3 Executor 的 `PASS_SOURCE_SCOPE` 只代表其自测报告，**不等于 CEO PASS**。
- **R4 集中待修：** ① `V12WorkflowCoordinator.initialize_run_state/discover_pending` 范围外历史订单的本地状态/事件/告警变更；② 安装脚本的旧版回滚快照完整性、身份和缺失 runtime junction 校验；③ `order_action_hint` 与后端受控权限一致。验收矩阵及证据在 CEO REVIEW。
- **Lean Review 生效：** 读取 `develop/AGENTS.md` 的 `Lean Review / bounded execution`；一次端到端效果路径审计、先定向测试、源码冻结后一次完整回归和最终构建，交付报告简洁链接证据；安全门禁不变。
- **历史和现场：** R3 源码 `1ef20c81`、候选 `faa3166d…` 已被 CEO 拒绝发布；2026-11-15 06:06 故障类别为 TLS EOF / `SHEETS_READ_UNAVAILABLE`，底层原因 `NOT_VERIFIED`；10:40 现场数据不代表实时进程。B3 完整一致回滚备份、B4 授权干净停机仍未满足。
- **绝对禁止：** 安装、重启旧生产、真实订单、Google/INSO/SMTP 写入、生产 SQLite/Chrome9222 操作、清理 UNKNOWN/hold，以及合并 `develop` / 晋升 `main` 或 `release/previous`。Owner 必须分别审批这些真实动作。

## R4 Executor 交付（2026-11-15 下午，待 CEO 独立复核）

**状态：`RFQ021_R4_SUBMITTED_FOR_REVIEW / RELEASE_HOLD / NOT_DEPLOYED`。** 自测通过不等于 CEO 通过。

- **源码**`2ad471e7b3c0101f18f6edae05d77522c6f71d47`（`557cde28` + 快照清单 BOM 修复）。
- **候选** EXE `199181856ac1430af5aa0bd0af37b6bf45a1bf17272413583b2bb6e27e679d32`，8,459,710 B，2,872 文件；清单 `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256`（`2de4df2f…`），逐文件 2,872/2,872 PASS。R1/R2/R3 候选与清单已归档，只认这一个。
- **三项 R4 阻断已处理：** 协调器 `initialize_run_state`/`discover_pending` 的范围过滤；安装脚本的快照完整性 / 旧版身份 / junction 目标 / 独立数据库校验；`order_action_hint` 与执行守卫一致。
- **审计另发现并修复：** 跨站点登录巡检在按钮之外还有三个自动入口；故障证据会挂到范围外订单；备份脚本写的清单带 BOM 导致好快照不可验证。
- **测试如实：** 4,260 项 / 4,253 通过 / 6 失败 / 1 跳过；6 个失败均在本轮未改动的 launcher 用例，单独运行各 5/5 通过，捕获原因为测试临时库只读；未删除或跳过任何测试。详见 [EXECUTION_LOG](RFQ-021/EXECUTION_LOG.md)。
- **仍未做：** 安装、停机、重启、真实业务、生产 DB/Chrome 一律未动；安装脚本的"通过路径"未在真实装机上跑过（生产在运行，末道门按设计拒绝）。


## R3 Executor 阶段记录（历史，不构成 CEO 通过）

**当前状态：`RFQ021_R3_PASS_SOURCE_SCOPE / RELEASE_HOLD / NOT_DEPLOYED`；事件 `INC-20261115 FAULT_CLASS_CONFIRMED / UNDERLYING_CAUSE_NOT_VERIFIED`。**

- **R3 第 1 条（P0-A 背景效果）已修**：`PurchaseCompletionActions` 现在接收范围订单集，`retry_saved_statuses` 与 `process()` 都按范围过滤；范围外 SAVED 订单即使 `google` 是已授权目标也不会触发 Google 写入或本地状态变更。显式 `inquiry_ids` 与 `RunScope` 冲突时直接拒绝（`SCOPE_INQUIRY_IDS_CONFLICT`）。
- **R3 第 2 条（P0-C）已修**：`start_login_all_sites` 在预览或任何受控范围下**一律拒绝**，与 google 权限无关；新增 `_action_in_scope` 逐个审计手动动作（`edit` 需 google、`purchase` 需 inso+google，报价/TP 因模块不可隔离永远拒绝）。
- **R3 第 3/4 条（证据与安装）已处理**：手册源码 SHA 更正为 `1ef20c81`、只用当前一个候选；R1 JSON 归档；R2 通过数由 4235 更正为 4234；安装脚本改为失败关闭（回滚快照逐文件复算 + 数据库备份文件头校验 + 显式确认），删除"旧 EXE 支持 `--safe-preview`"的错误假设；冷回滚与回滚后业务重启是两个独立审批。
- **新候选**：源码 `1ef20c81`，EXE 8,459,010 B / `faa3166d…`，2,872 文件，清单 `accd463a…`（r1/r2 已归档）；三种自检全 0，逐文件复算 2,872/2,872 PASS。
- **测试**：完整套件 4,248 项 → 4,245 通过 / 2 失败 / 1 跳过；两处失败与未修改的父提交基线相同（同一 nodeid，测试临时目录只读），未删除未跳过。新增 11 项 R3 负向/集成测试。
- **事件（第 5 条）**：`FAULT_CLASS_CONFIRMED`（`SSLEOFError` → `SHEETS_READ_UNAVAILABLE` → `MODULE_PAUSED`）、`UNDERLYING_CAUSE_NOT_VERIFIED`（为何那一刻断网）。10:40 只读复核：旧 EXE `e9e3da33…` 未变、日志停在 06:06:49、进程无 443 外连（未偷偷重试）、Google 现在可建连（302/0.40 s）、3 条 hold 与 0 活动告警未变、故障后 0 条业务事件。
- **仍未做**：未安装、未停机、未重启、未碰生产 SQLite/Chrome9222、未合并或晋升。B3/B4 仍需维护窗口。

## RFQ-021-R2 定点补修（保留记录，2026-11-15 上午）

**当前状态：`RFQ021_R2_PASS_SOURCE_SCOPE / RELEASE_HOLD / NOT_DEPLOYED`；事件 `INC-20261115 ROOT_CAUSE_CONFIRMED`。**

- **早间事件（只读取证，已结案为单一故障）**：正在跑的是旧 EXE `E9E3DA33…`（PID 38948 `--start-inquiry` + watcher 34304，2026-11-14 13:47 启动）。06:06:28 报价模块开始，06:06:48 失败（19.3 s），06:06:49 `SHEETS_READ_UNAVAILABLE / SSLEOFError` → `MODULE_PAUSED`。**不是崩溃**（fatal.log 为空、无 Windows 应用错误事件）。**无未确认外部效果**（失败在读取阶段；故障后 0 条业务事件；采购状态、3 条 V13 hold、0 活动告警均未变）。详见 [INCIDENT-20261115](INCIDENT-20261115.md)。
- **CEO 三个 P0 全部属实并已修复**：范围绑定到 `compose_v12_production`（此前传 None＝全量）；邮件服务改为 `may_start_process_services()` 双层把关；邮件/登录/单笔动作在预览与越界订单上双层拒绝。详见 [REVIEW_FOLLOWUP](RFQ-021/REVIEW_FOLLOWUP.md)。
- **能力收窄（刻意）**：报价/TP/通知无法按订单隔离，现在直接拒绝（`SCOPE_MODULE_NOT_ISOLATABLE`），`smtp` 也不能作为写入目标。受控试运行当前只支持 `inquiry` 模块 + 指定订单。
- **新候选**：源码 `1314da5d`，EXE 8,457,679 B / `74586eb2…`，2,872 文件，清单 `74ae29c7…`（旧候选 `63bcd6ce…` 与清单已归档为 `-r1`）；三种自检全 0，逐文件复算 2,872/2,872 PASS。
- **测试**：完整套件 4,237 项 → 4,235 通过 / 2 失败 / 1 跳过；两处失败与未修改的父提交基线相同（同一 nodeid），捕获原因为测试临时目录写入被拒，非本轮引入，未删除未跳过。
- **仍未做**：未安装、未停机、未重启旧程序、未碰生产 SQLite/Chrome9222、未合并或晋升。B3 完整回滚快照与 B4 干净停机仍需维护窗口。
- **下一步**：CEO 复核 RFQ-021-R2。旧程序当前仍处于"采购模块暂停"，是否重启恢复属业务动作，需 Owner 单独授权（建议先确认到 Google 的连通性）。

## RFQ-021-R1 首次交付（保留记录，2026-11-15 凌晨）

**当前状态：`RFQ021_READY_FOR_CEO_RELEASE_REVIEW / NOT_DEPLOYED / NOT_MERGED / B5-B6-B7_CLOSED_IN_SOURCE`。** 最新执行证据：[FINAL_REPORT](RFQ-021/FINAL_REPORT.md)、[EXECUTION_LOG](RFQ-021/EXECUTION_LOG.md)、[安装与回滚](RFQ-021/INSTALL_AND_ROLLBACK.md)、[JSON](../docs/evidence/rfq021/rfq021-final-candidate.json)、[候选清单](../docs/evidence/rfq021/INSO_V1.6-artifact-manifest-r1.sha256)、[JUnit](../docs/evidence/rfq021/pytest-report.xml)。

- **B7 关闭（源码+测试）**：普通双击＝安全预览，不调 `start_process_services`、不迁移、不读 IMAP、不发 SMTP、不连 CDP，开始按钮显示「安全预览（不启动业务）」且禁用；`--start-inquiry` 缺范围直接拒绝。候选 `--preview-self-check` 真机跑两轮全绿。
- **B5 关闭（源码+测试）**：`RunScope` 限制订单/模块/写入目标，写入需 `OWNER-APPROVED:` 审批串；Google 写入在唯一租约处拦截，INSO 写入在既有门外面加一层拒绝，范围只收窄不放宽；无范围不启动，不会退回 full Start。
- **B6 关闭（源码+测试）**：`workflow_write_intents` 在外部请求前落盘；进程崩溃后残留的 PENDING/UNKNOWN 会阻断同一文档的后续写入；账本不可读/不可写一律 fail closed；没有自动清理路径。
- **候选**：源码 `8cded532`，EXE 8,455,788 B / `63bcd6ce…`，2,872 文件、无 `runtime/`；清单 `d5cc3d4c…` 经脚本逐文件复算 2,872/2,872 一致。RFQ-020 的 `b358f687…` 不再作为本轮证据。
- **测试**：新增 35 项负向测试全绿；受影响模块 2,886 项全绿；完整套件 4,223 项中 4,220 通过、2 失败、1 跳过，两处失败与**未修改的父提交基线完全相同**（同一测试、同一现象），非本轮引入，未删除任何测试。
- **未做**：未安装、未停机、未正常 GUI、未业务 Start、未碰生产 SQLite/Chrome9222，未合并 `develop`、未晋升分支。B3 完整回滚快照与 B4 干净停机仍需 Owner 单独批准的维护窗口。
- **保护不变**：221 SAVED `rec_440fafd372440ecf9dacabf660dd155d` 不重下；SHAHAB/115 `MANUAL_REVIEW` 未证真实采购；3 条 V13 报价 hold 保留。
- **下一步**：CEO 复核 RFQ-021。通过后仍分三步，各自单独授权：①维护窗口内做停机+完整回滚快照；②安装候选并只做安全预览验收；③受控业务启用。

## RFQ-020 CEO Review（保留记录，2026-11-14）

**当前状态：`RFQ020_PASS_BUILD_AND_ISOLATED_SELF_CHECK / RELEASE_HOLD / NOT_INSTALLED / RFQ019_PREP_PASS / RFQ018_SOURCE_PASS`。** 最新审核：[RFQ-020 CEO Review](RFQ-020/REVIEW.md)，执行证据：[EXECUTION_LOG](RFQ-020/EXECUTION_LOG.md)、[JSON](../docs/evidence/rfq020/rfq020-build-2026-11-14.json)、[完整 SHA256 清单](../docs/evidence/rfq020/INSO_V1.6-artifact-manifest.sha256)。

- **候选存在且 staging 自检 PASS（仅按 Executor 实测）**：固定代码 `25894efa`，离线 Python3.12.10/Tk8.6.15/PyInstaller6.16.0，`-BuildOnly` 生成候选 `build/windows-release-stage-1.6/dist/INSO_V1.6`，EXE 8,436,056 B / `b358f687…`、2,872 文件、无 `runtime/`；`--self-check=0`、`--idle-self-check=0`（3秒/停止/无业务线程），扫描通过。CEO 从 GitHub 校验清单 2872 无重复文件路径，并独立重算 manifest SHA256 `c8806aea…` 匹配。**CEO 未验证 Windows EXE 实物字节，也未实机执行自检。**
- **现场不变要限时表达**：Executor 比对 22:38–22:45 自检窗口生产 EXE/PID/SQLite size+mtime/Chrome15页不变；稍后自报生产 DB mtime 和 Chrome 页数变化，属于继续运行环境的动态观察，**不能称整个 RFQ 全程无变化或独立证明变动原因**。记录中的 23:00 观测时间早于其 22:50 Git 提交不合时序，正式发布前澄清。
- **B1/B2 阶段性关闭，B3/B4/B5/B6/B7 仍发布阻断**。无完整当前旧版程序+配置+一致 DB 回滚备份、无授权干净 Stop；正常 GUI 启动带 DB/IMAP/SMTP 副作用，full Start 不限单笔，重启丢 process-local document hold，禁止安装/正常 GUI/真实业务 Start。当前旧 EXE `E9E3DA33…` 仍为旧生产候选；其源码血缘不可证。
- **保护**：221 SAVED `rec_440fafd372440ecf9dacabf660dd155d` 不重下；SHAHAB/115 `MANUAL_REVIEW/RECONCILIATION_UNREADABLE` 未证真实采购；3 条 V13 报价 hold 保留。不能操作 Chrome9222、生产 SQLite/WAL/SHM、外部 Google/INSO/SMTP 或晋升分支。
- **接管纠正**：RFQ019 REVIEW 在 Executor 分支和 develop 均存在；`docs/BRANCH_POLICY.md` 只在 develop 存在。下一个窗口明确逐分支读取，不据旧工作树缓存判断仓库全局文件缺失。候选 manifest 可检不代替真实 staging 文件 re-hash。
- **下一步建议**：一次性有界推进 B5/B6/B7 的离线受控启动保护设计与测试，**需 Owner 新授权才能改源码**；届时因源码新 SHA 需重新 build 候选。B3 回滚备份和 B4 停机另按 Owner 维护窗口批准，不自动连锁。
