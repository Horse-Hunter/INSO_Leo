# Agent Entry

Start with `AI_START_HERE.md`.

- Owner + CEO discuss requirements; CEO creates/completes the RFQ Task Spec.
- Owner may open any Codex / Claude implementation session and say only `执行 RFQ-XXX`.
- `Review RFQ-XXX` belongs to CEO/Architect/Safety, not the implementation agent.
- Task requirements live in `control-room/RFQ-XXX/TASK_SPEC.md`; RFQ status lives in `control-room/COORDINATION.md`.
- Read `docs/MODULE_INDEX.md` and only the module docs/code relevant to the RFQ.
- Executor owns ordinary implementation, debugging, tests, live verification, evidence, execution records and commit/push until acceptance.
- CEO owns independent Review and final PASS / CHANGES_REQUESTED verdict.
- **Anything shown directly to Owner must be plain business language.** It must answer: what happened, what it affects, and what happens next. Do not expose class names, selectors, method names, pagination details, stack traces, runtime internals, or similar implementation jargon unless Owner explicitly asks.
- **Technical findings are for Executor-facing records only.** Put precise implementation terms and repair instructions in RFQ `REVIEW.md` technical findings, `EXECUTION_LOG.md`, Git/tests/evidence, not in the Owner-facing summary.
- Owner is involved only for genuine business decisions, explicit Safety/Write Gate authorization, human security challenges, destructive Git, major architecture, or release/merge decisions.
- Never persist secrets in Git, logs, fixtures, evidence or reports.

## Mandatory Reuse-First Rule

- Existing working capability is the default solution. Reuse it before designing anything new.
- Before coding, search the current codebase, stable/release branches, module contracts, runtime configuration, migrations, tests, scripts, packaging and prior RFQ decisions for an existing solution.
- A newer version inherits the previous stable version's working infrastructure unless the Task Spec explicitly changes it. Do not rebuild configuration, credentials, Sheets, Research, Workflow, browser/session, GUI shell, database migration, packaging or release plumbing merely because the version changed.
- Do not reopen settled technical decisions or repeat discovery unless requirements changed or new evidence proves the old decision invalid.
- Do not create parallel implementations, duplicate adapters, duplicate launch paths, duplicate configuration formats, duplicate migration paths or temporary replacements when an existing path can be extended.
- New implementation is allowed only for a real capability gap. The Executor must record in `EXECUTION_LOG.md` what existing capability was inspected, why it could not be reused, and why the new code is the minimum necessary delta.
- Temporary discovery/verification code must converge back into the single canonical production path before delivery. Long-lived parallel production paths are prohibited unless explicitly approved by CEO/Task Spec.
- Repeated technical problems must become one shared capability/contract/regression test, not another implementation or another round of chat reasoning.
- If two usable implementations exist for the same responsibility, stop and consolidate rather than adding a third.
