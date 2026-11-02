# INSO_Leo — CEO 持续接管手册（GPT / WorkBuddy 通用）

> **性质**：项目专属、供后续 CEO/架构审核窗口首先阅读的**永久维护索引**，不是 Executor 换手时使用、接管后删除的临时 `HANDOFF*.md`。  
> **注意权限**：此文件虽约定“CEO专用”，但存放在当前**公开 GitHub 仓库**中；文件名及文档约定不能限制仓库读者权限。严禁写入密钥、Cookie、客户具体数据、完整生产配置、敏感截图或私密聊天。需要真正限制访问时由 Owner 决定迁移至私有仓库/单独权限空间。  
> **更新基准**：2026-11-02；本次只读审计原始 HEAD `f07ed60eac7c35b4a3f1e8170f92b547947c08bc`，本次新增交接文档产生的后续文档提交**不意味着应用代码更改**。  
> **证据等级**：`CODE_VERIFIED`=GitHub可见源码；`DOC_REPORTED`=历史部署/执行报告自述；`LIVE_VERIFIED`=本次现场实测。**本次没有LIVE_VERIFIED证据**，不要把昨日报告等同于今天的在线状态。

## Owner最新执行范围与窗口归属（2026-11-02，优先于旧待办）

- **本轮明确排除**：GitHub仓库公开性/信息审查；IMAP邮箱端到端验收、触发策略及相关优化。下文保留两项的历史事实只是接管背景，**不列本轮待办、不派给任何Executor**。
- **现有V1.6窗口独占所有可能影响正常V1.6业务的事项**：正式Windows环境、CDP9222及实体登录Profile、runtime/junction、数据库、SMTP状态、性能并发及实际运行观测、`src/`和`tests/`的业务实现、打包与部署。它决定是否只读检查或另行进行变更；CEO不向新Codex窗口分派这些事情。
- **新Codex窗口仅承担非业务资产整理**：只读磁盘空间/文件引用清单（接触到运行目录时仅元数据、不打开敏感内容）、无副作用的历史文档索引/过期标签/可删除候选报告。禁止删文件、迁目录、改源码、重跑业务、构建和安装；发现任何受保护工作树/数据/链接立即移交V1.6窗口。
- **CEO本窗口已完成**：Git代码树与文档资产统计、重点代码责任/大小映射、历史/当前区分及本接管手册维护。下面各节中旧的优化建议均服从本段最新范围。

## 0. 接手窗口的90秒操作

1. 首先读本文件的**当前快照、开放问题、最近变更**；然后读 `AGENTS.md`、`AI_START_HERE.md`、`control-room/COORDINATION.md`。
2. 核对 GitHub 当前分支 `codex/v1-6-independent-scheduling` 的实际 HEAD、最新代码 diff、当前 RFQ / Owner 新指示。**GitHub 的 HEAD ≠ 正式 EXE**；必须与 `V16_RELEASE_REPORT.md` 顶部、`control-room/RFQ-016/FINAL_REPORT.md` 比较。
3. 只有在确有工具和权限时，才核对 Windows 的正式 EXE SHA256、单实例、日志、SQLite只读健康、当前业务/IMAP状态。无法接触现场时标记 `NOT_VERIFIED`，不编造在线状态。
4. 判断任务类型：新需求由 CEO 完整归档到 RFQ；`Review RFQ-XXX` 是独立源码/测试/证据审查；Executor 负责实施、测试、构建和汇报。CEO 不代替 Executor 修改业务代码，除非 Owner 另行明确。
5. 给 Owner 的最终指令要**一次完整可复制**，避免让 Owner 拼接旧指令；但不自行扩大写库、邮件、生产部署授权。
6. 结束本次 CEO 决策/Review/发布复核时，**更新本文件的当前快照、风险状态和最近变更**，核对引用SHA，保留权威历史链接；不累计成第二份巨大执行日志。

## 1. 当前真实快照（截至本次审计）

