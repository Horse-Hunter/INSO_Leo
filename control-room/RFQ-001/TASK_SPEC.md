# RFQ-001 — V1.2 pre-save live acceptance closeout

**Status source:** `control-room/COORDINATION.md`  
**Review:** REQUIRED  
**Branch:** `feature/v1-2`

## Business goal

Finish the remaining V1.2 pre-save acceptance so the implementation is independently reviewable without performing any real external write.

## Ideal change

The V1.2 path is live-verified through duplicate/history access, unsaved purchase-draft parent-field write/read-back, and read-only save reconciliation. The next step after this RFQ is an independent review, not more infrastructure rediscovery.

## Before this RFQ

Already implemented and tested:
- shared INSO runtime/session capability;
- exact history query and settlement;
- production `PlaywrightParentProductFields`;
- production `PlaywrightReadOnlySaveReconciler`;
- production composition fail-closed wiring;
- forbidden Save-and-Send / Send dispatch paths remain closed.

Remaining acceptance was the live unsaved parent-field/read-back and reconciliation-detail verification. Latest implementation also binds the purchase draft to the business inquiry frame.

## Scope

1. Verify the real unsaved inquiry parent frame exposes one actionable PartNo, Brand and Qty input.
2. Verify safe synthetic values can be written and immediately read back exactly without Save.
3. Verify the read-only reconciliation detail contract against a unique existing safe record: BillID/PENO and MPN/Brand/Qty read-back.
4. Fix only the implementation needed for those acceptance checks.
5. Run focused tests, full tests, Ruff and diff check.
6. Record runtime evidence references, test results, diff/commits and implementation decisions in `EXECUTION_LOG.md`.
7. Produce `FINAL_REPORT.md` and set status to `REVIEW_REQUIRED`.

## Acceptance

- Shared INSO runtime is reused; solved runtime infrastructure is not reimplemented.
- Parent unsaved live write/read-back: PASS.
- Read-only reconciliation detail contract: PASS.
- No path exists to `#btnSave2` or `#bcSend`.
- Full regression: PASS.
- Ruff: PASS.
- `git diff --check`: PASS.
- Runtime evidence contains no secret values.
- REAL SAVE: NO.
- REAL SEND: NO.
- REAL SMTP: NO.
- SHEETS WRITE: NO.
- Implementation + Control Room records committed and pushed.
- RFQ status: `REVIEW_REQUIRED`.

## Non-goals

- No real Save.
- No real mail or Sheets write.
- No unrelated refactor or new framework.
- No new business rules.

## Canonical sources

- `AI_START_HERE.md`
- `docs/MODULE_INDEX.md`
- `docs/modules/INSO.md`
- `docs/V1_2_ARCHITECTURE.md`
- `docs/SAFETY.md`

## Safety

Production Write Gate remains **CLOSED** for this RFQ.
