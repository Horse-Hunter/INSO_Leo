# 产品基线

## V1.5 TP implementation authority (Owner 2026-10-25)

Owner approves offline TP design/development following discovery review d67ebfe.
Original 2026/SHAHAB physical row positions do not shift by insertion. TP uses
RFQ_BRIEF target_price and independently persisted source-position/requirement
identity; it must support historical orders without old inquiry/Research IDs.
Automatic completion is one-shot even after TP edits; manual TP-only rerun is
allowed through the existing GUI idle scheduler. TP history may extend to twelve
calendar months; ordinary Research retains its existing six-month policy.
TP mail goes only to linan229@qq.com and reports factual minima, without INSO's
ordinary preference override. Other requirement columns are not implemented.
Source code is REVIEW_REQUIRED, opt-in disabled; no real mail, TP execution,
production SQLite/Sheet writes, procurement, build or deployment is authorized.

本文件只维护长期产品范围与跨模块业务规则；当前进度与任务状态写在 `control-room/COORDINATION.md` 和对应 RFQ Task Spec，实现细节写在 module docs。

## V1.1

稳定流程：

```text
15 分钟 Scheduler
→ Sheets 读取待处理记录
→ Workflow 建立/恢复 inquiry
→ Research 调研
→ 写入 调研价格.xlsx
```

Research 价格源：IC.net、Findchips、HQEW、LCSC、Bom.Ai、INSO（INSO 仅作只读历史价格源）。

V1.1 Research Stability 已 CLOSED，稳定锚点：
`release/v1.1 = 44cd4a4cdb05fc069189801d24c4710bfd9445f3`。

## V1.2

V1.2 在 V1.1 上增量加入：

- INSO 近 7 天重复订单检查；
- 重要订单 / 重复订单通知；
- INSO 采购询价草稿录入；
- GUI 业务状态、事件历史和异常提醒。

关键业务规则：

- 重复检查使用 rolling 168h（Asia/Shanghai）；Owner 2026-10-08 更新同型号读取规则为共享模糊前缀策略（见末尾），数量只比较，不参与型号匹配。
- Owner 2026-10-02 明确：历史数据从业务询价页**下方采临时询价**查询取得，不能使用上方业务询价列表；核对 `CreateTime`、`PartNo`、`Qty` 和真实制单人 `UserName`，完整读取分页。Research 价格筛选不得丢弃零报价的重复历史。
- 重复订单仍先完成 Research，再发重复通知并停止采购。
- 非重复订单：A 必发重要通知；B 总额 > 50,000 且货少；C 总额 > 300,000 且货少。
- 采购类型与库存无关：A，或 B > 50,000，或 C > 300,000 → `需要问全价格`，否则 `普通询价`。
- 全价格采购员：颜浩坚；普通询价采购员：陈熙。
- AI 录单输入：`型号 + 6 个 ASCII 空格 + 品牌 + 6 个 ASCII 空格 + 数量`；型号与数量必须精确一致，品牌只需部分匹配（ERP 会把品牌归一成自己的规范码，如 `HRS(hirose)`→`HRS`）；任一校验失败不得保存。
- Owner 2026-10-02 最新授权：草稿及 AI/parent 校验通过后，允许客临时询价表单的「保存并发送」单次提交；等待五秒，再以**上方业务询价列表**同型号、本次时间的新记录确认结果。不明结果不得自动重发。首次真实提交只由 Owner 在下次真订单运行，Executor 不做提交测试、不自动重启上线；本次源码改动先交 Owner Review。此明确例外取代此前对保存并发送的绝对禁止；单独「保存」、其他 INSO 发送及 Sheets 写入仍不开放。
  - 命名澄清（2026-10-01 线上核证）：AI 录单面板页脚还有一个「保存数据」（`#win_btn__dialog11`），它是**纯客户端**的识别结果回填（`pasteImport` → `AiImport.doImport` → `ai_appendRow` 重载明细表），不写服务端，**不是**最终保存动作。两者不得混称。
