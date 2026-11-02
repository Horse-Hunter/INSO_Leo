# 非业务资产台账与瘦身候选（2026-11-02）

提交CEO审核：REVIEW_REQUIRED。仅完成文档治理交付；未作CEO审查结论。

## 结论与边界

本轮释放空间 **0字节**；无删除、迁移、证据改写。可先减少阅读负担，无须处理运行资产。唯一逐字节重复证据对为685字节；去重也需保留两个阶段出处。大样本具有复核价值，不建议删除。

本报告是现有 `control-room/CEO_HANDOVER.md` 第4节资产地图的逐项附件；当前RFQ状态仍只认 `control-room/COORDINATION.md`，需求仍只认各TASK_SPEC，不另建状态体系。CEO_HANDOVER、AGENTS、AI_START_HERE及所有原始记录均未修改。本地新增台账：[逐文件CSV](NON_BUSINESS_ASSET_INVENTORY_2026-11-02.csv)，本轮Task Packet：`tasks/2026-11-02-non-business-asset-governance.md`。

## 统计口径、版本与最后使用证据

- 审计快照完整SHA：`23aaf84bdb42da9fa1bd526a97a168e60202f383`。文件、字节、引用、行号全部固定于该SHA；不是远端实时HEAD或当前程序状态。
- 根目录HEAD：`c3a597d963ed418e45f6c7c75249bdef1b8147b4`（旧main、有既有改动）；本地命名V1.6分支为 `df6646c7542bea98f2aaeb8218e9254c7873a9c2`。未切换分支，未接管/清理运行工作树；只读共享Git对象。
- Git fetch受本机代理连接失败影响，未声称同步成功。所需CEO审计对象后来已可在共享对象库读取；对象来源/其他窗口动作UNKNOWN。本报告不依赖fetch成功。
- 空间是 `git ls-tree -rl <SHA>` 的blob逻辑字节，不是NTFS占用、Git压缩对象大小、完整历史大小或生产目录容量。CRLF、压缩和磁盘分配会造成差异。
- 每文件CSV列出完整blob SHA、最后修改提交SHA/提交时间及引用文档行号。最后修改由 `git log <SHA> --name-only --no-renames` 首次命中获得；不是最后打开、执行或业务使用时间。真实最后使用为UNKNOWN，不用文件系统访问时间冒充。
- 引用扫描覆盖该快照所有可解码的Markdown、Python、PowerShell、CMD、TXT、JSON/JSONL/CSV、TOML及spec；原始样本不作为文档引用权威。区分完整路径命中与文件名/独立父目录可能引用；后者可能误匹配。同一来源的行号以逗号合并，来源之间用分号。无静态命中不能排除动态拼接、外部工具和Owner人工引用。
- A=在当前权威索引/发布报告或源码测试中有完整路径引用；B=原始证据、审核或复用资产，历史价值高；C=任务时间线适合逻辑归档；D=精确重复待核实。A不表示内容是当前事实；历史文档之间的引用不自动升为A。单一分类是处置优先级，不是删除许可。
- CSV覆盖 **332文件 / 5,551,859字节**；分类 A=36, B=233, C=61, D=2。所有行的已授权可释放空间均为0。

| 范围（互不重叠） | 文件数 | blob字节 |
| --- | ---: | ---: |
| docs/evidence | 174 | 3,710,993 |
| tasks | 64 | 818,219 |
| RFQ-001至016 | 67 | 629,206 |
| 顶层V15/V16 | 4 | 299,484 |
| templates | 15 | 26,199 |
| scripts（含受保护入口，只盘点） | 8 | 67,758 |

`control-room/`整体含69文件/668,662字节；上述RFQ范围不含COORDINATION和CEO_HANDOVER。与交接手册旧统计不同是快照增加了CEO文档，不是业务资产增长。此表未纳入src/tests/packaging、未跟踪文件及任何运行资产。

## 短索引：复用原有权威入口

以下链接固定到审计SHA，避免旧main不存在对应文件造成误读。CURRENT仅指快照内的文档权威，不代表2026-11-02现场在线。

