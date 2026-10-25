# V1.5 TP independent research

status: REVIEW_REQUIRED
owner: Codex
authority: Owner request 2026-10-25; discovery review d67ebfe150340ea90760f5a2e44dcd7b92f8dac4

## Scope and safety

Offline source implementation and synthetic verification only. No real Sheets/CDP,
mail, production DB, procurement, build or deployment. Existing V1.5 worktree;
no copying dirty V1.4 work or merging later unreviewed commits. Owner confirms
original source physical positions do not change by insertion. Source anchor
must still corroborate exact model, quantity and available brand; conflicts hold.

## Reuse matrix / minimal design (recorded before implementation)

| Existing module | Reused public capability | Minimum extension | V1.4 effect |
| --- | --- | --- | --- |
| launcher.google_web / sheets | protected native TSV, document/gid guards, reader retry, schema and source rows | exact RFQ_BRIEF A:Q **read only**, strict header adapter, explicit source pointer validation | default source ranges and write whitelist unchanged |
| research six adapters / runtime | same clients, parsers, MPN/stock/price validation, authenticated sessions and typed errors | TP-only raw candidate projection via existing adapter instances; no second collector/login | ordinary search and 1–6 month selection unchanged |
| research.source_contracts | calendar_month_cutoff | independent TP quote DTO with real quotation date vs current-price provenance | existing PriceCandidate 1–6 contract unchanged |
| research.ecb_fx / fx | same ECB provider and Decimal conversion | TP currency parsing; same-day quote validation; actual min/second without INSO preference | ordinary aggregation unchanged |
| workflow.v12_store / notifications / smtp | same nullable-inquiry outbox, claim, retry, UNKNOWN quarantine, QQ SMTP | TP notification kind, task-linked command key with inquiry_id=None | no fake V1.4 inquiry; same worker/transport |
| workflow SQLite / V13 migration | additive tables, verified backup; existing nullable-outbox upgrade | requirement-kind/source-position task key, generations and CAS claim, durable completion/outbox recovery | no ordinary inquiry state changes |
| launcher.backend | existing poll thread, fifteen-minute wait, manual condition/gate, source recovery callbacks | opt-in TP phase after existing cycle; manual TP action on the same thread | disabled by default; no new daemon/scheduler |
| gui.app / contracts | existing context menu and order action dispatch/history DTO | third action 重跑 TP 价格; expose TP-only historical rows | purchase/quotation actions retain old path |

Independent TP task key includes Spreadsheet/source worksheet/source row/requirement
kind, not price or Brief row or old inquiry_id. Automatic generation runs once;
TP edits do not automatically reopen it. Explicit manual generation revalidates
fresh Brief and source, blocks while any delivery is pending/unknown. CAS prevents
duplicate claims; crash before durable outbox may requeue read-only research,
crash after enqueue reuses immutable command. No synthetic V1.4 parent inquiry.

Selection decision: second-lowest means the next **distinct positive RMB unit
price**, not a duplicate equal-price row. For each site expand calendar months
1..12 until two distinct eligible prices exist (or month 12), then take the two
lowest from that cumulative window. Current prices remain explicitly undated;
unknown historical dates are not replaced with capture time. Preserve stock
classification; global pool uses in-stock/ordinary quotes first, no-stock only
when no ordinary quotes and no technical uncertainty, matching existing fallback.
Global ranking has no INSO preferential override. These choices require CEO review.

The four real TP rows are **not re-read** in this offline phase. Synthetic cases
cover their documented missing-brand/known-brand and existing/no-old-ledger
states, plus conflict/ambiguity variants; no assertion that all four live orders
are presently READY. Live four-row gate stays pending before later activation.

## Acceptance / verification

Cover historical no-inquiry orders, pointer duplicates/conflicts, USD/RMB, stale
FX, month 1..12 boundaries, real dates/current prices, missing/invalid quotes,
per-site/global distinct minima, repeated polls, TP edits, restart and outbox crash
windows, failed/unknown delivery, manual-auto exclusion and existing regressions.
Document actual file/interface changes, results, limitations, full commit SHA.
Final status REVIEW_REQUIRED; no release/live authorization inferred.

## Completion / execution evidence

- Implemented the source-to-TP independent lifecycle, same-adapter TP research,
  same-outbox mail and original poll/manual GUI wiring. Default tp_enabled=false;
  no real configuration, DB or external operation was performed. Actual interfaces,
  changed-file list and risks: V15_TP_RESEARCH_IMPLEMENTATION.md.
- Final targeted: **73 PASS /2.59s** with synthetic Sheets/native UI/source captures,
  DB, transport and poll/manual tests. Same old GUI row and TP-only row can both
  dispatch only the selected TP generation; actual concurrent DB claims have one
  winner. Existing source policy/aggregation/SMTP implementation files remain intact.
