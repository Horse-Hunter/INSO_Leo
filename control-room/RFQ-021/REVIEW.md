# RFQ-021 — CEO Independent Review (R4, 2026-11-15 16:47+08:00)

**Verdict: `CHANGES_REQUESTED / RELEASE_HOLD / NOT_DEPLOYED`.** R4's requested coordinator scope fix and GUI hint fix are accepted **at source level**. The rollback/installer proof is improved but not yet sufficient for a release claim. **No authorization** to stop/restart production, install, execute real orders, touch live SQLite/CDP or promote branches.

## Fixed subject and independently checked evidence

- R4 source: `2ad471e7b3c0101f18f6edae05d77522c6f71d47` (predecessor source changes `557cde28`), Executor branch HEAD at this review `597dd07f95b1482a7399737c688c9d495db14b1d`. Source/code/manifest/JUnit were read directly from GitHub. No Windows bytes or production processes were directly inspected.
- Executor-reported candidate: EXE SHA256 `199181856ac1430af5aa0bd0af37b6bf45a1bf17272413583b2bb6e27e679d32`, 8,459,710 B, 2,872 files. CEO independently recalculated the **repository manifest** SHA256 `2de4df2f9f23fe56eea89633b25c46c941bbf9e7b35eae99bc855d2189c1e2e3`, checked 2,872 unique entries and the EXE entry; this is not a real staging-file rehash.
- JUnit XML: **4,260 total / 4,253 passed / 6 failed / 1 skipped**. R3 had 2 failures; R4 has 4 additional failures in existing launcher tests. Failure XML itself contains assertions/timing symptoms (`MODULE_PAUSED` versus `STOPPED`, missing expected events), **not** the underlying sqlite read-only exception. Executor's uniform `readonly database` attribution and 5/5 isolated reruns are evidence claims, but have not independently explained the four new full-run failures.
- R4 tests: 5 V12 out-of-scope-history tests, 5 auto-sweep tests, 2 GUI hint tests, plus offline script gate harness; none of the new Python cases failed in the recorded full run. Offline script reports 13 successful checks; **happy-path install was NOT_VERIFIED** because an actual INSO_V1.6 process was alive during the harness.

## Acceptance by change family

- **B5 scoped local mutation — SOURCE PASS:** `V12WorkflowCoordinator._in_scope()` now gates `initialize_run_state()` and `discover_pending()` **before** state/event/alert changes; `None` retains unscoped behavior. Negative tests include scoped and legacy cases.
- **P1 manual hint — PASS:** `order_action_hint()` now checks `_order_in_scope()` and `_action_in_scope()`.
- **B3 rollback — NOT YET PASS:** old EXE and complete `_internal` hashes, missing/misdirected runtime and SQLite integrity/report hash are better checked; the next section contains **remaining concrete safety gaps**.

## Consolidated blockers for a single bounded follow-up

1. **B3 / program+config rollback identity:** `backup_running_release.ps1` accepts arbitrary `-RuntimeConfigDir` and copies `production.json` / `research.json`; `install_release_candidate.ps1` only checks these two paths exist in the signed-by-self manifest, never compares their bytes to the **actual runtime junction's** live configuration. A stale or wrong config backup with valid self-hashes can pass. Bind backup source to the actual `runtime` target and verify *both* config files' hashes against current runtime before any switch. Add negative tests for stale/wrong config. The runtime gate currently checks only `ReparsePoint`, not explicitly `LinkType=Junction`, despite claiming junction-only.
2. **B3 / post-copy integrity:** after `Move-Item`/`Copy-Item`, the installer verifies the EXE hash but checks only the **count** of installed `_internal` files (lines 219–233). Same-count corrupt/mismatched DLL contents could yield `INSTALL_RESULT=PASS`. Compare every installed program file against the approved candidate manifest **after copy**, ignoring protected `runtime` and intentionally retained `.prev-` backup files. Add an offline post-copy corruption/mismatch negative test. Ensure incomplete copy / switch failure cannot be reported as a successful install; record a safe cold-recovery plan rather than auto-restart.
3. **B3 / current database identity:** `verify_database_backup.ps1` proves a supplied DB copy is structurally sound and binds a report to its bytes, but neither it nor the installer proves the backup was made from the **current stopped production ledger**, as opposed to an older valid file with the same schema. At the authorized maintenance window, bind the snapshot to live DB source path, quiescence evidence and business ledger invariants/recency; do not equate integrity with snapshot provenance. Add a stale-valid-backup refusal test where feasible without touching production.
4. **B5 / fail-closed entry consistency:** `_run_login_sweep()` currently refuses scope/preview only when `not check_only`; `check_only=True` still acquires protected Chrome and calls `_park_browser`. The currently identified automatic caller is gated by `_idle_login_tick`, so no actual scoped effect is proven, but the lower-level refusal is incomplete. Reject all `check_only` variants in preview/enforced scope; add a direct backend negative asserting no browser acquisition.
5. **Full-suite six failures:** preserve all original tests; diagnose the 4 additional full-suite failing nodeids and capture the actual source of `WORKFLOW_LEDGER_UNAVAILABLE` per failed case, using the smallest reproducible launcher test group and writable test temp path. Rerun the final full suite **once after source freeze**; do not treat isolated PASS as a full-suite PASS or claim the XML itself proved the SQLite cause.

## Release and handoff rules

- Use `develop/AGENTS.md` Lean Review. One consolidated source/installer patch, targeted regressions during development, one full suite and single new final build after freeze. Update the **existing** `EXECUTION_LOG.md` / installation evidence; preserve all prior failures/holds.
- B3 complete consistent program/config/current-DB rollback snapshot and B4 Owner-authorized clean Stop remain **NOT_VERIFIED** on the real Windows system. The 2026-11-15 TLS EOF fault is classified but its underlying cause remains unverified; the last old-process snapshot is time-bounded.
- No real purchase, Google/INSO/SMTP write, production SQLite/WAL/SHM modification/backup, Chrome9222 takeover, old EXE restart, install, merge to `develop`, or branch promotion is authorized by this Review. Preserve saved order 221, SHAHAB/115 and the existing V13 holds.

---

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
