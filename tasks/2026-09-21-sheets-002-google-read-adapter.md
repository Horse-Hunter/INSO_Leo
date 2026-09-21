# Task: SHEETS-002 Google Sheets API Read Adapter

status: complete
owner: Codex
created: 2026-09-21
updated: 2026-09-21

## problem

SHEETS-001 provides a pure pending-record query and reader boundary, but no adapter currently converts a real Google Sheets API values response into WorksheetRow objects.

## goal

Add a Sheets-owned, strictly read-only Google Sheets API adapter that feeds the existing WorksheetRowReader contract and query_pending_records behavior.

## current_facts

- HEAD contains SHEETS-001 commit ed3a9cbcadcb02c967152b728db5ebcbfe98fb10.
- The SHEETS-001 files are unchanged at task start.
- Google Sheets API with OAuth User Authorization is the preferred V1 integration.
- Owner authorizes a minimal live read-only smoke test against worksheet 2026.
- Pending remains exact A == "未发" and is owned by query_pending_records, not the adapter.
- Spreadsheet configuration, OAuth token persistence, and credential locations remain UNKNOWN.
- Other pre-existing worktree changes are outside this task and must remain untouched.

## scope

- Add a GoogleSheetsRowReader compatible with the existing WorksheetRowReader protocol.
- Read A:G using the Google Sheets values read endpoint and convert rows to WorksheetRow.
- Preserve physical row positions, including when reading from a non-first row.
- Fill missing trailing cells with None without shifting columns.
- Surface API/auth/response failures as a Sheets-owned read exception.
- Add a minimal interactive OAuth User Authorization helper using the read-only scope and no token persistence.
- Add network-free fake-client unit tests.
- Run a minimal live read-only smoke test only if required libraries, OAuth client credentials, and spreadsheet identity are available.

## non_scope

- Any Google Sheet write, update, append, clear, delete, creation, formatting, or permission operation.
- Pending-rule reimplementation, normalization, alternate pending statuses, or business conversion.
- Brand write, relocation, conflict handling, targeted updates, stable IDs, scheduling, polling, retry, duplicate prevention, or global state.
- Workflow, Research, INSO, Quotation, Core refactoring, or a general credential architecture.
- Packaging-system design or persistent OAuth token storage.

## requirements

- The adapter calls only the values read endpoint and requests A:G.
- API rows map by column position and retain the actual Google Sheet row number.
- Empty successful responses return an empty collection.
- Read/auth/malformed-response failures must not masquerade as an empty result.
- Unit tests never access the network.
- OAuth uses only the Google Sheets read-only scope, hardcodes no account or secret, stores no token, and prints no credential.
- No existing SHEETS-001 file is modified.

## acceptance

- [x] Multiple API rows convert correctly.
- [x] Physical row positions are correct for a non-first starting row.
- [x] Short rows and missing trailing cells do not shift columns.
- [x] Empty worksheet/range returns an empty collection.
- [x] Existing query_pending_records reads A/C/E/F/G from adapter rows.
- [x] Adapter returns non-pending rows and does not own pending filtering.
- [x] API failures raise a Sheets-owned read exception.
- [x] No Sheet write API behavior exists.
- [x] Mock tests pass without network access.
- [x] Live read-only smoke test passes or its exact environment blocker is recorded.

## verification

- Run scoped Sheets tests when pytest is available; otherwise run the pure test functions directly under Python 3.12 and record the limitation.
- Run ruff on changed Python files when available and record any limitation.
- Inspect the full scoped diff and run scoped whitespace checks.
- Scan adapter code for write methods, forbidden module imports, credentials, and secret material.
- Confirm SHEETS-001 files and unrelated worktree files remain unchanged.
- For live smoke, report only worksheet name, row count, pending count, and success state.

## completion

- status: complete
- changed: added a read-only Google Sheets values adapter, physical row-position mapping, short-row handling, Sheets-owned read errors, a non-persistent read-only OAuth helper, and six mock unit tests
- verified: Python 3.12 scoped pytest passed 11 tests; scoped ruff passed; source review found only values.get/execute API behavior, the read-only OAuth scope, no write methods, and no forbidden module imports; SHEETS-001 files remained unchanged
- limitations: live smoke test blocked because no OAuth client credential, spreadsheet ID/configuration, or official Google client libraries were available; OAuth token persistence remains UNKNOWN and unimplemented
