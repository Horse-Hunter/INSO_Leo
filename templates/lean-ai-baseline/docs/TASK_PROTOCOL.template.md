# Task Protocol

一个阶段级 Task Packet 对应一个有边界的结果。Task 自带执行所需上下文；历史 Tasks 是审计证据，不是默认阅读材料。

建议路径：`tasks/YYYY-MM-DD-short-slug.md`。

## Task Packet

```markdown
# Task: <TITLE>

status: proposed | ready | in_progress | blocked | complete
actor_role: <CANONICAL_ROLE>
module: <MODULE_ID | architecture | utility>
reports_to: <CANONICAL_SUPERIOR>
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

## Execution
写明必要检查、已授权副作用、commit/push 预期和停止点。

## Final Report
使用本文件的标准报告，记录限制和剩余 UNKNOWN。
```

新增/删除/重命名模块，改变职责/依赖、公共 Contract、全局 Workflow、安全边界或 AI 角色时，设为 `architecture_impact: REQUIRED`。模块角色升级，CEO 决策，Architecture Codex 同步 canonical 文件。

## FAST_V1 执行

Scope 内连续完成 diagnosis → implementation → tests → fix → smoke → self-review → commit → push。不得机械拆分简单功能，也不得因命名、内部结构、mock、parser、selector、测试布局、普通 library 选择、小 bug 或非关键重构而频繁请示。

只在以下情形中断 Owner：真实业务行为必须由 Owner 决定；人工登录/CAPTCHA/OTP/设备验证；首次或未授权生产写；可能覆盖/删除真实数据；敏感 Credential/客户消息/订单/支付；必须明显扩大业务 Scope。

所有外部副作用遵守 `BOUNDARIES.md`。新增网页流程先按 `AI_TEAM.md` 完成 Browser-first 观察，再发布端到端阶段 Task。

## Review

- **DONE：**满足验收。
- **CONTINUE：**只列影响验收的必须修改项。
- **FOLLOW-UP：**原 Task DONE；新问题另开 Task。
- **BLOCKED：**说明真实阻塞。

不得因非关键美观或技术债反复要求 V1 修改。

## 标准报告

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
<HASH>

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
NONE / <IMPACT>

需要 CEO 决定：
NONE / <ONE_DECISION>

下一步：
<NEXT_ACTION>

Commit：
<HASH_IF_ANY>
```

CEO → Owner：

```text
结论：
<ONE_SENTENCE>

进展：
<IMPORTANT_DELTA>

问题：
NONE / <REAL_PROBLEM>

需要你决定：
NONE / <CLEAR_OPTIONS>

下一步：
<WHO_DOES_WHAT>
```

向 Owner 提问时，第一屏使用：

```text
以前：
<OLD_STATE>

现在：
<CURRENT_PROBLEM>

真实效果：
<BUSINESS_IMPACT>

你要做什么：
<ONE_ACTION_OR_A_B>

还有什么没解决：
NONE / <GAP>

建议：
<A_OR_B>

原因：
<ONE_SENTENCE>
```

## 完成标准

报告 DONE 前：满足 Acceptance，运行适用检查，检查完整 diff，确认无无关内容或 Secret，更新 Task 状态，在授权时 commit/push，并停在 Task 边界。
