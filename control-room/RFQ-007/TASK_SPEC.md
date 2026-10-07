# RFQ-007: Sync reviewed V1.2 alert/cooldown increment into V1.3

Status: REVIEW_REQUIRED; review REQUIRED. Branch: feature/v1-3-sync-v12-increment.

## Approved sources and method
V1.3 base: 2a32007d96ae39aa3cf62fee4e53b7bf2f896f1a (RFQ-006 REVIEWED_DONE).
V1.2 approved HEAD: b0f27cde979c00bee95703936fa2d8fc5cc611df.
Only implementation source: f515a145360d0eb72c4ffd7b8988a6cea6ae7ed2,
parent c8d514ed7aff2542dda685d476cd6e92ff97a85d.
Incremental CEO review: 5bc0c6de9c220d810c8ca81cffb2e43b89e07967.
Read actual git show -- src tests first; compare each hunk, directly reuse where applicable.
No full-commit cherry-pick, branch merge, whole-file replacement or report-based redesign.

## Scope and requirements
- Reuse set_business_state QUEUED/HUMAN_RESOLUTION recovery via existing _recover_alerts:
  DATA_QUALITY, scope invalid-quantity only, same transaction and retained ALERT_RECOVERED history.
- Read-only legacy GUI filter only for PURCHASE_RECORDED, invalid-input/quantity DATA_QUALITY
  and later HUMAN_RESOLUTION_RECORDED; other alerts and quotation states remain independent.
- Append RunSession.row_cooldown_until: datetime | None = None.
- Reuse interruptible stop.wait wrapper, deadline set then finally cleared; bind only V1.2
  compose_v12_production row_wait. Preserve all other retry/updater/scheduler waits.
- Adapt existing combined GUI countdown, retaining QUOTATION_RUNNING and V1.2_PAUSED isolation.
- Reuse all three original tests without weakening; add narrow GUI and V1.3 isolation evidence.
- Verify B1 already equivalent; do not reimplement. Preserve RFQ-004/005/006, holds, fail-closed,
  website229, raw14/latest72h, headerless A1:N1, identity, durable one-submit safety and fixed CDP.
- Keep A/B/C validation; no guessed S mapping. No dependencies, second system or architecture.

## Authorization boundaries
Source/offline only. No historical replay, real procurement, Save/Save-and-Send, real Google
write/update/Apps Script, production state mutation or SMTP. No browser/profile/cookie changes.
BuildOnly/frozen self-check permitted if existing environment available; deployment forbidden.
Commit/push only sync branch, verify local/remote equality and clean worktree.
Stop at REVIEW_REQUIRED; independent CEO review required, never mark REVIEWED_DONE.

## Acceptance and verification
Focused RFQ-003 resilience, RFQ-006 workflow/backend, GUI and RFQ-004/005 regressions;
full python -m pytest -q tests (safe/offline); Ruff src tests; git diff --check.
Report per-file reuse/equivalence/adaptation, S->A selective recovery, legacy read-only projection,
V1.2 interruptible180s/final-row behavior, V1.3 no180s, quotation GUI and B1/holds/fault/scheduler.
Keep live-only facts UNKNOWN; no production acceptance claimed.

## Completion evidence
Source sync and focused/full/Ruff/diff/build checks complete; see FINAL_REPORT.md.
Independent CEO Review remains REQUIRED; no deployment authorized/performed.
