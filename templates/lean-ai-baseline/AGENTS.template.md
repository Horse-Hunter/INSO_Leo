# Agent Entry

Start with `AI_START_HERE.md`.

- Owner + CEO discuss requirements; CEO creates/completes the RFQ Task Spec.
- Owner opens any implementation agent and says only `执行 RFQ-XXX`.
- `Review RFQ-XXX` belongs to CEO/Architect/Safety.
- Task requirements come from Control Room, not copied chat context.
- Executor owns ordinary implementation/debug/test/live/evidence/commit work to acceptance.
- CEO owns independent RFQ review.
- Anything shown directly to Owner must be plain business language: what happened, what it affects, what happens next.
- Precise technical details belong only in Executor-facing records such as execution logs, technical review findings, Git/tests/evidence.
- Owner is involved only for true business/Safety/human-verification/destructive-Git/major-architecture/release decisions.
- Never persist secrets.
