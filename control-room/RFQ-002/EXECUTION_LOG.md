# RFQ-002 Execution Log — sanitized publication record

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