| 对象 | 当前可核实信息 | 证据性质 |
| --- | --- | --- |
| 仓库 | `https://github.com/Horse-Hunter/INSO_Leo`；API返回 `private=false` | CODE_VERIFIED |
| 活跃版本分支 | `codex/v1-6-independent-scheduling`；审计锚点 `f07ed60eac7c35b4a3f1e8170f92b547947c08bc` | CODE_VERIFIED |
| 最近正式应用源码 | `325cd19052a17c05c1d2b59a4528a2a38183b8bb`；截至审计HEAD其后只增文档 | CODE_VERIFIED + DOC_REPORTED |
| 冻结 `src/` 树 | `1e1e11776165fe0f920dd9fc4af8d0330fb8fc3f` | CODE_VERIFIED |
| 冻结 `tests/` 树 | `f87eb9dbfab149ce25adc995bf397c6cc65ae860` | CODE_VERIFIED |
| 正式安装（报告） | `D:\Program_Leo\INSO_Leo\dist\INSO_V1.6\INSO_V1.6.exe` | DOC_REPORTED；本轮未查Windows |
| EXE SHA256（报告） | `55be53be2c00079efcdb17addf930e30a7ce25cf233725bbd5f25500b1526bc3` | DOC_REPORTED |
| 上次发布状态 | 2026-11-01报告为 `BUSINESS_RUNNING`；询价、报价、TP首轮自然完成，900秒各自轮询 | DOC_REPORTED；**非2026-11-02实时值** |
| 测试结果 | 2026-11-01正式源码的专项148 PASS、全量3450 PASS / 1环境SKIP | EXECUTOR_REPORTED；CEO本轮未重跑 |
| 独立IMAP | QQ229收件；120秒检查；Owner已明确选择“**任何发件人，仅主题 `调研<MPN>`**”触发；自动研究发Shawn | CODE_VERIFIED；真实新邮件端到端仍NOT_VERIFIED |
| 邮件状态 | 发布报告保存了175 SENT、2 SUPPRESSED及两封历史研究DELIVERY_SENT、UID基线/游标；旧报告不重放 | DOC_REPORTED；当前值须现场复核 |
| 上轮执行权限 | Owner已授权原RFQ016受控部署，历史已完成；**不等于此后任意新代码自动获永久生产写入授权** | 历史Owner决议 |
| 本次审计动作 | 只读代码/文档/文件树+新CEO文档及索引；**未跑测试、未连真实Google/IMAP/SMTP/CDP、未删除资产或覆盖EXE** | 本轮动作 |

**版本辨别**：`V16_RELEASE_REPORT.md` 顶部2026-11-01版本取代其下10月/较早11月记录；`docs/evidence/v16/installation.json`、`reviewed-installed.json` 是旧安装快照，不能覆盖顶部现行发布收据。该报告体积约198KB，大量历史记录并非当前操作说明。

**唯一待自然业务闭环**：修复后的**新**邮件到达→IMAP接受UID→精确MPN→最近真实订单核对/无订单降级→六源详细调研→原SMTP真实发给Shawn→收件侧确认。这条链路在当前报告中仍为待自然触发；旧两封已发报告不能充当新版本验收。不要人为重放旧邮件或旧订单补证。

## 2. 产品与主流程地图

