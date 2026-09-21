# Task: Define V1 workflow scope

status: complete
owner: Codex
created: 2026-09-21
updated: 2026-09-21

## problem

The product baseline does not yet distinguish the executable V1 path from future INSO and Quotation scope, and the confirmed ResearchResult handling is not recorded.

## goal

Record the confirmed V1 pipeline, completion semantics, result handling, and durable Workflow boundary without changing the long-term module architecture.

## current_facts

- V1 runs a 15-minute Workflow scheduler and processes `未发` inquiries from Sheets through Research into local `调研价格.xlsx`.
- INSO, Quotation, final customer quotation, and final quotation write-back are future-version scope.
- The six-module architecture and dependency graph remain unchanged.
- Pre-existing uncommitted Vault and reference-document work is outside this task.

## scope

- Add the V1 product scope and ResearchResult handling to `docs/PRODUCT_BASELINE.md`.
- Create `docs/modules/WORKFLOW.md`.
- Record and verify this task.

## non_scope

- Changes to `docs/MODULE_INDEX.md` or `docs/modules/RESEARCH.md` unless a direct conflict is found.
- Scheduler, Google API, Excel writing, crawler, INSO, Quotation, credential, or Vault implementation.
- Any pre-existing uncommitted work.

## requirements

- Preserve all six modules and the long-term dependency direction.
- Define V1 `COMPLETED`, manual-review, and retryable-failure behavior exactly as confirmed.
- Preserve unresolved retry and contract details as `UNKNOWN`.
- Commit and push only this task's three files.

## acceptance

- [x] The V1 pipeline and future-version exclusions are explicit.
- [x] All four ResearchResult outcomes are documented.
- [x] `COMPLETED` requires a successful local Excel write for successful or qualifying partial results.
- [x] Workflow responsibilities and non-responsibilities are documented.
- [x] Module index, Research module document, business code, and Vault remain unchanged by this task.

## verification

- Check required V1 facts, outcome names, future scope, and `UNKNOWN` items.
- Confirm protected files have no task-local diff.
- Run scoped `git diff --check` and review the complete scoped diff.
- Verify staged and committed file scope before pushing.

## completion

- status: complete
- changed: defined the V1 pipeline and result handling in the product baseline and added the durable Workflow module document
- verified: V1 facts, outcomes, Workflow boundaries, protected files, no-business-code, secret scan, scoped diff, and formatting checks passed
- limitations: retry policy, inquiry identity/state details, duplicate keys, Sheet criteria, and local Excel failure handling remain `UNKNOWN`
