# Agent Entry

Start with `AI_START_HERE.md`.

- **Every task, including non-RFQ maintenance:** read `docs/REPORTING.md` before the final response. The final **chat reply** must use its exact seven Executor headings (RFQ `FINAL_REPORT.md` uses them too); status, tests, live verification and the single next Owner action must be explicit. Technical details stay in execution records.
- **No build/test artifact accumulation:** follow the artifact lifecycle in `docs/PROJECT_BASELINE.md` and release-specific `docs/WINDOWS_RELEASE.md`. Reuse a single canonical build/stage path; clean owned disposable copies during the same task after they cease to be useful, including on failure. Never sweep shared runtime, CDP, credentials, active release/rollback assets or unknown worktrees.

- Owner + CEO discuss requirements; CEO creates/completes the RFQ Task Spec.
- Owner may open any implementation-agent session (Codex / Claude / WorkBuddy or equivalent) and say only `执行 RFQ-XXX`.
- `Review RFQ-XXX` belongs to CEO/Architect/Safety, not the implementation agent.
- Task requirements live in `control-room/RFQ-XXX/TASK_SPEC.md`; RFQ status lives in `control-room/COORDINATION.md`.
- Read `docs/MODULE_INDEX.md` and only the module docs/code relevant to the RFQ.
- Executor owns ordinary implementation, debugging, tests, live verification, evidence, execution records and commit/push until acceptance.
- CEO owns independent Review and final PASS / CHANGES_REQUESTED verdict.
- **Anything shown directly to Owner must be plain business language.** It must answer: what happened, what it affects, and what happens next. Do not expose class names, selectors, method names, pagination details, stack traces, runtime internals, or similar implementation jargon unless Owner explicitly asks.
- **Technical findings are for Executor-facing records only.** Put precise implementation terms and repair instructions in RFQ `REVIEW.md` technical findings, `EXECUTION_LOG.md`, Git/tests/evidence, not in the Owner-facing summary.
- Owner is involved only for genuine business decisions, explicit Safety/Write Gate authorization, human security challenges, destructive Git, major architecture, or release/merge decisions.
- Never persist secrets in Git, logs, fixtures, evidence or reports.

## Mandatory Reuse-First Rule

- Existing working capability is the default solution. Reuse it before designing anything new.
- Before coding, search the current codebase, stable/release branches, module contracts, runtime configuration, migrations, tests, scripts, packaging and prior RFQ decisions for an existing solution.
- A newer version inherits the previous stable version's working infrastructure unless the Task Spec explicitly changes it. Do not rebuild configuration, credentials, Sheets, Research, Workflow, browser/session, GUI shell, database migration, packaging or release plumbing merely because the version changed.
- Do not reopen settled technical decisions or repeat discovery unless requirements changed or new evidence proves the old decision invalid.
- Do not create parallel implementations, duplicate adapters, duplicate launch paths, duplicate configuration formats, duplicate migration paths or temporary replacements when an existing path can be extended.
- New implementation is allowed only for a real capability gap. The Executor must record in `EXECUTION_LOG.md` what existing capability was inspected, why it could not be reused, and why the new code is the minimum necessary delta.
- Temporary discovery/verification code must converge back into the single canonical production path before delivery. Long-lived parallel production paths are prohibited unless explicitly approved by CEO/Task Spec.
- Repeated technical problems must become one shared capability/contract/regression test, not another implementation or another round of chat reasoning.
- If two usable implementations exist for the same responsibility, stop and consolidate rather than adding a third.

## Rule Operationalization — mandatory

A chat acknowledgement is **not** a rule change.

When Owner gives a durable workflow/governance instruction, CEO must operationalize it in the repository in the same work cycle. A rule is not complete until all are explicit: **trigger, owner, ordered procedure, source of truth, completion evidence, cleanup/retirement, Review enforcement**.

- **CEO** owns converting Owner policy into executable repository rules and deciding project-only vs reusable. Reusable rules must also update `templates/lean-ai-baseline/` in the same change.
- **Executor** owns applying the operational rule and recording evidence.
- **Reviewer/CEO** owns enforcing it during Review.
- **Owner must not be the reminder mechanism** for a rule already stated.

A rule that only says “must/should” but does not define who acts, when, how, evidence and cleanup is incomplete.

## Handoff and Worktree Lifecycle

**Trigger:** a real Executor switch, or stale/duplicate worktrees are discovered.

- **Outgoing Executor:** create/update at most one concise temporary `HANDOFF*.md` only if needed; stop unsafe/live activity if necessary; preserve the live worktree and uncommitted state. Do not create another worktree just for handoff.
- **Incoming Executor:** owns takeover cleanup. First inspect branch, `git status`, diff and `git worktree list --porcelain`; read the handoff once; verify it against current Git/runtime; merge durable facts into `EXECUTION_LOG.md` or the correct canonical doc; delete the consumed handoff in the same work cycle.
- **Active Executor:** owns worktree hygiene. Reuse an existing suitable worktree before creating one. Default: one active implementation worktree per active version/RFQ.
- Before removing a worktree, preserve unique commits/files in traceable Git history. Never force-delete unknown dirty state. After safe removal run `git worktree prune`.
- `TASK_SPEC.md` remains Owner/CEO-owned requirement meaning. `COORDINATION.md` contains current RFQ status. `EXECUTION_LOG.md` may preserve history, but obsolete blockers/next steps must be marked `RESOLVED` or `SUPERSEDED`.
- Handoff files are temporary transport only. After successful takeover no expired handoff, obsolete worktree path, or stale “current blocker” instruction may remain.

**Completion evidence:** Executor records surviving active worktree(s), consumed/deleted handoff, preserved commits and prune result in `EXECUTION_LOG.md`.

**Enforcement:** Review fails if stale handoffs, unexplained duplicate active worktrees, or obsolete current-state instructions remain.

## Delivery-First Principle

The repository exists to deliver the Owner's required product, not to maximize process.

Priority order:
1. Owner's current business intent and canonical requirements;
2. reuse of already-working capability;
3. necessary safety, data-integrity and reversibility controls;
4. process/documentation only when it directly supports 1–3.

Rules:
- Do not invent extra gates, reports, approvals, test ceremonies, abstractions or boundaries unless required by the Task Spec, real safety/data-loss risk, or a demonstrated recurring failure.
- Process must never become a substitute for implementation. If a housekeeping issue can be fixed immediately, fix it without stopping delivery.
- When Owner gives a correction, CEO must also check the nearby implications (ownership, lifecycle, stale state, reuse, handoff, release) so Owner does not have to point out each consequence separately.
- Prefer one short executable rule over many procedural requirements. Any governance change should reduce future work, not add routine burden.
- Reuse checks are lightweight: inspect only the relevant existing implementation/history. Extra documentation is required only when choosing not to reuse a plausible existing solution.
- Owner-facing instructions should contain only the minimum actions needed to move delivery forward.

