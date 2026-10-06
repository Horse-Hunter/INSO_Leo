# RFQ-002 Execution Log — sanitized publication record

## Owner blank-only idle follow-up — 2026-10-06

Supersedes the earlier preserve-Owner-business-tabs decision, not protection of
the Chrome process/context/profile/cookies. Owner wants exactly one blank page
before a row starts and after a normal closed-loop row finishes. Reuse audit:
existing launcher owns attach and synchronous per-row cleanup; added the small
`park_shared_cdp` capability to its existing browser_bootstrap module and invoked
it there. No new browser, adapter, workflow, credential path or business rule.
Blank is created/retained BEFORE closing any old page. Unique context and final
single-blank inventory are checked; failure stops the flow. Manual-verification
stop is not a closed row, so its human-needed page is preserved. Scope is the
dedicated 9222 context only, not other Chrome windows/profiles.

Owner also confirmed personally reducing the browser to one blank. A bounded
live cleanup check used the same canonical helper (no order execution) and
verified a connected browser, one about:blank and identical before/after cookie
records without printing/persisting their contents. After deployment/restart,
read-only inventory again found only about:blank. New pending order was NOT run;
no INSO Save/Save-and-Send, SMTP or Sheets write in this follow-up.

Checks after final source changes:
- `python -m pytest -q tests/launcher tests/inso --basetemp=.tmp/rfq002-blank-focused --tb=short`:
  381 passed, 12.58 seconds.
- `python -m pytest -q tests --basetemp=.tmp/rfq002-blank-full --tb=short`:
  972 passed, 11 skipped, 37.71 seconds; no outbound test SMTP attempts.
- `python -m ruff check src tests` and `git diff --check`: PASS.
- Existing V1.2 build, staged clean scan, frozen self-check and deployed
  self-check PASS. Only EXE/_internal replaced, runtime junction unchanged.
- New EXE SHA256:
  `2EEE1833FA2F2749C1DBE934010CFC0876BBE88A4E61D8783EDEF3611275EEBC`.
- Previous batch-repair assets recoverable at primary-project
  `dist/release-backups/INSO_V1.2-20261006-before-blank-tab-update`.
- Computer-use gracefully closed/reopened the app; exact-path new window
  observed alive. Idle only; no screenshot/pixel-smoke or new business claim.
- Changes: existing launcher lifecycle/helper, four safety regressions, protected
  CDP policy and RFQ records. All previous six-row no-resend evidence remains
  valid, not replayed. Return to REVIEW_REQUIRED for independent new-scope Review.

## Six-row repair and authorized production closure — 2026-10-06 23:07

This entry supersedes the diagnosis-only and older no-live-execution statements
below. Same RFQ, active worktree and feature/v1-2 branch; starting HEAD
`0fe1d5015ff80a4a1cbde44d6af2d683186f1fd5`. No redesign or second workflow.

### Reuse and confirmed causes

- Reused production JSON/config, Core Vault, cached Google grants, official ECB
  FX, Research sources/Excel facts, existing INSO lease/guards/native query,
  workflow ledger, SMTP worker, one-cell status writer and release pipeline.
- Native lower history really progressed sequentially, but page 11 included
  doubled whitespace in an unrelated raw model. Browser innerText collapses
  whitespace, so literal raw/display equality never settled. Render comparison
  now normalizes display whitespace only; raw model/business matching unchanged.
  Read-only fresh-tab verification completed all 16 pages / 158 native rows.
- Another lower fuzzy-search set contained an unrelated suffixed model with
  zero quantity. All pages/IDs remain verified; only exact dup-mpn-v1 models
  enter current inquiry quantity validation. Exact relevant invalid quantities
  still fail closed; old/out-of-window records remain outside the decision.
- Valid native final confirmation returned a raw BillID, but V12Store accepts
  only opaque rec_ references. Existing reconciler now hashes the ID using the
  canonical opaque format; store safety contract was not relaxed.
- Previously completion actions ran only after a whole worksheet batch;
  Research COMPLETED was counted as business completion. Synchronous per-row
  result hook now finishes status write/read-back, due notification processing
  and owned-tab cleanup before any next row. Unknown submission, write-back
  failure or unconfirmed required notification stops the batch.
- Every normal inquiry opens its own tab on the SAME 9222 context, enters via
  login.aspx?t=islogin and native menu, and pins all access/re-login to that
  page. Cleanup handles failed authentication/lease attachment and every
  terminal outcome. Owner-existing pages/profile/browser are never closed.
- GUI reads persisted business/waiting states rather than treating Research
  success as purchase success. Login-interrupted Research persists waiting
  state, not indefinite processing. Login mail explicitly distinguishes the
  INSO_V1.2 program name from the affected collection website.
