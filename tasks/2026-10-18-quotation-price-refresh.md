# Extend existing quotation poll to lower-price refreshes
status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-18

## CEO整改 / latest Owner rule (2026-10-18)
This supersedes the earlier verified-success-only baseline/refresh-Hold policy
ONLY after a refresh update button may have been dispatched. Do not re-click in
the same run; enqueue229-only uncertainty notice (identity, old/new RMB net price,
manual verification), advance existing comparison baseline, and return a
baseline-only outcome, never Google success or a blocking Hold. Same/higher price
then skips; a further reduction starts an ordinary new update. Pre-click failures
do not advance baseline. Reuse existing PriceStore/outbox/dedup/outcomes; no new
table, approval, scheduler or business state machine. Existing script-settlement
guards must temporarily protect shared input and re-check on later attempts,
not cause a permanent stop for this uncertainty. Real writes/CDP/runtime access,
packaging and deployment are not authorized in this整改. Offline-only tests and
original evidence update, normal V1.4 push, then REVIEW_REQUIRED.

## Owner requirements
Old quotation incident recovered; no further follow-up/replay. Poll statuses
发给采购 / 采购已报价 / 已报价给客户 in the existing scheduler. Look for INSO
quotes in the existing recent3-day (inclusive72-hour) window. Update via existing
quotation-input sub-sheet when a cheaper quote exists or a previous no-stock
zero price becomes positive. Initial 发给采购 processing retains its original
采购已报价 status confirmation. Refreshes of the latter2 statuses preserve their
source status and accept only a valid update popup as success. Reuse code; do not
create another scheduler, login, quote reader, browser or update implementation.

## Reuse audit / verified implementation
Existing select_recent_lowest already implements72h, supplier net-price RMB
comparison, newest-on-ties and positive-price preference over zero. Preserve it.
Current query_quotation_candidates and original relocation wrapper are sent-only.
WorkflowQuotationSource only reads sent/quoted statuses. V13QuotationUpdater
short-circuits quoted rows and validates all success by source status. Existing
holds can close merely on quoted state: that cannot serve as proof for a refresh
whose source status intentionally stays unchanged. Extend those seams together,
not only the initial filter. Existing popup parser accepts one inserted or one
already-existing/skipped row; a skip is not proof of a cheaper-price overwrite.
GoogleSheetsRowReader currently reads A:G identity/status fields, not a verified
existing-price column. Hold persistence strips quotations, so no reliable stored
last-successful purchase-price baseline is currently available there.

## Owner decisions / transport scope (confirmed 2026-10-18)
Compare the local minimum procurement net price keyed by the EXISTING inquiry_id,
never the marked-up customer price in Sheets. For already-quoted/customer-quoted
rows lacking a baseline, first observation records only the procurement baseline;
only later cheaper prices or zero-to-positive refresh. Advance a known baseline
only after verified successful update. The external script already overwrites;
success remains 成功填入：1行. Preserve later source statuses.

ALL production Google operations must use the existing unique CDP Chrome web
session, including source reads/writes, quotation input and sales intent. Close
owned Google operation tabs after use, without touching sales review/other tabs.
Reuse audit: launcher/google_quote_update.py already owns update navigation,
spreadsheet/auth/gid guards, drawing/button selection, result confirmation and
script settlement. Existing sheets readers/writers own schema, identity and
targeted write/readback. Reuse these; no second updater, scheduler or login.
No general web grid range reader/writer currently exists in src or prior tests;
only that missing transport may be added, behind existing domain contracts.
Keep browser UI mechanics in launcher, not Sheets domain logic. All quantities
must retain numeric identity semantics, and raw quotation strings must remain
literal (never evaluate formulas).

## Boundaries / acceptance
Owner additionally requires read-only web reconnaissance of BOTH 2026 and
SHAHAB before implementing Google transport. Authorized: attach to the existing
canonical 9222 session, inspect visible structure/navigation and existing UI
controls using an owned discovery tab, then close only that tab. No API calls,
credential access, edits, update-script execution or production DB changes.
Do not use the Edge sheet tab; Owner requires the unique Chrome CDP session.
Prepare incremental source+tests, protected real-auth/identity/zero/negative/FX
checks, same72h selection and strict lower-price-only trigger; preserve first
quotation behavior and later statuses. Prevent repeated updates of unchanged
prices and preserve failure holds without treating unchanged quoted status as
success. Run focused/full network-isolated offline tests and sensitive diff check;
record minimum evidence here and submit existing V1.4 branch for REVIEW_REQUIRED.
No production credentials, DB/Sheets writes, real quote runs, deployment,
new dependencies or change to INSO/procurement/order-mail/login flows in this
implementation task. Existing running EXE stays untouched. Preserve all dirty
work; clean only generated task-owned tests/builds. UNKNOWN business rules remain
explicit until answered; independent reuse/source audit may continue meanwhile.

