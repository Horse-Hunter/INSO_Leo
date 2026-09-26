# INSO Module — V1.2

## Scope

`src/inso` contains the shared-session lease, read-only duplicate history
adapter, prepare-only inspector, and minimal purchase adapter. The purchase
adapter uses exact observed selectors and defaults to the closed production
gate. It has one durable-before-dispatch Save Data path for the uniquely
verified `#btnSave`; it has no Save-and-Send or Send path.

## Session ownership contract

The launcher/composition root attaches Research to the configured CDP endpoint
and proceeds only when it exposes exactly one context. It never enumerates or
selects an existing tab. The root creates an `InsoSessionLease` with explicit
endpoint, browser, context and operation-page identities, and records
`APP_OWNED` or `REUSED`. Research receives only `InsoOperationAccess` and uses
lease-created child pages. A reused browser is disconnected from Playwright
after the cycle but is never closed; an app-owned browser closes only after its
child pages drain and the launcher confirms the cycle is drained. Stale or
mismatched identity fails closed.

This wiring restores the existing V1.1 INSO read-only Research source. The
V1.2 preparation adapter requires explicit lease-created form and AI operation
pages; it does not select arbitrary tabs or close the reused browser. The
production gate remains closed. Before the first real Save, the final local CDP
runtime must pass endpoint/browser/context/operation-page acceptance. That
runtime acceptance is not a blocker for the current code preparation task.

## Write safety seam

The closed `WriteAction` enum includes only the explicitly allowlisted draft
actions through `SAVE_DATA`. There is no `SEND`, `SUBMIT`, `FINAL_SUBMIT`, or
`SAVE_AND_SEND` enum member or public method. `InsoDraftActions` exposes only
business-named methods; it resolves a unique exact selector within a verified
scope, rejects deny-listed identities, re-reads semantic role/name/text/stable
attributes before dispatch, and raises `SecurityViolation` on drift or
ambiguity. The production feature gate is unconditionally closed. The only
dispatcher exercised by tests is fake.

The current action boundary is not production Save Data authorization.
`InsoPurchaseWriter` exposes new draft, customer, purchaser, quotation routing,
AI input/recognition, AI result reading, and the gated Save Data path. Business
`quotation_type` maps to
the observed `#ImpValueF` control, labeled `重要程度`. Its exact allowlist is
`需要问全价格` and `普通询价`; both were selected and read back on separate
blank forms. The writer rejects every other popup value. Save Data is bound
only to `button#btnSave` with exact button name and visible text `保存`; it must
be unique, visible, and enabled. `V12Store.begin_save_dispatch()` runs after
that preflight and before the private dispatch re-check/click, so any
uncertainty after the boundary remains `UNKNOWN_WRITE_OUTCOME`. `#btnSave2`
and `#bcSend` have no binding or action path. Save-and-Send and Send remain
prohibited in every stage.

The verified AI result reader requires `button#ai-recognize` text
`重新识别`, exactly one row under `#preview-body`, and one input per field:
`input[data-f="PartNo"]`, `input[data-f="Brand"]`, and
`input[data-f="Qty"]`. It returns raw model and brand strings plus a positive
integer quantity; canonical equality checks remain in Workflow. No result is
returned when the ready state, row count, field uniqueness, or quantity cannot
be confirmed.

### AI result import to parent — 2026-09-26

On a blank inquiry form, the embedded `AI录单` panel accepted the public
generic input `LM358      Texas Instruments      123`. Recognition completed;
the button changed to `重新识别`, and the one preview row read back those three
values. The footer control was `保存数据` (`win_btn__dialog11`), not an observed
`导入到单据` action. It was not clicked. The parent detail row remained blank,
so the AI-to-parent import operation and exact parent read-back remain UNKNOWN.
No import selector or method is enabled in the writer. The screenshot used to
inspect the panel was not saved as evidence or committed.

### Launcher composition and Save reconciliation

`ProductionBackend` has an explicit V1.2 composition seam that wires
`V12WorkflowCoordinator`, the duplicate checker, purchase draft adapter, and
`V12NotificationWorker`/transport only when a complete live adapter bundle is
provided. No fake adapters are substituted. This checkout has no
coordinator-compatible live purchase `prepare` adapter (`InsoPurchaseWriter`
still lacks the verified parent-import step), settled duplicate reader, or
canonical research-facts provider;
the V1.2 coordinator therefore remains uncomposed in the default production
runtime, and the existing V1.1 poller/worker is unchanged. The production
writer gate remains closed.

The launcher calls the existing store reconciliation contract. Without a
verified saved-record reader, the fallback returns typed `UNKNOWN`; the store
records manual review. It never infers absence and never retries Save Data.

## Discovery and UNKNOWNs

`ReadOnlyDiscoveryInspector` accepts only a protocol with metadata-reading
methods. It has no click, fill, clear, save, send, Sheets writer, or SMTP method.
The inspector remains a prepare-only seam; it was not used to control the live
browser in the discovery below.