- Official successful FX is cached for its observation day only; next day
  refreshes. No fixed/fake rate or cached failure was introduced.

### Actual production verification and protected recovery

Owner authorized first ONE unsubmitted row, then the remaining THREE only after
success. The canonical ProductionBackend/coordinator/store support an optional
inquiry-ID scope for bounded execution; normal GUI defaults to all pending rows.
This scope filters both fresh Sheet ingestion and existing due queue claims.
Ignored local helpers only orchestrated that same backend, not a second path.

- First attempt stopped before any purchase dispatch at lower page settlement;
  diagnosis/fix followed. First row then completed normal draft, AI model/brand/
  quantity validation, parent read-back, ONE Save-and-Send, authoritative final
  confirmation, Sheet status transition/read-back and tab cleanup.
- The next batch stopped without submission on an actual IC.net point-click
  CAPTCHA. Read-only inspection verified the challenge and left the tab for
  Owner. Owner personally completed it. No executor CAPTCHA solving/bypass.
- Two remaining rows then completed; the last row's unrelated fuzzy-history
  quantity defect was diagnosed/fixed before its first dispatch. Last row also
  completed the full normal chain. Completed rows were excluded from retries.
- Final fresh Google read and read-only SQLite audit: all SIX incident rows
  have status 发给采购, durable SAVED and PURCHASE_RECORDED; each has exactly
  ONE lifetime SAVE_DISPATCH_ARMED event. Four new authorized dispatches total;
  the original two were NEVER rearmed, replayed or dispatched again.
- THREE qualifying important-order commands have SENT receipts for both
  canonical recipients (six recipient successes). Real SMTP accepted these;
  inbox receipt is not asserted by the executor. Thresholds/content/recipients
  remain the existing canonical V1.2 rules. Prior exception receipts preserved.
- Original two native sent records were independently verified using exact
  model, quantity, Owner-provided inquiry number, native 已发送 status, and
  original armed timestamp ±30 minutes. A SQLite online consistent backup with
  quick_check was kept before audited state recovery and status-cell backfill.
  No pre-dispatch baseline was invented. Existing reconciliation now has an
  explicit owner_confirmed_sent opt-in for MANUAL_REVIEW only; typed authoritative
  singleton evidence must prove model/quantity/time/sent status and an original
  dispatch must exist. Default polling never enables it. Success appends human
  resolution evidence; absence/unknown cannot reopen submission.
- Production Write Gate remains CLOSED for standalone INSO Save Data and
  generic send/submit. Only already-authorized specific Save-and-Send, canonical
  SMTP, and 未发→发给采购 cell transition were exercised. No other Sheet cells,
  protected profile, credentials, prior unrelated orders or CDP ports changed.

### Release and current runtime

Reused `scripts/build_windows_release.ps1 -Version 1.2 -BuildOnly`: build,
frozen dependency self-check and clean staged-artifact scanner PASS. Replaced
only Owner's EXE/_internal; runtime junction unchanged. Deployed self-check PASS.
Full deployed-folder scanner rejects runtime data by design; the generic clean
artifact scan is the STAGING scan, not a claim the local data-bearing deployment
can be distributed. No runtime/customer output/credentials/EXE are in Git.

- Deployed: `D:\Program_Leo\INSO_Leo\dist\INSO_V1.2\INSO_V1.2.exe`.
- SHA256: `C2B46F90BBCD2AD19AC269F3F4459D72942B1B758D83F631316044BA1B44CEE5`.
- Recoverable old asset backup: `dist/release-backups/INSO_V1.2-20261006-before-batch-repair`
  under the primary project. Runtime was not moved/copied into this backup.
- Latest EXE launched normally through computer-use; its exact-path window was
  observed and re-observed alive. Left idle, never clicked Start Inquiry after
  this audit. Screenshot capture timed out (FrameArrived); visual pixel smoke
  is not claimed. Dependency self-check and window launch succeeded.
- Protected 9222 Chrome remains alive. Owner-existing INSO tab deliberately
  preserved; all inquiry-owned tabs cleaned. Human-verification tab belongs to
  Owner following handoff. No new CDP/profile or browser force termination.

Final verified checks (after all source edits and callback stop regressions):

- `python -m pytest -q tests/launcher tests/inso tests/workflow tests/research/test_ecb_fx.py tests/gui --basetemp=.tmp/rfq002-delivery-focused --tb=short`:
  603 passed, 1 skipped, 33.71 seconds.
- `python -m pytest -q tests --basetemp=.tmp/rfq002-delivery-full --tb=short`:
  968 passed, 11 skipped, 37.44 seconds.
- `python -m ruff check src tests`: all checks passed.
- `git diff --check`: PASS, CRLF normalization warnings only.
- Test SMTP replaced by deterministic fixtures, including the two former
  infrastructure leaks; no test outbound mail attempts in final runs.

