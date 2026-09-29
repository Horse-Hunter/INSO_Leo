# AI START HERE

This project is RFQ-driven.

## 执行 RFQ-XXX

Executor command. Read Control Room, Module Index, relevant code/docs and Git state. Implement to acceptance, write execution log/final report/tests/evidence/commit references, then set `REVIEW_REQUIRED` or `DONE`.

Ordinary technical problems stay inside the execution session.

## Review RFQ-XXX

CEO command. Owner returns to the CEO/Architect/Safety conversation and says only `Review RFQ-XXX`.

CEO independently reads Task Spec, Execution Log, Final Report, Git diff/commits, current code, tests and runtime evidence.

CEO writes `REVIEW.md`:
- PASS → `REVIEWED_DONE`
- FAIL → `CHANGES_REQUESTED`
