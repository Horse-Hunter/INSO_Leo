# Task: RESEARCH-007 — V1 Five-Source Production Runtime Prerequisite

status: complete
actor_role: Research Module Codex
executor_tool: OTHER # CodeBuddy
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

- Canonical `origin/main` HEAD for this Task is
  `73520c170f12a5c5054211c3e6f38da119ad3fbf`, which contains the Core Python
  Credential Provider public surface (`from src.core import get_login`).
- The original blocked Task record was committed as
  `abe1ad4614e46a4cdd57e01822a1bf439f662943` and contains only this Task Packet.
  It was cherry-picked to recover the Task Packet; no blocked content was
  discarded.
- This execution is an executor switch (`CODEX` → `OTHER # CodeBuddy`) of the
  same Task, not a new business Task.
- `docs/modules/CORE.md` states that business modules must not depend on DPAPI,
  vault paths, PowerShell, or other Credential Provider implementation details.
- `docs/BOUNDARIES.md` allows read-only Research access but forbids secret
  disclosure and security-challenge bypass.
- Sanitized local readiness inspection (original blocked execution) found the
  external vault present, five metadata entries, two of the three Research
  credential site IDs configured, Playwright installed, no `runtime/`
  configuration directory, and no listener on the loopback CDP port.
- Sanitized local readiness inspection (this execution, via the canonical Core
  Provider only) found: `ic.net.cn` credential available; `bom.ai` credential
  configured in the vault but NOT retrievable through the Provider; `inso`
  credential not configured; no listener on `http://127.0.0.1:9222`.
- The `bom.ai` Provider failure is a Core-owned defect, not a Research
  dependency on Core internals: `src/core/_vault_backend.py` calls
  `subprocess.run(..., text=True)` without an explicit `encoding`, so the
  redirected Windows PowerShell output is decoded with the locale codec (GBK on
  this host) while `powershell.exe` actually emits UTF-8 bytes. The reader thread
  raises `UnicodeDecodeError`, `stdout` becomes `None`, and the Provider surfaces
  `AttributeError: 'NoneType' object has no attribute 'strip'` instead of a typed
  `CredentialError`. Reproduced generically without any credential payload.
- No site URL, username, password, token, cookie, customer value, order value, or
  MPN was printed or persisted by any inspection or smoke in this execution.

## Owner Decisions

- The previous blocker — "no canonical Python Credential Provider" — is
  RESOLVED by Core PR #8 (`73520c170f12a5c5054211c3e6f38da119ad3fbf`). Research
  now consumes credentials exclusively through
  `from src.core import get_login` / `CredentialProvider` /
  `CredentialError`, and the blocker is closed. No architecture change was
  required for Research.
- Research does NOT call PowerShell, read DPAPI, read a vault path, parse
  `credential-vault.json`, or create a second credential store.

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

- [x] `ResearchService` can be composed from explicit Git-ignored runtime
  configuration for IC.net and all five price sources.
- [x] Every missing source prerequisite produces an observable fail-closed
  result.
- [x] A deterministic test proves every canonical source is called.
- [x] Bom.Ai has a concrete production read-only browser acquisition.
- [x] INSO consumes a canonical Python Credential Provider binding plus explicit
  production URL/selectors.
- [x] Excel remains idempotent by `_inquiry_id`.
- [x] Research tests, full tests, Ruff, diff review, and secret scan pass.
- [x] A bounded read-only smoke is completed as far as available runtime inputs
  allow.

## Pending Owner Decision

- Provide the `inso` Site ID in Vault Manager (the only missing Research
  credential site).
- Provide the real, non-secret INSO and Bom.Ai runtime URL/selector values
  (`runtime/research.json`); Research never guesses DOM or URL contract.
- Start the Owner-authorized ordinary Chrome with loopback CDP enabled
  (`http://127.0.0.1:9222`) for the HQEW and IC.net-CDP read-only paths.
- Authorize a Core-owned fix for the `_vault_backend.py` output-encoding defect
  (`subprocess.run(..., text=True, encoding="utf-8")`), which currently blocks
  the `bom.ai` credential from being retrieved at all.

## Execution

- Recovered the Task Packet by cherry-picking
  `abe1ad4614e46a4cdd57e01822a1bf439f662943` onto
  `buddy/research-v1-production-runtime` from `origin/main`
  (`73520c170f12a5c5054211c3e6f38da119ad3fbf`). The cherry-pick was clean; no
  content was discarded.
- Added `src/research/credentials.py`: the single Research-owned binding to the
  canonical Core Provider, with fail-closed translation into each Research
  native login object and a non-secret per-site readiness report.
- Added `BomAiBrowserConfig` and `PlaywrightBomAiAuthenticatedBrowser` in
  `src/research/bom_ai.py`: concrete credential-injected, read-only Bom.Ai
  acquisition with HTTPS/host pinning, challenge rejection, and no write
  capability.
- Added `src/research/runtime.py`: validated Git-ignored non-secret runtime
  configuration, an IC.net acquisition-mode selector, readiness assessment for
  credentials and the authorized CDP endpoint, full `ResearchService`
  composition, and fail-closed `build_production_research_service`.
- Preserved the existing Findchips and LCSC production paths unchanged.

## Final Report

status: complete

changed: `src/research/credentials.py` (new), `src/research/runtime.py` (new),
`src/research/bom_ai.py`, `src/research/__init__.py`, `src/research/README.md`,
`tests/research/test_credentials.py` (new),
`tests/research/test_bom_ai_browser.py` (new),
`tests/research/test_runtime.py` (new), and this Task Packet.

verified: 266 deterministic tests pass for the whole Repo, of which 180 are in
`tests/research` (26 newly added). Ruff clean over the whole Repo. `compileall`
clean. Secret scan over `src/` and `tests/` found no private keys, tokens, bearer
values, emails, or vault paths; the only matches are Core-owned files and
explicit Research "must never touch" prohibitions. Git diff reviewed; no secret,
credential, cookie, customer value, or real MPN is present.
Runtime composition smoke: `ResearchService` composed from runtime configuration
and executed; Findchips and LCSC returned live read-only `SUCCESS`, while HQEW,
IC.net (CDP mode), Bom.Ai, and INSO returned observable `SOURCE_UNAVAILABLE` with
`BROWSER_FAILURE` / `CREDENTIALS_UNAVAILABLE`. Excel snapshot written with the
canonical 14 columns and `_inquiry_id`. `build_production_research_service` on the
current host failed closed with `ResearchRuntimePrerequisiteError`.
Bounded read-only smoke: IC.net credential path reached the correct result URL
but IC.net served an empty 121-byte document with no CAPTCHA and no interactive
challenge, so Research failed closed with `RESULT_PAGE_BLOCKED`; no bypass was
attempted.

limitations: Live end-to-end five-source runtime smoke is not yet reachable.
`inso` credential site is unconfigured, the `bom.ai` credential is unreadable
because of the Core encoding defect, the authorized CDP endpoint is not running,
and the real INSO/Bom.Ai URL/selector runtime configuration has not been supplied
by the Owner. Research fails closed observably on each of these.
