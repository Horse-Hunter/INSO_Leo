# Current Task — V1.2 PRE_SAVE closeout

Status: PRE_SAVE_READY / REAL_SAVE_GATED

## Done

- WorkBuddy duplicate reader `441b984db4703deeae66bda2878398a3f01b92de` was cherry-picked as `9c7e621`.
- The live duplicate adapter reads `#_id_dg` model/quantity/time cells 9/11/14 and verifies the detail `BillID` identity. It delegates all duplicate semantics to `evaluate_duplicate_history`.
- Query settlement remains `QUERY_SETTLEMENT_UNCONFIRMED`; the live result therefore remains unavailable and cannot be treated as nonduplicate. Creator and INSO quote selectors default to `None`.
- A launcher `ResearchExcelFactsProvider` now reads the persisted canonical Research workbook snapshot by inquiry identity. It does not run searches or recalculate Research rules; missing/unreadable facts return `None`.
- V1.2 adapter construction can bind the existing `QQSMTPTransport` to an explicit `QQSMTPConfig.sender_address`, recipients and credential provider. This performs no SMTP operation. The production write gate remains closed.
- Existing exact quotation routing, purchaser allowlists, durable UNKNOWN-before-click Save path and UNKNOWN/manual reconciliation seam remain unchanged.
- First real Save still requires explicit complete adapters. No production adapter is substituted with a fake.

## AI import and purchase prepare

- The signed-in UI currently shows AI recognition ready for the public generic test values. The “保存数据” footer control's static callback could not be inspected: the browser security policy rejected `view-source:` and prohibits equivalent workarounds.
- The control was not clicked. Parent-form import and exact parent model/brand/quantity read-back remain UNKNOWN. No import selector was guessed.
- A coordinator-compatible production `PurchaseDraftWriter.prepare()` is not ready until that import/read-back path is verified. Current low-level `InsoPurchaseWriter` remains prepare-only in intent but has no verified parent import operation.

## Required acceptance before first real Save

- Nonempty duplicate query settled signal, creator selector, and INSO quote selector.
- Local CDP endpoint, browser/context and lease-owned operation-page identities; reused browser must remain open.
- AI preview-to-parent import and exact parent read-back.
- Live `#btnSave` uniqueness/semantics and reliable read-only saved-record identity/reconciliation.
- Owner's explicit authorization for the first real Save.

## Verification and side effects

- No Save Data, Save-and-Send, Send, SMTP, Sheets write, production migration, or production smoke occurred.
- Verification results for the current change are recorded in the delivery report.
- V1.1 Research behavior and its canonical rules are unchanged.

CEO performs the daily Safety Review. Keep the production write gate CLOSED.
