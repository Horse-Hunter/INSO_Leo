# RFQ-016 Phase 1 — release readiness and verification status (2026-11-13, offline only)

**Status:** `SOURCE_PHASE_COMPLETE_CANDIDATE`, `PRODUCTION_HEALTH_HOLD`,
`DEFAULT_OFF_SWITCH_VERIFIED_OFFLINE`, `LIVE_SA_READ_VERIFIED_ON_SYNTHETIC_SHEET`,
`LIVE_API_WRITE_NOT_VERIFIED`, `CDP_SCRIPT_HANDOFF_NOT_VERIFIED`,
`FROZEN_RUNTIME_IMPORT_NOT_VERIFIED`.
Nothing in this document authorizes a production action. Every item marked
`WAITING_OWNER_AUTHORIZATION` needs a new explicit Owner decision.

## 1. What is verified, and how

| Area | Level | Evidence |
| --- | --- | --- |
| Google API read/write *code paths* (types, blanks, identity, W proof, whitelists, receipts, unknown writes) | `OFFLINE_VERIFIED` | `tests/sheets/test_google_api_service.py`, `tests/workflow/test_rfq016_api_chain.py` |
| Quotation handoff (API write → page reload → single click) | `OFFLINE_VERIFIED` | `tests/workflow/test_quote_api_handoff.py`, `tests/launcher/test_google_quote_update.py` |
| Durable hold, manual retry gate, restart/status-change survival | `OFFLINE_VERIFIED` | `tests/workflow/test_rfq006_integration.py`, `tests/launcher/test_rfq008_hold_lifecycle.py` |
| Failure classification (429/5xx defer, 4xx accurate, unknown write fails closed) | `OFFLINE_VERIFIED` | `tests/launcher/test_google_api_migration.py`, `tests/sheets/test_quotation_input.py` |
| Service-account credential (JWT exchange, no refresh token, DPAPI copy) | `OFFLINE_VERIFIED` + one real read | `tests/sheets/test_service_account_auth.py`, feasibility §22 |
| Real read of the synthetic spreadsheet | `VERIFIED` on 2026-11-13 (Viewer only) | feasibility §22 |
| Real API **write** to the synthetic sheet | `WAITING_OWNER_AUTHORIZATION` | SA is Viewer; no write was attempted |
| Real Chrome reload/script-menu readiness with the API transport | `WAITING_OWNER_AUTHORIZATION` | needs the protected CDP session |
| Import inside the frozen EXE runtime | `NOT_VERIFIED` | archive inventory only (see §2.3) |
| Eight-day unattended run | `NOT_VERIFIED` | probe plan in feasibility §15 |

## 2. C1 — final assembly audit (read-only)

### 2.1 One default-off switch
`production.json` has no `google_api` key today. `ProductionBackend._sheet_service_for`
returns the CDP transport unless `google_api.enabled` is exactly `true`
(`backend.py`), and `_google_api_service` then requires
`google_api.service_account_file`. Enabling it without a readable key raises
`ProductionConfigurationError` (no path) or `V12Fault(GLOBAL_STOP,
SHEETS_AUTH_UNAVAILABLE)` (unreadable/incomplete key) **before any business runs**.
Tests: `tests/launcher/test_google_api_migration.py` (off by default, missing path,
missing key, enabled build). No second switch, no per-module overrides.

### 2.2 Credential handling
The key file lives outside the repository; plain JSON or the existing
CurrentUser DPAPI copy of it is accepted (`load_service_account_info`), the
private key stays in memory, nothing is written back to disk, and no token cache
is created (a service account has no refresh token). On Windows the file has a
single-user ACL. Tests: `test_key_file_is_read_from_plain_json`,
`test_key_file_is_read_from_a_dpapi_protected_copy`,
`test_incomplete_or_unreadable_key_is_rejected`.

### 2.3 Frozen-build dependencies (evidence, not a guess)
`docs/evidence/v16/frozen-archive-2026-11-13.json` (PyInstaller CArchive/PYZ
inspection of the installed EXE, sha256 `00ac7d68…f30bd`) already lists every
module the API transport imports: `google.oauth2` (16), `google.oauth2.service_account`
(1), `googleapiclient` (16), `google.api_core` (8), `google_auth_httplib2` (1),
`httplib2` (6), `requests` (18), `urllib3` (36), `cryptography` (54),
`uritemplate` (5). `packaging/INSO_V1.1.spec` collects `collect_submodules("src")`,
so `src/sheets/google_api_service.py` is included automatically. **No spec change
is required and none was made.** A real import inside the frozen process remains
`NOT_VERIFIED` because running the installed EXE starts the business.

