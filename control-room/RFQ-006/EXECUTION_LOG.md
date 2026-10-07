# RFQ-006 Execution Log

## Baseline / scope
Fetched origin/feature/v1-3 and verified 75b6043c3819339cbd8fe7ad38388de9d484ad1a.
Created Owner-requested independent managed worktree and feature/v1-3-integration.
Main checkout dirty assets and feature/v1-2 / feature/v1-3 preserved.
No handoff file consumed; prior V1.3 worktree retained as reviewed baseline.

## Reuse audit
Reuse canonical ProductionBackend poll thread, V12WorkflowCoordinator cooldown/restart,
WorkflowStateStore SQLite, V12Store migration/verified backup and notification worker/SMTP,
RFQ-004 V13QuotationCycle and RFQ-005 updater, shared BrowserHandle and CoreLoginBridge,
existing production.json and Windows release script/spec/scanner.
Gaps: final serial A->B cycle, durable final ROW_FAILED hold, GUI projection, notification
composition and production quotation geometry. Minimum additive changes only.
Read-only production discovery authorized; business writes/clicks/SMTP not performed by Executor.

## Implementation / isolation
Canonical launcher wires CombinedCycle on the existing production-sheets-poller, not
another daemon. All V1.2 worksheets precede all V1.3 worksheets in one cycle; existing
900-second interruptible wait begins only after complete cycle. Optional RFQ-004
skip/on_result callbacks preserve default behavior and settle RFQ-005 per row immediately.
Reviewed V1.2 coordinator cooldown and restart code unchanged. IC.net/isolated V1.2
faults set QUOTATION_RUNNING and disable only A for subsequent cycles. Typed shared
faults stop both and preserve manual pages before finally cleanup. Existing worker remains
refresh/mail-only, with no concurrent business execution. Shared instance mutex unchanged.
Stop interrupts the next V1.3 safe boundary/wait; existing updater confirms a dispatched
attempt before returning. Poll-owned Playwright client is detached on its owner thread.

V13HoldStore adds workflow_v13_holds to the same SQLite DB. Final ROW_FAILED persists
sanitized operational result plus observed identifying snapshot; quotation payload excluded.
NO_RECENT_QUOTE is never held and is queried each cycle. Crash without final result has
no hold; explicit final failure survives restart. Completion clears only on safely relocated
matching source status 采购已报价; missing/ambiguous source is retained with a safe log.
Holds prevent both query and update. Notification repair on hold revisit is idempotent,
covering crash between hold persistence and outbox enqueue. Same reason/episode one command;
reason change or a newly opened episode creates a new command.

The existing V12 backup helper accepted only the original V1.1-only table set. Extended
that same verifier to reviewed user_version1201 + integrity, so V13 can reuse it instead
of another backup path. V13 migration is transactional and leaves user_version1201;
old migration still accepts it. Existing notification commands gain nullable inquiry FK
for unresolved row/shared operational notices, without manufacturing business inquiries.
OPERATIONAL_PENDING/SENDING/RETRYABLE_FAILURE are processed by the same new worker and
ignored by the old V1.2 worker, protecting rollback. Bound V1.2 notifications unchanged.
Migration copies the complete existing commands; recipient FK/history integrity preserved.
One table is rebuilt transactionally solely to relax nullable inquiry binding, not dropped
history; no second SMTP/notification database. SMTP adapter failures never stop business.

GUI uses existing rows/DTOs, with neutral 等待采购报价, green 采购已报价 and red
报价处理异常，需人工处理. Existing yellow unconfirmed submission/writeback and red
interruption/duplicate states preserved. V1.2暂停 / V1.3正常 has stop-capable running UI.
Safe runtime logging accepts only verified cycle_id/module/inquiry/stage/fixed result codes.

## READ_ONLY_LIVE_ACCEPTANCE
2026-10-07: cached existing Google service used only spreadsheets.get metadata and
values.get. Exactly one metadata title equals 报价输入; real sheetId/gid489913321.
A1:AZ20 and A1:AZ40 return zero cell rows; actual bounded grid response A1:Z40.
No14 headers found. header_row=UNKNOWN, input_row=UNKNOWN, first_column=UNKNOWN.
BLOCKED LIVE CONFIG; no guessed values. Fixed127.0.0.1:9222 probe true and configured
profile equals D:\Program_Leo\INSO_CDP\chrome-profile. No profile/session modification.
Exposed browser inventory contains Edge, not the protected Chrome CDP; do not substitute
another browser/session for live acceptance. Production Google button, login, dialog DOM,
INSO reader live-page structure and Script refresh remain UNKNOWN; no live UI click/query
or raw page capture. LIVE_SELECTOR_ACCEPTANCE=UNKNOWN (metadata acceptance PARTIAL).
No real quotation input/status write, update click, Script, Save/Save-and-Send or SMTP sent.

