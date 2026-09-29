# AI Workflow

```text
Owner 与 CEO 讨论需求
→ CEO 创建/完善 RFQ Task Spec
→ Control Room 保存完整 Task Spec
→ Owner 打开任意 Codex / Claude，只说“执行 RFQ-XXX”
→ Executor 读取 AI_START_HERE / MODULE_INDEX / RFQ / repo / coordination
→ Executor 先做 Reuse Audit
→ 复用现有稳定能力，只实现最小增量
→ 实现 + execution log + tests/evidence/commits + final report
→ Executor 只给 Owner 固定的人话总结
→ 若需 Review，Executor 告诉 Owner“RFQ-XXX 已完成，需要独立 Review”
→ Owner 回到 CEO，只说“Review RFQ-XXX”
→ CEO 独立读取全部技术证据并检查 reuse discipline
→ CEO 对 Owner 只说：发生了什么 / 影响什么 / 接下来做什么
→ 技术修复细节只写给 Executor
→ PASS = REVIEWED_DONE
→ FAIL = CHANGES_REQUESTED
```

## Reuse Gate

Before coding, inspect existing production/stable code, contracts, config, migrations, tests, scripts, packaging and prior decisions.

- Reuse every capability that already satisfies the need.
- New versions inherit stable infrastructure by default.
- Do not repeat settled discovery/architecture work without new evidence.
- Do not build parallel implementations for an existing responsibility.
- If reuse is impossible, document why before adding the minimum replacement.
- Temporary validation paths must converge into the canonical production path before delivery.
- Duplicate capability or unretired parallel production paths are review failures.

Owner-facing communication must not require software-development knowledge.
Technical implementation terms belong in Executor-facing logs/review findings/Git/tests/evidence.

States:

`DRAFT → READY → IN_PROGRESS → REVIEW_REQUIRED → REVIEWED_DONE`

Review failure:

`REVIEW_REQUIRED → CHANGES_REQUESTED → IN_PROGRESS`

No-review task:

`IN_PROGRESS → DONE`
