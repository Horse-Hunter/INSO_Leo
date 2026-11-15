# INSO LEO — Agent Rules (current)

Read [AI_START_HERE.md](AI_START_HERE.md). **Current rules here outrank historic task notes.** Original pre-compaction rules: [pinned archive](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/AGENTS.md).

## Branch promotion is Owner-only

**Bootstrap trap:** repository default `main` still contains historic V1.1. Every replacement CEO/Executor must explicitly open current `develop` entry docs before treating any branch as the project baseline. Do not auto-promote.

Three long-lived lines: `develop` (R&D + installed trial), `main` (only Owner-accepted current), `release/previous` (prior Owner-accepted current). **Packaging, installation, live operation, successful tests or elapsed time never promote a version.** Only explicit Owner approval may advance `main`; see [BRANCH_POLICY](docs/BRANCH_POLICY.md). During initial migration, `main` still contains legacy V1.1 and MUST NOT be presented as the verified current V1.6. Preserve existing DeepSeek worktree/branch.

## Ownership and source of truth

- **Owner** sets business intent, grants real external-effect/production permissions, decides release; **CEO** owns requirements, architecture, independent Review; **one Executor** owns implementation, tests, deployment and live business evidence.
- Requirements: `control-room/RFQ-XXX/TASK_SPEC.md`; current status: `control-room/COORDINATION.md`; handover: `control-room/CEO_HANDOVER.md`; technical record: existing `EXECUTION_LOG.md`; independent verdict: `REVIEW.md`.
- A new Executor can receive just `执行 RFQ-XXX`; a CEO can receive `Review RFQ-XXX`. Neither asks Owner to repeat context already committed.

## Lean Review / bounded execution (Owner approved 2026-11-15)

**Goal:** reduce repeated context, token use, test/build churn and R2→R3→R4-style serial discoveries; **never trade away independent safety review or live evidence**. This is an execution-efficiency rule, not an authorization to deploy.

1. **One authoritative baseline, then diff first.** On takeover still read `develop` entry/AGENTS and active `COORDINATION`, `CEO_HANDOVER`, RFQ Task Spec/last Review. Verify actual ref/HEAD, dirty worktrees and live state where relevant. Thereafter review changes against the last fixed reviewed SHA with Git Diff and trace only changed/affected call chains. Expand to full files only for risks or gaps; never rely on stale chat summaries as evidence.
2. **One bounded effect-path audit per release blocker.** Before claiming a scoped run is isolated, inventory the real startup, background/periodic, manual/GUI and recovery paths; include local SQLite/event/alert changes, Google/INSO/SMTP effects, uncertain-effect holds and rollback/installer gates. Verify scope checks **before** each possible effect, including out-of-scope historical orders. Use one consolidated negative-test matrix (in-scope/out-of-scope, permission denied, crash/restart, legacy unscoped compatibility). CEO reports all material findings of that pass together rather than knowingly spacing them over rounds.
3. **Two-stage tests, one final candidate.** During development run smallest relevant tests and targeted regressions. When source is frozen run affected suites, then one full test suite and record all failed/skipped nodeids and baseline comparison. Do not delete/deselect/skip tests to claim green. Build/sign/hash/scan **once after source freeze**; any subsequent source change invalidates the candidate and requires rebuilding and revalidation. No automatic repeat of the full suite or build just for a status update.
4. **Compact, linked reporting.** Keep one `EXECUTION_LOG.md` for checkpoints and evidence paths, one independent `REVIEW.md` (PASS / CHANGES_REQUESTED + findings + gates), and update `COORDINATION.md` only for real state changes. The Executor retains the canonical [seven reporting headings](docs/REPORTING.md) but keeps them concise: fixed SHA/changed paths, tests, candidate hash, open blockers, actual production actions, next handoff. Reference prior evidence by exact path/SHA; do not replicate long logs or rewrite historical versions.
5. **Non-negotiable gates remain.** Executor self-reported PASS is not CEO independent acceptance; hash manifests do not verify uninspected executable bytes; a dated process record is not live status. Installation, production Stop/restart, real orders and branch promotion each require their own Owner authorization and verifiable preconditions. A failed/unknown external effect stays held and is never replayed to save time.