## Offline verification
Environment: existing Python3.12 and previously approved bundled IANA data through
PYTHONTZPATH=C:\Users\Leo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\tzdata\zoneinfo.
No installed dependency. Deterministic synthetic tests; mail entry points blocked by suite.
RFQ-006/combined tests:38 passed in3.45s (35 workflow +3 actual backend/poll thread cases).
Focused reviewed-engine+integration command, recorded in .tmp/rfq006-focused-final.txt:
284 passed in8.12s. Includes RFQ-003, RFQ-004/B1, RFQ-005, new integration.
Full `python -m pytest -q tests --basetemp=.tmp/rfq006-full-final-verified --tb=short`:
1273 passed /1 skipped in54.65s, exit0. Ruff src/tests PASS; git diff --check PASS.
Previous early setup/coding failures RESOLVED: missing .tmp parent/timezone environment,
synthetic quotation clock mismatch, V1.2-only backup validation, enum mirror and renamed
version expectations. Initial full results are superseded by final verified run.
Focused tests demonstrate real V1.2 coordinator0/1/2/3 rows, terminal no-quote/normal states,
only180-second between rows, no tail wait, local pause continuation, shared stop, actual
combined poll default900-second wait, stop and start nonoverlap while paused, row failure
next row/no cooldown, persistent hold/reason episodes, SMTP pending, nullable identity,
quoted completion, crash-before-final no hold, corrupt hold global stop and backward
migration acceptance. Full run includes reviewed interruption/queued-row/cooldown crash,
query retry/auth/source isolation, GUI yellow/regression and update retry cases.

## Release preparation
Existing release Python/PyInstaller6.16.0 reused via ignored .venv-release junction to
V1.2's environment. Build script/spec extended Version1.3 only; generic staging excludes
runtime/config/credentials/data. Bounded --idle-self-check builds the actual hidden dashboard,
Start disabled, no business thread. Shared normal-launch mutex still prevents two versions.
Owner's existing V1.2 GUI/process preserved. No normal second business app started.
Backup created before build/deploy:
D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-006-before-v13-20261007-144306\INSO_V1.2
Backup and original EXE SHA256:
1A49C9650BA531F2299326FFC89761D0391CD5F2C0FE32327DDD0736BD5C3E84.
No prior V1.3 deployment/build existed at the target; no old backup replaced.

## Final release / deployment
`scripts/build_windows_release.ps1 -Version1.3 -BuildOnly`: build exit0.
Script frozen --self-check exit0; staged scan RELEASE_SCAN_OK. No runtime data in clean stage.
Final V1.3 EXE SHA256:
FB8AA11FC2B300BA1B56D08FD2AC9B6122405E67C31A0361DF21CC09B700EC16.
Deployed path D:\Program_Leo\INSO_Leo\dist\INSO_V1.3\INSO_V1.3.exe.
Deployment self-check exit0. Bounded idle launch/self-check exit0; actual GUI title INSO_V1.3,
state 已停止, Start text 开始询价, GUI rendered, business_thread_started=false.
Existing V1.2 normal GUI/process preserved; no second production cycle. Transient idle
self-check bypasses normal instance guard only with Start disabled and no business thread.
No visual screenshot acceptance claimed; real Tk widget construction/update checked.

Automatic approval review rejected the initially proposed shared runtime junction + change
of shared V1.2 production.json, because that would mutate cross-version production config.
That rejected command did not execute. RESOLVED via safer independent V1.3 runtime config
files, using the existing per-app-root configuration mechanism (same format, not a second
configuration system). V1.2 production/research config hashes matched before/after exactly.
V1.3 config references original SQLite/client-secret/OAuth/profile/research-output assets;
no copied/diverging workflow DB, grant, cookie or profile. Existing production paths were
resolved to their original V1.2 absolute resources. No runtime migration or production Start
executed. Formal ignored V1.3 production.json includes real gid489913321 and null geometry,
BLOCKED LIVE CONFIG / UNKNOWN selector acceptance. Missing geometry fails closed before
any business poll; verified by pure configuration parser tests. All prior assets/logs preserved.