- **主业务**：Google Sheets（含2026、SHAHAB；RFQ_BRIEF辅助源）→识别 `未发` 与型号、品牌、数量→IC.net厂家/货量→六源Research市场价（IC.net / Findchips / 华强HQEW / 立创LCSC / 正能量Bom.Ai / INSO）→重复询价/采购草稿与受控真实保存→Google源状态写回；采购报价读取→报价比较和受控写回；TP独立调研与报告。
- **周期与资格**：询价、报价、TP三模块默认独立900秒；自动询价/报价只处理最近7个上海自然日；TP及未来个性化模块最近1个自然月；Owner明确单笔手工重跑仅年龄豁免，仍有来源/状态/写入保护。独立IMAP120秒检查。
- **业务邮件**：重要询价、采购报价待跟进优先用TP级详细六源信息；详细调研在原通知创建后120秒仍不可用时，合法原业务邮件采用明确说明“详细市场报价暂不可用／未核实”的降级文本，最终发送前再次审核订单状态与收件人。历史SENT/UNKNOWN禁止盲发。
- **邮件指令**：项目专用229邮箱的合法 `调研 MPN` 主题即可触发，不检查真实发件人（Owner明确的便利性取舍）。精确可靠匹配最新询价才附客户/数量/市场参考总价；不确定时MPN-only，不伪造数量。仅向Shawn送详细报告；技术异常按既有规则通知Owner229。
- **注意**：独立IMAP仍共享唯一Chrome/CDP9222的物理资源，但标签页/工作线程/队列管理独立；不可表述成CPU、网络和Chrome故障的物理隔离。普通Research与TP的市场价窗口/优先级不同，**不要**为了统一模板偷偷统一交易选价逻辑。

## 3. 正典代码入口与职责

| 区域 | 首先阅读 | 当前说明 |
| --- | --- | --- |
| 程序进程/UI | `src/gui/main.py`、`src/gui/app.py`、`src/gui/workbench.py` | 单实例、托盘、控制台；`main`启动process-lifetime后台服务 |
| 生产装配/调度 | `src/launcher/backend.py`、`src/launcher/v12_composition.py`、`src/workflow/` | 询价/报价/TP、邮件审核、CDP Owner、任务状态 |
| 市场调研 | `src/research/service.py`、`detailed.py`、`report.py`、`runtime.py`、`cdp_pages.py` | 六源读取、时间/FX/单价、详细HTML、精确native target |
| 数据源 | `src/sheets/google_reader.py`、`worksheet_schema.py`、`tp_brief.py` | Google表读取、行身份/数量/TP来源凭据 |
| INSO操作 | `src/inso/duplicate_history.py`、`purchase_writer.py`、`src/launcher/inso_session.py` | 站内历史、重复、草稿与保存/不确定写入 |
| 报价 | `src/workflow/v13_quote_update.py`、`v13_integration.py`、`src/launcher/google_quote_update.py` | 真正的V1.3报价实现在这里，而不是只有占位的 `src/quotation/` |
| 业务/IMAP通知 | `src/workflow/v12_notifications.py`、`v12_store.py`、`mail_research.py`、`mail_research_store.py`、`src/order_mail/research_requests.py` | 原outbox/SMTP SENT-UNKNOWN、独立IMAP UID与调研 |
| IMAP运行装配 | `src/launcher/mail_research_composition.py`、`src/research/mail_session.py` | 同一9222 CDP的专属只读标签页与独立收件/调研 |
| 登录与凭据 | `src/core/credential_provider.py`、`src/core/_vault_backend.py`、`src/research/site_login.py` | Windows Vault，绝不放明文到Git |
| 发布 | `scripts/build_windows_release.ps1`、`packaging/INSO_V1.1.spec`、`scripts/windows_release_entry.py`、`scripts/scan_release_artifact.py` | **V1.6仍复用名为V1.1的spec**；不能因文件名旧而误删 |

业务代码权威文档：`docs/MODULE_INDEX.md`、`docs/modules/{RESEARCH,WORKFLOW,SHEETS,INSO,CORE,QUOTATION}.md`、`docs/CDP_SESSION_POLICY.md`。正式运行以实际源码+运行证据为准，老文档标题不能自动充当新版本状态。

## 4. 完整资产分类（本次Git树统计）

以 `f07ed60` 的 `git/trees?recursive=1` 统计：**678个跟踪文件，Git blob合计9,399,088字节（约9.40MB，非Windows工作区或发布目录磁盘占用）**。

