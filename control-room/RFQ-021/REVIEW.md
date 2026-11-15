# RFQ-021 — CEO Independent Review (R3, 2026-11-15)

**CEO verdict: `CHANGES_REQUESTED / RELEASE_HOLD / NOT_DEPLOYED`.** This is the independent CEO decision. Executor's `REVIEW_R3.md` is an implementation/evidence report, **not** the final CEO approval. No deployment, old-program restart, real orders or branch promotion is authorized.

## Fixed evidence under review

- Source fix: `1ef20c8123b08f40871bcfa51ba3d1b54a3451e9`; Executor branch HEAD at review: `a577e94ded8f4cb94b16e9bb8176079529dbcdb3` (later documentation-only commits must not be substituted for candidate source).
- Executor-reported R3 candidate: `INSO_V1.6.exe` SHA256 `faa3166d41db5a738348dc57f6adebbfcda0b3dbf29eb99f3549cf0d0d2596c1`, 8,459,010 B, 2,872 files. CEO independently recalculated the GitHub manifest SHA256 `accd463a78c23d5739d298a0ea6d2735ab1f51af051aad13900697ca406455ae` and confirmed the EXE manifest entry, **not** actual staging EXE bytes or Windows self-check.
- JUnit `docs/evidence/rfq021/pytest-report-r3.xml`: 4,248 collected / 4,245 passed / 2 failed / 1 skipped. Existing baseline-failure attribution is Executor evidence, not an independently rerun baseline.
- Accepted narrowly: `PurchaseCompletionActions` scope filter; backend refusal of `start_login_all_sites` in controlled mode; module/write-target checks on manual actions. This does **not** establish end-to-end B5 isolation.

## Material blockers — resolve together in R4

1. **P0/B5 — out-of-scope local business effects in V12 coordinator**. In `src/workflow/v12_flow.py`, `V12WorkflowCoordinator.initialize_run_state()` (around lines 280–324) loops over `all_items()` and may `mark_interrupted` / `_set_state` for any historical order; `discover_pending()` (around lines 383–453) loops over `all_items()` and may mark `HUMAN_COMPLETED` or `INVALID_INPUT_SKIPPED`, append events and `recover_stale_alerts`. Both occur **before** `prepare_pending()` filters by `_inquiry_ids`. The R3 tests cover `PurchaseCompletionActions`, not these earlier mutations. Add scope filtering ahead of each mutating branch; preserve legacy unscoped behavior; add negative integration tests with out-of-scope historical orders whose mutation preconditions are satisfied.
2. **P0/B3 — incomplete rollback-snapshot admission**. `scripts/install_release_candidate.ps1` verifies only files **listed by** `PROGRAM-MANIFEST.sha256` and permits a manifest with ≥2 lines, without proving the old EXE, full `_internal`, mandatory config and expected old-build identity are complete. Its junction guard checks `runtime` only **if it exists**, so missing junction can pass. Before any target changes, require completeness/identity, exact junction target, verified backup proof and fail-closed negatives for missing/partial snapshot or junction. Do not mistake an operator acknowledgement and SQLite magic header for independently verified DB integrity.
3. **P1 UI consistency**: `order_action_hint()` does not apply `_action_in_scope()`; it may advertise an action the backend later rejects. Align the hint with the execution guard without weakening backend refusal.

## R4 scope and acceptance

- Reuse the one existing Executor branch/worktree; first inspect remote HEAD, local status/diff and active RFQ evidence. Use `develop/AGENTS.md` Lean Review protocol: **one complete bounded effect-path audit** (startup, background, manual, local DB/event/alert, external writes, installer/rollback), one consolidated failure list, targeted regression during development.
- Demonstrate that a controlled run touches **no out-of-scope order state/events/alerts or external target**, including restart/initialization and polling; include negative tests for the branches listed above. Preserve existing UNKNOWN/hold and legacy unscoped behavior.
- After **source freeze**, run affected tests and one full suite; freeze/build/hash/scan one final candidate. Any subsequent source change invalidates that candidate. Record nodeids and source SHA without hiding failures.
- Update the existing `EXECUTION_LOG.md`, `INSTALL_AND_ROLLBACK.md`, compact evidence links and handover. Submit for a new independent CEO Review. Source PASS, build PASS and real-business permission remain separate.

## Incident and unverified production gates

`INCIDENT-20261115`: `SSLEOFError` → `SHEETS_READ_UNAVAILABLE` → `MODULE_PAUSED` is the confirmed fault class, not a proved underlying network cause. Executor's last 10:40 local inspection is not continuously live proof. Old installed EXE `e9e3da33…` lineage remains unverified. B3 consistent full rollback snapshot and B4 clean stop are unfulfilled; no verified live installation or real scoped trial exists. Preserve 221 SAVED, SHAHAB/115 and three V13 holds; never replay or clear UNKNOWN.

**Prohibited until separately authorized by Owner:** stop/restart or install the production program, production SQLite/Chrome9222 changes, Google/INSO/SMTP effects, real order actions, merge to `develop`, or promote `main`/`release/previous`. This documentation commit alone authorizes none of these.
