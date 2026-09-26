# Current Task — V1.2 final runtime acceptance

Status: BLOCKED — LOCAL_CDP_UNREACHABLE
Production write gate: CLOSED

## Code already accepted

- WorkBuddy duplicate reader `441b984db4703deeae66bda2878398a3f01b92de` was cherry-picked as `9c7e621`.
- The live duplicate adapter reads `#_id_dg` model/quantity/time cells 9/11/14 and verifies the detail `BillID` identity. It delegates all duplicate semantics to `evaluate_duplicate_history`.
- Query settlement remains `QUERY_SETTLEMENT_UNCONFIRMED`; the live result therefore remains unavailable and cannot be treated as nonduplicate. Creator and INSO quote selectors default to `None`.
- `ResearchExcelFactsProvider` reads the persisted canonical Research workbook snapshot by inquiry identity; it does not re-search or recalculate Research rules.
- V1.2 adapter construction can bind the existing `QQSMTPTransport` to explicit sender config and recipients. This performs no SMTP operation. Production write gate remains closed.
- Existing exact quotation routing, purchaser allowlists, durable UNKNOWN-before-click Save path and UNKNOWN/manual reconciliation seam remain unchanged.
- `ParentProductFields` and coordinator-compatible `CoordinatorPurchaseDraftWriter.prepare()` exist. Prepare validates AI preview before touching parent fields, writes validated values, then validates parent read-back. Prepare exposes no Save or Send method and does not refer to `win_btn__dialog11`.
- No production parent-field adapter exists because live model/brand/quantity selectors have not been verified; the production purchase prepare cannot be composed without it.

## Runtime acceptance attempt — 2026-09-26

- `runtime/research.json` was absent. A valid non-secret file was created using the current `ResearchRuntimeConfig` schema and the existing loopback endpoint `http://127.0.0.1:9222`; it is Git-ignored. The checked-in `tests/v1_integration/write_runtime_config.py` helper is stale and fails because it passes removed INSO config fields.
- The configured local CDP endpoint did not accept a connection. No browser was started and `attach_inso_research_session` was not called. Browser/context/lease/operation-page identity and reused-browser lifecycle were not accepted. No arbitrary tab or context was selected.
- With no reachable authenticated session, no INSO page was opened or interacted with. Synthetic parent fields, complete purchase prepare, duplicate query/settlement/creator/quote, Save controls and existing-record reconciliation were not live-verified.
- Specific remaining blockers before first Save authorization: a reachable intended local CDP session; verified parent model/brand/quantity fields and prepare dry-run; verified duplicate query settlement plus creator and INSO quote fields; live Save-control semantics; and a usable read-only saved-record reconciliation identity.
- No production adapter was enabled or substituted with a fake. Production write gate remains CLOSED.

## Verification and side effects

- No Save Data, Save-and-Send, Send, SMTP, Sheets write, production migration, or production smoke occurred. No INSO page interaction occurred.
- `python -m ruff check src tests`: passed.
- `python -m pytest tests/inso tests/workflow tests/launcher -q --tb=short --basetemp runtime/pytest-v12-acceptance-20260926`: 246 passed, 1 skipped. The default Windows pytest temp path was inaccessible; rerunning under a unique ignored workspace temp directory passed.
- `git diff --check`: checked before delivery.
- V1.1 Research behavior and its canonical rules are unchanged.

CEO performs the daily Safety Review. Keep the production write gate CLOSED.
