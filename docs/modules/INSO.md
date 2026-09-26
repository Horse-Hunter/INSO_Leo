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

`button#win_btn__dialog11` with text `保存数据` remains
`AI_IMPORT_SEMANTICS_UNCONFIRMED`; it is not clicked, registered, or used by
purchase automation. CEO's revised flow validates the AI preview, then writes
the validated preview values into the blank parent form through the separate
`ParentProductFields` seam and exact-reads them back. The seam exposes only
`set_model`, `set_brand`, `set_quantity`, and matching read methods.

`CoordinatorPurchaseDraftWriter.prepare()` now sequences draft/customer/routing/
purchaser/AI recognition, uses Workflow's existing exact validator before
touching parent product fields, writes the validated AI values, and validates
the parent read-back with the same rule. It returns `AI_RECOGNIZED` only after
both checks pass. It has no Save or Send method. Tests use a fake parent adapter;
no live selector implementation exists. Parent model/brand/quantity selectors
remain UNKNOWN, so status is `CODE READY / LIVE FIELD SELECTORS PENDING` and
production composition requires the explicit parent-field seam to be supplied.

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
- local-CDP lease identity and parent-field selectors with unique/visible/
  actionable checks, empty initial state, and synthetic write/read-back;
- unique live `#btnSave` semantics and saved-record read-only identity/reconciliation;
- explicit Owner authorization for the first real Save.

No Save, Save-and-Send, Send, SMTP, Sheets write, or production migration was
performed in this closeout. CEO performs the daily Safety Review; the production
write gate remains CLOSED.
