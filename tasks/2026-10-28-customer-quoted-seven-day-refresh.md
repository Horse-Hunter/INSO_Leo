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

## CEO independent SOURCE Review — customer-quoted 7-day restriction (2026-10-28)

**Review verdict: `CUSTOMER_QUOTED_7DAY_SOURCE_PASS` for a separate isolated Windows build candidate; `NOT_DEPLOYED`, no live 7-day acceptance and no permission to alter current running production.**

**Exact review evidence.** Remotely verified final delivery
`11d16ae421a5c969a59fa2639ebade1178362709` is one
documentation/evidence child of the final code SHA
`63d161cd3ec998d1fbbd3f584ab46797399dce6c`.
Final source tree `c1fc44b0bf87f1f6742939a9f33114c325f8405b`,
tests tree `c36c35b55f4d1ad201baee8f2dd3304f41e52079`;
actual code commits `f89caf41015b940cbb29165c28bf00f8f7245a6c`
and the source-row relocation fix `63d161cd3ec998d1fbbd3f584ab46797399dce6c`.
Original source-only implementation changed seven src paths:
`src/launcher/backend.py`, `src/launcher/google_web.py`,
`src/sheets/tp_brief.py`, `src/workflow/quotation_age.py` (new),
`src/workflow/store.py`, `src/workflow/v13_integration.py`
and `src/workflow/v13_quotation.py`. Read each changed interface and
the 234-line new `tests/workflow/test_customer_quoted_age.py`,
targeted unchanged `run_inso_query` and `settle_result`, plus
current GitHub production report and JSON receipt. This review has no
read access to actual installed Windows EXE bytes or live browser state.

**Findings:**
1. The authoritative current row/status/unique original inquiry identity
   is revalidated in `V13QuotationCycle._execute_candidate`
   before its `automatic_refresh` / exact `已报价给客户` age
   gate. Current verified physical row, not stale discovery row,
   is used when matching the preexisting Brief snapshot.
   If date is expired/unverified, `_QuotationAgeSkip` exits
   the ordinary original `run_inso_query` operation *before*
   `_operations.open`; `settle_result` bypasses updater
   for the new non-QUOTE_FOUND outcomes and retains ordinary
   GUI observation. No INSO tab/query/retry, supplier price
   baseline, hold, SMTP notification or source write is created
   by that skip. The original candidate loop and safe
   Option A TP yield still receive a returned terminal
   no-effect result. Existing sticky unknown write barrier
   is not reset by that new outcome.
2. Only original scheduled/automatic refresh has the gate:
   launcher composition uses `automatic_refresh=source_store is None`;
   manual custom source_store leaves its existing explicit
   authorization and realtime validations alone.
   Other status `发给采购`, `采购已报价`, TP
   and supplier inclusive rolling72h price-selection logic
   are unchanged; original module clock/Stop/120s
   and existing single Owner remain intact.
3. Date policy uses existing verified fresh (<60s) cached
   `RFQ_BRIEF` only, with original source sheet/current
   physical row/exact model/quantity/brand and SHAHAB
   inquiry-date proof via the existing TP binder.
   It never creates a second client/reader/download on
   cache miss. If no unambiguous valid cached match,
   falls back to same `inquiry_id` immutable SQLite
   `workflow_items.created_at` (aware timestamp only).
   Selected malformed/future Brief is
   `QUOTE_AGE_UNVERIFIED`, not guessed from a later
   local clock. The inclusive168h-aware vs inclusive
   Shanghai-calendar-day cutoff is explicitly tested.
   Unbound/ambiguous older customer rows already
   lacked an original safe inquiry ID; remain
   unqueried with only fixed diagnostic counter.
4. Crucial semantic limitation: neither
   `RFQ_BRIEF.rfq_date` nor local immutable intake
   is the confirmed time of customer quote issuance.
   Brief inquiry date often precedes the actual
   customer quote and can exclude a more-recently
   quoted older inquiry; an imported late local
   intake could keep an actually old customer quote
   in scope. This matches Owner's explicit
   existing-data convenience tradeoff but must
   never be called a strict true customer-send
   seven-day SLA. Do not mislabel a quoted item
   as eligible just because INSO has a recent
   supplier quote.