### 2.4 Browser, scheduler, duplication
The API transport owns no browser, no page, no profile and no thread: it exposes
only the service shape plus inert lifecycle ports, and the quotation button still
uses the single protected CDP handle (`_page_service()` keeps
`operations_idle`/`suspend_idle_poll` on the CDP transport). No second Chrome
profile, debug port, scheduler, ledger or mail path was added; `git diff` for this
phase touches only the files listed in `EXECUTION_LOG.md`.

## 3. C2 — controlled first-run plan (preparation only, nothing executed)

Order matters; each step is independently reversible.

1. **Backup (Owner, before anything).** With INSO closed: copy
   `runtime/production/workflow.sqlite3` (+ `-wal`/`-shm`) and
   `runtime/production.json` to a dated folder; export the current
   `dist/INSO_V1.6` directory or note its hash. Do **not** delete the old build.
2. **Keep the switch off.** Confirm `production.json` still has no `google_api`
   key; the old CDP path must remain the default until step 5 passes.
3. **Read-only parity check (needs authorization: read the real sheet with the SA).**
   Share the *real* workbook read-only with the test SA only if the Owner accepts
   it, then compare, per column and per row, what the API returns with what the
   current CDP run displays (model including leading zeros, brand, quantity,
   status, dates, `W` quote_date, blank cells). Any difference stops the rollout.
   **WAITING_OWNER_AUTHORIZATION** — never write during this step.
4. **Synthetic write check (needs authorization: make the synthetic sheet writable
   for the SA).** Recreate the 3×4 synthetic sheet with a real Row 1/2 header
   layout, grant the SA Editor *on that test sheet only*, then write one raw14 row
   and one single cell through `GoogleApiSheetsService`, verifying the receipt and
   reading back with the API. **WAITING_OWNER_AUTHORIZATION** — this is the only
   remaining unverified transport behaviour besides the browser.
5. **Button handoff check (needs authorization: the protected CDP session).**
   With the API transport enabled for one controlled cycle, confirm: the page
   reload happens after the write, the script menu is ready, exactly one click is
   dispatched, the popup is read, and the source status settles to `采购已报价`.
   **WAITING_OWNER_AUTHORIZATION** — requires the real Chrome and a real order.
6. **Enable for real business only after 3–5 pass**, by adding
   `"google_api": {"enabled": true, "service_account_file": "<repo-external path>"}`
   to `production.json`, then restarting the program **once**, then observing one
   full module cycle in the GUI.

**Stop immediately if:** the API returns a different value than the CDP display for
any identity/status/date column; any `SOURCE_CHANGED` appears that the old path did
not produce; a write returns no receipt; the button produces no popup or an unknown
popup; the hold list shows an `UNKNOWN`-marked row that nobody has reviewed; the GUI
reports `需要人工处理` twice for the same cause.

**Rollback (no data loss):** remove `google_api` from `production.json` (or set
`enabled: false`) and restart once — the CDP transport is the fallback and needs no
migration. Restoring the backup is only for a database-level problem; never clear
holds, `UNKNOWN`/`SENT` records or credentials to "fix" a failed switchover.

## 4. C3 — production stop register (read-only evidence)

| Time (2026-11-13) | Reason | Class | Phase-1 effect |
| --- | --- | --- | --- |
| 03:32 | `QUOTE_INPUT_WRITE_FAILED`, `QUOTE_AGE_EXPIRED` in the quotation stage | mixed: quote-input write on CDP + business age gate | write-uncertainty path now fails closed with a durable hold; age gate untouched (not Google) |
| 18:33–18:48 | `google-read-fragment-drift` ×153, `google-write-fragment-drift` ×178, `google-download-read` timeouts ×92, `google-open-sheet` native timeouts ×14, then `CDP_PAGE_CLEANUP_UNCONFIRMED` | **CDP page/download mechanics** | removed for reads and writes by the API transport; the read/write drift family cannot occur |
| 21:44–21:46 | `CDP_PAGE_CLEANUP_UNCONFIRMED` with `elapsed_s=0.000` (no cycle could start) | **CDP page ownership/cleanup** | **not** removed: the quote button still owns a page; Phase 2 |
| 21:50:59 / 21:52:45 | `SHEETS_SCHEMA_UNAVAILABLE` from `google-download-read` | **CDP download identity proof** (wrong/stale/truncated body or a changed header — cause still `NOT_VERIFIED`) | the API path cannot select the wrong sheet, but it deliberately re-implements the same header proof, so a genuinely changed header still stops |
| — | INSO login/session, SMTP, scheduler behaviour | non-Google | untouched; Phase 2 |

