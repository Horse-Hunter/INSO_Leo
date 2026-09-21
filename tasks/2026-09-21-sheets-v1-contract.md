# Task: Confirm Sheets V1 contract

status: complete
owner: Codex
created: 2026-09-21
updated: 2026-09-21

## problem

The Sheets baseline still marks column mapping, pending criteria, writable fields, and record-location contract broadly unknown even though their V1 safety contract is now partly confirmed.

## goal

Record the confirmed Sheets V1 read, identity, safe-write, Workflow, and integration contract while preserving implementation details as `UNKNOWN`.

## current_facts

- V1 uses columns A, C, E, F, and G with confirmed meanings.
- Pending records have A exactly equal to `未发`.
- Safe writes require record relocation, validation, fail-closed conflict handling, and targeted field updates.
- Google Sheets API with OAuth User Authorization is preferred for V1.
- The six-module architecture and full V1 path remain unchanged.
- Pre-existing uncommitted Vault, code, Task, and reference-document work is outside this task.

## scope

- Update `docs/modules/SHEETS.md`.
- Update outdated Sheets `UNKNOWN` statements in `docs/PRODUCT_BASELINE.md`.
- Record and verify this task.

## non_scope

- Google API or OAuth implementation, real Sheet login/access, polling, business code, Vault changes, or stable-ID column creation.
- Changes to Module Index, Workflow, Research, AI navigation, or pre-existing worktree files.

## requirements

- Preserve all confirmed column, pending, identity, conflict, Brand, targeted-update, integration, and V1-path facts.
- Do not invent OAuth, snapshot, matching, or additional writable-field details.
- Commit and push only this task's three files.

## acceptance

- [x] Sheets V1 column mapping and pending criterion are explicit.
- [x] Composite record identity and fail-closed relocation rules are explicit.
- [x] Brand F and targeted-field update rules are explicit.
- [x] Preferred API/OAuth approach and remaining implementation unknowns are explicit.
- [x] Protected architecture/module documents and business code remain unchanged.

## verification

- Check all confirmed Sheets facts and required `UNKNOWN` items.
- Confirm protected files have no task-local diff.
- Run scoped `git diff --check` and review the complete scoped diff.
- Verify staged and committed file scope before pushing.

## completion

- status: complete
- changed: confirmed the Sheets V1 column, pending, identity, fail-closed, Brand, targeted-update, integration, and product-path contract
- verified: confirmed-fact, remaining-UNKNOWN, protected-file, secret scan, scoped diff, and formatting checks passed
- limitations: spreadsheet/worksheet configuration, identifying-snapshot fields, matching algorithm, OAuth token/scope/refresh behavior, and additional writable fields remain `UNKNOWN`