- Owner 指定：保存成功后的 GUI 业务文案为 `已发采购单`。
- Owner 决定（数量数据异常）：待处理记录的数量单元格**不是数字**时（列名图例如 `Qty`、空白、文本占位），**跳过该行并记明确原因**，不发起 Research、不进入采购。该行在 GUI 显示为一类"已跳过"业务状态，并产生醒目的数据质量提醒；跳过不消耗重试预算，且表格修正为数字后该 inquiry 可自动恢复，无需人工清库。
- Owner 决定（崩溃恢复）：查价（Research）过程中进程被强杀后，重启必须把残留的"查价中"占用**自动释放回队列**并重新排队；Research 只读，故释放占用是安全恢复，不产生重复写入。

V1.2 Production Write Gate 当前 **CLOSED**。

## 长期边界

- Chrome 是唯一支持的生产浏览器；Edge 支持已废弃。
- Core Vault 是唯一凭据源。
- LCSC credential SiteId = `szlcsc.com`；认证 host = `passport.jlc.com`。
- CAPTCHA / OTP / 设备验证一律人工处理，不绕过。
- 不引入 Redis、Celery、Kafka、Docker 或大型 Workflow Engine，除非出现真实需求。

- Owner2026-10-07：正常 Research/采购订单行间隔由180秒缩短为120秒，GUI按同一期限倒计时（冷却02:00）。Owner随后补充：查询失败重试亦由180秒改120秒；报价正常行间0秒和15分钟循环不变。

- Owner2026-10-08：客户等级S与A使用完全相同的业务规则，canonical effective tier为A；源表、WorkItem、identity snapshot的真实S保持不变。旧S非法规则已被取代；未发的旧S跳过订单在正常poll中以同inquiry自然恢复，不做历史重放或批量迁移。

- Owner 2026-10-08：Research 全部网站、采临时询价防重复/报价识别统一使用 `core.mpn`：NFKC/大小写规范化，去空白、下划线及横线，Google 型号清理后去末尾两位；结果必须以此前缀开头，前缀之后最多10个清理后字符。清理后1–2位型号仅精确匹配，空型号不匹配。匹配是方向性的。采购提交及 Google 行身份仍按原精确规则。窗口、价格、库存、采购提交安全规则不变。

- Owner 2026-10-08：报价输入B列必须等于源表型号原文；若选中报价型号原文不同，L列在已有备注之后换行追加“报价实际型号：XXX”，并通过既有队列提醒229与shawn。重试不重复追加或重复创建同一报价差异邮件；INSO raw14记录保持原样。

Owner clarification 2026-10-08: INSO Research/procurement-history duplicate/quotation searches use the original full source model verbatim (HTTP transport encoding only). Cleaned-prefix/initial-token retrieval is superseded. Normalization and two-character-tail removal apply only to returned-model comparison; no effect on other website queries or exact source identity.


## Owner correction: missing brand (2026-10-12)

Blank or case-insensitive `UNKNOWN` Brand means no known brand, not invalid
inquiry input. Valid model/quantity/tier records enter the existing Research path
with `brand=None`; existing ICNET resolves the brand. Procurement still requires
a real brand after Research. This overrides the RFQ-003 pre-Research brand gate;
model/quantity/tier checks and procurement validation remain in force. Previously
input-skipped records may resume on the next normal poll without a brand edit.


## Owner brand writeback repair (2026-10-12)

The canonical V1.2 inquiry worker now uses the existing safe BrandUpdater.
Resolved missing/UNKNOWN brands are written to only the uniquely relocated
Brand cell using the existing cached noninteractive write service, then read back.
An existing real source brand is never overwritten. The post-Research source
check accepts the resolved brand only when the ledger records confirmed UPDATED;
other source changes remain conflicts. Completed procurement is never rerun for
brand writeback. Executor deployment does not independently write live cells.


## Owner Google transient-read correction (2026-10-13)

Transient source Google GET failures get one retry at the existing read boundary.
If both attempts fail, skip the current poll and notify229 once per failed cycle,
then use the existing15-minute poll wait and continue normally when reads recover.
No new timer/state machine, business retry, write retry or V1.4 order polling.
Permanent auth/permission, schema, database and INSO failures retain stop guards.
This supersedes GLOBAL_STOP only for identified exhausted transient Google reads.


