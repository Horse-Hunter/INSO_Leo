# V1.5 RPF_BRIEF Discovery

status: DISCOVERY_REVIEW_REQUIRED
phase: DISCOVERY_ONLY
verified_on: 2026-10-25 (Asia/Shanghai)
branch: codex/v1-5-tp-research
baseline: 124e39ca17dcf4a59e7e72b97a40331609d955e8

结论：已安全读取真实子表并证明两个来源均有可关联到既有 inquiry_id 与 Research 的真实样本。实际名称是 **RFQ_BRIEF**，Owner 已确认纠正原请求中的 RPF_BRIEF，并授权精确名称的一次性只读嗅探。当前数据存在重复联合键、字段冲突与未落本地账本的记录；本结论不是自动轮询/报价/部署许可。

## A. 读取方式、授权与限制

- 使用已安装 V1.4 的生产配置，在内存中取得现有 Spreadsheet 绑定（报告代号 S1，不公开地址/ID）。2026、SHAHAB、RFQ_BRIEF 位于同一 S1；精确标签选择、激活标题和 gid 绑定验证通过。
- 最初发现 V1.4 正在占用两个 Google 页面，立即中止交互式嗅探。Owner 随后明确通知程序停止、CDP 可用；重新检查后才恢复。后续保留 Owner 手动打开的页面，仅操作本次新建页面。
- 复用 shared_playwright_factory、canonical CDP 9222、BrowserHandle(owned=False)、GoogleQuotationUpdateActions、GoogleSheetsWebService._select/_download。只用文件菜单的原生 TSV 下载；未新建登录/API/浏览器框架，未读取凭据，未修改生产白名单或默认 Schema。
- 原生下载器保持 32 MiB/100000 行上限、文档/认证/gid 校验及临时下载删除；除下载器自动删除的临时 TSV 外，解析数据仅在内存；未持久保留整表/原始 TSV/截图/业务值证据。每次完成后关闭本次页面，原有页面均保留，浏览器保持连接可用。
- RFQ_BRIEF 导出 86 行（含表头）、17 列 A:Q，85 条非空记录；来源 2026 为 41 条、SHAHAB 为 44 条。最终再次导出与本次首读逐值相同。
- 原始 2026 TSV 为 206 行、最大 36 列；SHAHAB 为 128 行、最大 21 列。源表头分别在第 1、2 行，既有表头校验通过。保留物理行号，不因空行/表头过滤而重编号。
- 当前生产入口拒绝 RFQ_BRIEF，默认 RowReader 仅 A:G，直接使用会漏掉 H:Q；开放式范围亦仅允许 A:G，显式范围最多 Z。此次只在临时 helper 中检查原生 TSV 全列；未改 src/tests。
- TSV 给出展示字符串，不能将其当成 API 的底层 UNFORMATTED_VALUE/公式元数据；尾部空白网格、其他子表和历史完整性未证明。读取成功不证明写入权限；本次未测试写入。

## B. 完整字段映射

表头实测在第 1 行；无重复列名。下表列名、位置和非空数为实测，业务含义按名称解释，决策规则均待确认。除目标价另有公式栏核验外，底层单元格类型不由 TSV 推断。

