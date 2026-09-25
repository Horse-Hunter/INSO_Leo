# Task: INSO V1.2 architecture/design spike

status: ready_for_ceo_review
owner: Leo / CEO review
created: 2026-09-25
updated: 2026-09-25

## problem

V1.1 provides a stable Sheets → Workflow → Research pipeline and Windows GUI/launcher, but V1.2 adds new cross-module business routing, notification delivery, INSO reads/writes, alert history and shared browser lifecycle. Implementing those behaviors before agreeing on public contracts and safety boundaries risks changing V1.1 behavior or performing an unintended production write.

## goal

Produce a reviewable additive architecture proposal and update `docs/CURRENT_TASK.md` to READY_FOR_CEO_REVIEW without implementing V1.2 production behavior.

## current_facts

- `origin/main`, `origin/release/v1.1`, and `origin/feature/v1-2` were at `be9d0a51d0375884dfa3e5e9e4317958899fdc75` at task start; `feature/v1-2` contained latest `origin/main`.
- Existing Workflow state is persisted in SQLite; GUI consumes `GuiBackend`; worksheet mappings belong to Sheets.
- Existing Research INSO history is read-only and does not expose all duplicate-review fields.
- Existing Research canonical behavior must remain unchanged.
- See `docs/V1_2_ARCHITECTURE.md` for remaining UNKNOWN items and proposed contracts.

## scope

- Create `docs/V1_2_ARCHITECTURE.md` with state machine, public contract proposals, lifecycle, safety allowlist, migration/evidence strategy, test matrix, implementation plan and review gates.
- Update `docs/CURRENT_TASK.md` with stage status and handoff.
- Commit/push only these design/task files on `feature/v1-2`.

## non_scope

- Runtime code, contract skeletons, SMTP transport, live browser selectors, database migration implementation or GUI behavior.
- Real INSO access/write, real Google Sheets change, production purchase process, and real business email.
- Changing V1.1 Research, Brand write, or `release/v1.1`.
- Merge to `main`.

## requirements

- Preserve the confirmed Owner business rules in the task request.
- Keep Research unchanged; add duplicate read as a separate seam.
- Separate business state, append-only event history and multiple active alerts.
- Specify retry/idempotency per recipient and fail-closed write/session boundaries.
- Record unresolved rules as CEO decisions or UNKNOWN instead of inventing answers.

## acceptance

- [x] Architecture document covers all 15 requested design areas.
- [x] Current task is marked `READY_FOR_CEO_REVIEW`.
- [x] No runtime code or external production side effect is included.
- [x] Diff is limited to architecture and task-state documentation.
- [x] Commit and push to `feature/v1-2`; do not merge main.

## verification

- Inspect complete scoped diff and `git diff --check`.
- Confirm only the three intended documentation files are changed.
- Confirm no source/test files, secrets, production data or screenshots are added.
- Confirm commit branch/upstream and pushed commit.

## completion

- status: pending
- changed: design documents only
- verified: pending
- limitations: CEO decisions and Safety Supervisor review remain required before production implementation or live write/smoke.
