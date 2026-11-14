# Module Index — single ownership per responsibility

Only load the module relevant to the current RFQ. Existing code and tests are final technical contract; historical designs are [pinned](HISTORY.md), not automatic new plans.

| Area | Code | Responsibility | Current compact contract |
| --- | --- | --- | --- |
| Core | `src/core/` | credentials, original-MPN policy, shared browser-call budget | [Core](modules/CORE.md) |
| GUI | `src/gui/` | state/DTO presentation and manual action requests; no independent business writes | [GUI source](../src/gui/README.md) |
| Launcher | `src/launcher/` | production composition, original Windows/CDP ownership, API enablement, release entry | [CEO handover](../control-room/CEO_HANDOVER.md) |
| Sheets | `src/sheets/` | exact source schema, API/CDP adapters, single-cell writes and 14-cell quote input | [Sheets](modules/SHEETS.md) |
| Research | `src/research/` | six-source read-only price/stock research, evidence aggregation and output | [Research](modules/RESEARCH.md) |
| Workflow | `src/workflow/` | schedulers, 7-day/TP month admission, state/holds, purchasing & quotation orchestration, mail ledger | [Workflow](modules/WORKFLOW.md) |
| INSO | `src/inso/` | single authenticated session, duplicate history, controlled native purchase | [INSO](modules/INSO.md) |
| Quotation | `src/quotation/` | native quotation result interpretation (not another scheduler) | [Quotation](modules/QUOTATION.md) |
| Order mail | `src/order_mail/` | inbound mail parsing and sales-order structure; outbound ledger owned by Workflow | [current workflow](modules/WORKFLOW.md) |

**Dependencies:** Workflow composes Core + Sheets + Research + INSO + Quotation; Launcher composes the runtime; GUI only displays/requests actions. No new parallel adapter/browser/ledger/scheduler. Cross-module changes escalate to CEO; reuse prior stable public contracts first.

**Current V1.6 priority:** RFQ-016 single real API inquiry; latest reviewed source fix `24b73be7` is accepted only at source level. Production API current mode/Editor, business closure and old worker state remain unverified. [Active spec](../control-room/RFQ-016/TASK_SPEC.md) · [Actual checkpoint](../control-room/RFQ-016/EXECUTION_LOG.md).

Original historical module boundary design: [pinned Module Index](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/docs/MODULE_INDEX.md).