| 目录/资产 | 文件数 | Git blob字节 | 处置 |
| --- | ---: | ---: | --- |
| `src/` | 140 | 1,798,251 | 原生产模块，绝不按旧文件名/体积直接删除 |
| `tests/` | 179 | 1,783,525 | 回归资产，高价值保留 |
| `docs/evidence/` | 174 | 3,710,993 | 可分层索引/冷归档，**不可先删后补证据** |
| `control-room/` | 68 | 640,333 | 001–016任务规格与审核证据，保存决策 |
| `tasks/` | 64 | 818,219 | 历史任务和研究日志，标SUPERSEDED，优先索引而非删 |
| `templates/` | 15 | 26,199 | Reuse-First和AI协作规则模板，保留 |
| `scripts/` | 8 | 67,758 | 发布/测量/验收工具，逐项标记当前使用 vs 仅供历史 |
| `packaging/` | 2 | 19,770 | 当前V1.6仍引用的spec和图标，保留 |
| 顶层V15/V16报告与其他文档 | 见Git树 | 多历史阶段 | 控制当前版优先顺序、不要无限追加重复结论 |

本次没有访问Windows现场的 `dist/`、`release-backups/`、`runtime/`、`.tmp/`、`.venv-release/`、`.worktrees/` 实际体积/目录内容，**不得把Git统计当成整机瘦身结论**。

### 资产处置清单（不是删除授权）

- **保护级A（任何自动清理禁止）**：共享受保护Chrome登录profile/9222、session-backup、Vault/OAuth、当前运行EXE、`runtime`目标及junction、SQLite及WAL/SHM、采购/报价UNKNOWN、outbox SENT/UNKNOWN、用户配置、必要回滚、未合并的Git工作树和唯一证据。
- **保留级B（有价值未充分利用）**：`src/launcher/market_actors.py` 的双市场只读Actor实验框架（`ProductionBackend(market_actor_factory=None)` 默认不启用；不是生产并行成功证明）；V1.5/V1.6性能样本和 `scripts/measure_workbench.py` / `accept_workbench.py`（可作为性能基准）；`templates/lean-ai-baseline/`（跨智能体治理模板）。
- **静置级C（不要误当主线）**：`src/quotation/README.md` 仅未来版本占位；`scripts/start_v12_phase_a.ps1` 偏历史启动入口；众多历史分支、早期V1.1/V1.2/V1.5说明不能指向当前正式实例。先查引用与独有提交，再决定归档。
- **可审计瘦身级D**：`V16_RELEASE_REPORT.md`约198KB、`tasks/2026-10-27-v16-independent-scheduling.md`约301KB、`src/launcher/backend.py`约195KB、历史JSONL大样本及重复状态段落。对报告采取“当前状态摘要在顶部/旧事件只读归档+索引”，对代码采取职责小步提取，**禁止整块删除**。
- **现场可清理的前提**：只针对“Owner可证明已无引用、无独有数据且已有可用回滚”的旧stage/测试临时文件；先做精确路径/文件数量/容量/占用/重解析点审计，确认无进程使用，再按现有 `docs/WINDOWS_RELEASE.md` 同任务清理。不要在本轮审计清理。

## 5. 重大风险和当前证据