Current V1.2 EXE remains at its original path with the baseline SHA256 unchanged.
No previous V1.3 target existed; new release directory does not overwrite V1.2 or a backup.
Unchanged reviewed feature/v1-2 and feature/v1-3 remain separate baselines; active integration
worktree retained for CEO Review. Original main dirty/untracked files untouched. Temporary
build/test logs remain ignored, not committed. No dependency installed or business data
included in the source delivery. Final status REVIEW_REQUIRED; no Executor PASS or REVIEWED_DONE.

## Remaining live-only requirements
BLOCKED LIVE CONFIG: real14 header layout/header_row/input_row/first_column unavailable
because read-only quotation sheet was empty in inspected40-row range. gid489913321 confirmed.
LIVE_SELECTOR_ACCEPTANCE=UNKNOWN: Google actual button/dialog/dismiss roles and login/session,
INSO reader live-page structure and real Script refresh delay not accepted. Only fixed endpoint
reachability/profile config and Sheets metadata/read access accepted.
Owner must establish/verify input geometry. After that, one explicit authorized live-order
acceptance is still needed to validate quote input, update button, Apps Script popup and source
status transition. Executor did not write any business cells or click any submission action.
Do not interpret offline or packaging checks as production business acceptance.

## Final closure audit / superseding release verification
Found quotation-running login/exit guards and inherited global-stop close wait needed
extension. Fixed GUI/launcher sweep exclusion and close safe-stop while quotation polling;
backend-stopped check accepts fault states only after actual launcher thread exits.
Six regressions verify no concurrent login sweep and responsive exit from paused/global states.
Combined fault classifier now follows shared preparation causes (INSO/auth/Sheets/CDP/DB),
so the existing Research preparation wrapper cannot downgrade a shared failure to local pause.
Six direct/wrapped regression cases cover that boundary; local unknown business fault stays pause.
Added full existing V1.2 notification/history preservation and crash-between-hold/enqueue tests.

Final exact-source results (supersede earlier full/focused/release counts above):
- `pytest tests/gui/test_rfq006_shutdown.py tests/workflow/test_rfq006_integration.py
  tests/launcher/test_rfq006_backend.py --basetemp=.tmp/rfq006-focused-release`:52 passed3.35s;
  combined46 +GUI6. Earlier latest V1.3 focused182 passed0.84s; read/update code unchanged afterward.
- `pytest tests --basetemp=.tmp/rfq006-full-release --tb=short`:1287 passed /1 skipped53.02s, exit0.
- Ruff src/tests PASS; git diff --check PASS. No outbound-mail attempts.
- Rebuilt exact final source through existing build script after checks: build0,
  frozen self-check0, clean staged RELEASE_SCAN_OK.
- Prior deployed V1.3 fully backed up before replacement:
  D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-006-before-final-closure-20261007-145551\INSO_V1.3
  prior EXE SHA256 CADF5EA32B2F443D77BC86871714E042DC3E404D37221394131238CB1E1F8B31.
- Final assets2178 internal files match prior asset inventory; replaced only EXE/_internal,
  keeping runtime untouched. Deployed self-check0 and bounded idle GUI self-check0 again.
- Final V1.3 runtime configuration hashes identical before/after final asset deployment;
  original V1.2 config hashes match the first release backup. V1.2 EXE still unchanged.
- Pure deployed configuration parse confirms GLOBAL_STOP/QUOTE_INPUT_CONFIGURATION_REQUIRED;
  no workflow migration, business poll, website query, SMTP or submission was executed.
- Worktree prune dry-run/actual produced no stale entries; all5 surviving worktrees retained:
  main(existing dirty assets), reviewed hotfix, reviewed V1.2 rollback, reviewed V1.3 baseline,
  and only active RFQ-006 integration. No HANDOFF file exists in active worktree.
- Final staged source review excludes dist/build/runtime/.tmp/.venv-release and all secrets.


## CEO CHANGES_REQUESTED repair and resubmission
The old header/geometry UNKNOWN and BLOCKED LIVE CONFIG entries above are historical and
superseded by Owner correction; do not interpret them as current config requirements.

