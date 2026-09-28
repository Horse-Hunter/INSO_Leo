# AI Workflow

The project uses one canonical workflow:

```text
Owner ↔ CEO discuss requirement
        ↓
Owner/CEO creates or completes RFQ-XXX Task Spec
        ↓
Control Room stores the complete Task Spec
        ↓
Any Codex / Claude session receives only:
“执行 RFQ-XXX”
        ↓
Agent reads AI_START_HERE / MODULE_INDEX / repo / coordination
        ↓
Agent implements and writes technical execution records
        ↓
Agent returns the fixed human summary
        ↓
If independent review is required:
“RFQ-XXX 已完成，需要独立 Review”
        ↓
A new session receives:
“Review RFQ-XXX”
        ↓
Independent review reads spec/log/report/diff/code/tests/runtime evidence
        ↓
PASS → REVIEWED_DONE
FAIL → CHANGES_REQUESTED
```

## Task ownership

- Owner/CEO own requirement meaning and Task Spec.
- Executor owns implementation and `EXECUTION_LOG.md` / `FINAL_REPORT.md`.
- Independent reviewer owns `REVIEW.md`.
- Git stores actual code history/diff; Control Room stores task intent, execution references and review state.

## RFQ states

`DRAFT → READY → IN_PROGRESS → REVIEW_REQUIRED → REVIEWED_DONE`

Review failure:

`REVIEW_REQUIRED → CHANGES_REQUESTED → IN_PROGRESS`

If review is not required:

`IN_PROGRESS → DONE`

`BLOCKED` is reserved for a true escalation condition, not ordinary technical failure.

## Execution rule

Every instruction and action must advance the RFQ acceptance criteria. If progress stalls, reread the Task Spec, coordination state and relevant canonical docs, then return to the shortest implementation path. Do not create long procedural prompts to compensate for slow progress.
