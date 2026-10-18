# Extend existing quotation poll to lower-price refreshes
status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-18

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
