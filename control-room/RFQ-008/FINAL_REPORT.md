# RFQ-008 CHANGES_REQUESTED repair — CEO report
Status: REVIEW_REQUIRED; independent review required, not self-approved.
Branch: feature/v1-3-integration.
Repair baseline:43b9bccea94b71f5727662aaba7fd37f0d5077a1 (latest CEO CHANGES_REQUESTED).
Implementation: commit containing this report (git log -1).
Previous RFQ008 implementationbc4c1e4 preserved; RFQ006/007 REVIEWED_DONE unchanged.
CEO REVIEW.md unchanged, SHA256485CDFD7BD0DC33408746AB03CE2FF4BD8D939477CBE362DFB00483022AB55F0.

## B1: superseded manual purchase alert episode
Code: src/workflow/v12_flow.py:169 rerun_unsubmitted / flag at181;
src/workflow/v12_store.py:266 set_business_state / recovery at288.
Only accepted explicit manual QUEUED + HUMAN_RESOLUTION_RECORDED + manual_purchase_retry=True
recovers PURCHASE_EXCEPTION/ai-recognition and DUPLICATE_ORDER/empty scope, within the same
transaction and through existing _recover_alerts/ALERT_RECOVERED append-only evidence.
Existing DATA_QUALITY/invalid-quantity recovery stays unchanged; ordinary input correction
passes defaultFalse and cannot clear purchase/duplicate decisions. One existing human event
is shared recovery evidence, without fabricated additional HUMAN_RESOLUTION events.
No customer-name/other DATA_QUALITY/security/notification/save-outcome/unknown-send alert recovery.
No change to submit safety: armed/clicked/unknown/saved/submit-unconfirmed/pending states block retry.

Regression tests/workflow/test_rfq008_alert_lifecycle.py:
- stale ai-recognition recovered after fake durable successful purchase:PASS;
- stale duplicate recovered after corrected source/nonduplicate/success:PASS;
- unrelated customer/data-quality/security/notification/purchase scope retained:PASS;
- repeated AI mismatch/duplicate creates a new current active alert:PASS;
- old events unchanged by ID, recovery appended, single human retry evidence:PASS;
- GUI does not project stale recovered alert/red styling; ordinary resolution doesn't recover:PASS.
Existing tests/launcher/test_manual_order.py verify all four forbidden Save evidence gates remain PASS.

## B2: one-shot hold bypass and terminal settlement
Code: src/launcher/manual_order.py:69 ManualRetryHolds / finalize at105;
src/launcher/backend.py:1088 manual quote invocation / returned canonical tuple at792;
src/workflow/v13_integration.py:135 close_many atomic old-key settlement.
Bound match:hold key exactly selected inquiry_id. Unbound match:unresolved key observed_identity
exact worksheet (spreadsheet + title) and original row_position; no MPN/brand/quantity fuzzy matching.
Matching old holds remain durable active and are hidden only from this selected invocation.
Other inquiries/locations stay outside the scoped reader/adapter and are untouched.
After exactly one selected terminal result returned by canonical integrated cycle:
- NO_RECENT_QUOTE, UPDATED_INSERTED, UPDATED_ALREADY_EXISTS:atomic close of matched old keys.
- ROW_FAILED:canonical hold delegate persists/records new key; verify durable active current reason
  first, then close old keys excluding all new/current keys. Same bound key is never closed.
- GLOBAL_STOP/exception/interruption/empty result:old barrier retained; no premature close.
- DB fault during old-key batch closure:transaction rollback retains all previous barriers.
SOURCE_STATUS_NOT_UPDATED unchanged exact model/brand/quantity refuses before bypass, including
matching unbound holds. Changed source follows existing manual rule and same settlement logic.
Existing automatic cycle/hold semantics and underlying singleton durable hold store unchanged.

Regression tests/launcher/test_rfq008_hold_lifecycle.py (27 PASS):
- bound/unbound + NO_RECENT_QUOTE and both update successes:old barrier closes after settlement;
- next normal cycle can check repaired/no-quote source; selected reader only original row;
- bound/unbound + global/unknown/interruption/empty result:old barrier remains, normal cycle blocked;
- new ROW_FAILED:same bound key current reason/episode retained; unresolved→bound leaves only new hold;
- missing new durable failure hold refuses closure; SQLite mid-close failure rolls back both old keys;
- other inquiry/worksheet/different-row holds bytewise unchanged;
- same snapshot no-repeat, edited snapshot allowed, invalid source status gate:PASS.

## Final verification
Focused final451 PASS (required manual/store/flow/gui/sheets/RFQ003/004/005/006/007 suites).
Full safe/offline:1507 PASS /1 SKIP (SMTP guard active).
Ruff:PASS. git diff --check:PASS.
V1.3 BuildOnly:PASS; frozen --self-check:PASS; release scan:RELEASE_SCAN_OK.
New candidate SHA256:7ECE6917BF77E263E1E56BC528A63EE0798404DB1D03D494499B94A4A16B663F.
Superseded candidate (DO NOT DEPLOY):136902DD75B3C7F4B25BAECEE70D95174CEC7AD61CA6AB4B158726EC88E99EC1.

## Scope and release
Only B1/B2 production changes; accepted GUI edit/menu/counters/RAW writer/current reread/
S→A/120s waits/zero quote gap/fixed CDP/Script latch/SMTP/keepalive/scheduler remain unchanged.
No dependency/second browser/identity/purchase/quote/alert/hold system.
Prior GUI historical-source-view limitations remain as reviewed; no added business task.
No new CEO/Owner business-rule conflict discovered.
No historical order replay, real procurement, Save/Save-and-Send, quote input/write, 更新报价,
Apps Script, real SMTP, actual source business mutation or current EXE deployment executed.
New candidate is BuildOnly, installed release untouched. REVIEW_REQUIRED only, never REVIEWED_DONE.
RFQ-008 resubmitted for CEO independent Review.