## Interrupt-anytime / replace-any-window (Owner rule 2026-11-14)

**Trigger:** start, every task/role transfer, before/after real effects, after meaningful progress, and whenever interruption is possible. Applies equally to CEO and Executor. **Goal:** a replacement window needs only repo + live evidence, never old chat memory.

1. **Before work** read the active documents; inspect actual branch/HEAD, `git status --short`, `git diff`, `git worktree list --porcelain`; for production check running processes, config, SQLite, logs, Sheet/INSO/SMTP truth. Reuse the existing worktree; preserve uncommitted/unknown files. An expired model window does **not** imply its program stopped.
2. **Checkpoint before irreversible actions:** in the **existing** RFQ `EXECUTION_LOG.md` record exact target/scope, pre-state, authorization, live process, planned action, and potential unknown outcome; persist the original business guard/hold before dispatch. Record CEO decisions in existing `REVIEW.md` or Task Spec; update `COORDINATION.md` only for real state changes. Commit/push bounded coherent checkpoints when safe; never replace native SQLite safety with Git documentation.
3. **After each real response** reconcile the external system, record request/receipt/actual observed outcome (`DONE / NOT_DONE / UNKNOWN / WAITING_OWNER`), next single action and blockers. A request/timeout is not success. Preserve uncertain holds and stop further effects for that order.
4. **On takeover** reconcile local dirty state + live processes + all external records against last checkpoint; do not assume the last chat text, Git HEAD, old EXE hash or dated report is live proof. Confirm prior Executor is no longer initiating actions and no in-flight operation survives **before** any second start or replay. One active Executor; CEO may review independently without executing business.
5. **At interruption** no last-minute message is required for safety: pre-action durable guard + existing log checkpoint + on-site audit must suffice. Do not claim continuous monitoring after window ends. Temporary `HANDOFF*.md` only if necessary for one transfer; fold into existing record, then retire it.

**Enforcement:** CEO fails Review for missing recoverable state, duplicate/unknown external effects, or stale instructions presented as current. **Cleanup:** retire only owned disposable files; never force-delete unknown dirty worktrees, protected runtime, Chrome/CDP, SQLite/WAL/SHM, secrets, rollback or evidence. This rule is also in reusable templates.

## Safe execution and reuse

- **Computer Use permitted** by Owner 2026-11-14, including supported desktop GUI inspection/click/type. CLI, PowerShell/Python, API and existing app-owned CDP remain permitted; actual use is recorded truthfully. Tool permission **does not** grant purchase, Google Editor, quotation button, SMTP, release or other real effects. See [SAFETY](docs/SAFETY.md).
- One protected browser: profile `D:\\Program_Leo\\INSO_CDP\\chrome-profile`, port `9222`; never reset/force-kill or clone it. See [CDP policy](docs/CDP_SESSION_POLICY.md).
- Guard exact source identity, dates, status, purchase/quote/mail dedup, durable `SENT/UNKNOWN`; no blind retry or clearing holds. Before running a single order, prove other modules cannot simultaneously cause effects.
- Reuse existing stable paths, adapters, config, migrations, packaging and tests; no duplicate production implementations. Implement only proven gaps; document justified non-reuse in `EXECUTION_LOG.md`.
- No secrets in Git, report, chat or fixtures. Owner sees plain business language. Completed Executor reports use exact [seven headings](docs/REPORTING.md); CEO Review uses the short CEO format.
- Durable policy changes: CEO supplies trigger/owner/procedure/source/evidence/cleanup/enforcement in canonical docs; **project-generic** rules also update `templates/lean-ai-baseline/`. Review enforces them, not Owner reminders.
