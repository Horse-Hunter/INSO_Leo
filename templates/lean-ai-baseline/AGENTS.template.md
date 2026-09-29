# Agent Entry

Start with `AI_START_HERE.md`.

- Owner + CEO discuss requirements; CEO creates/completes the RFQ Task Spec.
- Owner opens any implementation agent (Codex / Claude / WorkBuddy or equivalent) and says only `执行 RFQ-XXX`.
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

## Rule Operationalization

A chat acknowledgement is not a rule change. Durable Owner workflow/governance instructions must be persisted and made executable.

Every durable rule must define: trigger, owner, ordered procedure, source of truth, completion evidence, cleanup/retirement and Review enforcement.

- CEO owns operationalizing the rule and mirroring reusable rules into the baseline templates.
- Executor owns applying it and recording evidence.
- Reviewer/CEO owns enforcement.
- Owner must not be required to repeat or remind the team about an already-stated rule.

A “must/should” rule without owner/procedure/evidence/cleanup is incomplete.

## Handoff / Worktree Lifecycle

- Outgoing Executor leaves one minimal temporary handoff only for a real switch and preserves the live workspace.
- Incoming Executor owns takeover cleanup: inspect Git/worktrees, verify handoff facts, merge durable facts into canonical records, delete the handoff in the same work cycle.
- Active Executor reuses before creating; default one active implementation worktree per active version/RFQ.
- Preserve unique work before safe worktree removal; never force-delete unknown dirty state; prune afterward.
- Mark obsolete blockers/next steps resolved or superseded.
- Review rejects expired handoffs or unexplained duplicate active worktrees.

## Delivery-First Principle

The project exists to deliver the Owner's required outcome, not to maximize process.

Priority: Owner intent → canonical requirement → reuse → necessary safety/data integrity → minimal process.

- Do not invent extra gates, reports, approvals, abstractions or boundaries without a real requirement/safety/data-loss/recurring-failure reason.
- Process must not replace implementation or become an artificial blocker.
- When Owner corrects one issue, CEO also handles obvious adjacent ownership/lifecycle/reuse implications so Owner need not enumerate them.
- Reuse checks stay lightweight; document only deliberate non-reuse of a plausible existing capability.
- Governance should reduce future work, not add routine burden.

