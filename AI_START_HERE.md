# AI START HERE

This repository is **RFQ-driven**. The Control Room is the task source of truth.

**New window:** read `AGENTS.md`. Follow `docs/PROJECT_BASELINE.md` for same-task artifact cleanup and `docs/REPORTING.md` for the exact seven-heading final chat reply (also required in RFQ `FINAL_REPORT.md`).

## Owner 2026-11-14: Agent Computer Use is permitted

The Owner has **withdrawn** the earlier blanket ban on agent Computer Use. A connected agent may use supported desktop GUI screen reading, mouse/keyboard interaction and Windows UI controls for authorized project tasks; using CLI/PowerShell/Python, Git, APIs and the established application's CDP/Playwright remains equally permitted. No tool should claim access it does not have.

**This is a tool-permission change, not a production write grant.** Preserve the single Chrome 9222/profile, original worktree, running process and durable SQLite/UNKNOWN/SENT state. Before any real Google write, INSO purchase, quotation button, SMTP send, permission elevation or production release, apply existing scoped Owner authorization and fail-closed protections. Do not launch a second order processor or replay uncertain effects. Actual tool usage must be stated truthfully as `COMPUTER_USE_USED` or `COMPUTER_USE_NOT_USED` in RFQ evidence, not automatically declared non-use. See `AGENTS.md`, `docs/SAFETY.md` and `docs/CDP_SESSION_POLICY.md`. Historical Computer Use bans in older reports are superseded only prospectively by this Owner decision.

## For implementation agents: 执行 RFQ-XXX

The Owner may open any implementation-agent session (Codex / Claude / WorkBuddy or equivalent) and say only:

`执行 RFQ-XXX`

The command alone is sufficient. Do not ask the Owner to restate the task.

1. Read `control-room/COORDINATION.md` and `control-room/RFQ-XXX/TASK_SPEC.md`.
2. Read `docs/MODULE_INDEX.md`, then only relevant module docs/code.
3. Inspect current Git state, relevant commits/diff, tests and existing evidence.
4. **Run a reuse audit before design or coding:** inspect the current implementation, previous stable/release version, existing runtime configs, shared adapters, migrations, scripts, packaging, tests and prior RFQ decisions. Reuse every capability that already satisfies the requirement.
5. Set RFQ to `IN_PROGRESS` and implement the **minimum incremental change** needed to satisfy acceptance.
6. Record technical detail in `EXECUTION_LOG.md`: reused capabilities, any justified non-reuse, decisions, changed files/diff range, exact tests/results, evidence references, commits and true blockers.
7. Clean up owned disposable artifacts during this task; retain protected runtime/CDP/rollback.
8. Use the exact `docs/REPORTING.md` seven-heading template in `FINAL_REPORT.md` **and the final chat reply**.
9. If review is required, set `REVIEW_REQUIRED`; otherwise set `DONE`.
10. Commit and push implementation + Control Room records, subject to normal security/release authorization.

Ordinary technical problems stay inside the implementation session.

## Reuse is mandatory

- Existing stable behavior is an inheritance baseline, not an example to re-create.
- Do not repeat discovery, architecture thinking or implementation that the repository has already solved.
- Do not introduce a second production path, second config format, second adapter or second release mechanism for an existing responsibility unless the RFQ explicitly requires replacement.
- If the existing capability cannot be reused, prove that in `EXECUTION_LOG.md` before adding a replacement.
- Temporary validation/discovery paths must be folded back into the canonical production path before delivery.
- If progress stalls, first search for an already-solved path. Do not compensate by inventing another framework or implementation.

## Protected shared asset: the INSO CDP session — mandatory

**Trigger:** any work that reads INSO, or that touches the browser/CDP, session, launcher or runtime configuration.

The Owner has completed the one-time INSO phone-code login and will not provide another. That login lives in exactly one Chrome profile and is the single most critical, non-reproducible asset in the project.

- **One profile, one port.** Every `browser_bootstrap.profile_dir` is
  `D:\Program_Leo\INSO_CDP\chrome-profile`; every `debug_port` is `9222`. No version, worktree, AI session or test may use anything else.
