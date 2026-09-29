# RFQ-002 — V1.2 runnable Windows release closeout

**Status source:** `control-room/COORDINATION.md`  
**Review:** REQUIRED  
**Branch:** `feature/v1-2`

## Business goal

Turn the already-built V1.2 capability into a real runnable production candidate that the Owner can test with live data first, then package as a Windows V1.2 release only after the Owner explicitly confirms the live test passed.

This RFQ is release/integration closeout, not a new feature project. Delivery sequence is mandatory: Phase A = run the source production candidate for Owner live-data testing; Phase B = package only after Owner explicitly says the live test passed and authorizes packaging.

## Current gap

RFQ-001 closed the pre-save live acceptance, but the current Windows release path is still the V1.1 release path:

- packaging, executable naming and release docs still identify V1.1;
- the default production launcher does not automatically activate the V1.2 production flow;
- V1.2 persistence/runtime readiness is not yet proven from a clean packaged-start path;
- there is no V1.2 packaged smoke evidence proving that the real release entry point reaches the safe V1.2 workflow.

Therefore V1.2 is not yet ready to hand to Owner as a packaged runnable release.

## Required outcome

Phase A must first make the normal source production entry run V1.2 by default so the Owner can immediately test live data without silent V1.1-only fallback. Phase B packaging starts only after explicit Owner approval.

A safe release-candidate run must be able to reach the V1.2 workflow through the current allowed boundary:

Sheets/read → Research → duplicate/business-rule evaluation → V1.2 state/GUI → safe purchase-draft preparation/read-back where applicable.

Owner explicitly authorizes real SMTP only for canonical V1.2 notification testing in Phase A. No real INSO Save, Save-and-Send, other INSO Send, or Sheets write is authorized.

## Scope

1. Phase A: make the normal source production entry activate the existing V1.2 production workflow without test-only/manual dependency injection.
2. Complete the minimum production composition needed for the existing V1.2 modules to run from the packaged application.
3. Ensure V1.2 persistence is initialized/migrated through the approved additive/backup-safe path and does not require a pre-handcrafted database.
4. Phase A: prove the real source production entry reaches the complete V1.2 Owner-test checkpoint. Phase B only after Owner approval: create a V1.2 Windows release artifact/path clearly separate from V1.1.
5. Phase B only after Owner approval: update Windows release documentation and user-facing version identity to V1.2.
6. Phase A: prove real SMTP notification behavior for important-order and duplicate-order rules under the explicit SMTP test authorization. Phase B: prove the packaged V1.2 smoke path.
7. Run focused integration/release tests, full regression, Ruff and diff check.
8. Record execution facts in `EXECUTION_LOG.md`, produce `FINAL_REPORT.md`, and set status to `REVIEW_REQUIRED`.

## Acceptance

- V1.1 release anchor remains unchanged and recoverable.
- Before packaging, the source production candidate reaches the full V1.2 path and is ready for Owner live-data testing. Packaging is not started until Owner explicitly approves Phase B.
- After Phase B authorization, a V1.2 Windows artifact can be built successfully and passes frozen self-check/artifact safety scan.
- The produced executable/release directory is identified as V1.2, not V1.1.
- Launching the V1.2 production artifact uses the V1.2 workflow path by default; it must not silently run V1.1-only processing because V1.2 production adapters were omitted.
- A clean/approved runtime can initialize or migrate V1.2 persistence through the canonical safe migration path; no destructive schema rewrite.
- Packaged smoke evidence proves the real V1.2 entry reaches V1.2 state/flow and does not merely import V1.2 code.
- Existing business rules from `docs/PRODUCT_BASELINE.md` and `docs/V1_2_ARCHITECTURE.md` are preserved; no new business rules are invented.
- GUI can surface V1.2 business state from the same packaged production run.
- Missing/invalid V1.2 production dependencies fail closed and visibly; no silent downgrade to V1.1-only behavior.
- Repository-visible sanitized evidence is sufficient for independent CEO Review and contains no credentials, cookies, business values, raw page dumps or sensitive record identifiers.
- Full regression: PASS.
- Ruff: PASS.
- `git diff --check`: PASS.
- Build/release smoke: PASS.
- REAL SAVE: NO.
- REAL SAVE-AND-SEND: NO.
- REAL SEND: NO.
- REAL SMTP: YES, only for canonical V1.2 notification testing explicitly authorized by Owner.
- SHEETS WRITE: NO.
- Production Write Gate: CLOSED.
- Implementation + Control Room records committed and pushed.
- RFQ status: `REVIEW_REQUIRED`.

## Non-goals

- Do not open Production Write Gate.
- Do not perform real INSO Save / Save-and-Send / Send.
- Do not send real email except the Owner-authorized canonical V1.2 SMTP notification tests.
- Do not write Google Sheets.
- Do not redesign V1.2 business rules.
- Do not add unrelated frameworks or refactor V1.1.
- Do not merge/release to main in this RFQ.

## Canonical sources

- `AI_START_HERE.md`
- `docs/PROJECT_BASELINE.md`
- `docs/PRODUCT_BASELINE.md`
- `docs/V1_2_ARCHITECTURE.md`
- `docs/WINDOWS_RELEASE.md`
- `docs/SAFETY.md`
- `docs/MODULE_INDEX.md`
- `control-room/RFQ-001/REVIEW.md`

## Safety

Production Write Gate remains **CLOSED** for INSO writes and Sheets writes. Owner explicitly authorizes real SMTP only for canonical V1.2 notification testing; this does not authorize any INSO Save/Send or Sheets write.
