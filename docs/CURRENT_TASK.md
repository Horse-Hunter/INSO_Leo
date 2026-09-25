# Current Task

Status: READY_FOR_CEO_REVIEW

Goal: Integrate the V1.2 business flow on existing contracts and fake adapters while preserving V1.1 Research and keeping all live external actions disabled.

Acceptance:
- [x] Sheets pending rows enter the existing V1.1 queue; V1.2 duplicate check runs before the unchanged Research worker.
- [x] Research runs for duplicate and lookup-unavailable orders; final routing waits for a confirmed duplicate result.
- [x] Confirmed duplicates stop purchase, raise a red alert, and enqueue an unconditional duplicate notification.
- [x] Non-duplicates use canonical Research facts for important notification and purchase routing; B/C unknown totals remain INDETERMINATE.
- [x] Notification delivery remains recipient-scoped, fake-only and independent from purchase draft processing.
- [x] Fake purchase adapter validates AI recognition only and cannot save to INSO.
- [x] GUI consumes optional V1.2 business state, latest active alert and event history while preserving the existing single-page layout.
- [x] V1.1 exception / Research remark values are not persisted into `workflow_items.last_error`; canary is absent from SQLite and GUI remark.
- [x] Deterministic tests, Ruff and `git diff --check` pass.

Constraints:
- No live INSO discovery/control, Save Data, Save-and-Send, production smoke, SMTP, Sheets write, or production DB migration.
- V1.1 Research business rules and `workflow_items` schema/semantics remain unchanged.
- Production writer gate remains closed. No credentials, production data, raw external errors, or screenshots are added.

Done:
- Synced `feature/v1-2` to `ea2a9c61b1a98aa48498e9191a3d233746bd5755` before editing.
- Added `V12WorkflowCoordinator` around the unchanged V1.1 `WorkflowWorker`; duplicate lookup is persisted before Research. An unconfirmed duplicate result leaves a durable ROUTING state, and a later confirmation resumes using the persisted V1 work item/customer snapshot without rerunning Research.
- Duplicate orders stop before purchase and enqueue a repeat notification containing the latest history fields and quantity × INSO quote total. Non-duplicates independently enqueue important-order notifications and create a fake AI-validated purchase draft.
- Notification commands can be delivered later; retry/failure/recovery stays in the existing recipient ledger and cannot alter purchase state.
- GUI reads migrated V1.2 state read-only. The main table shows the newest active alert in red; order detail shows the business label and full event history.
- V1.1 error persistence now stores Research reason/status, exception class name, or fixed Brand update codes; no exception message or Research remarks are stored.
- No live Sheets, Research, INSO, SMTP, or production SQLite activity was performed.

Verification:
- `python -m ruff check src tests` — passed.
- `python -m pytest --basetemp .tmp/pytest-v12-final2 -q` — 473 passed, 11 skipped.
- `git diff --check` — passed.

Remaining / UNKNOWN:
- Production V1.2 orchestration, database migration, duplicate-history reader and purchase writer remain unconnected and gated. This integration is fake-only.
- Live selectors/record identity, saved-record readback, notification provider behavior, and production smoke remain gated/unknown.

Branch: `feature/v1-2`
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