# RFQ-006 CEO repair submission — 2026-10-07

Status: REVIEW_REQUIRED. Branch: feature/v1-3-integration.
Updated from CEO commit 80d8f3b6ae45ecd3c418896d5c4168637e8c0d30 with fetch / pull --ff-only.
No new branch or architecture. REVIEW.md unchanged (SHA256
2432263F4E89B57CCBFD610156B52BBA86567429A387B12F4AB098B59D662B79).

## Repairs
- B1: src/workflow/v13_integration.py:222. Strict relocation first; original worksheet/observed
  position only blocks automation or reads Owner completion status. Snapshot mutations while sent
  cannot trigger query/update/new hold/mail or new inquiry. Quoted closes hold; missing/unknown retains
  hold while unrelated orders continue. No fuzzy or business identity fallback.
- B2: src/workflow/v13_quotation.py:176 /258; src/workflow/v13_integration.py:261.
  Unknown reader/operation/factory/update/close/result-contract failures globally stop with fixed
  V13_INTERNAL_FAILURE. No row hold or later query. Typed V13SourceRowError and normal RFQ-005
  retry exhaustion stay row-local; shared DB/Sheets/CDP/auth faults keep reviewed global scope.
- Website229: src/launcher/v13_integration.py:103; src/launcher/backend.py:945.
  Every SOURCE_UNAVAILABLE site is notified via the existing ledger/QQ SMTP worker. Closed categories,
  inquiry/site/category durable dedup, known MPN, owner linan229@qq.com; no raw provider error/HTML/token.
  IC.net pauses V1.2, INSO authentication stops globally, other sites continue. Existing IC/INSO duplicate
  manual/fault alerts suppressed. Pending SMTP retry changes no business scope.
- Headerless input: src/sheets/quotation_input.py:21 /86 and src/launcher/v13_integration.py:15.
  Removed header_row/header_range and header reads/equality checks. RAW14 order remains INSO canonical
  QUOTATION_COLUMNS. Metadata binding remains mandatory before every write and UI open; malformed
  title/gid globally stops with zero write/open/click. Exact blank/leading zero/decimal/whitespace/newline
  payload and readback remain verified offline.

## Configuration and read-only evidence
QUOTE_INPUT_GEOMETRY CONFIRMED; header NONE / NOT APPLICABLE.
Target: 报价输入!A1:N1. Own V1.3 production config: gid=489913321, input_row=1,
first_column=1, header_row absent. Existing V1.2 config bytes unchanged.
Read-only API metadata again proved unique title 报价输入 and sheetId=489913321.
Only spreadsheets.get metadata requested; no grid reads/writes in this acceptance.
更新报价 DOM UNKNOWN: native Chrome window inventory only about:blank; browser DOM surfaces
expose Edge/IAB, not fixed production Chrome. Edge is not substituted. No UI input/click/navigation.

## Exact-source checks
- Hold mutation regression:12 status/mutation cases + deleted/unrelated-row continuation PASS.
- Unknown exceptions:12 RuntimeError/ValueError reader/operation/factory/update/contract/close cases PASS;
  typed row-local updater error remains ROW_FAILED; no new hold/mail/inquiry for unknown errors.
- Website229 regression:24 six-site/four-reason cases PASS, durable dedup, fake retry transport,
  fixed recipient and sanitized body, preserved scope. Research optional-site continuation PASS.
- RFQ-004:47 passed0.67s. RFQ-005:93 passed0.59s.
- Combined RFQ-006 workflow/backend/GUI:102 passed6.97s.
- Focused read/update/integration total:242 passed across the three disjoint suites above.
- V1.2 workflow/RFQ-003/backend:243 passed,1 skipped16.86s.
- Full safe/offline:1334 passed,1 skipped58.66s; exit0, no outbound-mail attempts.
- Ruff src/tests PASS; git diff --check PASS.
- Canonical build_windows_release.ps1 -Version1.3 -BuildOnly exit0.
- Frozen/deployed self-check exit0; staged RELEASE_SCAN_OK.
- Idle GUI exit0: INSO_V1.3, 已停止, gui_rendered=true, business_thread_started=false.
  Start was disabled by the diagnostic; no business worker was invoked.