5. Executor's receipts: **345 targeted PASS** in
   24.50s, **3140 full PASS / 1 SKIP** in125.63s,
   Ruff/diff check PASS and no reported real
   SMTP attempts; the SKIP is the known
   Windows symlink creation case, not omitted
   quotation safety. Tested immutable SQLite
   `created_at`, current-row relocation/old-row
   occupant, unique vs ambiguous Brief, invalid/future,
   Stop, date crossing, no INSO tab, no DB/SMTP
   writes for skip, manual exclusion, other statuses,
   originalBackend wiring and Option A integration.
   CEO inspected the source/test construction,
   exact recorded test counts/hashes, but has
   **not rerun** the Executor's native Windows
   tests or verified raw local test logs.

**Residual constraints:** Proof is offline only.
Actual 7-day coverage, numbers of skipped rows,
amount of saved INSO time, GUI behavior of the
new frozen EXE, production mail/outbox effects
and exact customer-send date are NOT_VERIFIED.
On malformed existing Brief cache schema,
the existing shared read safety behavior may
stop rather than manufacture an age; preserve
current fail-closed policy. Do not add extra
browser probes to collect timestamps.
Prohibit silent changes to the currently
running Option A frozen executable
`DB9463D4D1DBDF716C80C8A48A2E5D6E9CB7EBE4BB4254A0A2CD40BEEA440969`.

**CEO next action:** Approve ONLY reuse of the
original canonical `-Version 1.6 -BuildOnly`
pipeline for a separate candidate,
same unchanged code SHA/tree, frozen
module/executable manifest, `--self-check`
and `RELEASE_SCAN_OK`. Retain current
business program undisturbed: **no Stop,
Exit, Start, live CDP/Sheets/INSO/SMTP
probe, software installation or actual
release switch** without Owner's later
specific approval for this new version.
If future Owner authorizes a window,
repeat original safe drain, immutable
data check, fresh current-version
program backup, protected-state backup,
program-only swap and natural acceptance
without synthetic orders. Any missing
qualifying customer-quoted case remains
live NOT_VERIFIED. Root AGENTS prohibition
of Codex agent Computer Use applies:
`COMPUTER_USE_NOT_USED` in every delivery.

**Record scope:** CEO appends this Review
to the original seven-day task only.
This verdict is source PASS, not overall
V1.6 release closure or new production
installation approval.

## Owner explicitly authorizes independent controlled deployment without another CEO gate (2026-10-28)

**Decision (verbatim):** "如果没问题就自己打包覆盖运行，不用再给你复审了。"

This is the **specific Owner release authorization** required by the previous CEO source review for the **already SOURCE_PASS** seven-day customer-quoted age gate. It supersedes the preceding "BuildOnly-only, return to CEO for candidate review" step **for this exact frozen source version only**. No additional CEO candidate or post-install review is required **if** all original installer/self-check/safety controls pass and production naturally resumes; send a concise final report directly to Owner. This is not general permission to auto-deploy future source changes, disable safety protections or treat the previously-not-deployed feature as installed.

**Exact eligible code:** `63d161cd3ec998d1fbbd3f584ab46797399dce6c`; source tree `c1fc44b0bf87f1f6742939a9f33114c325f8405b`, test tree `c36c35b55f4d1ad201baee8f2dd3304f41e52079`; CEO source review `8696066c322f7290bde177b9a5b5f5416257ecb7`. The reviewed source/test trees, including original Option A implementation, must match at build time. Only documentation/release receipts may be appended during the authorized release. **Any source/test/functionality change invalidates this automatic authorization** and requires the usual review/Owner decision; do not silently repair with modified code then deploy.

