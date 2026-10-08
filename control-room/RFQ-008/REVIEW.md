# RFQ-008 CEO Independent Review — 2026-10-08

**Status:** COMPLETE  
**Verdict:** CHANGES_REQUESTED  
**Reviewed HEAD:** `bc4c1e42085c9d3e68fe723fd23fc240d86f1308`  
**Reviewed base:** `7e4a63b0f74f4363053e90b12ef1835748a05cff`

## Decision

RFQ-008 is not approved for deployment yet.

The overall architecture is acceptable: edits are single-cell RAW writes with readback, manual purchase/quotation reruns are serialized on the existing poll thread, the 15-minute timer restarts after a manual action, and the existing purchase/quotation/browser implementations are reused rather than duplicated.

Two blocking lifecycle issues remain.

## B1 — HIGH — Successful manual purchase rerun leaves stale failure alerts active

The new manual retry path allows pre-submit failures to be rerun:

- `V12WorkflowCoordinator.rerun_unsubmitted()` revives the existing inquiry;
- `V12Store.reset_unsubmitted_purchase_for_manual_retry()` deletes only mutable pre-submit purchase state;
- the existing workflow is then run again.

However, the durable alert ledger is not updated for the superseded failure episode.

Examples:

1. A previous `VALIDATION_FAILED` raises an active `PURCHASE_EXCEPTION` alert in scope `ai-recognition`.
2. A previous duplicate stop raises an active `DUPLICATE_ORDER` alert.
3. Owner corrects model/brand/quantity and right-clicks “重跑采购流程”.
4. The rerun can succeed, but neither `reset_unsubmitted_purchase_for_manual_retry()` nor the successful rerun recovers those old alerts.
5. `read_v12_order_state()` still returns the stale alert as active, and the GUI continues to render the order red even after the new successful purchase path.

This recreates the same class of stale-alert problem previously fixed for invalid-input recovery.

### Required repair

On an explicit Owner manual purchase rerun, supersede only the alerts whose underlying pre-submit decision is being intentionally rerun.

At minimum:

- recover the old `PURCHASE_EXCEPTION` / `ai-recognition` alert when the manual retry is accepted;
- recover the prior `DUPLICATE_ORDER` alert when the selected inquiry is explicitly rerun through duplicate checking;
- preserve unrelated customer/data-quality/security/notification/save-outcome alerts;
- append recovery evidence through the existing alert/event ledger; do not delete historical events or alert rows.

If the rerun fails again, the canonical workflow must be able to raise a new active alert for the new failure episode.

### Required regression

1. validation failure -> active purchase alert -> manual rerun -> successful purchase -> no stale ai-recognition alert;
2. duplicate stop -> active duplicate alert -> corrected source + manual rerun -> nonduplicate/success -> no stale duplicate alert;
3. unrelated `CUSTOMER_NAME_MISSING` remains active;
4. rerun fails again -> a current failure alert is active;
5. event history remains append-only.

## B2 — HIGH — Manual quotation rerun does not safely resolve all durable holds

The new quotation action currently does:

`holds.close(inquiry)`

before invoking the selected-row quotation runner.

That is insufficient and unsafe in two cases.

### Case A: unbound hold at the selected row

RFQ-006 can persist unbound holds such as `SOURCE_MPN_UNAVAILABLE` / `SOURCE_IDENTITY_UNRESOLVED` using a key like `unresolved:<hash>`.

After the Owner edits the row and right-clicks “重跑报价流程”:

- `InquiryHolds.active()` only exposes holds whose key equals the inquiry id;
- `holds.close(inquiry)` cannot close the unbound location hold;
- the manual rerun may complete normally, including `NO_RECENT_QUOTE`;
- the old unbound hold remains active and the next automatic cycle continues blocking the row.

So a successful manual repair can leave the source permanently held.

### Case B: bound hold is deleted before the manual rerun is known to settle

For a normal bound hold, the code deactivates the durable barrier before running the selected-row quotation flow.

