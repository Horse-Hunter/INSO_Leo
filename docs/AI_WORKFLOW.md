# AI Workflow — minimal operating cycle

`Owner → CEO Task Spec → one Executor → tests/live evidence → CEO Review → Owner business decision when needed`.

**New window:** [AI_START_HERE](../AI_START_HERE.md) → [handover](../control-room/CEO_HANDOVER.md) → [current RFQ status](../control-room/COORDINATION.md) → active task files. Do not require past chat transcript.

## Executor (`执行 RFQ-XXX`)

1. Inspect actual local/remote Git, worktrees, live process and existing effects; reuse approved code and worktree.
2. Read only relevant [modules](MODULE_INDEX.md). Implement minimum difference, not parallel architecture.
3. **Checkpoint pre-effect** (authorization, target, before-state, operation/hold); **reconcile post-effect** (actual receipt/state or UNKNOWN) in existing `EXECUTION_LOG.md`. Commit/push bounded safe progress. Never replay on session loss.
4. Record real tests, deployment, residual failures and cleanup. Publish exact [seven-heading report](REPORTING.md). Mark RFQ `REVIEW_REQUIRED` or `DONE` as appropriate.

## CEO (`Review RFQ-XXX`)

Verify active Task Spec, Git diff/commit, tests, release/live evidence, safety and reuse independently; write `REVIEW.md` with `PASS` or `CHANGES_REQUESTED` and update `COORDINATION.md`. CEO decisions belong in the repo, not only a chat response. CEO does not run an overlapping production Executor.

## Sudden interruption

Both roles may disappear with **no final response**. Resume from last durable checkpoint plus live verification; interrupted chat means **not verified**, not automatically stopped or completed. Keep a single current handover index and one RFQ execution log. Temporary `HANDOFF*.md` only for exceptional one-time transport; consume and retire it. No duplicated worktree, daemon or handoff system.

State flow: `DRAFT → READY → IN_PROGRESS → REVIEW_REQUIRED → REVIEWED_DONE`; failure: `CHANGES_REQUESTED → IN_PROGRESS`; no-review: `DONE`. Historical decisions: [archive](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/docs/AI_WORKFLOW.md).