No stop in this table is claimed as "fixed"; each entry states only which mechanism
the API migration removes and which remains.

## 5. Release blockers

1. Real API write on the synthetic sheet `WAITING_OWNER_AUTHORIZATION`.
2. Real reload/button handoff on the protected CDP session `WAITING_OWNER_AUTHORIZATION`.
3. Frozen-runtime import of the API client `NOT_VERIFIED` (needs an isolated build test).
4. `CDP_PAGE_CLEANUP_UNCONFIRMED` and the INSO session failures are Phase 2.
5. An unreviewed `effect_uncertain` hold has **no** self-service release action:
   silence is not resolution. A human must verify the sheet, and a reviewed
   settlement path is still to be designed with the Owner.

---

## 6. Phase 2 results (2026-11-14)

| Gate from §5 | Status | Evidence |
| --- | --- | --- |
| 1. Real API write on the synthetic sheet | **`VERIFIED`** | Editor on the synthetic document only → real `values.update` (single cell + raw14), real `UpdateValuesResponse`, readback identical, leading zeros preserved, date cell returns text; Viewer restored and a later write answers `HttpError 403`. `docs/evidence/v16/rfq016-phase2-live-write-2026-11-14.json` |
| 2. Reload/button handoff on the protected CDP session | **`PARTIAL`** | API write → browser reload → the page displays the written value (`VERIFIED`, synthetic document). The container-bound `更新报价` button, its script menu and popup remain **`NOT_VERIFIED`**: that script exists only in the production document. |
| 3. Frozen-runtime import of the API client | **`VERIFIED`** | `INSO_V1.6.exe --api-self-check` → `TRANSPORT_READY` on the freshly built artifact; a missing key → `AUTHORIZATION_REJECTED`, never a crash. `docs/evidence/v16/rfq016-phase2-candidate-build-2026-11-14.json` |
| 4. `CDP_PAGE_CLEANUP_UNCONFIRMED` | **reduced, not eliminated** | A `Target.closeTarget` answer of `success:false` is now proved against `Target.getTargetInfo`: a target Chrome already removed is cleanup-complete instead of a poisoned admission. A real leak still stops the run and still needs a program restart. |
| 5. No self-service release for an unreviewed `effect_uncertain` hold | **open** | Manual replay and overwrite are refused (phase 1); an owner-reviewed settlement path is still undesigned. |

### 6.1 Replacement decision: **not replaced**

Owner allowed replacing the program files once six conditions hold. Five do.
Condition 5 — "production API permission and configuration explicitly authorized
and sufficient for the business" — does **not** hold: the service account has no
access to the production spreadsheet (metadata read answers `HttpError 404`), and
granting it would mean changing production sharing, which is a separate Owner
decision. Shipping the new program with the API switched off would run exactly
today's CDP path, and the production stops of 2026-11-13 (18:33 drift family,
21:50 header proof) live on that path. Replacing the binary would therefore not
fix the reason the Owner asked for a new version, while still touching the
installed program. The candidate is delivered verified instead.

### 6.2 Shortest path to a working production version

1. **Owner:** confirm the production document may be shared with
   `rfq016-sheets-test@inso-509314.iam.gserviceaccount.com` as **Editor**
   (write access is required for `报价输入` and the single-cell status columns).
   If production must not be writable by a service account, say so and the API
   path is dropped in favour of the CDP path only.
2. **Executor:** copy the candidate over `dist/INSO_V1.6` program files only
   (`INSO_V1.6.exe` + `_internal`), leaving `runtime/production.json`, the SQLite
   database, `research.json`, the credentials and the Chrome profile untouched;
   record both hashes.
3. **Executor:** add `"google_api": {"enabled": true, "service_account_file":
   "<repository-external key>"}` to the production configuration, plus the
   production worksheet identifiers, and run `--api-self-check` → expect
   `TRANSPORT_READY`.
4. **Owner + Executor:** one controlled single order — pre-flight identity,
   no UNKNOWN/SENT/hold, source status confirmed; purchase, sheet write and the
   quote button each explicitly authorized for that one order.
5. Compare Google, INSO, SQLite, quote result and notification for that order;
   only then consider ordinary operation.

