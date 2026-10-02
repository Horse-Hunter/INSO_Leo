# AI START HERE

This project is RFQ-driven.

## 执行 RFQ-XXX

Owner may open any implementation agent (Codex / Claude / WorkBuddy or equivalent) and say only `执行 RFQ-XXX`.

Executor reads Control Room, Module Index, relevant code/docs and Git state.

Before design or coding, Executor performs a mandatory Reuse Audit across:
- current production implementation;
- stable/release versions;
- module contracts and adapters;
- runtime configuration and migrations;
- tests/evidence;
- build/packaging/release scripts;
- prior RFQ decisions.

Existing capability must be reused when it satisfies the requirement. Implement only the minimum incremental gap.

Executor writes reuse decisions, any justified non-reuse, execution log/final report/tests/evidence/commit references; then sets `REVIEW_REQUIRED` or `DONE`.

Ordinary technical problems stay inside the implementation session. Do not solve slow progress by creating a second architecture or duplicate implementation.

## Review RFQ-XXX

Owner returns to the CEO/Architect/Safety conversation and says only `Review RFQ-XXX`.

CEO independently reads Task Spec, Execution Log, Final Report, Git diff/commits, current code, tests and runtime evidence, and verifies that unnecessary reimplementation or parallel production paths were not introduced.

CEO writes `REVIEW.md`:
- PASS → `REVIEWED_DONE`
- FAIL → `CHANGES_REQUESTED`

## Durable rules and takeover

Durable Owner governance instructions must be operationalized, not merely acknowledged. Every rule must define trigger, owner, procedure, source of truth, evidence, cleanup and enforcement.

When taking over:
1. Reuse the existing active worktree; do not create another by default.
2. Inspect Git status/diff and `git worktree list --porcelain`.
3. Read and verify the single temporary handoff if present.
4. Move durable facts into canonical records.
5. Delete the consumed handoff in the same work cycle.
6. Preserve unique work before safely removing stale worktrees; never force-delete unknown dirty state; prune afterward.
7. Mark obsolete blockers/next steps resolved or superseded.

Incoming Executor owns cleanup; outgoing Executor only prepares the minimal handoff and preserves the workspace.

## Delivery first

Take the shortest safe path from Owner intent and canonical requirements to a working result.

Reuse existing working capability. Do not create extra process around reuse unless a plausible reusable path is being rejected.

Do not add gates/reports/approval steps unless required by the task, real safety/data-loss risk, or a proven recurring failure.

When Owner corrects one workflow problem, address the obvious adjacent ownership/lifecycle/stale-state implications in the same change.

