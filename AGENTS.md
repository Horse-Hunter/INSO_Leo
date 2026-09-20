# AGENTS.md

## Working rules

- Start every task at `docs/AI_START_HERE.md` and follow the navigation there.
- Read the relevant Task Packet in `tasks/` before changing code. If none exists, create or request one using `docs/TASK_PROTOCOL.md`.
- Respect the module boundaries and dependency rules in `docs/MODULE_INDEX.md`.
- Treat `docs/PRODUCT_BASELINE.md` as the source of verified product facts. Preserve `UNKNOWN` where evidence is missing; do not invent business rules.
- Keep changes scoped to the active task. Do not add dependencies, access production, use credentials, or perform external side effects unless the Task Packet explicitly authorizes them.
- Never commit secrets, credentials, customer data, raw production output, or unnecessary generated files.
- Place implementation under `src/<module>/` and corresponding tests under `tests/<module>/`.
- Verify proportionally to the change, review `git diff`, and report changed files, checks, limitations, and remaining `UNKNOWN` items.
- Do not start a follow-on business task without an explicit user request.

## Project navigation

- AI entry point: `docs/AI_START_HERE.md`
- Module ownership and dependency rules: `docs/MODULE_INDEX.md`
- Product facts and unknowns: `docs/PRODUCT_BASELINE.md`
- Task Packet format and lifecycle: `docs/TASK_PROTOCOL.md`
- Active and completed task records: `tasks/`
