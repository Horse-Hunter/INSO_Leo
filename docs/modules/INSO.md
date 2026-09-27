# INSO Module — V1.2

## Scope and session ownership

`src/inso` provides the explicit INSO session lease, read-only duplicate-history
adapter, and purchase draft actions. The launcher owns CDP/browser lifecycle.
The lease pins the unique verified authenticated shell page and list frame as
the operation page; no child page is created. Each access rechecks browser,
context, page, origin, shell-frame and login-path identity. A reused shell page
and browser are never closed by the lease. APP_OWNED browser cleanup remains at
the composition root after the full cycle drains.

## Duplicate history

`PlaywrightDuplicateHistoryPage` uses the visible `#select_btns` query button
and the loaded native `search()`/form serializer in the verified authenticated
shell. It sets `#nolike` checked and `#leftlike` unchecked as form state only;
it never clicks either hidden control or hand-builds a request. The live
request used bracket-encoded `searchData[<field>]` keys and matched
`DetailField=PartNo`, the current target, and `nolike=on`. The response passed
settlement and row validation with an empty `rows` array. A nonempty response
is still needed to confirm creator and quote/currency. The verified list fields
remain model `td:nth-child(9)`, quantity `td:nth-child(11)`, and time
`td:nth-child(14)`. BillID remains the stable list-to-detail identity. No
stable tie-break for equal timestamps has been verified.

`evaluate_duplicate_history` remains the only owner of canonical MPN matching,
the inclusive 168-hour window, latest record selection, and equal-time
`AMBIGUOUS` outcome. `PlaywrightDuplicateHistoryPage` now enforces the confirmed
settlement contract: the `List_Detail` response must correspond to the current
exact MPN request with `nolike=on`; the `dg` request sequence must advance;
`_select_pending` must be false; the query button must be enabled; and response,
`table.cache.dg`, and `#_id_dg` BillIDs must agree. Any missing evidence fails
closed as `QUERY_SETTLEMENT_UNCONFIRMED`. Deterministic fake tests cover this
contract. Response and request MPN comparison use the exact `dup-mpn-v1`
normalization (NFKC, trim, ASCII uppercase only); punctuation and internal
spacing remain significant.

Creator remains UNKNOWN. `#UserName_text` is the purchaser and
`#OwnerID_text` is the salesperson; neither is treated as the record creator.
The primary history schema reviewed so far does not establish a creator field.
`OfferPrice` is the history-grid field labelled `报价`, paired with
`OfferCurrencyID` (`报价币种`); however the response-to-detail field mapping and
currency semantics have not been closed end-to-end. It is not substituted from
Research's supplier-side `InPrice`. No live selector is configured for either
optional field. BillID is stable list-to-detail identity, but no ordering
relationship that can break equal-time ties has been proven; equal timestamps
remain `AMBIGUOUS`.

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
callback and the loaded opener appears dialog-only, but the read-only panel-open
attempt did not expose one unique AI frame. AI recognition, import, synthetic
input, and parent-field writes were not run. AI read-back and blank-form
model/brand/quantity selectors remain UNKNOWN.

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
distinct from BillID and cannot substitute for it. Static inspection of the
loaded Save handler showed `#btnSave` → `bill_save_auto()` → `bill_save()`, a
server save request whose success response includes BillID/PENO, followed by
the read-only detail view. This is distinct from `bill_save_send()` behind
`#btnSave2` and the `#bcSend` action. No Save was clicked. Future reconciliation
can use returned BillID, open that exact detail, verify `#BillID`, then compare
MPN/Brand/Qty and available customer/purchaser/importance fields. If the server
does not return a unique BillID or exact detail read-back is unavailable, the
result is UNKNOWN/AMBIGUOUS; absence never means not-saved. Runtime confirmation
after the first authorized Save is still pending.

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

## Phase A-3 closeout — 2026-09-27

