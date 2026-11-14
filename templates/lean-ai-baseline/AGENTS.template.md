# Agent Entry — reusable baseline

Read `AI_START_HERE.md`. Roles: Owner authorizes business effects; CEO owns Task Spec, independent Review and governance; **one Executor** owns implementation and live execution. Source of truth: `control-room/COORDINATION.md`, active RFQ `TASK_SPEC.md`, `EXECUTION_LOG.md`, `REVIEW.md` and Git evidence.

## Interruption-safe takeover (generic Owner rule)

**Trigger:** any new window, handoff, meaningful progress, **before** and **after** external effects. **Owner:** current CEO/Executor. **Procedure:** inspect active branch/HEAD/dirty diff/worktrees and live process/database/external outcomes; read last canonical checkpoint; record intended effect and existing durable idempotency guard before dispatch; record confirmed receipt/UNKNOWN and next action after. Commit/push safe checkpoints. On unplanned session loss, next window **reconciles** the live operation rather than starting a duplicate; never infer a process stopped because chat ended. One active Executor only.

**Source:** `AGENTS.md`, `AI_START_HERE.md`, existing RFQ record. **Evidence:** recoverable task status, pre-/post-effect records, live reconciliation, exact Git refs. **Cleanup:** retire task-owned temporary handoff/test/build artifacts while preserving dirty work, runtime, secrets, history and rollback. **Review:** CEO fails unsafe replay, untraceable state or stale handoffs. No separate permanent handoff mechanism.

## Safeguards and reuse

- Agent Computer Use permission is **project-specific** and must follow its Owner-approved rules. Never infer a blanket GUI ban or permission from a generic template; tool access does not itself permit external purchase/write/mail/release.
- Reuse existing stable code, config, migrations, browser, ledger, adapters, tests and packaging. No unnecessary duplicate production implementation.
- Do not expose secrets or clear unknown external effects. Owner receives plain business summaries; technical evidence belongs in RFQ logs.
- Final Executor response and `FINAL_REPORT.md` use [seven headings](docs/REPORTING.md). CEO gives independent PASS/CHANGES_REQUESTED.
- Durable rules: CEO encodes trigger/owner/procedure/source/evidence/cleanup/Review, and copies general rules into template source. Keep live docs short, archive history by immutable commit link.
