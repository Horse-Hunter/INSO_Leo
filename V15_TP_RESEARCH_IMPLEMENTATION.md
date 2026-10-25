# V1.5 TP independent research — offline delivery

status: REVIEW_REQUIRED
baseline: d67ebfe150340ea90760f5a2e44dcd7b92f8dac4
branch: codex/v1-5-tp-research
authority: Owner 2026-10-25 feature request; offline development only

## CEO correction delivery (review c64d9d8076f38d2fe8702f68ab95f612afbcb0f8)

P1/P2 only. Existing browser/readers, collectors, ECB, outbox/SMTP, SQLite,
poll/manual thread and GUI paths remain canonical. No ordinary Research policy,
purchase/quotation logic, dependency, runtime config, package or deployment change.

### P1: isolated TP holds, shared failures retain canonical handling

- `TpLocalError` identifies TP-only Brief schema failure in BOTH native header
  validation and the adapter; source-sheet schema/document/gid guards stay shared.
  Malformed Brief values/rows are also explicit TP schema holds.
- `TpCycle.run` is the outer TP boundary on the existing poll/manual thread.
  Recognized TP validation/identity/FX failures, plain TP research calculation
  errors and pure mail-composition errors are held. Per-task pre-enqueue failure
  remains FAILED with a safe reason; queued commands are recovered before any
  retry decision. No ordinary workflow item or fabricated inquiry is inserted.
- `TpStore.record_issues` persists current cycle/row/task holds in the additive
  `workflow_tp_failures` table, including malformed Brief/no-bindable-order cases.
  Migration reuses the existing verified backup before adding either TP table.
  Existing GUI warnings expose automatic holds; manual failures report failure,
  never completion. A later corrected poll can retry pre-mail FAILED tasks.
- `tp_local_failure_reason` positively classifies known TP domains and walks
  exception causes/contexts (including suppressed context). Shared typed CDP,
  authorization, security, SQLite/ledger faults and unknown errors propagate to
  existing recovery/pause/stop handling. ECB untrusted redirects are NOT local
  missing-FX holds. Unknown browser/provider RuntimeError is deliberately not
  guessed to be TP-only. Mail composition alone is pure/no shared I/O, so its
  plain calculation RuntimeError is explicitly local. This is not catch-all
  continuation or a change to the V1.4 fault policy.
- Manual handling uses the same classifier. Missing selection is local; malformed
  persisted order data and local-looking wrappers around shared faults propagate.
  Existing pending/UNKNOWN outbox delivery still blocks resend.

### P2: due-only snapshots and current-target final check

- `read_orders(..., manual_key=None)` reads fresh Brief once, normalizes source
  anchors, checks duplicates and persisted eligibility BEFORE source reads, then
  takes at most one current snapshot per due source worksheet. No cross-poll or
  pre-write snapshot is reused. Completed/non-retryable tasks read no source.
- `_revalidate(order)` fetches fresh Brief and only the selected source, binds
  only the current target and compares the entire TP order immediately before
  enqueue. It never calls `read_orders` or binds other TP orders. Source model,
  quantity, available brand/date, TP and source anchor still must agree. Duplicate
  anchors including `010` vs `10`, removed targets and conflicts hold.
- Counted synthetic four-order run: **20 -> 5 source reads** for one source,
  **20 -> 6** for two sources. Fresh Brief remains **5** (discovery + four final
  checks). All-completed later poll: **1 Brief, 0 source reads**. Manual one-target
  rerun: **2 Brief, 2 selected-source reads, 0 other-source reads**. Existing native
  TSV still downloads the selected worksheet; target-only refers to validation,
  not an invented single-row transport or relaxed range guard.

### Correction file map / verification

| File | Scoped delta |
| --- | --- |
| src/sheets/tp_brief.py | explicit local schema error; malformed-response checks |
| src/launcher/google_web.py | Brief-only header classification; original guards unchanged |
| src/workflow/tp_research.py | persisted TP holds, local boundary, due/source batching, target-only final check |
| src/launcher/backend.py | manual local/shared distinction and missing-selection handling |
| tests/sheets/test_tp_brief.py | malformed schema/value regression |
| tests/workflow/test_tp_research.py | counted reads, final identity holds, durable retry, shared fault matrix |
| tests/launcher/test_tp_integration.py | two actual ordinary poll iterations after TP fault; shared stop/manual/native guards |
| V15_TP_RESEARCH_IMPLEMENTATION.md | this correction map and verification |
| tasks/2026-10-25-v15-tp-research.md | correction execution evidence; REVIEW_REQUIRED |