### Verified read-only interactive discovery — 2026-09-26

Owner authorized non-persistent read-only interactions in the already signed-in
browser. Inspection reused the explicitly selected Edge tab and read DOM
metadata. It did not save, send, or modify business data. One AI recognition
attempt using the authorized synthetic input is described below.
The application `InsoSessionLease` browser/context identity was not available
through the selected-tab inspection path; these are observed UI facts, not a
live lease verification. Follow-up findings from the final discovery attempt
are recorded below.

Observed application/page identity:

- Origin: `https://yingsuo.alperp.cn`; top page title `英索实业`, path `/`.
- Inquiry list is embedded as frame id `iframe_YeWuXJ_frame`, title
  `1.业务询价`, path `/skins/etaoerp//InnerEnquiry/YeWuXJ/List.aspx`.
- The existing logged-in shell was usable. Account/company identity and the
  CDP endpoint/browser/context identity under `InsoSessionLease` remain
  `UNKNOWN`.

Observed history query behavior:

- Model input `#DetailFieldValue`; field selector `#DetailField_text` showed
  `型号`; query control `button#select_btns` showed `查询`.
- `#nolike` is the `精确` checkbox and `#leftlike` is `左匹配`. A full-model
  test query in exact mode returned rows whose displayed model exactly equaled
  the query. A prefix-only query in exact mode returned no final rows; the same
  prefix in left-match mode returned rows beginning with that prefix. This
  supports strict equality for the tested examples only; complete server-side
  semantics and all edge cases remain `UNKNOWN`.
- The result table exposes inquiry number, model, brand, quantity, and time.
  No business row values were retained in Git.
- Result row DOM ids use `<digits>_Main` and were unique in the observed result
  set. A detail link uses a numeric `Bill_View_Open(...)` argument that differs
  from the row DOM id. Persistence/stability of either identifier across
  searches or reloads is `UNKNOWN`.
- No equal timestamps occurred in the observed matching results. Deterministic
  tie-break behavior is `UNKNOWN`.

Observed blank-add-form metadata (opened then closed without filling or saving):

- `新增`: `button#product_add_`; it opened a blank form iframe at
  `/skins/etaoerp//sale/Enquiry/Bill.aspx` (title `客临时询价`) and did not
  immediately create a record in this observation.
- Customer input `#CompanyName` was empty. `OwnerID_text` is labeled `业务员`.
  No distinct `询价类型` or `采购员` control was found in the inspected form;
  mapping of requested workflow concepts to this page is `UNKNOWN`.
- `AI录单`: `button#ai_import_`; opening it displayed iframe
  `#winIframe_dialog1` at `/skins/etaoerp/product/Import_ai.aspx` (title
  `AI识别`).
- AI input: `textarea#paste-area`. The dialog had buttons `#ai-recognize`
  (`AI 智能识别`), `#fast-recognize` (`极速识别`), `#load-sample`
  (`载入示例`), `#clear-btn`, `#paste-btn`, and `#upload-btn`. Its visible
  `识别结果` heading had no populated result fields. Recognition was not run;
  result fields and deterministic ready/`重新识别` state are `UNKNOWN`.
- `保存`: `button#btnSave`; `保存并发送`: `button#btnSave2`. Neither was
  activated. An additional `发送` control `#bcSend` was present in the existing
  record view; it was not activated. These controls are deny targets for future
  writer review, not approved selectors.

### Final discovery follow-up — 2026-09-26

The form checks used the explicitly selected Edge tab and separate blank Add
forms. The AI checks used only the authorized synthetic input and one public
generic component string. No Save or Send action occurred.

- The blank form labels `采购人员` beside text input `#UserName_text`
  (placeholder `请选择...`) with backing hidden input `#UserName`. The separate
  `业务员` field is `#OwnerID_text` with backing hidden input `#OwnerID`; it is
  not the purchaser field.
- The form has label `重要程度` and text input `#ImpValueF` (placeholder
  `请输入或选择...`). No field or hidden field labeled `询价类型` was found.
  Clicking the empty input opened `.select-menu-modal .select-menu-item` with
  six options. The two business routing values are `需要问全价格` and
  `普通询价`. Each was selected on a different blank form and read back exactly
  from `#ImpValueF`; the form was closed without saving. Other popup options
  are not in the writer allowlist.
- `#btnSave` is a visible button with exact text `保存`; `#btnSave2` is a
  visible button with exact text `保存并发送`. `#bcSend` is a separate send
  control observed on an existing record. None was activated. They remain
  forbidden except the specifically gated Save Data action in a future,
  separately reviewed writer; Save-and-Send and Send stay prohibited.
- `#ai_import_` has inline handler attribute `ai_import()`. One click created
  an embedded `Import_ai.aspx?BillPage=Enquiry&VendorID=&h=510` iframe but it
  remained hidden. The form frame and its parent did not expose a readable
  `ai_import` function in the discovery context. No repeated button attempts
  were made.
