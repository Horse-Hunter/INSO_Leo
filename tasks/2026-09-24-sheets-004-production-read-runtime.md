# Task: SHEETS-004 Production Read Runtime Prerequisite

status: complete
owner: Sheets Module Codex
created: 2026-09-24
updated: 2026-09-24

## problem

The Sheets read adapter and non-persistent read-only OAuth helper exist, but there is no fail-closed runtime composition for supplying the OAuth client-secret path, production spreadsheet identity, and complete target worksheet list from local non-repository configuration. Workflow V1 live smoke therefore cannot construct the existing reader from an explicit production runtime input.

## goal

Provide the smallest Sheets-owned, one-shot, read-only production runtime prerequisite so a caller can load explicit local configuration, construct the existing GoogleSheetsRowReader, enumerate every configured worksheet, and read each worksheet without adding polling or Workflow state.

## current_facts

- The canonical Sheets public domain contract already contains WorksheetIdentity and WorksheetRowReader.
- build_read_only_google_sheets_service requests only the spreadsheets.readonly scope and does not persist tokens.
- GoogleSheetsRowReader performs values.get reads over A:G.
- Official Google API dependencies were previously installed and a live read of worksheet 2026 was previously validated.
- docs/BOUNDARIES.md does not exist; docs/MODULE_INDEX.md and docs/modules/SHEETS.md define the applicable module boundary.
- No production runtime config mechanism, config-path environment variable, spreadsheet identity input, or worksheet-list input exists at task start.
- The task delegation explicitly authorizes a real read-only Google Sheet smoke, but prohibits writes and sensitive values in Git, tasks, logs, and reports.
- The current process does not have INSO_SHEETS_READ_CONFIG_FILE, so no production identity is available to the runtime and a live smoke cannot start in this task.

## scope

- Add a Sheets-owned local JSON config loader selected by one explicit environment variable or explicit file argument.
- Validate the OAuth client-secret file path, production spreadsheet identity, and complete non-empty, duplicate-free target worksheet list.
- Compose the existing read-only OAuth helper and GoogleSheetsRowReader.
- Provide one-shot enumeration/read behavior for all configured worksheets.
- Add network-free tests for valid composition and fail-closed configuration.
- Run a real read-only smoke only when local configuration is present and OAuth can be completed by the Owner.

## non_scope

- Polling, scheduling, retries, Workflow state, duplicate prevention, or inquiry lifecycle behavior.
- Any Google Sheet write, Brand update, permission change, Drive scope, token persistence, or secret persistence.
- Changes to cross-module public domain contracts or module dependency direction.
- Workflow backlog implementation or follow-on business tasks.

## requirements

- Configuration comes only from an explicitly supplied local JSON file; there is no production identity or credential default.
- The default loader entrypoint requires INSO_SHEETS_READ_CONFIG_FILE.
- The JSON contains oauth_client_secret_file, spreadsheet_id, and worksheets; unknown keys and malformed or blank values fail closed.
- Relative OAuth paths resolve relative to the config file, and the referenced file must already exist as a regular file.
- Worksheet order is preserved and duplicates are rejected.
- Runtime composition uses only build_read_only_google_sheets_service and GoogleSheetsRowReader.
- The one-shot runtime invokes the existing reader once per configured worksheet and returns results in configured order.
- Tests and reports contain only synthetic identities and aggregate live counts, never secrets, tokens, customer data, actual orders, or actual MPN values.

## acceptance

- [x] A caller can load all required runtime values from explicit local configuration.
- [x] Missing, malformed, incomplete, blank, duplicate, and unexpected configuration fails closed.
- [x] Existing GoogleSheetsRowReader is constructed with read-only OAuth service composition.
- [x] All configured worksheet identities can be enumerated and each is read exactly once in configured order.
- [x] No polling, Workflow state, token persistence, write scope, or Sheet write operation is added.
- [x] Scoped and full tests pass.
- [x] Scoped Ruff, diff review, whitespace check, and secret/sensitive-data inspection pass.
- [x] The single required Owner configuration/OAuth action is recorded without sensitive detail.
- [x] Task Packet is completed for commit and push on the task branch.

## verification

- Run pytest for tests/sheets and the full test suite.
- Run ruff check for source and tests.
- Run git diff --check and inspect the complete diff.
- Scan changed files for secret material, real spreadsheet identities, real worksheet content, write methods, write scopes, token persistence, forbidden imports, polling, and Workflow state.
- If INSO_SHEETS_READ_CONFIG_FILE is set, run one read-only smoke and report only per-worksheet row counts and overall success without identities or row content.

## completion

- status: complete
- changed: added strict local JSON configuration loading, ordered production worksheet identities, read-only OAuth/reader composition, one-shot read-all behavior, Git ignore coverage, durable Sheets documentation, and network-free tests
- verified: Sheets pytest passed 41 tests; full pytest passed 57 tests; scoped Ruff passed; git diff --check passed; manual diff and sensitive-data scan found no secret values, production identities, real row data, new write path, token persistence, polling, Workflow state, forbidden import, or Public Contract change; official Google client imports are available
- limitations: live smoke was not run because INSO_SHEETS_READ_CONFIG_FILE is absent; full-repository Ruff still reports two pre-existing Research-module findings outside this task; docs/BOUNDARIES.md requested by the delegation does not exist
- owner_action: create or select one non-repository (or `*.local.json`) config containing the real OAuth client-secret file path, production spreadsheet ID, and complete worksheet-title list; set INSO_SHEETS_READ_CONFIG_FILE to it and complete the interactive read-only OAuth prompt when the live process starts
- workflow_live_poll_condition: the Sheets-owned code prerequisite is complete, but the Workflow live poll is not operationally ready until the owner_action is completed and a read of every configured worksheet succeeds