| 等级 | 风险/债务 | 证据及准确边界 | CEO下一步 |
| --- | --- | --- | --- |
| **P0 运营资产** | 唯一INSO已登录Chrome实体profile位于**旧Research工作树内部**，对工作树清理/迁移高度敏感 | `docs/CDP_SESSION_POLICY.md` 明示稳定junction `D:\Program_Leo\INSO_CDP\chrome-profile` 指向旧 `.worktrees\research-v1-production-runtime-buddy\.browser-profile\cdp`；本次未核Windows当前链接 | 先只读核对junction目标及备份可恢复性；有明确Owner授权和完整冷备后才考虑把实体目录迁至稳定非worktree位置。现在绝对不移动/删除 |
| 排除本轮 | 历史记录：GitHub公开性与证据信息风险 | 留作上下文；Owner本轮明确不做该项 | **不立项，不派任务** |
| 排除本轮 | 历史记录：独立IMAP新邮件真实端到端闭环未完成 | 原RFQ016报告有背景，当前不启动验证 | **不立项，不派任务** |
| **P1 架构集中** | `src/launcher/backend.py`约195KB、3700余行，混合调度、Browser Owner、报价、邮件、GUI投影、恢复；`src/workflow/v12_store.py`约82KB | 代码体积与实际职责可见；**复杂度高是维护风险，不是已证实线上错误** | 先做接口/状态清单和安全边界回归，分三四次无业务行为变更地抽取组合层，不整体重写 |
| 排除本轮 | 历史记录：Owner已接受仅主题触发的邮件策略 | 仅保留既定业务合同，不复议 | **不改IMAP策略** |
| **P1 共享依赖** | 独立IMAP任务仍共享Chrome/CDP/CPU/网络；Google/六源站点故障和页面资源隔离须持续观察 | `mail_research_composition.py`、`research_budget.py`、`mail_session.py`、对应fake CDP测试 | 在不扰动自然订单前提下做长期延迟/页面数量/Chrome RSS观测；不要称“完全物理独立” |
| **P1 冷热状态** | 运行中原SQLite加WAL/SHM、不可逆外部写入和SMTP UNKNOWN，跨版本恢复成本高 | `v12_store.py`、RFQ016历史、release规范 | 保留有时点一致性的备份+EXE manifest；只回滚程序，不以旧账本覆盖新业务 |
| **P2 文档过载** | 执行报告、实验结果、RFQ时间轴中旧结论易遮盖当前状态 | `V16_RELEASE_REPORT.md`顶部已有“当前/历史”区分，仍有约2435行；`COORDINATION.md`中历史状态多 | CEO_HANDOVER维持一页决策摘要+资产地图+权威链接；历史日志保持只读，旧结论加SUPERSEDED |
| **P2 未充分利用能力** | MarketReadActors已有大量并行架构与测试，但默认生产未启用 | `src/launcher/market_actors.py` 顶部明确Not enabled，Backend参数默认None | 先用实测是否超900秒/影响TP评估收益，做实验/增量门控，不直接打开双Actor |
| **P2 业务日期依据** | 普通订单没有可信原询价日期时，来源可能只提供“本地登记日期近似”，不应冒充真正客户日期 | `src/workflow/automatic_admission.py::source_date`、RESEARCH/邮件报告日期说明 | 报告继续准确标注近似；未来最好补上原询价日期的权威来源而非用更复杂的猜测兜底 |

### 特别避免的三种混淆

1. **历史截图/日志通过 ≠ 当前真实网站仍相同**；适配器可能因网页变化失效。
2. **邮件命令入队 `MAIL_QUEUED` ≠ SMTP `SENT` ≠ Shawn实际收件**，要区分三个阶段。
3. **Git HEAD / 审核通过 / EXE SHA / 当前运行进程**是四种不同事实；不能从第一项推出后面三项。

## 6. 架构优化建议（先小后大）

**第一阶段 P0：运维资产安全和证据可靠性（由原V1.6窗口执行）**
- 只读核对共享CDP实体Profile与runtime的junction/真实目录/备份和受保护工作树拓扑，防止后续瘦身误删；**不移动、不重建、不登录**。
- 由V1.6窗口确认“应用源码SHA / 已安装EXE SHA / 当前进程 / 数据库只读状态 / 最近自然轮次”的现行摘要，无法核实的字段如实标注。
- 新Codex仅整理与正式运行无关的文档资产索引；**本轮不做GitHub公开性及IMAP链路审查**。

