# AI START HERE

This repository is **RFQ-driven**. The Control Room is the task source of truth.

## Command: 执行 RFQ-XXX

The command alone is sufficient. Do not ask the Owner to restate the task.

1. Read `control-room/COORDINATION.md` and `control-room/RFQ-XXX/TASK_SPEC.md`.
2. Read `docs/MODULE_INDEX.md`, then only the relevant module docs and code.
3. Inspect the current branch, git status, relevant commits/diff, tests and existing evidence.
4. Change RFQ status to `IN_PROGRESS` and implement until every acceptance item is satisfied or a true escalation condition is hit.
5. Write technical work to `EXECUTION_LOG.md`: implementation decisions, changed files/diff range, exact tests/results, evidence references, commits and real blockers. Do not paste secrets or raw terminal noise.
6. Write `FINAL_REPORT.md` using the fixed human summary in `docs/REPORTING.md`.
7. If independent review is required, set status to `REVIEW_REQUIRED`; otherwise set `DONE`.
8. Commit and push the implementation and Control Room records.

Ordinary technical problems stay inside the execution session. Reuse existing shared capabilities; do not rediscover solved infrastructure.

## Command: Review RFQ-XXX

Use a **new independent session/agent**.

Read:
- Task Spec
- Execution Log
- Final Report
- Git diff/commits for the RFQ
- current code
- test evidence
- runtime evidence

Do not implement fixes during the review. Write `REVIEW.md`.

- PASS → `REVIEWED_DONE`
- FAIL → `CHANGES_REQUESTED`

A `CHANGES_REQUESTED` RFQ is executed again with the same RFQ ID.
