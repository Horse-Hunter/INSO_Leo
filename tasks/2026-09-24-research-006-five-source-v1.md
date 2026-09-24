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

状态：DONE

完成：
- Added a concrete Research-owned Playwright INSO read-only acquisition for credential-injected login, exact navigation through `1.业务询价 → 采购临时询价`, MPN query, and a table-scoped extraction of only date plus `供方未税价`; HTTPS/cross-host/challenge checks fail closed and no procurement-write capability exists.
- Replaced the incorrect international LCSC smoke path with the production Chinese path `so.szlcsc.com/global.html?k=<MPN> → item.szlcsc.com/<productId>.html`; search results are strict/suffix matched, unrelated variants are excluded, displayed price tiers are parsed, and product identity is verified again on the official item page.
- Removed the mixed-currency-unsafe legacy `select_bom_ai_price` implementation and its package-level export; `BomAiAdapter` remains the single V1 selection path and normalizes currencies before comparison.
- Added deterministic browser/parser/safety tests for both acquisitions and a public-API regression test for Bom.Ai.

验证：
- Research tests: PASS, 154 tests.
- Full tests: PASS, 179 tests.
- Ruff: PASS.
- compileall: PASS.
- diff-check: PASS.
- Live smoke: LCSC Chinese production path PASS for the Owner-confirmed MPN; official search resolved an official item page, identity validation passed, and a stocked `PriceCandidate` was formed. No price/session value was recorded. INSO live smoke remains runtime UNKNOWN because canonical Python Credential Provider integration, production URL/selectors, and an approved credential runtime are unavailable; no credential or procurement history was accessed.
- Forbidden dependency / sensitive-data scan: PASS; no Research import of Sheets/Workflow/INSO/Quotation and no credential, cookie, token, customer procurement history, or supplier detail added.

真实效果：
- Research V1 can now execute the LCSC Chinese-site read-only path end to end and has an executable, credential-injected INSO browser path that is limited to login, navigation, query, and reading date/`供方未税价` columns. Mixed RMB/USD Bom.Ai selection can no longer be entered through the unsafe legacy helper.

剩余：
- Non-blocking runtime prerequisite: INSO live verification requires the Owner-provided production URL/selectors and canonical Credential Provider binding. The implementation and deterministic safety coverage are complete without handling or persisting real runtime data.

Commit：Recorded in this Task branch history; exact hash is reported at handoff.

Push：NOT PUSHED

Branch：`codex/research-006-five-source-v1`

PR：NONE

需要决定：NONE
