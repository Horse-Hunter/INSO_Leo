# Task: Workflow V1 Mainline Implementation

status: complete
actor_role: Workflow Module Codex
executor_tool: CODEX
module: workflow
reports_to: Workflow Module Chat
execution_mode: FAST_V1
architecture_impact: REQUIRED

## Problem

Workflow V1 has a confirmed architecture but no executable scheduler, durable queue,
deduplication, retry, recovery, or Sheets-to-Research orchestration.

## Goal

Implement the complete Workflow V1 mainline with a local SQLite state store, one
poll at a time, one Research worker, safe Brand handoff, and restart recovery.

## Current Facts

- The CEO Gate is complete for the V1 row-based dedup decisions in this Task.
- Sheets exposes pending records with an opaque record identity and safe Brand write.
- Research exposes canonical input/result contracts.
- Research completion-confirmation remains `UNKNOWN`; this Task may add only a
  narrow injectable Workflow seam and must record real wiring as the sole gap.

## Required Context

- `docs/AI_TEAM.md`
- `docs/TASK_PROTOCOL.md`
- `docs/modules/WORKFLOW.md`
- `docs/modules/SHEETS.md`
- `docs/modules/RESEARCH.md`
- `src/workflow/**`, `tests/workflow/**`
- Sheets and Research Public Contracts and necessary public implementation

## Write Scope

- `docs/modules/WORKFLOW.md`
- `src/workflow/**`
- `tests/workflow/**`
- This Task Packet
- `.gitignore` only if Workflow runtime exclusions are missing

## Scope

Implement polling, durable queue/dedup, single-worker Research execution, status
mapping, configurable 15/30/60 retry, restart recovery, and safe Brand handoff.

## Non-scope

UUID, Sheet status writes, V2 lifecycle, INSO procurement, Quotation, Research or
Sheets internals, production side effects, and new infrastructure.

## Requirements

- Scan all configured worksheets every 15 minutes and enqueue all pending records.
- Deduplicate for V1 by `spreadsheet + worksheet + row_number` for the DB lifetime.
- Persist a stable non-UUID `inquiry_id` and the opaque Sheets identity.
- Pass canonical Research input including unchanged `importance_raw`.
- Use only the six confirmed Workflow states and the confirmed result mappings.
- Retry after 15, 30, and 60 minutes, then fail after the fourth failed attempt.
- Recover `RESEARCHING` by checking completion first, without a stale timeout.
- Send `resolved_brand` through Sheets safe Brand update; preserve terminal Research
  status on Brand conflict.

## Acceptance

- [x] All configured worksheets and all pending rows are polled.
- [x] SQLite dedup survives restart and never uses UUID.
- [x] Stable `inquiry_id` and opaque identity are persisted.
- [x] Worker concurrency is one and canonical input is preserved.
- [x] All Research result mappings and retry timings are tested.
- [x] Restart recovery is tested through an injectable completion-check seam.
- [x] Brand updates use opaque identity and conflicts preserve Research completion.
- [x] Runtime SQLite files are ignored.
- [x] Mock/fake smoke passes without external side effects.
- [x] Module doc matches implementation.

## Owner Decisions

- Enqueue every pending record from every target worksheet on each 15-minute poll.
- V1 dedup identity is `spreadsheet + worksheet + row_number`; row number is never
  used for Sheet writes.
- V1 does not use UUID. UUID and formal order lifecycle are V2.
- Research concurrency is one; retry defaults are 15/30/60 minutes.

## Execution

Complete diagnosis, implementation, tests, fixes, fake smoke, self-review, Task
completion, commit, and push. Do not perform live Sheet writes or live Research.

## Final Report

- Final result: implemented the Workflow V1 durable mainline, including all-target
  polling, all-pending enqueue, SQLite dedup/state, one Research worker, result
  mapping, retry, restart recovery, and safe Brand handoff.
- Verification: `204 passed`; Workflow Ruff checks passed; fake mainline smoke
  passed without Google Sheet or Research website side effects; scoped diff and
  runtime-ignore checks passed.
- Remaining gap: Research completion-confirmation has no canonical Public Contract,
  so real restart wiring remains `UNKNOWN`; Workflow provides only the approved
  injectable seam and tested recovery behavior.
