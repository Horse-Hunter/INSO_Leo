# Task: Synchronize V1 pre-implementation baseline

status: complete
owner: Codex
created: 2026-09-21
updated: 2026-09-21

## problem

The cross-module contract is nearly complete, but canonical Research input/result fields, Excel idempotency details, NO_MATCHING_PRODUCT semantics, and the selected V1 technical baseline are not yet consistently recorded.

## goal

Finalize the Sheets, Workflow, and Research documentation baseline before implementation without changing module ownership or writing code.

## current_facts

- Canonical ResearchInput and ResearchResult fields and statuses are confirmed.
- `调研价格.xlsx` is the official Research V1 persisted output with hidden `_inquiry_id` idempotency.
- NO_MATCHING_PRODUCT has a strict four-source success-and-no-match rule.
- The Windows/Python/SQLite/openpyxl/Google API/HTTP/Playwright technical baseline is confirmed.
- Pre-existing uncommitted Vault, code, Task, and reference-document work is outside this task.

## scope

- Update Product Baseline, Research, Workflow, Sheets, and only the outdated implementation-status lines in AI Start Here.
- Record and verify this task.

## non_scope

- Module Index changes, business implementation, dependency installation, external-system access, credentials, Vault changes, or pre-existing worktree files.

## requirements

- Keep one canonical detailed contract in the owning module and use concise cross-module references elsewhere.
- Record all confirmed fields, statuses, idempotency, no-match, and technology decisions.
- Preserve unconfirmed implementation details as `UNKNOWN`.
- Commit and push only this task's six files.

## acceptance

- [x] ResearchInput, ResearchResult, and status contracts are explicit and consistent.
- [x] Excel persistence/idempotency and success-result consistency are explicit.
- [x] NO_MATCHING_PRODUCT cannot mask technical failure or unavailable Bom.Ai pricing.
- [x] Workflow and Sheets public record contracts are aligned without changing dependencies.
- [x] Technical baseline replaces obsolete UNKNOWN statements.
- [x] Protected Module Index, business code, and Vault remain unchanged.

## verification

- Check all confirmed contract and technology facts plus required `UNKNOWN` items.
- Confirm protected files have no task-local diff.
- Run scoped `git diff --check` and review the complete scoped diff.
- Verify staged and committed file scope before pushing.

## completion

- status: complete
- changed: finalized Research contracts/statuses, Excel idempotency, NO_MATCHING_PRODUCT, cross-module record references, and the V1 technical baseline
- verified: contract, technology, narrowed-UNKNOWN, protected-file, secret scan, scoped diff, and formatting checks passed
- limitations: price-item and status-field rules, reason-code catalog, workbook mechanics, OAuth/browser operations, packaging, CI/CD, observability, and deployment automation remain `UNKNOWN`
