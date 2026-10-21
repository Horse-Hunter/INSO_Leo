# Google read timeout followed by busy page must not globally stop

status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-21

## Owner scope / verified incident
Owner reports repeated Google failures stopping the whole application, requests
locating/fixing the bug, and asks for the most recent global-fault cause.
Installed sanitized log: 2026-10-21 13:14:48.440 google-download-read TimeoutError,
GOOGLE_WEB_READ_UNAVAILABLE; at 13:14:50.486 google-open-sheet QuotationInputBusy,
GOOGLE_WEB_READ_UNCLASSIFIED, then SHEETS_READ_UNAVAILABLE at .489.
The typed busy condition is missing from the read-only transient classifier.
GoogleSheetsRowReader therefore wraps it as ordinary GoogleSheetsReadError;
the existing poll deferral only accepts GoogleSheetsReadUnavailable, and the
ordinary Sheets failure becomes global-stop. This is a recovery-path defect.
The busy exception can mean either a protected pool slot or the three-tab cap;
the historical log does not distinguish them: exact busy trigger is UNKNOWN.
Read-only CDP inspection now shows one program-owned Google page, saved, no
visible dialog/pending-refresh and unsafe predicate false, plus one blank page.
This current state does not prove the historical state at 13:14:50.

## Requirements / reuse
Reuse the original bounded five-attempt read retry, 15-minute next-poll deferral,
single notification, existing native actions, three worksheet slots and page cap.
Normalize only the explicit existing Google busy condition during READ calls.
Verify auth/document/ownership before retry; real credential/auth/schema/security
or wrong-document failures remain stops. Writes and uncertain Script/input work
must never acquire read retry or be closed by read-only recovery.
Only failed READ pages may be rechecked and retired when genuinely safe; do not
leave a stale protection flag permanently blocking ordinary read recovery.
No new framework, credentials, browser configuration, business rule or production
write. Add real-transport/reader/backend poll-loop regression for the complete
timeout -> protected busy -> exhaust -> notify -> next-poll recovery path.
Keep unrelated dirty work and local HEAD/index; normal commit/push on original
V1.4 branch, REVIEW_REQUIRED. No production replay or unrequested deployment.

## Verification / completion
Reproduced before correction using the real Google native transport, reader and
ProductionBackend poll loop with synthetic page/clock/mail: download timeout,
protected busy slot, ordinary Sheets failure, global stop and no next poll.
The same regression now passes: bounded read exhaustion gives one notification
and two virtual 900-second waits, followed by normal next-cycle recovery.

Google web READ-only classification accepts the existing explicit busy condition
and logs GOOGLE_WEB_READ_BUSY. Existing retry/defer/backend policies are reused;
no global exception catch-all or write retry was introduced. Failed READ pages
carry a browser-visible read-failed flag so they can be verified safe and closed
on a later retry/poll/client, before opening a fresh page. Real pending/unsaved
work and unknown/manual pages are not tagged by writes or indiscriminately
closed. Protected pool entries recheck the existing auth/document guard before
returning busy, and their cleanup controller is the actual failing operation.
This prevents stale read protection from accumulating against the three-tab cap.

Final focused/cross-module verification: **387 PASS in 6.76s** across Google
web/actions/tab pool, Sheets, quotation update/discovery and backend tests;
Ruff PASS; scoped diff reviewed. Includes same-poll busy settlement, next-poll
recovery, expired auth remaining a stop, unknown/schema/security stops, no fourth
tab and uncertain writes neither read-tagged nor replayed/closed as recovered.
Initial reproduction was red as expected; two old tests were updated to expect
the new READ-only transient surface instead of raw busy. No dependencies added;
tests reuse release tzdata through command-local PYTHONTZPATH.

Production actions: only sanitized log and read-only CDP state inspection.
No Google data read/download/write, script, email, inquiry/order, restart,
configuration/credential/profile mutation, packaging or deployment performed.
Current installed package therefore still has the incident bug until an
authorized later replacement. Historical exact busy branch and original timeout
cause remain UNKNOWN; this fix addresses the reproduced recovery/global-stop
chain, not a guarantee that Google/network can never fail.

All four task-owned synthetic test directories retired in this task (13946605
bytes); no build/worktree/release copies created. Original local HEAD/index and
unrelated dirty bytes preserved. Remote was fetched before publication and the
five existing source/test files were verified unchanged from the pre-repair
remote baseline, preserving concurrent Review/docs changes. Commit only these
five files plus this packet to the original remote V1.4 branch.

## Owner-authorized installed release
The prior source-only delivery limit is superseded: Owner explicitly requested
packaging/overwrite/run after combined verification. Installed with the INSO
login retry on2026-10-21;1471 combined tests PASS/1 skipped, scanner and staged/
installed/idle GUI checks PASS, normal idle startup responding. Canonical
receipt/rollback/limits: tasks/2026-10-21-recovery-authorized-release.md.
REVIEW_REQUIRED remains; no actual business run or long-running acceptance claim.
