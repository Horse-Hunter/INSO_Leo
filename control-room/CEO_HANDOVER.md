# INSO_Leo — CEO / Agent 无缝接管手册

> **更新时间：2026-11-07。** 本文是供 GPT、WorkBuddy、Codex、Claude 等新任 CEO/架构/Review Agent 接手的**唯一长期交接索引**，不代替 `AGENTS.md`、RFQ Task Spec、实际源码或正式发布收据。与 Executor 切换时一次性使用、接管后删除的临时 `HANDOFF*.md` **不是一类文件**。
>
> **最重要的认知**：源码HEAD、最后一次打包源码、正式EXE哈希、上次现场进程和**当前实时健康**是五种不同事实。下文的运行结果基于11月6日Executor报告，本次11月7日只访问GitHub源码/文档，**未触碰Windows现场、没有独立重跑测试、不声称现在实时在线**。
>
> **内容约束**：本文件位于仓库，任何可以读取仓库的Agent也可以读取本文；“CEO专用”是职责约定，不是技术访问权限。不得在本文放密码、Cookie、密钥、客户资料、邮件正文或秘密诊断数据。

## 0. 新Agent接管：90秒路线

1. **定位**：仓库 `Horse-Hunter/INSO_Leo`；活动版本是 `codex/v1-6-independent-scheduling`，**不是旧默认分支 `main`**。优先看本文件最顶部快照。
2. **读规则**：`AGENTS.md` → `AI_START_HERE.md` → `control-room/COORDINATION.md`；CEO读本文件，Executor按任务读 `control-room/RFQ-XXX/TASK_SPEC.md`、`docs/MODULE_INDEX.md`。
3. **核对最新事实**：取得当前分支HEAD和diff，对照 `V16_RELEASE_REPORT.md`**顶部**、`control-room/RFQ-016/{FINAL_REPORT.md,TEST_REPORT.json,EXECUTION_LOG.md}`，必要时看原 `TASK_SPEC.md`。任何“最新”字段若已变更，以新证据覆盖本文。
4. **分清身份**：CEO/Reviewer负责需求边界、独立核查与结论；Executor负责实现、测试、发布及现场证据。**Owner未明确移交前，所有可能影响V1.6业务的执行仍由原V1.6窗口负责**。GPT↔WorkBuddy换CEO窗口可直接接管决策，不能由此产生两个同时操作正式业务的Executor。
5. **现场核验（仅有权限时）**：确认本地 `git status`、worktree、正式EXE SHA256、单实例、原Chrome/9222、运行日志、原持久化状态。无法访问真实电脑时用 `NOT_VERIFIED`，**绝不把旧运行报告升级为实时事实**。
6. **执行/交付**：新任务沿用RFQ-XXX，不自行造平行框架；给Owner的实施指令**一次完整可复制**，不要让Owner拼接消息。更新当前文档只需刷新快照/风险/下一步，不把数百页执行日志复制进来。

### 不能直接访问GitHub时

若新Agent（例如WorkBuddy）只有本地仓库访问权：打开含本文件的**现有**项目工作区，先执行 `git status --short`、`git rev-parse HEAD`、`git branch --show-current`、`git worktree list --porcelain`（CLI），再读取同目录上述文件。优先复用已存在的V1.6工作树，**不为了交接新建工作树或覆盖有未提交内容的目录**。若只能看到旧本地副本或无法访问仓库，则说明缺口，不能自行假定本手册的SHA已同步。Agent不得使用Computer Use或自行编写替代GUI控制器。

## 1. 当前版本与生产状态（2026-11-07的最新文档核验）

