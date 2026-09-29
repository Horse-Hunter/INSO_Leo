# Agent Entry

Start with `AI_START_HERE.md`.

- Owner + CEO discuss requirements; CEO creates/completes the RFQ Task Spec.
- Owner may open any Codex / Claude implementation session and say only `执行 RFQ-XXX`.
- `Review RFQ-XXX` belongs to CEO/Architect/Safety, not the implementation agent.
- Task requirements live in `control-room/RFQ-XXX/TASK_SPEC.md`; RFQ status lives in `control-room/COORDINATION.md`.
- Read `docs/MODULE_INDEX.md` and only the module docs/code relevant to the RFQ.
- Executor owns ordinary implementation, debugging, tests, live verification, evidence, execution records and commit/push until acceptance.
- CEO owns independent Review and final PASS / CHANGES_REQUESTED verdict.
- **Anything shown directly to Owner must be plain business language.** It must answer: what happened, what it affects, and what happens next. Do not expose class names, selectors, method names, pagination details, stack traces, runtime internals, or similar implementation jargon unless Owner explicitly asks.
- **Technical findings are for Executor-facing records only.** Put precise implementation terms and repair instructions in RFQ `REVIEW.md` technical findings, `EXECUTION_LOG.md`, Git/tests/evidence, not in the Owner-facing summary.
- Owner is involved only for genuine business decisions, explicit Safety/Write Gate authorization, human security challenges, destructive Git, major architecture, or release/merge decisions.
- Repeated technical problems must become shared code/contracts/tests, not repeated chat instructions.
- Never persist secrets in Git, logs, fixtures, evidence or reports.
