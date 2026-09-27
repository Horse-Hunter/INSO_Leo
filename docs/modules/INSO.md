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
`AMBIGUOUS` outcome. The browser settlement contract is verified: the matching
`List_Detail` response completes, the `dg` request sequence advances,
`_select_pending` is false, the query button is enabled, and both
`table.cache.dg` and `#_id_dg` reflect that response. A checked native exact
checkbox serializes as `nolike=on`. The production adapter still fails with
`QUERY_SETTLEMENT_UNCONFIRMED` until it can execute this through the same
verified shell/frame boundary. Creator and INSO quote selectors remain unset
(`None`); no column is guessed.

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

Read-only detail inspection confirms unique visible cells at
`#_id_dg td[data-field="PartNo"]`, `Brand`, and `Qty`, backed by the detail-table
cache. This is only a read-back contract: a blank form starts with no product
row, so no live parent-field writer is enabled. `ai_import()` has an in-memory
callback, but its runtime panel opening returned a generic form submission
error. No AI recognition, import, synthetic input, or retry occurred; live AI
selectors remain UNKNOWN.

The existing gated Save boundary remains closed. If later authorized, it requires
one visible, enabled `button#btnSave` with exact semantics `保存`, records durable
`UNKNOWN_WRITE_OUTCOME` before the private click, and re-resolves the control
before dispatch. An uncertain result is never saved a second time automatically.
There is no executable path for `#btnSave2`, `#bcSend`, Save-and-Send, or Send.
Without a verified read-only saved-record reader, reconciliation remains
UNKNOWN/manual review and never infers “not saved” from absence.

For an existing record, the list's `Bill_View_Open(BillID, ...)` link was
verified against detail `#BillID`. The detail exposes PENO, customer, purchaser,
importance, inquiry time, and product MPN/brand/quantity. The row DOM id is
distinct from BillID and cannot substitute for it. This supports read-only
inspection once an identity is known, but a newly saved record has no verified
BillID return/read-back; post-Save reconciliation remains UNKNOWN/manual review.

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

## Live read-only facts — 2026-09-27

The authenticated Chrome runtime exposes exactly one context. The existing INSO
shell was identified by its expected origin/title and a unique `main` frame at
`InnerEnquiry/YeWuXJ/List.aspx`; this was discovery-only and does not relax the
lease rule for production adapters. The lease itself can create an
operation-owned child page while preserving the reused browser.

On that list frame, `#DetailFieldValue`, `button#select_btns` (`查询`),
`button#product_add_` (`新增`), and `#_id_dg` are unique and visible. The native
`#nolike` exact checkbox is not actionable and was not force-clicked. The
scoped grid headers confirm `PartNo`, `Qty`, and `PEDate`. `OfferPrice` is
visibly labelled `报价`, but it is not yet proven to be the required INSO quote;
creator and equal-timestamp tie-break remain UNKNOWN. BillID is the verified
list-to-detail identity.

`新增` was verified from its loaded handler to open an unsaved temporary-inquiry
dialog. Its form has unique, visible `#CompanyName`, `#ImpValueF`,
`#UserName_text`, and `#ai_import_`; `#btnSave` is visible with exact text
`保存`. `#btnSave2` is visibly `保存并发送`, and `#bcSend` is `发送`; both remain
hard-forbidden. The empty form has no product rows. Existing-detail parent
read-back selectors are verified, but a live writer remains disabled.
`ai_import()` has an in-memory callback, but its runtime panel open failed with
a generic form error; no recognition, import, input, or retry occurred. BillID
and PENO are verified on an existing detail, while saved-record read-back after
a future Save remains unproven. The write gate remains CLOSED.

## Runtime browser baseline — 2026-09-26

The canonical production browser is Chrome (`browser.channel = "chrome"`) as
in V1.1 and V1.2. Edge and `runtime/browser-profile` were an accidental runtime
drift and are retained only as a backup; they are not used for production
acceptance. V1.1's final integration task identifies the existing dedicated
Chrome CDP profile as Git-ignored `.browser-profile/cdp`. That original profile
was found and left in place without copying, clearing, or migrating it.

The ignored `runtime/production.json` now points to the installed Chrome
executable, that original profile, and port 9222. `runtime/research.json` remains
unchanged. Chrome policy values `RemoteDebuggingAllowed` and `UserDataDir` were
NOT_SET in the inspected HKLM/HKCU policy locations. The V1.1 packaged
`--self-check` passes but deliberately does not launch Chrome. Calling V1.1's
exact `_launch()` from the current diagnostic process uses the same executable,
profile, port, remote-debugging arguments, startupinfo, creation flags, and
redirected standard handles as the V1.1 production boundary; it exits before
CDP is ready in the same way as V1.2.

The current diagnostic token is `LEO229\CodexSandboxOffline` at Medium
integrity, whereas the original profile and accepted V1.1 smoke belong to
`LEO229\Leo`. The sanitized GPU child-process access denial is classified as
`DIAGNOSTIC_EXECUTION_CONTEXT_MISMATCH`, not as a V1.2 Chrome blocker or a
profile/login failure. The owner-known packaged Windows runtime remains the
acceptance environment. No Chrome workaround flags, security changes, or profile
changes were made. INSO login state is UNKNOWN, not `OWNER_LOGIN_REQUIRED`.

The earlier Edge CDP and `/login.aspx` observations are historical and do not
establish Chrome authentication. Do not ask the Owner to log in until the
original Chrome profile has actually been opened through a working Chrome CDP
session and redirects to `/login.aspx`. Phase A remains pending in the
Owner-known runtime; duplicate settlement/creator/quote, purchase selectors,
Save control semantics, and saved-record reconciliation remain UNKNOWN.
Production write gate remains CLOSED.
