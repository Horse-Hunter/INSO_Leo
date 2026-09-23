# Task: Sheets SHAHAB V1 Worksheet-specific Adaptation

status: complete
actor_role: Sheets Module Codex
executor_tool: CODEX
module: sheets
reports_to: Sheets Module Chat
execution_mode: FAST_V1
architecture_impact: REQUIRED

## Problem

Sheets hard-codes standard worksheet columns for pending reads, source identity, Brand relocation, blank validation, and targeted writes. The confirmed V1 `shahab` worksheet uses different physical columns while downstream modules must continue to receive one unified record and opaque provenance.

## Goal

Implement worksheet-specific standard and `shahab` behavior entirely inside Sheets while preserving the existing standard contract.

## Current Facts

- CEO Architecture Gate is complete; `docs/modules/SHEETS.md` is canonical.
- Standard mapping is A/C/E/F/G with A/C/E/G Brand relocation and F Brand writes.
- SHAHAB mapping is B/(normalized `A`)/D/E/F with B/D/F Brand relocation and E Brand writes.
- SHAHAB normalized importance is not a source observation and must not enter source identity.
- Google reader already reads A:G, which covers both V1 schemas.
- Real Brand writes are not authorized by this Task.

## Required Context

- `docs/AI_START_HERE.md`
- `docs/AI_TEAM.md`
- `docs/TASK_PROTOCOL.md`
- `docs/modules/SHEETS.md`
- `src/sheets/`
- `tests/sheets/`

## Write Scope

- `src/sheets/**`
- `tests/sheets/**`
- `docs/modules/SHEETS.md`
- `tasks/2026-09-24-sheets-shahab-v1.md`

## Scope

- Add minimal internal mappings for standard worksheets and `shahab`.
- Produce unified pending records with worksheet-specific source snapshots.
- Relocate by the correct globally unique non-Brand source fields.
- Validate and target the correct Brand cell immediately before writing.
- Add regression and SHAHAB tests, sync docs, run checks and mock smoke, self-review, commit, and push.

## Non-scope

- Fields other than Brand, quotation, other modules, polling/retry, OAuth persistence, stable IDs, broad configuration, or real Google Sheet writes.

## Requirements

- Pending status remains strict equality with `未发`.
- Standard snapshot remains A/C/E/F/G; SHAHAB snapshot represents only B/D/E/F and excludes normalized importance.
- Provenance retains spreadsheet, worksheet, original row, and source snapshot.
- Standard relocation requires one A/C/E/G match; SHAHAB requires one B/D/F match. Brand and row number never break ties.
- Zero or multiple candidates fail closed.
- Only `None` and `""` are blank.
- The writer updates one cell only: standard F, SHAHAB E.

## Acceptance

- [x] Existing standard Sheets behavior and tests pass.
- [x] SHAHAB pending mapping, strict status, normalized importance, and provenance are covered.
- [x] SHAHAB source snapshot excludes synthetic importance.
- [x] Both relocation schemas and fail-closed cases are covered.
- [x] Blank-only safety and single-cell writers are covered.
- [x] Module doc matches implementation.
- [x] Sheets pytest, ruff, mock smoke, diff and security review pass.
- [x] Task status is complete and commit/push succeed.

## Execution

Use a clean isolated worktree based on latest `origin/main`. Do not perform a real Google Sheet write.

## Final Report

- Result: added internal standard/SHAHAB worksheet schemas, unified SHAHAB pending output with synthetic importance excluded from source identity, globally unique worksheet-specific Brand relocation, correct blank-cell validation, and standard F / SHAHAB E targeted writers.
- Verification: 35 Sheets tests passed; Ruff passed; three focused fake-based smoke tests passed; diff check, file-scope review, forbidden dependency scan, and Secret review passed.
- Operational limitation: no real Google Sheet smoke was run because this Task did not authorize a real write and no read-only production environment was required or available.
- Remaining gap: NONE for this Task.