- Full tests: **2544 PASS,11 SKIP,2 FAIL /86.48s**. Both failures are the unchanged
  unsettled-manual CDP/GLOBAL_STOP expectations documented in the report. Independently
  reran with all82 src imports loaded from d67ebfe Git blobs, **6 PASS/2 same FAIL/
  19 deselected /4.86s**. No baseline files/branch were changed or tests suppressed.
- Commands: `python -m pytest tests/sheets/test_tp_brief.py tests/research/test_tp.py
  tests/workflow/test_tp_research.py tests/launcher/test_tp_integration.py
  tests/gui/test_manual_order.py -q -p no:cacheprovider --basetemp <owned-temp>`;
  full `pytest.main(['tests','-q','-p','no:cacheprovider','--tb=short',
  '--basetemp',<owned-temp>])` after appending existing V1.4 release site-packages.
  Command-local PYTHONDONTWRITEBYTECODE, PYTHONTZPATH, TCL_LIBRARY and TK_LIBRARY
  reused existing dependencies. Initial missing-PDF/Tcl environment failures were
  resolved without installing anything or changing machine/runtime configuration.
- Existing SMTP test guard blocked two legacy test attempts; no mail left the
  machine. Ruff over all src + changed tests and git diff checks PASS. Only
  synthetic data in tests; no real data fixtures, screenshots, TSV, IDs or prices.
- Automatic approval rejected the first shared-whitelist proposal before applying
  it. Replaced by dedicated read-only interface with unconditional write rejection;
  old range/title/action/write lists remain unchanged and rejection tests pass.
- Retired all six owned helper/test directories after absolute-path/reparse checks,
  **110783232 bytes**. No permission changes, runtime/profile/CDP cleanup, worktree
  deletion, handoff, package or deployment. Original V1.4/main dirty work untouched;
  same V1.5 managed worktree retained for CEO review.
- Remaining limits: two reproducible baseline failures; four live TP rows require
  a separately authorized preflight; actual12-month site coverage/date fidelity,
  future SMTP/migration acceptance and 2026 date provenance remain UNKNOWN.
  Independent TP identity does not require old inquiry_id or Research records.
  No production/live PASS claim. Stop at this review-required delivery.


## CEO independent code review — 2026-10-25

**CHANGES_REQUESTED / REVIEW_REQUIRED — TP live activation, real mail, and deployment NOT authorized.**

Reviewed exact commit `0ffd65407f79c0e4ff4eea880571a6de4e08398d`,
the full delivery/reuse report, TP production source
(`src/sheets/tp_brief.py`, `src/research/tp.py`,
`src/workflow/tp_research.py`, `src/launcher/tp_composition.py`,
new Google/backend/GUI hooks), pertinent existing V1.4 Research,
Google, workflow outbox/smtp, and the new test source. Scope is 22
touched files, default `tp_enabled` off. Source reuse largely matches
the Owner's mandate: existing native CDP TSV and site acquisition
clients/parsers, existing ECB/Decimal, V12 outbox/notification worker/
SMTP, existing poll/manual dispatch, and source-only TP DTO/ranking.
No duplicated browser, site login, SMTP worker or secondary timer was
found. Ordinary Research's existing 1–6-month algorithm, INSO priority,
and ordinary Excel writer are not changed by the new TP research entry.
Synthetic tests/report describe 73 targeted PASS and 2544 full PASS,
11 SKIP and 2 pre-existing baseline failures; CEO inspected code/tests
but did NOT independently run the test environment or live business
acceptance. Reported baseline failure reproduction is executor-only
evidence.

### P1 BLOCKER: TP-specific failures can stop ordinary V1.4 inquiry/quotation

The backend inserts `self._tp.run(...)` inside the **same** `try`
around the standard `poll_loop` and forwards its exceptions to
`_defer_website_poll`, then to `_runtime_error` if not categorized
(`src/launcher/backend.py`). For example, a changed/missing
`RFQ_BRIEF` header raises `ValueError("TP_BRIEF_SCHEMA_UNAVAILABLE")`
from `BriefReader.read`, not a recognized website outage. Thus
`_defer_website_poll` returns False and the main poll worker invokes
`_runtime_error`, setting stop and pausing the ordinary procurement /
quotation loop. TP-only FX/input/mailer/research errors can likewise
propagate from `TpCycle.run`. This violates the approved requirement
that *an optional independent TP task must not bring down ordinary
V1.4 on a TP-local fault*.

