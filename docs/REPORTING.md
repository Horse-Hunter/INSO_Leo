# Human Report

Anything shown directly to Owner must be understandable without software-development knowledge.

## Mandatory delivery channel and template (Executor)

**Trigger:** completion, blocked handoff or final status of **any** implementation, bugfix, audit, cleanup, release or RFQ task, including a freshly opened Codex window. **Executor** must use the seven headings below **verbatim, in the same order in the final chat message**. For RFQs, use the same structure in `FINAL_REPORT.md`; writing a report file does **not** replace the required chat reply. Fill each heading concisely in plain Chinese; use `NONE` when no Owner action is needed. Do not replace the template with a free-form paragraph or a technical log. Clearly distinguish safe/offline tests from real business verification; do not claim live PASS without evidence.

**Source of truth:** this file. **Evidence:** the actual final chat reply and, for RFQs, `FINAL_REPORT.md`. **Cleanup:** detailed logs, paths, internal codes and stack traces stay in technical records, not the Owner summary. **Enforcement:** CEO Review requests correction if the final reply or RFQ report omits/reorders the required headings; no new independent paperwork is needed.

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