**第二阶段 P1：拆分最重的编排职责，不动业务结果**
- 优先从 `backend.py` 提取 `NotificationCoordinator`（内容准备、最后审核、事件观察），再考虑 `BrowserRuntimeOwner`（资源与页租约）、`ModuleSchedulerFacade`（三模块调度）。每次只迁移一个稳定边界，保持现有函数入口/状态兼容与原测试不变。
- 当前SQLite统一账本是优点，**不建议立刻拆成多个数据库**；只对migration、单写入口、事务竞争与状态定义做收敛，明确UNKNOWN/SENT的全生命周期。
- 定义很轻的结构化健康快照（模块上次开始/结束/失败、IMAP最近成功检查、队列未处理数、CDP owned page count、当前SHA、未知写入数）。优先复用原日志和 `get_diagnostics`，不要创建第二个监控daemon。

**第三阶段 P2：按实测收益选择并发或文档瘦身**
- 若正常询价常常接近/超过900秒或明显挤占报价、TP，再评估MarketReadActors从默认OFF变为可控试点；先对一条新的自然订单计量，不把源码实验当已投入生产能力。
- 文档用“当前事实索引 + 只读历史附录”代替无止境叠加新大报告。大的证据按唯一测试/发布ID归档并保留hash；执行日志冷存但保持可追溯，不因Git仓库仅9.4MB就追求删除资产。
- `src/quotation/` 未来占位与旧阶段脚本仅标记低优先级，不值得为清理占位引入打包风险。

## 7. 接管决策与近期未完事项

### 本轮按窗口分开的三个后续动作

1. **V1.6窗口：保护与核对运行资产**。只读核对受保护CDP实体Profile、runtime/junction、当前正式程序和已存在回滚备份的真实关联；输出“禁止清理/可提出候选”两档，不进行任何迁移或业务操作。
2. **新Codex窗口：非业务资产瘦身预清单**。统计历史日志/证据/无引用临时stage的真实空间，列出引用和独特历史价值；只处理明确无运行关联的文档索引。任何删除候选必须先报告，不直接执行。
3. **V1.6窗口：后台架构技术方案**。为 `backend.py` 建立调用/状态/锁/数据库/浏览器边界与回归映射，选择最低风险的一个抽取点；先给建议，不在本轮直接修改业务源码或启用默认OFF的双Actor。

### Owner已明确的长期偏好

- 以结果交付和代码复用优先；不为了形式化流程无限返工。
- 新的独立功能不能影响原业务；即使详细研究失败，合法重要邮件仍需有界降级，而不是静默丢失。
- 给Codex/WorkBuddy的实施指令要**整合成一次完整可复制版本**，不要让Owner拼接多轮文字。
- Executor不得使用agent Computer Use；但程序本身原有Playwright/CDP业务能力可以正常运行。
- 独立IMAP触发保留Owner选定的subject-only策略；不要绕过其他UID、历史重放、SENT/UNKNOWN和来源写入保护。
- 生产场景需区分“源码正确、安装成功、自然业务正常、对外邮件实际送达”；Owner不希望无意义的重复审批，但不能伪造验收。

## 8. 权威资料、旧资料的使用顺序

1. **现行发布/真实状态**：`V16_RELEASE_REPORT.md` **最顶部当前发布段**；`control-room/RFQ-016/FINAL_REPORT.md`、`TEST_REPORT.json`；部署后必须另核实际程序。
2. **现行授权/审查结论**：`control-room/COORDINATION.md` 的RFQ状态行、Owner最新决策、对应 `TASK_SPEC.md` 最末权威决定。
3. **稳定的架构/安全合同**：`AGENTS.md`、`AI_START_HERE.md`、`docs/MODULE_INDEX.md`、`docs/CDP_SESSION_POLICY.md`、`docs/modules/*.md`。
4. **历史证据**：`control-room/RFQ-001..016/`、`tasks/`、`docs/evidence/v15b/`、`docs/evidence/v16/`。只有解释历史问题时按SHA回看；旧截图及旧安装JSON不覆盖现况。
5. **用户提供的Research流程Word**：`research模块工作流程.docx` 是Git忽略的**早期用户工作流程附件**（10步骤，含未发筛选、品牌识别、库存、六源报价、Excel与15分钟周期）。本轮读取了段落，但它是早期需求，不可替代当前已修改的价格逻辑、日期规则及RFQ016；附件未上传至Git，图示不被本次文本提取视为当前程序证据。