## Implementation and read-only web evidence
Reused query_records_by_status, strict original-ID relocation, INSO 72h/raw14
selection, updater, popup parser, hold store, manual retry and scheduler. Extracted
the existing supplier-net-price normalization as a shared pure helper. Added only
one small additive baseline table (inquiry FK + Decimal RMB text); verified
success advances its positive minimum, failed/skipped updates do not. Refresh
holds cannot close just because status is still quoted. Historical quoted rows
without a unique existing ledger binding are skipped without inventing IDs or
creating mass failure alerts; initial sent rows keep original failure handling.
Awaiting/overdue counts and follow-up notices remain sent-to-procurement only.

Read-only reconnaissance used the unique existing Chrome9222 context, never Edge.
2026 header row1: A STATUS, C CLASS, E MPN, F MFR, G Qty.
SHAHAB header row2: B STATUS, D Part Number, E Brand, F QTY.
Native sheet tabs are .docs-sheet-tab with role button; gid comes from confirmed
navigation, never DOM array position. Name box and contenteditable formula editor
were observed. File > Download > TSV worked for both sheets; temporary downloads
were deleted immediately. No clipboard permission or new dependency is needed.
The observed saved-state badge is reused before closing writes.

Real web reads through the new transport passed for BOTH sheets after reusing
the existing 报价工具 onOpen readiness guard. Early experimental SHAHAB reads were
correctly stopped when initialization reset navigation to2026; fixed by waiting
for that canonical readiness and confirming active title + URL transition. Live
source includes empty/non-numeric quantity cells; these remain missing/invalid,
not fabricated numbers. No business values are retained in evidence.

Existing Sheets readers/writers and quotation input remain the only domain
implementations; the new launcher web transport implements their narrow local
service contract using UI, not API/OAuth calls. Source/brand/manual edits,
procurement status, intent status and raw14 input all share it. Existing quote
button/result/script-settlement controls remain canonical. Browser attachments
reuse existing bootstrap/provider; no new profile, login or Browser.close path.
Only owned Google operation tabs close normally; auth/unsynced-write uncertainty
preserves the page and safely stops. Sales review tabs stay protected.

UNKNOWN / not executed: real cell writes, RAW string editor behavior against live
Google, real lower-price overwrites/popups and initial status advancement; no
authorized live business was replayed. These require independent Review and
controlled acceptance before deployment. No package/EXE/runtime/credentials or
production ledger was changed.

## Validation / cleanup / handoff
Focused native Google + quote actions/background ownership + procurement refresh:
64 passed (final focused run). Additional integrated/hold/follow-up/count tests:
131 passed; production/manual/sales/refresh/web focused batch140 passed.
Final full offline regression: **2159 passed, 1 skipped, 77.51s**. Ruff for changed
implementation and new tests PASS; git diff --check PASS. Network-isolated pytest
entry ran with socket connect/connect_ex denied except test-created ephemeral
loopback listeners;9222 was always denied, bind restricted to ephemeral loopback.
Command: python <temporary offline guard> -q tests
--basetemp=.tmp/quotation-refresh-20261018/full-final -p no:cacheprovider --tb=short.
Earlier expected sent-only tests were updated for the new scope; genuine reminder
and ownership regressions were fixed before the final run. No skipped/failing
live write acceptance is represented as a PASS.

Additional read-only inspection confirmed the source's nonnumeric quantities are
literal nonnumeric contents, not numeric display-format loss. They remain
unchanged and invalid under existing business checks; no numbers were guessed.
All native TSV downloads were deleted; all eight owned test directories and
three read-only probe scripts plus the offline guard were retired in this task.
Cleanup checked absolute workspace .tmp paths and reparse points first; normal
and test-matching permissions were used without changing ACLs or forcing locks.
No task-owned disposable build/download/test copy remains. All prior unrelated
dirty work and historical temporary directories were preserved.