## Local deployment and rollback
New V1.3 EXE SHA256: 96765BB7BD59E627A33CC5621BECAEEC03D0BE677B628085969C2AA3C5DAFDD0
Backup: D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-006-before-ceo-repair-20261007-153211\INSO_V1.3
Backup old EXE SHA256: FB8AA11FC2B300BA1B56D08FD2AC9B6122405E67C31A0361DF21CC09B700EC16
Deployed executable/_internal only;2178 internal files verified against staged hashes.
V1.3 own runtime configs retained during asset replacement; shared DB/OAuth/profile paths unchanged.
V1.2 EXE SHA256 unchanged:1A49C9650BA531F2299326FFC89761D0391CD5F2C0FE32327DDD0736BD5C3E84.
V1.2 production/research JSON byte hashes match pre-repair values.
No dependencies installed. No credentials, generated release files or production payload committed.

未执行真实 A1:N1 报价写入、更新报价、Apps Script、Save、Save-and-Send或真实采购。
Live-only UNKNOWN: actual INSO quotation DOM, 更新报价 role/locator uniqueness, Google login/session,
Apps Script execution/popup, inserted/already-existing feedback, source-status transition and refresh delay.
Separate Owner authorization is still needed for one controlled live acceptance.
The previous geometry BLOCKED LIVE CONFIG conclusion is superseded by Owner confirmation;
live business acceptance itself remains UNKNOWN. CEO review is required; no follow-on task started.

## Controlled button path acceptance / readiness repair — 2026-10-07
Owner resumed the single existing quotation test; this is separate from RFQ-007 offline sync.
Fixed Chrome/CDP reused; no browser/profile/cookie reset, no procurement/full scheduler.
Initial DOM capture proved drawing overlay existed before visible drawing/custom menu finished
loading. After observed 报价工具 readiness, one canonical click returned and one Script execution
request was observed. Real modal body: 更新完成 / 成功填入0行 / 已有价跳过1行.
Dismissed only that exact modal's unique 确定; script running notice ended. Three bounded read-only
status checks remained 发给采购. Owner confirms this is expected: source was manually restored
and existing-price Script skip does not rewrite status. Do not repeat submission or alter source.
Button -> Script -> already-priced popup path CONFIRMED; first-insert path remains UNKNOWN.

Canonical source improvements:
- GoogleQuotationUpdateActions waits for exact observed 报价工具 menu visibility, bounded30s,
  before unique control discovery/writes and again before clicking. Returns promptly when ready;
  no fixed sleep, coordinates, cell clicking or direct Script invocation. Playwright click retains
  its visibility/stability/hit-target checks; ambiguous/missing controls fail closed.
- Result dialog identified by observed body title (accessible name may be absent); both original
  报价更新完成 and actual 更新完成 supported. Stale result prevents another click.
- Pure popup parser accepts actual 已有价跳过 while keeping strict single-row counts;
  contradictory, duplicate, negative, multi-row and unknown feedback remain UNCONFIRMED.
- Source-status completion policy and Script code unchanged. Expected manual-reset status is
  not represented as new status-write acceptance. No production data adjusted to force success.

Verification: button/parser/updater focused101 passed0.58s; full safe/offline1367 passed,
1 skipped56.16s; Ruff --no-cache PASS; git diff --check PASS.
The first focused iteration found only a fake-locator Match-to-int error; fixed fake boolean
conversion and reran; no failed production tests remain. No additional live click for verification.
Changes are in existing RFQ-006 worktree source, not RFQ-007 reviewed sync delivery; no build,
deployment or published runtime change for this repair. Raw screenshots/output stay ignored .tmp.

Owner-confirmed popup latency: read_update_result now waits up to30s independently of
click/navigation10s; separate readiness/result settings. Focused101 passed0.59s, Ruff/diff PASS.
A pending Script result remains an explicit wait, not immediate success.

## Final Owner rule / verification — 2026-10-07
Latest30s status requirement supersedes earlier unconditional existing-price acceptance.
Inserted1 and skip1 both pass Script parsing; unresolved source status creates existing durable
SOURCE_STATUS_NOT_UPDATED hold, pale-yellow GUI, warning log and229 notification. Script is never
repeated after confirmed success; Script alone clears input. Research NO_MATCHING_PRODUCT alone
adds Shawn; other recipients unchanged, command payload version changed only in this case.
Final focused462 PASS24.32s; full1393 PASS/1 SKIP55.85s; Ruff/diff PASS.
BuildOnly/frozen self-check/scan PASS; separate candidate idle GUI PASS/no business thread.
Candidate EXE6B9248BB591F4A43885CA32399F2835F9FB3051AFF20BB31A4633B9F8C3625EB.
New increment REVIEW_REQUIRED; installed release/configs not overwritten pending independent review.
RFQ007 approved five-file patch/B1/cooldown preserved; CEO review files untouched.
No additional live update, replay, procurement, Save-and-Send or SMTP acceptance after known skip.
See final report for file-level implementation locations and exact current evidence/UNKNOWN limits.