Current scope is complete operationally; publishing requires independent CEO
Review, not an executor PASS declaration. Local diagnostic/raw evidence and
pre-existing untracked probes are preserved/excluded, never committed.

Pre-publication fetch found CEO-only upstream commits c74e6ee and 7f1caa1,
closing the old ProductID-test checkpoint at 0fe1d50. Fast-forwarded both;
REVIEW.md is preserved untouched. Their PASS does not cover this new batch
source repair. COORDINATION returns to REVIEW_REQUIRED for the new scope.
No production source changed during this integration; no rebuild/replay needed.
Owner's additional new pending inquiry is outside the bounded six-row run;
left for Owner to start from the already restarted latest idle EXE.

## Owner six-row incident — read-only diagnosis (2026-10-06 evening)

Owner reports a six-row batch, lower-history pagination hang, two native sent
records not reflected in Sheets, inaccurate GUI counters and missing important
notification. New explicit Owner rule: every order must open its own fresh INSO
tab, never select a pre-existing INSO page; close the order-owned tab afterwards.
Same protected Chrome/CDP/profile remains mandatory; this is not a new browser.
This entry records diagnosis, not a claim that production fixes are complete.

Read existing SQLite via mode=ro, Research snapshots through existing Excel
reader and approved CDP via an attach-only client; no new page/login/credentials,
dispatch, production state update, notification or Sheets write. Detached only
Playwright, never closed Chrome. Deployed EXE hash matches the recorded a1bed40
artifact; not a stale executable substitution.

Evidence for the six rows (customer fields/record IDs omitted):
- Two have Research COMPLETED, one SAVE_DISPATCH_ARMED each, then MANUAL_REVIEW /
  RECONCILIATION_UNREADABLE. Owner screenshot shows native sent records. Current
  read-only upper exact queries also return one matching record each and pass
  all first-page settlement stages. No queue rearm or fabricated SAVED state.
  Status writer requires durable SAVED, so no status write occurred; not evidence
  of a rejected Google write grant. The precise historical confirmation failure
  stage was not persisted; a later successful read does not prove what failed
  immediately after submission.
- Two have successful Research but UNAVAILABLE duplicate history; no purchase
  state/dispatch exists. They remain ROUTING awaiting duplicate confirmation.
- Two have RETRYABLE_FAILURE / RETRY_WAIT; persisted remarks identify unavailable
  FX (INSO for one, INSO and Findchips for the other). They never entered purchase.
- Only PURCHASE_EXCEPTION commands were created for this batch; all six show
  SMTP SENT in the existing delivery ledger, not new executor mail sends.

Important notification explanation: the large C-tier/low-stock qualifying row
is one of the duplicate-unconfirmed rows. _route_after_research returns before
important-order evaluation on that branch. The two dispatched C-tier rows do
not qualify (one low-stock total below threshold, one high-stock). Thus the
missing eligible mail is blocked by duplicate confirmation, not SMTP transport.
Business ordering must not be changed without canonical rule review.

Code-confirmed lifecycle defect relative to latest Owner rule:
_existing_or_new_login_page prefers existing INSO shell/login tabs;
attach_inso_research_session globally selects a unique shell and tracks only a
newly opened page as owned. Batch readiness is reused while _research_ready.
Final tab cleanup only closes an owned page after an armed dispatch, while
ordinary owned session cleanup is deferred to batch drain. A borrowed old tab
is consequently neither isolated per order nor closed. Future repair must
select the explicit current-order owned page even if Owner has another shell,
retain ownership across re-login/re-lease and clean every terminal path without
closing borrowed tabs or protected Chrome. No such production change yet.

Lower-page inspection: code clicks scoped next-page controls sequentially, not
an explicit page-11 jump. A bounded read-only recheck of the earlier affected
model now fetched four pages / 34 rows successfully. This does not reproduce or
disprove the earlier hang; old page state and its failed stage remain unproven.
GUI get_status counts Workflow COMPLETED (Research), not purchase SAVED: 4 means
four successful Research outcomes, not four sent purchases. RETRY_WAIT/ROUTING
fall through existing display labels and can look perpetually Processing after
stop. Batch completion/mail processing also occurs after coordinator returns
the whole worksheet, rather than immediately after each row; this delays side
effects when an earlier row/read blocks. These are separate from dispatch safety.

No production fixes, database reconciliation, source-row status repair or test
order executed during this diagnostic pass. Already-sent purchases retain their
non-replay durable states; ordinary restart must never be used as a resend.

## CEO B1 ProductID test-contract repair — 2026-10-06

