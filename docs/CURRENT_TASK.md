# Current Task — V1.2 pre-save integration

**Stage:** Phase A COMPLETE; pre-save integration review complete.
**Production Write Gate:** CLOSED.

## Verified baseline

- V1.1 Research Stability: CLOSED (`release/v1.1 = 44cd4a4cdb05fc069189801d24c4710bfd9445f3`).
- V1.2 Phase A: COMPLETE.
- Duplicate history: exact query PASS; nonempty history query PASS.
- Creator: `CREATOR_NOT_EXPOSED_BY_INSO`.
- Quote/currency: CONFIRMED.
- AI recognition/preview: CONFIRMED.
- Parent product fields, unsaved read-back: CONFIRMED.
- Real Save: NO. Real Send: NO. Real SMTP: NO. Sheets write: NO.
- Production browser: Chrome only.

## Completed pre-save integration

- Duplicate check → Research → routing coordinator and retry-safe persisted state/events.
- SQLite V1.2 migration, active alerts, recipient outbox/ledger, and fake notification transport.
- Purchase routing, AI draft preparation, validation and parent-field read-back contract.
- Read-only reconciliation state machine and fail-closed result handling.
- GUI DTO/state integration.

## Latest verification

- `feature/v1-2` fast-forwarded normally to fetched `origin/feature/v1-2` HEAD `74cb518`.
- `python -m pytest -q`: 631 passed, 11 skipped.
- `python -m ruff check src tests`: passed.
- Launcher CDP focus: 17 passed. `git diff --check`: pending final review.
- Edge runtime branch and `EDGE_CDP_ATTACH_FAILED` removed; Chrome launch behavior remains windowless.

## Concrete blockers before first real Save gate

- No production `ParentProductFields` adapter is bound to the confirmed unsaved INSO form; the code currently requires an injected implementation.
- Save reconciliation defaults to `UnavailableReadOnlySaveReconciler`; no production read-only adapter proves a unique saved record or authoritative absence.
- Current computer-use surface exposed Edge only, so no Chrome live verification was attempted. Do not use Edge as a substitute.

No Save Data, Save-and-Send, Send, SMTP, or Sheets write is authorized. Keep Production Write Gate CLOSED until the two adapters and Chrome-only read-only verification are complete.

## Task packet

See `tasks/2026-09-28-v1-2-clean-handoff.md`.
