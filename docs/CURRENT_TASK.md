# Current Task — V1.2 PRE_SAVE closeout

Status: PRE_SAVE_READY / REAL_SAVE_GATED
CODE READY / LIVE FIELD SELECTORS PENDING

## Done

- WorkBuddy duplicate reader `441b984db4703deeae66bda2878398a3f01b92de` was cherry-picked as `9c7e621`.
- The live duplicate adapter reads `#_id_dg` model/quantity/time cells 9/11/14 and verifies the detail `BillID` identity. It delegates all duplicate semantics to `evaluate_duplicate_history`.
- Query settlement remains `QUERY_SETTLEMENT_UNCONFIRMED`; the live result therefore remains unavailable and cannot be treated as nonduplicate. Creator and INSO quote selectors default to `None`.
- A launcher `ResearchExcelFactsProvider` now reads the persisted canonical Research workbook snapshot by inquiry identity. It does not run searches or recalculate Research rules; missing/unreadable facts return `None`.
- V1.2 adapter construction can bind the existing `QQSMTPTransport` to an explicit `QQSMTPConfig.sender_address`, recipients and credential provider. This performs no SMTP operation. The production write gate remains closed.
- Existing exact quotation routing, purchaser allowlists, durable UNKNOWN-before-click Save path and UNKNOWN/manual reconciliation seam remain unchanged.
- First real Save still requires explicit complete adapters. No production adapter is substituted with a fake.

## AI preview and parent product fields

- `AI_IMPORT_SEMANTICS_UNCONFIRMED` remains recorded for `button#win_btn__dialog11` (“保存数据”). CEO's decision removes it from automation and the purchase prepare flow; it is not a blocker.
- Added `ParentProductFields` with only model/brand/quantity set and read methods, plus a coordinator-compatible `CoordinatorPurchaseDraftWriter.prepare()`. It validates preview with the existing Workflow rule before writing parent fields, then reads back and validates again.
- No production parent-field adapter is implemented because its selectors are UNKNOWN. `V12ProductionAdapters` requires the coordinator writer, which itself requires the explicit parent-field seam; without verified live fields no production purchase prepare can be composed.
- Prepare does not expose Save or Send and does not refer to `win_btn__dialog11`.

## Required acceptance before first real Save

- Local CDP endpoint, intended browser/context, lease and operation-page identity; reused browser remains open.
- Parent model/brand/quantity selectors are unique, visible/actionable, initially empty, and exact-read-back after synthetic fill.
- Duplicate nonempty query settled signal, creator selector, and INSO quote selector.
- Live `#btnSave` uniqueness and exact semantics, plus saved-record read-only identity/reconciliation.
- Owner's explicit authorization for the first real Save.

## Verification and side effects

- No Save Data, Save-and-Send, Send, SMTP, Sheets write, production migration, or production smoke occurred.
- Verification results for the current change are recorded in the delivery report.
- V1.1 Research behavior and its canonical rules are unchanged.

CEO performs the daily Safety Review. Keep the production write gate CLOSED.
