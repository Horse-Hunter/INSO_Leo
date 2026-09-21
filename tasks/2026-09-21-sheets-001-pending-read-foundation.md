# Task: SHEETS-001 Pending Record Read Foundation

status: complete
owner: Codex
created: 2026-09-21
updated: 2026-09-21

## problem

The Sheets module has a confirmed V1 read and record-identity contract, but it has no implementation that can map worksheet rows into pending records behind a testable reader boundary.

## goal

Provide the smallest network-free Sheets domain foundation for a one-shot pending-record query, suitable for an in-memory reader now and a future Google Sheets API adapter.

## current_facts

- `docs/PRODUCT_BASELINE.md` and `docs/modules/SHEETS.md` define A/C/E/F/G as status, raw importance, model/MPN, brand, and quantity.
- A row is pending only when A is exactly `未发`.
- Record identity combines worksheet identity, row position, and an identifying snapshot; row position alone is not permanent identity.
- Sheets may depend on `core` but must not depend on `workflow`, `research`, `inso`, or `quotation`.
- Google Sheets API/OAuth implementation and all write behavior are outside this task.
- For this task, the identifying snapshot may contain the exact observed A/C/E/F/G values.
- UNKNOWN: real spreadsheet/worksheet configuration and adapter details remain unconfirmed.

## scope

- Define worksheet identity, worksheet row, identifying snapshot, record identity, and pending-record value objects under `src/sheets/`.
- Define a narrow injected worksheet-row reader protocol.
- Implement a one-shot query that returns every row whose A value is exactly `未发`.
- Map A/C/E/F/G without normalization or business conversion and preserve row position.
- Add network-free unit tests under `tests/sheets/`.

## non_scope

- Google Sheets API, OAuth, credentials, network access, configuration management, or dependency installation.
- Any Sheet write, Brand update, relocation/matching algorithm, conflict handling, or stable ID column.
- Scheduling, polling, retry, duplicate prevention, `inquiry_id`, or global state.
- Workflow, Research, INSO, Quotation, pricing, or importance interpretation.
- Packaging, CI, or cross-module architecture changes.

## requirements

- The reader is injected through a narrow protocol and can be implemented in memory.
- Pending comparison is exactly `status == "未发"`; no trimming, case conversion, Unicode normalization, or aliases are allowed.
- A/C/E/F/G values are returned exactly as observed; `importance_raw` receives no business conversion.
- Each result includes the actual row position and a record identity containing worksheet identity, row position, and the exact A/C/E/F/G snapshot.
- Querying no matching rows returns an empty collection.
- The implementation uses no network or forbidden cross-module imports.

## acceptance

- [x] One and multiple exact `未发` rows are returned.
- [x] No pending rows produce an empty result.
- [x] Non-exact status values are excluded.
- [x] A/C/E/F/G mapping and raw importance preservation are proven.
- [x] Record identity includes worksheet identity, row position, and identifying snapshot.
- [x] Row position is not represented as a standalone permanent business ID.
- [x] Tests use only a fake/in-memory reader and perform no network access.
- [x] No forbidden cross-module imports or out-of-scope behavior are introduced.
- [x] Scoped pytest and applicable ruff checks pass, or limitations are recorded truthfully.

## verification

- Run scoped Sheets pytest.
- If available, run ruff against this task's Python files.
- Inspect the complete task diff and run `git diff --check` for task files.
- Search changed Sheets code for forbidden module imports and network/Google/OAuth/credential behavior.
- Confirm no files outside the task packet and Sheets source/test paths were changed by this task.

## completion

- status: complete
- changed: added immutable Sheets read-contract value objects, an injected worksheet-row reader protocol, the exact pending query, and five fake-reader unit tests
- verified: all five test functions passed directly under Python 3.12; scoped boundary scan found no forbidden imports, network/API/OAuth/credential behavior, or write behavior; scoped whitespace/diff and file-scope reviews passed
- limitations: pytest and ruff are not installed for Python 3.12 (or the PATH Python 3.8), so their commands could not run; real spreadsheet/worksheet configuration, Google adapter/OAuth, relocation/matching, writes, and other previously documented items remain UNKNOWN and out of scope
