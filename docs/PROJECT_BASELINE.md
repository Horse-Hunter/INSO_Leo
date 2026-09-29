# Project Baseline

## Operating model

- Work is RFQ-driven. The complete current requirement lives in Control Room, not chat.
- Any executor must be able to start from only `执行 RFQ-XXX`.
- Review is owned by CEO: Owner returns to the CEO conversation and says only `Review RFQ-XXX`.
- Git/code/tests/evidence are implementation truth; Task Spec is requirement truth; `COORDINATION.md` is status truth.
- CEO instructions must stay requirement-progress focused: business outcome, acceptance, relevant source docs, Safety boundary. No hundreds-line implementation manuals.
- If progress is slow, reread the RFQ and workflow rules and reduce scope to the shortest path that advances acceptance.
- Repeated failures become shared code/contracts/regression tests rather than repeated Owner guidance.
- Owner is not a technical message bus.

## Reuse contract

**Reuse First is a project invariant.**

- V1.1 is the working inheritance baseline for V1.2. V1.2 extends it; it does not independently recreate it.
- Unless a requirement explicitly changes them, V1.2 must reuse the V1.1 production configuration model, Sheets/OAuth integration, Research runtime, Workflow foundation, Chrome/CDP lifecycle, Core Vault, GUI shell, filesystem/app-root conventions, release safety checks and packaging infrastructure.
- Existing working code/config/scripts/tests/contracts are authoritative candidates for extension before any new implementation is considered.
- No duplicate production launcher, duplicate runtime config format, duplicate credential path, duplicate browser/session stack, duplicate migration path, duplicate release pipeline or equivalent parallel infrastructure may be introduced without explicit CEO/Task Spec approval.
- A stable decision or solved discovery question is not reopened unless requirements changed or new evidence invalidates it.
- Temporary discovery/live-verification helpers are allowed only as temporary evidence tools. Before release they must either be removed/retired or feed the same canonical production code path.
- Any unavoidable non-reuse must be documented in the RFQ Execution Log with the inspected existing solution, incompatibility evidence and minimum replacement scope.
- If the project contains multiple implementations of the same responsibility, consolidation is preferred over adding more code.

## Roles

- Owner: final business authorization.
- CEO: requirement clarification, Task Spec, business rules, architecture boundary, Safety/Write Gate, reuse governance, and independent RFQ review.
- Executor: reuse audit, implementation, debugging, tests, live verification, evidence, execution log, final report, commit/push.
- CEO Review: independently verifies implementation evidence and reuse discipline and returns only PASS / CHANGES_REQUESTED; does not implement fixes inside the review.

## Stable project anchors

- V1.1 Research Stability: CLOSED, `release/v1.1 = 44cd4a4cdb05fc069189801d24c4710bfd9445f3`.
- V1.2 branch: `feature/v1-2`.
- Production browser: Chrome only.
- Credential source: Core Vault only.
- INSO runtime readiness is a shared capability; ordinary runtime/session recovery is not an Owner blocker.
- V1.2 Production Write Gate: CLOSED.

## Rule operationalization invariant

- Durable Owner process instructions must be operationalized by CEO in repository rules; chat acknowledgement alone has no standing.
- Every durable rule must name its trigger, responsible role, procedure, canonical state, completion evidence, cleanup and Review enforcement.
- Reusable governance changes must be mirrored into `templates/lean-ai-baseline/` in the same change.
- Executor is responsible for executing the rule; Reviewer/CEO is responsible for enforcement. Owner is not responsible for reminding either role.

## Workspace / handoff invariant

- Default is one active implementation worktree per active version/RFQ.
- Outgoing Executor preserves the live workspace and may leave one minimal temporary handoff only for a real agent switch.
- Incoming Executor owns takeover cleanup: inspect current Git/worktrees, verify handoff claims, move durable facts to canonical records, delete the handoff, preserve unique work, safely remove stale worktrees, and prune.
- Unknown dirty worktrees are never force-deleted.
- Handoff files are never canonical and expire after takeover.
- `EXECUTION_LOG.md` may preserve history but obsolete current blocker/next-step statements must be marked resolved/superseded.
- Review requires cleanup evidence and rejects expired handoffs, stale current-state text or unexplained duplicate active worktrees.

