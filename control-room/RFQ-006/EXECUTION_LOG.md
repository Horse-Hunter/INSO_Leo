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
