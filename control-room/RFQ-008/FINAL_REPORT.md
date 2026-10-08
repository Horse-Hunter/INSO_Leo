# RFQ-008 CEO report
Status: REVIEW_REQUIRED. Prior RFQ-006/RFQ-007 REVIEWED_DONE unchanged.
Branch: feature/v1-3-integration; approved base7e4a63b0f74f4363053e90b12ef1835748a05cff.
Implementation commit: the commit containing this report (git log -1).

## Delivered
1. Current poll found/completed counters reset every15min cycle and update independently of history.
2. Double-click model/brand/quantity/importance: idle-only single-field editor, canonical schema,
   exact one-cell RAW Google write, fresh readback before GUI source projection. No source status edit.
3. Right-click purchase/quote selected row; serial existing poll thread rereads original worksheet/row.
   Purchase requires未发 + proven unsubmitted; sent/armed/clicked/unknown/pending remain blocked.
   Quote requires发给采购; canonical V13 quotation/read/write/Script/hold/notification code reused.
4. No parallel business runtime; one pending command, busy/stop rejection; full15min after completion.
5. Same inquiry and immutable historical events; original submitted purchase evidence not rewritten.
   V12 pause keeps independent V13 quotation, prior confirmed Script pending same source cannot repeat.

## Implementation locations
- src/gui/app.py: row context menu, four individual editors, asynchronous result display.
- src/gui/contracts.py: optional capability/command/result DTO, backward-compatible defaults.
- src/launcher/backend.py: per-poll counters, idle serial command boundary and canonical runner binding.
- src/launcher/manual_order.py: original-row scoped source reader, current quote projection, hold scope.
- src/sheets/google_writer.py: write_order_field reuses whitelist schema and _write_cell RAW.
- src/workflow/v12_flow.py: rerun_unsubmitted delegates existing process_pending.
- src/workflow/store.py: explicit retry input refresh through revive_item.
- src/workflow/v12_store.py: pre-submit evidence gate and narrow mutable projection reset.

## Verification
- New edit/menu/source/readback/single-row quote/purchase/dispatch-safety tests:45 PASS.
- First GUI/backend focused:168 PASS.
- Full safe/offline pytest:1475 PASS,1 SKIP; SMTP guard active, no production access.
- Final shared focused:523 PASS (GUI/Sheets/backend/keepalive/RFQ003/004/005/006).
- Ruff PASS; git diff --check PASS.
- V1.3 BuildOnly PASS; frozen --self-check PASS; RELEASE_SCAN_OK.
- Candidate SHA256:136902DD75B3C7F4B25BAECEE70D95174CEC7AD61CA6AB4B158726EC88E99EC1.
- Packaging generated files remain ignored; current installed EXE untouched.
- Existing asynchronous startup regression originally asserted between two durable writes;
  now waits for the same final INTERRUPTED_UNSENT assertion, without changing production behavior.

## Review / limits / UNKNOWN
Public GUI command contract and workflow manual retry entry require independent CEO review.
No architecture/dependency addition, no parallel purchase/quote/browser system; prior review files untouched.
Status gates deliberately preserve existing rules; source status never changed to enable retry.
SHAHAB importance fixedA/no physical cell: rejected explicitly rather than inventing a column.
Edits refresh inputs only; old research price is not recalculated until explicit rerun.
Google edits persist; GUI current-source overrides are session views. Restart historical audit may show
old saved input until a fresh selected-row action; historical purchase audit is intentionally retained.
Original worksheet/row is Owner-approved anchor; moved/replaced rows are not fuzzy-guessed.
UNKNOWN: live Google/GUI/CDP acceptance and deployment, intentionally not executed here.
No historical replay, real procurement, Save/Save-and-Send, quote write/更新报价, Apps Script,
actual business status mutation or real SMTP executed during verification.
RFQ-008 submitted for CEO independent Review; no self-approval.
