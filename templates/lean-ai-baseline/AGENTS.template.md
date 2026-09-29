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

## Mandatory Reuse-First Rule

- Existing working capability is the default solution; inspect and reuse it before designing new code.
- Search current implementation, stable/release versions, module contracts, runtime config, migrations, tests, scripts and packaging before coding.
- New versions inherit stable infrastructure unless requirements explicitly change it.
- Do not reopen solved decisions without changed requirements or new invalidating evidence.
- Do not create parallel production paths, duplicate adapters/configs/migrations/release pipelines for an existing responsibility.
- If reuse is impossible, document inspected alternatives and the minimum necessary replacement in the Execution Log before implementing it.
- Temporary discovery/verification paths must converge back into the single canonical production path before delivery.
- Repeated failures become shared capability/contracts/tests, not repeated reasoning or repeated implementations.
