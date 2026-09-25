# Current Task

Status: READY_FOR_CEO_REVIEW

Goal: Complete V1.2 Stage 2A fake-only safety and persistence seams without connecting to production systems. Keep the accepted V1.1 Research rules and `workflow_items` semantics unchanged.

Business Outcome:
- Deliver deterministic contracts, persistence, browser ownership and write guards ready for CEO and Safety Supervisor review.
- Preserve `release/v1.1` as the independent rollback baseline.

Acceptance:
- [x] Implement B1–B4 mitigations at fake-only seams; retain live identity, selectors and saved-record identity as UNKNOWN.
- [x] Add V1.2 contracts, append-only events, active alerts, recipient ledger, purchase state and safe GUI DTO seam.
- [x] Add exact duplicate/research routing rules, separate important-mail vs full-price purchasing decisions, and AI recognition verification.
- [x] Add consistent SQLite online backup and additive transactional migration against synthetic V1.1-shaped databases.
- [x] Add `dup-mpn-v1` / `ai-mpn-v1`, Sheets customer mapping, read-only inspector skeleton and evidence path helpers.
- [x] Run Ruff and full deterministic suite; no live system, real write, SMTP or production data used.
- [x] Commit and push this Stage 2A result to `feature/v1-2`; no merge to main.

Constraints:
- No live INSO discovery/control, Save Data, Save-and-Send, production smoke, real SMTP, Google Sheets read/write, or production DB migration.
- Production writer feature gate remains unconditionally closed. Production Brand write remains disabled.
- Preserve V1.1 Research canonical rules and the meaning/schema constraints of `workflow_items`.
- Evidence stays under ignored `runtime/evidence/`; no secrets, customer production data, raw exception text or screenshots in Git.

Done:
- Fast-forwarded isolated `feature/v1-2` worktree to `e711e06cb1bdaf8fd7da3a26f2aa590999359b4b`, preserving the authorized latest branch state.
- Added explicit `InsoSessionLease` with endpoint/browser/context/page identity, `APP_OWNED`/`REUSED`, child-page ownership, cycle-drain guard and fail-closed stale checks. Research INSO history no longer enumerates arbitrary pages or closes attached browsers.
- Added closed write action enum, narrow business methods, selector allow/deny registry, pre-dispatch semantic deny and production gate fixed closed. There is no Save-and-Send action or coordinate path.
- Added durable pre-dispatch `UNKNOWN_WRITE_OUTCOME`, restart lockout, read-only reconciliation contract/fake, manual review for ambiguous/unreadable results, and explicit human acknowledgement after authoritative absence.
- Added allowlisted reason codes, exception type-only classification, V1.2 event/DTO payload sanitization, recipient-scoped notification ledger/retries, and synthetic canary checks.
- Added V1.2 SQLite state/events/alerts/duplicate/notification/purchase tables, DB-enforced append-only event triggers, consistent online backup verification and atomic additive migration.
- Added separate `dup-mpn-v1` and `ai-mpn-v1` policies, Sheets `SHAHAB` / exact `2026` customer mapping, GUI DTO seam, fake-only read-only inspector and evidence path helpers.

Verification:
- `python -m ruff check src tests` — passed.
- `python -m pytest --basetemp .tmp/pytest-v12 -q` — 459 passed, 11 skipped.
- `git diff --check` — passed.

Current:
- Prior gate remains `DESIGN_SAFE` only. This implementation does not grant `READ_ONLY_DISCOVERY_ALLOWED`, `WRITE_IMPLEMENTATION_ALLOWED`, `REAL_SAVE_DATA_SMOKE_ALLOWED`, or `REAL_NOTIFICATION_SMOKE_ALLOWED`.
- The inspector was exercised only with a deterministic fake, never against a browser or INSO.
- Runtime composition does not yet provide a verified session lease to Research. The Research INSO source consequently fails closed until the composition root is safely wired; no V1.1 price/MPN/stock/FX/retry rule changed.

UNKNOWN / Blockers:
- Live endpoint, browser, account, company, context, page and selectors remain UNKNOWN; no discovery has been run.
- Stable history identity and timestamp tie policy, live saved-record identity/read-back fields, AI result DOM contract, evidence crop/redaction viability, live notification provider idempotency and restore operator procedure remain UNKNOWN.
- B1–B4 code seams are implemented but still require independent Safety Supervisor review before any live-capable implementation. Live Save Data remains unavailable until B2 identity is established; Save-and-Send stays prohibited at all stages.

Next:
- CEO reviews the Stage 2A implementation and current diff. Safety Supervisor independently reviews session identity/ownership, all write hard guards, unknown-save reconciliation, event/alert scoping, notification recipient retry/recovery, sanitized persistence, and backup/restore failure paths.
- Only after separate gate changes may the project prepare/execute read-only discovery or implement live writes/notifications. This task does not authorize those steps.

Branch: `feature/v1-2`

Stage 2A base commit: `e711e06cb1bdaf8fd7da3a26f2aa590999359b4b`
V1.1 rollback baseline: `be9d0a51d0375884dfa3e5e9e4317958899fdc75`
