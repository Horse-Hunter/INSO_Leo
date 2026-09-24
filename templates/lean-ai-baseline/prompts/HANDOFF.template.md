# 临时 Handoff

仅执行器中途故障、上下文严重退化或 dirty worktree 需接管时创建。恢复后删除；正常换 Agent 直接按 `AGENTS.md` 与 Git 恢复。

Role: `<ROLE>`

Goal: `<CURRENT_STAGE_GOAL>`

Branch/worktree: `<BRANCH_AND_PATH>`

Last Good Commit: `<HASH>`

Done: `<VERIFIED_DONE>`

Uncommitted: `<FILES_AND_PURPOSE>`

Tests: `<RUN_AND_RESULT>`

Blocker: `<TRUE_BLOCKER_OR_NONE>`

Next: `<ONE_CONCRETE_ACTION>`

接管者先核对 `git status`、`git diff`、近期提交和 canonical docs，不把本文件当作替代证据。
