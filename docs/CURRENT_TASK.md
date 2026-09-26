# Current Task — V1.2 final runtime acceptance

Phase A: BLOCKED — OWNER_LOGIN_REQUIRED
V1.2 status: PRE_SAVE_READY / REAL_SAVE_GATED
Production write gate: CLOSED

CDP diagnostic: EDGE_CDP_READY. Lease attachment passed; live discovery stopped at the login boundary.

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
- At the time of the original attempt, the blocker was Playwright CDP attachment. The controlled diagnostic below now passes. Still-required acceptance is: Owner login if needed; parent field selectors and synthetic read-back plus prepare dry-run; duplicate settlement/creator/quote; live Save-control semantics; and read-only saved-record identity/reconciliation.
- No production adapter was enabled or substituted with a fake. Production write gate remains CLOSED.

## Automated Edge/CDP diagnostic — 2026-09-26

- Read-only policy checks across HKLM/HKCU Edge policy keys, including WOW6432Node: `RemoteDebuggingAllowed=NOT_SET`; `UserDataDir=NOT_SET`. No registry values were changed.
- Before the controlled launch, 32 Edge processes were visible to CIM, none matched `runtime/browser-profile` or `--remote-debugging-port=9222`; port 9222 had no listener. No user Edge process was closed.
- Using the project `_launch` with the existing `runtime/browser-profile`, CIM observed a newly created Edge process whose actual command line contained the expected user-data-dir, `--remote-debugging-port=9222`, and `--remote-debugging-address=127.0.0.1`. The 9222 listener PID matched that process; no process reuse was observed.
- `/json/version` returned a non-empty websocket URL on consecutive checks; `/json/list` returned successfully (target count only was recorded). Playwright `connect_over_cdp` passed; browser was connected with one context. The existing `acquire_cdp_browser` path also returned `owned=True` and one context.
- Both diagnostic APP_OWNED Edge processes were closed through their own handles after verification. The persistent profile was retained. An isolated profile was not run because the current runtime profile passed; no INSO or business page was opened.
- The earlier `EDGE_CDP_ATTACH_FAILED` was not reproducible in the authorized Windows diagnostic execution. Its original trigger remains UNKNOWN; no persistent policy, command-line, profile, port ownership, or Playwright attach failure was found.
- Final Runtime Acceptance remains pending and was not run. Production write gate remains CLOSED; no Save, Send, SMTP, or Sheets write occurred.

## Final Runtime Acceptance Phase A — 2026-09-26

- Reused the configured CDP endpoint and project lease path. `acquire_cdp_browser` launched an APP_OWNED Edge; the browser was connected with exactly one context, and a lease-created operation page had a verified identity.
- Navigating that operation page to the known read-only history-list route redirected to `yingsuo.alperp.cn/login.aspx`; one password input was present. Result: `OWNER_LOGIN_REQUIRED`. No credentials, OTP, or challenge were entered or bypassed. The dedicated Edge/profile was left open at the login page.
- No authenticated INSO business page was reached. Duplicate settlement/creator/quote, parent product selectors, purchase/AI controls, Save controls, and saved-record reconciliation were not inspected and remain UNKNOWN.
- No business-page click, query, form input, AI action, Save, Send, SMTP, or Sheets write occurred. Production write gate remains CLOSED.

## Verification and side effects

- No Save Data, Save-and-Send, Send, SMTP, Sheets write, production migration, or production smoke occurred. No INSO page interaction occurred.
- `python -m ruff check src tests`: passed.
- `python -m pytest tests/inso tests/workflow tests/launcher -q --tb=short --basetemp runtime/pytest-v12-acceptance-20260926`: 246 passed, 1 skipped. The default Windows pytest temp path was inaccessible; rerunning under a unique ignored workspace temp directory passed.
- `git diff --check`: checked before delivery.
- V1.1 Research behavior and its canonical rules are unchanged.

CEO performs the daily Safety Review. Keep the production write gate CLOSED.
