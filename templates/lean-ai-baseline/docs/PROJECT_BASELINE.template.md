# Project Baseline

- Work is RFQ-driven; Control Room is the requirement/status source of truth.
- Any executor starts from `执行 RFQ-XXX`.
- Review is owned by CEO; Owner returns to CEO with `Review RFQ-XXX`.
- Git/code/tests/evidence are implementation truth.
- CEO/Owner own requirement meaning and Task Spec.
- Executor owns reuse audit, implementation and execution records.
- CEO independently reviews without implementing fixes.
- Instructions stay focused on current RFQ acceptance; no long procedural prompts.
- Repeated technical failures become shared code/contracts/tests.
- Owner is not a technical message bus.

## Reuse contract

- Existing stable working capability is the inheritance baseline for the next version.
- Reuse current/stable implementation, configuration, adapters, runtime, migrations, tests, scripts and packaging before adding anything new.
- Do not repeat solved discovery or architecture thinking unless requirements changed or new evidence invalidates the prior decision.
- Do not create duplicate production paths or equivalent infrastructure for the same responsibility.
- Unavoidable non-reuse must be justified in the RFQ Execution Log before implementation.
- Temporary discovery/verification paths must converge into one canonical production path before delivery.
- Review fails on unjustified reimplementation, duplicate capability or unretired parallel production paths.

Stable anchors:
- `<CURRENT_STABLE_BASELINE>`

## Rule operationalization invariant

- Durable Owner workflow/governance instructions are complete only when repository rules define trigger, owner, procedure, canonical state, evidence, cleanup and enforcement.
- CEO owns operationalization and template propagation for reusable rules.
- Executor owns execution/evidence; Reviewer owns enforcement; Owner does not repeat reminders.

## Workspace / handoff invariant

- Default one active implementation worktree per active version/RFQ.
- Outgoing Executor preserves the live workspace and leaves at most one temporary handoff.
- Incoming Executor owns verified handoff consumption and cleanup.
- Unique work must be preserved before stale worktree removal; unknown dirty worktrees are never force-deleted; prune afterward.
- Handoff files expire after takeover; obsolete blockers/next steps are marked resolved/superseded.
- Review fails on expired handoffs, stale current-state text or unjustified duplicate active worktrees.