Rollback at any step: restore the previous `INSO_V1.6.exe`/`_internal` from the
recorded backup and remove the `google_api` key; the database, credentials and
profile are never part of the rollback because they are never modified.

---

## 7. Production read parity (2026-11-14) and the write-test request

### 7.1 What was verified

The service account now holds **Viewer** on the production workbook `INSO_QUOTE`
(id `12bRXb…fwboO9k`), granted through the normal share dialog and proven by API
(read succeeds, an editor-only call answers `HttpError 403`). Reading with the real
`GoogleSheetsRowReader` / `transport.read_brief` / `GoogleQuotationInput`:

| Worksheet | Result |
| --- | --- |
| `SHAHAB` | **compatible** — header on row 2 `DATE/STATUS/Item/Part Number/Brand/QTY/UM`, 140 rows, model text, quantity numeric, blanks `None` |
| `RFQ_BRIEF` | **compatible** — 100 rows, every row 17 cells, every cell a string |
| `报价输入` | **compatible** — gid `489913321` matches `production.json`, `A1:N1` reads as 14 strings |
| `2026` | **blocked: the header moved** (below) |

### 7.2 `2026` — the real cause of the production stops

```
row 1  Model | … | Brand | … | MPN | MFR | Qty | … | quote_date      <- W1
row 2  (model, qty)
row 3  (model, qty)
row 4  (model, qty)
row 5  STATUS | … | CLASS | … | MPN | MFR | Qty          <- the contract header
row 6+ …
```

221 rows; 73 of them carry the literal `STATUS` in column A; column `W` has
`quote_date` at row 1 and dates only at rows 101–221 (69 cells). Both transports
require the contract header on row 1 (`GoogleSheetsWebService._headers` and
`google_api_service._require_source_header`), and both raise
`V12Fault(GLOBAL_STOP, SHEETS_SCHEMA_UNAVAILABLE)`. That is exactly what the
production log shows at **21:50:59 and 21:52:45** — the download was not corrupt;
the table header was moved down by a block that appeared above it.

Nothing was relaxed to make it pass, because a header-row change also moves the
`W = quote_date` proof (its header is still on row 1, its dates belong to the rows
from 101 down) and that would silently mis-age orders.

**Owner decision required (one question):** is the `Model/Brand` block in rows 1–4
accidental, so the contract header belongs back on row 1 (recommended, no code
change), or is row 5 from now on the authoritative header (then a header-row
contract plus an explicit `quote_date` alignment has to be designed and reviewed
before any order runs)?

### 7.3 The write test, ready to request

Preconditions that are already met: candidate built and gated, CDP protocol fixed,
`SHAHAB`/`RFQ_BRIEF`/`报价输入` reading correctly, Backup/rollback documented in §6.2.

| Item | Plan |
| --- | --- |
| Document needing Editor | `INSO_QUOTE` only. **Editor is whole-file**, including the container-bound Apps Script, so this must be an explicit Owner decision for the test window and revoked afterwards. |
| Candidate rows | `SHAHAB` 140 (`MAIL-RFQ-658`, referenced by `RFQ_BRIEF`), `2026` 217 / 219 (`MAIL-RFQ-658`, `MANUAL-RFQ-A`) — all chosen because `RFQ_BRIEF` already binds them, so identity is independent of my reading. |
| Writes | Brand single cell (`'SHAHAB'!E{row}` / `'2026'!F{row}`), purchase status (`'SHAHAB'!B{row}` / `'2026'!A{row}`), quotation input `'报价输入'!A1:N1` (14 RAW cells). Nothing else, no new rows, no formatting. |
| Real effects | Cell writes alone trigger nothing. The `更新报价` button runs the sheet's own script and produces a real quote; purchase submission and mail happen only if the whole cycle runs for that order. |
| Confirmation | Pre-write snapshot of exactly those cells (read via the Viewer role), post-write `updatedRange`/`updatedCells` + read-back, byte comparison for the 14-cell row, and a diff proving no other cell changed. |
| Restore | Original values written back from the snapshot if any step is ambiguous; the durable hold mechanism protects an uncertain write; a mismatch stops the run before the button. |
| Stop conditions | Any receipt mismatch, any 5xx, an unexpected popup, or any unplanned cell changed. |

Two authorisations are therefore outstanding: (a) the `2026` layout decision above,
(b) an Editor grant on `INSO_QUOTE` for one named row, with the quote button and any
purchase/mail action confirmed separately per action.