Fast-forward synchronized feature/v1-2 to CEO Review commit 9685a56, read current
Review/Task Spec/Execution Log/module boundaries; B1 is the only repair scope.
Reuse audit confirmed production reader already returns an empty compatibility
product_id and coordinator waits by model, validating model/brand/quantity.
No production deficiency required changes; only two existing test files updated.

AI ready/async assertions now expect the unused empty compatibility field.
Reader test covers absent, empty, matching and unrelated ProductID, all accepted
when business fields are ready. Parent fixtures use wait_for_model; a ProductID
read raises in the stand-in so success proves it is not consulted. Blank or
unrelated parent code no longer rejects valid business fields. Replaced obsolete
parent-id-mismatch diagnostic with actual unreadable-model parent-read coverage;
model/brand/quantity read-back mismatch failures remain explicitly covered.
Legacy read_product_id/wait_for_row adapter compatibility tests remain intact;
they do not assert those helpers are production success prerequisites.

Actual safe/offline commands and results (existing developer Python, sandbox):
- python -m pytest -q tests/inso/test_v12_purchase_writer.py
  tests/launcher/test_v12_composition.py
  --basetemp=.tmp/rfq002-productid-focused-20261006 --tb=short
  -> 91 passed in 1.02s, exit 0.
- python -m pytest -q tests
  --basetemp=.tmp/rfq002-productid-full-20261006 --tb=short
  -> 946 passed, 11 skipped in 33.98s, exit 0. No deselected tests.
- python -m ruff check src tests -> All checks passed, exit 0.
- git diff --check -> PASS; reviewed test/doc-only diff.

Full run reported two existing outbound SMTP attempts from
test_backend_closes_only_owned_browser_after_runtime_thread_exits[False/True]
in tests/launcher/test_release_infrastructure.py. The unchanged suite-wide
SMTP/SMTP_SSL guard blocked both locally before connection; no real email left
the machine. Recorded transparently; unrelated fixtures were not changed under
the Owner's ProductID-only scope. Tests used synthetic fixtures/mocked external
boundaries; no production orders or credentials were used, and no real
Save/Save-and-Send, SMTP or Sheets writes were performed.

Earlier records saying latest full regression was missing or ProductID tests
were stale are SUPERSEDED by this test-only repair and current 946/11 result.
No src, business logic, dependencies, runtime, CDP or packaging changes. Existing
V1.2 EXE remains the a1bed40 production artifact; no rebuild under packaging rule.
Control Room returned to REVIEW_REQUIRED; B1 closure verdict belongs to CEO,
not executor. Raw pre-existing probe files/test runtime remain untracked/ignored.

## Owner-authorized EXE refresh and CEO handoff — 2026-10-06

Reused existing release script/spec and release Python, production source
a1bed4094af8a834483c8f9f7852f6e7de0c7ac4. BuildOnly Version 1.2 succeeded;
staging frozen self-check exit 0 and RELEASE_SCAN_OK. Tcl initialized under
Owner identity; no environment replacement. No production source changed here.

Validated exact staging/deployment roots and child names, no staged reparse
points/runtime, no running INSO executable. Old EXE/_internal moved recoverably
to D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.2-20261006-before-completion-update;
new generic assets copied into D:\Program_Leo\INSO_Leo\dist\INSO_V1.2.
Runtime junction identity/target checked before and after, unchanged; did not
move/copy runtime, delete data/grants, overwrite V1.1 or touch protected CDP.
Deployed frozen self-check exit 0; new executable SHA256
FDAA40FEF27AB83C7C014F2C3BC0FB5072207882DFB1F748AD08050E9597482D.

Window inventory showed prior source GUI already absent, not closed by agent.
Computer-use skill used for attempted EXE startup, but app approval timed out;
no bypass or Start Inquiry. Native GUI launch and packaged full chain therefore
NOT verified this round. No order replay, INSO Save/Save-and-Send, real SMTP,
Sheets update, authorization or credential probe during packaging.

Expanded CEO report with build provenance, Oct 6 repairs/features, verified vs
unverified scopes, original inquiry_id -> Workflow store -> opaque Sheet
identity -> unique current-row relocation procedure. Recorded row movement/
reuse limits and that later statuses require their own authorized transition,
not arbitrary use of the purchase-only helper. No follow-on module implemented.
Updated canonical Sheets/release docs and latest report, not CEO's Review verdict.

Ruff src/tests PASS using existing developer Python; release Python lacks Ruff
(not a packaging dependency). Latest full pytest not rerun; 152 selected checks
are prior feature evidence, older 921/11 full regression is not current-source
proof. Diff check at final publication; only docs staged, raw local probes and
runtime excluded. RFQ remains REVIEW_REQUIRED for independent CEO Review.

## Owner completion status / exception notification extension — 2026-10-06