| 标签 | 阅读入口 | 使用规则 |
| --- | --- | --- |
| CURRENT | [CEO_HANDOVER](https://github.com/Horse-Hunter/INSO_Leo/blob/23aaf84bdb42da9fa1bd526a97a168e60202f383/control-room/CEO_HANDOVER.md) 第8–12、24–54行及资产地图 | CEO维护的分工、快照与资产总入口；不复制完整快照 |
| CURRENT | [COORDINATION](https://github.com/Horse-Hunter/INSO_Leo/blob/23aaf84bdb42da9fa1bd526a97a168e60202f383/control-room/COORDINATION.md) RFQ-016行及末尾收据；[RFQ016 FINAL_REPORT](https://github.com/Horse-Hunter/INSO_Leo/blob/23aaf84bdb42da9fa1bd526a97a168e60202f383/control-room/RFQ-016/FINAL_REPORT.md) | 状态与当前交付出处；历史段落中的状态不可覆盖现行收据 |
| CURRENT | [V16_RELEASE_REPORT](https://github.com/Horse-Hunter/INSO_Leo/blob/23aaf84bdb42da9fa1bd526a97a168e60202f383/V16_RELEASE_REPORT.md#L1-L9) 第1–9行 | 只读顶部最新发布摘要；发布内容是DOC_REPORTED，不是本轮实测 |
| HISTORICAL | 同报告第10行以后 | 原时点发布现场保留；历史收据中的“当前”仅在当时有效 |
| SUPERSEDED | [V16任务](https://github.com/Horse-Hunter/INSO_Leo/blob/23aaf84bdb42da9fa1bd526a97a168e60202f383/tasks/2026-10-27-v16-independent-scheduling.md#L3) 第3行状态、267行“current authority”、2211行“Latest execution status”及旧安装下一步 | 作为现行状态/操作指令已过期；并不宣布未完成的Actor验收通过，也不废除唯一设计/审核证据 |
| HISTORICAL | 上述V16任务完整时间线 | 保留需求演进、复审及失败证据；现行业务状态转读RFQ016，不照抄旧部署指令 |
| SUPERSEDED | [RFQ016 EXECUTION_LOG](https://github.com/Horse-Hunter/INSO_Leo/blob/23aaf84bdb42da9fa1bd526a97a168e60202f383/control-room/RFQ-016/EXECUTION_LOG.md#L3) 第3行SOURCE_ONLY/NOT_DEPLOYED、43–49行旧隔离限制、61行IN_PROGRESS | 仅旧阶段状态被后续授权/收据取代；本轮不改该日志 |
| CURRENT | 同日志第333行起的第二次修正收据 | 快照内最近执行收据，简版看FINAL_REPORT；不将旧邮件待办转成本轮任务 |
| HISTORICAL | V15_RPF_BRIEF_DISCOVERY.md、V15_TP_RESEARCH_IMPLEMENTATION.md、V15_UI_UPGRADE_REPORT.md | 三份不同阶段报告，保留；V15的共线程/RELEASE_HOLD不能用于判断V16 |
| HISTORICAL | docs/evidence/v15b/、docs/evidence/v16/ | 各时点原始证据；installation.json和reviewed-installed.json是旧安装快照 |
| HISTORICAL | control-room/RFQ-001至015/及相应tasks | 原需求和验收链；不是新执行授权 |
| CURRENT | templates/lean-ai-baseline/README.md | 可复用模板入口；与项目规则相似是设计用途，不认定重复闲置 |

## 四处重点瘦身分析

1. **V16_RELEASE_REPORT.md**：198,119字节、2,434行。已有第9、19、28行历史分界，应复用；顶端仅需链接RFQ016收据，无须再抄执行细节。第11/22行的旧“当前发布”、第386–413行旧替换顺序、第516行“转CEO/无安装授权”、第1743行旧未授权安装窗口都只能按当时时点读。推荐逻辑归档正文，在现有入口直达顶部与历史锚点；本轮不移动或删改正文。
2. **tasks/2026-10-27-v16-independent-scheduling.md**：308,121字节、5,303行。第3行旧3001PASS状态、第2211行Latest与后续复审交错；第4669–4750行候选准备、第4887行授权、第4920行安装回执为连续阶段，不能把旧“未安装”作为最新阻断。第5013行单独一周报价跟进也不由本窗口启动。需求/CEO独立审核有唯一性，保留；从现有RFQ入口按时点链接，未来经原窗口确认再决定缩短重复叙述。
3. **control-room/RFQ-016/EXECUTION_LOG.md**：61,624字节、350行。开头旧状态与后续296行最终授权、316/333行后两次修正冲突；未来由其维护窗口在顶部加指向最新收据的短链接即可，保留原始记录与各时点限制。完整测试结果优先链接同目录TEST_REPORT.json，最终状态优先链接FINAL_REPORT.md，避免四处复制。此项涉及V1.6交付记录，本轮仅提出建议，不改日志或决定运行状态。
4. **docs/evidence/v15b和v16**：见下表。CPU原生JSONL、GUI样本、截图、合成及真实观测不能相互替代；先读summary/environment/complete，再按测试ID查看原样本。无新目录、无复制样本、无重新采集。

| 证据版本 | 文件数 | blob字节 |
| --- | ---: | ---: |
| docs/evidence/v15b/ | 137 | 3,283,598 |
| docs/evidence/v16/ | 37 | 427,395 |

两个大文档间以连续相同行段（至少5行且500字节）比较，共7段、37,009字节。仅作为单份重复叙述可链接化的**理论上限**，不含替代链接开销，不是已批准可删空间；涉及唯一授权、复审和原始回执的段落仍保留。主要对应位置：

| 发布报告行号 | 任务记录行号 | 相同片段字节 |
| --- | --- | ---: |
| V16_RELEASE_REPORT.md:2361–2434 | tasks/2026-10-27-v16-independent-scheduling.md:5230–5303 | 13,142 |
| V16_RELEASE_REPORT.md:1978–2102 | tasks/2026-10-27-v16-independent-scheduling.md:1830–1954 | 8,211 |
| V16_RELEASE_REPORT.md:1893–1977 | tasks/2026-10-27-v16-independent-scheduling.md:1566–1650 | 5,428 |
| V16_RELEASE_REPORT.md:2128–2184 | tasks/2026-10-27-v16-independent-scheduling.md:2496–2552 | 3,573 |
| V16_RELEASE_REPORT.md:1846–1892 | tasks/2026-10-27-v16-independent-scheduling.md:1343–1389 | 3,033 |
| V16_RELEASE_REPORT.md:2351–2360 | tasks/2026-10-27-v16-independent-scheduling.md:5218–5227 | 2,062 |

## 精确瘦身候选及后续动作（不执行）

以下数值互有重叠，**不得相加**。保留路径仅逻辑归档释放0；移出热阅读路径可减少阅读/浏览负担，但没有外部保管副本、引用迁移与批准，就没有可兑现的磁盘收益。普通git提交删除也不会清除历史对象；禁止为此改写Git历史。

| 精确候选 | 用途与引用证据 | 唯一性 / 生产关联 | 建议及预计收益 |
| --- | --- | --- | --- |
| V16_RELEASE_REPORT.md；tasks/2026-10-27-v16-independent-scheduling.md | 发布/演进；被CEO_HANDOVER和RFQ记录引用，逐行见CSV | 独有回执/审核；关联运行历史，文件本身为文档 | 保留原位，逻辑归档；合计506,240字节从默认阅读路径淡出；物理0。未来正文链接化上限见上表，由文档维护窗口确认 |
| control-room/RFQ-016/EXECUTION_LOG.md | 61,624字节；RFQ验收链、旧状态与最新收据同存 | 唯一执行证据；关联V1.6交付 | 保留，建议维护者加顶端最新收据导航；释放0 |
| docs/evidence/v15b/cpu-review/ | 34文件/1,438,613字节；V15报告/任务引用目录及样本，工具有文件名相对引用 | 性能根因复核及不同规模对照；历史采集关联程序 | 冷阅读归档标签、保持原路径；可减少1.37MiB默认浏览；物理0，不列删除候选 |
| docs/evidence/v15b/cpu-review/seeded-250/native.jsonl；docs/evidence/v15b/cpu-review/rows-250/native.jsonl；docs/evidence/v15b/cpu-review/exact-1000/native.jsonl | 均在上述cpu-review目录；451,692 / 417,982 / 224,244字节 | 三种场景，不是副本；原始时序不可只用summary替代 | 保留；三文件合计1,093,918字节只作冷归档容量，不是可删收益 |
| docs/evidence/v16/order-resource-regression.json | 280,614字节；V16验收目录引用，详见CSV | 唯一blob，原始资源回归；历史运行关联 | 保留，先看对应摘要；物理0 |
| docs/evidence/v15b/performance.json | 137,147字节；性能证据引用见CSV | 唯一blob；合成/历史数据仍需可追溯 | 保留，索引摘要；物理0 |
| docs/evidence/v15b/completion-acceptance/google-anchor-result.json；docs/evidence/v15b/release-execution/google-anchor-result.json | 各685字节；未发现完整路径引用，文件名/目录可能引用见CSV，尚不能确认对应哪个副本 | 两路径blob相同；但归属不同阶段，不能推断重复采集 | D，仅未来删除候选之一；上限685字节（一个副本），需先确认来源一致、保留阶段映射并修引用；本轮0 |
| tasks/（逐文件见CSV） | 64文件/818,219字节；历史研究/开发及审核指令 | 多数有唯一决策；含旧业务操作指令 | A保留现有入口；C逻辑归档；不凭无引用删任务；物理0 |
| control-room/RFQ-001至015/ | 原需求与审核链，分RFQ容量见下表 | 验收/授权证据独有；与产品历史有关 | 全保留；按现有COORDINATION进入，不建第二状态表；物理0 |
| 顶层三份V15报告 | 分阶段发现/实现/UI；CSV列出各自精确字节与引用 | 非互相替代；报告时点已过 | HISTORICAL保留；未来重复技术细节改为来源链接需维护者确认；本轮0 |
| templates/lean-ai-baseline/ | 15文件/26,199字节；项目治理明确要求复用 | 治理模板，不是无用复制 | 保留；物理0 |
| scripts/accept_workbench.py；scripts/measure_workbench.py；scripts/verify_workbench_ui.py；docs/evidence/下全部.py | 手动诊断/历史探针；逐项用途/引用/大小见CSV | 可能打开程序、采样或浏览器，不能因非默认入口就认定无运行影响 | 保留TEST_TOOL；不运行、不迁移，任何变更交原V1.6窗口；本轮0 |
| scripts/build_windows_release.ps1；scripts/windows_release_entry.py；scripts/scan_release_artifact.py；scripts/open_cdp_session.ps1；scripts/start_v12_phase_a.ps1 | 正式发布/启动/CDP与历史Phase入口 | 与生产基础设施关联，旧版本名不是闲置证据 | 禁止本窗口操作；包括Phase入口的任何退役决定均移交原V1.6窗口；收益UNKNOWN |

## RFQ逐项容量

此处只列资产量，不复制/改变COORDINATION中的业务状态。各RFQ每个文件及其引用、最后修改SHA均在CSV。

| RFQ | 文件数 | blob字节 | 用途/处置 |
| --- | ---: | ---: | --- |
| RFQ-001 | 5 | 13,719 | 需求、执行、交付/复审出处；保留 |
| RFQ-002 | 6 | 98,306 | 需求、执行、交付/复审出处；保留 |
| RFQ-003 | 4 | 43,160 | 需求、执行、交付/复审出处；保留 |
| RFQ-004 | 4 | 46,411 | 需求、执行、交付/复审出处；保留 |
| RFQ-005 | 4 | 28,008 | 需求、执行、交付/复审出处；保留 |
| RFQ-006 | 4 | 105,594 | 需求、执行、交付/复审出处；保留 |
| RFQ-007 | 4 | 23,758 | 需求、执行、交付/复审出处；保留 |
| RFQ-008 | 5 | 41,151 | 需求、执行、交付/复审出处；保留 |
| RFQ-009 | 4 | 22,552 | 需求、执行、交付/复审出处；保留 |
| RFQ-010 | 4 | 20,907 | 需求、执行、交付/复审出处；保留 |
| RFQ-011 | 3 | 11,917 | 需求、执行、交付/复审出处；保留 |
| RFQ-012 | 3 | 7,182 | 需求、执行、交付/复审出处；保留 |
| RFQ-013 | 3 | 7,193 | 需求、执行、交付/复审出处；保留 |
| RFQ-014 | 6 | 27,664 | 需求、执行、交付/复审出处；保留 |
| RFQ-015 | 4 | 6,602 | 需求、执行、交付/复审出处；保留 |
| RFQ-016 | 4 | 125,082 | 需求、执行、交付/复审出处；保留 |

## 不能动与待核实清单

- **原V1.6窗口独占**：runtime、dist、release-backups、worktree、CDP/Profile/junction、SQLite/WAL/SHM、Vault/OAuth、正式构建/启动/发布工具、回滚及并发架构。未深入扫描或打开这些目录，容量、锁定、链接拓扑、备份恢复性均UNKNOWN；不据此提出可删结论。
- 根目录既有未跟踪docx/xlsx/pdf/html等不属于本Git快照盘点范围，可能是业务/客户资料；不打开、不加入台账、不删除，是否属于独立非业务资产由Owner/CEO确认。
- 真实“最后使用”UNKNOWN；CSV最后修改和静态引用仅是证据下限。未来若考虑任何删除，先由相应维护窗口确认动态工具/人工引用、独有审核证据和保管要求；本轮没有删除授权。
- 精确重复685字节的两个JSON文件：CEO先确认同一采集结果在两阶段的含义；未确认前两份均保留。没有其他同blob副本，不代表不存在语义重复。
- 上述文档重复行仅提出链接化位置；是否可以改写、真正净节省多少需原文维护者核实。本轮完整保留历史证据，不通过压缩/转格式绕过保留要求。
- 不做GitHub公开性检查和IMAP专项，不从旧待办恢复业务工作。

## 验证与CEO接收

使用只读Git树、blob、历史和静态引用完成统计；没有运行任何盘点到的Python/PowerShell工具，没有业务测试、打包、网络业务、进程操作或Computer Use。CSV保存路径/大小/blob/引用/最后修改等元数据，没有复制原始业务样本。

验证通过：332个路径覆盖完整、无重复路径，5,551,859字节总和与逐项blob一致；3,004处引用行号有效，完整路径命中已逐行复核；最后修改SHA格式、分类、0删除收益及新增Markdown空白检查通过。审阅了新增全文及Git diff；既有 `.gitignore`、`src/core/README.md`、`tests/core/README.md` 改动保留。CSV按来源合并引用行号，避免重复路径扩大台账；报告约17KB，明细约214KB，仅作审核附件。

CEO审核本报告及CSV的归档建议即可。接收时仅将本报告、CSV和Task Packet纳入目标版本的文档变更，核对路径与固定SHA；不覆盖业务文件、不合并旧main、不要求原V1.6窗口做清理。接收后CEO可在自己维护的CEO_HANDOVER资产地图加本附件链接；本窗口不改该文件、不发送外部消息，也不自行发起业务任务。

COMPUTER_USE_NOT_USED。

## CEO补交说明（2026-11-02）

Owner本轮授权仅提交这三个已完成文件。已复核CSV可解析、332项及5,551,859字节与报告一致，不重新审计或统计资产。通过GitHub连接器核对原V1.6分支HEAD仍为审计SHA；以该SHA为父版本，在独立文档分支 `codex/non-business-asset-audit-20261102` 交付。首轮关于本地分支、代理失败及未知状态的描述保留为当时记录；不将未验证的动态引用或真实最后使用写成确定事实。未切换本地分支、未操作原V1.6工作树，未修改任何受保护文件。
