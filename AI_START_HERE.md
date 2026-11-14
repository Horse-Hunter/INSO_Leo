# INSO LEO — New Window Entry

**An interrupted CEO or Executor is replaceable without the prior conversation.** Only live systems and canonical repo records are authoritative; this file is the small routing map.

**Version routing:** read [three-branch policy](docs/BRANCH_POLICY.md). `develop` is the integration line; `main` only after **explicit Owner sign-off following real trial**; `release/previous` holds rollback source. **During initial migration, `main` is still the old V1.1 pointer and not the verified running V1.6.** Do not auto-promote after deployment.

## Mandatory 90-second recovery

1. Read [AGENTS.md](AGENTS.md) and [CEO_HANDOVER.md](control-room/CEO_HANDOVER.md).
2. Read [COORDINATION.md](control-room/COORDINATION.md); identify active RFQ, its `TASK_SPEC.md`, latest `EXECUTION_LOG.md`, `REVIEW.md`, `FINAL_REPORT.md`. Read only the necessary sections; [MODULE_INDEX](docs/MODULE_INDEX.md) routes to module details.
3. Verify exact remote/local branch and HEAD, `git status --short`, `git diff`, `git worktree list --porcelain`. Preserve dirty work and existing active worktree.
4. When real business is involved, independently verify live process, installed EXE/config, SQLite holds and WAL/SHM, Google sheet row/permissions, INSO purchase, quotation and SMTP outcomes **before resuming**. Another session ending does not mean a process stopped.
5. Reconcile the last checkpoint in the **existing** `EXECUTION_LOG.md` with live facts; only then continue the next authorized safe action. Do not double-start or replay UNKNOWN.

## Roles

- **CEO:** translate Owner intent into Task Spec, maintain short authoritative status/hand-over; review code/evidence independently. Write a bounded `REVIEW.md` conclusion (PASS or CHANGES_REQUESTED). No second production Executor.
- **Executor:** receive `执行 RFQ-XXX`; follow current Task Spec; reuse production infrastructure; checkpoint before real effects and after receipts; test, verify, commit/push safe progress; final chat and `FINAL_REPORT.md` use [seven headings](docs/REPORTING.md).
- **Replacement window:** start here, not from chat. If a predecessor is unresponsive, inspect actual live operations and durable protections; preserve anything uncertain and report `NOT_VERIFIED`.

## Current non-negotiables

- Owner now **permits Agent Computer Use** where supported; real business operations remain separately authorized under [SAFETY](docs/SAFETY.md). Record whether GUI tools were actually used.
- Single Chrome CDP profile/port `9222` remains protected: [session policy](docs/CDP_SESSION_POLICY.md).
- No duplicate order effects, no fabricated completion, no deletion of dirty work, protected DB or rollback. Prefer CLI/API where safe; supported GUI is allowed.
- Keep docs short: current decision at top, historic details via pinned links. [History index](docs/HISTORY.md).

Previous extended instructions: [pinned revision](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/AI_START_HERE.md).