Owner authorized source status 未发 -> 发给采购 only after purchase success,
exception mail only to the Owner, and bounded tests of these two features.
Task Spec records the narrow Sheets exception; no generic write gate opened.
Returned the requested internal inquiry ID privately to Owner, not published
as customer data here. No INSO writer or order processing was invoked in tests.

Reuse audit: Sheets already owns unique snapshot relocation and RAW single-cell
API updates; OAuth already protects grants by CurrentUser DPAPI. SMTP and V12
immutable command / recipient retry / delivery ledger already exist. Gaps were
the status-specific adapter/guard and post-purchase side-effect connection only.
Extended existing API writer, added status helper and small launcher completion
handler. Existing contracts gain PURCHASE_EXCEPTION notification kind; existing
schema stores string kind without migration. No new transport/config/launcher,
dependencies, browser, CDP, migration, alternate workflow or screenshot path.

Normal production composition invokes completion handler on flow outcomes:
durable SAVED only -> targeted status write; failures -> one immutable command
per inquiry/phase/reason with Owner-only recipients. Mail contains order ID,
model, brand, quantity, source worksheet/row, phase, Chinese explanation and
safe reason code, not raw provider/page/credential output. Unknown dispatch
explicitly says it may already be sent and must not be replayed. Research
retry/failed/manual, duplicate-confirmation failure and purchase exceptions are
covered; original login operator alert now includes affected order details.
Existing notification worker owns delivery/retry and suppresses sent recipients.
Write-back failure keeps SAVED and never invokes purchase; future polls/restart
retry saved status only. In-memory settled cache avoids repeated successful
lookups; fresh read-back of 发给采购 handles a prior uncertain write response.

Tests: final 152 passed in 8.48s for tests/sheets, new launcher completion tests,
launcher backend, existing V12 notifications/SMTP and GUI contract mirrors.
Notification due processing uses current time after completion, not the poll's
earlier start timestamp, so newly created exception commands can send this cycle.
Ruff src/tests PASS; diff check PASS. Initial selected run had one stale login
mail fixture expectation and blocked SMTP attempts in older backend fixtures;
reused original login transport path and mocked send_one in that fixture. Final
run has no outbound-mail guard warnings. Full repository pytest not rerun; prior
ProductID-contract tests are outside this feature-specific validation scope.

Real bounded verification: no write grant existed; Owner completed official
Google OAuth and grant was persisted in the existing protected cache. Subsequent
non-interactive reuse succeeded without another prompt. Owner additionally
instructed no repeated routine consent; canonical Sheets doc records operational
reuse/protection/fail-closed procedure. No consent was automated.

Using only Owner's already-confirmed sent inquiry, targeted status API update
succeeded. First post-write read hit Google 502; idempotent retry found 发给采购
already present, read-back succeeded and repeat call caused no second write.
No other cells or other orders were written. Native purchase state was not
rewritten/manufactured as SAVED; no rearm/INSO repeat or resend occurred.
Separate synthetic local SQLite fixture exercised the new exception command
through real QQ SMTP to Owner only: recipient outcome SENT (SMTP acceptance,
not proof of inbox display). Subject/model visibly denote a test without any
INSO action. Re-enqueue/worker retry caused no additional mail. Fixtures/raw
output/grants/runtime stay local ignored, excluded from Git.

Normal source app restarted gracefully after confirming no active Research;
only Python INSO window closed, protected Chrome not manipulated. New source
window and command line confirmed; default STOPPED, no Start Inquiry action.
Screenshot capture timed out (Tk accessibility/process inventory available),
not used as business-test evidence. Existing EXE not rebuilt in this request.
Changes submitted for independent Review; no self-certified overall RFQ PASS.

## Read-only post-submit confirmation repair — 2026-10-06

Owner confirmed native 已发送 and requested this fix; then explicitly allowed
record/submission time skew within plus/minus 30 minutes. No replay, Save,
Save-and-Send, queue rearm or SMTP was performed.

Reused PlaywrightDuplicateHistoryPage and PlaywrightReadOnlySaveReconciler.
Read-only queries showed response total=-1 can retain a previous pager count;
it is not necessarily a slow paint. Matching response/cache/DOM were current.
The current-page selector also read the first decorative empty em rather than
the numeric last em. Scope pagination to the current upper grid's table-view
and own pager; read em:last-child. First-page-only proof requires page 1 and
row count within page capacity, not min(stale total, capacity). All exact
request/HTTP/JSON/sequence/pending/cache/DOM identity and order guards remain.
Default complete-set and lower seven-day full pagination are not relaxed.

Read-only verification with the repaired adapter returned FIRST_PAGE_SETTLED
True, current page 1, FAILED_STAGE None despite stale total; RESULT_SET_COMPLETE
remained False, not misrepresented as full history. HTTP Date was about three
minutes ahead of local time. Latest Owner rule is absolute difference between
record PEDate and this attempt's submission time <= 30 minutes, while exact
model and changed first-row ID remain mandatory. Removed speculative precise
server-offset code before commit; no new clock contract/dependency.

