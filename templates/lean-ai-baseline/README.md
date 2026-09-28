# Lean AI RFQ Template

Use this template when you want any fresh Codex/Claude session to work from a one-line command.

## Setup

Copy into the project:
- `AI_START_HERE.template.md` → `AI_START_HERE.md`
- `AGENTS.template.md` → `AGENTS.md`
- needed `docs/*.template.md` → `docs/*.md`
- `control-room/COORDINATION.template.md` → `control-room/COORDINATION.md`
- one copy of `control-room/RFQ_TEMPLATE/` per RFQ

Rename the RFQ folder to the real ID, e.g. `RFQ-001`.

## Daily use

After requirement discussion, Owner/CEO completes the Task Spec.

Executor receives only:

`执行 RFQ-001`

Independent reviewer receives only:

`Review RFQ-001`

Git preserves implementation history. Control Room preserves task intent, execution references, final report and review state.
