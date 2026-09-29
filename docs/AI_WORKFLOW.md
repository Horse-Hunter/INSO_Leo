# AI Workflow

The project uses one canonical workflow:

```text
Owner ↔ CEO discuss requirement
        ↓
CEO creates / completes RFQ-XXX Task Spec
        ↓
Control Room stores the complete Task Spec
        ↓
Any Codex / Claude implementation session receives only:
“执行 RFQ-XXX”
        ↓
Agent reads AI_START_HERE / MODULE_INDEX / repo / coordination
        ↓
Agent implements and writes execution log / tests / evidence / commits / final report
        ↓
Agent returns the fixed human summary
        ↓
If review is required:
“RFQ-XXX 已完成，需要独立 Review”
        ↓
Owner returns to CEO and says only:
“Review RFQ-XXX”
        ↓
CEO independently reads Task Spec / execution log / final report / Git diff /
current code / tests / runtime evidence
        ↓
PASS → REVIEWED_DONE
FAIL → CHANGES_REQUESTED
```

## Task ownership

- Owner + CEO own requirement meaning.
- CEO owns Task Spec quality, business rules, architecture/Safety boundaries and independent Review.
- Executor owns implementation and `EXECUTION_LOG.md` / `FINAL_REPORT.md`.
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

## Review rule

Review is performed by CEO, independent from the implementation agent. CEO does not fix code inside the review. PASS closes the RFQ as `REVIEWED_DONE`; FAIL records concrete findings and changes status to `CHANGES_REQUESTED`, after which an implementation agent executes the same RFQ again.
