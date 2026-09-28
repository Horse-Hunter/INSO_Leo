# Agent Entry

Start with `AI_START_HERE.md`.

- `执行 RFQ-XXX` and `Review RFQ-XXX` are complete commands; recover the task from Control Room and Git instead of asking for copied context.
- Task requirements live only in `control-room/RFQ-XXX/TASK_SPEC.md`; status lives in `control-room/COORDINATION.md`.
- Read `docs/MODULE_INDEX.md` and only the module docs/code relevant to the RFQ.
- Main Programmer owns ordinary implementation, debugging, tests, live verification, commit/push and execution records until the RFQ reaches its acceptance state.
- Owner is involved only for genuine business-rule decisions, explicit Safety/Write Gate authorization, human security challenges, destructive Git, major architecture, or release/merge decisions.
- Repeated technical problems must become shared code/contracts/tests, not repeated chat instructions.
- Never persist secrets in Git, logs, fixtures, evidence or reports.
