# Task: RESEARCH-007 — V1 Five-Source Production Runtime Prerequisite

status: blocked
actor_role: Research Module Codex
executor_tool: CODEX
module: research
reports_to: Research Module Chat
execution_mode: FAST_V1
architecture_impact: NONE

## Problem

Workflow V1 live smoke cannot construct the production Research runtime from the
current approved inputs. Bom.Ai has only an injected authenticated-browser
protocol, INSO has no canonical Python Credential Provider binding or local
production URL/selector configuration, and the authenticated local CDP endpoint
used by HQEW is not running.

## Goal

Add the smallest Research-owned production composition, adapters, configuration
loading, and fail-closed startup checks needed to construct `ResearchService`
for IC.net plus the five canonical price sources without changing
`ResearchInput` or `ResearchResult`.

## Current Facts

- `origin/main` at `ce265c5` contains the canonical Workflow V1 and five-source
  Research implementation.
- `docs/modules/CORE.md` states that business modules must not depend on DPAPI,
  vault paths, PowerShell, or other Credential Provider implementation details.
- The same Core contract states that a language-neutral or Python application
  Credential Provider API is `UNKNOWN`.
- Core currently exposes only the PowerShell `Get-InsoVaultLogin` capability.
- A Research-owned Python bridge would therefore depend on forbidden Core
  implementation details and change or bypass the Core Credential Contract.
- Sanitized local readiness inspection found the external vault present, five
  metadata entries, two of the three Research credential site IDs configured,
  Playwright installed, no `runtime/` configuration directory, and no listener
  on the loopback CDP port. No site URL, username, password, token, cookie,
  customer value, order value, or MPN was printed or persisted.
- `docs/BOUNDARIES.md` allows read-only Research access but forbids secret
  disclosure and security-challenge bypass.

## Required Context

- `docs/AI_START_HERE.md`
- `docs/TASK_PROTOCOL.md`
- `docs/BOUNDARIES.md`
- `docs/MODULE_INDEX.md`
- `docs/PRODUCT_BASELINE.md`
- `docs/modules/CORE.md`
- `docs/modules/RESEARCH.md`
- `docs/modules/WORKFLOW.md`
- `tasks/2026-09-24-research-006-five-source-v1.md`
- Current `src/research/**`, `tests/research/**`, and Core Credential Provider
  public capability

## Write Scope

- `src/research/**`
- `tests/research/**`
- This Task Packet

## Scope

- Research-owned runtime composition, concrete read-only acquisition adapters,
  Git-ignored non-secret configuration loading, and fail-closed readiness.
- Consumption of an existing canonical Core Credential Provider capability.
- Bounded, authorized, read-only smoke without recording real business values.

## Non-scope

- Core implementation or Credential Provider contract changes.
- Public Research or Workflow contract changes.
- Credential-vault duplication in Research.
- CAPTCHA, OTP, device-verification bypass, external writes, procurement,
  messages, orders, or production-data changes.

## Requirements

- Preserve canonical `ResearchInput` and `ResearchResult`.
- Never print, persist, or commit credentials, cookies, tokens, customer data,
  order content, or actual MPNs.
- Stop and escalate if safe binding requires a Core Credential Contract change.
- Missing source configuration must be observable and fail closed.
- Preserve inquiry-idempotent Excel output.

## Acceptance

- [ ] `ResearchService` can be composed from explicit Git-ignored runtime
  configuration for IC.net and all five price sources.
- [ ] Every missing source prerequisite produces an observable fail-closed
  result.
- [ ] A deterministic test proves every canonical source is called.
- [ ] Bom.Ai has a concrete production read-only browser acquisition.
- [ ] INSO consumes a canonical Python Credential Provider binding plus explicit
  production URL/selectors.
- [ ] Excel remains idempotent by `_inquiry_id`.
- [ ] Research tests, full tests, Ruff, diff review, and secret scan pass.
- [ ] A bounded read-only smoke is completed as far as available runtime inputs
  allow.

## Pending Owner Decision

Authorize a separate Core-owned, architecture-gated Task to define and implement
the canonical Python application Credential Provider API. After that capability
lands, resume this Research Task to consume it without knowing PowerShell, DPAPI,
or vault storage details.

## Execution

Execution stopped before Research implementation because the required canonical
Python Credential Provider capability does not exist. Per the Task instruction,
Research did not copy or wrap the PowerShell vault implementation. Only this
blocked Task record may be committed and pushed.

## Final Report

status: blocked

changed: Added this Task Packet with the verified cross-module blocker and
sanitized runtime readiness evidence.

verified: Canonical boundaries, existing source adapters, current Core provider,
Git state, local credential coverage counts, Playwright presence, runtime-config
presence, and loopback CDP readiness were inspected without exposing sensitive
values.

limitations: Production composition cannot safely retrieve IC.net, Bom.Ai, and
INSO credentials until Core owns a canonical Python application provider API.
Bom.Ai concrete browser wiring and Research runtime composition remain pending
behind that architecture prerequisite.
