# Owner change — stop INSO quote-refresh for customer-quoted orders older than one week

status: REVIEW_REQUIRED / OFFLINE_IMPLEMENTED / NOT_DEPLOYED
owner: CEO requirement; Codex Executor implementation after the currently authorized Option A production cutover is safely completed or deferred
created: 2026-10-28 (Asia/Shanghai)
source: Owner's latest explicit request and follow-up acceptance of existing internal DB / RFQ_BRIEF timestamps

## Owner business outcome

Only for source rows whose confirmed business status is exactly **`已报价给客户`**:
- During periodic automatic quotation refresh, keep them eligible for INSO re-check only while the corresponding existing order is **within one week** of the best defensible existing business date.
- Older than one week: skip the entire INSO refresh query for that row. No fresh quotation, repricing input, update button, price baseline advance or follow-up SMTP should be triggered solely by a skipped historical row.
- Initial `发给采购` processing and `采购已报价` refresh remain unchanged. Do not apply this expiry to TP, inquiry, Research, order creation, customer quote status display, manual intentionally authorized order handling or the existing INSO 72-hour **supplier quote selection** rule.
- User favors reusing local SQLite data and/or the existing `RFQ_BRIEF` date. Avoid new schema/new polling/network/browser calls for this feature.

## Existing evidence — do not mislabel dates

CEO independently inspected source and previous real `RFQ_BRIEF` discovery:
- `src/sheets/pending.py` already reads `已报价给客户` as one of `QUOTATION_STATUSES`; `src/workflow/v13_quotation.py::read_v13_candidates` binds it by original `inquiry_id` and current source row identity.
- `src/workflow/store.py` has persisted inquiry `created_at`/`updated_at`; creation means intake into local workflow and `updated_at` is mutable workflow lifecycle, **not** proven date of customer quote.
- `RFQ_BRIEF.rfq_date` is the **inquiry date** (date-only), not date the quotation was sent to customer. Prior verified `RFQ_BRIEF.updated_at` was identical for all 85 inspected rows, thus not a per-customer-quotation timestamp.
- Prior Brief discovery identified duplicate model/quantity/day combinations, ambiguous/mismatched pointers and records missing a local inquiry; never join by MPN alone, row order, approximate model or re-created `inquiry_id`. Reuse already-reviewed unique source+row+model/brand/quantity identity mapping if and only if actually confirmed.
- Existing INSO quote records are supplier quotation timestamps, **not** the age of when a specific customer was quoted.
- Do not use `workflow_items.updated_at`, RFQ_BRIEF bulk `updated_at`, supplier INSO quote date, web scan time or the date a row was first noticed in an already customer-quoted state to claim the true customer quote date.

## CEO decision on the date source — Owner expressly allows a convenient existing proxy

**Priority** for a uniquely verified current `已报价给客户` original `inquiry_id`:
1. If the existing event/ledger already stores the exact customer-quotation-send/transition timestamp in a trustworthy attributable record, use it. No new data layer.
2. Otherwise prefer **verified `RFQ_BRIEF.rfq_date`** only when the original order is safely/uniquely matched by its canonical business identity and the Brief reader is already safely available as part of ordinary work. This is a *date-of-inquiry proxy*, not the actual send date. Do **not** start new full Brief downloads/CDP sessions or introduce ambiguous matching solely for this optional optimization.
3. Otherwise use the original immutable `workflow_items.created_at` of this same existing inquiry_id as a *local intake-time proxy*, after checking its exact schema/immutability and timezone handling. If the field is not guaranteed reliable, do not use it.
4. If no reliable date or identity exists, skip **automatic customer-quoted INSO refresh** as `QUOTE_AGE_UNVERIFIED` and retain a short sanitized diagnostic counter; do not create new inquiry IDs, query INSO merely to discover a time, silently treat the item as recent, or modify source status. This conservative missing-date behavior is for `已报价给客户` ONLY.

