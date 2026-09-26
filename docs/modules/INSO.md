# INSO Module — V1.2

## Scope and session ownership

`src/inso` provides the explicit INSO session lease, read-only duplicate-history
adapter, and purchase draft actions. The launcher owns CDP/browser lifecycle.
Adapters receive lease-created operation pages; they cannot close a reused
browser or select an arbitrary existing tab. The first real Save still requires
local runtime acceptance of endpoint, browser, context, and operation-page
identity.

## Duplicate history

`PlaywrightDuplicateHistoryPage` is the live read-only row adapter for result
table `#_id_dg`. The verified fields are model `td:nth-child(9)`, quantity
`td:nth-child(11)`, and time `td:nth-child(14)`. The reader verifies detail
`BillID` against the numeric `Bill_View_Open(...)` argument for the record it
opens. No stable tie-break for equal timestamps has been verified.

`evaluate_duplicate_history` remains the only owner of canonical MPN matching,
the inclusive 168-hour window, latest record selection, and equal-time
`AMBIGUOUS` outcome. The live page adapter fails with
`QUERY_SETTLEMENT_UNCONFIRMED` because a nonempty settled signal is not verified.
Creator and INSO quote selectors remain unset (`None`); no column is guessed.
Consequently the production duplicate check stays unavailable until settlement
is verified, and an unavailable result never means nonduplicate.

## Purchase draft and Save boundary

Business quotation routing maps to `#ImpValueF` (visible label `重要程度`),
with exact allowlisted values `需要问全价格` and `普通询价`. Customer is limited
to `Win Source Elec. Tech. Ltd`; purchasers are `颜浩坚` and `陈熙`.

The AI preview reader requires `button#ai-recognize` text `重新识别`, one row at
`#preview-body > tr`, and unique fields
`input[data-f="PartNo"]`, `input[data-f="Brand"]`, and
`input[data-f="Qty"]`. Workflow owns exact AI validation.

Parent import is not verified. On a fresh blank form, the accessibility tree
showed footer `button#win_btn__dialog11` with exact visible text `保存数据`.
The available browser interface did not expose `onclick`, form/formaction/type
attributes, or loaded JavaScript objects. No source-loading or alternate
inspection path was used. Whether this button only transfers preview values to
the parent form DOM remains UNKNOWN, so it was not clicked. Parent model/brand/
quantity selectors and exact read-back remain UNKNOWN. Therefore a live
coordinator-compatible `PurchaseDraftWriter.prepare()` is still pending; record
this seam as `AI_IMPORT_SEMANTICS_UNCONFIRMED`.

The existing gated Save boundary remains closed. If later authorized, it requires
one visible, enabled `button#btnSave` with exact semantics `保存`, records durable
`UNKNOWN_WRITE_OUTCOME` before the private click, and re-resolves the control
before dispatch. An uncertain result is never saved a second time automatically.
There is no executable path for `#btnSave2`, `#bcSend`, Save-and-Send, or Send.
Without a verified read-only saved-record reader, reconciliation remains
UNKNOWN/manual review and never infers “not saved” from absence.

## Production composition

`compose_v12_production` accepts explicit adapters only. The launcher now has a
`ResearchExcelFactsProvider` that reads the existing Research-owned persisted
snapshot by inquiry id; it does not re-search or recompute canonical business
rules and returns unavailable facts when data is missing or unreadable.
`V12ProductionAdapters.with_qq_smtp()` binds an explicit `QQSMTPConfig` (including
`sender_address`) to the existing QQ SMTP transport and requires explicit
recipients. Construction does not send mail. Production composition remains
disabled unless all actual adapters are supplied; fakes are not substituted.
V1.1 Research execution is unchanged.

## Before first real Save

Complete one local runtime acceptance covering:

- CDP endpoint, exactly one intended context, lease and operation-page identity;
- duplicate nonempty query settlement, creator selector, and INSO quote selector;
- AI preview import into a blank parent form and exact parent read-back;
- unique live `#btnSave` semantics and saved-record read-only identity/reconciliation;
- explicit Owner authorization for the first real Save.

No Save, Save-and-Send, Send, SMTP, Sheets write, or production migration was
performed in this closeout. CEO performs the daily Safety Review; the production
write gate remains CLOSED.