Required narrow fix: establish a TP-specific outer error boundary
in the existing single poll/manual architecture, distinguish
TP-local schema/invalid input/FX/indeterminate delivery/research
faults from genuine shared CDP/authorization/production ledger
integrity/security faults, record and expose a safe TP held/failure
state for local faults, and **continue ordinary polls**. Genuine
shared safety faults must retain canonical V1.4 pause/fail-closed
semantics. Do not add a second scheduler, swallow all exceptions,
replay purchase/send, bypass existing CDP protections or enable TP.
Add integration regression proving a synthetic malformed Brief/TP-local
fault does not stop ordinary follow-up polls, and that a genuine shared
infrastructure/security fault is still propagated. For manual TP
action, report the TP-local failure without marking completion or
pausing unrelated business.

### P2 IMPORTANT: O(N^2) repeated Google downloads in TP cycle

`TpCycle.read_orders` calls the live `reader.read_rows(source)`
for **each** populated TP row, even if its task already completed
and needs no research. After **each** research, `TpCycle.run`
calls `read_orders` again to revalidate the one completed order,
re-downloading the entire Brief **and every active TP source row**.
For N active TP rows this incurs N + N*N source read/downloads
within one full run, plus N+1 Brief downloads, rather than a bounded
per-source snapshot + targeted fresh final revalidation.
At the four existing TP rows, a first full pass can mean roughly
20 source TSV read operations and five Brief reads, on top of normal
V1.4 polling. Even future 15-minute cycles with all four tasks
already sent reread all four source rows. This is inefficient and
unnecessarily drives the protected shared Google UI.

Required minimal improvement before activation: still fetch fresh
Brief for due discovery and revalidate **that task** and its source
immediately before enqueueing mail, but avoid rereading other TP
orders during each final check; batch/cross-reference source rows per
sheet when safe (respect live freshness before send), and skip source
reads entirely for automatically completed, non-retryable TP tasks
unless needed to surface status. Preserve the explicit source-pointer
identity verification and post-research source-change hold. Add
counted-read synthetic tests for four TP rows and for already
completed tasks (no redundant source downloads).

### Accepted safeguards and outstanding acceptance

- Dedicated read-only `RFQ_BRIEF` transport preserves existing source
  read/write whitelists and typed native TSV geometry.
- Original source sheet+row and corroborating model/qty/available brand
  anchor are used without inventing a V1 inquiry ID. Snapshot changes
  hold; no old Research record is required for old TP orders.
- TP source selection uses 1..12 months and **distinct** positive RMB
  price levels, truthful quote-vs-current-date marking, INSO priority
  *not* substituted for actual factual minimum, and no-stock fallback
  restricted by technical uncertainty. Four live TP rows still require
  a separately authorized, real-data preflight.
- Per-TP durable generation and existing shared outbox prevent blind
  retry after ambiguous sends; same-thread manual **重跑 TP 价格**
  is not ordinary purchase/quotation replay.
- No actual Windows production SMTP, shared CDP, sqlite migration, or
  full end-to-end 15-minute/12-month website acceptance was executed
  by CEO; source inspection is not a runtime safety sign-off.

**Disposition:** keep `REVIEW_REQUIRED`; resolve P1 and P2 with
scoped code/tests on the same V1.5 branch. Return exact new SHA,
relevant test results and a brief fix map for CEO re-review. No
packaging, installation, production-data changes, or live email
authorization is granted by this review.

## Executor correction evidence — P1/P2 only (2026-10-25)

status: REVIEW_REQUIRED
review_base: c64d9d8076f38d2fe8702f68ab95f612afbcb0f8

- Reused the same V1.5 managed checkout and fast-forwarded cleanly to the CEO
  review. No new worktree, parallel infrastructure, dependency, live config,
  production data access, packaging or deployment. Existing V1.4/main dirty work
  and protected CDP assets were untouched. No handoff was created or consumed.
- P1 RESOLVED for re-review: explicit TP-only schema/data/research/mail composition
  boundary and durable cycle/row/task holds. The additive TP failure table uses
  existing verified migration backup. Existing task/outbox recovery remains the
  authority on pre/post-enqueue retry and UNKNOWN delivery. Manual local failures
  cannot report completion; missing selection is local, corrupt persisted payload
  remains shared. Typed/wrapped CDP/auth/security/SQLite/ledger and unclassified
  faults continue through existing V1.4 recovery/pause/stop paths. No catch-all
  business continuation. Ordinary source schema guards remain GLOBAL_STOP.
- P2 RESOLVED for re-review: fresh Brief due discovery filters durable task states
  before source I/O; one source snapshot per due worksheet, discarded each run.
  Final verification rereads Brief and only the current target's source, binds
  only that target, and compares full order before enqueue. Normalized duplicate
  anchors, missing targets and changed identity/TP still block mail.
- Four-order count tests: same-source initial cycle **5 source reads vs20**;
  two-source cycle **6 vs20**; fresh Brief stays5. Completed next cycle **1 Brief,
  0 source**. One manual target **2 Brief,2 selected-source,0 unrelated-source**.
  Native TSV still downloads a full selected sheet; no new row-read framework or
  relaxed range/write guard. Snapshot reuse is TP-phase-local, not across earlier
  ordinary purchase/quotation writes or later polls.