**Business caveat**: Proxy inquiry/intake date can precede actual send-to-customer date; it may conservatively exclude an older inquiry quoted recently. Executor must clearly disclose the fallback used and identify that limitation in acceptance evidence, never claim it measures actual customer quote age. Do not introduce extra data-writing to counterfeit an exact send timestamp. If reliable direct customer quote time is already in the existing local DB, it always wins.

**Boundary and time:** Asia/Shanghai timezone. If authoritative timestamp has time, use inclusive rolling7*24h (`at >= now - timedelta(days=7)`). If only a source **calendar date** is known, use inclusive calendar-day threshold `date >= Shanghai_today - 7 days` (the boundary day counts as eligible, older days are skipped); never fabricate hours or confuse UTC with Beijing local. Future dates or invalid/unparseable values are `QUOTE_AGE_UNVERIFIED`. Use deterministic injected clock for tests. The age check must occur **before opening any INSO quote tab or making any INSO request**, not after the query. Preserve source-row/identity safety checks and closed-row/unknown-effect behavior.

## Executor implementation and evidence

**Trigger:** Separate follow-up code change after Option A controlled production replacement is either completed safely or formally deferred. The present approved frozen candidate EXE
`DB9463D4D1DBDF716C80C8A48A2E5D6E9CB7EBE4BB4254A0A2CD40BEEA440969`
is immutable; do not quietly add this feature during that release and do not cancel the imminent-new-order business window.

**Ordered procedure:**
1. Sync current Git and read `AGENTS.md`/`AI_START_HERE.md`, including the **absolute agent Computer Use ban**. Inspect existing local quotation event and intake timestamps and existing Brief/date mapping from code/tests only. No production CDP, GUI or business ledger access for initial implementation.
2. Reuse canonical quotation candidate source/quote loop; implement **minimum scoped early skip** only for exact `已报价给客户` and only before native INSO quotation query. Existing `发给采购`, `采购已报价`, TP and 72-hour supplier selection unchanged. Do not add a second scheduler, browser adapter, migration, page crawler or new persistent fields.
3. Write offline tests for <=7d, >7d, exact boundary, timezone crossing/date-only, future/malformed dates, unique vs ambiguous Brief row, no INSO call/tab for excluded or date-unknown rows, no SMTP/Sheet/price writes, other two quotation statuses unchanged and default production adapter flow. Include actual existing SQLite schema storage contract and no invalid customer quote date guesses.
4. Run targeted and full offline regression (with actual source/test/tree SHA). Record one concise report and test receipt in this canonical task and existing V16 report/JSON if relevant; no real deployment or newly started browser probe. Existing protected runtime/rollback remain intact.
5. Push source and evidence for CEO independent SOURCE Review. New packaged EXE / production installation is **separately Owner-authorized only** after accepting new source. Do not alter an in-progress approved Option A production deployment.

**Review enforcement:** CEO rejects changes that query INSO for a verified expired/unknown-age customer-quoted row, change other statuses, treat inquiry/Brief date as actual customer quote date, add a separate costly Brief browser query or break source identity/no-duplicate guarantees. Explicitly label `REVIEW_REQUIRED / NOT_DEPLOYED` until approved. **Cleanup:** retire only owned test/build scratch under normal project rules, never production/state/Chrome/rollback. Final report must state `COMPUTER_USE_NOT_USED` and any blocked non-programmatic step.

## Implementation status

Requirement-recording paragraph superseded by the offline implementation receipt below. Production executable still unchanged; original Option A controlled release retains its own SHA and scope.

## “已报价给客户”七天自动刷新限制 — 离线源码交付（2026-10-28）

**REVIEW_REQUIRED / NOT_DEPLOYED。生产仍是方案A b57f467，未混入本次规则。**
独立源码提交：`63d161cd3ec998d1fbbd3f584ab46797399dce6c`；src树`c1fc44b0bf87f1f6742939a9f33114c325f8405b`；tests树`c36c35b55f4d1ad201baee8f2dd3304f41e52079`。
主实现`f89caf41015b940cbb29165c28bf00f8f7245a6c`，当前来源行绑定修正为上述最终提交。
此前实际发布证据提交`408ddb6688e30d8829a5b9a71b43cd17afb494bc`单独保留。