## Latest Owner120-second increment — 2026-10-07
Base e8ae7e9880fdcce4ffd200c1366b1bb5b1c02a71; current branch feature/v1-3-integration.
Owner expanded the normal Research row request to all fixed180-second waits. Production diff:
- src/workflow/v12_flow.py:168: normal Research/purchase row wait120s.
- src/workflow/inso_query.py:30: shared INSO duplicate/history/quotation query retry120s.
- Existing backend deadline and GUI rendering reused unchanged: 冷却02:00 then01:59.
- Existing interruptible Event.wait, four total query attempts, close-before-retry, no final-row
  cooldown, V1.3 normal row0s and combined scheduler900s preserved.
- Chrome configured timeout maximum180s remains a validation bound, not a fixed180s wait;
  default30s and fixed browser/session protections remain unchanged.
Latest exact-source focused289 PASS12.18s; full1394 PASS/1 SKIP58.08s; Ruff/diff PASS.
BuildOnly/frozen self-check/RELEASE_SCAN_OK PASS. New candidate EXE SHA256:
BFD2BAFF59E19D46D31DA3E8BFEE81968B5C860D4EF0A3FF2A54F7EA21F52F30.
This candidate supersedes the prior candidate hash/test totals; prior idle diagnostic remains
historical evidence only, not a new idle run. Installed release/configs not overwritten.
All earlier quote robustness/status-warning/Research-mail changes remain in this branch.
No real business action/SMTP/order replay; no dependencies. Independent review remains REQUIRED.

## Idle Research login keepalive — 2026-10-07
Owner requests independent V1.3 maintenance after consecutive empty Research polls and actual
30 minutes. Base d8204b5; previous120s interval, quote selection/update/status warning and
Research-only Shawn recipient changes retained. New increment remains REVIEW_REQUIRED.

Canonical V12FlowCoordinator observes pending未发 records across all worksheets without an
extra Sheets read; begin_poll_cycle resets observation. Any pending row resets idle window,
including invalid/preexisting rows, avoiding false empty detection. Failed reads never reach
the maintenance boundary; purchase pause/manual/global/stop conditions skip maintenance.
V1.3 backend runs maintenance serially AFTER completed combined business work and BEFORE
notifications/next900s countdown. Two empty polls AND elapsed30min are required; the immediate
startup poll cannot cause a15min refresh. Restart begins a fresh idle window.

Reuse _run_login_sweep/sweep_sites and all existing site login recipes. Borrow active poller
CDP rather than creating a second Playwright; otherwise attach fixed Chrome using existing
acquirer. No new scheduler/worker, login recipe, browser/profile/cookie or SMTP system.
Background sweep does not publish SiteLoginReport/callback/popup or bring failed tabs to front.
Site failures continue other sites, generate sanitized operational owner229 outbox commands,
and never produce business hold/pause/global stop. Notification insertion errors log warning.
Stop checked between sites and immediately after sweep, respecting existing bounded site waits.

All-success cleanup uses existing park_shared_cdp with a blank background tab. Failed/manual
or preexisting nonblank pages are preserved; successful owned sweep page is closed, Chrome stays
open. Existing manual one-click report/foreground behavior remains intact. New idle window begins
after sweep completion, followed by ordinary15min countdown; failure does not block that countdown.

Exact verification: focused273 PASS16.49s; final maintenance20 PASS1.17s;
full safe/offline1414 PASS/1 SKIP55.90s; Ruff/diff PASS. BuildOnly/frozen self-check/scan PASS.
Latest candidate EXE6FE03F2442377CA49A1A919A1715C401F83B8C481033F98802017AE8F11157B9,
superseding earlier candidate hashes. Installed release/configs not overwritten pending Review.
No real login/SMTP/order replay/quotation update/purchase; real keepalive login and SMTP delivery
remain UNKNOWN. No dependency added; CEO review files unchanged.