Publish only this task's implementation/tests/three module-baseline updates and
this original packet. Normal non-force V1.4 publication is based on remote
a69a6a6d407595505e33298ea36e26bc275c6831 using the existing isolated-index procedure;
the old local checkout HEAD/index and all dirty bytes are preserved. No reset,
stash, rebase, force push, new branch or deployment. CEO review evidence: this
packet, tests/launcher/test_google_web.py, tests/workflow/test_v13_price_refresh.py,
and the scoped Git commit. Next: independent CEO Review; controlled live write
acceptance remains required before any packaging/deployment claim.

## CEO independent review — 2026-10-18

**CHANGES_REQUESTED — one refresh idempotency blocker; do not live-write or package.**
Reviewed actual GitHub code at `23671c7` and the focused test files.
Three-state read scope, original inquiry-ID binding, supplier-net RMB baseline,
historical bootstrap, later-source status preservation and existing CDP browser
read transport match the approved design at the reviewed code level. Executor
reports 2159 offline passing / 1 skipped and real read-only reconnaissance on
both source tabs; CEO did not independently run tests or live writes.

**Blocking, reproducible in control flow:** in
`src/workflow/v13_quote_update.py` `V13QuotationUpdater.update_one`,
after `click_update_quote()`, an `UNCONFIRMED` popup takes `continue`
and `UpdateAttemptUnconfirmed` takes an outer retry. For refresh rows
(`采购已报价` / `已报价给客户`), source status intentionally stays unchanged;
therefore the next attempt can **click the script again after a previous
possibly-successful click**, potentially updating/appending duplicate quotes.
The pre-existing first-quotation status-change shortcut cannot protect refresh.
`tests/workflow/test_v13_price_refresh.py::test_skip_or_unconfirmed_popup_never_advances_baseline`
checks no baseline advance but does **not** assert one maximum click.

**Narrow correction:** Once a refresh script click may have occurred, any
ambiguous click/popup/settlement result must stop further submissions for that
inquiry and surface a durable `ROW_FAILED`/existing hold for manual read-only
reconciliation. Never advance baseline and never infer success from unchanged
quoted status. Keep required auth/ongoing-script tab protection where outcome
is uncertain; do not close a possibly executing page solely to retry.
Allow retry of clearly pre-click read/input/validation failures only. Add
regression tests for unknown popup, click timeout after dispatch, popup timeout
after dispatch and successful refresh, asserting max one click, no baseline
advance on uncertainty, hold across next poll/restart and no other-row replay.
Do not alter reviewed first-quotation behavior or broaden the web transport.

**Acceptance still pending:** Google native RAW14 and targeted single-cell
writes, actual script overwrite, preserved status and session/tab hygiene have
not been live-verified. Controlled real writes require a separately approved,
isolated Owner-attended acceptance plan after code re-review; no production
writes, no packaging/overwrite and no synthetic business replay in this fix.

**Disposition:** Scoped rework only. Existing V1.4 installation, CDP/profile,
local ledger, rollback and dirty work remain protected. Update this evidence,
run network-isolated offline checks, push normal non-force to the current branch
and return `REVIEW_REQUIRED` for CEO re-review.


Owner latest clarification above supersedes ONLY this historical review's
requested blocking Hold / no-baseline-advance policy; its one-click idempotency
blocker, script safety, no-live-write and no-packaging boundaries remain in force.

## CEO整改 implementation evidence (offline only)
Reuse audit: kept ProcurementPriceStore.record/get, BASELINE_RECORDED/QUOTE_FOUND,
UPDATE_RESULT_UNCONFIRMED, existing notify_quotation outbox/recipient/command dedup,
and the existing script MutationObserver/dismiss/owned-tab cleanup. No new table,
business state enum, scheduler, login, approval flow, side database or live access.

Native refresh click now distinguishes failure BEFORE dispatch from a possibly
delivered click. After possible dispatch, unknown popup/read/settlement returns
BASELINE_RECORDED with the uncertainty reason after229 notice enqueue and normal
baseline record. It cannot enter the old four-click retry or ROW_FAILED Hold.
Google success is not fabricated; GUI explicitly says uncertain/notified/continue
checking later reductions. Mail identifies inquiry/model/source location and
old/new RMB supplier net prices; dedup uses existing inquiry/price-transition key.
Enqueue precedes comparison update so a successful baseline advance cannot lose
its notice. Shared ledger/outbox infrastructure errors retain existing safeguards.

