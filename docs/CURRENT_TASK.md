# Current Task — V1.2 final runtime acceptance

Phase A: PENDING — DIAGNOSTIC_EXECUTION_CONTEXT_MISMATCH
V1.2 status: PRE_SAVE_READY / REAL_SAVE_GATED
Production write gate: CLOSED

Canonical browser baseline: Chrome (`browser.channel = "chrome"`). Edge is retained only as a backup and is not used for production acceptance.

## Code already accepted

- WorkBuddy duplicate reader `441b984db4703deeae66bda2878398a3f01b92de` was cherry-picked as `9c7e621`.
- The live duplicate adapter reads `#_id_dg` model/quantity/time cells 9/11/14 and verifies the detail `BillID` identity. It delegates all duplicate semantics to `evaluate_duplicate_history`.
- Query settlement remains `QUERY_SETTLEMENT_UNCONFIRMED`; the live result therefore remains unavailable and cannot be treated as nonduplicate. Creator and INSO quote selectors default to `None`.
- `ResearchExcelFactsProvider` reads the persisted canonical Research workbook snapshot by inquiry identity; it does not re-search or recalculate Research rules.
- V1.2 adapter construction can bind the existing `QQSMTPTransport` to explicit sender config and recipients. This performs no SMTP operation. Production write gate remains closed.
- Existing exact quotation routing, purchaser allowlists, durable UNKNOWN-before-click Save path and UNKNOWN/manual reconciliation seam remain unchanged.
- `ParentProductFields` and coordinator-compatible `CoordinatorPurchaseDraftWriter.prepare()` exist. Prepare validates AI preview before touching parent fields, writes validated values, then validates parent read-back. Prepare exposes no Save or Send method and does not refer to `win_btn__dialog11`.
- No production parent-field adapter exists because live model/brand/quantity selectors have not been verified; the production purchase prepare cannot be composed without it.

## Earlier Edge runtime drift — 2026-09-26

- The earlier attempt mistakenly configured Edge despite both V1.1 and V1.2 canonical runtime selecting Chrome. That Edge profile is retained as a backup and is not used for this acceptance.
- Edge diagnostics below are historical only. They do not establish the current production browser baseline or Phase A readiness.

## Historical automated Edge/CDP diagnostic — 2026-09-26

- Read-only policy checks across HKLM/HKCU Edge policy keys, including WOW6432Node: `RemoteDebuggingAllowed=NOT_SET`; `UserDataDir=NOT_SET`. No registry values were changed.
- Before the controlled launch, 32 Edge processes were visible to CIM, none matched `runtime/browser-profile` or `--remote-debugging-port=9222`; port 9222 had no listener. No user Edge process was closed.
- Using the project `_launch` with the existing `runtime/browser-profile`, CIM observed a newly created Edge process whose actual command line contained the expected user-data-dir, `--remote-debugging-port=9222`, and `--remote-debugging-address=127.0.0.1`. The 9222 listener PID matched that process; no process reuse was observed.
- `/json/version` returned a non-empty websocket URL on consecutive checks; `/json/list` returned successfully (target count only was recorded). Playwright `connect_over_cdp` passed; browser was connected with one context. The existing `acquire_cdp_browser` path also returned `owned=True` and one context.
- Both diagnostic APP_OWNED Edge processes were closed through their own handles after verification. The persistent profile was retained. An isolated profile was not run because the current runtime profile passed; no INSO or business page was opened.
- The earlier `EDGE_CDP_ATTACH_FAILED` was not reproducible in the authorized Windows diagnostic execution. Its original trigger remains UNKNOWN; no persistent policy, command-line, profile, port ownership, or Playwright attach failure was found.
- Final Runtime Acceptance remains pending and was not run. Production write gate remains CLOSED; no Save, Send, SMTP, or Sheets write occurred.

## Chrome baseline parity investigation — 2026-09-26

- V1.1's completed integration task identifies the dedicated Chrome profile as the existing Git-ignored `.browser-profile/cdp`; that directory still exists with Chrome `Local State` and `Default` profile data. It was not copied, cleared, migrated, or recreated.
- The installed Chrome executable is `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`. The ignored `runtime/production.json` now points to that executable, the existing `.browser-profile/cdp`, and port 9222. `runtime/research.json` was not changed and still targets `http://127.0.0.1:9222`.
- Chrome RemoteDebuggingAllowed and UserDataDir policy values are NOT_SET in the checked HKLM/HKCU policy locations. No Chrome process was present before launch and no listener was present on 9222.
- The V1.1 packaged `--self-check` still passes, but it intentionally imports GUI dependencies only and never starts Chrome. Starting V1.1's exact `_launch()` code from the current diagnostic process used the same Chrome executable, original profile, port, remote-debugging address, startup-window flag, creation flags, startupinfo, and redirected standard handles as the historical V1.1 production boundary. It exited with `2147483651` before CDP became ready, exactly as the V1.2 diagnostic did.
- The decisive difference is the process token: this diagnostic runs as `LEO229\CodexSandboxOffline` at Medium integrity, while the original profile and accepted V1.1 smoke are owned by `LEO229\Leo`. The sandbox process cannot reproduce the Owner's packaged Windows execution context. The observed GPU child-process access denial is therefore classified as `DIAGNOSTIC_EXECUTION_CONTEXT_MISMATCH`, not a V1.2 Chrome product blocker and not evidence that the profile or INSO login expired.
- V1.1 and V1.2 use the same Chrome executable/profile/port. V1.1's configured readiness timeout is 45 seconds versus V1.2's 30 seconds; this does not explain a process that exits within seconds. No Chrome workaround flags, profile changes, or security-policy changes were made.
- No browser context, lease, operation page, or INSO page was established in this sandbox. INSO login remains UNKNOWN. Resume Phase A directly from the Owner's known-good packaged Windows runtime; do not ask for another login unless that runtime actually redirects the original Chrome profile to `/login.aspx`.
- No ordinary Chrome or Edge process was closed. The Edge backup profile remains untouched. No duplicate query, business-page inspection, Save, Send, SMTP, or Sheets write occurred.
- Remaining Phase A work after Chrome can expose CDP: lease/context identity, read-only INSO discovery, duplicate settlement/creator/quote, purchase selectors, Save control semantics, and saved-record reconciliation.

## Verification and side effects

- No Save Data, Save-and-Send, Send, SMTP, Sheets write, production migration, or production smoke occurred. No INSO page interaction occurred.
- `python -m ruff check src tests`: passed.
- `python -m pytest tests/launcher tests/inso tests/workflow -q --tb=short --basetemp runtime/pytest-chrome-baseline-20260926`: 252 passed, 1 skipped. Ruff and `git diff --check` passed.
- `git diff --check`: checked before delivery.
- V1.1 Research behavior and its canonical rules are unchanged.

CEO performs the daily Safety Review. Keep the production write gate CLOSED.
