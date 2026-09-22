# AI Start Here

This repository is organized for long-lived collaboration among humans, ChatGPT,
Codex, and Git. It contains working Research V1 functionality plus architecture
and documentation scaffolding for the remaining modules.

## Read in this order

1. Read the active Task Packet in `tasks/`.
2. Read `MODULE_INDEX.md` for ownership and dependency constraints.
3. Read `PRODUCT_BASELINE.md` for verified product facts and explicit unknowns.
4. Read `TASK_PROTOCOL.md` when creating, updating, or closing a task.
5. Inspect the relevant source and test directories before making changes.

## Operating principles

- Separate durable facts from task-specific context.
- Prefer the smallest change that satisfies the active Task Packet.
- Keep orchestration in `workflow`; keep domain behavior in its owning module.
- Record missing evidence as `UNKNOWN`, not as an assumption presented as fact.
- Keep external systems behind explicit module boundaries and test doubles.
- Do not add a dependency until a concrete task requires it and its cost is justified.
- Before completion, run applicable checks and inspect `git diff`.

## Repository map

| Path | Purpose |
| --- | --- |
| `AGENTS.md` | Short, durable rules for coding agents |
| `docs/` | Stable product, architecture, and collaboration documentation |
| `docs/AI_TEAM.md` | AI collaboration roles and decision hierarchy |
| `docs/modules/` | Durable boundaries and confirmed facts for individual modules |
| `tasks/` | Task Packets describing bounded units of work |
| `src/` | Source modules |
| `tests/` | Tests mirroring source module ownership |
| `data/` | Local runtime data and explicit non-sensitive fixtures |

## Current implementation status

- Platform and runtime: single-machine Windows with Python 3.12
- Verification baseline: pytest and ruff; packaging and exact commands remain `UNKNOWN`
- Selected V1 infrastructure: Python `sqlite3`, openpyxl, Google Sheets API with OAuth User Authorization, ordinary HTTP first, and Playwright where JavaScript or login is required
- External access: Research V1 is authorized only for read-only market research against the sources listed in `PRODUCT_BASELINE.md`; INSO and other production operations remain unauthorized
- Research V1 implementation: source adapters, market aggregation, idempotent
  Excel persistence, and the public `ResearchService` execution path are
  implemented
- Remaining implementation: Sheets, Workflow orchestration, INSO, and Quotation
  business behavior remain unimplemented on the current branch
- Credential Provider: the capability is documented, but its implementation is
  not present in the canonical source tree