Final verification and owned-artifact cleanup are recorded in the Task Packet.
All tests are synthetic/offline with the existing SMTP guard. No real Sheets,
CDP, mail, production ledger, purchase, build or deployment was used. Live
activation/date coverage and the previously documented baseline failures remain
outside this correction; no new live acceptance is claimed.

## Reuse audit and design

The [Task Packet](tasks/2026-10-25-v15-tp-research.md) contains the reuse matrix
and minimum design written **before** implementation. The existing V1.5 managed
worktree was fast-forwarded to the supplied CEO review; no dirty V1.4 checkout,
unreviewed later fixes, deployment file or runtime configuration was copied.

| Area | Reused interface / behavior | Necessary extension | Ordinary V1.4 |
| --- | --- | --- | --- |
| Google | GoogleSheetsWebService native TSV, GoogleQuotationUpdateActions guards, source RowReader and retry | dedicated read_brief + exact17 header adapter | shared range/title/write allowlists unchanged |
| Six sources | existing adapter instances and their clients, parsers, MPN/stock validation, source/inso callbacks | TP raw-offer projection; IC.net calls existing search directly | ordinary search() bodies and 1–6 month policies unchanged |
| Dates | calendar_month_cutoff and each site's existing quote-date parser | independent TP DTO with current vs real quote date; BOM is_current flag | legacy observed_at and existing PriceCandidate unchanged |
| FX / ranking | existing ECB provider, USD/RMB quote validation, Decimal, stock buckets | run-local conversion snapshot, factual distinct minimum/second | existing aggregation.py / INSO preference untouched |
| Mail | same V12Store outbox, V12NotificationWorker, QQSMTPTransport | TP_RESEARCH kind, inquiry_id=None, generation-keyed commands | sender, retries and UNKNOWN quarantine unchanged |
| SQLite | existing file, verified backup, reviewed V13 nullable-outbox upgrade | additive workflow_requirements and workflow_tp_failures tables | no fake workflow_items row or ordinary inquiry mutation |
| Scheduler / GUI | same poll thread, 900-second wait, manual condition/gate and Order DTO | opt-in TP phase, third context action, TP historical display rows | no new thread, daemon, scheduler, browser or GUI shell |

Ordinary SourceResult only retains selected prices and omits some individual
quote dates, and ordinary PriceCandidate permits only months1–6. Calling that
result twice cannot safely recover the discarded second quote. Therefore TP
projects the **same existing acquisition clients/parsers** into its own quote
contract; it does not duplicate acquisition/login/browser code. ResearchService
remains the public execution entry point. No dependencies were added.

## Implemented interfaces and behavior

- `GoogleSheetsWebService.read_brief(spreadsheet)` is the dedicated exact
  RFQ_BRIEF A:Q read. Generic get/update `_range`, `_TITLES` and action worksheet
  whitelist remain unchanged. An unconditional write+brief_read rejection is
  checked before any browser operation. Synthetic native UI verifies successful
  full-column reading, original-page preservation, download deletion, and rejection
  of explicit-cell/range/no-geometry writes.
- `BriefReader.read` validates all17 headers and preserves physical row positions.
  `bind_tp_order` uses explicit source sheet+sheet_row with exact full MPN,
  numeric integral quantity and available brand corroboration. SHAHAB date is
  checked against A/DATE. 2026 date provenance remains UNKNOWN, not a fabricated
  match condition. Owner's fixed-source-position rule makes matching independent
  of Brief order and of duplicate business keys at **different explicit anchors**.
  Duplicate Brief anchors and conflicts hold without arbitrary relocation.
- `ResearchService.execute_tp` reuses all six sources and existing retry/session
  callbacks, writes no ordinary Research Excel and needs no old inquiry_id.
  Each source expands cumulative calendar months1..12 until two **distinct RMB
  unit-price levels** exist or month12. Ties do not manufacture a second price.
  Stocked and no-stock buckets are selected independently. Global actual minimum/
  second use normal quotes first; no-stock fallback requires absence of normal
  quotes and of technical uncertainty. No INSO preference override applies.
