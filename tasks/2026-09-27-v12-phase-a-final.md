# Task: V1.2 Phase A final contract discovery

status: blocked_on_runtime_contract
owner: Main Programmer
created: 2026-09-27
updated: 2026-09-27

## problem

Production duplicate query settlement is implemented. Creator, INSO quote
semantics, AI recognition/read-back, and blank-draft product writer still need
Owner-authenticated Chrome evidence. The Codex execution context cannot safely
inspect the Owner's authenticated browser.

## goal

Finish statically provable work and provide one bounded, read-only Owner-session
runner for remaining browser observations. Keep Production Write Gate CLOSED.

## implementation

- Reuse current Chrome bootstrap and `InsoSessionLease`; validate configured
  executable/profile/endpoint before attach and require one verified context.
- Use the production duplicate page adapter for one exact public-part query;
  record schema and approved labels only.
- Inspect at most one unambiguous detail and a blank temporary form/AI panel.
- Do not run AI recognition, import a row, fill product fields, or click Save or
  Send controls.
- Write a sanitized JSON report only under ignored runtime evidence.
- Provide `runtime/run_v12_phase_a_readonly.cmd` as a local ignored double-click
  entry point; do not add a browser profile or change configuration.

## acceptance

- [x] Existing query settlement implementation is reused.
- [x] Creator/quote are confirmed only from matching schema/grid/detail facts.
- [x] The report stores no row values or raw exceptions.
- [x] The runner never clicks `#btnSave`, `#btnSave2`, or `#bcSend`.
- [x] AI recognition/import are not executed by the runner.
- [x] The local one-click command is Git-ignored.
- [x] Owner-session runner executed; report records current read-only result.
- [ ] Lease child shares the authenticated shell session, or an approved
  explicit verified-page read-only path is available.
- [ ] Exact query control becomes safely actionable; never force the hidden
  `#nolike` checkbox.

## verification

- Run Ruff and deterministic Launcher, INSO, Workflow, and notification tests.
- Run `git diff --check` and inspect the scoped diff.
- Do not execute the Owner-session runner from the Codex sandbox.

## completion

- status: blocked_on_runtime_contract
- changed: bounded read-only runner, deterministic report/classifier tests,
  current task and INSO module docs
- remaining: authenticated shell page and lease child session boundary, plus
  safe exact-query control access. No Save or other business write is involved
  or authorized.
