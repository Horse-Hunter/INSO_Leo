# Human Report

The executor's chat reply and `FINAL_REPORT.md` use exactly these seven fields:

```text
正在实现什么：
<一句话>

理想变化是什么：
<用户/业务期望>

以前是什么：
<执行前状态>

现在是什么：
<执行后状态；含 RFQ 状态>

做完了什么：
<已完成的可验收结果>

测试结果：
<关键 tests / live / evidence / commit>

你接下来需要做什么：
NONE / Review RFQ-XXX / <唯一需要 Owner 做的动作>
```

Rules:
- Technical detail belongs in `EXECUTION_LOG.md`, Git, tests and evidence—not in the Owner-facing reply.
- If review is required, the final field says `Review RFQ-XXX`, meaning **return to the CEO conversation**; do not open a new implementation/reviewer agent.
- Ordinary technical failures never become Owner actions.