- **Never create a second CDP.** Keep `persistent_session: true`; the launcher attaches to the running endpoint or resumes the *same* profile, and refuses to start a blank profile.
- **Never force-kill the Chrome on 9222.** Persistent handles are never owned, so no release, failure or timeout path may stop it.
- **Never delete or move** the canonical folder, its junction, or the physical profile.
- **Source of truth:** `docs/CDP_SESSION_POLICY.md`. **Only supported start/reuse tool:** `scripts/open_cdp_session.ps1`. **Backup:** `D:\Program_Leo\INSO_CDP\session-backup\` (refreshed automatically on every attach).
- **Owner:** Executor applies it and records evidence; Reviewer/CEO enforces it.
- **Enforcement:** Review fails if any config diverges from the canonical profile/port, if `persistent_session` is disabled, or if a change can close the session browser.

## CEO / WorkBuddy 随时接管入口（2026-11-07）

**先读 [control-room/CEO_HANDOVER.md](control-room/CEO_HANDOVER.md)**。这是持续更新的跨GPT、WorkBuddy及其他Agent的**唯一CEO长期交接索引**：第0节90秒接管、第1节冻结Git/正式EXE/业务与Review状态、第3节生产资产依赖、第5节开放风险、第7节跨Agent单一所有权切换。**当前V1.6分支不是默认main**；最新生产事实请核对 `V16_RELEASE_REPORT.md` 顶部及 `control-room/RFQ-016/FINAL_REPORT.md`。

- **切换CEO窗口无需新建工作树**，读本文件和当前Git便可接手。只有Owner明确将V1.6实施者从原窗口切换到另一个Agent时，才按原工作区/任务/未提交状态执行单一Executor交接；**禁止两个窗口同时操作正式业务**。
- Owner在2026-11-02资产治理范围中**排除GitHub公开性和IMAP专项**；作为历史范围约定保留，新任务以Owner最新明确要求为准，不从过时待办自动重开。
- 重要：旧Research、V1.2工作树、V1.4 runtime与Chrome/CDP/SQLite共享运行资产可能相互引用，不得将“旧目录”当可清理对象。详情见CEO交接第3节。
- 任何接手Agent不得把Git HEAD、离线测试、上次EXE哈希或历史 `BUSINESS_RUNNING` 直接等同为此刻实时运行状态；对无法核实的项目说明 `NOT_VERIFIED`。
- CEO负责更新原交接索引及独立Review；新Codex/WorkBuddy若只做非业务文档任务，不能顺带修改V1.6运行源码/部署。给Owner一份完整、可直接转发的执行指令，减少重复审批和搬运。

## For CEO: Review RFQ-XXX

The Owner returns to the CEO conversation and says only:

`Review RFQ-XXX`

CEO independently reads Task Spec, Execution Log, Final Report, RFQ Git diff/commits, current code, test evidence and runtime evidence.

CEO also verifies reuse discipline: no unnecessary parallel path, duplicate capability, repeated infrastructure or unjustified reimplementation.

CEO writes/updates `REVIEW.md` and RFQ status:

- PASS → `REVIEWED_DONE`
- FAIL → `CHANGES_REQUESTED`

CEO does not implement fixes inside the review. A failed RFQ goes back to an implementation agent under the same RFQ ID.

## Durable rule changes

Owner workflow/governance instructions are not satisfied by replying “understood.” CEO must convert them into executable repository rules immediately.

Every durable rule must define: **trigger, owner, procedure, source of truth, completion evidence, cleanup, enforcement**. Project-specific rules update project docs; reusable rules also update `templates/lean-ai-baseline/` in the same change.

## Taking over another Executor

Do not start by creating another worktree.

1. Inspect branch, `git status`, diff and `git worktree list --porcelain`.
2. Reuse the existing active worktree when suitable.
3. Read the single temporary `HANDOFF*.md` if present and verify it against current Git/runtime.
4. Move durable facts into `EXECUTION_LOG.md` or the correct canonical doc.
5. Delete the consumed handoff in the same work cycle.
6. Preserve any unique work before safely removing stale worktrees; never force-delete unknown dirty state; then run `git worktree prune`.
7. Mark obsolete blockers/next steps `RESOLVED` or `SUPERSEDED`.

Incoming Executor owns this cleanup. Outgoing Executor only prepares the minimal handoff and preserves the live workspace.

## Delivery first

Do not turn workflow into the task. The task is the required product outcome.

- Start from Owner intent + Task Spec and take the shortest safe path to a working result.
- Reuse existing working paths; do not create process around reuse unless a non-reuse decision needs justification.
- Do not add new gates/reports/approval steps unless the requirement, real safety/data-loss risk, or a proven recurring failure requires them.
- Fix housekeeping in-line when possible; do not stop implementation just to create more process.
- When Owner corrects one workflow problem, infer and address the obvious adjacent lifecycle/ownership implications so the same class of issue does not return in another form.

