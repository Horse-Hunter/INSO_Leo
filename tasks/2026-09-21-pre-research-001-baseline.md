# Task: Synchronize pre-RESEARCH-001 baseline

status: complete
owner: Codex
created: 2026-09-21
updated: 2026-09-21

## problem

The baseline still excludes `importance_raw` from ResearchInput and does not fully record the formal Bom.Ai/no-match decision or the latest module-autonomy operating model.

## goal

Synchronize the final pre-RESEARCH-001 cross-module contract and AI operating model without implementing Research or changing module architecture.

## current_facts

- `importance_raw` is a Sheet-C raw value passed unchanged through Workflow for Excel display only.
- NO_MATCHING_PRODUCT requires successful no-match results from all four price sources and maps to MANUAL_REVIEW_REQUIRED.
- Bom.Ai product existence is distinct from price freshness or availability.
- Module Chats operate autonomously and escalate only specified architecture-level matters.
- Pre-existing uncommitted Vault, code, Task, and reference-document work is outside this task.

## scope

- Update Research, Workflow, Product Baseline, and AI Team documentation.
- Record and verify this task.

## non_scope

- RESEARCH-001 implementation, business code, Vault, credentials, new modules, architecture expansion, or pre-existing worktree files.
- Changes to Module Index, Sheets, or AI Start Here unless a direct conflict is found.

## requirements

- Record the canonical ResearchInput and strict display-only importance rule.
- Record the formal Bom.Ai/no-match status and reason-code semantics.
- Add the concise module-autonomy and necessary-escalation rule without rewriting existing collaboration guidance.
- Commit and push only this task's five files.

## acceptance

- [x] ResearchInput includes `importance_raw` and its A/B display mapping.
- [x] The non-influence list prevents importance from changing Research behavior.
- [x] NO_MATCHING_PRODUCT requires four successful strict-no-match source results.
- [x] Bom.Ai strict product match is distinct from price age or availability.
- [x] AI module autonomy and escalation triggers are explicit.
- [x] Protected documents, business code, credentials, and Vault remain unchanged.

## verification

- Check all confirmed contract, no-match, and AI operating-model statements.
- Confirm protected files have no task-local diff.
- Run scoped `git diff --check` and review the complete scoped diff.
- Verify staged and committed file scope before pushing.

## completion

- status: complete
- changed: Research, Workflow, Product Baseline, and AI Team documentation plus this Task Packet
- verified: cross-document contract checks, protected-file scope check, sensitive-assignment scan, scoped diff review, and `git diff --check`
- limitations: implementation and remaining schema details stay `UNKNOWN`