| 层次 | 事实与状态 | 证据级别 |
| --- | --- | --- |
| Git活动分支HEAD（本轮读到） | `e3ed774c9cea0db38ee8862e8a69812935cca89c`，2026-11-06，只读报价/邮件核查的**文档提交** | `GIT_VERIFIED`；本次文档更新会产生新HEAD |
| 最后已部署的应用源码 | `92d18b093b2ad6f724dd8268989a66534b392a2c`（2026-11-06稳定性整包） | `GIT_VERIFIED+RELEASE_REPORTED`；此后至原HEAD只有两次文档提交 |
| 该源码的 `src/` / `tests/` 树 | `9125cfdb9621df32f56ef76ffc35d781e5359f6e` / `7431e791ba0f8f4db33f2f055a174b10a99de0e6` | `GIT_VERIFIED` |
| 正式EXE（上次部署报告） | `D:\Program_Leo\INSO_Leo\dist\INSO_V1.6\INSO_V1.6.exe`；SHA256 `fcdc8b70d0f1d89bc578a942fb479a547385083b623326cf452bb51eaacfad02` | `EXECUTOR_LIVE_REPORTED`；本轮未现场复测 |
| 最新可定位的回滚 | `D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.6-stability-bundle-20261106T042044Z`，报告确认新旧程序清单及一致性数据备份 | `RELEASE_REPORTED`；切勿用旧DB覆盖后来业务 |
| 最近一次真实业务观察 | 11月6日正式启动后，询价197.516s、报价211.047s、TP9.594s，三个自然轮次完成；一笔采购答复报价和源表状态经原逻辑确认；未见本轮新运行故障 | `EXECUTOR_LIVE_REPORTED`；**不是11月7日现场健康保证** |
| 本轮相关测试 | 完整3667 PASS / 1原系统symlink权限SKIP；Ruff/diff通过，2875冻结文件、16修改模块、自检/扫描通过 | `EXECUTOR_REPORTED`；CEO未独立重跑 |
| 邮件和不可逆状态 | 最新报告：原177条邮件终态保留；Owner授权的金额更正通知通过原SMTP发给原两位收件人，各一次，总SENT=179；51原登记时间、1条受保护UNKNOWN未清除 | `EXECUTOR_LIVE_REPORTED`；SMTP接收不等于收件人已阅读 |
| 当前RFQ-016控制室状态 | `REVIEW_REQUIRED / BUSINESS_RUNNING`；**实施者两路限域只读复审已过，最新整包没有独立CEO最终PASS记录** | `GIT_VERIFIED`：`control-room/COORDINATION.md` |
| 11月6日最近只读调查 | 原Shawn收件人账本SENT/attempt1；既有详细报告保存两条Findchips报价但均无库存；无库存/其他来源不可用时报告“无有效报价”与逐来源报价并存，存在**表达歧义**。未对外程序的陌生邮件措辞作来源证明 | `DOC_REPORTED`：原RFQ执行日志尾部；尚未修文案/业务逻辑 |
| 11月7日当前实时状态 | **NOT_VERIFIED**：本轮未访问生产电脑、日志/数据库、Chrome或SMTP，也未做新部署 | 本次交接维护 |

**容易误读的历史状态：** 11月1日源码 `325cd190`、旧EXE `55be53be...` 现已被11月6日正式整包取代；11月3–6早期 `HEALTH_HOLD`、`BLOCKED_NORMAL_EXIT` 均是被后续正式覆盖/观察取代的**阶段记录**。后续如出现新故障，要读取最新现场事实，不能因历史BLOCKED自动停止，也不能因上次BUSINESS_RUNNING自动宣称一切正常。

## 2. 产品价值与稳定业务合同

- **主业务**：Google 2026/SHAHAB/RFQ_BRIEF源读取 → 原单型号/品牌/数量/来源身份确认 → IC.net与六来源市场调研（IC.net、Findchips、华强HQEW、立创LCSC、正能量Bom.Ai、INSO）→ 重复采购检查/受控采购保存与Google状态回写；独立报价读取/安全更新；TP调研与邮件；V1.4订单邮件辅助。
- **周期**：询价/报价/TP各900秒原间隔（不是所有真实工作同一时间并行）；独立邮件调研收信120秒周期。**自动询价和报价最近7个上海自然日；自动TP最近1个上海自然月**；Owner手工指定单仅年龄豁免，仍需正确来源、当前状态和写入安全门禁。
- **重要通知**：原询价/采购跟进邮件有120秒详细市场报告有界等待；详细研究不可用必须如实退化为可核实基础业务信息，不能伪造当前报价/库存/金额、静默无限拖延。11月6日修复了实际入队时钟和可核实历史金额依据，已进行**特定原通知一次更正**，不得再次重复发。
- **独立邮件研究**：Owner确认“229专用邮箱收到主题以 `调研` 开头且合法MPN即触发”，任何发件人可触发（已接受的策略取舍）；执行独立研究并用原SMTP向Shawn发送。仍须保留UID历史基线、持久化与SENT/UNKNOWN。**Owner在11月2日明确排除GitHub公开性及IMAP专项作为本轮资产治理任务；历史要求不等于当前新增审计委托。**
- **不可逆操作**：Google写入、INSO保存采购、SMTP外发不允许通过重试绕过原身份/状态/受保护UNKNOWN。已发送记录不可因修复重放，不能以“邮件入队”冒充外部SMTP已接受。
- **浏览器与并发**：只有共享Chrome `127.0.0.1:9222`、同一Profile；程序持有专属页但不能误关人工页。MarketReadActors有离线框架，**默认生产未启用**；不自行切换第二Chrome/端口/Profile，也不以激进并发替换单Owner受控写入。