| 位置 | 列名 | 含义/读取形态 | 非空/85 | 可用性 |
| --- | --- | --- | --- | --- |
| A / 1 | rfq_line_id | 外部询价行标识，文本 | 85 | 本次无重复；稳定生命周期 UNKNOWN |
| B / 2 | sheet | 原来源子表，文本 | 85 | 2026 / SHAHAB，精确来源绑定 |
| C / 3 | sheet_row | 原来源物理行号，整数字符串 | 85 | 定位指针；不能独立生成 inquiry_id |
| D / 4 | rfq_date | 询价日期，ISO 日期字符串，无时间 | 85 | SHAHAB 可与 A/DATE 核对；2026 原始日期来源 UNKNOWN |
| E / 5 | mpn | 型号，原文字符串 | 85 | 保留数字外观型号，禁止数值化 |
| F / 6 | mfr | 品牌/制造商，文本 | 71 | 14 条空白；作辅助核验，不强制补造 |
| G / 7 | qty | 数量展示文本 | 85 | 84 条符合所测数值展示形态；1 条无法按现有正整数数量规则解析 |
| H / 8 | target_price | 数值加币种后缀的字面文本 | 4 | 81 条空白；详见 C，不计算报价 |
| I / 9 | target_price_source | 目标价来源标记，文本 | 4 | 含义/来源规则 UNKNOWN |
| J / 10 | status | Brief 状态，文本 | 85 | 与原表状态的转换关系 UNKNOWN |
| K / 11 | suggested_sourcing_mode | 建议寻源方式，文本 | 85 | 分类规则 UNKNOWN |
| L / 12 | customer_type | 客户类型，文本 | 85 | 不是原始客户名称或客户唯一 ID |
| M / 13 | decision_window | 决策窗口，文本 | 85 | 单位及规则 UNKNOWN |
| N / 14 | min_datecode | 最低日期码要求，文本 | 85 | 语义/默认规则 UNKNOWN |
| O / 15 | full_package | 完整包装要求，文本 | 85 | 布尔编码/默认规则 UNKNOWN |
| P / 16 | customer_default_requirements | 客户默认要求 | 0 | 全空，不推断默认业务要求 |
| Q / 17 | updated_at | 更新时间，ISO 日期时间文本 | 85 | 本次 85 条值相同，不作为逐行排序区分依据 |

未发现独立 customer_name/customer_id、currency 或现有 inquiry_id 列。rfq_line_id 并非现有 inq_ 格式；逐值扫描两个源表已导出数据的全部列，未发现其与原始行字段的直接相等关联。2026 AJ 有 AUTOMATION_ID 表头，但未与这些 rfq_line_id 对上；不据表头推断可关联。

## C. target_price 实际格式

4 条非空值均为“数值 + 币种后缀”的文本：3 条 USD、1 条 RMB。既不是独立数值列，也不能默认为同一币种。只读选中 H31、H36、H69、H70，在公式栏核对字面内容与 TSV 一致，均不以等号开头，未见公式。未公开价格数值；未换汇、拆价或报价计算。Sheets API 底层类型未查询；其他未来格式/公式仍 UNKNOWN。

## D. RFQ_BRIEF → 2026

- 样本 S2026-01：Brief 第 5 行 → 2026 第 203 行。来源、完整型号、数量、非空品牌一致；扫描全源表仅一条候选，sheet_row=203 同时吻合。沿用现有 NFKC/首尾空白/ASCII 大小写精确比较，不用模糊前缀或部分品牌匹配。
- 现有 A/C/E/G 快照及状态迁移定位逻辑进一步唯一绑定到本地已存原始身份（首次行位置 203），同一 inquiry_id 在 Research 中有且仅有一条记录。报告不公开实际 ID、型号、品牌、客户、日期或数量。
- 2026 表头 B 是 WHAT，未确认它是 rfq_date；本次不能宣称已用日期完成 2026 的三字段跨表验证。首轮按“来源+型号+数量+已有品牌”得到 34 条业务字段唯一匹配、4 条重复候选、3 条字段冲突未匹配。
- Owner 指出两条重复可按倒序对应两条后，补充记录当前组级/指针对应：Brief 43→2026 151，Brief 44→2026 149。两侧型号/数量相符，倒序与 sheet_row 一致；这两条应称 CURRENT_ORDER_POINTER_ALIGNED，不能误写成当前无对应，也不能把重复三字段伪称唯一键。指针在原表排序/插行后的维护契约尚未验证。
- 单独放宽为“来源+型号+数量”的候选检查得到 36 条唯一候选、4 条重复候选、1 条未匹配。其中 Brief 12→199、13→197 有唯一候选但品牌冲突，分别记录候选位置与冲突，不擅自认定是另一笔订单，也不把冲突当作已解决。

## E. RFQ_BRIEF → SHAHAB

