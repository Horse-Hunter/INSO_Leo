# Current Task — V1.2 Phase A final

Phase A FINAL: BLOCKED — the Owner-authenticated shell is present in the reused tab, but the lease child redirects to login; exact query is also unavailable because `#nolike` is hidden and unchecked.
V1.2 status: PRE_SAVE_READY / REAL_SAVE_GATED
Production write gate: CLOSED

Canonical browser baseline: Chrome (`browser.channel = "chrome"`). Edge is retained only as a backup and is not used for production acceptance.

## Code already accepted

- WorkBuddy duplicate reader `441b984db4703deeae66bda2878398a3f01b92de` was cherry-picked as `9c7e621`.
- The live duplicate adapter reads `#_id_dg` model/quantity/time cells 9/11/14 and verifies the detail `BillID` identity. It delegates all duplicate semantics to `evaluate_duplicate_history`.
- `PlaywrightDuplicateHistoryPage` now enforces exact current-MPN request matching (`nolike=on`), matching response, advanced `dg` sequence, idle state, enabled query button, and response/cache/DOM BillID agreement. Deterministic fake tests cover stale/malformed cases. Creator and quote selectors remain unset.
- `ResearchExcelFactsProvider` reads the persisted canonical Research workbook snapshot by inquiry identity; it does not re-search or recalculate Research rules.
- V1.2 adapter construction can bind the existing `QQSMTPTransport` to explicit sender config and recipients. This performs no SMTP operation. Production write gate remains closed.
- Existing exact quotation routing, purchaser allowlists, durable UNKNOWN-before-click Save path and UNKNOWN/manual reconciliation seam remain unchanged.
- `ParentProductFields` and coordinator-compatible `CoordinatorPurchaseDraftWriter.prepare()` exist. Prepare validates AI preview before touching parent fields, writes validated values, then validates parent read-back. Prepare exposes no Save or Send method and does not refer to `win_btn__dialog11`.
- No production parent-field adapter exists because live model/brand/quantity selectors have not been verified; the production purchase prepare cannot be composed without it.

## Chrome live read-only discovery — 2026-09-27

- The Owner-authenticated, dedicated Chrome CDP endpoint is reachable. It exposes one context and a reused browser; `InsoSessionLease` can create an operation-owned child page without closing the reused browser.
- The authenticated application shell has one verified INSO root page and exactly one `main` frame at `InnerEnquiry/YeWuXJ/List.aspx`. This explicit frame identity was used only for read-only discovery; no production adapter selects an arbitrary existing tab.
- The business-inquiry list has unique, visible `#DetailFieldValue`, `button#select_btns` (`查询`), `button#product_add_` (`新增`), and `#_id_dg`. The native `#nolike` exact-match checkbox is not actionable in this shell; no force or coordinate interaction was used.
- The scoped history-grid headers confirm `PartNo` (`型号`), `Qty` (`数量`), and `PEDate` (`时间`). `OfferPrice` is labelled `报价`, but its equivalence to the required INSO quote has not been proven. BillID is verified as the list-to-detail identity; no scoped `制单人` field or timestamp tie-break is confirmed.
- `新增` was statically verified to open the blank temporary-inquiry dialog only. The blank form was opened, inspected, and closed without filling or saving. Unique visible controls are `#CompanyName`, `#ImpValueF`, `#UserName_text`, `#ai_import_` (`AI录单`), `#btnSave` (`保存`), and `#btnSave2` (`保存并发送`). `#bcSend` exists with text `发送` and remains hard-forbidden.
- The blank form starts with no product rows. An existing read-only detail verifies parent product read-back cells, but no blank-form writer was exercised. The loaded `ai_import()` code has an in-memory callback; AI-panel controls and recognition read-back remain unverified after its runtime open failed safely.
- Existing detail inspection verifies BillID/PENO and the relevant read-only fields, but no post-Save BillID return/read-back is known. Reconciliation remains UNKNOWN/manual review.
- No Save Data, Save-and-Send, Send, SMTP, Sheets write, production migration, synthetic field input, AI recognition, or existing-record modification occurred.

## Phase A-2 targeted contract discovery — 2026-09-27

- **Settlement implementation is confirmed; live exact-mode execution is not.** The query contract binds the current MPN and `nolike=on` request to its response, advanced `dg` sequence, `_select_pending=false`, enabled `#select_btns`, and matching `table.cache.dg`/`#_id_dg` BillIDs. The adapter fails closed if any part is absent. Prior live discovery found `#nolike` not actionable and did not force it, so a live exact-mode query was not completed in this turn.
- **BillID identity is confirmed.** `Bill_View_Open(BillID, ...)` opens a read-only detail whose `#BillID` matches the linked BillID. The detail exposes PENO, customer, purchaser, importance, inquiry time, and one MPN/brand/quantity row. The row DOM id is separate and cannot replace BillID. Equal-timestamp ordering by BillID remains unproven.
- **Creator and INSO quote remain UNKNOWN.** `#UserName_text` is labelled purchaser and `#OwnerID_text` salesperson. `OfferPrice` is labelled `报价`, but its equivalence to the duplicate-notification INSO quote has not been proven.
- **Parent product read-back is confirmed for an existing read-only detail:** `#_id_dg td[data-field="PartNo"]`, `Brand`, and `Qty` are each unique and visible. A blank form starts without a row, so no parent-field writer is enabled.
- **AI panel/read-back remains UNKNOWN.** Static code is in-memory after the dialog returns, but opening the panel produced the form's generic submission-error dialog. It was cancelled immediately; there was no recognition, import, synthetic input, or retry.
- **Reconciliation at Phase A-2 was PARTIAL:** BillID identity and required existing-detail fields were verified; new-BillID acquisition had not yet been established. Phase A-3's static handler inspection is recorded below.

