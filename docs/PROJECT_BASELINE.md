# Project Baseline — live rules

Owner intent → canonical RFQ Task Spec → reuse existing stable product → minimum safe change → real evidence → CEO Review. **Process exists to deliver, not replace delivery.**

- **Owner** decides business permissions. **CEO** owns Task Spec, architecture, independent Review and concise current-state docs. **Executor** owns implementation, testing, production evidence, exact commit and safe cleanup. Only one production Executor.
- Requirements: `control-room/RFQ-XXX/TASK_SPEC.md`; status: `COORDINATION.md`; active execution checkpoint: `EXECUTION_LOG.md`; CEO result: `REVIEW.md`. No chat-only state. Any session must be replaceable from these plus live systems.
- **Interruptibility:** checkpoint before potentially irreversible effects and after each observed result; never assume a previous window's process stopped; new window independently reconciles process, worktree, logs, database and external effect. No second writer for an UNKNOWN effect. Full procedure: [AGENTS](../AGENTS.md).
- Reuse existing production code, config, migration, CDP/session, runtime, adapters, tests and release path. No redundant second scheduler/ledger/API/browser/SMTP or new handoff framework. Explain a necessary non-reuse in the existing execution log.
- A durable Owner rule must give trigger, responsible role, procedure, authoritative source, evidence, cleanup and Review enforcement; CEO mirrors **generic** rules into `templates/lean-ai-baseline/`.
- One suitable active worktree/RFQ; preserve unknown dirty/unique files and commits. Retire proven task-owned disposable build/staging copies in the same work cycle, even on failure; never remove shared runtime, CDP/profile, SQLite/WAL/SHM, secrets, rollback or unknown assets.
- Production permission, writes and safety are controlled by [SAFETY](SAFETY.md) and [CDP policy](CDP_SESSION_POLICY.md). Computer Use is project-allowed if supported, not a blanket real-write grant.
- Historical decisions and obsolete instructions must be read **by pinned commit** only when investigating; never promote historical `NOT_DEPLOYED` or `BUSINESS_RUNNING` to current state. [History](HISTORY.md).

Full previous baseline: [archive](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/docs/PROJECT_BASELINE.md).
