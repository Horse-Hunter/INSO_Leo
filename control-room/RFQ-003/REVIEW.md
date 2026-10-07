# RFQ-003 CEO Independent Review — 2026-10-07

**Status:** COMPLETE  
**Verdict:** PASS / REVIEWED_DONE  
**Reviewed Executor HEAD:** `241fd487bdb7452d2049feaa130c8439ff1bc4d9`  
**Previous Blocking Review:** B1 at CEO review commit `d1ae0048289ada76462ae92129d67d8a97a320ef`

## Decision

RFQ-003 is approved.

The B1 blocker from the previous review is repaired without broad queue/state-machine redesign.

The new startup-interruption decision now distinguishes:

- rows merely pre-enqueued/pre-created as `DUPLICATE_CHECK_PENDING`, which remain resumable;
- rows with durable evidence that execution really started, which are quarantined on restart when unfinished;
- rows with possible-submit evidence, which remain conservatively isolated;
- already closed business states, which remain closed and are not reopened.

This matches the Owner requirement that a crash/restart only red-marks the order that was genuinely in progress, while later untouched rows continue in source-sheet order.

## B1 verification

### PASS — untouched queued rows are no longer quarantined

The original defect came from pre-enqueuing the entire batch before serial processing.

The repair does not treat the pre-created `DUPLICATE_CHECK_STARTED` event by itself as execution proof. Startup quarantine now requires stronger durable evidence such as:

- a claimed/researching work item or prior attempt;
- a later execution event;
- a real non-pending business phase;
- purchase/submission evidence.

Thus later rows that exist only as `QUEUED + DUPLICATE_CHECK_PENDING` remain eligible after restart.

### PASS — genuinely active unfinished row is still quarantined

A row already claimed or advanced into duplicate/research/purchase execution is still projected and persisted as an interruption on restart.

The existing red interruption behavior is therefore preserved for the actual in-progress row.

### PASS — possible-send safety boundary is preserved

`SAVE_DISPATCH_ARMED` and `SAVE_CLICK_COMPLETED` are explicitly included in the possible-submit evidence path.

Existing purchase outcomes such as:

- `UNKNOWN_WRITE_OUTCOME`
- `READ_ONLY_RECONCILIATION_REQUIRED`
- `MANUAL_REVIEW`
- `SUBMIT_UNCONFIRMED`

continue to prevent automatic purchase replay.

No B1 change weakens the unique Save-and-Send / no-resend boundary.

### PASS — cooldown-exit case is covered

The new three-row regression covers the case where:

1. row 1 closes;
2. V1.2 enters the 180-second inter-row cooldown;
3. the program exits before row 2 starts;
4. restart occurs.

Row 1 remains closed and rows 2/3 remain normal queued work rather than red interruptions.

This is the exact edge case required by the previous CEO review.

### PASS — idle GUI projection uses the same rule

`read_startup_interruptions()` uses the same execution-evidence helper and remains SQLite read-only.

Untouched pre-enqueued rows are not projected as red interrupted history before Start.

### PASS — human completion path remains intact

The repaired tests retain the rule:

- source still `未发` → interrupted row remains red/skipped;
- Owner changes source to `发给采购` → row becomes `HUMAN_COMPLETED`, red state clears, V1.2 does not repurchase it.

## Wider RFQ-003 review

The previous review found no additional blockers in the broader RFQ-003 implementation, and B1 was the only requested repair.

The following boundaries remain present after the B1 commit:

- IC.net failure → V1.2 module pause, not shared global stop;
- INSO authentication/manual-verification → shared global stop and protected page preservation;
- other Research-site failures remain source-local;
- INSO lower-history query uses bounded initial + three retry behavior;
- V1.2 inter-row cooldown remains 180 seconds, interruptible, and not applied after the final row/empty poll;
- durable click receipt supports `SUBMIT_UNCONFIRMED` without automatic second Save-and-Send;
- Google `发给采购` write-back failure remains a yellow manual-update state rather than purchase replay;
- SMTP remains non-blocking to business flow;
- shared Sheets/ledger/CDP failures retain global-stop semantics;
- RFQ-002 manual-verification page preservation is retained.

## Executor verification evidence reviewed

Executor reports for the repaired HEAD:

- focused: **996 passed / 1 skipped**
- full safe/offline: **1043 passed / 11 skipped**
- Ruff: **PASS**
- `git diff --check`: **PASS**
- build: **PASS**
- frozen self-check: **PASS**
- deployed self-check: **PASS**
- clean staged release scan: **PASS**
- idle launch: **PASS**

No real order, Save/Save-and-Send, SMTP, Sheets write, production replay, or live CAPTCHA was run during this repair.

Final deployed EXE SHA256 reported:

`1A49C9650BA531F2299326FFC89761D0391CD5F2C0FE32327DDD0736BD5C3E84`

Current repair backup:

`D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.2-20261007-before-rfq003-b1`

## Residual boundary

Live production behavior is still not claimed from offline evidence alone. That does not block RFQ-003 because the task explicitly required offline/safe verification plus idle release verification, not a new real procurement submission.

## Final state

`CHANGES_REQUESTED → REVIEW_REQUIRED → REVIEWED_DONE`

RFQ-003 is complete and may be used as the baseline for the next V1.3 RFQ.

---

## Incremental CEO Review — corrected-input alert + row-cooldown display — 2026-10-07

**Status:** COMPLETE  
**Verdict:** PASS / REVIEWED_DONE  
**Reviewed implementation commit:** `f515a145360d0eb72c4ffd7b8988a6cea6ae7ed2`  
**Reviewed latest sync/report commit:** `68b6913c8c69017a7cdaedac79e486197da4271b`