No pytest, Ruff, fixtures or final-submit tests, per Owner no-test instruction.
Only two production files changed; git diff --check PASS. No fabricated baseline,
automatic SAVED override or rearm for the sent inquiry. Current open process
and old EXE were not replaced; source fix loads on next restart, no packaging.
Prior independent Review/regression do not cover this delta.

## Owner AI preview correction — 2026-10-06 (IN_PROGRESS)

### Owner-run result after source fix

Owner clicked Start, not executor. Read-only local monitoring observed
AI_RECOGNITION_READY followed by SAVE_DISPATCH_ARMED and then MANUAL_REVIEW /
RECONCILIATION_UNREADABLE. No executor click/replay/rearm was performed after
dispatch. Reused the production session and exact upper-query adapter solely
to inspect the outcome; the single matching visible upper row has the requested
model and quantity and native status 已发送. This establishes a saved/sent INSO
record, not downstream supplier delivery. Raw business row data stays out of Git.

Automatic confirmation failed at FIRST_PAGE_SETTLED: request match, HTTP 200,
JSON, exact response rows (one), sequence advancement, pending=false, enabled
button, cache and DOM identities/order all passed. Pagination current page was
None and the native pager total was 1604 despite the exact filtered response
having one row. The first-page completeness assumption therefore rejected a
visible successful submission. No override to SAVED and no second dispatch.
Timestamp-window confirmation was never reached; that remains unverified.
Remaining work is this read-only confirmation defect, not another AI/Save retry.

Owner reported a genuine new inquiry stalled after recognition and authorized
diagnosis only through AI validation, explicitly excluding final submission.
Reused ProductionBackend session setup and InsoPurchaseWriter on the canonical
9222/profile. No polling worker, queue replay, SMTP or persisted INSO action was
run. Default ProductionWriteGate was used; stopped before AI_ENTRY_COMMIT and
Save-and-Send. The one specified inquiry's durable state was VALIDATION_FAILED /
CONTROL_NOT_FOUND with zero SAVE_DISPATCH_ARMED / saved / unknown-send events.

Live diagnostic reproduced recognition in about 1.1–1.3s: exactly one preview
row exposes PartNo, Brand and Qty, but no ProductID input. The original reader
requires all four inputs, returns None and eventually maps to CONTROL_NOT_FOUND;
the GUI's generic validation message is not evidence of a three-field mismatch.
Model and quantity match; the AI brand is a substring of the Research brand,
which satisfies the existing AI_BRAND_V1 policy. Raw values remain local only.
Additional read-only scripts could not inspect the closed operation tab;
second probe's supplementary structure print hit local console encoding, after
the same three-field observation; cleanup ran and no submission occurred.

Owner explicitly clarified that ERP generates its code after AI 保存数据 and
the code must not be checked at either stage. Removed ProductID as a preview
prerequisite and removed active parent-code wait/read/comparison. Preview and
parent model/brand/quantity checks remain unchanged; parent wait now watches
the imported model row. Legacy code helpers/value field remain compatibility
only, unused by this production chain. AI result failures now have the separate
ai-result-read diagnostic step. Reverted the speculative 120s wait change;
the existing 20s ready predicate remains. No parallel production implementation.
docs/modules/INSO.md records the latest Owner correction over old code assumptions.

No automated tests, Ruff, fake submission or real submission run for this fix,
per Owner request. Existing prior regression/Review PASS does not cover this
delta. Source startup for Owner verification is the next step; existing EXE
still contains the old reader until a later authorized rebuild. Only the
specified pre-dispatch failed inquiry was made retryable using the previously
established targeted rearm pattern, after verifying zero dispatch/saved/unknown
events and creating an integrity-checked backup
owner-ai-retry-20261006T065416322727Z.sqlite3. Only its replaceable failed purchase
snapshot was removed and its queue state set QUEUED; append-only events,
notification ledger and every other inquiry were retained. No order was run.
Started existing scripts/start_v12_phase_a.ps1 with hidden console, canonical
runtime reuse, no worker Start action. Native inventory and accessibility
confirmed the Python-owned INSO_V1.2 window; screenshot capture timed out,
accessibility recovery succeeded but Tk did not expose button text. This is
startup evidence only, not proof of fixed business execution. No EXE rebuild.
git diff --check passed. Awaiting Owner's manual run; RFQ remains IN_PROGRESS.

## CEO Review B1 repair — 2026-10-02

