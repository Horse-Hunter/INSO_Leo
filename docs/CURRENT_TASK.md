# Current Task — V1.2 final runtime acceptance

Status: BLOCKED — EDGE_CDP_ATTACH_FAILED
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

- Edge Stable was found at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` (version `153.0.4234.48`). The persistent dedicated profile `runtime/browser-profile` and ignored `runtime/production.json` were created; `runtime/research.json` points to `http://127.0.0.1:9222`.
- `acquire_cdp_browser` launched an APP_OWNED Edge process. The TCP-only readiness path returned before Playwright could attach (`ECONNREFUSED`). A stricter `/json/version` readiness attempt timed out with the default launcher. A diagnostic launch with the startup-window flag omitted exposed `/json/version`, but `attach_inso_research_session` still failed with a connection reset. No lease or operation page was established.
- The app-owned launches were closed through their browser handles. The dedicated profile remains on disk for reuse; no process using that profile or CDP port remained after cleanup. Existing user Edge processes were left untouched.
- No INSO page was opened, and no login state was inspected. Synthetic parent fields, complete purchase prepare, duplicate query/settlement/creator/quote, Save controls and existing-record reconciliation were not live-verified.
- The current blocker is stable Playwright CDP attachment to the project Edge profile. After attachment is working, still-required acceptance is: Owner login if needed; parent field selectors and synthetic read-back plus prepare dry-run; duplicate settlement/creator/quote; live Save-control semantics; and read-only saved-record identity/reconciliation.
- No production adapter was enabled or substituted with a fake. Production write gate remains CLOSED.

## Verification and side effects

- No Save Data, Save-and-Send, Send, SMTP, Sheets write, production migration, or production smoke occurred. No INSO page interaction occurred.
- `python -m ruff check src tests`: passed.
- `python -m pytest tests/inso tests/workflow tests/launcher -q --tb=short --basetemp runtime/pytest-v12-acceptance-20260926`: 246 passed, 1 skipped. The default Windows pytest temp path was inaccessible; rerunning under a unique ignored workspace temp directory passed.
- `git diff --check`: checked before delivery.
- V1.1 Research behavior and its canonical rules are unchanged.

CEO performs the daily Safety Review. Keep the production write gate CLOSED.