- Real quote dates are kept. Current IC.net/LCSC quotes have no invented dates;
  Findchips/HQEW undated current quotes are labelled current; BOM's explicit
  current-price marker is retained separately. Unknown historical dates, future
  dates, beyond12-month records and invalid prices do not become historical quotes.
- `TpStore` uses a TP-specific hash of spreadsheet/source sheet/source row/
  requirement kind. Brief row, target price and V1.4 inquiry_id are not that key.
  Automatic generation runs once; later price edits do not reopen it. Manual TP
  rerun creates a new generation with fresh input only after prior delivery is
  SENT or a definite permanent failure (or a pre-mail research failure).
- SQLite immediate transactions exclude competing claims. Research crash before
  enqueue can recover read-only work; crash after enqueue adopts the same immutable
  command. Existing mail retry sends the same command without repeating research.
  SENDING after restart becomes UNKNOWN through the existing worker/store; UNKNOWN
  and pending delivery block manual/automatic blind resend.
- `TpCycle.run` performs fresh Brief/source checks before research and again
  before enqueueing. Source changes/FX problems are held, not guessed. Its mail
  includes customer/source row, MPN/quantity, original TP and RMB conversion,
  stock label/estimated total, six-source minimum/second/date and factual global
  minimum/second. Lower-than-TP or absent valid prices lead with manual urgency.
  Missing price/second/total is explicit, never a false zero. Only recipient is
  linan229@qq.com, through the original outbox and SMTP worker.
- `build_tp_cycle` is opt-in through `tp_enabled: true` in the existing config
  format; default is disabled, and **no real config was changed**. TP follows the
  normal poll on the same thread after its native page scope closes. Manual
  **重跑 TP 价格** is the third menu item and runs in the existing 15-minute idle
  command loop, independent of purchase/quotation actions. TP-only historical
  orders are displayed using a tp_ UI row key, never a fake persisted inquiry.

## Four-target evidence boundary

No live Sheets/SQLite/Research data was re-read during this offline phase. The
following are sanitized **discovery-snapshot** facts, not current READY verdicts:

| Alias | Brief physical row | Discovery source anchor | Brand in Brief | Price parse evidence | Existing inquiry/Research per row | Current verdict |
| --- | --- | --- | --- | --- | --- | --- |
| TP01 | 31 | 2026 /172 | blank | suffix currency text | UNKNOWN | LIVE_REVALIDATION_PENDING |
| TP02 | 36 | 2026 /167 | blank | suffix currency text | UNKNOWN | LIVE_REVALIDATION_PENDING |
| TP03 | 69 | 2026 /123 | present | suffix currency text | UNKNOWN | LIVE_REVALIDATION_PENDING |
| TP04 | 70 | 2026 /122 | present | suffix currency text | UNKNOWN | LIVE_REVALIDATION_PENDING |

Discovery observed four currency-suffixed target strings in total (3 USD,
1 RMB), with no individually published currency assignment. Do not invent that
assignment or current source/ledger cardinality. Synthetic four-row variants
cover missing/known brand, USD/RMB and absence of a V1.4 ledger; additional variants
cover conflicting fields, duplicate/missing anchors, source-state/date changes and
fresh source changes during research. Missing old inquiry/Research never gates
the new TP path. Before any future live activation, validate each actual row and
price under a separate authorization; no mail or TP execution was attempted here.

## Actual changed files

