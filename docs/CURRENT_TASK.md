# Current Task

Status: READY_FOR_CEO_REVIEW

Goal: Resolve CEO Stage 2A findings C1–C4 and the two small follow-ups without connecting to production systems. Keep accepted V1.1 Research rules and `workflow_items` semantics unchanged.

Business Outcome:
- Deliver deterministic contracts, persistence, browser ownership and write guards ready for CEO and Safety Supervisor review.
- Preserve `release/v1.1` as the independent rollback baseline.

Acceptance:
- [x] C1: Launcher supplies Research an explicit lease-backed INSO access; no arbitrary tab selection or reused-browser close.
- [x] C2: Save dispatch requires AI_RECOGNIZED; VALIDATION_FAILED cannot be reset through ordinary state mutation.
- [x] C3: B/C with missing estimated total return INDETERMINATE with no purchase route.
- [x] C4: Notification transport returns a typed outcome and allowlisted reason; unexpected Workflow-boundary exceptions become UNKNOWN.
- [x] Discovery is non-ready when required controls are missing, duplicated or non-unique.
- [x] V1.2 customer-name value and allowlisted source snapshot can be persisted together.
- [x] Run full deterministic tests, Ruff and `git diff --check`; commit and push `feature/v1-2`.

Constraints:
- No live INSO discovery/control, Save Data, Save-and-Send, production smoke, real SMTP, Google Sheets read/write, or production DB migration.
- Production writer feature gate remains unconditionally closed. Production Brand write remains disabled.
- Preserve V1.1 Research canonical rules and the meaning/schema constraints of `workflow_items`.
- Evidence stays under ignored `runtime/evidence/`; no secrets, customer production data, raw exception text or screenshots in Git.

Done:
- Synced `feature/v1-2` to the requested `e3f58699bbb56a166e90c0620b224eaaf9fea199` before editing.
- C1: Launcher lazily attaches Playwright to the configured CDP endpoint, requires exactly one context, opens only lease-owned child pages, and gives Research an operation access provider. Reused-browser cleanup disconnects Playwright without closing Chrome; app-owned Chrome closes only after the worker drains.
- C2: `begin_save_dispatch()` accepts only AI_RECOGNIZED. State transitions from PRE_SAVE_READY are limited to AI_RECOGNIZED or VALIDATION_FAILED; ordinary updates cannot move a failed or recognized result back to a save-eligible state. Confirmed absence plus human acknowledgement retains AI_RECOGNIZED.
- C3: `PurchaseRoutingDecision` now carries READY or INDETERMINATE; B/C without `estimated_total` has no quotation type or purchaser.
- C4: `NotificationTransportResult` freezes the four transport outcomes and an allowlisted `ReasonCode`. The transport owns provider error classification; unexpected exceptions persist as UNKNOWN.
- Discovery inspection requires explicit required-control IDs and reports non-ready if any is absent, duplicated or not uniquely resolved.
- Sheets records `CustomerNameSource`; V1.2 inquiry state can persist the customer value/source and emits the data-quality event/alert for missing values.
- V1.1 Research canonical rules, `workflow_items`, production Brand write boundary and the closed writer feature gate are unchanged. No live discovery, INSO write, production data, SMTP or Sheets write was performed.

Verification:
- `python -m ruff check src tests` — passed.
- `python -m pytest --basetemp .tmp/pytest-v12-c1-c4-final -q` — 468 passed, 11 skipped.
- `git diff --check` — passed.

Current:
- C1–C4 and the two requested follow-ups are implemented at the existing additive seams. This work does not change any live-system authorization gate.
- `READ_ONLY_DISCOVERY_ALLOWED`, `WRITE_IMPLEMENTATION_ALLOWED`, `REAL_SAVE_DATA_SMOKE_ALLOWED` and `REAL_NOTIFICATION_SMOKE_ALLOWED` remain ungranted. The inspector has not been run against a browser or INSO.

UNKNOWN / Blockers:
- No code blocker remains for the requested C1–C4 scope.
- Live endpoint, account/company identity, selectors, stable history identity and timestamp tie policy, saved-record identity/read-back fields, AI result DOM contract, evidence crop/redaction viability, live notification idempotency and restore operator procedure remain UNKNOWN; no live discovery was run.
- B1–B4 remain subject to the planned independent Safety re-review before any future live-capable implementation. The writer gate remains closed and Save-and-Send is prohibited.

Next:
- CEO reviews the Stage 2A implementation and current diff. Safety Supervisor independently reviews session identity/ownership, all write hard guards, unknown-save reconciliation, event/alert scoping, notification recipient retry/recovery, sanitized persistence, and backup/restore failure paths.
- Only after separate gate changes may the project prepare/execute read-only discovery or implement live writes/notifications. This task does not authorize those steps.

Branch: `feature/v1-2`

Stage 2A base commit: `e711e06cb1bdaf8fd7da3a26f2aa590999359b4b`
V1.1 rollback baseline: `be9d0a51d0375884dfa3e5e9e4317958899fdc75`


Owner Lean-Safety Decision:
- Safety for V1.2 should be pragmatic and lightweight, not a separate over-engineered architecture project.
- Keep only the high-value, low-complexity protections as mandatory:
  1. No code/API/action path for `保存并发送`.
  2. Before any INSO write, require one exact intended control; zero/multiple/changed target -> stop.
  3. After an uncertain `保存数据` outcome, never auto-click Save Data again; require read-only confirmation or manual handling.
  4. Never persist/log SMTP authorization codes, cookies/tokens, or raw external exception text.
  5. Do not close a reused user browser or select an arbitrary first tab/context.
- SQLite safety should stay simple: create one verified consistent backup before the first V1.2 migration, keep migration additive, and avoid automatic destructive downgrade. Do not turn backup/recovery into a large subsystem.
- Safety Supervisor is a lightweight reviewer. It should focus on the five protections above and obvious regressions, not continuously add new gates, abstractions, or exhaustive threat-model requirements.
- Prefer simple exact selectors, explicit checks, and fail-closed behavior over elaborate frameworks. A recommendation is not a blocker unless it can realistically cause wrong-order mutation, duplicate Save Data, forbidden send, secret leakage, or breaking the accepted V1.1 runtime.
