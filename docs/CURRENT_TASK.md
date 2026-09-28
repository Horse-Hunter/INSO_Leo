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

## Completed pre-save integration

- Duplicate check → Research → routing coordinator and retry-safe persisted state/events.
- SQLite V1.2 migration, active alerts, recipient outbox/ledger, and fake notification transport.
- Purchase routing, AI draft preparation, validation and parent-field read-back contract.
- Read-only reconciliation state machine, production exact-history/detail adapter, and fail-closed result handling.
- GUI DTO/state integration.

## Latest verification

- `feature/v1-2` fast-forwarded normally to fetched `origin/feature/v1-2` HEAD `74cb518`.
- `python -m pytest -q`: 645 passed, 11 skipped.
- `python -m ruff check src tests`: passed.
- Focused parent-field/composition tests: 35 passed. `git diff --check`: pending final review.
- Edge runtime branch and `EDGE_CDP_ATTACH_FAILED` removed; Chrome launch behavior remains windowless.

## Gate status before first real Save

- `PlaywrightParentProductFields` binds the verified parent form frame and exact PartNo/Brand/Qty controls without a Save capability.
- `PlaywrightReadOnlySaveReconciler` reuses the settled exact history query, validates BillID/PENO/detail fields, and never chooses among multiple candidates or retries Save.
- Production composition now requires an explicit read-only reconciler; it no longer silently falls back to `UnavailableReadOnlySaveReconciler`.
- The bounded Chrome-only read-only runner executed with all side effects false, but returned `RESEARCH_RUNTIME_CONFIG_INVALID`; no Chrome/CDP session was available. Edge was not used as a substitute.

No Save Data, Save-and-Send, Send, SMTP, or Sheets write is authorized. Keep Production Write Gate CLOSED until the two adapters and Chrome-only read-only verification are complete.

## Task packet

See `tasks/2026-09-28-v1-2-clean-handoff.md`.