- **Query settlement:** implemented in the existing production page adapter and
  covered with deterministic fake tests. A query is settled only when the
  current exact-MPN `List_Detail` request carries `nolike=on`, its matching
  response completes, the `dg` sequence advances, `_select_pending` is false,
  the query control is enabled, and response/cache/DOM BillIDs agree. A stale,
  malformed, or ambiguous state maps to `QUERY_SETTLEMENT_UNCONFIRMED`.
- **Creator:** UNKNOWN. The reviewed primary-list schema does not expose a
  verified creator field. `#UserName_text` is purchaser and `#OwnerID_text` is
  salesperson; neither is used as creator.
- **INSO quote:** UNKNOWN. The history schema uses `OfferPrice`, displayed as
  `报价`, with `OfferCurrencyID` displayed as `报价币种`. Its detail mapping and
  currency/decimal semantics have not been confirmed end-to-end. Research's
  supplier `InPrice` is not used.
- **Timestamp tie-break:** AMBIGUOUS. BillID is stable identity only; no evidence
  proves its numeric/lexical order tracks creation order. Equal timestamps stay
  `AMBIGUOUS`.
- **AI and parent writer:** UNKNOWN. Existing-detail read-back does not prove
  blank-form product selectors. The prior AI entry attempt returned a generic
  form error; no further AI entry, recognition, or parent-field write was
  attempted.
- **Save/reconciliation:** the loaded handler chain identifies `#btnSave` as
  `bill_save_auto()` → `bill_save()`, distinct from `bill_save_send()` and
  `#bcSend`; the success response includes BillID/PENO and routes to read-only
  detail. No Save was clicked. This provides the reconciliation contract, but
  actual post-save confirmation remains gated until a separately authorized
  first Save.
- **Runtime:** this execution context could not safely attach to the
  authenticated Chrome CDP session, so no additional live query/detail
  inspection was performed. No alternate browser profile was used.

No Save, Save-and-Send, Send, real SMTP, or Sheets write occurred. Production
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

## Phase A FINAL read-only runner — 2026-09-27

`src/launcher/v12_phase_a_readonly.py` is a bounded one-run inspector for the
Owner-authenticated Chrome session. The ignored
`runtime/run_v12_phase_a_readonly.cmd` launches it by double-click. It requires
the canonical Chrome configuration to point at the existing
`.browser-profile/cdp` and `127.0.0.1:9222`; mismatch, multiple contexts, login
redirect, or uncertain page/frame identity stops the inspection.

The runner performs one exact history query through
`PlaywrightDuplicateHistoryPage`, inspects schema keys/approved labels only, and
opens a detail only for one unambiguous result row. It then opens a blank
temporary inquiry and inspects the AI panel without recognition, import, parent
field writes, or Save. The report contains no record values and is written under
ignored `runtime/evidence/v12-phase-a-final/report.json`.

Creator is confirmed only when response schema, grid label, and detail label
agree on creator semantics; purchaser `UserName` and salesperson `OwnerID` are
excluded. `OfferPrice` is confirmed only when response schema, `报价` grid and
detail mapping, `OfferCurrencyID`/`报价币种` detail mapping, and a parseable
decimal sample agree. The amount itself is not reported. Equal timestamps
remain `AMBIGUOUS` without a proven ordering rule.

AI recognition and parent row writing remain UNKNOWN until their server-side
effects and unsaved behavior are evidenced. The runner never clicks recognition
or import. Save controls are read only; `#btnSave2` and `#bcSend` remain
hard-forbidden. No live Save, Send, SMTP, or Sheets write is permitted.

### Owner session follow-up — 2026-09-27

After the Owner reported login complete, read-only inspection found one Chrome
context, one existing page with the verified INSO shell/list controls, and a
lease-created page that redirected at the top level to `/login.aspx`. The runner
records `LEASE_CHILD_AUTH_NOT_SHARED`; it does not infer why the existing shell
state is absent from the child page. It leaves the reused page/browser open.

