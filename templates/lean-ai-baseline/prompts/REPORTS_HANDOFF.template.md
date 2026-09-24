# 汇报、提问与 Handoff 提示模板

正式字段和状态以 `docs/TASK_PROTOCOL.md`、`docs/AI_TEAM.md` 为准；本文件只提供可复制提示词。

## Coding Executor 阶段汇报

```text
请按 canonical Executor Final Report 输出，仅包含：
状态 / 需要决定 / 你要做什么 / 完成 / 验证 / 真实效果 / 剩余 / Commit / Push。
结论优先，不搬运开发过程、长日志或大段代码。
```

## 管理层汇报

```text
Module Chat → CEO：状态 / 需要决定 / 你要做什么 / 完成 / 跨模块影响 / 下一步 / Commit。
CEO → Owner：状态 / 需要决定 / 你要做什么 / 进展 / 问题 / 下一步。
```

## 向 Owner 提问

```text
以前：<OLD_STATE>
现在：<CURRENT_PROBLEM>
真实效果：<BUSINESS_IMPACT>
需要决定：<ONE_DECISION_OR_NONE>
你要做什么：<ONE_ACTION_OR_A_B>
还有什么没解决：NONE / <GAP>
建议：<A_OR_B>
原因：<ONE_SENTENCE>
```

## 长期 Chat 交接

```text
# ⚠️ 建议开始 <ROLE> Chat 交接

请生成一份可复制 Handoff，包含：
角色 / canonical 事实 / 当前 Task / Repo 与 HEAD / 已完成 / 未完成 / 风险 / 下一步。
新 Chat 必须先核对 Git 当前事实，再继续原职责。
```

## Executor 强制交接

```text
# ⚠️ HANDOFF_REQUIRED
Task: <TASK>
HEAD: <HASH>
已完成: <DONE>
未完成: <NOT_DONE>
修改文件: <FILES>
未提交内容: <UNCOMMITTED>
Tests: <CHECKS>
Blocker: <BLOCKER>
下一步: <NEXT_ACTION>
```
