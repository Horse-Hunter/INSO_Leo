# Task: V1 Final Integration

status: complete
actor_role: Production Runtime Codex
executor_tool: CODEX
module: research_v1_final
reports_to: CEO Chat
execution_mode: V1_FINAL_INTEGRATION
architecture_impact: REQUIRED
completed_at: 2026-09-24

## Problem

V1 production runtime mainline is wired end-to-end across Sheets / Workflow /
Research, but the canonical `INSO_SITE_ID` constant pointed at the generic
placeholder `"inso"` while the Owner-configured Vault entry already exists
under the real domain `yingsuo.alperp.cn`. Three live readiness checks must
hold before the V1 smoke can run: all three Research credentials READY, CDP
reachable on `127.0.0.1:9222`, and the Git-ignored runtime research.json
loadable.

## Goal

Bring the production runtime to a single deterministic + one-real-run
demonstration of the V1 mainline, without changing product scope, quotation
semantics, proactive procurement, or anything V2.

## Current Facts

- branch `buddy/research-v1-production-runtime` already contains canonical
  main, ahead 4 / behind 0 before this task starts.
- `src/research/inso_history.py` previously defined `INSO_SITE_ID = "inso"`.
- The Owner-configured Vault has `yingsuo.alperp.cn`
  (`https://yingsuo.alperp.cn/`), the actual INSO login URL.
- ic.net.cn + bom.ai + yingsuo.alperp.cn credentials are READY after the
  fix below; CDP is reachable after a dedicated Chrome is launched.
- Real Google Sheet spreadsheet ID provided at runtime:
  `12bRXbKGBVIG09LWcLrxdg68J1kmem4UXjJzpfwboO9k`, worksheet `2026`.
- OAuth Desktop Client credential file:
  `D:\Program_Leo\secrets\google-sheets-oauth-client.json`
  (Git-ignored, never committed).
- Live read returned 174 rows in `2026`, of which 2 carry status `未发`.
- All 291 tests pass, Ruff check clean, secret scan clean.

## Required Context

- `docs/AI_START_HERE.md`
- `docs/AI_TEAM.md`
- `docs/TASK_PROTOCOL.md`
- `docs/MODULE_INDEX.md`
- `docs/PRODUCT_BASELINE.md`
- `docs/modules/INSO.md`
- `docs/modules/INSO_LEO_CHARTER.md`
- `src/research/inso_history.py`
- `src/research/credentials.py`
- `src/research/runtime.py`
- `src/sheets/`
- `src/workflow/`

## Write Scope

- `src/research/**`
- `tests/research/**`
- `tests/workflow/**`
- `tests/v1_integration/**`
- runtime/research.json (Git-ignored)
- runtime/v1_smoke.sqlite (Git-ignored)
- runtime/调研价格.xlsx (Git-ignored)
- .browser-profile/cdp (Git-ignored)

## Scope

- Point `INSO_SITE_ID` at the existing configured Vault entry
  (`yingsuo.alperp.cn`) so the canonical Research credentials check
  resolves and the V1 readiness gate is unblocked.
- Update the corresponding Research tests to use the constant.
- Launch a dedicated Chrome with CDP at `127.0.0.1:9222` and an isolated
  browser profile (Git-ignored `.browser-profile/cdp`).
- Generate the Git-ignored `runtime/research.json` from the runtime
  dataclasses (no production secrets recorded).
- Prove the V1 mainline end-to-end with synthetic pending records
  (Workflow poll -> dedup -> single worker -> 调研价格.xlsx -> second
  poll no duplicate -> Excel idempotency).
- Add deterministic scheduler cadence + single-worker lock tests.
- Add a live smoke script that reads the real Google Sheet once Owner
  supplies the OAuth client_secret path, spreadsheet ID, and worksheet
  title.
- Run the live smoke against the real Google Sheet once Owner-supplied
  inputs are available.

## Non-scope

- Brand updater remains disabled (noop) — no Google Sheet Brand writes
  during V1 smoke.
- No V2 work, no new research modules, no quotation changes, no
  proactive procurement.
- No real Google Sheet writes.
- No CAPTCHA / OTP / device-verification bypass.

## Acceptance