- On `/skins/etaoerp/product/Import_ai.aspx`, `textarea#paste-area` accepted
  `TEST-MPN-001      TEST-BRAND      123`; recognition returned an alert and
  no results. With `LM358      Texas Instruments      123`,
  `button#ai-recognize` changed to `重新识别` and the result row exposed fields
  through `data-f="PartNo"`, `data-f="Brand"`, and `data-f="Qty"`. The result
  fields read back as the same public test values. The result-ready button and
  selectors are verified.
- The AI page includes `pasteImport() { AiImport.doImport(); }` as a parent-call
  hook. The discovery AI tab was opened independently and had no `window.opener`.
  Its `导入到单据` action was not activated. Because the embedded AI frame stayed
  hidden, AI-to-parent form propagation and parent model/brand/quantity read-back
  remain `UNKNOWN`.
- The earlier read-only history detail check compared one visible row's
  `<digits>_Main` DOM id and numeric `Bill_View_Open(...)` argument against its
  detail form's `BillID`. The row id differed from the argument, and the
  `BillID` value matched the link argument for that one opened record. A repeat
  open attempt timed out before confirmation. This is a one-record observed
  mapping, not proof of stable identity across repeated opens, queries, or
  reloads.
- The selected tab is controlled through the Edge extension path, not the
  launcher's CDP connection. `runtime/research.json` was absent, so no configured
  lease endpoint was available. The code default `http://127.0.0.1:9222` was
  unreachable. No `InsoSessionLease` was created; this is a runtime acceptance
  required before the first real Save, not a blocker for current coding.
- Existing detail structure still offers a populated `BillID`, read-only
  `PENO`, and model/brand/quantity fields, while the list shows model, brand,
  quantity, and time. Save-after identity correlation, status, and creation
  time remain unverified.

No screenshot was captured. No Save, Save-and-Send, Send, SMTP, Sheets write,
or persistent INSO operation occurred. Blank forms and the independent AI tab
were closed.

### Duplicate reader integration — 2026-09-26

Cherry-picked `fafc6b7f3101ff0c69c1872a9f094e2148398903`. The public
`InsoDuplicateHistoryReader` consumes `InsoOperationAccess`, and
`InsoDuplicateHistoryChecker` implements the existing Workflow `DuplicateChecker`
seam by delegating business rules to `evaluate_duplicate_history`. It can be
injected into `V12WorkflowCoordinator`; production composition accepts it only
as an explicit adapter, but the current live reader remains unavailable because
query settlement and row extraction are unresolved. The rules already return
`AMBIGUOUS` when multiple latest records share a timestamp.

Read-only DOM inspection of the rendered list found the result layout table
`#_id_dg`; model, quantity, and time correspond to cells 9, 11, and 14
(`td:nth-child(9/11/14)`). A search for the synthetic `TEST-MPN-001` in exact
mode returned no results; the completed empty state showed `.layui-table-none`,
no row nodes, and a zero count. This confirms the empty-query state only. A
reliable completion signal for nonempty results and the concrete live row
extractor are not yet implemented, so these seams remain fail-closed.

Observed existing-record/read-back structure (opened read-only from the history
list, then closed without changes):

- Existing form iframe is the same `/sale/Enquiry/Bill.aspx` path. Its fields
  included `BillID` (populated text input) and `PENO` (populated read-only text
  input). Their values and customer/order details were not retained.
- Visible form structure included customer, inquiry date, importance, model,
  brand, and quantity fields. The list itself displays model/brand/quantity/time.
- The opened record could not be safely correlated to a stable list/link identity
  using the current observations. Newly saved record identity, same-record
  read-back, status, and creation-time feasibility remain `UNKNOWN`.

No screenshot was captured. The live page contained unrelated business details;
safe crop/redaction feasibility remains `UNKNOWN`.

### Remaining UNKNOWNs

- Whether exact search is guaranteed strict server-side equality for all input
  cases; only the tested full and prefix examples were observed.
- Stable historical record identity, relationship between list/link/detail
  identifiers, and deterministic equal-timestamp tie-break.
- Repeated stability of history row/link/`BillID` mapping across opens, queries,
  or reloads.
- Final local-CDP lease acceptance before the first real Save. The current
  extension session did not expose lease identities; this does not block
  prepare-only coding.
- `#ImpValueF` is labeled `重要程度` but has the two exact business routing
  values. The writer maps quotation routing to this control by CEO decision.
- AI result-to-parent-form import and read-back. AI result page selectors/readiness
  are verified; callback propagation is not.
- Reliable nonempty history-query settlement and concrete row extraction.
- A newly saved draft's stable identity and post-save read-back of status/time.
- Safe, repeatable screenshot crop/redaction.

Do not treat these observations as production writer approval. AI-to-parent
import and saved-record reconciliation remain unresolved before any Save.
Lease/CDP identity is a required runtime acceptance immediately before the
first real Save, not a current coding blocker. The production gate remains
closed. `#btnSave2` and all send controls remain unavailable in this writer.
