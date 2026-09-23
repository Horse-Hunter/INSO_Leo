# Task: SHEETS-002A Google Sheets Live Read Smoke

status: complete
owner: Codex
created: 2026-09-21
updated: 2026-09-21

## problem

SHEETS-002 proves the Google Sheets read adapter with fakes, but the authorized live read-only path has not yet been verified against the business spreadsheet.

## goal

Verify that the existing OAuth helper, GoogleSheetsRowReader, and query_pending_records work end to end against worksheet 2026 without performing or exposing any write or sensitive-data operation.

## current_facts

- HEAD includes SHEETS-001 commit ed3a9cbcadcb02c967152b728db5ebcbfe98fb10 and SHEETS-002 commit bda3835ce9c93d974ae006c33430cdc11e8e20e4.
- Owner explicitly authorizes Google Sheets API OAuth User Authorization and a minimal read-only smoke test.
- Worksheet title is 2026.
- Only the OAuth read-only scope and values.get read path are authorized.
- Credentials, tokens, secrets, and complete business rows must not be printed or committed.
- Other existing worktree changes are outside this task.
- A repo-external OAuth Desktop Client credential and the authorized spreadsheet identity were supplied at runtime and are intentionally not recorded here.

## scope

- Check or install the two minimum official Google Python client libraries in the development environment.
- Locate an existing OAuth Desktop Client credential without reading or exposing its secret material.
- Resolve the previously supplied business spreadsheet identity without recording it in the repository.
- Run the existing OAuth helper, row reader, and pending query once against worksheet 2026.
- Record only worksheet name, read success, row count, and pending count.

## non_scope

- Any Sheet write, update, append, clear, delete, create, formatting, or permission API.
- Adapter refactoring, Public Contract changes, token persistence, packaging design, or credential architecture.
- Workflow, Research, INSO, Quotation, SHEETS-003, or unrelated worktree changes.

## requirements

- Use only build_read_only_google_sheets_service, GoogleSheetsRowReader, and query_pending_records for the live path.
- Use only the Google Sheets read-only OAuth scope and values.get API.
- Do not print credentials, tokens, spreadsheet identity, or real row content.
- Stop if credentials or spreadsheet identity cannot be resolved, OAuth cannot complete, or the adapter contract is incompatible.
- Leave all pre-existing unrelated worktree files untouched.

## acceptance

- [x] Official Google client imports are available.
- [x] OAuth User Authorization completes with read-only scope.
- [x] The target spreadsheet and worksheet 2026 are readable.
- [x] The adapter produces WorksheetRow objects.
- [x] query_pending_records executes and produces a pending count.
- [x] Output contains no real row content or secret material.
- [x] No write API operation occurs.

## verification

- Check library imports without logging credential data.
- Inspect only credential presence and type, never credential contents.
- Run one minimal read-only smoke command and report only aggregate counts.
- Confirm repository diff remains limited to this Task Packet unless a narrow reader bug must be fixed.
- Confirm no write methods appear in the executed path.

## completion

- status: complete
- changed: prepared a repo-external OAuth Desktop Client environment; no business code was changed
- verified: Google Sheets API enabled; consent configured for External/Testing with only the spreadsheets.readonly scope; OAuth authorization passed; worksheet 2026 returned 174 rows; query_pending_records returned 3 pending records; no row content or secret material was recorded
- limitations: OAuth tokens remain non-persistent by design, so a later process may require interactive authorization again
