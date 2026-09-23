# Task: BASELINE-V2.2 Executor Independence & Context Lifecycle

status: complete
actor_role: Architecture Codex
executor_tool: CODEX
module: architecture
reports_to: CEO / Architecture Chat
execution_mode: FAST_V1
architecture_impact: REQUIRED

## Goal

以最少文字完成当前项目和通用模板的执行器解耦与上下文生命周期规则，不修改业务代码或业务 Contract。

## Final Result

- 当前正式 `* Codex` 名称保留为逻辑岗位，实际 Coding Agent 可替换。
- Task 支持可选 `executor_tool`、安全切换、最小现场恢复和单 dirty worktree 单写入者。
- Owner Decision 可跨执行器恢复；DONE 后临时上下文被清理，completed Task 仅作审计。
- 通用模板改用厂商无关的 Architecture/Browser-Recon/Utility/Module Executor 名称。

## Owner Decisions

- 换工具不改变 Task Contract，也不触发 Architecture Sync。
- 岗位、模块、汇报关系或职责变化才触发团队架构同步。
- 本 Task 不修改架构图；图形维护由对应职责另行处理。

## Verification

- 修改范围和 Markdown 相对链接检查通过；业务代码、产品/安全基线、module docs 未变。
- `git diff --check`、Secret scan clean；未引入 Registry、Queue、Lease、调度平台或复杂状态系统。
- 十个治理/模板文件字符总量约 `15,842 -> 16,345`（`+3.2%`），diff 净减少 66 行。

## Commit

- `docs: decouple executors and compact task context`（本 Task 所在提交）

## Remaining Gap

- `DIAGRAM_SYNC_REQUIRED`：现有架构图关系不变，但可由 Utility 后续补充“执行岗位不绑定具体工具”的 Legend。