- Changed files, interfaces and fix map: correction section of
  `V15_TP_RESEARCH_IMPLEMENTATION.md`. Existing collectors, research windows,
  aggregator, ECB implementation, sender and timer are unchanged. The only new
  persistence is sanitized TP fault keys/reasons, not copied business payloads.
- Final targeted **143 PASS /11.01s**: same five test modules as original delivery.
  Includes malformed native/adapted Brief, TP calculation/input/FX/mail faults,
  durable retry/manual failure, two real synthetic ordinary poll iterations after
  TP faults, shared safety stop, cause/context and ledger/auth fault matrices,
  changed target/source refusal, batching/completion/manual read counters, and
  existing TP/outbox/GUI regression. A first harness run was interrupted because
  its substituted runtime-error recorder omitted the stop signal; the harness
  was corrected and all subsequent targeted runs completed.
- Broad regression **2613 PASS,11 SKIP,2 same baseline FAIL /102.10s**. Both remain
  `tests/launcher/test_rfq008_hold_lifecycle.py::test_unsettled_manual_attempt_preserves_durable_old_hold_and_automatic_barrier`
  `[False-failure0]` / `[True-failure0]`: expected V12Fault versus existing browser
  recovery deferral. These are the same two failures independently reproduced
  against the reviewed baseline in the original delivery; their code is unchanged.
  No failures were suppressed. Final scoped run additionally verifies explicit
  InvalidResearchInput isolation added after broad-suite collection.
- Commands: prior documented pytest environment/commands reused, `-q -p
  no:cacheprovider --tb=short --basetemp <owned-temp>`; broad run uses existing
  V1.4 release site-packages for pypdf only, no installation. Ruff over all src
  and changed tests PASS; git diff whitespace review PASS. Existing SMTP guard
  blocked the same two old tests' connection attempts: no real mail or external
  action occurred.
- Retired all **7** owned synthetic test directories after resolved workspace
  path and nested reparse checks, **408322481 bytes**. No permission/ACL changes,
  runtime/profile/rollback cleanup or worktree deletion. Retained canonical V1.5
  checkout `C:\Users\Leo\.codex\worktrees\v1-5-tp-research\INSO_Leo` for review;
  no duplicate V1.5 checkout was created, so prune/removal was not needed.
- Remaining UNKNOWNs are unchanged: separately authorized four-live-row preflight,
  production migration/SMTP, real website date/coverage and 2026 date provenance.
  Unknown infrastructure errors remain fail-closed rather than guessed local.
  Return to CEO for independent review; activation, sending and release stay closed.

## Owner-authorized single-order mail trial — 2026-10-25

Owner now explicitly requests one live trial of the newest dated RFQ_BRIEF row
with valid TP and the resulting mail to the existing TP recipient. Owner confirms
ordinary inquiry/quotation polling is stopped (GUI may remain open). This narrow
authorization supersedes the earlier offline-only restriction for this ONE trial:
read authorized Sheets and the six existing sources, corroborate the selected
source anchor, use existing TP research/outbox/QQ SMTP, send only that selected
TP result to linan229@qq.com. Persist delivery/idempotency in an isolated ignored
local trial ledger, never the production DB. No automatic poll, other recipients,
purchase/quotation, Sheets write, browser/profile reset/foreign-page cleanup,
packaging or deployment. Unknown delivery must not be blindly resent. Source
release remains REVIEW_REQUIRED; this is not deployment or general activation.

Trial outcome: SENT (SMTP accepted), one command / one recipient, no blind retry.
Read four populated TP rows; unique newest rfq_date is 2026-09-17, Brief row31,
source2026 row172. Source anchor corroboration and final fresh Brief/source
verification passed. Existing six-source execution: Findchips/BOM/INSO SUCCESS;
IC.net/HQEW NO_STRICT_MPN_MATCH; LCSC SOURCE_UNAVAILABLE. Valid price facts were
available; no unavailable source quote/date was fabricated. Mail sent through
existing QQSMTPTransport + V12NotificationWorker to the authorized TP recipient.
Ignored isolated trial ledger holds one TP task, zero ordinary workflow items,
one mail command and one SENT recipient. Retain that private delivery receipt to
prevent replay; do not commit it. Disposable composition script retired after
verification. Pre-existing CDP pages were protected using existing keepalive
ownership support; only owned operation pages were retired, client detached,
canonical9222 remained available. No production DB/Sheet write, ordinary order
processing, polling, extra notice, package or deployment. Owner can now inspect
the delivered mail; source status remains REVIEW_REQUIRED.