Synced feature/v1-2 by fast-forward to CEO Review commit 2f89580. Read REVIEW.md,
this log and FINAL_REPORT.md. B1 is addressed for independent re-review, not
self-certified PASS. Reused existing writer, gates, fake form and store fixtures;
only the two obsolete tests in tests/inso/test_v12_purchase_writer.py changed.
The callable Save-and-Send API is allowed to exist, but default production and
ordinary fake gates reject it before store or click dispatch. Standalone Save
remains closed by default; generic send/submit methods remain absent. The
non-recognized store test retains its Save rejection and confirms unauthorized
Save-and-Send makes no additional store calls and no form events.

Actual offline checks:
- Focused: python -m pytest -q tests/inso/test_v12_purchase_writer.py ->
  56 passed in 0.61s. Initial edit incorrectly expected an empty fake-store call
  list after the existing rejected Save attempt; corrected only that test to
  compare its pre-call snapshot, then all focused tests passed.
- Full: python -m pytest -q tests --basetemp=<new workspace .tmp directory>
  --tb=short -> 921 passed, 11 skipped in 34.07s, exit 0. Default OS pytest temp
  directory initially caused 159 setup permission errors (763 passed, 10 skipped);
  diagnostic confirmed WinError 5 at pytest-of-Leo. Reran the entire unchanged
  suite using a newly generated, non-existing workspace temp path, not by
  excluding failing tests or deleting another user's temporary directories.
- python -m ruff check src tests -> All checks passed, exit 0. This scope does
  not include the previously recorded unchanged release-script style findings.
- git diff --check -> PASS.

Only tests and Control Room records changed; no production source, runtime,
dependencies or build tools changed. No repackaging: existing V1.2 EXE retained.
Tests use synthetic/local fixtures and the existing suite-wide SMTP guard;
no real Save, Save-and-Send, SMTP, Sheets writes, production order/browser action
or old-order replay. First real final submission still belongs to Owner's next
genuine order. Prior statements that no new offline regression was run are
SUPERSEDED by these results, not by any real submission or packaged-chain proof.
RFQ returns to REVIEW_REQUIRED; REVIEW.md remains the CEO-owned prior verdict.

## Publication scope

2026-10-02: Owner explicitly requested committing/pushing the current work to
feature/v1-2 so CEO chat can review it through Git. The accumulated WorkBuddy
and executor source/tests/docs are one RFQ-002 implementation checkpoint.
Original local execution/summary records contained raw business evidence;
preserved unchanged under Git-ignored .tmp/rfq002-before-publish before replacing
these publication records with sanitized technical facts. No production data,
credentials, raw probes, EXE, runtime DB/Excel or screenshots are committed.

Remote fetch found nine documentation/rule commits beyond the local baseline
51d17ba3aac6658bad25e468358aa1e6f51186f9. They change governance and the older
RFQ plan, not production code. Preserve them through a normal merge, not force
push; latest Owner submission/packaging decisions remain explicit in TASK_SPEC.
Independent Review remains required; REVIEW_REQUIRED is not a PASS verdict.

## Reuse and prior Phase A integration

- Reused stable V1.1 config, Sheets/OAuth, Research, Workflow, Core Vault,
  Chrome/CDP, GUI, additive/backup-safe SQLite readiness and release tools.
- Normal production entry composes existing V1.2 workflow directly; missing
  adapters fail visibly, not silently V1.1-only. No alternate production path.
- Shared authentication uses native login -> home -> business-inquiry menu;
  no direct list shortcut for purchase forms. CAPTCHA/OTP/device checks remain
  manual, no bypass. Site-login sweep uses the single protected CDP.
- Duplicate checking uses complete LOWER procurement temporary inquiry history,
  true creator, quantity and timestamps; does not use upper business inquiry
  history or Research quote eligibility filtering. Workflow rolling 168h rules
  remain unchanged. Native paging/completeness reused.
- Completed Research waiting for duplicate confirmation rejoins the normal
  routing without redoing Research, clearing queues or forcing purchase resets.
- Existing native draft/customer/type/purchaser, AI preview/client-side handoff
  and parent model/brand/quantity/product identity validation were reused.
- Explicit native Findchips no-result response for the searched model is an
  empty source outcome, not a technical error; generic blank/error/login/script
  pages and conflicting offers do not become valid no-results.
- Notification decisions use original business rules. Created commands remain
  immutable; sent recipient ledger entries are not resent, existing worker owns
  permitted retries. Real SMTP previously authorized and observed as accepted
  for canonical important/duplicate notifications, not proof of inbox delivery.
- Earlier normal source runs reached duplicate-stop and successful unsaved
  parent draft validation. Raw business evidence remains local and is not in Git.
- Earlier full regression: 926 passed / 11 skipped. This precedes the final
  submission/packaging changes and must NOT be used as their regression proof.

## Latest Owner-authorized submission delta

