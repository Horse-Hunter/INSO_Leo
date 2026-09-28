# Current Task — V1.2 pre-save integration

**Stage:** Pre-save production adapters implemented; Chrome live verification pending valid local runtime configuration.
**Production Write Gate:** CLOSED.

## Verified baseline

- V1.1 Research Stability: CLOSED (`release/v1.1 = 44cd4a4cdb05fc069189801d24c4710bfd9445f3`).
- V1.2 Phase A: COMPLETE.
- Duplicate history: exact query PASS; nonempty history query PASS.
- Creator: `CREATOR_NOT_EXPOSED_BY_INSO`.
- Quote/currency: CONFIRMED.
- AI recognition/preview: CONFIRMED.
- Parent product fields: production adapter implemented with unique frame/field and immediate read-back checks.
- Real Save: NO. Real Send: NO. Real SMTP: NO. Sheets write: NO.
- Production browser: Chrome only.
- INSO ordinary authentication recovery: VERIFIED with Core Vault credentials; authenticated shell and exact-history settlement were confirmed. Canonical procedure is in `docs/modules/INSO.md` and must be reused by every new Main Programmer window.

## Completed pre-save integration

- Duplicate check → Research → routing coordinator and retry-safe persisted state/events.
- SQLite V1.2 migration, active alerts, recipient outbox/ledger, and fake notification transport.
- Purchase routing, AI draft preparation, validation and parent-field read-back contract.
- Read-only reconciliation state machine, production exact-history/detail adapter, and fail-closed result handling.
- GUI DTO/state integration.

## Latest verification

- Current feature baseline includes pre-save adapters through `987fd8820f3ec80024726d3557617160eb2c1e0c`.
- `python -m pytest -q`: 645 passed, 11 skipped.
- `python -m ruff check src tests`: passed.
- Focused parent-field/composition tests: 35 passed. `git diff --check`: pending final review.
- Edge runtime branch and `EDGE_CDP_ATTACH_FAILED` removed; Chrome launch behavior remains windowless.

## Shared runtime prerequisite

- Before further INSO live work, ensure the canonical ordinary recovery path is implemented as one shared executable helper with regression tests. It must verify non-empty account/password field read-back before one exact submit, and all INSO windows must call it instead of repeating manual browser steps.

- INSO shared runtime readiness is now a hard project invariant: approved Chrome/CDP + Core Vault + ordinary authentication recovery + unique authenticated shell must be resolved internally before any INSO feature step. Ordinary readiness failures are not Owner blockers. If the shared path is absent or regresses, fix it and its tests first.

## Gate status before first real Save

- `PlaywrightParentProductFields` binds the verified parent form frame and exact PartNo/Brand/Qty controls without a Save capability.
- `PlaywrightReadOnlySaveReconciler` reuses the settled exact history query, validates BillID/PENO/detail fields, and never chooses among multiple candidates or retries Save.
- Production composition now requires an explicit read-only reconciler; it no longer silently falls back to `UnavailableReadOnlySaveReconciler`.
- Chrome bootstrap, Core Vault credential access, ordinary INSO authentication recovery, unique authenticated shell, exact-history query and settlement have been live-verified. Reuse the canonical procedure in `docs/modules/INSO.md`; do not rediscover it.

No Save Data, Save-and-Send, Send, SMTP, or Sheets write is authorized. Keep Production Write Gate CLOSED until the two adapters and Chrome-only read-only verification are complete.

## Task packet

See `tasks/2026-09-28-v1-2-clean-handoff.md`.
