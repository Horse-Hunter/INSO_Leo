# Task: SHEETS-003 Record Relocation and Brand F Blank-only Safe Write

status: complete
owner: Codex
created: 2026-09-22
updated: 2026-09-22

## problem

Sheets can read pending records and produce composite identities, but it cannot yet relocate an original record or safely write a resolved Brand without risking a stale-row or human-overwrite error.

## goal

Implement the smallest Sheets-owned safe Brand write path: relocate by composite identity, fail closed unless the record is safely resolved, independently re-check column F, and update only the target F cell.

## current_facts

- Record identity combines worksheet identity, original row position, and the exact A/C/E/F/G snapshot.
- Relocation first checks the original row; if it no longer matches, the snapshot must match exactly one current row.
- Zero or multiple fallback matches are conflicts.
- Brand may be written only while F is blank immediately before the write.
- A Brand write must target one F cell and must never write a complete row.
- SHEETS-002A live read was reported by Owner as passed for worksheet 2026 with 174 rows and 3 pending records.
- Real Google Sheet writes are forbidden in this task.
- Other existing worktree changes, including the SHEETS-002A Task Packet, are outside this task.

## scope

- Implement record relocation and snapshot validation.
- Implement unique-match fail-closed conflicts.
- Re-read and revalidate the target immediately before the Brand write.
- Treat only None and the empty string as blank F values.
- Define a targeted Brand writer boundary and Sheets-owned conflict/write errors.
- Add a minimal Google Sheets values.update adapter targeting one F cell.
- Add fake/in-memory unit tests with no real network calls.
- Create and complete this Task Packet.

## non_scope

- Real Google Sheet writes or live write tests.
- Workflow retry, scheduler, polling, duplicate prevention, global state, Research, INSO, or Quotation.
- Sheet status changes, stable IDs, whole-row writes, cross-module contracts, general transaction frameworks, or Core changes.
- Changes to SHEETS-001, SHEETS-002, or SHEETS-002A artifacts.

## requirements

- Never use the old row number alone as identity.
- Prefer a matching original row; otherwise require exactly one full snapshot match.
- Re-read before writing and independently enforce blank-only F.
- Whitespace or any other F content is non-blank.
- Update only the resolved F cell through a narrow writer boundary.
- Surface unsafe identity as SheetRecordConflict and write failures as SheetsWriteError.
- Google adapter failures must surface as GoogleSheetsWriteError.
- Default tests must use only fakes and must not perform network access.

## acceptance

- [x] Matching original row is resolved.
- [x] A uniquely shifted row is relocated.
- [x] Zero snapshot matches produce conflict.
- [x] Multiple snapshot matches produce conflict.
- [x] F blank on re-read permits Brand write.
- [x] Human-populated F on re-read produces conflict and no write.
- [x] A row moving between reads is relocated again.
- [x] Google adapter updates exactly one F cell with RAW input.
- [x] Google write failure produces a Sheets-owned write error.
- [x] No real network write is executed.
- [x] Scoped pytest and ruff pass.
- [x] Diff and boundary checks contain only SHEETS-003 work.

## verification

- Run all scoped Sheets pytest tests.
- Run ruff against SHEETS-003 Python files.
- Inspect the complete scoped diff and run whitespace checks.
- Scan for forbidden cross-module imports and accidental whole-row/write operations.
- Confirm no real Google API call or live write test ran.
- Confirm unrelated worktree files remain untouched.

## completion

- status: complete
- changed: added composite-identity relocation, two-read pre-write validation, blank-only Brand conflict handling, a targeted Brand writer boundary, a one-cell Google values.update adapter, and fake unit tests
- verified: all 22 scoped Sheets pytest tests passed; scoped ruff passed; tests prove original and moved relocation, zero/multiple conflicts, F precondition, re-relocation, targeted F-only update, and Sheets-owned write failures; no live write ran
- limitations: Google Sheets does not provide a transaction spanning relocation, precondition read, and values.update; real write validation remains prohibited pending separate Owner authorization
