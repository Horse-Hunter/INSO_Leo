# INSO LEO — Agent Rules (current)

Read [AI_START_HERE.md](AI_START_HERE.md). **Current rules here outrank historic task notes.** Original pre-compaction rules: [pinned archive](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/AGENTS.md).

## Ownership and source of truth

- **Owner** sets business intent, grants real external-effect/production permissions, decides release; **CEO** owns requirements, architecture, independent Review; **one Executor** owns implementation, tests, deployment and live business evidence.
- Requirements: `control-room/RFQ-XXX/TASK_SPEC.md`; current status: `control-room/COORDINATION.md`; handover: `control-room/CEO_HANDOVER.md`; technical record: existing `EXECUTION_LOG.md`; independent verdict: `REVIEW.md`.
- A new Executor can receive just `执行 RFQ-XXX`; a CEO can receive `Review RFQ-XXX`. Neither asks Owner to repeat context already committed.

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