Owner accepted the unsaved draft results, removed automatic screenshot scope,
authorized a single final 客临时询价 Save-and-Send, relaxed ten-line ceiling and
requested personal Review. Owner expressly forbids executor testing of this
final step; first actual verification is the next genuine Owner order.

Nine existing source files implement this bounded connection; detailed inventory
is FINAL_SUBMISSION_REVIEW.md. No new browser/workflow/config/dependency/migration.
Automatic production draft screenshot hooks and screenshot-only tests removed;
old local evidence preserved.

Sequence: read settled upper first-row ID before draft; existing draft and
AI/parent validation; durable AI_RECOGNIZED; exact authorized final form control;
transactional UNKNOWN + SAVE_DISPATCH_ARMED before one click; Playwright five-
second wait; native surface dismissal; same upper query and first-row new-ID,
model and current-time confirmation; existing saved/manual-review transitions.

Owner confirms native newest-first order: final confirmation uses only page 1,
rows[0]. Adapter first_page_only opt-in retains request/HTTP/JSON/sequence/pending
checks and response/cache/DOM identity and order; proves first-page expected row
count, not complete history. Default complete-set query remains unchanged.
Upper history exceeding one page does NOT block submission. Lower seven-day
procurement history still requires full pagination.

Timestamp parsing reuses Asia/Shanghai parser. Minute-resolution lower bound is
the submission minute; upper bound is post-query observation. Changed first-row
stable ID excludes the previous top row. Missing/stale/wrong first row or lookup
failure -> manual review, never confirmed absence or automatic resend. Record
appearance does not prove delivery to downstream suppliers.

ProductionWriteGate.require_open remains closed. Only explicit normal production
composition injects OwnerAuthorizedSaveAndSendGate. Standalone Save Data, generic
Send and Sheets writes stay closed. Default/Fake gates do not enable the new
action. Unique visible/enabled control, exact ID/role/caption/scope and final
identity recheck precede dispatch.

Any existing purchase state prevents repeated routing/submission, including old
accepted unsaved test drafts. No automatic historical backlog submission. Submit
exceptions do not enter pre-submit session retry. UNKNOWN persists through
restart; baseline is in-memory, so legacy old-record reconciliation refuses new
submission markers on restart. Uncertain outcome requires actual INSO inspection.

Only app-created operation tab is returned after operation contexts end; Owner
tab and protected browser/context stay open. Profile and port remain canonical.

## Packaging and local deployment

Owner explicitly authorized EXE packaging after Review discussion, superseding
prior Phase B deferral. Reused build_windows_release.ps1 and existing spec with
Version parameter, default 1.1 retained and distinct 1.2 staging/artifact names.
Same icon/assets/hooks/scanner/self-check. V1.1 directory never replaced.

Command: powershell -ExecutionPolicy Bypass -File
scripts/build_windows_release.ps1 -Version 1.2. PASS.
Sandbox Tcl initialization failed; same installed Python under Owner identity
returned Tcl 8.6.15. Build collected Tcl/Tk runtime correctly without reinstall.
Clean artifact RELEASE_SCAN_OK; frozen --self-check exit 0.

Deployed EXE: D:\Program_Leo\INSO_Leo\dist\INSO_V1.2\INSO_V1.2.exe.
SHA256: 99F131DBDFC69C961121FF896FF8C9573C0BC0CBAB3D73B1BEFF60455E095D7C.
Local runtime junction points to the active worktree's existing V1.1 runtime;
preserves configs, SQLite, Excel and historic purchase state without copying
business data into the generic artifact. Deployed private runtime directory is
NOT a portable clean distribution. Do not archive its target worktree before
safe runtime relocation.

Normal EXE launch smoke: window INSO_V1.2, responding, nonzero window handle;
default ProductionBackend remains STOPPED. Own smoke instance PID 36596 closed
normally with exact-path validation, no force kill. No Start Inquiry action or
packaged business-chain execution. Protected CDP not accessed by build/smoke.

## Checks and limitations

- Source Ruff PASS; scoped changed-source/test Ruff PASS; PowerShell parse errors
  zero; git diff --check PASS (pre-existing CRLF warning only).
- Expanded Ruff on unchanged windows_release_entry.py found three existing
  style findings; do not claim full-repository Ruff PASS.
- No new pytest/fake dispatch/replay/final-submit test under Owner restriction.
- No production order, SMTP/Sheets/INSO write, credential readiness probe or
  browser interaction during final implementation/packaging/publishing.
- New final submit and packaged complete business chain are NOT verified.
- Publishing this checkpoint does not establish acceptance/Review PASS. CEO must
  review current diff; first genuine final submit remains Owner's responsibility.
- Raw local probes/test output/runtime/EXE are excluded, not deleted. Source
  merged/pushed through normal history; inspect CEO_REPORT.md for Review scope.
