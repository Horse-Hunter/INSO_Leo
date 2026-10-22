# Task: V1.4 six Research prices and first-valid 1–6 month windows

status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-22

## authorization / scope
Owner explicitly authorizes Research/necessary Excel adaptation only: add current
IC.net reference price from body > div.navigation > div.cankaoPrice > a > span
to the existing query capture, retain brand/stock, six-source aggregation of
positive RMB candidates, 1→2→3→4→5→6 calendar-month expansion independently for
Findchips/HQEW/Bom.Ai/INSO, first window with valid prices only. LCSC/IC.net are
current prices without month filtering. Reuse calendar_month_cutoff, ECB FX,
matching, stock/fallback/status and existing Excel atomic migration/persistence.
Keep all old Excel records and hidden identities/status, add IC.net column.
No architecture/module/dependency changes, procurement/Google/state changes,
credentials, browser/production/customer operations, live site queries, packaging
or installed V1.4 replacement. Offline synthetic data only. Commit/push original
codex/v1-4-order-mail-inspection; final status REVIEW_REQUIRED for CEO review.

## facts / reuse audit
ResearchService already queries IC.net once for brand/stock and five price
adapters. SourceResult permits IC.net but PRICE_SOURCES currently excludes it;
PriceCandidate supports only1–3. IC.net existing HTML tree/visibility helpers
can parse the exact reference-price path in the same captured page; normal
missing/invalid/zero reference has no candidate, while existing acquisition/
authentication/result errors must retain SOURCE_UNAVAILABLE. No second query.
Existing window rules differ (Findchips/HQEW/Bom.Ai one month; INSO1–3; LCSC one).
Excel already migrates recognized legacy schemas by header and saves atomically;
extend its recognized old five-source schema rather than a second migration.
Raw live page date availability remains UNKNOWN; document only observed parser/
fixture contracts, never treat product/stock timestamps as quotation dates.

## acceptance / verification
Synthetic offline tests: IC.net valid/empty/zero/non-numeric/malformed prices and
technical faults; brand/certified-stock unchanged; one acquisition; six-source
minimum/quantity and FX; all four independent windows1–6 including more recent
price beating cheaper older price, future/>6mo exclusion and invalid/zero quotes
not blocking expansion; no fictitious undated history. LCSC no time filtering
and original tiers/stock/fallback. Excel five-source/older schema read/upgrade
preserves historical fields/styles/identity/status; zero vs technical failure
distinct. Run relevant Research and caller regressions, Ruff and scoped diff.
Retire task-owned synthetic test copies, keep compact local receipts; preserve
real Git HEAD/index/unrelated dirty work and the running install/browser.

## implementation / date capabilities
Reused the existing IC.net query capture, HTML tree and strict-model/brand/stock
logic; added a single positive RMB candidate from the exact reference path.
Empty/zero/invalid/range/foreign-currency reference text has no candidate and
normal output0, not an availability failure. Typed acquisition/authentication/
challenge/result errors remain SOURCE_UNAVAILABLE, displayed temporarily
unavailable with the existing failure remark. IC.net observer/query still runs
once, its brand/stock response can succeed without a price, and it joins the
existing six-result aggregation (no duplicate IC.net failure remark).

All four historical adapters now choose the first nonempty valid window1–6
using existing calendar_month_cutoff, then that window's lowest normalized price.
Findchips considers usable supported-currency/known-stock price tiers when
deciding whether a window has a valid price; an unpriced recent row cannot block
expansion. Normal/out-of-stock pools still use the existing global fallback
policy within the source's first valid window. LCSC entirely bypasses historical
filtering and no longer mistakes cooperation/product update timestamps for
quotation dates; tiers/stock/preorder/fallback unchanged. ECB conversion unchanged.
PriceCandidate supports1–6 and all historical source cells render older month
labels including out-of-stock candidates. No new history fetch/page/module.

Existing parser/capture date evidence, not a new live-site claim:
- Findchips:data-quotedate/data-quote-date; generic data-date ignored; undated
  currently displayed tiers are current price (first month).
- HQEW:quotationDate/quoteDate including existing relative-date formats; missing
  date on current quotationPrice is current price (first month).
- Bom.Ai:quoteDate; undated rows only when explicitly labelled 当前报价/实时报价/现价
  use the passed page capture timestamp. Other undated rows remain unpriced.
  Selected observed-date evidence uses the actual selected record (not an older
  record sharing its MPN/price).
- INSO:existing Stock_VenQuote CreateTime quotation-record time, InPrice/CurrencyID;
  rows without parseable required time remain excluded. No stock date substitution.
- LCSC/IC.net:current display, no historical time filter; no invented history.
Live field presence and history completeness remain UNKNOWN; source first-page
coverage unchanged. Updated Research module and product-baseline facts accordingly.

Excel adds IC.net using the existing header-based atomic migration. Both current
old-five-source header orders and older recognized formats remain readable.
Old source values/rows/identity/status/style/comment/formula and unrelated sheets
are retained; old IC.net cells remain blank, new missing prices display0. Numeric0
is preserved on history read instead of being converted to a missing result.

## verification / delivery
Final combined offline regression:1643 passed,1 skipped in70.02s, covering Research,
INSO/Sheets/workflow/GUI and relevant backend/site/manual/hold/countdown callers.
New cases exercise all four windows1–6, future/>6mo boundaries, newer quote beating
cheaper old quote, per-site independent windows, FX, all six possible minima,
IC.net single fetch and unchanged brand/stock, missing/invalid/zero vs fault,
LCSC no-date/stale/future date with stock/tier/fallback, five-source Excel upgrade
in both header orders without loss. Ruff and git diff --check PASS.
Initial caller run found an old test fake using all PRICE_SOURCES as the five
non-IC adapters; corrected only that fixture list/assertion in the workflow test.
GUI Tcl failed under the sandbox; final suite ran with existing release
dependencies and permitted Tcl initialization, using a synthetic backend only.
No production procurement/Google/order-status/GUI/launcher code changed.

Installed EXE SHA256 remains
fe805ef6d7b051c214cafa0683680a8eec8eaf2c3fb28f384d4ebb25ea0076a0.
No production/customer data/credentials/CDP were accessed, no real website query,
login/order/Sheets/SMTP performed, no package created/deployed, no production
application/browser process started or stopped. Source complete; independent CEO review required.
Task-owned temporary test retirement and original-branch publication receipt are
recorded locally; no generated evidence/workbook/customer output goes into Git.
Retired all five owned synthetic test roots (154236162 bytes), without following
reparse points. Retain only compact ignored logs/manifests under
.tmp/research-six-evidence-20261022; no staging/package was created.
