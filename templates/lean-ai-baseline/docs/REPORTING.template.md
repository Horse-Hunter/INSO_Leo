# Human Report

**Every Executor task (RFQ or not):** final Owner-facing **chat reply** must use these exact seven headings, in order; RFQ `FINAL_REPORT.md` must match. State actual status, test vs. live verification and one Owner action (`NONE` if none). Source/evidence: this file and final responses; CEO Review enforces. Technical detail stays in logs.

## Executor final summary to Owner

```text
正在实现什么：
<一句话>

理想变化是什么：
<用户/业务期望>

以前是什么：
<执行前状态>

现在是什么：
<执行后状态>

做完了什么：
<可验收结果>

测试结果：
<人话说明通过/未通过、范围、是否真实验证>

你接下来需要做什么：
NONE / Review RFQ-XXX / <唯一 Owner 动作>
```

## CEO Review summary to Owner

```text
Review 结论：
PASS / CHANGES_REQUESTED

发生了什么：
<人话>

影响什么：
<人话>

接下来做什么：
<人话>
```

Owner-facing text must stay plain-language. Precise technical detail belongs in Executor-facing execution logs, technical review findings, Git, tests and evidence.
