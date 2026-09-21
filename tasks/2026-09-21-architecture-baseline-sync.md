# Task: Sync architecture baseline for Sheets and Research

status: complete
owner: Codex
created: 2026-09-21
updated: 2026-09-21

## problem

The repository baseline still describes five modules and an initialization-era ban on webpage access. It does not capture the confirmed Sheets boundary, Workflow scheduling ownership, Research V1 sources and output, or the local Credential Provider safety boundary.

## goal

Synchronize durable architecture documentation and module skeletons with the six-module design without implementing business behavior.

## current_facts

- The confirmed modules are `core`, `sheets`, `research`, `workflow`, `inso`, and `quotation`.
- Workflow owns scheduling, global state, retry, duplicate prevention, and module orchestration.
- Sheets is a single-operation Google Sheets integration boundary and does not own scheduling or global workflow state.
- Research V1 may perform read-only market research against the five approved sources and currently outputs to a local Excel file.
- A Windows CurrentUser DPAPI Credential Provider exists as infrastructure; live secrets and its external vault must never enter Git.
- Existing uncommitted Credential Vault implementation work and local reference artifacts predate this task and are excluded from this task's commit.

## scope

- Update the module index, product baseline, and only outdated AI entry-point status.
- Add durable Research and Sheets module documentation.
- Add README-only source and test skeletons for `sheets`.
- Record this task and its verification.

## non_scope

- Google Sheets API implementation, scheduler implementation, web crawler implementation, Bom.Ai login, Excel writing, INSO behavior, or quotation behavior.
- Credential Vault implementation changes or a new credentials business module.
- Real external-system access, dependency installation, or handling live credentials.
- Any pre-existing uncommitted work outside the files named in this packet.

## requirements

- Preserve the dependency directions and forbidden dependencies supplied by the requester.
- Keep selectors, XPath, credentials, customer data, and temporary implementation details out of durable documentation.
- Leave unconfirmed Sheet column mappings and business schemas as `UNKNOWN`.
- Commit and push only this task's files to `main`.

## acceptance

- [x] Six modules and their code/test paths are documented.
- [x] Sheets, Workflow, and Research responsibilities and dependency boundaries are explicit and consistent.
- [x] Research V1 access authorization replaces the obsolete blanket webpage-access ban.
- [x] Credential Provider architecture and secret-handling rules are recorded without live secrets.
- [x] `src/sheets/` and `tests/sheets/` contain documentation-only skeletons.
- [x] Documentation consistency, secret-safety, no-business-code, and Git diff checks pass.
- [x] The scoped staged change contains only this task's files; commit and push are verified during delivery.

## verification

- Validate required files, module sections, dependency declarations, approved Research sources, and required `UNKNOWN` markers.
- Search this task's diff for secret-bearing fields and forbidden implementation files.
- Run `git diff --check` and review the complete scoped diff.
- Verify the commit contents, local/remote commit identity, upstream, and remaining pre-existing worktree changes.

## completion

- status: complete
- changed: synchronized the six-module architecture, Research and Sheets boundaries, Research V1 authorization, Credential Provider principles, and Sheets documentation-only skeleton
- verified: module/dependency, documented-fact, UNKNOWN, scoped secret-assignment, no-business-implementation, and git diff checks passed
- limitations: Sheet mappings, Research schemas, workflow policies, and multiple product/business facts remain `UNKNOWN`; commit and push are verified after this packet is written
