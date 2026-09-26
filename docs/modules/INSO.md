# INSO Module — V1.2

## Scope

`src/inso` now contains additive fake-only safety contracts for shared browser
ownership, allowlisted purchase actions, and a separately bounded read-only
discovery protocol. It contains no live duplicate-history adapter, selector
registry for production controls, Save Data writer, or Save-and-Send capability.

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

This wiring restores the existing V1.1 INSO read-only Research source. It does
not add an INSO purchase writer, live discovery selectors, or any new external
write capability. Do not restore arbitrary CDP context/page enumeration to
regain availability.

## Write safety seam

The closed `WriteAction` enum includes only the explicitly allowlisted draft
actions through `SAVE_DATA`. There is no `SEND`, `SUBMIT`, `FINAL_SUBMIT`, or
`SAVE_AND_SEND` enum member or public method. `InsoDraftActions` exposes only
business-named methods; it resolves a unique exact selector within a verified
scope, rejects deny-listed identities, re-reads semantic role/name/text/stable
attributes before dispatch, and raises `SecurityViolation` on drift or
ambiguity. The production feature gate is unconditionally closed. The only
dispatcher exercised by tests is fake.

The current Stage 2A action boundary is not a production WRITE ALLOWLIST
approval. Page/current-order identity, current/target values, approved selectors,
read-back, Save Data recovery and evidence rules need independent Safety
Supervisor review. Save-and-Send remains prohibited in every stage.

## Discovery and UNKNOWNs

`ReadOnlyDiscoveryInspector` accepts only a protocol with metadata-reading
methods. It has no click, fill, clear, save, send, Sheets writer, or SMTP method.
The inspector remains a prepare-only seam; it was not used to control the live
browser in the discovery below.

### Verified read-only interactive discovery — 2026-09-26

Owner authorized non-persistent read-only interactions in the already signed-in
browser. Inspection reused the explicitly selected Edge tab and read DOM
metadata. It did not save, send, run AI recognition, or modify business data.
The application `InsoSessionLease` browser/context identity was not available
through the selected-tab inspection path; these are observed UI facts, not a
live lease verification.

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
- Live `InsoSessionLease` endpoint, browser, context, and operation-page
  ownership verification.
- Whether the blank-form page has controls corresponding to the intended
  inquiry type and purchaser fields.
- AI recognition output selectors/values and a deterministic ready state; AI
  recognition was deliberately not executed.
- A saved draft's stable identity and post-save read-back of status/time.
- Safe, repeatable screenshot crop/redaction.

Do not treat these observations as production writer approval. No write gate is
enabled. Save Data, Save-and-Send, and all send controls remain prohibited.
