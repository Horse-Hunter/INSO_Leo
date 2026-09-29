# AI START HERE

This repository is **RFQ-driven**. The Control Room is the task source of truth.

## For implementation agents: 执行 RFQ-XXX

The Owner may open any Codex / Claude implementation session and say only:

`执行 RFQ-XXX`

The command alone is sufficient. Do not ask the Owner to restate the task.

1. Read `control-room/COORDINATION.md` and `control-room/RFQ-XXX/TASK_SPEC.md`.
2. Read `docs/MODULE_INDEX.md`, then only relevant module docs/code.
3. Inspect current Git state, relevant commits/diff, tests and existing evidence.
4. **Run a reuse audit before design or coding:** inspect the current implementation, previous stable/release version, existing runtime configs, shared adapters, migrations, scripts, packaging, tests and prior RFQ decisions. Reuse every capability that already satisfies the requirement.
5. Set RFQ to `IN_PROGRESS` and implement the **minimum incremental change** needed to satisfy acceptance.
6. Record technical detail in `EXECUTION_LOG.md`: reused capabilities, any justified non-reuse, decisions, changed files/diff range, exact tests/results, evidence references, commits and true blockers.
7. Write `FINAL_REPORT.md` using the fixed human summary in `docs/REPORTING.md`.
8. If review is required, set `REVIEW_REQUIRED`; otherwise set `DONE`.
9. Commit and push implementation + Control Room records.

Ordinary technical problems stay inside the implementation session.

## Reuse is mandatory

- Existing stable behavior is an inheritance baseline, not an example to re-create.
- Do not repeat discovery, architecture thinking or implementation that the repository has already solved.
- Do not introduce a second production path, second config format, second adapter or second release mechanism for an existing responsibility unless the RFQ explicitly requires replacement.
- If the existing capability cannot be reused, prove that in `EXECUTION_LOG.md` before adding a replacement.
- Temporary validation/discovery paths must be folded back into the canonical production path before delivery.
- If progress stalls, first search for an already-solved path. Do not compensate by inventing another framework or implementation.

## For CEO: Review RFQ-XXX

The Owner returns to the CEO conversation and says only:

`Review RFQ-XXX`

CEO independently reads Task Spec, Execution Log, Final Report, RFQ Git diff/commits, current code, test evidence and runtime evidence.

CEO also verifies reuse discipline: no unnecessary parallel path, duplicate capability, repeated infrastructure or unjustified reimplementation.

CEO writes/updates `REVIEW.md` and RFQ status:

- PASS → `REVIEWED_DONE`
- FAIL → `CHANGES_REQUESTED`

CEO does not implement fixes inside the review. A failed RFQ goes back to an implementation agent under the same RFQ ID.
