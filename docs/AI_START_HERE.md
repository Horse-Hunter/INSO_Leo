# AI Start Here

This repository is organized for long-lived collaboration among humans, ChatGPT, Codex, and Git. The current repository contains architecture and documentation scaffolding only; it does not contain working business functionality.

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
| `tasks/` | Task Packets describing bounded units of work |
| `src/` | Source modules |
| `tests/` | Tests mirroring source module ownership |
| `data/` | Local runtime data and explicit non-sensitive fixtures |

## Current implementation status

- Project language and runtime: `UNKNOWN`
- Build, lint, type-check, and test commands: `UNKNOWN`
- Production connectivity: not configured and not authorized by the baseline scaffolding
- Business functionality: intentionally not implemented
