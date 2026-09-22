# Task Protocol

一个阶段级 Task Packet 对应一个有边界的结果。Task 自带 Codex 所需上下文；历史 Tasks 是审计证据，不是默认阅读材料。

建议路径：`tasks/YYYY-MM-DD-short-slug.md`。

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
使用下方 Codex 标准报告，记录限制和剩余 UNKNOWN。
```

新增/删除/重命名模块、改变模块职责或依赖、公共 Contract、全局 Workflow、安全边界或 AI 角色时，必须设为 `architecture_impact: REQUIRED`。模块角色负责升级，CEO 决策，Architecture Codex 同步 canonical 文件。

## FAST_V1 执行

在已批准 Scope 内，Codex 连续完成 diagnosis → implementation → tests → fix → smoke → self-review → commit → push。不得把简单功能机械拆成微型 Tasks，也不得因函数名、class/function 选择、mock、parser、selector、测试结构、内部异常封装、普通 library 选择、Scope 内小 bug 或非关键重构而停下来请示。

Codex 只在以下情形中断 Owner：必须决定真实业务行为；需要人工登录/CAPTCHA/OTP/设备验证；首次或未授权生产写；可能覆盖/删除真实数据；涉及敏感 Credential/客户消息/订单/支付；必须明显扩大已批准业务 Scope。普通实现问题自主决定。

所有外部副作用遵守 `BOUNDARIES.md`。新增网页流程先按 `AI_TEAM.md` 完成 Browser-first 观察，再优先用一个端到端阶段 Task 覆盖 understanding、adapter、parser、automation、integration、tests 和 smoke。

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
