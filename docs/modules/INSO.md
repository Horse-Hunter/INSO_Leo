# INSO Module — V1.2

## Scope

`src/inso` contains the shared-session lease, allowlisted action boundary, a
prepare-only read-only inspector, and a minimal live-capable purchase
preparation adapter. The adapter uses exact observed selectors and defaults to
the closed production gate. It has no Save Data or Send method, registers no
Save selector, and leaves AI result selectors unimplemented until verified.

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
`InsoPurchaseWriter` exposes only new draft, customer, purchaser, importance,
AI input/recognition, and a read-result contract. The separate inquiry-type
setter fails closed. `#btnSave`, `#btnSave2`, and `#bcSend` are denied in this
writer. Save-and-Send and Send remain prohibited in every stage.

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

The form and type checks used the explicitly selected Edge tab and a blank Add
form. No real customer, model, or order data was entered.

- The blank form labels `采购人员` beside text input `#UserName_text`
  (placeholder `请选择...`) with backing hidden input `#UserName`. The separate
  `业务员` field is `#OwnerID_text` with backing hidden input `#OwnerID`; it is
  not the purchaser field.
- The form has label `重要程度` and text input `#ImpValueF` (placeholder
  `请输入或选择...`). No field or hidden field labeled `询价类型` was found.
  Clicking the empty input opened its associated
  `.select-menu-modal .select-menu-item` popup with exact options
  `需要问全价格` and `普通询价`. This is confirmed as an `重要程度` field; the
  UI label is not `询价类型`. The writer does not operate this field and
  leaves `SET_QUOTATION_TYPE` fail-closed.
- `#btnSave` is a visible button with exact text `保存`; `#btnSave2` is a
  visible button with exact text `保存并发送`. `#bcSend` is a separate send
  control observed on an existing record. None was activated. They remain
  forbidden except the specifically gated Save Data action in a future,
  separately reviewed writer; Save-and-Send and Send stay prohibited.
- `#ai_import_` is a visible button with inline handler attribute
  `ai_import()`. It did not leave the embedded AI dialog visible in this
  session. The dedicated AI page was opened directly on an independent blank
  tab; page load alone showed no persistent record or save action.
- On `/skins/etaoerp/product/Import_ai.aspx`, `textarea#paste-area` accepted
  the exact authorized synthetic string `TEST-MPN-001      TEST-BRAND      123`.
  `button#ai-recognize` had visible text `AI 智能识别` and was clicked once. A
  JavaScript alert appeared; after dismissing it, the page still showed its
  empty-result prompt, the button text had not changed to `重新识别`, and no
  result fields were populated. Recognition therefore did not reach an
  observable ready result. No retry was made.
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
- No separate `询价类型` field exists in the observed form. The confirmed
  choices live under `重要程度` / `#ImpValueF`; do not label that control as a
  separate inquiry-type field.
- AI result selectors/values and deterministic ready state. The single
  synthetic recognition attempt did not produce an observable result. The
  writer result reader therefore fails closed until a result selector is
  verified.
- A newly saved draft's stable identity and post-save read-back of status/time.
- Safe, repeatable screenshot crop/redaction.

Do not treat these observations as production writer approval. AI result
read-back and saved-record reconciliation remain unresolved before any Save.
Lease/CDP identity is a required runtime acceptance immediately before the
first real Save, not a current coding blocker. No write gate is enabled. Save
Data, Save-and-Send, and all send controls remain unavailable in this writer.