## Owner SHAHAB / inquiry-mail correction (2026-10-13)

SHAHAB is an independent customer rule, overriding the old normalized A default.
Estimated RMB total >=20,000 (including equality) uses 颜浩坚 / 需要问全价格
and important inquiry notice; below uses 陈熙 / 普通询价 without important notice.
Inventory does not alter this rule. Unknown total does not guess ordinary routing
or send important notice. Other A/S, B/C and duplicate-stop rules remain unchanged.
Source snapshots/IDs and existing submission/dedup guards stay intact; no replay
or migration. New SHAHAB sheet records display SHAHAB instead of invented A.
Important/duplicate/exception email copy uses 询价; model-difference email subject
is 【INSO】采购报价差异. Historical outbox payloads remain immutable.
# V1.4 sales completion -> Google intent status (2026-10-13 Owner decision)

Only after INSO fields/PDF and local filled-mail receipt are confirmed, match each
contract line by model and quantity across both configured worksheets, limited
to 已报价给客户 / 意向订单. Unique matches transition to 意向订单; existing intent
is success without change. Missing/ambiguous/failed rows are listed by model in
the existing GUI result popup for Owner manual repair. The completed INSO page
and local processed receipt remain retained; never rerun sales entry for Sheets
repair. No INSO save/submit or new browser/login/scheduler is authorized.

## Owner pending-state / tray / site retry correction (2026-10-15)

Confirmed saved procurement may settle its local pending-Sheets warning by fresh,
unique source identity/brand proof when source is 发给采购, 采购已报价, 已报价给客户,
意向订单 or 成交. Do not rewrite advanced statuses or replay procurement.
Window X hides the GUI from the taskbar into a native tray icon while workers
continue. Tray Open restores; tray Exit uses existing graceful shutdown. If tray
creation fails, keep the window and offer explicit normal exit, never lose access.
External research-site transient failures get initial plus three stop-aware retries
before final observation/notification; login sweep follows the same classification.
INSO reuses its existing three query retries. Known security challenges, rejected
credentials, missing credentials and unverified session identity keep immediate
human-handling safeguards. Genuine no-result/no-price is not a technical retry.

## Owner quotation refresh / Google web transport (2026-10-18)

The existing poll watches 发给采购 / 采购已报价 / 已报价给客户 for the same
inclusive72-hour INSO supplier-net-price selection. Compare local RMB procurement
baselines keyed by the original inquiry ID, never customer sale prices. Existing
quoted rows first bootstrap a missing baseline without updating; subsequently
only cheaper positive prices or zero-to-positive refresh. Verified inserted
updates advance the stored positive minimum. Owner CEO整改 (same date): after a
refresh update click may have executed, uncertain result also advances ONLY the
comparison baseline and enqueues229 manual-check mail with old/new RMB net prices;
no same-run re-click, Google-success outcome or blocking Hold. Pre-click failure
never advances it; same/higher then skips, further reduction can update normally.
Existing owned script/input guard re-checks later instead of permanently stopping.
Initial
sent rows still require 采购已报价; refreshes preserve the later source status.
Unbound historical quoted rows are skipped, never given invented inquiry IDs.
Pending/overdue purchase counts and reminders remain sent-status only.

Owner replaces API/OAuth in production composition with the canonical CDP Google
web UI for all source reads, targeted writes, quote input and intent updates.
Existing domain adapters and quote-script UI are reused. Read-only reconnaissance
verified2026 header row1 and SHAHAB header row2 with their existing column rules.
The missing native range transport reads via File/Download TSV (immediate temp
deletion), writes through the observed name box/formula editor, waits for cloud
sync and exact readback, then closes only owned Google tabs. Auth/unsynced-write
uncertainty preserves the operation page and stops; sales review tabs stay intact.
No new Google login, OAuth refresh, browser profile or scheduler is introduced.
Live read acceptance passed; real writes/overwrite acceptance remains UNKNOWN
pending independent Review. No deployment is part of this implementation task.


## Owner website outage recovery correction (2026-10-22)

