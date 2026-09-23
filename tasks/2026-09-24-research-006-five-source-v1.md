# Task: RESEARCH-006 — Five-Source Research V1 Contract Implementation

status: complete
actor_role: Research Module Codex
executor_tool: CODEX
module: research
reports_to: Research Module Chat
execution_mode: FAST_V1
architecture_impact: REQUIRED
architecture_gate: DONE

## Problem

Research still implements the previous four-price-source, strict-MPN, quantity-tier, and eight-column Excel behavior. The canonical Research contract now requires five price sources and revised selection, aggregation, status, and snapshot semantics.

## Goal

Implement the canonical `docs/modules/RESEARCH.md` flow from `ResearchInput` through IC.net Brand/stock, five read-only price sources, RMB normalization, normal/fallback aggregation, the 13-column Excel snapshot, and `ResearchResult` while preserving inquiry idempotency, crash/retry safety, and security boundaries.

## Current Facts

- Canonical baseline: `origin/main` at `ac0ba1487a0edbb166c923dfcde9e5f55ba4597a`.
- The original local `main` was dirty and diverged; this Task runs in an isolated worktree on `codex/research-006-five-source-v1`.
- CEO Architecture Gate is complete; the canonical module contract may be implemented without changing cross-module contracts.
- Research must not import `sheets`, `workflow`, `inso`, or `quotation`.

## Required Context

- `docs/AI_START_HERE.md`
- `docs/AI_TEAM.md`
- `docs/TASK_PROTOCOL.md`
- `docs/modules/RESEARCH.md`
- `docs/MODULE_INDEX.md`
- `docs/BOUNDARIES.md`
- `docs/PRODUCT_BASELINE.md`
- Current `src/research/` and `tests/research/`

## Write Scope

- `src/research/**`
- `tests/research/**`
- This Task Packet
- `docs/modules/RESEARCH.md` only for a minimal implementation-driven clarification if needed

## Scope

- IC.net Brand/stock behavior with strict MPN matching.
- Findchips, HQEW, LCSC, Bom.Ai, and read-only INSO adapters.
- Suffix MPN matching, natural-month windows, USD/RMB conversion, stocked/out-of-stock pools, five-source status aggregation, 20% rule, source display values, deterministic Excel migration/full-snapshot idempotency, and safety regression tests.
- Bounded read-only smoke, self-review, commit, and Task branch push.

## Non-scope

- Active INSO procurement or any external write.
- Workflow scheduling/downstream behavior, Sheets, Quotation, or changes to other modules/global canonical files.
- New shared infrastructure or public cross-module contracts.

## Acceptance

- [x] Canonical five-source Research behavior is implemented with deterministic tests.
- [x] IC.net strict MPN and Brand/stock behavior does not regress.
- [x] Suffix matching and natural-month clamp boundaries are covered.
- [x] Normal/fallback pools, statuses, remarks, and 20% rule are correct.
- [x] Excel has exactly 13 visible columns plus hidden `_inquiry_id`, safe known-schema migration, atomic full-snapshot upsert, and fail-closed behavior.
- [x] No forbidden imports or secret/customer procurement data.
- [x] Research tests, full tests, Ruff, compileall, diff-check, and bounded read-only smoke are reported.
- [x] Changes are self-reviewed and prepared for commit/push without merging.

## Execution

Run diagnosis → implementation → tests/fix → bounded read-only smoke → self-review → Task cleanup → commit → push. Stop only at the Task Protocol escalation boundaries.

## Final Report

Implemented the canonical five-source Research V1 contract within the Research module. The source model now separates normal and out-of-stock candidates, applies exact/short-suffix MPN matching and natural-month windows, normalizes supported USD prices through the shared Research FX boundary, and adds the INSO read-only 1/2/3-month history adapter without importing the future INSO module.

Aggregation now implements all SUCCESS/PARTIAL/RETRYABLE/MANUAL paths, deterministic technical remarks, normal/fallback 20% comparison, and correct source-cell display. Excel now writes the exact 13 visible columns plus hidden identity, safely migrates known prior schemas, replaces full snapshots idempotently, and fails closed for corrupt, ambiguous, duplicate, or unsavable workbooks.

Verification:

- Research tests: 148 passed.
- Full tests: 173 passed.
- Ruff: passed.
- compileall: passed.
- diff-check: passed.
- Forbidden dependency and plaintext-secret pattern scans: no matches.
- Read-only live smoke: ECB positive/finite quote and Findchips result structure succeeded. HQEW attach-only loopback CDP returned `BROWSER_FAILURE`; LCSC public search-page attempt returned `NEXT_DATA_MISSING`. Bom.Ai and INSO authenticated live reads were not attempted because the canonical language-neutral/Python Credential Provider remains `UNKNOWN`; no authentication challenge was bypassed and no sensitive value was emitted.

Remaining non-blocking runtime UNKNOWN: authenticated browser capability/credentials for Bom.Ai and INSO, an open authenticated HQEW CDP target, and a live LCSC product URL resolver are deployment inputs outside this Task's approved module-local implementation.
