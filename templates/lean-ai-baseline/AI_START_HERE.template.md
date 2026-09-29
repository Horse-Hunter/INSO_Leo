# AI START HERE

This project is RFQ-driven.

## 执行 RFQ-XXX

Owner may open any Codex / Claude implementation session and say only `执行 RFQ-XXX`.

Executor reads Control Room, Module Index, relevant code/docs and Git state; implements to acceptance; writes execution log/final report/tests/evidence/commit references; then sets `REVIEW_REQUIRED` or `DONE`.

Ordinary technical problems stay inside the implementation session.

## Review RFQ-XXX

Owner returns to the CEO/Architect/Safety conversation and says only `Review RFQ-XXX`.

CEO independently reads Task Spec, Execution Log, Final Report, Git diff/commits, current code, tests and runtime evidence.

CEO writes `REVIEW.md`:
- PASS → `REVIEWED_DONE`
- FAIL → `CHANGES_REQUESTED`