This incremental review is separate from, and does not rely on, the earlier RFQ-003 B1 PASS above.

### Scope reviewed

The implementation delta from the previously approved `c8d514ed7aff2542dda685d476cd6e92ff97a85d` baseline to `f515a145...` is exactly one code commit. The production delta is limited to:

- `src/workflow/v12_store.py`
- `src/launcher/v12_gui.py`
- `src/gui/contracts.py`
- `src/launcher/backend.py`
- `src/gui/app.py`

plus three targeted regressions in `tests/workflow/test_rfq003_resilience.py` and delivery/report documentation.

### PASS — corrected invalid input recovers only the stale input-quality alert

When an `INVALID_INPUT_SKIPPED` inquiry becomes valid again, the existing `_resume_after_input_fix()` path returns it to `QUEUED` with `HUMAN_RESOLUTION_RECORDED`. `V12Store.set_business_state()` now reuses the existing `_recover_alerts()` transaction to recover only `DATA_QUALITY` alerts in the existing `invalid-quantity` scope.

This is the same scope already used for both `INQUIRY_QUANTITY_INVALID` and the newer critical `INQUIRY_INPUT_INVALID` reason. It does not recover customer-name, purchase, notification, security or other alert scopes.

The S -> A regression confirms the program does not map or guess ratings: S remains invalid under the existing A/B/C rule; after the Owner changes the source row to A, the original inquiry resumes, the stale invalid-input alert is recovered, and an unrelated missing-customer alert remains active.

### PASS — legacy saved rows are corrected only in read-only GUI projection

`read_v12_order_state()` handles already-produced legacy data where an older build resumed valid input but left the invalid-input alert active. The compatibility filter is deliberately narrow:

- business state must already be `PURCHASE_RECORDED`;
- alert type must be `DATA_QUALITY`;
- reason must be `INQUIRY_INPUT_INVALID` or `INQUIRY_QUANTITY_INVALID`;
- a later `HUMAN_RESOLUTION_RECORDED` event must exist.

The projection does not write or rewrite the production database. Other alerts remain visible. The regression proves event/alert history is unchanged by the read and a later customer-data alert remains visible.

### PASS — 180-second purchase cooldown policy is unchanged; only its GUI projection is exposed

`RunSession` gains an additive optional `row_cooldown_until=None` field. `ProductionBackend` wraps the existing V1.2 `row_wait` callback with `_wait_between_rows()`:

- sets a display deadline;
- calls the same interruptible `self._stop.wait(seconds)`;
- clears the deadline in `finally`.

No duration, row ordering, final-row behavior, empty-cycle behavior, stop semantics, purchase gate, submit proof or notification behavior is changed.

`_countdown_text()` now prefers `冷却 MM:SS` while the V1.2 row wait is active and `订单处理中` while an active order is reported, instead of showing the misleading `即将轮询` state.

### PASS — earlier RFQ-003 B1 remains present

The reviewed increment is based directly on `c8d514e`, which already contains the approved B1 repair. No B1 code was removed or weakened. Pre-enqueued `QUEUED / DUPLICATE_CHECK_PENDING` rows without durable execution proof remain resumable after restart; genuinely started unfinished rows and possible-submit evidence remain quarantined.

### PASS — no purchase / identity / browser safety boundary changed

The implementation delta does not alter:

- `inquiry_id / record_identity`;
- A/B/C rating rule;
- duplicate/history logic;
- Research price rules;
- Save-and-Send durable arming/click proof;
- `SUBMIT_UNCONFIRMED` / `STATUS_WRITE_PENDING`;
- fixed CDP/profile ownership;
- manual-verification page preservation;
- no-resend/restart rules;
- V1.2 180-second policy itself.

### Verification evidence reviewed

Executor reports for the exact implementation commit:

- focused: **999 passed / 1 skipped**
- full safe/offline: **1046 passed / 11 skipped**
- Ruff: **PASS**
- `git diff --check`: **PASS**
- build: **PASS**
- frozen self-check: **PASS**
- clean staged release scan: **PASS**
- deployed self-check: **PASS**

Deployed V1.2 EXE SHA256 reported:

`340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F`

Previous reviewed EXE is preserved in the reported backup and runtime DB/config/grant/fixed CDP/profile were preserved.

### Real-order evidence boundary

The Owner has confirmed the current four-order handling is correct: three orders were submitted once and written back `发给采购`; the fourth had no quote across all five sources, was not purchased, and generated the expected exception mail. That closes the business handling of those four rows.

This does **not** establish a new post-rebuild end-to-end order acceptance for the newly packaged EXE. The rebuilt V1.2 application was idle-launched; Start was not successfully clicked/observed and polling must not be claimed as active.

### V1.3 synchronization decision

Approved for synchronization by **reusing the actual `f515a145...` source/test patch**, not by redesigning from the report.

The target V1.3 integrator must:

- compare each affected shared file against current `feature/v1-3-integration`;
- apply the same shared alert recovery / legacy projection / additive DTO behavior where absent;
- adapt the cooldown display minimally to the combined V1.2+V1.3 GUI, keeping the 180-second wait attached only to the V1.2 purchase `row_wait`;
- preserve V1.3 quotation states, scheduler, durable holds, browser/session, identity and update behavior;
- retain the already-present RFQ-003 B1 logic;
- record per file: direct patch reuse / already equivalent / minimal compatibility adaptation;
- rerun focused, full safe/offline, Ruff and diff check before independent review.

Blind cherry-pick, whole-file overwrite, a second alert/GUI/workflow implementation, historical replay and real purchase submission are not approved for synchronization.

### Incremental final state

`REVIEW_REQUIRED -> REVIEWED_DONE`
