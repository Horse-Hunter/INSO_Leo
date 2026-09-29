# AI Workflow

```text
Discuss requirement with CEO
→ CEO creates/completes RFQ Task Spec
→ Control Room stores spec
→ “执行 RFQ-XXX” to any implementation agent
→ implementation + execution log + tests/evidence/commits + final report
→ fixed human summary
→ if review required, Owner returns to CEO:
  “Review RFQ-XXX”
→ CEO independently reviews spec/log/report/diff/code/tests/runtime evidence
→ PASS = REVIEWED_DONE
→ FAIL = CHANGES_REQUESTED
```

States:

`DRAFT → READY → IN_PROGRESS → REVIEW_REQUIRED → REVIEWED_DONE`

Review failure:

`REVIEW_REQUIRED → CHANGES_REQUESTED → IN_PROGRESS`

No-review task:

`IN_PROGRESS → DONE`

Every action must advance RFQ acceptance. If progress stalls, reread the RFQ and canonical docs and return to the shortest implementation path.
