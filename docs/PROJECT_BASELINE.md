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

## Artifact lifecycle — prevent build/test disk growth (binding)

**Trigger:** every Executor task that creates, copies, freezes, scans or packages sizeable test/build/release assets; also completion, failure, handoff and deployment verification. This is continuous housekeeping, **not** a separate end-of-month cleanup project.

**Owner/procedure:**
1. **Before creating:** reuse existing build scripts, canonical stage and verified artifacts; avoid copying complete frozen apps, dependency trees or worktrees for repeated verification. Estimate size and keep only the minimum simultaneously required; give any necessary temporary copy a clear task/owner and exact path.
2. **During execution:** keep disposable outputs inside known owned build/test/staging paths; distinguish them from runtime, operational evidence and required rollback. Do not silently retain a new frozen copy for every test or deployment attempt. Prefer reusable test fixtures and small evidence.
3. **As soon as an intermediate step succeeds, fails or is abandoned:** retire that step's **own** verified-disposable frozen copies, scan directories and temporary build outputs in the same work cycle. On failure retain only minimal useful diagnostic evidence and genuine recovery assets. Do not wait until project-wide disk use becomes large.
4. **At release closeout:** preserve active versions, shared operational state, and the smallest *actually viable* Owner-approved rollback set; retire superseded duplicate package assets after successful verification. A backup folder can contain irreplaceable runtime or links: inspect individual objects, never bulk-delete on age/name alone.
5. **At handoff/end:** identify any deliberately retained large artifact, its owner/purpose and retirement condition. Any unexplained duplicate needs cleanup or a concrete blocker before marking work complete. Never require Owner to manually clean normal build/test leftovers.

**Protected boundary:** never follow/delete junctions or symlinks into shared data; do not touch CDP Chrome profile/session/backup, business runtime/databases/outbox, Vault/OAuth, current or required rollback releases, Git history or unknown dirty worktrees. If a particular deletion has a **real, specific** dependency/data-loss risk, preserve it and record why; unavailable global Windows file-handle enumeration **alone** is not grounds to block unrelated safe cleanup. Do not circumvent file locks or permissions.

**Source of truth/evidence:** this baseline defines the invariant; `docs/WINDOWS_RELEASE.md` and the existing canonical packaging scripts define release handling. For RFQs, note created/retired/retained large assets and any space impact or justified exception briefly in `EXECUTION_LOG.md`; for a non-RFQ maintenance task use the final chat response. Do not create a new report or cleanup framework solely for this check.

**Review enforcement:** CEO rejects unexplained accumulating frozen bundles, staging/scanning copies, redundant backups or destructive cleanup of protected state, even if feature tests pass. Routine safe cleanup is part of Executor delivery, not a separate Owner approval gate.

## Delivery-first invariant

- The project's primary objective is correct, working delivery of Owner requirements. Governance serves that objective and must not compete with it.
- Priority is: Owner intent → canonical requirement → reuse → necessary safety/data integrity/reversibility → minimal process.
- CEO must not create additional gates, reports, boundaries or acceptance burdens unless they are required by the requirement itself, a real safety/data-loss risk, or a demonstrated recurring failure.
- When Owner corrects a process/design issue, CEO is responsible for identifying and fixing the obvious adjacent implications so Owner does not have to issue multiple follow-up corrections.
- Reuse enforcement should reduce work: inspect relevant existing capability, reuse it, and only document non-reuse when a plausible reusable path is deliberately rejected.
- Housekeeping should be done in-line and must not become an artificial blocker to implementation or live verification.
- Any rule that adds recurring effort without improving correctness, safety, recoverability or delivery speed should be simplified or removed.

