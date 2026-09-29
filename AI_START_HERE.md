# AI START HERE

This repository is **RFQ-driven**. The Control Room is the task source of truth.

## Command: 执行 RFQ-XXX

This is an **executor command** for Codex / Claude / other implementation agents. The command alone is sufficient; do not ask the Owner to restate the task.

1. Read `control-room/COORDINATION.md` and `control-room/RFQ-XXX/TASK_SPEC.md`.
2. Read `docs/MODULE_INDEX.md`, then only the relevant module docs and code.
3. Inspect the current branch, git status, relevant commits/diff, tests and existing evidence.
4. Change RFQ status to `IN_PROGRESS` and implement until every acceptance item is satisfied or a true escalation condition is hit.
5. Write technical work to `EXECUTION_LOG.md`: implementation decisions, changed files/diff range, exact tests/results, evidence references, commits and real blockers. Do not paste secrets or raw terminal noise.
6. Write `FINAL_REPORT.md` using the fixed human summary in `docs/REPORTING.md`.
7. If review is required, set status to `REVIEW_REQUIRED`; otherwise set `DONE`.
8. Commit and push the implementation and Control Room records.

Ordinary technical problems stay inside the execution session. Reuse existing shared capabilities; do not rediscover solved infrastructure.

## Command: Review RFQ-XXX

This is a **CEO review command**, not a Main Programmer / Codex implementation command.

The Owner returns to the CEO/Architect/Safety conversation and says only:

`Review RFQ-XXX`

CEO independently reads:
- Task Spec
- Execution Log
- Final Report
- RFQ Git diff/commits
- current code
- test evidence
- runtime evidence

CEO does not implement fixes during the review. CEO writes/updates `REVIEW.md` and the Control Room status.

- PASS → `REVIEWED_DONE`
- FAIL → `CHANGES_REQUESTED`

A `CHANGES_REQUESTED` RFQ goes back to an executor with the same RFQ ID.
