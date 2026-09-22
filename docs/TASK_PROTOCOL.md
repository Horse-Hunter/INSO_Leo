# Task Protocol

Use one stage-sized Task Packet for one bounded outcome. The packet carries the context Codex needs; historical Tasks are audit evidence and are not default reading.

Recommended path: `tasks/YYYY-MM-DD-short-slug.md`.

## Task Packet

```markdown
# Task: <title>

status: proposed | ready | in_progress | blocked | complete
actor_role: <canonical role>
module: <module_id | architecture | utility>
reports_to: <canonical superior>
execution_mode: FAST_V1
architecture_impact: NONE | REQUIRED

## Problem
## Goal
## Current Facts
Only facts required by this Task; mark missing evidence UNKNOWN.

## Required Context
Exact files/evidence to read. Do not request all historical context.

## Write Scope
Exact paths or systems the actor may change.

## Scope
## Non-scope
## Requirements
## Acceptance
- [ ] Observable outcome.

## Execution
Required checks, authorized side effects, commit/push expectation, and stop point.

## Final Report
Use the standard Codex report below; record limitations and remaining UNKNOWN.
```

`architecture_impact: REQUIRED` applies to module add/delete/rename, responsibility or dependency changes, public contracts, global Workflow, safety boundaries, or AI roles. Module actors escalate it; CEO decides and Architecture Codex synchronizes canonical files.

## FAST_V1 execution

Within approved scope, Codex runs diagnosis → implementation → tests → fix → smoke → self-review → commit → push continuously. Do not split a simple feature into mechanical micro-Tasks or pause over function names, class/function choice, mocks, parsers, selectors, test layout, internal exception wrappers, ordinary library choice, small scoped bugs, or non-critical refactors.

Codex interrupts Owner only for: a real business-behavior decision; human login/CAPTCHA/OTP/device verification; a first or unauthorized production write; possible overwrite/deletion of real data; sensitive Credential/customer-message/order/payment behavior; or material expansion beyond approved business scope. Ordinary implementation choices remain autonomous.

All external effects follow `BOUNDARIES.md`. For a new website flow, complete the browser-first reconnaissance in `AI_TEAM.md`, then prefer one end-to-end stage Task covering understanding, adapter, parser, automation, integration, tests, and smoke.

## Review

- **DONE:** acceptance is met.
- **CONTINUE:** list only changes required for acceptance.
- **FOLLOW-UP:** original Task is DONE; open a new Task for the new issue.
- **BLOCKED:** state the real blocker.

Do not prolong V1 Review for naming, cosmetic abstraction, non-critical debt, or “could be prettier.”

## Reports

Codex → superior:

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

Module Chat → CEO:

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

CEO → Owner:

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

When Codex or a subordinate must ask Owner, the first screen is:

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

Only then attach essential tests, logs, or technical evidence. Do not paste development history.

## Completion

Before reporting DONE: satisfy acceptance, run proportionate checks, inspect the full diff, confirm no unrelated or secret material, update Task status, commit/push when authorized, and stop at the Task boundary.
