# AI Workflow

Use role names, not “我/你”, to avoid ambiguity.

```text
Owner 与 CEO 讨论需求
        ↓
CEO 创建 / 完善 RFQ-XXX Task Spec
        ↓
Control Room 保存完整 Task Spec
        ↓
Owner 随便打开任意 Codex / Claude 实现会话，只说：
“执行 RFQ-XXX”
        ↓
Executor 自己读取：
AI_START_HERE / MODULE_INDEX / RFQ / repo / coordination
        ↓
Executor 先做 Reuse Audit
        ↓
优先复用现有稳定能力，只做最小增量
        ↓
Executor 开始实现
        ↓
所有技术细节自动写入：
EXECUTION_LOG
git diff / commit
tests
evidence
decisions
FINAL_REPORT
        ↓
Executor 最后只给 Owner 固定的人话总结
        ↓
如果需要 Review，Executor 告诉 Owner：
“RFQ-XXX 已完成，需要独立 Review”
        ↓
Owner 回到 CEO 会话，只说：
“Review RFQ-XXX”
        ↓
CEO 自己读取全部技术材料并独立 Review
        ↓
CEO 同时检查是否存在重复实现/平行生产路径
        ↓
CEO 对 Owner 只说人话：
发生了什么
影响什么
接下来做什么
        ↓
技术修复要求只写给 Executor
        ↓
PASS → REVIEWED_DONE
FAIL → CHANGES_REQUESTED
```

## Ownership

- Owner：与 CEO 讨论需求；启动任意实现 Agent；接收最终人话总结；需要 Review 时回到 CEO。
- CEO：把需求写成完整 Task Spec；维护业务规则、架构/Safety 边界；独立 Review；对 Owner 负责把技术结论翻译成人话。
- Executor（Codex / Claude）：负责实现、调试、tests、live evidence、execution log、final report、commit/push，并读取技术化的 Review findings。
- Git：实现事实源。
- Control Room：需求、执行记录与 RFQ 状态源。

## Mandatory Reuse Gate

任何 RFQ 在进入设计/编码前必须先经过 Reuse Audit：

1. 查当前生产实现；
2. 查最近稳定/发布版本；
3. 查模块 Public Contract 与已有适配器；
4. 查 runtime 配置、数据库迁移、浏览器/session、GUI、Sheets、Research、Workflow、打包/发布脚本；
5. 查已有 tests、evidence 与已关闭 RFQ 的技术结论。

规则：

- **能复用的必须复用。**
- 新版本默认继承旧稳定版本已经跑通的基础设施和运行方式。
- 已经有结论的问题不得无新证据重复 discovery / 重复架构讨论。
- 已经有实现的能力不得另起一套平行实现。
- 新代码只能填真实 gap，并以最小增量方式加入现有生产主链。
- 如确实无法复用，Executor 必须先在 `EXECUTION_LOG.md` 记录：检查过什么、为什么不可复用、为什么新实现是最小必要变化。
- 临时验证、discovery、实验代码不得长期成为第二生产路径；交付前必须收敛回唯一 canonical path。
- 同一职责如果已经出现两套实现，优先合并/淘汰，不允许再造第三套。
- 重复故障必须沉淀为共享能力/contract/regression test，禁止靠重复人工排障或重复开发维持。

违反上述任一项即使功能测试通过，也不能视为 RFQ 完成。

## Owner communication rule

任何直接发给 Owner 的 CEO / Executor / Review 说明，都必须先转换成人能直接理解的业务语言，只回答三件事：

1. 发生了什么；
2. 对需求或使用有什么影响；
3. 接下来是谁做什么。

除非 Owner 主动要求技术细节，否则不在 Owner-facing 内容里出现 selector、class、method、stack trace、分页实现、runtime 内部状态等术语。

技术细节必须写入 Executor-facing 区域，例如：
- `EXECUTION_LOG.md`
- `REVIEW.md` 的 Technical Findings
- Git diff / commit
- tests / evidence

## RFQ states

`DRAFT → READY → IN_PROGRESS → REVIEW_REQUIRED → REVIEWED_DONE`

Review failure:

`REVIEW_REQUIRED → CHANGES_REQUESTED → IN_PROGRESS`

No-review task:

`IN_PROGRESS → DONE`

`BLOCKED` 只用于真实升级条件，不用于普通技术失败。

## Progress rule

Every executor action must advance the RFQ acceptance criteria. If progress stalls, reread the Task Spec, coordination state, Reuse Audit and relevant canonical docs, then return to the shortest implementation path. Do not create long procedural prompts, duplicate infrastructure or parallel paths to compensate for slow progress.

## Review rule

Review belongs to CEO, never to the implementation agent that executed the RFQ. CEO reviews independently and does not implement fixes inside the review. PASS closes the RFQ as `REVIEWED_DONE`; FAIL records concrete findings and changes status to `CHANGES_REQUESTED`.

CEO-facing review output has two layers:
- **Owner Summary:** plain language only.
- **Executor Technical Findings:** precise technical details and repair instructions.

CEO Review must reject unnecessary reimplementation, duplicated capabilities and unretired parallel production paths even when isolated tests pass.

## Rule Definition of Done

A governance/process instruction is complete only after it is operational, not when it is acknowledged in chat.

Every durable rule must define:

| Field | Required meaning |
| --- | --- |
| Trigger | exactly when the rule runs |
| Owner | role responsible for execution |
| Procedure | ordered actions |
| Source of truth | canonical file/state that is updated |
| Evidence | observable proof of completion |
| Cleanup | temporary/stale state to remove or supersede |
| Enforcement | Review consequence if skipped |

Responsibilities:
- Owner states policy/business intent.
- CEO converts durable intent into executable project rules; reusable rules also update the lean baseline templates in the same change.
- Executor applies the rule and records evidence.
- Reviewer/CEO checks evidence and rejects violations.
- Owner is never the reminder mechanism for a rule already given.

## Handoff / Worktree Procedure

**Trigger:** Executor changes, or duplicate/stale worktrees are discovered.

**Outgoing Executor**
1. Stop unsafe/live activity if needed.
2. Preserve the current worktree and all uncommitted work.
3. Create/update one minimal temporary `HANDOFF*.md` only if useful context is not already recoverable from canonical docs/Git.
4. Do not create a new worktree for the receiving agent.

**Incoming Executor**
1. Inspect branch, `git status`, diff and `git worktree list --porcelain`.
2. Reuse the current active worktree when suitable.
3. Read the handoff once and verify each current claim against Git/runtime.
4. Merge durable facts into `EXECUTION_LOG.md` or the correct canonical document.
5. Delete the consumed handoff in the same work cycle.
6. Audit other worktrees. Preserve unique work in traceable Git history before removal; never force-delete unknown dirty work.
7. Remove stale worktrees and run `git worktree prune`.
8. Record cleanup evidence in `EXECUTION_LOG.md`.

**Canonical-state rules**
- `TASK_SPEC.md`: current requirement meaning; Owner/CEO only.
- `COORDINATION.md`: current RFQ status.
- `EXECUTION_LOG.md`: durable execution history; old blockers/next steps remain only if explicitly marked `RESOLVED` or `SUPERSEDED`.
- `HANDOFF*.md`: temporary transport only; deleted after successful takeover.
- Default: one active implementation worktree per active version/RFQ. Extra worktrees require a current documented purpose.

**Review enforcement:** CHANGES_REQUESTED if expired handoff files, stale current-state instructions, or unexplained duplicate active worktrees remain.