- 样本 SSH-01：Brief 第 6 行 → SHAHAB 第 128 行。来源、完整型号、品牌、数量、rfq_date 与原 A/DATE 一致，全源表仅一条候选，sheet_row=128 吻合。
- 沿既有 B/D/F 身份/品牌/允许状态迁移规则唯一关联既有本地 inquiry_id（首次行位置 128），Research 同一 ID 有且仅有一条记录。
- 当前 42 条业务字段/日期匹配、1 条 AMBIGUOUS、1 条 UNMATCHED。日期以日核对，不伪造时分秒；Brief 第 83 行对应原表 63/64 两条候选，属于一对二，未任意选择。Brief 第 68 行数量无法按现有规则解析，未据型号与行号猜配。

## F. inquiry_id、Research 与本地订单衔接

V1.4 的实际实现（src/workflow/store.py）是表格+来源子表+首次行号生成去重键，再生成 inq_ 加 SHA256 前 24 位；不是另建 UUID，也不能按 Brief 行号或排序后的行号重算。继续使用账本已存 record_identity 和 inquiry_id。

仅对首轮 76 条业务字段唯一匹配记录检查本地关联：2026 中 11 条有唯一既有账本+Research、23 条无对应账本；SHAHAB 中 7 条有唯一账本+Research、4 条有唯一账本但无 Research、31 条无账本。以上“无账本”指现有定位规则下未找到，不能解释成业务订单不存在。Brief 第 2 行→2026 第 206 行虽然源表唯一匹配，本地未找到，未创建记录补齐。

使用 sqlite3 URI mode=ro 与 query_only；未构造会初始化/迁移/写 WAL 的 WorkflowStateStore。Research 复用 ResearchExcelOutput.read_history 的 read_only/data_only 路径。SQLite 主文件、既有 WAL/SHM、Research 文件读取前后哈希一致；没有把真实记录写入测试数据库。组级指针对应的两条未计入上述 76 条唯一业务匹配或本地汇总。

## G. 重复、排序与错单风险

- Brief 中 rfq_line_id 85 个均非空且当前无重复；不能证明刷新/排序后稳定。完整 TSV 行无重复；原文型号有 2 组重复；来源+日期+型号+品牌+数量有 1 组重复。
- 按 Owner 建议单独核对 mpn+qty+rfq_date：83 条在 Brief 内键唯一，第 43/44 行键完全相同。此统计是 Brief 内唯一性，不等于已证明该键在两个原来源中全局唯一。
- rfq_date 的 85 条均可解析为日期，整体从新到旧，无升序逆转，48 处相邻同日。SHAHAB 来源行号递减；2026 来源行号有 2 次回升。两来源均跳过部分原表行；不存在已证明的“整表反向行号公式”。同日的稳定排序和过滤规则 UNKNOWN。
- 当前位置明确的重复组可记录两对两的倒序/指针对应；其业务键仍重复。保留业务字段唯一、当前顺序指针对应、真正多候选三种证据层次，避免混称“全部无法对应”或“全部永久唯一”。
- 仍需 AMBIGUOUS：Brief 27→2026 176/178；82→2026 101/109；83→SHAHAB 63/64。未用倒序挑其中一条。
- 保守核验下 UNMATCHED/冲突：Brief 12、13 品牌与指针处来源不同（型号数量仍有唯一候选）；15 的型号与指针处来源不同且无完整型号数量候选；68 数量不可解析。字段变化的原因 UNKNOWN，不直接归因于排序或人为错误。
- 14 条缺品牌、81 条无目标价、全部默认客户要求为空；存在 USD/RMB 混用。匹配不要求填造缺失字段。
- 源表状态变化可能使旧快照失配，V1.4 已有特定报价状态的原锚点/唯一重定位能力；不能任意把后续状态改回未发。行号复用、重复询价、插入/排序可能错绑旧 ID；本次未在真实表格执行排序、编辑或状态变化实验。

## H. 最小 V1.5 数据契约与复用建议（仅建议，未实现）

