# Task: Baseline V2 — Lean AI Governance Refactor

status: complete
actor_role: Architecture Codex
module: architecture
reports_to: CEO / Architecture Chat
execution_mode: FAST_V1
architecture_impact: REQUIRED

## Problem

Canonical governance repeats facts across routing, product, module, and README documents; some status text is stale and every actor is directed to read too much context.

## Goal

Establish a shorter Baseline V2 with role-based minimum reading, stage-sized FAST_V1 execution, one canonical owner per fact, fixed reports, strict safety boundaries, and hardened runtime/secret ignores.

## Current Facts

- Canonical base is remote `main` at `467a0c1f787c3c5670d624f0157314ec50c9c7aa`.
- Sheets V1 is protected at `backup/sheets-v1-before-baseline-v2`; it must not be merged.
- Credential Vault source exists only as protected local work and must not be merged or inspected for live values.
- Research is the only implemented business module on the canonical base.

## Required Context

- Canonical governance, module docs, module READMEs, source/test inventory, `.gitignore`, and the CEO-confirmed Baseline V2 request.

## Write Scope

- `AGENTS.md`, `.gitignore`, `docs/**/*.md`, `src/*/README.md`, `tests/*/README.md`, and this Task Packet.

## Scope

- Refactor governance ownership/templates; slim product/module docs; repair stale READMEs; strengthen ignores; verify, commit, and push canonical `main` safely.

## Non-scope

- Business code; Research/Sheets integration; Sheets or Vault merge; Workflow implementation; real external systems.

## Requirements

- Preserve confirmed product/module contracts while removing duplication.
- Keep safety strict and give Codex autonomy for ordinary scoped implementation.
- Do not read or commit secrets, runtime data, or local reference documents.

## Acceptance

- [x] Role routing, identity, FAST_V1, escalation, Review, report, browser-first, and Handoff rules are concise and canonical.
- [x] Product, module, README, and safety facts each have one primary owner.
- [x] Governance volume decreases after adding `BOUNDARIES.md` and `CORE.md`.
- [x] Ignore rules cover observed sensitive/runtime risks without hiding source/tests/Tasks.
- [x] Consistency, diff, formatting, and secret checks pass; no business code changes.

## Execution

Work in an isolated canonical-main worktree. Do not merge/rebase/reset/clean or touch protected local assets. Commit and push only after verification.

## Final Report

Use `docs/TASK_PROTOCOL.md`. Stop after reporting to CEO Chat.
