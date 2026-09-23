# Task Protocol

一个阶段级 Task Packet 对应一个有边界的结果，并自带执行所需上下文。

建议路径：`tasks/YYYY-MM-DD-short-slug.md`。

## Task Packet

```markdown
# Task: <title>

status: proposed | ready | in_progress | blocked | complete
actor_role: <canonical role>
executor_tool: CODEX | BUDDY | OTHER  # optional；当前实际工具
module: <module_id | architecture | utility>
reports_to: <canonical superior>
execution_mode: FAST_V1
architecture_impact: NONE | REQUIRED

## Problem
## Goal
## Current Facts
只放本 Task 必需事实；缺少证据时标记 UNKNOWN。

## Required Context
指定必须读取的文件/证据，不要求全量历史上下文。

## Write Scope
列出允许修改的路径或系统。

## Scope
## Non-scope
## Requirements
## Acceptance
- [ ] 可观察的验收结果。

## Owner Decisions（optional）
只记录会改变代码行为的正式决定。

## Pending Owner Decision（temporary, optional）
只记录当前唯一待确认问题。

## Execution
写明必要检查、已授权副作用、commit/push 预期和停止点。

## Final Report
使用下方 Codex 标准报告，记录限制和剩余 UNKNOWN。
```

模块增删/改名、职责/依赖、Public Contract、产品范围、全局 Workflow、安全边界或 AI 角色变化须设 `architecture_impact: REQUIRED` 并通过 CEO Gate。批准后按 `AI_TEAM.md` 分配 Write Scope：Module Codex 同一 Task 更新 module doc、code、tests；Architecture Codex 只改受影响的全局 canonical。Gate 不转移 ownership。

## 执行器与上下文

`actor_role` 是逻辑岗位，`executor_tool` 是当前工具。优先在 Task 边界切换；中途故障可 Handoff，但 Task ID、role、Scope、Contract、权限和 Acceptance 原则上不变。新执行器读取当前 Task、必要 canonical docs、`git status`、`git diff`、recent commits，不假定继承隐藏上下文。

同一 dirty worktree 只允许一个写入执行器；并行须拆分 Write Scope/worktree。等待 Owner 时写 `Pending Owner Decision`；回答后、继续前移入 `Owner Decisions`。若未记录便中断，新执行器只确认该 Pending Decision。

## FAST_V1 执行

Scope 内连续完成 diagnosis → implementation → tests → fix → smoke → self-review → commit → push。普通实现选择自主处理，不机械拆 Task。

仅因真实业务决定、人工验证、未授权生产写、真实数据覆盖/删除、敏感 Credential/客户消息/订单/支付或明显扩 Scope 中断 Owner。

外部副作用遵守 `BOUNDARIES.md`；新增网页流程先按 `AI_TEAM.md` 做 Browser-first，再发布端到端阶段 Task。

## Review

- **DONE：**满足当前 Task 验收。
- **CONTINUE：**只列影响验收的必须修改项。
- **FOLLOW-UP：**原 Task DONE；新问题另开 Task。
- **BLOCKED：**说明真实阻塞。

不得因命名、轻微抽象、非关键技术债或“可以更漂亮”而反复要求 V1 修改。

## 汇报模板

Codex → 上级：

```text
状态：
DONE / BLOCKED

完成：
- 核心结果

验证：
- 关键 tests / smoke

真实效果：
- 业务上现在能做什么

剩余：
NONE / 真实 gap

Commit：
<hash>

Push：
SUCCESS / NOT PUSHED

需要决定：
NONE / 一个明确问题
```

Module Chat → CEO：

```text
状态：
DONE / CONTINUE / BLOCKED / ESCALATE

完成：
<1-3 句>

跨模块影响：
NONE / 具体影响

需要 CEO 决定：
NONE / 一个明确问题

下一步：
<准备做什么>

Commit：
<如有>
```

CEO → Owner：

```text
结论：
一句话。

进展：
重要变化。

问题：
NONE / 真问题。

需要你决定：
NONE / 明确选项。

下一步：
谁做什么。
```

Codex 或下级机构必须向 Owner 提问时，第一屏使用：

```text
以前：
<原状态>

现在：
<当前问题>

真实效果：
<业务影响>

你要做什么：
<一个明确动作 / A 或 B>

还有什么没解决：
<NONE / gap>

建议：
<A / B>

原因：
<一句话>
```

之后只附必要 Tests、Logs 或 Technical Evidence，不搬运开发过程。

## 完成标准

报告 DONE 前：满足 Acceptance，运行适用检查，检查完整 diff，确认无无关内容或 Secret，更新 Task 状态，在授权时 commit/push，并停在 Task 边界。

DONE 后删除 Pending Decision、临时 Handoff、debug/报错、中间方案和恢复说明；保留 Goal、Final Result、关键 Owner Decisions、Verification、Commit、Remaining Gap。长期决定提升到 canonical owner 文档；completed Task 仅供追溯，不是默认上下文。