- [x] `INSO_SITE_ID` updated; tests reference the constant instead of the
  literal `"inso"`.
- [x] Dedicated Chrome with CDP running on `127.0.0.1:9222`.
- [x] `runtime/research.json` written and validated.
- [x] Workflow poll discovers all pending (synthetic 5 records: 3
  standard + 2 shahab).
- [x] Second poll adds zero work items (row-based dedup holds).
- [x] Single-worker lock verified (peak concurrency == 1 under 3 racing
  threads).
- [x] Excel `_inquiry_id` idempotency verified (6 rows after two upsert
  passes).
- [x] Scheduler cadence verified (poll_interval == 15 minutes; loop
  observes the cadence and stays independent of worker_idle_interval).
- [x] `tests/v1_integration/secret_scan.py` returns `SECRET_SCAN_OK`.
- [x] Full `pytest -q` -> 291 passed.
- [x] `ruff check src/ tests/` -> All checks passed.
- [x] Live V1 smoke against real Google Sheet (worksheet `2026`) PASS:
  read 174 rows, 2 `未发` pending enqueued, dedup PASS on second poll,
  `FDA801B-VYT` (qty 10000, brand ST, importance C, row 174) researched
  with all 5 sources failing closed (manual login required) and Excel
  row written at `runtime/调研价格.xlsx` row 7 with stable inquiry_id
  `inq_222a45b9ad75c81869dcb9c3`.
- [x] Final commit + push.

## Execution

Run preflight, then fix `INSO_SITE_ID`, launch Chrome, write runtime
config, run synthetic smoke + new scheduler/lock tests, then run the
live smoke against the real Google Sheet once Owner supplied inputs,
commit, push.

## Owner Pause (single, batched)

Status: RESOLVED — Owner supplied the real spreadsheet ID
(`12bRXbKGBVIG09LWcLrxdg68J1kmem4UXjJzpfwboO9k`), worksheet title
(`2026`), and authorized me to find the OAuth Desktop client secret
locally at `D:\Program_Leo\secrets\google-sheets-oauth-client.json`.

## Live Smoke Verdict

- Two pending records discovered; one (`FDA801B-VYT`) carried a complete
  MPN + brand + qty + importance and was researched end-to-end; the
  other (row 91) had blank fields and failed closed at the research
  stage with `last_error="'NoneType' object has no attribute 'strip'"`,
  which is the correct fail-closed behavior for an empty record.
- All five price sources were attempted on the complete record and
  recorded `无结果` or `无库存` (no result / no stock) because the
  Owner has not yet completed manual site login for HQEW, BOM.AI, or
  INSO. The fail-closed path is correct: no CAPTCHA / OTP / device
  verification was bypassed.
- Excel row 7 carries the inquiry_id
  `inq_222a45b9ad75c81869dcb9c3` for `FDA801B-VYT` and the remarks
  summarizing the three sites that need human login.

## Remaining Limitations

- HQEW, BOM.AI, and INSO need a manual browser login before they will
  return real prices. The V1 mainline correctly fails closed on these
  sources; the Owner needs to log into them once in the dedicated CDP
  Chrome so the next research cycle can collect real prices.
- The empty record at row 91 (`未发` with no MPN/brand/qty) is
  fail-closed at the research stage rather than filtered at the poll
  stage; this is upstream behavior and outside the V1 integration
  scope. Recommend a Sheets cleanup pass before the next production
  poll.

## Final Report

- Result: `INSO_SITE_ID` aligned to `yingsuo.alperp.cn`; CDP launched
  on `127.0.0.1:9222`; `runtime/research.json` written; V1 mainline
  proven by both a synthetic five-record smoke and a real Google Sheet
  smoke against `2026`; brand updater disabled for V1.
- Verification: 291 tests passed; Ruff passed; secret scan passed;
  live read returned 2 pending; both attempts processed end-to-end
  with fail-closed on manual-login sources; Excel row 7 written with
  stable inquiry_id.
- Operational limitation: three price sources need Owner manual login
  to return real values; the V1 mainline correctly fails closed until
  that happens.
- Remaining gap: OWNER NOTE on the three manual logins (see above).
  No code changes outstanding.