| Files | Change |
| --- | --- |
| src/sheets/tp_brief.py (new) | Brief schema/price/quantity parsing and pointer binding |
| src/research/tp.py (new) | TP quote contract, source projection, FX snapshot, 12-month ranking |
| src/research/bom_ai.py | backward-compatible current-price provenance flag |
| src/research/service.py; src/research/runtime.py | public TP entry and reuse the same FX provider |
| src/workflow/tp_research.py (new) | requirement store, serial cycle, idempotency and mail rendering |
| src/workflow/v12_contracts.py | TP notification kind only |
| src/launcher/tp_composition.py (new) | existing migration/outbox composition and GUI projection |
| src/launcher/google_web.py | dedicated read-only Brief operation, no shared whitelist expansion |
| src/launcher/backend.py | opt-in phase, manual dispatch, TP UI rows and non-inquiry fault handling |
| src/gui/app.py | third right-click action |
| tests/sheets/test_tp_brief.py (new) | price/schema/source identity cases |
| tests/research/test_tp.py (new) | real existing parser projections, dates/FX/windows/ranking |
| tests/workflow/test_tp_research.py (new) | durable dedup, crash/retry/unknown/manual and real concurrent claims |
| tests/launcher/test_tp_integration.py (new) | native read-only transport, old poll/manual path, no-inquiry site faults |
| tests/gui/test_manual_order.py | third-menu eligibility and TP-only dispatch |
| docs/PRODUCT_BASELINE.md; docs/modules/SHEETS.md; docs/modules/RESEARCH.md; docs/modules/WORKFLOW.md | Owner authority and public contract/limits |
| tasks/2026-10-25-v15-tp-research.md; this report | pre-code reuse matrix, execution and verification evidence |

The IC.net/Findchips/HQEW/LCSC/INSO adapter source files, ordinary aggregation, source
contracts, SMTP sender, notification worker/store and Google action framework are
byte-unchanged from the CEO-reviewed baseline. BOM only adds provenance; ordinary
selection code is unchanged. Module dependency directions are unchanged.

## Verification and remaining risks

- Final targeted suite: **73 PASS /2.59s**, new TP tests plus existing GUI menu
  tests. Real concurrent SQLite claims, same-thread idle dispatch, normal 900-second
  polling with TP disabled/enabled, repeated polls, changed TP, historical orders,
  quote dates, leap-day/1..12-month boundaries, mixed FX, stock fallback, missing/
  invalid prices, no fake zero/second, enqueue crash and UNKNOWN quarantine covered.
- Final full suite: **2544 PASS,11 SKIP,2 FAIL /86.48s**. The two failures are
  `tests/launcher/test_rfq008_hold_lifecycle.py::test_unsettled_manual_attempt_preserves_durable_old_hold_and_automatic_barrier`
  `[False-failure0]` and `[True-failure0]`: old tests expect GLOBAL_STOP where the
  reviewed baseline defers browser recovery. They were independently reproduced
  with all82 imported src modules loaded directly from **d67ebfe** Git objects:
  **6 PASS,2 identical FAIL,19 deselected /4.86s**. No test/old behavior changed
  to suppress the failures. Existing suite's SMTP guard blocked both test attempts;
  **nothing was sent**. These baseline failures remain explicit for CEO review.
- Initial collection lacked local pypdf; first broad run additionally lacked Tcl.
  Reused existing V1.4 pypdf/tzdata/Tcl/Tk via command-local paths; no installation,
  dependency addition, machine configuration or runtime mutation. The three
  environment-only failures passed after that correction. Full commands/evidence
  summarized in the Task Packet. Ruff (all src + changed tests) and diff checks pass.
- No live browser/session/grants/Sheets/database/mail/procurement access, package,
  deployment or actual TP task. Websites' actual available12-month history and
  future online date coverage remain UNKNOWN. This code selects only quotes that
  the existing capture actually provides; it does not promise inaccessible history.
- 2026 date derivation and external rfq_line_id lifecycle remain UNKNOWN; explicit
  Owner-fixed source anchors plus fresh key revalidation replace guessed stable ID.
  Future source insertion/deletion/reuse would require re-evaluating this contract.
- Distinct-price/tie and cross-month selection semantics are explicit design
  decisions for CEO review. Real SMTP delivery and cross-version migration need a
  separately authorized live preflight; UNKNOWN delivery has no new automated
  reconciliation/reset UI, and is intentionally held rather than blindly resent.
- An initial shared-whitelist patch was rejected by automatic approval review;
  it was not applied. The implemented dedicated read-only interface leaves both
  old whitelists unchanged and has unconditional write rejection tests.

Source completion is **REVIEW_REQUIRED**, not release acceptance. Keep the same
V1.5 worktree for CEO review and stop at this delivery. All six owned temporary
test/helper directories were retired after path/reparse checks (110783232 bytes);
no runtime/profile/CDP/other-worktree cleanup. No follow-on task started.