A website failure must not globally stop shared business before its necessary
business operations have continuously failed for three hours in the active run.
Owner explicitly confirms: a working login page alone is not INSO query recovery;
a proven necessary business read resets that site's outage clock. Sites have
independent clocks; intermittent failures do not accumulate. Existing bounded
read/login/query retries and interruptible15-minute polling remain canonical.
Only a fresh observed failure at/after3h permits global stop; stale timers or a
working unrelated site cannot justify it. Owner stop always wins. Browser/CDP
connection loss is a recoverable dependency, not proof a website is down for3h.
CAPTCHA/SMS/rejected credentials preserve the original page and wait for human
completion; recovery checks never bypass security or replay writes. A successful
read is required before clearing a site outage; login-only DOM observation only
permits the next safe attempt. Uncertain purchase/update dispatch remains held
per order, with no automatic re-click; safe independent orders/quotes continue.
Schema/config/database/invariant failures are local business pauses requiring
repair, never proof of a website outage or a blanket claim of global failure.
Their affected business may need to stop safely; the UI must state that honestly.
Older immediate website GLOBAL_STOP policies above are superseded. Executor owns
implementation/tests/release evidence in tasks/2026-10-22-site-outage-three-hours.md;
independent Review remains required. No production writes are run as verification.

## Owner Research six-price-source correction (2026-10-22)

Supersedes previous five-source and individual shorter history windows: IC.net
joins Findchips/HQEW/LCSC/Bom.Ai/INSO as a sixth price source using its existing
query page's current RMB reference price. Missing/invalid/zero reference produces
no candidate, not a technical failure; existing IC.net brand/certified-stock rules
stay unchanged. Only positive valid RMB-normalized candidates compete; same ECB
FX and minimum times original customer quantity. Findchips/LCSC stock fallback
and all other Research status/matching/quantity rules stay unchanged.
Findchips/HQEW/Bom.Ai/INSO independently select the minimum within the first valid
1,2,3,4,5,6 calendar-month window using calendar_month_cutoff. Actual quote dates
take precedence; only evidenced current undated quotes use capture-time current
pricing. Product/stock update dates are not historical quotation dates. LCSC and
IC.net current prices have no month filter. No invented unavailable history.
Research Excel adds IC.net through its existing atomic schema migration without
dropping old rows/identity/status. See docs/modules/RESEARCH.md for date contracts
and UNKNOWN live coverage. Task:tasks/2026-10-22-research-six-price-sources.md,
offline only, REVIEW_REQUIRED; no packaging/deployment/production-data access.

## Owner INSO reference preference and nonzero display (2026-10-23)

Within the unchanged valid six-source normal pool compute the true minimum RMB
price, then prefer INSO if its first-valid1–6 month candidate is at most that
minimum times1.12/1.10/1.08/1.06/1.04/1.02 respectively (inclusive, Decimal).
Otherwise use the actual minimum; no average or raw-price/filter change. Existing
market-reference column stores only the final selected unit price, replacing its
old second-price multiline display; estimated total is that exact selected price
times original quantity. Six source columns, stock/fallback/status and old Excel
schema compatibility remain unchanged; no extra decision/explanation columns.
Keep two-decimal display unless it would erase a positive usable value to0, in
which case preserve its nonzero Decimal digits. True zero still has no candidate.
CEO review5594feb78d1f955412c15519779856b0254994a9 is the prior display-defect
source; implementation/evidence:tasks/2026-10-23-research-inso-preference.md.
Offline source change only, REVIEW_REQUIRED; no packaging/deployment/live business.

## Runtime disappearance evidence (2026-10-23)

Core/GUI/frozen-entry source now records per-launch lifetime, sanitized Python
main/thread/Tk/shutdown errors, stack-only native faults and independently observed
Windows exit codes under runtime/logs. An unexplained zero-code exit is unexpected;
normal exit requires explicit exit intent and main completion. Next launch reports
dead runs lacking exit observation. This adds no restart or business replay.
Previous installed-app disappearance remains UNKNOWN: absent Windows reports do
not prove clean exit. Source-only offline verification, REVIEW_REQUIRED, not yet
installed; power loss/observer also killed/pre-Python failures can remain UNKNOWN.
Contract and limits: docs/modules/CORE.md;
task: tasks/2026-10-23-runtime-exit-diagnostics.md.
