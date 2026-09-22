# AI Start Here

This file routes each role to its minimum context. Do not read every Markdown file “for safety.” Formal role and module names come from `AI_TEAM.md` and `MODULE_INDEX.md`.

## Reading matrix

| Role | Read by default | Read only when needed |
| --- | --- | --- |
| Human Owner | Nothing required | Requested decision evidence |
| CEO Chat | `AI_TEAM.md`, `BOUNDARIES.md`, `PRODUCT_BASELINE.md`, `MODULE_INDEX.md` | Relevant module doc and current Git facts |
| Architecture Codex | `AGENTS.md`, current Task, `AI_TEAM.md`, directly affected architecture docs | `BOUNDARIES.md`, `MODULE_INDEX.md` |
| Requirements / Browser-Recon | `AI_TEAM.md`, `BOUNDARIES.md`, `PRODUCT_BASELINE.md`, Owner request | Relevant module doc and live/Repo evidence |
| Utility Codex | `AGENTS.md`, current Task, directly affected files | `BOUNDARIES.md`, affected module doc |
| Module Chat | `AI_TEAM.md`, `TASK_PROTOCOL.md`, its module doc | `BOUNDARIES.md`, `MODULE_INDEX.md`, related public contracts |
| Module Codex | `AGENTS.md`, current Task, its module doc, Task-related code | Product baseline, module index, other module docs, historical Tasks |

## Canonical owners

| Fact | Canonical document |
| --- | --- |
| AI organization, authority, escalation, handoff | `AI_TEAM.md` |
| Task format, execution, review, reporting | `TASK_PROTOCOL.md` |
| Safety and real-side-effect authorization | `BOUNDARIES.md` |
| Module names, ownership, dependencies | `MODULE_INDEX.md` |
| Product scope and cross-module business facts | `PRODUCT_BASELINE.md` |
| One module’s public contract and durable rules | `modules/<MODULE>.md` |
| Current implementation | Git `main`, current Task, code, tests, Module Final Report |

`tasks/` is audit history, not default context. Local AI1/AI2/AI3 and old Word files are reference material, not canonical facts.
