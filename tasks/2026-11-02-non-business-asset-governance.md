# Task: 非业务资产台账与文档瘦身候选

status: complete
owner: Codex（非业务资产窗口）
created: 2026-11-02
updated: 2026-11-02

## problem / goal
依照Owner本轮完整指令及CEO审计 `23aaf84bdb42da9fa1bd526a97a168e60202f383`，逐文件盘点历史资料，提供短索引、候选空间收益及可执行的后续核实清单，交CEO审核。

## current_facts
- 当前根目录HEAD为 `c3a597d963ed418e45f6c7c75249bdef1b8147b4`（main），含既有未提交工作，全部保留。
- 本地命名V1.6分支为 `df6646c7542bea98f2aaeb8218e9254c7873a9c2`，不能当成CEO最新版本。
- 直接从共享Git对象库读取指定CEO审计SHA，不切换分支、不接管运行工作树。Git fetch因代理连接失败，未声称更新了远端。
- 先读根目录现有 `docs/AI_START_HERE.md`、AGENTS及导航；再读审计快照的根 `AI_START_HERE.md`、AGENTS、CEO_HANDOVER、PROJECT_BASELINE、MODULE_INDEX、REPORTING、COORDINATION与相关任务/日志。
- UNKNOWN：远端实时HEAD、真实文件最后打开时间、运行目录容量及生产引用现状。

## scope / requirements
- Git快照中的docs/evidence、tasks、RFQ-001至016、顶层V15/V16报告、templates、scripts逐项统计用途、引用、最后修改证据、分类和建议。
- 复用CEO_HANDOVER的资产分类与COORDINATION状态权威；本任务报告只是该快照的补充索引，不建立新管理体系。
- A当前仍被引用；B高历史价值保留；C适合逻辑归档；D重复/闲置待确认。无引用不等于无用；旧版本名称不构成删除证据。

## non_scope
不改src/tests/packaging、构建启动发布脚本、AGENTS、任一AI_START_HERE、CEO_HANDOVER、V1.6运行资产；不删改原始证据，不迁移或清理工作树、缓存、数据库、备份。无生产、网络业务测试、GitHub公开性检查、IMAP专项、Computer Use、业务重构。

## acceptance
- [x] 逐文件台账可追溯至固定SHA、Git blob大小、引用来源及最后修改提交。
- [x] 提供CURRENT/HISTORICAL/SUPERSEDED短索引、四个重点区域分析及精确候选。
- [x] 分开列出预计阅读/空间收益、禁止操作项、UNKNOWN与CEO后续动作。
- [x] 检查覆盖率、总和、引用、重复blob、diff及变更范围。

## verification
只读Git树/blob/历史和静态路径引用；不执行任何被盘点工具，不重跑业务测试。文档验证结果见completion。

## completion
- status: complete（文档交付完成，CEO审核REVIEW_REQUIRED；不是RFQ016状态变更）
- changed: 本Task Packet、`docs/NON_BUSINESS_ASSET_AUDIT_2026-11-02.md`、`docs/NON_BUSINESS_ASSET_INVENTORY_2026-11-02.csv`。
- verified: 332个文件、5,551,859字节，Git树范围全覆盖且无重复路径；逐行核对blob大小/SHA、最后修改完整SHA、引用路径/行号格式、A/B/C/D分类与0删除收益。A36/B233/C61/D2。仅一对685字节同blob证据；两大文档7段重复叙述共37,009字节（未来单份链接化的理论上限，非删除授权）。已检查文档内容及git diff；只有本轮三个新增文档，既有改动保留。未运行盘点工具、业务测试或生产验证。COMPUTER_USE_NOT_USED。
- limitations: 首轮只交本地文档；Owner本轮明确要求补交GitHub审核证据，现授权仅将上述三个文件提交至独立非业务文档分支 `codex/non-business-asset-audit-20261102`。不切换本地分支、不操作原V1.6工作树、不改其远端分支。

## CEO补交核对（2026-11-02）
- 范围仅为三个已完成文件的完整性、CSV解析、已有统计一致性、候选措辞与提交；未重新审计、未扩大候选。
- CSV解析通过：332个不重复路径，合计5,551,859字节，分类A36/B233/C61/D2，与报告一致。保留静态完整路径命中、文件名/目录可能引用和真实使用UNKNOWN之间的区别。
- 通过GitHub连接器核对V1.6远端HEAD为 `23aaf84bdb42da9fa1bd526a97a168e60202f383`；以此为文档提交父版本。仅新建文档分支，不覆盖原分支，不合并旧main，不提交其他未跟踪文件。
- 仅明确重复JSON候选的可能引用措辞；候选仍需确认，不产生删除许可。COMPUTER_USE_NOT_USED。