复用审计：原报价candidate/execute_candidate/settle_result、WorkflowStateStore、
已验证Brief身份字段与60秒快照、原ManualRetryHolds及Backend组合均复用。
现有事件/表未提供可归属的真实客户报价发送时刻，不新增伪造事件/字段。
只对当前原行状态为“已报价给客户”的自动INSO查询启用：先通过原唯一inquiry/source
身份和状态核验，再按日期判定，随后才可能打开INSO页。优先使用已有有效缓存中
唯一匹配**当前已核验行**的RFQ_BRIEF.rfq_date；缺少合适缓存/匹配则使用同一ID原
created_at。两个都是询价/入库代理，**不是真实客户报价日**，可能保守排除旧询价新报价。
历史导入的本地时间也可能晚于真实客户报价，因此不能保证等同真实客户报价满7天；
实际日期覆盖率/提速幅度未读取生产数据测量。
不使用updated_at、供应商报价时间或扫描/首次发现时间。无可靠身份/日期保守跳过，
保留固定脱敏诊断计数；不新建ID/账本/定时器/依赖，也不为优化额外下载Brief。

边界：时间戳按真实滚动168小时、日期按上海today-7自然日，恰好7天含边界；
未来、无时区、坏日期为QUOTE_AGE_UNVERIFIED，过期为QUOTE_AGE_EXPIRED。
跳过时不打开/请求INSO、不更新报价输入/价格基线、不建hold或通知，不写来源状态。
“发给采购”“采购已报价”、TP、询价、供应商72小时选价和人工主动处理不受此过滤。
原权限、Stop、来源租约、双Actor上限（生产仍未启用）、120秒等待及SENT/UNKNOWN不变。
纯Brief来源校验从原TP绑定提取复用，TP业务语义和价格逻辑不变；报价后的无副作用
跳过仍可作为原方案A的安全收口点，不清除之前未知写入的阻断。

实际文件：7个src文件（原Backend/WebService、Sheets Brief、Workflow Store、
原V13报价/集成及一个纯日期策略文件），5个测试文件、2个原模块接口文档。
唯一新增公共窄接口为原服务只读peek/BriefReader缓存解析、原Store的入库时间读取、
纯Brief来源绑定；不跨线程共享Page或调用新的浏览器客户端。

最终专项：**345 PASS / 24.50秒**；新增46项，含旧行换占用者/当前行移动、Brief歧义、
上海跨UTC日、未来/空/错误日期、实际SQLite不可变created_at、跳过无SQL/SMTP/Google
副作用、默认Backend接线和人工/Stop。最终完整离线：**3140 PASS / 1 SKIP，125.63秒**。
跳过原因沿用Windows当前权限无法创建symlink；没有跳过业务保护。
Ruff/diff PASS，真实SMTP守卫无外发尝试。中间版本3136 PASS不充当本次最终证据。

`COMPUTER_USE_NOT_USED`。本功能实现/测试没有读取生产账本、连接Chrome/CDP/Google/
INSO/SMTP，没有构建/安装或修改正在运行的EXE、配置、Vault。当前生产程序哈希仍
`DB9463D4D1DBDF716C80C8A48A2E5D6E9CB7EBE4BB4254A0A2CD40BEEA440969`。
真实加速幅度、客户发送日准确性和新规则生产行为仍NOT_VERIFIED；先交Owner转CEO
独立源码复审，通过后另行批准发布。生产实际让位与Google短暂超时恢复见下方原发布记录。

本轮离线临时工作清理：8个自有测试目录、15415文件、635609959字节已退休；
保留必要小型测试输出和摘要。9个本轮CLI检查/发布/测试辅助脚本已退休，
原生产、共享runtime、账本、Vault、Chrome及新鲜程序回滚保持不变。
