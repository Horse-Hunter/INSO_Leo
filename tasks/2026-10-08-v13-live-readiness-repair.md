# V1.3 live readiness diagnosis and repair
status: review_required
owner: Integration Executor
created: 2026-10-08

## Authority / goal
Owner reports deployed one-click login CDP failure and explicitly requests testing ALL V1.3
features/end-to-end paths, repairing failures and continuing until usable. Exception: DO NOT
send purchase orders or actual emails. Latest deployment/head03f4bf3, reviewed candidate7ECE6917.
This supersedes deployment-only no-live scope for requested functional verification, while
purchase send/real SMTP remain strictly blocked. Original approved release is kept until a
concrete repaired candidate is verified; record source/frozen/live evidence separately.

## Scope / acceptance
Diagnose real deployed CDP login failure first, preserve fixed Chrome/profile/cookies/human pages.
Reuse existing browser/workflow/identity/login/research/quote/GUI paths; no parallel implementation.
Exercise login, read-only research/duplicate/quotation, GUI edits/reruns, Google quote update,
counters/timers/stop and fault recovery as authorized, safe controlled cases and exact readbacks.
A live harness must block Save/Save-and-Send and actual SMTP at concrete adapter boundaries.
Never start an unguarded production loop during this verification. No invented success based
on source-only or idle imports: frozen/real CDP path must be proved. Never repeat uncertain writes.

## Verification
Offline regression + actual deployed/bundled-driver CDP checks; safe guarded end-to-end probes;
focused/full/Ruff/diff/frozen checks for changes. Logs sanitized, secrets/business raw data uncommitted.
Final report distinguishes live proven, offline proven, blocked/UNKNOWN; do not claim full readiness
until failures resolved and required functional verification finished.

## Result
Implementation and permitted verification complete. See 2026-10-08-v13-live-readiness-report.md.
The formal reviewed EXE remains unchanged as Owner chose CEO Review first for the different rebuilt hash.