**Executor procedure (authorization is active now):**
1. Read latest `AGENTS.md` and `AI_START_HERE.md`, especially the absolute Owner **agent Computer Use ban**, and original Windows release instructions. Reuse existing authorized release toolchain, path safety scans, and original `scripts/build_windows_release.ps1 -Version 1.6 -BuildOnly`. Keep candidate separate from installed program until verification succeeds. No redundant full source regression if source/tests unchanged; original full 3140 PASS/1SKIP receipt remains traceable.
2. Verify actual candidate EXE/`_internal`, SHA256/full manifest, frozen module equivalence with the approved code tree, frozen `--self-check` exit0 and `RELEASE_SCAN_OK`. If any mismatch, security alert, missing dependency or unowned staging issue occurs: **BLOCKED; leave production untouched**.
3. Prioritize imminent real orders. While old current approved Option A EXE `DB9463D4D1DBDF716C80C8A48A2E5D6E9CB7EBE4BB4254A0A2CD40BEEA440969` is BUSINESS_RUNNING, do not stop during an in-flight transaction, pending Google write, unknown effect, protected page or SMTP/INSO step. Select a verified safe gap; use only original application safe Stop/drain then normal Exit, not force-kill, duplicate-start, destructive lock removal, additional Playwright/CDP client or old-page adoption. **If safe Stop/Exit cannot be achieved without forbidden agent Computer Use, request exactly the manual Owner GUI action needed and HOLD until done.** The Owner's release approval is not permission to violate the global Computer Use prohibition.
4. After confirmed exclusive normal exit, verify existing original program hash/manifests, create **fresh, checksum-verified current DB9463D4 program-only rollback** and consistent protected-state snapshot via existing approved procedure. Preserve immutable latest SQLite/WAL/order/TP/SENT/UNKNOWN/mail data; do not copy any backup data *over* live state or replay uncertain effects.
5. Replace only original installed EXE and `_internal` with verified frozen 7-day candidate; **do not touch** runtime junction/target, config, Vault, original Chrome9222 profile/browser, active pages, protected datasets or unowned files. Verify installed hash/assets, self-check, single-instance, the original real GUI idle state, then resume already-authorized normal business exactly once without changing 900sec/120sec, recipient, source status, manual gates, optional double market actors or any other business policy.
6. Observe only via existing sanitized logfile and non-invasive OS counters. Distinguish `已报价给客户` seven-day age skip (date proxy clearly labeled, no INSO query), original active quotations, TP mid-batch and safe quote resumption, new real order handling, Google timeout recurrence and true errors. Do not synthesize orders/emails, claim actual customer-send precision, or provoke browser/CDP probes; missing qualifying rows are `NOT_VERIFIED`, not FAIL or a reason to manufacture data.
7. On a blocked drain or unknown/unsafe external state, **HOLD while retaining the last known working installed EXE and intact state**. If a fresh install fails after safe swap, follow original safeguarded **program-only rollback** to current DB9463D4 *only when external effects are reconciled*, never restoring older DB/mail ledgers or blindly replaying orders.
8. Update **the existing** `V16_RELEASE_REPORT.md`, this original 7-day task, original V1.6 task and existing JSON evidence with exact installer commit, built/installed SHA and manifest, backed-up old DB9463D4 program, safe drain/exit, protected-state integrity, poststart business/age-skip observations, status and cleanup. Commit and push; deliver direct short business-readable completion to Owner with exact status `BUSINESS_RUNNING`, `INSTALLED_IDLE`, `DEFERRED_BUSINESS_CONTINUITY`, `HEALTH_HOLD` or `BLOCKED`. Include `COMPUTER_USE_NOT_USED`. **Do not route a successful unchanged-code deployment back to CEO; this Owner has explicitly waived that extra gate for this single update.**

**Owner of execution:** Codex Executor. **Source of truth:** this original 7-day task and exact CEO SOURCE_PASS/Owner chat decision. **Completion evidence:** original report/JSON plus actual installed asset hashes and business state. **Cleanup:** retire only task-owned disposable staging as original release rules require; preserve live program, fresh rollback and protected files. **Enforcement:** failed identity, safety, auth or no-Computer-Use checks mean **no forced replacement**; no fake post-deploy success, and any unauthorized changed code must return to normal review.