## Phase A-3 — 2026-09-27

- **Query adapter:** implemented strict settlement in `PlaywrightDuplicateHistoryPage`; deterministic tests cover exact request binding and response/cache/DOM BillID agreement. Live exact-mode query was not repeated because this execution context could not safely attach to the authenticated Chrome CDP endpoint; the previously observed hidden `#nolike` control is never force-clicked.
- **Creator:** UNKNOWN. The primary history schema does not establish a creator field. `#UserName_text` is purchaser and `#OwnerID_text` is salesperson, so neither is substituted.
- **INSO quote:** UNKNOWN. `OfferPrice` is labelled `报价` and paired with `OfferCurrencyID` (`报价币种`), but the response-to-detail mapping and currency/decimal semantics remain unconfirmed. Research's supplier-side `InPrice` is not used.
- **Timestamp tie-break:** AMBIGUOUS. BillID is stable identity, but no evidence ties its ordering to creation order; no tie-break was added.
- **AI panel and parent writer:** UNKNOWN. No AI panel action, recognition, blank-form product field write, or import was attempted in this turn. Existing-detail read-back selectors do not establish blank-form write selectors.
- **Save semantics/reconciliation:** static handler inspection identifies `#btnSave` → `bill_save_auto()` → `bill_save()`, separate from `bill_save_send()`/`#btnSave2` and `#bcSend`. Its success response returns BillID/PENO and routes to detail; no Save was clicked. The read-only reconciliation contract can verify the returned BillID and compare available detail fields. Actual post-save behavior still requires the authorized first Save gate.
- **Browser boundary:** this execution context could not safely inspect/attach to the Owner-authenticated Chrome process; no Edge or new profile was substituted, and no business page was interacted with.
- No Save, Send, real SMTP, or Sheets write occurred. Production Write Gate remains CLOSED.

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

## Phase A FINAL — 2026-09-27

- **Query settlement:** production implementation remains in the duplicate
  page adapter. The one-run inspector uses that adapter and records response
  schema keys/grid headers, never row values.
- **Creator / quote:** remain UNKNOWN until the Owner-session report closes the
  response-schema → grid → detail mapping. The inspector excludes `UserName`
  and `OwnerID` from creator. It checks quote decimal readability in memory and
  stores only a boolean. Research `InPrice` is never read.
- **AI and blank-draft writer:** remain UNKNOWN. The inspector opens a verified
  blank form and AI panel only when the loaded handler shows the known dialog
  route and no detected persistence call. It does not run recognition, import a
  row, or fill parent fields. It records visible input metadata and callback
  field-name evidence, never values.
- **Save/reconciliation:** controls and loaded handlers are inspected without
  clicking. `#btnSave2` and `#bcSend` remain hard-forbidden. Static Save response
  facts are not treated as proof of post-Save reconciliation.
- **Runner:** `src/launcher/v12_phase_a_readonly.py` is ready. The local ignored
  entry `runtime/run_v12_phase_a_readonly.cmd` is available for one double-click
  in the normal Owner Windows session. It requires configured Chrome, the
  original `.browser-profile/cdp`, and port 9222; it uses a one-context lease
  and operation-owned pages. A sanitized report will be written to
  `runtime/evidence/v12-phase-a-final/report.json`.
- No Save, Send, SMTP, Sheets write, or existing-record modification occurred.
  Production write gate remains CLOSED. The runner has since been executed;
  the remaining runtime findings are recorded below.

## Owner session follow-up — 2026-09-27

- The runner was executed after the Owner reported login complete. CDP was
  READY, with one context and a reused Chrome browser. It found exactly one
  existing page with the verified INSO shell and visible list controls, while
  the lease-created operation page's top-level URL redirected to `/login.aspx`.
  The report records `LEASE_CHILD_AUTH_NOT_SHARED`; this is an observed page
  boundary, not a claim about its underlying cause. The existing user tab was
  not closed or repurposed.
- A direct read-only attempt on that unique shell page filled the authorized
  public query MPN, then stopped before dispatch. `#nolike` was unique and
  enabled, but unchecked and invisible. Its unique associated `精确` label was
  also invisible, so `PlaywrightDuplicateHistoryPage` returned
  `QUERY_SETTLEMENT_UNCONFIRMED`. No force/coordinate click was used.
- The current loaded grid had no cached result row or header metadata, so this
  session produced no creator, quote, or detail-schema evidence. The AI panel
  and blank form were not opened on the reused user tab because that page is
  outside the current lease's operation-page lifecycle.
- Loaded list-handler inspection found functions that reference `List_Detail`,
  but did not establish a safe visible action that toggles `#nolike`; its
  associated `精确` label has zero visible bounds. The query adapter remains
  fail closed rather than invoking a hidden control or guessed JavaScript path.
- No Save, Send, SMTP, Sheets write, AI recognition, or existing-record
  modification occurred. Production write gate remains CLOSED.