The unique existing shell's exact checkbox `#nolike` was unchecked, hidden, and
enabled; its unique associated `精确` label was also hidden. The duplicate
adapter therefore failed closed with `QUERY_SETTLEMENT_UNCONFIRMED` before
dispatch; neither control was force-clicked. The loaded grid had no cached
result row/header metadata. Creator, quote, AI
recognition/read-back, and blank-draft product writer remain UNKNOWN. The
existing tab was not used to open forms or details outside the lease lifecycle.
Loaded list-handler inspection found functions referencing `List_Detail`, but
did not verify a safe visible action to toggle `#nolike`; no hidden-control or
guessed-JavaScript interaction was attempted.

## Current authenticated-shell reuse result — 2026-09-27

The shell-page lease correction supersedes the older child-page lifecycle notes
above. Chrome attached as `REUSED`, with exactly one context and the unique
authenticated INSO shell/list frame. No child page was created and cleanup
left the reused browser open.

The loaded list button calls `search()`, which runs the site's search
preparation and serializer. One live query produced bracket-encoded
`searchData[<field>]` fields. The adapter's `_is_exact_history_request()`
matched the current MPN and exact-mode state, and the response settled as a
valid empty result. This confirms the request/response path, but yields no
creator or quote/currency data. None was inferred.

`新增` opened the blank inquiry form on the same shell. Loaded code confirms
`ai_import()` calls the page's `windows()` wrapper, which delegates to
`alertbox._open()` and builds a `details-dialog` containing an iframe `src` for
`product/Import_ai.aspx`; these functions contained no detected persistence
call. The opener click was intercepted by an already-visible dialog before
the handler ran, so the live AI iframe was not found. The code now locates it
only as a unique `iframe[src*='/product/Import_ai.aspx']` inside the unique
`details-dialog._dialog1`; it does not scan `page.frames` for a guess. No AI
recognition/import ran. AI read-back and blank-form model/brand/quantity
selectors remain UNKNOWN. Save/Send/SMTP/Sheets were not used.

## Targeted owner-session follow-up — 2026-09-27

- A single existing list row was opened read-only via its unique
  `Bill_View_Open` link. The detail BillID and PartNo matched the list identity;
  PENO and model/brand/quantity read-back fields were present. Values were kept
  local and were not recorded.
- The live primary-grid labels are `OfferPrice` → `报价` and
  `OfferCurrencyID` → `报价币种`. The detail column for `OfferPrice` is labelled
  `未税报价`; no `OfferCurrencyID` detail selector was found. The current list
  price was blank, so no response/detail amount comparison was possible. Do
  not configure production quote/currency fields from this evidence.
- No creator field is confirmed. Current grid fields do not provide creator
  semantics, but the structured List_Detail response schema was not captured;
  therefore `CREATOR_NOT_EXPOSED_BY_INSO` is not established. `UserName` and
  `OwnerID` remain purchaser and salesperson only.
- The previously accepted exact-query implementation was not changed. In this
  page the exact checkbox remains inside a collapsed hidden region; no exact
  query was dispatched in this follow-up. The accepted `EXACT_QUERY` contract
  remains distinct from the still-unconfirmed non-empty exact query.
- No visible dialog was open initially. The unique `新增` action did not open a
  visible blank form after the read-only detail was closed. The AI iframe
  remains hidden; recognition, import, and parent-field writes were not run.
  No live adapter fields were added. Production Write Gate remains CLOSED.

## Bounded Phase A closeout follow-up — 2026-09-27

- A lease-pinned production Playwright attach reached the verified shell, but
  its operation-frame grid had no rows to seed the accepted exact-query adapter.
  A separately surfaced browser UI list had rows but was not mixed into that
  adapter call. The adapter was not dispatched; no MPN was substituted.
- Read-only UI inspection opened one blank temporary inquiry and its unique AI
  dialog iframe at `/product/Import_ai.aspx`. The input is `textarea#paste-area`
  and the visible recognition control is `button#ai-recognize`. No preview row
  existed. The recognition handler/persistence behavior was not provable from
  the exposed runtime, so recognition and import were not run. These observations
  do not configure production selectors or enable a parent writer.
- The AI dialog was closed through its visible cancel action. The untouched
  blank temporary inquiry remains open because its Back implementation was not
  verifiable in this frame. No Save or Send control was activated.
