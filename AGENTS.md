# Agent Entry

Start with `AI_START_HERE.md`.

- `执行 RFQ-XXX` is the complete command for Main Programmer / Codex / Claude implementation sessions.
- `Review RFQ-XXX` belongs to the CEO/Architect/Safety role; implementation agents do not independently review their own RFQ.
- Task requirements live only in `control-room/RFQ-XXX/TASK_SPEC.md`; status lives in `control-room/COORDINATION.md`.
- Read `docs/MODULE_INDEX.md` and only the module docs/code relevant to the RFQ.
- Main Programmer owns ordinary implementation, debugging, tests, live verification, commit/push and execution records until the RFQ reaches its acceptance state.
- CEO owns independent RFQ review and writes the final PASS / CHANGES_REQUESTED verdict.
- Owner is involved only for genuine business-rule decisions, explicit Safety/Write Gate authorization, human security challenges, destructive Git, major architecture, or release/merge decisions.
- Repeated technical problems must become shared code/contracts/tests, not repeated chat instructions.
- Never persist secrets in Git, logs, fixtures, evidence or reports.
