# Human Report

Anything shown directly to Owner must be understandable without software-development knowledge.

## Mandatory Executor response

**Trigger:** final status of **every** task, RFQ or not. **Executor** uses the seven headings below **verbatim and in order in the final chat reply** and, for RFQs, `FINAL_REPORT.md`. Keep it concise and business-readable; state real vs. offline verification, RFQ status and one next Owner action (`NONE` if none). Technical detail stays in logs.

**Source/evidence:** this file and actual chat/`FINAL_REPORT.md`. **Enforcement:** CEO requests correction for missing or altered headings; no extra paperwork.

## Executor final summary to Owner

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
<只说通过/未通过、关键范围和是否做过真实验证；不要堆技术术语>

你接下来需要做什么：
NONE / Review RFQ-XXX / <唯一需要 Owner 做的动作>
```

## CEO Review summary to Owner

```text
Review 结论：
PASS / CHANGES_REQUESTED

发生了什么：
<人话说明>

影响什么：
<对当前需求、上线、安全或下一步的实际影响>

接下来做什么：
<Executor 继续修 / Owner 无需操作 / 唯一 Owner 动作>
```

Rules:
- Owner-facing 内容只说人话。默认不出现 class、method、selector、stack trace、分页实现、runtime 内部状态等术语。
- Technical detail belongs in `EXECUTION_LOG.md`, `REVIEW.md` 的 Technical Findings、Git, tests and evidence.
- If review is required, the final field says `Review RFQ-XXX`, meaning return to the CEO conversation.
- Ordinary technical failures never become Owner actions.
