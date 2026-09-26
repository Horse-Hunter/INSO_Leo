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

### Verified read-only discovery — 2026-09-26

Owner authorized read-only access in the already signed-in browser. Inspection
used the explicitly selected existing Edge tab and DOM reads only. No new page
was opened, no form was opened, no controls were clicked, and no query or
business action was submitted. The browser account/context identifiers exposed
by the application code's `InsoSessionLease` were not available through this
inspection path, so these findings are page observations, not a live lease
verification.

Observed application entry:

- Origin: `https://yingsuo.alperp.cn`
- Top page: title `英索实业`, path `/`
- Active embedded page: title `1.业务询价`, frame id `iframe_YeWuXJ_frame`,
  path `/skins/etaoerp//InnerEnquiry/YeWuXJ/List.aspx`
- Existing logged-in application shell and page content were visible. Account
  and company identity were not independently verified.

Observed history/list query seam:

- One visible model text input: `#DetailFieldValue`; the adjacent field selector
  is `#DetailField_text` and displayed `型号`.
- One visible query button `button#select_btns`, accessible text `查询`.
- The search UI contains `左匹配` and `精确` checkboxes. At inspection time,
  `左匹配` was checked and `精确` was unchecked. No search was submitted, so
  exact-match backend behavior is not verified.
- The visible business inquiry result table includes inquiry number, model,
  brand, quantity, and time columns, along with other business fields. No row
  data was retained in this repository.
- Visible result rows have DOM ids shaped like `<digits>_Main`, unique within
  the current table. The row DOM id and the numeric argument in its detail link
  did not match in the inspected rows. This is only an in-page row identity
  candidate; persistence across queries/reloads and its meaning are unverified.
- The timestamp column had no `aria-sort` value. Stable ordering for equal
  timestamps is `UNKNOWN`.

Observed control metadata on the currently open list page:

- `新增`: one visible `button#product_add_`, native `button` type, accessible
  name from text. It was not clicked.
- The customer, inquiry type, purchaser, AI entry/input/recognition/result, and
  save controls were not present in the inspected list view. Opening the form
  would require the explicitly prohibited `新增` action; their metadata and
  AI read-back fields therefore remain `UNKNOWN`.
- `保存数据` and `保存并发送` were not inspected in a form. Their live
  selectors and semantics remain `UNKNOWN`; this does not relax the permanent
  prohibition on Save-and-Send.
- Saved draft id, same-record fields, and status read-back feasibility remain
  `UNKNOWN`; no record was saved or opened for post-save inspection.

No screenshot was captured. The visible list contains unrelated customer and
commercial details, so a full-page image would not be safe evidence. Whether a
header-only crop can be reliably isolated and redacted remains `UNKNOWN`.

### Remaining UNKNOWNs

- Exact search behavior and whether its precise-match filter can safely serve
  duplicate lookup.
- A stable historical record identity and deterministic tie-break for equal
  timestamps.
- Authenticated account/company identity and browser/context/page ownership
  as verified by `InsoSessionLease` on the live endpoint.
- Metadata for all purchase-form controls; AI recognition readiness and exact
  result-field read-back.
- A stable saved-draft identity and same-record read-back fields/status.
- Safe, repeatable evidence crop/redaction.

Do not mark discovery ready for production selectors or writes from these
partial page observations. Any missing form details require a separately
authorized, read-only inspection path that does not click `新增` or execute AI
actions.