## 3. 生产资产地图：旧目录名字不能作为删除依据

> 下列路径依赖由原V1.6窗口于**2026-11-02**在Windows现场用只读元数据验证，11月6日发布报告称保持原junction/Profile，但**本轮11月7日没有再次独立核对**。权威现场细节：`control-room/RFQ-016/ASSET_ARCHITECTURE_AUDIT_2026-11-02.md`，发布变化查最新`V16_RELEASE_REPORT.md`。

| 资产 | 实体/关系 | 必须保护 |
| --- | --- | --- |
| 正式V1.6 | `D:\Program_Leo\INSO_Leo\dist\INSO_V1.6` | 程序及`runtime`链接、单实例；不可热覆盖 |
| 共享运行目录 | V1.6的`runtime`是指向`INSO_V1.4/runtime`的junction，V1.5也共享 | **V1.4不是无用旧目录** |
| 核心生产数据库 | V1.2 runtime链接→`D:\Program_Leo\INSO_Leo\.worktrees\v1-2-design\dist\INSO_V1.1\runtime` 内SQLite、WAL/SHM | **旧V1.2工作树仍承载现行业务账本** |
| 唯一已登录Chrome | `D:\Program_Leo\INSO_CDP\chrome-profile`（junction）→ `D:\Program_Leo\INSO_Leo\.worktrees\research-v1-production-runtime-buddy\.browser-profile\cdp` | **此旧Research目录承载唯一会话**，不能git worktree清理顺带删 |
| CDP备用资料 | `D:\Program_Leo\INSO_CDP\session-backup` | 11月2日仅约21KB，**不是已证明可恢复的完整冷备** |
| 发布回滚 | `D:\Program_Leo\INSO_Leo\dist\release-backups`；11月2日约4.03GiB，11月6日另有新备份 | 不等于全部可删，最新大小NOT_VERIFIED；不能恢复旧数据库覆盖新业务 |
| 旧发布环境 | V1.4源工作树下`.venv-release`仍用于既有发布；旧应用目录还可能含在线链接/运行数据 | 清理前必须查原真实路径、独有提交、文件锁、可用回滚 |

**直接可批准清理量：0**（截至11月2日审计；此后未知）。严禁删Profile别名/实体、Chrome、Vault/OAuth、`runtime`及junction、SQLite/WAL/SHM、mail/purchase UNKNOWN、已有发布备份、未知dirty/独有Git提交。只有所有权、引用和真实对象都查清后才能提清理方案；不要碰运行中的程序。

## 4. 快速找到代码：唯一职责入口

| 目标 | 核心入口与查证路径 |
| --- | --- |
| 启动、界面、单实例 | `src/gui/main.py`、`src/gui/app.py`、`src/gui/workbench.py` |
| 主模块/Chrome总装配 | `src/launcher/backend.py`、`src/launcher/browser_bootstrap.py`、`src/workflow/service.py` |
| Google读取/写入 | `src/launcher/google_web.py`、`src/sheets/google_reader.py`、`src/sheets/quotation_input.py`、`src/launcher/google_quote_update.py` |
| 日期、重试、业务流程 | `src/workflow/automatic_admission.py`、`v12_flow.py`、`v12_store.py`、`v13_quote_update.py` |
| INSO身份/重复/采购 | `src/launcher/inso_session.py`、`src/inso/duplicate_history.py`、`purchase_writer.py` |
| 六来源调研、现价报告 | `src/research/service.py`、`detailed.py`、`report.py`、`cdp_pages.py`、`mail_session.py` |
| 收件指令、通知与SMTP | `src/order_mail/research_requests.py`、`src/workflow/mail_research.py`、`mail_research_store.py`、`v12_notifications.py`、`src/launcher/mail_research_composition.py` |
| 报价结果语义 | `src/quotation/update_result.py` **实际被** `src/workflow/v13_quote_update.py` 调用，非闲置 |
| 可选双Actor | `src/launcher/market_actors.py`，默认OFF；不能未经实际论证打开 |
| 发布 | `scripts/build_windows_release.ps1`、`scripts/scan_release_artifact.py`、`scripts/windows_release_entry.py`、`packaging/INSO_V1.1.spec`（**名称虽旧仍被V1.6构建使用**） |

