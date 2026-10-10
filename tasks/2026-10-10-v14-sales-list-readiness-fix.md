# Task: Owner V1.4 sales header stop / RFQ-013 follow-up fix
status: complete (implementation); REVIEW_REQUIRED
owner: Codex
created: 2026-10-10

Owner reported header stop after source GUI test. Read-only canonical CDP inspection
found only owned unique V1.4 sales list visible, add button present, no bill form.
Code checks list immediately after iframe attached (not loaded); this readiness
race is a supported cause, original exact reason was not persisted and is UNKNOWN.
Scope: bounded list/add readiness wait before one existing add action; clearer
safe page-stage error attribution; native prompt cancel semantics retained.
No business rerun/upload/save/submit/SMTP/receipt writes from diagnostics. No new
login/browser/tab or deployment. Preserve existing failed page and other tabs.
Verify delayed-load/timeouts/ambiguity/ownership and existing prompt behavior,
focused/full offline regression, Ruff/diff, commit/push REVIEW_REQUIRED.
Owner must close idle source GUI before updated source can be loaded; do not kill
active GUI or automatically trigger another order. Live retry remains Owner action.

Completion: readiness wait/page-stage labels and targeted regression added.
Verified focused92/full1837+1skip/Ruff/diff; retained owned-list read-only probe.
Limitations: original exception precise reason UNKNOWN, Owner live retry pending.
Owner confirmed GUI closed; reopen same source GUI without auto-trigger/deployment.
