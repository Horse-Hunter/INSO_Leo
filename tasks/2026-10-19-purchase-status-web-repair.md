# Repair confirmed procurement source-status writeback

status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-19

## Owner authorization and scope
Owner confirms the two latest diagnosed procurements were sent; only Google
source status remains. Diagnose/fix the web writeback bug, then recover only
these two source rows through the existing guarded status writer, after fresh
identity/brand/quantity/status checks and durable SAVED verification. Existing
canonical local settlement may follow verified source success. No procurement,
research replay, quotation update, INSO mutation, SMTP, OAuth or packaging.
Use the existing unique CDP attachment and native Sheets adapters; never launch
or close Chrome, change its profile, or affect other owned/Owner tabs. Only
task-owned Google pages/downloads may be opened/closed/deleted. No blanket retry
of uncertain writes. Keep private business data/artifacts out of Git.
Owner additionally requires resolving the latest Google read stop in this same
task. Installed log at 00:06 on 2026-10-19 records FileNotFoundError during
google-download-read, classified as unknown and GLOBAL_STOP. Only loss of the
owned downloaded read artifact may enter existing five-attempt recovery; do not
whitelist unrelated missing files or retry uncertain writes. Keep the preceding
four-download discovery optimization and stop-aware retry policy.

## Reuse audit / evidence
PurchaseCompletionActions records STATUS_WRITE_PENDING on a writer exception;
retry_saved_statuses presently only checks whether pending source status was
manually resolved. Two latest records are durably SAVED but pending status,
and both outbox reasons are GoogleSheetsWriteError. Existing diagnostic output
does not capture the inner write failure. Exact cause is not yet proven.
Reuse write_purchase_status_safely, GoogleSheetsPurchaseStatusWriter,
GoogleSheetsWebService, source schema/relocation and existing local settlement.

## Acceptance / verification
Reproduce the exact write failure, apply minimal correction and regress it.
Retain unique-source proof, sent-or-later non-regression, uncertainty safeguards,
canonical CDP ownership, and the previous discovery/read retry fixes.
Only recover fixed pending->sent status on the two confirmed saved inquiries;
later statuses satisfy success. Verify source readback before local settlement.
Focused and necessary full offline regression must isolate production network,
CDP and browser lifecycle. Publish only implementation/tests/this evidence on
existing V1.4 branch, REVIEW_REQUIRED, preserving dirty work/index/local HEAD.
Clean task-owned test/probe files in this task; no extra report or EXE changes.

## Completion
Owner subsequently authorized packaging/overwrite/launch, confirmed program exit,
then explicitly requested starting inquiry after launch. These supersede the
earlier no-packaging boundary. No unrelated replay or unguarded purchase is added.
The canonical GUI had no command-line start operation. Add one explicit
--start-inquiry opt-in in the same main/instance guard, calling the existing
backend.start ONLY after GUI initialization. Default launch remains idle; no
second worker/launcher/login path. Owner-authorized normal inquiry after launch
may perform its existing business actions and outbox delivery; the repair and
release tools themselves never resend procurement or SMTP.

### Causes and corrections
Writeback: the old formula-bar contenteditable fill did not persist the Sheets
cell model; real readback rejected it with GOOGLE_WRITE_READBACK_MISMATCH, which
was masked by the generic GoogleSheetsWriteError notification. Simply focusing
the formula editor/bulk insertion was also insufficient. Final canonical fix
selects/verifies the exact grid cell, requires focus to leave the name box, types
literal text through native sequential grid keyboard events, then presses Enter.
Existing cloud-save and exported readback remain mandatory. Add fixed safe stage /
reason diagnostics before masking uncertainty, without cell values/page content.
No uncertain write is retried automatically or claimed successful.

During diagnosis one target's status was inadvertently cleared; other source
fields remained intact. Automatic approval rejected a temporary wrapper that
would normalize blank to pending, and that wrapper was deleted without execution.
Owner explicitly approved correcting this one blank cell. Recovery matched its
REAL blank snapshot with the existing relocation primitive, rechecked all source
cells, brand and durable SAVED, wrote only the approved status, independently read
it back and verified all non-status cells unchanged. The second target used the
ordinary guarded pending->sent writer. Both now have actual sent-status readback.
No INSO mutation, research replay, procurement resend, quotation script or SMTP.
Canonical pending-state settlement preserves original procurement/workflow rows;
minimal consistent DB rollback is local ignored, never a Git artifact.

Read stop: installed 00:06 log shows FileNotFoundError in google-download-read,
classified unknown and stopped. Catch missing files ONLY around the owned TSV
path/stat/read and translate to existing transient five-attempt recovery. Ignore
only FileNotFoundError from already-deleted artifact cleanup. Missing runtime /
credential/other files remain immediate stops. A missing readback AFTER input
still stays write-uncertain, with no write retry. Exact artifact-removal actor is
UNKNOWN. Keep the preceding discovery optimization and next-900-second retry.

### Verification
Focused: 143 PASS (1.91s), final native-input focused 84 PASS (1.64s). First full
offline 2243 PASS/1 skipped (77.78s); final full offline **2243 PASS/1 skipped,
75.05s**; Ruff PASS. Production network/CDP/browser launch/close blocked in tests.
After Owner requested automatic inquiry start, the final release-source suite
is **2245 PASS / 1 skipped, 74.88s**; Ruff PASS. New GUI startup tests verify
default idle and explicit-start order: instance guard -> GUI initialized ->
existing backend.start once -> normal GUI run -> normal shutdown/release.
Tests extend the real grid model to reject DOM-only commits; both source schemas,
RAW literal leading zeros/formula-like/multiline text, name-box focus safety,
missing export fresh retry, harmless already-deleted cleanup, unrelated missing
runtime immediate stop, and missing post-write readback without repeat are covered.
Actual backend poller + real guards/grid/simulated outbox prove five missing
exports -> one 229 notice -> next poll recovers with four discovery downloads.
Current receipt covers source status live writes; raw14 overwrite, prolonged
production polling and origin of external artifact loss remain UNKNOWN.

Packaging / deployment / started-inquiry receipt follows after verification.
Task-owned test/probe files will be retired; keep minimum protected rollback.
Both approved source repairs and canonical local pending-state settlements are
now confirmed. Original purchase/workflow item rows remain byte-for-byte equal
at SQL row comparison; first target non-status source columns were unchanged.