## 9. 持续维护规则（本文件是活索引，不是额外审核关卡）

- **触发**：任一CEO窗口切换、新RFQ需求确定、独立Review结果、Owner实际发布/回滚决策、确认重大事故，或仓库分支发生影响项目现状的重要变更。
- **Owner**：当前CEO窗口（GPT或WorkBuddy）负责文档，执行Agent可以提供事实与SHA但**不能单方面将其实施自述改成CEO PASS**。
- **步骤**：拉取当前Git→核对真实代码/发布证据→更新第1节快照、第5节风险状态、第7节最近事项→补充第10节简短时间线→更新明确的证据级别。可读性优先，不复制整个执行日志。
- **权威来源**：源码、冻结commit/tree、正式发布收据、RFQ Task Spec/测试证据；本文件仅索引事实和CEO判断，冲突时先核实源头而非自我引用。
- **完成证据**：保存本文件及 `AI_START_HERE.md` 索引，提交Git并报告commit SHA；不读写外部业务，不触发邮件。
- **清理**：不新建重复的CEO handover版本、临时 `HANDOFF*.md` 或自动监控；维护同一个文件，过期状态标SUPERSEDED并汇总至时间线。
- **强制判断**：后续CEO若跳过现行HEAD/EXE/Owner授权核对、把历史部署结论冒充实时状态、或清理受保护资产，应先纠正证据再给PASS；但本文件不能制造新的Owner审批环节。

## 10. 最近关键时间线（仅帮助定位，不代替完整日志）

| 日期 | 事件 | 状态 |
| --- | --- | --- |
| 2026-10-31 | RFQ016 A–F源码反复Review修正；Owner授权取消新IMAP发件人身份过滤并进行受控部署 | 历史审核，后续部署已取代未部署判断 |
| 2026-10-31 | `4b61f521` 首次上线subject-only IMAP；据报告已建立真实229 IMAP收件基线，三模块自然轮次完成 | DOC_REPORTED；新邮件Shawn收件待验证 |
| 2026-11-01 | `5bb8c941` 修复邮件研究的最近订单关联并受控覆盖 | 已被后续修正版取代 |
| 2026-11-01 | `325cd190` 修复原品牌/日期近似与报价明细，受控覆盖；全量3450 PASS/1SKIP；三模块自然轮次完成 | **最后明确的应用源/EXE部署收据** |
| 2026-11-01 | `f07ed60e` 补全最新部署与任务文档 | 仅文档提交；应用源树未变化 |
| 2026-11-02 | CEO只读资产/架构审计；创建此跨窗口永久交接索引 | 无生产代码修改、无Windows在线验收 |

---

**新CEO的第一句话应当是**：我先核对当前Git SHA、真实已安装版本、上次开放风险和Owner本轮要求，然后才判断修改/验收；不会把旧的 `REVIEW_REQUIRED` 或 `BUSINESS_RUNNING` 当成今天未经核实的事实。

## 11. 2026-11-02 本轮深化审计：可直接使用的证据与准确任务边界

### A. 代码责任密度（静态Git扫描，不等于静态分析器/实时运行）

