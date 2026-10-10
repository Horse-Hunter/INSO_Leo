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

## Build/test/release artifact lifecycle (mandatory)

**Trigger:** any task generating or copying sizeable build, frozen-test, staging, deployment-scan or release artifacts; also success, failure, handoff and release closeout. **Executor** owns this in the generating task.

1. Prefer reuse of canonical build/test/release paths and existing validated artifacts. Before an expensive copy, decide its owner, expected size, purpose, and retirement point; avoid producing a full dependency bundle for every check.
2. Keep disposable assets inside task-owned, clearly delimited paths, separate from runtime, unique evidence and necessary rollback. Retire duplicates and intermediate staging/scans **as their purpose ends**, including after failed or abandoned attempts. Keep small useful evidence, not many frozen binaries.
3. At release completion, keep active installations and the minimum genuinely usable approved rollback assets. Inspect mixed backup folders individually; never delete linked/shared runtime, CDP/session, business state, Vault/OAuth, Git, dirty worktrees or unique evidence. Do not force file locks, change permissions, or require impossible global proof of zero open file handles for otherwise proven-disposable files.
4. Record briefly in the RFQ `EXECUTION_LOG.md` what large assets were retained/retired and why, plus material space impact; for non-RFQ tasks state the result in the final chat. No extra report or cleanup framework is required.

**Source of truth:** this baseline and the project's canonical release scripts/docs. **Enforcement:** CEO Review rejects unexplained piles of duplicate frozen builds/scans/backups or unsafe cleanup; normal owned-artifact retirement is part of delivery, not a separate Owner chore.

## Delivery-first invariant

- Correct working delivery of Owner requirements is primary; governance is subordinate.
- Priority: Owner intent → canonical requirement → reuse → necessary safety/data integrity/reversibility → minimal process.
- Do not add gates, reports, boundaries or acceptance burden without a real requirement, safety/data-loss risk, or demonstrated recurring-failure reason.
- CEO handles obvious adjacent implications of Owner corrections without requiring repeated prompts.
- Housekeeping is performed in-line and should not become an artificial blocker.
- Rules that add recurring effort without improving correctness, safety, recoverability or delivery speed should be simplified or removed.

