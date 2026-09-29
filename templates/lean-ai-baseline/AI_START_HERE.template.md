# AI START HERE

This project is RFQ-driven.

## 执行 RFQ-XXX

Owner may open any Codex / Claude implementation session and say only `执行 RFQ-XXX`.

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
