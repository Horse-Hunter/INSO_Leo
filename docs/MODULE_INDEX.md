# Module Index

This is the sole registry for formal module, Module Chat, and Module Codex names. It defines ownership and dependency direction, not internal algorithms.

## Registry

| module_id | display_name | module_chat_role | module_codex_role | code_path | public contract / module doc |
| --- | --- | --- | --- | --- | --- |
| `core` | Core | Core Module Chat | Core Module Codex | `src/core/` | `docs/modules/CORE.md` |
| `sheets` | Sheets | Sheets Module Chat | Sheets Module Codex | `src/sheets/` | `docs/modules/SHEETS.md` |
| `research` | Research | Research Module Chat | Research Module Codex | `src/research/` | `docs/modules/RESEARCH.md` |
| `workflow` | Workflow | Workflow Module Chat | Workflow Module Codex | `src/workflow/` | `docs/modules/WORKFLOW.md` |
| `inso` | INSO | INSO Module Chat | INSO Module Codex | `src/inso/` | Future-version contract: `UNKNOWN` |
| `quotation` | Quotation | Quotation Module Chat | Quotation Module Codex | `src/quotation/` | Future-version contract: `UNKNOWN` |

Tests mirror ownership under `tests/<module>/`.

## Boundary map

| module_id | responsibility | allowed dependencies | forbidden dependencies |
| --- | --- | --- | --- |
| `core` | Shared primitives and infrastructure capabilities, including the Credential Provider boundary | standard library; approved general libraries | every business module; business rules |
| `sheets` | One-shot Google Sheets reads, pending-record queries, record identity, and explicitly commanded safe field updates | `core`; approved Google adapters | `research`, `workflow`, `inso`, `quotation`; polling/global state/business rules |
| `research` | Read-only market research, evidence, price aggregation, and Research-owned local Excel output | `core`; approved web/Excel adapters | `sheets`, `workflow`, `inso`, `quotation`; Google Sheet access |
| `workflow` | Scheduling, global process state, retry, duplicate prevention, and module handoffs | `core`, `sheets`, `research`, `inso`, `quotation` public contracts | module-internal business logic; direct external adapters |
| `inso` | INSO query, inquiry action, and result retrieval for a future version | `core`; future approved INSO adapters | `sheets`, `research`, `workflow`, `quotation` |
| `quotation` | Future quotation rules, generation, and result output | `core`; explicit input contracts | `sheets`, `research`, `workflow`, `inso`; direct external access |

```text
workflow -> core, sheets, research, inso, quotation
sheets | research | inso | quotation -> core
```

Cross-module calls use public contracts; private implementations are not imported. A registry, responsibility, contract, or dependency change has `architecture_impact: REQUIRED` under `AI_TEAM.md`.
