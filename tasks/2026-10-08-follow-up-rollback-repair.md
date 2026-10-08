# Follow-up rollback compatibility repair
status: review_required
owner: Integration Executor
created: 2026-10-08
base: e0ea036ca90437e7a31794d5a15323785f450b45

## Scope and authority
Repair only B1 in CEO CHANGES_REQUESTED; preserve original CEO Review file verbatim.
Local confirmed sending episodes move into a narrow V1.3 additive sidecar table
in the same workflow DB, with canonical inquiry binding. Old event/kind enums
must not be expanded or written. Reuse PURCHASE_EXCEPTION outbox/worker.
Business working-time/source/dedup rules remain unchanged.
Confirmed remote write followed by local sidecar failure must propagate the
existing GLOBAL_STOP/WORKFLOW_LEDGER_UNAVAILABLE boundary, never requeue purchase.
Remove the optional new GUI event message rather than polluting the old ledger.

## Verification and boundaries
Run actual old V1.3 03f4bf3 and fetched current V1.2 readers/startup in isolated
subprocess source snapshots against a DB touched by new synthetic status-write,
sidecar and pending/retryable reminder logic. No substitutes for old readers.
Focused/shared/full safe-offline, Ruff, diff-check, BuildOnly/release scan and
frozen dependency/idle/CDP probes required. No real orders, quotes, SMTP, Google
writes or production loop. Formal releases/DB/config/credentials/profile unchanged.
Frozen CDP probe must use isolated copied config with persistent cookie backup
explicitly disabled to avoid writing production backup; attach/detach only.
Finish with commit/push and REVIEW_REQUIRED, never REVIEWED_DONE.

## Completion
B1 repaired and offline/rollback/frozen verification complete. See 2026-10-08-follow-up-rollback-report.md. No deployment or business actions. CEO verdict unchanged; REVIEW_REQUIRED.
