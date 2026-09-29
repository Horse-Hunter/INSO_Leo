# AI START HERE

This repository is **RFQ-driven**. The Control Room is the task source of truth.

## For implementation agents: 执行 RFQ-XXX

The Owner may open any Codex / Claude implementation session and say only:

`执行 RFQ-XXX`

The command alone is sufficient. Do not ask the Owner to restate the task.

1. Read `control-room/COORDINATION.md` and `control-room/RFQ-XXX/TASK_SPEC.md`.
2. Read `docs/MODULE_INDEX.md`, then only relevant module docs/code.
3. Inspect current Git state, relevant commits/diff, tests and existing evidence.
4. Set RFQ to `IN_PROGRESS` and implement until acceptance is satisfied or a true escalation condition is hit.
5. Record technical detail in `EXECUTION_LOG.md`: decisions, changed files/diff range, exact tests/results, evidence references, commits and true blockers.
6. Write `FINAL_REPORT.md` using the fixed human summary in `docs/REPORTING.md`.
7. If review is required, set `REVIEW_REQUIRED`; otherwise set `DONE`.
8. Commit and push implementation + Control Room records.

Ordinary technical problems stay inside the implementation session. Reuse existing shared capabilities; do not rediscover solved infrastructure.

## For CEO: Review RFQ-XXX

The Owner returns to the CEO conversation and says only:

`Review RFQ-XXX`

CEO independently reads Task Spec, Execution Log, Final Report, RFQ Git diff/commits, current code, test evidence and runtime evidence.

CEO writes/updates `REVIEW.md` and RFQ status:

- PASS → `REVIEWED_DONE`
- FAIL → `CHANGES_REQUESTED`

CEO does not implement fixes inside the review. A failed RFQ goes back to an implementation agent under the same RFQ ID.
