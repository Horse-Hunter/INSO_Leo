# Task: Idle Research login keepalive

status: complete
owner: Integration Executor
created: 2026-10-07

## Goal / authority
Owner requests after two empty15-minute Research polls /30 minutes without pending未发
orders, reuse one-click login all sites via fixed CDP in background, cleanup then countdown.
Site login problems notify229; keepalive must not block workflow through pause/stop/holds.

## Requirements
V1.3-only optional maintenance (existing operational ledger migration); reuse canonical sweep and site recipes; no second browser/login/SMTP/scheduler thread.
Run only serially at completed poll boundary, before next900s countdown. Require successful
source polling, no pending未发 rows, two consecutive empty polls and elapsed30min; startup
immediate poll alone must not cause a15min trigger. Any pending row resets idle window.
Skip when purchase paused/manual/global stop or stopping. Failed source read is not empty.
Stop checks between sites; preserve bounded per-site login behavior and existing protection.
Success cleanup uses existing park_shared_cdp; failed/manual pages preserved, blank added if
needed. No foregrounding of failed pages in automatic sweep. One-click manual behavior intact.
Reuse durable operational outbox/recipient worker to notify229 with sanitized site/outcome.
Keepalive failure log/notification must not create business holds or change run state.
No production login or real SMTP acceptance, history replay or release installation.

## Verification
Fake clocks/source pending aggregation, thresholds/resets/pause/stop, all-site continuation,
background presentation, cleanup/manual protection, error isolation/outbox and actual poll wiring.
Focused/full safe offline, Ruff/diff, BuildOnly/frozen; commit/push clean local==remote.
CEO independent review REQUIRED. Live login/SMTP remain UNKNOWN.

Owner clarification: automatic maintenance must publish no login report/callback/dialog and
never raise/focus Chrome. Failure detail is not copied into mail. All login routines reused.

## Completion
Implementation complete; independent review REQUIRED before installation.
Focused273 PASS; full1414 PASS/1 SKIP; Ruff/diff PASS; BuildOnly/frozen/scan PASS.
Final maintenance-only20 PASS after test formatting adjustment. No production login/SMTP.
See RFQ-006 FINAL_REPORT latest section for source/release facts and remaining UNKNOWN.