域边界详见 `docs/MODULE_INDEX.md` 与 `docs/modules/*.md`。不要根据旧V1.1/V1.2名称判定死代码，或新建第二套SMTP/数据库/发布管线。

## 5. 当前开放问题与最小路线（不是自动开工令）

| 级别 | 当前事实与风险 | 下一步/归属 |
| --- | --- | --- |
| P1 — 安全资产 | 旧Research工作树承载唯一Profile，旧V1.2工作树承载SQLite，V1.4 runtime被现版复用；自动清理可能越过junction | **原V1.6窗口**负责：未来清理入口优先做精确真实路径保护/dry-run；**不现在迁移、删目录或重启** |
| P1 — 维护 | `backend.py`职责集中；`shutdown`有多个无统一上限的`join()`；不等于已证实当前线上卡死 | 原V1.6窗口：如确有需求，从通知组合层做小步、行为不变抽取；exit/drain需以真实Owner退出为准，不用超时冒充安全退出 |
| P1 — 外部读取/写入 | 11月3–6出现Google工作表切换、SDK URL滞后、名称框/焦点未稳定、异常类型丢失与安全重试漏洞；11月6整包回归及自然轮次通过，但无法保证未来网站变化零故障 | **保留真实页面身份/期限/UNKNOWN门禁；有新故障按新现场证据精准排查**，不能恢复旧的手工写修复 |
| P2 — 报告清晰度 | 11月6只读调查确认“2条Findchips报价均无库存”与“总体无有效报价”的展示并存；措辞可能被用户误解。未证实所报陌生外部邮件措辞来自本系统 | **记录为待产品决定的展示问题**；需要改文案时由原V1.6窗口，先核实最终售价/有效性语义，不能擅改业务选择价规则 |
| P2 — 性能可观测 | 同一Chrome/CDP/CPU仍共享；默认OFF的MarketReadActors并发策略没有本轮真实收益论证；健康信息分散 | 保留现有稳定调度，若实际延迟严重，再复用`get_diagnostics`和现有日志提最小可观测增强 |
| 状态 — 独立Review | RFQ-016目前为`REVIEW_REQUIRED / BUSINESS_RUNNING`，最后一轮不是独立CEO最终PASS | Owner若要求`Review RFQ-016`，按正式差异/证据独立审核；**不因此重复打包、停止或重新部署** |
| 任务排除 | Owner之前明确不把GitHub公开性和IMAP专项作为这轮资产治理改造内容 | 仅保留既有功能背景，未经新的明确需求不自行启动这些专项 |

**不要重复做已关闭的工作**：11月2日资产体检已由CEO `AUDIT_PASS`；11月6日的整包部署、自然首轮、特定金额更正已经有正式收据。新的Agent应先核证是否确有后续事件，不再把“11月3–5曾阻断”当成今日未完成任务。

## 6. 项目资产与旁支任务（防止交接丢失）

- 之前Git跟踪的源码、测试、RFQ001–016、`tasks/`、`docs/evidence/`、模板均有长期价值；数百KB的旧报告多是**历史取证**，不是“当前任务清单”。保留历史证据；以本页作为当前索引。
- 独立非业务资产梳理**位于另一分支**：`codex/non-business-asset-audit-20261102`，截至本轮查得提交 `269176e51c02b90f5d0e1a6266118d6fda31ffe2`，包含`docs/NON_BUSINESS_ASSET_AUDIT_2026-11-02.md`、`docs/NON_BUSINESS_ASSET_INVENTORY_2026-11-02.csv`和任务记录；这些**不在当前V1.6分支**。如需合并，只选经确认纯文档内容，**不要合并其旧V1.6源码/测试基线**。
- 11月2日资产体检：`control-room/RFQ-016/ASSET_ARCHITECTURE_AUDIT_2026-11-02.md`；11月6日Google交叉复审：`control-room/RFQ-016/GOOGLE_READ_CROSS_REVIEW_2026-11-06.md`；11月6日完整事后复盘：`control-room/RFQ-016/OWNER_ACCOUNTABILITY_REPORT_2026-11-06.md`。
- 正式测试与部署事实在 `control-room/RFQ-016/TEST_REPORT.json`、`FINAL_REPORT.md`、`V16_RELEASE_REPORT.md` **最新版顶部**。历史日志的任何`HEALTH_HOLD`、`NOT_DEPLOYED`、旧SHA都必须先与最新发布比较再使用。