1. 在现有 Sheets 边界增加独立只读 Brief schema；精确 S1/标题/gid 绑定、唯一表头 A:Q、列名映射、原文和物理位置保留。禁止落入标准表默认 Schema；生产读取扩展须单独审核。
2. rfq_line_id 作为外部行键保留，其生成/刷新/删除重建契约明确前不作为本地 inquiry_id。优先寻找已验证的稳定共享 ID；当前未找到直接共享 ID。
3. Owner 建议的 mpn+qty+rfq_date 作为首选联合键候选，同时保留明确来源；先核实 2026 日期来源及两源全量唯一性。品牌、客户、原始业务号、sheet_row 用作补充核验，不一概要求缺品牌行失败，也不忽略明确冲突。
4. 重复键组分别记录全体候选、来源行指针及组内顺序。当前两对两一致可返回 CURRENT_ORDER_POINTER_ALIGNED；稳定排序/指针生成规则未验证前不升级为永久稳定身份或自动处理许可。一对多、不完整组及冲突仍 AMBIGUOUS/UNMATCHED。
5. 唯一关联后的本地绑定复用 Sheets source parser、数量解析、opaque identity、现有重定位与 Workflow 既有账本/Research ID。无既有身份时返回 LOCAL_UNRESOLVED，不另造 inquiry_id，不自动入队。
6. target_price_raw 与 price_source_raw 原文保留；未来解析时单独保留币种/解析结果，空值及混合币种不默认化。本阶段没有定价/轮询/邮件实现。

## I. 实测、UNKNOWN 与 Owner/CEO 待确认

实测：精确 RFQ_BRIEF 的 S1/gid/读取、完整 17 列、85 条记录、4 条字面目标价、两来源真实唯一样本、本地及 Research 同 ID 关联、重复键及候选、日期倒序、两对两当前来源指针、只读文件哈希、页面保留；不是仅离线模拟。

UNKNOWN/待确认：rfq_line_id 与 AUTOMATION_ID 的生成/稳定性/关系；2026 的 rfq_date 从何字段生成；同日排序/筛选/重建及 sheet_row 在排序后的维护规则；两条相同三字段究竟是独立询价还是业务重复；品牌/型号冲突成因；Brief 状态、各建议/要求列和目标价来源的正式业务语义；本地无记录是否应后续建单（本阶段不建）；全局长期身份一致性和未来自动流程权限。

本阶段已停止 live 嗅探。CEO 审核本报告与 Task Packet，状态保持 DISCOVERY_REVIEW_REQUIRED；不继续 TP 轮询、最低/次低价、邮件、发布或部署。

## Verification / changed files

- 仅新增本报告、tasks/2026-10-25-v15-rpf-brief-discovery.md；src/tests/生产配置/部署文件均未修改。
- 复用既有离线测试：Google Web transport、Sheets reader/pending/brand relocation、V1.3 identity binding、Workflow V1，共 185 PASS / 3.99s。测试仅 synthetic 数据，无真实订单入测试库、无真实邮件/CDP/网站。
- 命令：python -m pytest tests/launcher/test_google_web.py tests/sheets/test_google_reader.py tests/sheets/test_pending.py tests/sheets/test_brand_write.py tests/workflow/test_v13_quotation.py tests/workflow/test_workflow_v1.py -q -p no:cacheprovider --basetemp <task-owned-temp>。
- 初次收集因系统 Python 缺时区资料失败；通过命令级 PYTHONTZPATH 复用现有 V1.4 捆绑 tzdata 后通过，未安装依赖。覆盖排序后重定位、重复快照冲突、状态变化、保留原 ID 及范围/身份保护；未修改测试规避失败。
- 分支从已有明确 CEO 代码审核记录的 124e39c 创建；远端最新 4f58926 含后续 REVIEW_REQUIRED 的 INSO 修复，本阶段不带入。独立 app-managed worktree 保留供审核；原 main/V1.4 的 HEAD、索引与未提交工作不操作。
- 临时 helper 在原仓库已忽略 .tmp 下运行，未包含业务样本；本任务结束清退 helper 与 synthetic 测试目录。原生下载逐次删除；未清理他人页面、Profile、运行数据或既有构建。