An unfinished refresh retains its EXISTING owned Google tab and a single browser
marker. Reuse existing script observer/dialog confirmation to settle it on a later
attempt; while running/dialog pending, return temporary QuotationInputBusy, leave
prices unchanged and defer without Hold/global stop. If no result dialog remains,
require observable script-idle/dialog-free UI quiescence before releasing the owned
surface. Re-check both quote-open and native raw14-write boundaries. Script busy
is not ignored, but its old uncertainty cannot permanently freeze later polls.
Normal source reads/writes/INSO work remain independent. Genuine auth/CDP failures
retain existing security guards. No production browser was contacted for整改.

### 整改 verification / publication
Final full network-isolated offline regression: **2172 passed, 1 skipped, 79.57s**.
Focused quote/refresh/holds/manual-retry checks:161 passed before the additional
pre-click-retry rearming test, which is included in the final full run. Ruff and
git diff --check PASS. Real SQLite price/outbox/hold/cycle tests cover10→8 unknown
(one click, baseline8,229 notice, no Hold/success)→8 and9 skip→6 update; the6-unknown
variant advances6/notifies again. Dedup is tested with equivalent Decimal forms,
only229 recipients, and actual outbox command counts. A following inquiry succeeds
in the same run. Fake native DOM controls cover dispatched click timeout, late
result dismissal, running-script input exclusion and later idle recovery; initial
quotation guards/regression remain passing. No real SMTP, CDP, Google writes,
production ledger changes, package or deployment were performed.

The original CEO review from ce60daf45791a0eb98edda7a1a523a946de143ed is preserved
verbatim above. Only its requested Hold/no-baseline policy is superseded by the
latest explicit Owner decision. Publish this scoped整改 as a normal child of
that remote commit, using the established isolated index and preserving the old
local HEAD/index/all unrelated dirty work. REVIEW_REQUIRED; CEO independent
re-review next. Prior live-write acceptance remains UNKNOWN and unauthorized.
Cleanup: all five整改-owned test directories and the temporary offline guard
removed after absolute-path/reparse checks, using their original permissions;
no ACL changes, force-unlock, browser/profile/runtime or prior-temp deletion.


## CEO independent re-review — 2026-10-18

**PASS — scoped price-refresh uncertainty code review; LIVE WRITE / RELEASE NOT ACCEPTED.**
Independently checked GitHub diff `ce60daf..26b6b3a` and actual updater,
launcher, Google operation-page, outbox, price-store, and related focused tests.
No additional business-code changes requested.

- The Owner's amended rule supersedes the preceding review's mandatory Hold:
  once a refresh click might have been dispatched, an unknown result or
  click/result/settlement uncertainty returns a non-success
  `BASELINE_RECORDED + UPDATE_RESULT_UNCONFIRMED`, enqueues a deduplicated
  Owner-229 price-transition notice before persisting the new RMB comparison
  minimum, and does not enter another update-click retry or durable quotation
  Hold. A definite pre-click failure does not advance the minimum.
- Focused tests with SQLite storage/notification queue and cycle integration
  demonstrate 10→8 uncertain, 8/9 skip, 6 update (or uncertain), no duplicate
  click for the uncertain attempt, no blocking Hold, one 229 recipient, and
  another inquiry processed in the same cycle.
- Browser-visible pending marker and owned-tab/script-idle recovery guard
  defer shared quotation-input reuse while an earlier refresh may still be
  running; scoped synthetic tests cover late popup, running script, click
  delivery timeout and pre-click retry. This is **code-level evidence**, not
  assurance that Google's production DOM/script always matches the synthetic
  surface. Genuine CDP/auth outages can still trigger the established shared
  stop; the Owner's nonblocking guarantee applies to one ambiguous quote
  result, not an unavailable shared infrastructure.
- Executor reports 2172 offline PASS / 1 skipped, Ruff/diff PASS. CEO did
  not independently execute the offline suite, send SMTP, or contact
  production CDP, Google Sheets or INSO. No CI statuses were reported for
  this commit.

**Disposition:** `REVIEWED_DONE` for this scoped code correction only;
do **not** equate with deployed or live-accepted status. Preserve installed
V1.4, profile, database, credentials, rollback and dirty work. Next is
an Owner-authorized, controlled **single-target** live Google web-cell/RAW14
write and quotation script confirmation on a safely disposable/non-business
test target, with readback, non-duplicate result and tab/session checks.
No unapproved business data edits, broad replay, batch automation or
deployment before the live-write acceptance and runtime preflight.
