# Task: Confirm Workflow V1 architecture

status: complete
owner: Codex
created: 2026-09-21
updated: 2026-09-21

## problem

Workflow and Research documentation still leaves now-confirmed V1 identity, state, retry, concurrency, restart, Excel consistency, and Brand-flow decisions unspecified.

## goal

Synchronize durable Workflow V1 architecture, its Research contract implications, and the AI communication discipline without implementing behavior or changing long-term dependencies.

## current_facts

- Workflow V1 uses a local SQLite state store and `inq_<UUIDv4>` identities.
- Polling and Research execution are decoupled with one active poll and Research concurrency one.
- States, default retries, restart recovery principle, and Excel consistency rules are confirmed.
- Brand resolution flows Research -> Workflow -> Sheets, while Brand conflict does not undo completed Research.
- Pre-existing uncommitted Vault, code, Task, and reference-document work is outside this task.

## scope

- Update `docs/modules/WORKFLOW.md`, `docs/PRODUCT_BASELINE.md`, and `docs/modules/RESEARCH.md`.
- Add the concise Communication Discipline to `docs/AI_TEAM.md`.
- Record and verify this task.

## non_scope

- SQLite, scheduler, Research, Excel, Sheets, INSO, Quotation, credential, or Vault implementation.
- Changes to Module Index, Sheets module document, AI entry point, or pre-existing worktree files.

## requirements

- Record every confirmed Workflow V1 decision without inventing implementation details.
- Preserve remaining design/implementation gaps as `UNKNOWN`.
- Keep long-term module dependencies unchanged.
- Commit and push only this task's five files.

## acceptance

- [x] Workflow state, identity, concurrency, retry, and restart behavior are explicit.
- [x] ResearchInput, Excel idempotency/result consistency, and resolved Brand flow are explicit.
- [x] Product baseline no longer marks confirmed Workflow facts as unknown.
- [x] Communication Discipline is concise and complete.
- [x] Protected documents, business code, and Vault remain unchanged.

## verification

- Check all confirmed facts and remaining `UNKNOWN` items.
- Confirm protected files have no task-local diff.
- Run scoped `git diff --check` and review the complete scoped diff.
- Verify staged and committed file scope before pushing.

## completion

- status: complete
- changed: confirmed Workflow V1 state, identity, concurrency, retry, recovery, Research/Excel/Brand contracts, and communication discipline
- verified: confirmed-fact, narrowed-UNKNOWN, protected-file, secret scan, scoped diff, and formatting checks passed
- limitations: SQLite schema/migrations, duplicate key/algorithm, transition guards, scheduling and recovery mechanisms, remaining result schema, and Excel mechanics remain `UNKNOWN`