| 模块 | 行数 | 静态可见职责与处理建议 | 归属 |
| --- | ---: | --- | --- |
| `src/launcher/backend.py` | 3711 | 约137个顶层/缩进级`def`；`ProductionBackend`包含调度、页面、邮件最后审核、故障恢复、手工动作和GUI状态。**先绘制依赖与副作用边界，再提取无行为变化的稳定接口**。 | V1.6窗口 |
| `src/workflow/v12_store.py` | 1802 | 事务迁移、通知账本、审批/UNKNOWN和多种状态在同一文件；不建议拆数据库，优先梳理持久化状态/事务责任。 | V1.6窗口 |
| `src/workflow/service.py` | 1024 | 已有 `WorkflowRuntime`/任务与资源租约所有权；不应新造第二调度器。 | V1.6窗口 |
| `src/inso/duplicate_history.py` | 1548 | 站点页面读取、严格来源及历史解析；重构涉及真站解析契约，非简单“长文件删除”。 | V1.6窗口 |
| `src/launcher/market_actors.py` | 416 | 2个固定Actor及页面回收契约，但 `ProductionBackend`默认`market_actor_factory=None`；**有价值、非默认生产**，按自然轮次耗时决策试点，不盲开。 | V1.6窗口 |
| `src/quotation/README.md` | 占位 | 真正报价逻辑在 `workflow/v13_*`、`launcher/google_quote_update.py`；避免误删当前业务模块，也不必为占位重构。 | 新Codex仅标注 |

### B. 脚本/文档资产复用与轻量瘦身证据

- **现行发布链必保留**：`scripts/build_windows_release.ps1`（支持1.6）、`packaging/INSO_V1.1.spec`（名字旧但真在用）、`scripts/scan_release_artifact.py`、`scripts/windows_release_entry.py`；`scripts/open_cdp_session.ps1`关联唯一登录会话，只归V1.6窗口。
- **历史/专项工具非默认产品入口**：`scripts/start_v12_phase_a.ps1`偏旧Phase A；`scripts/measure_workbench.py`、`scripts/accept_workbench.py`、`scripts/verify_workbench_ui.py`属于性能和UI验收能力，保留供对照而非加入日常后台。文档索引标记LEGACY或TEST_TOOL即可，不删。
- **最值得索引而不是删除的体积源**：`tasks/2026-10-27-v16-independent-scheduling.md`约308KB，`V16_RELEASE_REPORT.md`约198KB，`control-room/RFQ-016/EXECUTION_LOG.md`约62KB；`docs/evidence/v15b`及`v16`存在大型JSONL、PNG和单次性能样本。先以每个任务/发布的SHA、时间、报告和唯一证据建索引，再谈冷归档。
- **文件名不是废弃凭据**：旧V1.1 spec仍为V1.6真实入口、旧V1.4 runtime可能承载当前V1.6状态、旧Research工作树可能承载唯一Chrome实体；这三类旧名字都不能按版本号扫删。
- **本轮未查的现场容量**：`D:\\Program_Leo\\INSO_Leo\\dist`、`release-backups`、`runtime`、`.tmp`、`.venv-release`、`.worktrees`，也没有查Windows锁/真实junction，**不能声称已经替Owner清理空间**。

### C. 任务包及验收口径（不用另开平行业务窗口）

**现有V1.6窗口接收 V16-OWNER-SCOPE：** 只读资产拓扑与受保护Profile/共享runtime备份检查、真实安装版本快照、`backend.py`/SQLite/页面资源合同的最小拆分方案；**只生成诊断与建议，不进行Profile迁移、旧worktree清理、EXE覆盖、业务自动化、业务代码变更或双Actor启用**。若后续Owner决定实施架构修改，仍由此窗口执行与回归，CEO独立复审。

**新Codex窗口接收 DOC-ASSET-ONLY：** 只读文件体积/引用/重复证据与历史任务状态索引；维护与业务无关的文档和资产候选清单，不操作生产目录任何内容，也不得更改 `src/`、`tests/`、`runtime/`、发布构建脚本/Spec、GUI/CDP/DB/SMTP/IMAP。即使发现可删候选，本轮**只列精确路径+引用判据+预计回收空间+回滚证据**，禁止实际删除。经CEO确认不影响资产和旧证据后另行决定是否由资产窗口执行清理。

**CEO完成条件：** 已把这两个完整窗口分工记入持久交接；新业务事项不再误派给新Codex；已读Git元数据部分不重复采样或重建资产表；任务返回时核对现场实证并更新本文件，不把Executor自述写成实时验证。