If the manual rerun then exits via a shared/global fault before producing a new terminal row result, the previous durable barrier has already been lost. On a later restart/cycle the still-`发给采购` row may become automatically eligible even though this one explicit manual rerun did not settle.

### Required repair

Treat the right-click quotation rerun as a **one-shot Owner-authorized bypass**, not as an unconditional permanent deletion of the old hold before execution.

The selected rerun must be able to ignore only the matching hold for this one attempt while the underlying durable barrier remains recoverable until the new attempt settles.

The matching scope must support both:

- bound hold for the selected inquiry id;
- unbound hold whose saved worksheet + original row position safely match the selected original row.

Do not fuzzy-match by MPN/brand/quantity.

After the manual attempt:

- new terminal `ROW_FAILED` -> canonical new/updated hold remains active;
- `NO_RECENT_QUOTE` -> prior selected hold is closed because the repair attempt settled normally and future automatic polling must be allowed;
- successful update / source becomes `采购已报价` -> prior selected hold closes;
- shared/global fault / unexpected interruption -> prior hold remains active;
- `SOURCE_STATUS_NOT_UPDATED` with the same source snapshot remains non-repeatable.

Other inquiries' holds must remain untouched.

### Required regression

1. unbound SOURCE_MPN_UNAVAILABLE hold -> edit model -> manual quote -> NO_RECENT_QUOTE -> old unbound hold closes and next automatic cycle is eligible;
2. unbound identity hold -> manual rerun successful update -> old hold closes;
3. bound ROW_FAILED hold -> manual rerun global fault -> original hold remains active;
4. bound hold -> manual rerun new ROW_FAILED -> active hold remains with the new reason/episode;
5. other inquiry holds unchanged;
6. existing SOURCE_STATUS_NOT_UPDATED same-snapshot no-repeat regression remains PASS.

## Areas accepted in this review

No blocker found in the following RFQ-008 additions:

- current-poll found/completed projection reset;
- serial manual command execution during the idle countdown;
- 15-minute countdown restart after manual action;
- exact single-cell RAW edit and readback;
- SHAHAB fixed-A importance edit rejection;
- current source reread before purchase/quotation rerun;
- purchase status gate `未发`;
- quotation status gate `发给采购`;
- durable Save/Save-and-Send no-resend gate;
- same row-position inquiry identity reuse as explicitly authorized by Owner;
- no second browser/workflow/SMTP implementation;
- RFQ-006/007 reviewed code preserved.

## Verification evidence reviewed

Executor reports:

- focused: **523 passed**;
- full safe/offline: **1475 passed / 1 skipped**;
- Ruff: **PASS**;
- `git diff --check`: **PASS**;
- BuildOnly / frozen self-check / release scan: **PASS**;
- candidate SHA256: `136902DD75B3C7F4B25BAECEE70D95174CEC7AD61CA6AB4B158726EC88E99EC1`.

These results do not cover B1 or the unbound/global-fault hold lifecycle in B2.

## Release decision

**DO NOT DEPLOY** the `136902DD...` candidate.

Both blockers can be repaired offline without any real purchase, quote update, Apps Script, SMTP, or historical replay.

After repair, rebuild a new candidate and resubmit RFQ-008 for independent CEO Review.

## State transition

`REVIEW_REQUIRED -> CHANGES_REQUESTED`

---
# RFQ-008 B1/B2 Repair CEO Independent Review — 2026-10-08

**Status:** COMPLETE  
**Verdict:** PASS / REVIEWED_DONE  
**Reviewed repair HEAD:** `5275fc37adbfb73d704acadda993b1cb084d0887`  
**Repair base:** `43b9bccea94b71f5727662aaba7fd37f0d5077a1`

## Decision

Both blockers from the prior RFQ-008 review are closed. No new blocker was found in the reviewed repair diff.

## B1 closure — manual purchase rerun supersedes only the stale pre-submit alert episode

PASS.

