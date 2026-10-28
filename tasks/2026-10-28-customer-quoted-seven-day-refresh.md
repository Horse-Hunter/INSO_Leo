# Owner change — stop INSO quote-refresh for customer-quoted orders older than one week

status: REQUIREMENT_RECORDED / NOT_IMPLEMENTED / NOT_DEPLOYED
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

This task records the requirement and agreed practical timestamp strategy; **no new program code or production executable has been changed here**. Original approved Option A controlled release retains its own SHA and scope.