## 7. 对不同Agent的交接协议

**新CEO / GPT / WorkBuddy：**
- 只要拥有GitHub或现有仓库的读取能力，就能从本文件恢复项目背景；不依赖原ChatGPT聊天记忆。
- 对新的Owner意图，先核查当前事实，维护既有RFQ/决策记录。必要时独立审查实际diff、测试、业务和发布证据；Review结论只代表审核覆盖的版本。**不要把Executor自审或内部交叉审查冒充CEO最终PASS**。
- 需要指派开发时给Owner一份**完整、直接转发、明确分工的指令**，不让Owner拼接。先复用原已能工作的实现，少造文档、少重复审批。
- **不自行成为第二个生产Executor。** 如果Owner明确决定由WorkBuddy/新Codex**替换**原V1.6窗口，必须先确认旧窗口停止生产操作、保留其未提交工作和当前工作树，并完成单一责任人移交；移交成功后才允许新窗口接管V1.6任务，绝不两个窗口同时操作同一业务。

**接手实现的Executor：**
- 读 `AGENTS.md`、相关RFQ Task Spec、模块索引与所需源码，先执行 `git status / branch / worktree list`；避免覆盖未知dirty work、重复启动业务或建立新Profile。
- 先读共享CDP合同 `docs/CDP_SESSION_POLICY.md` 和 Windows发布规范 `docs/WINDOWS_RELEASE.md`；部署采用原单实例/受控退出/原备份/原PyInstaller流水线。涉及不可逆外部写入、真实邮件、未知状态不得自行扩大已授权范围。
- 对源码/测试/业务/EXE四层逐级验证；所有真实发布记录必须含**实际SHA、构建源树、EXE SHA256、备份与正常退出、业务轮次和未验证的项目**。
- Owner禁止**agent Computer Use**（截图点击、键鼠自动操作及绕行替代），允许已批准的应用自身Playwright/CDP业务运行；命令行、Git、PowerShell、Python和适用连接器按原权限。最终报告应写 `COMPUTER_USE_NOT_USED`。

## 8. 关键链接及后续维护规则

| 用途 | 路径 |
| --- | --- |
| 仓库活动分支 | `https://github.com/Horse-Hunter/INSO_Leo/tree/codex/v1-6-independent-scheduling` |
| CEO永久交接 | `control-room/CEO_HANDOVER.md`（本文件） |
| Agent原始规则 | `AGENTS.md`、`AI_START_HERE.md`、`docs/AI_WORKFLOW.md` |
| RFQ所有权、审核状态 | `control-room/COORDINATION.md`、`control-room/RFQ-016/` |
| 当前部署与测试 | `V16_RELEASE_REPORT.md`顶部、`RFQ-016/FINAL_REPORT.md`、`TEST_REPORT.json` |
| 资产/会话不可清理范围 | `docs/CDP_SESSION_POLICY.md`、`docs/WINDOWS_RELEASE.md`、`RFQ-016/ASSET_ARCHITECTURE_AUDIT_2026-11-02.md` |
| 源码模块 | `docs/MODULE_INDEX.md`、`docs/modules/` |
| 独立资产整理分支 | `codex/non-business-asset-audit-20261102`（尚未合并至V1.6） |

**什么时候更新**：新任CEO接管时先校验，不必无变化地重新提交；当实际Owner决策、RFQ审核状态、正式生产部署、重大问题的解决/重新打开、默认分支/产品职责真正变化时，才更新本文件。由当前CEO负责更新**第1节快照、第5节风险、第6节旁支状态**，保留可追踪的链接/正确完整SHA。不要日积月累追加“当前的当前”的巨大历史块，详细过程继续归原RFQ日志。

**2026-11-07本次维护声明**：已核对11月6日最新代码/测试树、正式发布报告、RFQ控制室状态、最近只读报价来源说明以及独立资产分支。**本次仅更新此长期交接文档，既不改`src/`/`tests/`，也不访问生产Windows、Chrome、SQLite或邮件，不执行部署或清理**。本文件提交后Git HEAD必然变化，但被冻结的应用源码/EXE版本不会因此改变。