The explicit manual purchase path reuses the existing `HUMAN_RESOLUTION_RECORDED` transition and adds a narrow `manual_purchase_retry=True` flag. Inside the existing V12 transaction, the retry now recovers only:

- `PURCHASE_EXCEPTION` with scope `ai-recognition`;
- `DUPLICATE_ORDER` with the existing empty scope.

The existing invalid-input recovery remains unchanged. Customer-name, other data-quality, security, notification, save-outcome and uncertain-submit alerts are not recovered.

Recovery continues through the canonical `_recover_alerts()` path, preserving old rows/events and appending recovery evidence. If the new retry fails again, the canonical workflow can raise a new active alert for the new episode.

The durable no-resend gates for armed/clicked/unknown/saved submission evidence remain unchanged.

## B2 closure — manual quotation retry is now a one-shot durable-hold bypass

PASS.

`ManualRetryHolds` does not delete a matching old barrier before execution. It identifies only:

- a bound hold whose key exactly equals the selected inquiry id;
- an unbound `unresolved:` hold whose stored worksheet and original row position exactly match the selected row.

No MPN/brand/quantity fuzzy matching was introduced.

For the selected invocation, matching old holds are hidden from the canonical integrated cycle while remaining durable in SQLite. New ROW_FAILED holds are still delegated to the real hold store.

Final settlement is conservative:

- `NO_RECENT_QUOTE`, `UPDATED_INSERTED`, `UPDATED_ALREADY_EXISTS`: matching old holds close only after exactly one selected terminal result is returned;
- `ROW_FAILED`: a new/current durable hold with the current reason must already be active before superseded old keys may close; a same-key bound hold remains active;
- global fault, unexpected exception, stop/interruption, empty/nonterminal result, or close transaction failure: old barriers remain active.

The existing `SOURCE_STATUS_NOT_UPDATED` same-snapshot no-repeat rule is checked before the bypass and remains intact, including matching unbound holds.

`V13HoldStore.close_many()` uses one SQLite transaction, so a batch-close failure rolls back instead of partially dropping barriers.

## Regression and safety review

The repair preserves the previously accepted RFQ-008 behavior:

- single-cell RAW source edits and readback;
- SHAHAB fixed-A edit restriction;
- current 15-minute cycle counters;
- serial idle-countdown manual commands;
- full countdown restart after a command;
- current source reread before rerun;
- purchase requires current `未发`;
- quotation requires current `发给采购`;
- original worksheet/row manual anchor;
- existing V1.2/V1.3 workflow, identity, browser/CDP, SMTP and notification implementations.

RFQ-003 through RFQ-007 reviewed safety boundaries remain unchanged.

## Verification evidence reviewed

Executor reports for the exact repair HEAD:

- focused: **451 passed**;
- full safe/offline: **1507 passed / 1 skipped**;
- Ruff: **PASS**;
- `git diff --check`: **PASS**;
- V1.3 BuildOnly: **PASS**;
- frozen self-check: **PASS**;
- release scan: **PASS**.

The focused repair tests cover stale AI/duplicate alert recovery, unrelated-alert preservation, repeated-failure re-alerting, append-only history, bound/unbound hold settlement, unresolved-to-bound replacement, global-fault preservation, transaction rollback, other-hold isolation and confirmed-Script no-repeat behavior.

New candidate EXE SHA256:

`7ECE6917BF77E263E1E56BC528A63EE0798404DB1D03D494499B94A4A16B663F`

The prior `136902DD...` candidate remains superseded.

## Live boundary

No real procurement, Save-and-Send, quotation write, 更新报价, Apps Script or real SMTP was executed in this repair. The candidate remains BuildOnly and is not yet deployed.

## Release decision

RFQ-008 source/offline review is approved. The `7ECE6917...` candidate is eligible for the controlled deployment step, preserving the existing runtime DB, OAuth/grants, credentials, fixed Chrome profile, production configuration and V1.2 release.

## Final state

`CHANGES_REQUESTED -> REVIEW_REQUIRED -> REVIEWED_DONE`
