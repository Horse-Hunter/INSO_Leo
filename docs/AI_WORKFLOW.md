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
Executor 最后只给 Owner 固定的人话总结：
正在实现什么
理想变化是什么
以前是什么
现在是什么
做完了什么
测试结果
你接下来需要做什么
        ↓
如果需要 Review，Executor 告诉 Owner：
“RFQ-XXX 已完成，需要独立 Review”
        ↓
Owner 回到 CEO 会话，只说：
“Review RFQ-XXX”
        ↓
CEO 自己读取：
Task Spec
Execution Log
Final Report
Git diff / commits
当前代码
Test evidence
Runtime evidence
        ↓
CEO 直接独立 Review
        ↓
PASS → REVIEWED_DONE
FAIL → CHANGES_REQUESTED
```

## Ownership

- Owner：与 CEO 讨论需求；启动任意实现 Agent；接收最终人话总结；需要 Review 时回到 CEO。
- CEO：把需求写成完整 Task Spec；维护业务规则、架构/Safety 边界；独立 Review。
- Executor（Codex / Claude）：只负责实现、调试、tests、live evidence、execution log、final report、commit/push。
- Git：实现事实源。
- Control Room：需求、执行记录与 RFQ 状态源。

## RFQ states

`DRAFT → READY → IN_PROGRESS → REVIEW_REQUIRED → REVIEWED_DONE`

Review failure:

`REVIEW_REQUIRED → CHANGES_REQUESTED → IN_PROGRESS`

No-review task:

`IN_PROGRESS → DONE`

`BLOCKED` 只用于真实升级条件，不用于普通技术失败。

## Progress rule

Every executor action must advance the RFQ acceptance criteria. If progress stalls, reread the Task Spec, coordination state and relevant canonical docs, then return to the shortest implementation path. Do not create long procedural prompts to compensate for slow progress.

## Review rule

Review belongs to CEO, never to the implementation agent that executed the RFQ. CEO reviews independently and does not implement fixes inside the review. PASS closes the RFQ as `REVIEWED_DONE`; FAIL records concrete findings and changes status to `CHANGES_REQUESTED`.
