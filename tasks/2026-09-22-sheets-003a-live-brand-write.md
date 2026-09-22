# Task: SHEETS-003A Live Brand F Safe Write Validation

status: blocked
owner: Codex
created: 2026-09-22
updated: 2026-09-22

## problem

SHEETS-003 proves safe Brand relocation and targeted F-only writes with fakes, but the path has not yet been validated against the authorized shared business worksheet.

## goal

Validate the existing safe Brand write path against one real pending record, with at most one successful targeted F-cell update and a read-only post-write verification.

## current_facts

- SHEETS-003 passed Module Review and is committed as f6ca43ff648f9d7c0e428751be0f25d41aef5b64.
- Owner authorizes at most one successful real Brand write to the supplied spreadsheet and worksheet 2026.
- The OAuth Desktop Client credential is supplied from a repository-external path and must not be read into logs or committed.
- The final Brand must be an explicitly confirmed real business value; Sheets must not research, infer, or guess it.
- The precondition read and values.update are not an atomic transaction or CAS operation.
- Live read passed and the live write dry-run completed without calling a writer.
- No complete safe production candidate was available, so the dry-run failed closed with zero real writes; this is not a code failure.
- Other existing worktree changes are outside this task.

## scope

- Perform a read-only live dry run using GoogleSheetsRowReader and query_pending_records.
- Select only a pending record whose F cell is blank and whose A/C/E/G snapshot uniquely identifies one current row.
- Add only the minimum Sheets-owned writable OAuth capability if Phase B becomes authorized by a confirmed Brand.
- Revalidate the record and blank F immediately before one targeted values.update call.
- Verify the written F value and unchanged A/C/E/G with an immediate read.
- Record only non-sensitive validation facts.

## non_scope

- Brand research, inference, guessing, or test values.
- Writes to A/C/E/G, whole-row writes, append, clear, delete, create, formatting, permissions, rollback, or automatic write retry.
- Google Drive scopes, token persistence, Core Credential Provider changes, cross-module contracts, or unrelated worktree files.
- Any task after SHEETS-003A.

## requirements

- Phase A must be read-only and must not construct or call a writer.
- Stop when no safe candidate exists or when the candidate lacks an explicitly confirmed resolved_brand.
- Before Phase B, scoped Sheets pytest and ruff must pass.
- Phase B must use the spreadsheets OAuth scope only, with no persisted token.
- Immediately before the write, re-read, require one A/C/E/G match, confirm the same record, and confirm F is blank.
- Permit at most one successful update targeting exactly one F cell through values.update.
- If write outcome is uncertain, read to determine the outcome and never retry blindly.
- After success, verify F and unchanged A/C/E/G by read only; do not restore F to blank.

## acceptance

- [x] Phase A live read and write dry-run complete; no safe candidate exists and the operation fails closed.
- [ ] A real Brand is explicitly confirmed before any write.
- [x] Scoped Sheets pytest and ruff pass before any real write.
- [x] Writable OAuth uses only the spreadsheets scope and does not persist tokens.
- [ ] Exactly one targeted F update succeeds, with no other write operation.
- [ ] Post-write read confirms expected F and unchanged A/C/E/G.
- [ ] No credential, token, or full real business row is printed or committed.

## verification

- Check only credential-file existence and official library imports.
- Run scoped Sheets pytest and ruff separately from live operations.
- Run Phase A with the existing read-only OAuth helper and expose only candidate row, MPN, blank-F state, and uniqueness.
- If Brand confirmation is absent, stop with no write and record the blocker.
- Inspect the scoped diff and git status before review.

## completion

- status: blocked
- changed: added a minimal non-persistent read/write Sheets OAuth helper with an exact spreadsheets scope, kept the existing read-only helper, and added unit coverage proving scope separation
- verified: live read passed; live write dry-run executed; the only blank-F row with unique A/C/E/G relocation had no MPN and therefore was not accepted as a complete safe candidate; the operation failed closed with zero real writes and this is not a code failure; all 25 Sheets tests passed and scoped ruff passed
- limitations: real write validation remains an operational limitation until a complete safe production candidate with a confirmed real Brand exists
