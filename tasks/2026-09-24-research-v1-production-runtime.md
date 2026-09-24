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
  `e99f416714c08141fe69af35f49054e77f2df29e` (Core PR #9 UTF-8 fix landed);
  the previous canonical HEAD `73520c170f12a5c5054211c3e6f38da119ad3fbf` was
  the baseline before that fix.
- The original blocked Task record was committed as
  `abe1ad4614e46a4cdd57e01822a1bf439f662943` and contains only this Task Packet.
  It was cherry-picked to recover the Task Packet; no blocked content was
  discarded.
- This execution is an executor switch (`CODEX` → `OTHER # CodeBuddy`) of the
  same Task, not a new business Task.
- This resume merged `origin/main` into
  `buddy/research-v1-production-runtime` as commit
  `dc09c4c068c339d6462fa16114324d57166d93da` (no rebase, no reset, no clean, no
  stash; ort merge; no conflicts). No Research source files were modified by the
  merge.
- `docs/modules/CORE.md` states that business modules must not depend on DPAPI,
  vault paths, PowerShell, or other Credential Provider implementation details.
- `docs/BOUNDARIES.md` allows read-only Research access but forbids secret
  disclosure and security-challenge bypass.
- Sanitized local readiness inspection (original blocked execution) found the
  external vault present, five metadata entries, two of the three Research
  credential site IDs configured, Playwright installed, no `runtime/`
  configuration directory, and no listener on the loopback CDP port.
- Sanitized local readiness inspection after Core PR #9 (this resume, via the
  canonical Core Provider only) found: `ic.net.cn` credential READY;
  `bom.ai` credential READY; `inso` credential NOT READY
  (`CredentialSiteNotFoundError`); no listener on `http://127.0.0.1:9222`.
- The Core PR #9 fix (`src/core/_vault_backend.py` now decodes redirected
  PowerShell output as UTF-8) is the resolution of the previous "bom.ai Provider
  returns `AttributeError`" failure class; the `bom.ai` credential is now
  retrievable through the canonical Core Provider.
- Bounded read-only Bom.Ai recon (this resume, using the Core Provider only):
  the public Bom.Ai login host (`www.bom.ai`) is reachable and the `Login.url`
  is `https://www.bom.ai/`. The login page contains a challenge marker in the
  static HTML before any submission, so Research's established conservative
  fail-closed policy halts immediately with `INTERACTIVE_CHALLENGE_REQUIRED`. No
  credential value, no business data, no submission, and no challenge bypass
  was attempted. Owner manual login is required to capture the current Bom.Ai
  form selectors and the model-result URL pattern.
- No site URL, username, password, token, cookie, customer value, order value, or
  MPN was printed or persisted by any inspection or smoke in this execution.

## Owner Decisions

- The previous blocker — "no canonical Python Credential Provider" — is
  RESOLVED by Core PR #8 (`73520c170f12a5c5054211c3e6f38da119ad3fbf`). Research
  now consumes credentials exclusively through
  `from src.core import get_login` / `CredentialProvider` /
  `CredentialError`, and the blocker is closed. No architecture change was
  required for Research.
- The previous blocker — "Core `_vault_backend.py` output-encoding defect
  prevents `bom.ai` retrieval" — is RESOLVED by Core PR #9
  (`e99f416714c08141fe69af35f49054e77f2df29e`). The `bom.ai` Login is now
  retrievable through the canonical Core Provider.
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
- Perform one manual Bom.Ai login in the Owner-authorized Chrome, capture the
  current form selectors and the model-result URL pattern, and write them to
  the Git-ignored `runtime/research.json`. Research halts before login because
  the Bom.Ai login page already contains a challenge marker in the static HTML;
  Research never bypasses it. No credential value is requested from the Owner.
- Start the Owner-authorized ordinary Chrome with loopback CDP enabled
  (`http://127.0.0.1:9222`) for the HQEW and IC.net-CDP read-only paths.
- After the two prerequisites above are met, repeat the Workflow V1 live smoke
  to verify the full five-source end-to-end runtime. The code stage is complete
  but the live five-source runtime readiness is NOT yet DONE.

## Execution

- Recovered the Task Packet by cherry-picking
  `abe1ad4614e46a4cdd57e01822a1bf439f662943` onto
  `buddy/research-v1-production-runtime` from `origin/main`
  (`73520c170f12a5c5054211c3e6f38da119ad3fbf`). The cherry-pick was clean; no
  content was discarded.
- Merged Core PR #9 (`e99f416714c08141fe69af35f49054e77f2df29e`) into
  `buddy/research-v1-production-runtime` via `git merge --no-edit origin/main`
  (ort strategy, no conflicts). Brings the UTF-8 fix and its deterministic
  encoding tests into the branch. New HEAD: `dc09c4c068c339d6462fa16114324d57166d93da`.
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

status: complete (code stage; live five-source runtime readiness NOT yet DONE)

changed: `src/research/credentials.py` (new), `src/research/runtime.py` (new),
`src/research/bom_ai.py`, `src/research/__init__.py`, `src/research/README.md`,
`tests/research/test_credentials.py` (new),
`tests/research/test_bom_ai_browser.py` (new),
`tests/research/test_runtime.py` (new), and this Task Packet. The Core UTF-8 fix
(Core PR #9) was merged from `origin/main`; no Research source files were
modified by the merge.

verified: 283 deterministic tests pass for the whole Repo after the Core PR #9
merge (180 in `tests/research`, 26 newly added by RESEARCH-007, 17 newly added
by Core PR #9 for the UTF-8 fix). Ruff clean over the whole Repo. `compileall`
clean. Secret scan over `src/` and `tests/` found no private keys, tokens, bearer
values, emails, or vault paths; the only matches are Core-owned files and
explicit Research "must never touch" prohibitions. Git diff reviewed; no secret,
credential, cookie, customer value, or real MPN is present.
Post-merge credential readiness (via canonical Core Provider): `ic.net.cn` READY,
`bom.ai` READY, `inso` NOT READY (`CredentialSiteNotFoundError`); loopback CDP
NOT REACHABLE.
Runtime composition smoke (previous execution): Findchips and LCSC returned live
read-only `SUCCESS`; HQEW, IC.net (CDP mode), Bom.Ai, and INSO returned
observable `SOURCE_UNAVAILABLE`. Excel snapshot written with the canonical 14
columns and `_inquiry_id`.
Bounded read-only smokes: IC.net credential path reached the correct result URL
but IC.net served an empty 121-byte document with no CAPTCHA and no interactive
challenge (fail closed `RESULT_PAGE_BLOCKED`; no bypass attempted). Bom.Ai login
page (`www.bom.ai`) is reachable but contains a challenge marker in the static
HTML; Research halted before any submission with
`INTERACTIVE_CHALLENGE_REQUIRED` (no bypass attempted).

limitations: Live end-to-end five-source runtime smoke is not yet reachable.
`inso` credential site is unconfigured, the Bom.Ai login page is gated by a
challenge that Research will not bypass, the authorized CDP endpoint is not
running, and the real INSO/Bom.Ai URL/selector runtime configuration has not
been supplied by the Owner. Research fails closed observably on each of these.
The Core UTF-8 blocker (PR #9) is resolved and `bom.ai` Login is now retrievable.
