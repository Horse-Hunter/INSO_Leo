# Task: purchase quotation follow-up by working hours
status: review_required
owner: Integration Executor
created: 2026-10-08

## Goal / Owner decisions
After the canonical source status transition from 未发 to 发给采购 is confirmed,
record its actual timestamp locally. During existing V1.3 quotation polling,
if that same source is still 发给采购 and elapsed working time is strictly greater
than three hours, enqueue one reminder to linan229@qq.com and shawn@inso-hk.com.
Owner chose local-only timestamps and once per sending episode; historical rows
without a new timestamp are skipped. CEO Review is deferred until this addition.

## Rules / boundaries
Asia/Shanghai, Monday-Friday 09:00-12:30 and 13:30-18:00.
Exclude lunch, nights and weekends; no separate public-holiday calendar was specified.
Reuse canonical source relocation, V1.3-only additive episode sidecar and recipient-scoped
notification outbox/worker. Never create a second scheduler or SMTP implementation.
Record only confirmed source writes, never old SAVED timestamps or first observation.
Skip unresolved/ambiguous/changed identities. Reminder does not block quotation flow.
No real procurement, SMTP test, production DB migration or formal deployment in this task.
No new Google column; no production config/profile change.

## Acceptance / verification
Offline tests: midday/night/weekend/timezone/strict threshold; timestamp confirmed-write
only and no historical backfill; dedup across polls/restart and new episode; both recipients;
source movement/ambiguity/status completion; held rows included; production composition hook.
Run focused/full safe-offline, Ruff, diff-check and final candidate BuildOnly/self-check.
Record final source/candidate hashes and verification limits before renewed CEO report.

## Superseded implementation (fa8201f, never deployed)
Implemented with local PURCHASE_STATUS_RECORDED append-only events after confirmed
status transitions; historical already-sent rows never acquire an artificial timestamp.
PURCHASE_FOLLOW_UP commands reuse the existing recipient-specific notification worker;
the durable event ID provides once-per-episode dedup across cycles and restarts.
Canonical V1.3 source identity binding/relocation is reused before held-row skips.
GUI contract mirror and event wording were updated. No database schema migration needed.

Final focused: 144 passed. Full safe/offline: 1550 passed, 1 environment symlink skip.
Ruff and git diff --check: PASS. BuildOnly/release scan: PASS.
Final frozen self-check, idle GUI self-check and fixed CDP self-check: exit 0.
Candidate EXE SHA256: 22756C738C7DE7DEB278ABB17E8738A4B99C781E0116A71E4A8C1C7FF20E8431

Formal production EXE remains the original 7ECE6917 candidate. No production DB
writes, real purchase, real SMTP, Google source-field edits or deployment in this task.
Calendar treats weekdays as specified; no public-holiday exception calendar requested.
If the process crashes between confirmed remote status write and local event commit,
no timestamp is invented on restart; such an untimed row is skipped rather than falsely timed.
While the application is stopped there is no separate reminder service; overdue reminders
are evaluated at the next normal quotation poll when the application runs again.
Owner explicitly deferred CEO Review; no review was dispatched or marked complete.

## Current repaired representation
Confirmed timestamps/episodes now use workflow_v13_purchase_follow_up_episodes.
Old EventType/kind additions were removed; reminder kind is PURCHASE_EXCEPTION.
See 2026-10-08-follow-up-rollback-report.md for canonical implementation and compatibility evidence.
Current status: REVIEW_REQUIRED.
