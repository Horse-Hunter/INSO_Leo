# INSO V1.2 Safety Review

Status: `DESIGN_SAFE` for additive, fake-only contracts and persistence design, subject to the blockers below. No live discovery or external action was performed by this review.

Review baseline: `feature/v1-2` at handoff `f38fc73cf788b818351db107c2e91e23503eabe9`, including CEO-frozen decisions from `763ffc0e7045eaee59f793cb09b58b5a246cc74d`. The V1.1 comparison baseline is `release/v1.1` at `be9d0a51d0375884dfa3e5e9e4317958899fdc75`.

This review does not change Owner/CEO business rules. It defines fail-closed implementation constraints and identifies live facts that remain `UNKNOWN`. It is a static review only: no production INSO page was opened, no live discovery was run, and no Sheet, order, mail, or other external data was changed.

## Verdict and blockers

**Verdict:** The frozen business flow is suitable for additive implementation behind fake adapters. It is not safe to implement or exercise live INSO writes, real notifications, or production smoke until the blockers below are resolved and the applicable independent gate is granted.

### BLOCKER B1 — CDP page and browser ownership are not safe for shared use

**Risk / trigger:** `src/research/inso_history.py` enumerates all pages from all contexts and selects the first open page. It then calls `browser.close()` on a CDP-attached browser. That does not prove page, context, company, or account identity; closing an attached browser may close a reused user browser. It also makes arbitrary-tab selection incompatible with an `InsoSessionLease`.

**Required Main Programmer changes:** remove first-page selection; require an explicitly supplied verified context and operation-owned page; represent `APP_OWNED` versus `REUSED` explicitly; never close a reused browser; close only the operation's child page; and close an app-owned browser only after the complete lease/cycle drains. Existing Research may reattach to the verified endpoint/context if safely passing the same page is infeasible, but it must not select a global/first page or close the browser. A fake test must prove that a reused browser and unrelated tabs remain open and that only the owned child is closed.

This blocker applies to any live INSO duplicate read or purchase path. Read-only discovery must use a separately bounded inspector and must not reuse the unsafe adapter.

### BLOCKER B2 — Save Data is not yet protected against duplicate creation

**Risk / trigger:** after `保存数据` is dispatched, timeout, process crash, lost response, or page transition can leave the result unknown. Repeating the click can create a second draft. Architecture currently names `UNKNOWN_WRITE_OUTCOME` but cannot identify a saved row/record reliably; saved-record identity and read-back fields are `UNKNOWN`.

**Required Main Programmer changes:** make `UNKNOWN_WRITE_OUTCOME` durable before leaving the commit step; on restart prohibit all further Save Data calls for that inquiry; provide a read-only reconciliation operation keyed to the verified inquiry/order identity; transition to `SAVED` only on unique identity plus field verification; permit another controlled pre-save flow only if reconciliation positively proves no record was created; otherwise stop for manual review. Do not create an automatic timeout-to-retry path. Discovery must first establish a stable saved-record identity and readable verification fields; if it cannot, live Save Data remains unavailable.

### BLOCKER B3 — Save-and-Send has no enforceable technical boundary yet

**Risk / trigger:** a developer instruction or selector convention alone cannot prevent an accidental send; similar labels, DOM changes, or a broad submit helper can route a click to `保存并发送`.

**Required Main Programmer changes:** implement the independent controls in §5 and prove them in fake/deterministic tests before any write adapter can be enabled. The adapter's public surface must have no send/final-submit method. There must be no `SEND`/`SAVE_AND_SEND` member in the write action enum/allowlist. A centralized semantic action helper must reject any target whose accessible name/text or resolved control identity matches the forbidden control, raising `SecurityViolation` before dispatch. A selector registry must explicitly deny the forbidden control and reject ambiguous matches. Runtime assertions and static checks are defense in depth. Any failed check disables the write gate; there is no coordinate fallback.

### BLOCKER B4 — Raw exception text can flow into durable workflow state

**Risk / trigger:** `src/workflow/store.py` persists `str(error)` into `workflow_items.last_error`, and `src/launcher/backend.py` exposes that value as a GUI remark. SMTP/library exceptions and browser/page exceptions can contain recipient data, server responses, URLs, form data, or other sensitive values.

**Required Main Programmer changes:** V1.2 events, alert detail, GUI DTOs, and logs must persist and display allowlisted reason codes and sanitized metadata only. Do not pass raw exception strings or provider responses into V1.2 persistence/logging. Audit every catch/log boundary in new code. The V1.1 table is frozen and must not be rewritten as a side effect of this task; V1.2 must not copy raw `last_error` into new event/alert fields. Add synthetic canary-secret tests that assert the canary never appears in SQLite, GUI DTOs, logs, fixtures, or screenshots.

## 1. Threat model

Protect against accidental or ambiguous writes, session confusion, stale/changed DOM, wrong inquiry or company, retries after an unknown commit, forbidden sending, duplicate email, secret/data leakage, partial migrations, and misleading recovery/UI state. The relevant actors and failures are:

- a human using the same Chrome profile while automation runs;
- an unrelated or stale tab/context attached to CDP;
- INSO login expiration, company/account switch, security challenge, navigation, or DOM change;
- two matching controls/records or missing/ambiguous fields;
- timeout/crash between a dispatched action and durable acknowledgement;
- SMTP transient/permanent failure or accepted-but-unacknowledged send;
- app crash during SQLite backup/migration or evidence capture;
- exceptions and screenshots containing credentials, customer details, or unrelated rows.

Trust only explicit, freshly read identity/value evidence tied to the current `inquiry_id`. A prior successful check, cached page handle, visible toast, or presumed ownership is insufficient after navigation, reconnect, crash, or material DOM change. All uncertainty fails closed and produces a sanitized event/reason code.

## 2. External write operation risk classes

| Class | Examples | Safety treatment |
|---|---|---|
| E0 local read | inspect workflow state; read-only INSO history | No external mutation. Verify endpoint/page identity; do not leak data into logs or fixtures. |
| E1 local durable write | workflow event, alert, retry ledger, evidence reference | Transactional, append-only event; bounded local paths; no secrets/image bytes in SQLite. Migration requires verified backup. |
| E2 external draft mutation | create a new inquiry and populate allowlisted fields; Save Data | High risk. Per-action identity and value checks; one inquiry only; Save Data has unknown-outcome reconciliation; independent feature gate. |
| E3 external send/finalize | Save-and-Send, submit/send/publish | Prohibited in V1.2 under every gate. No implementation path or API. |
| E4 destructive/broad mutation | delete, edit history/other order, bulk update, clear unknown values | Prohibited. |
| E5 external notification | SMTP send to intended recipients | Separate high-risk gate; per-recipient ledger and unknown-outcome reconciliation; does not block purchase. |

## 3. WRITE ALLOWLIST review

The frozen allowlist is narrow and inquiry-scoped: open the approved `1.业务询价` page; click the single verified `新增`; set customer `Win Source Elec. Tech. Ltd`; set quotation type and purchaser from the frozen rules; open `AI录单`; enter exactly `MPN + six U+0020 spaces + Brand + six U+0020 spaces + quantity`; click `AI智能识别`; wait for a deterministic ready state; read back MPN/Brand/Quantity; and, only after every gate and precondition passes, click `保存数据`. After save, read back and verify the unique saved record; present Owner's GUI label `已发采购单` only after that verification.

The allowlist does not authorize editing an existing inquiry, selecting an arbitrary similar row, clearing unknown fields, changing any unlisted value, retrying an ambiguous write, or sending. `保存并发送` remains prohibited regardless of Owner authorization for Save Data.

The quotation type is `NEED_FULL_PRICE` for A, or B with total `> 50,000`, or C with total `> 300,000`; otherwise `NORMAL_INQUIRY`. Stock does not enter this decision. Purchaser is `颜浩坚` or `陈熙` respectively. Missing B/C total must block purchase routing rather than default to normal. Preserve the independent important-notification stock/threshold rule and all frozen duplicate, Research ordering, and customer-name rules as stated in `docs/V1_2_ARCHITECTURE.md`.

MPN recognition is required to compare using an approved canonical exact-equality rule. The precise recognition canonicalizer remains `UNKNOWN`; do not silently reuse duplicate normalizer `dup-mpn-v1` unless the Owner/CEO confirms that contract. Brand comparison is trim-outer-whitespace then exact equality; quantity is integer exact equality. Missing, mismatch, multiple candidate, unreadable value, or unknown result blocks Save Data, emits `SECURITY_CHECK_FAILED`/a security event with a sanitized reason code, raises active `采购录单异常`, captures evidence only when safely redacted, and stops purchase for that inquiry. Never auto-correct AI output.

## 4. WRITE DENYLIST

- `保存并发送`, any send/final-submit/submit/publish action, and any alias or unlabeled equivalent.
- Delete, edit, overwrite, or resend any existing/history order; bulk edit; unknown-field mutation; clearing unknown values.
- Any write without unique page, authenticated context, order, control, and value identity.
- Any write with multiple candidates, stale identity, unexpected existing target, login expiry, CAPTCHA/OTP/device challenge, or changed DOM.
- Coordinate clicks, blind fallback selectors, fuzzy row/control matching, arbitrary first/last result, or retry after an unknown write outcome.
- Retrying SMTP `UNKNOWN` without reconciliation/manual review.
- Screenshot persistence if redaction/scope cannot be guaranteed.

## 5. Save-and-Send hard prohibition

Use these independent layers; a single configuration switch or programmer convention is not sufficient:

1. **Closed action enum:** only enumerated allowlisted actions exist, including `SAVE_DATA`; no `SEND`, `FINAL_SUBMIT`, or `SAVE_AND_SEND` action exists. Unknown action values raise `SecurityViolation`.
2. **Narrow adapter API:** expose methods for the specific allowlisted draft actions and verified `save_data`; do not expose generic `click`, `submit`, `send`, or a final-submit method to Workflow. Keep any low-level locator dispatch private and require a validated action token.
3. **Semantic deny guard:** immediately before dispatch, inspect the resolved control's role, accessible name, visible text, and stable attributes. Any match to deny terms (`保存并发送`, `发送`, final-submit aliases) blocks the action, even if a caller asks for another action. Ambiguous labels/controls block too. No coordinate fallback.
4. **Selector registry deny entry:** explicitly register the forbidden control/aliases as denied; never store them as an actionable selector. Resolve exactly one allowlisted control within the verified page/form scope.
5. **Runtime invariant + independent feature gate:** before each dispatch, assert action is in allowlist, context/page/order token is current, and `WRITE_IMPLEMENTATION_ALLOWED` is enabled. Production default is disabled. Save Data smoke requires its own later gate; no gate can enable Send.
6. **Static/fake tests:** source/API scan rejects forbidden action names as callable methods/enum values, and deterministic tests prove text/semantic aliases, duplicate matches, selector drift, unknown actions, and direct low-level bypass attempts all fail before dispatch. Static scanning complements runtime checks; it is not the only control.

Treat a DOM change or any guard failure as a security event and stop. Do not attempt alternate controls or coordinates.

## 6. Page identity policy

Every operation must freshly prove all of the following in the current context:

- approved INSO origin (exact expected scheme/host/port policy), approved business page identity/path, and expected page title or stable app/page attributes established by discovery;
- expected authenticated account and company/context from safe, stable identity signals; login form, expired session, account mismatch, security challenge, or unavailable signal means fail closed;
- exact CDP endpoint/browser identity and explicit browser context identity, not simply “port responds”;
- operation-owned child page is bound to that context and its opener/creation record is known;
- current `inquiry_id` maps to the intended new draft flow and no pre-existing record is being edited;
- no material navigation or DOM identity change since the last verification.

URL/title examples or selectors are not approved until READ_ONLY_DISCOVERY records their observed stable values and CEO separately authorizes the next stage. Do not log cookies, headers, tokens, credential values, or full authenticated URLs with query data.

## 7. Order identity policy

Bind every command to a persisted `inquiry_id`, stable local `command_id`/draft revision, and frozen source snapshot (worksheet identity and input MPN/brand/quantity/customer/tier/derived purchase values). Before each mutation, re-check that the page is the new-inquiry form belonging to this command and that there is exactly one candidate. Never infer identity from row number, current selection, similar MPN, visible customer alone, or DOM position.

Saved order identity and the readable fields that prove it are `UNKNOWN`. Do not implement live Save Data until discovery proves a stable unique record identifier or an equally strong, independently reviewable identity tuple and verifies MPN, Brand, Quantity and required allowlisted fields on the same record. If multiple records satisfy the tuple, reconciliation is ambiguous and requires manual review.

## 8. Control identity policy

For every click or field write, use the verified page/form scope and require exactly one control with the discovered semantic role/name and stable identity attributes. Confirm visible text/accessible name and expected enabled/visible state. For fields, read current value before writing and compare to the expected precondition; target value must be fully determined from this inquiry. Do not clear/refill an unknown or non-empty value automatically. If current values already match, treat the step as verified without a duplicate action where safe; otherwise stop on conflicts.

The control identity check must be rerun immediately before dispatch. A locator timeout, zero/multiple matches, hidden/disabled control, changed text, changed value, or stale page token is a failure, never a reason to broaden the selector.

## 9. Browser/session ownership review

The existing launcher bootstrap distinguishes `BrowserHandle.owned` as a boolean and returns `owned=False` for any reachable CDP endpoint. A successful endpoint probe does not identify which browser, profile, context, user, account, or company is behind it. Current Research INSO history independently attaches to CDP, takes the first open page across contexts, and closes the attached browser. These behaviors do not satisfy V1.2 identity or shared ownership requirements.

Do not treat “same port” as “same authenticated session.” A `REUSED` browser must never be shut down by this application. An `APP_OWNED` browser may be closed only after its lease is drained and all child operations are complete. Every child page has one explicit owner and is closed by that owner. Background-tab creation must name the verified context; no global page, arbitrary first page, or hidden ownership inference.

Failure handling:

- **Page/context invalidated or Chrome crash:** invalidate the lease and all page handles; stop current operation. Reacquire only into a newly verified endpoint/context, then repeat full page/account/order checks. Do not resume a pending write from stale state.
- **Login/session expiry or challenge:** stop and raise manual/security handling. Never bypass CAPTCHA/OTP/device verification and never continue a write after re-login without re-establishing all identities.
- **Restart:** leases are process-local and never serialized as live ownership. On restart, do not assume an inherited lease or resume a mutation. Reconcile durable operation state read-only; unknown writes go to `UNKNOWN_WRITE_OUTCOME`.
- **Interrupted purchase:** continue only from a persisted state whose last completed step is proven; otherwise read-only reconcile or manual review. Do not replay a click solely because the local state says “in progress.”
- **Background cleanup:** close only owned child pages. Do not close tabs that existed before acquisition. If child ownership cannot be proven, leave the browser open and require manual cleanup.

## 10. InsoSessionLease review and modifications

Keep `InsoSessionLease` in launcher/composition root, with immutable identity fields and explicit lifecycle state. Minimum contents: owner enum (`APP_OWNED`/`REUSED`), endpoint identity, browser handle/connection, verified context identity, context health, lease/cycle ID, child-page registry with owner, and acquire/release/invalidated timestamps. It must not contain credentials or be persisted to SQLite. Adapters receive an explicit lease/context capability and cannot discover global pages or close the browser.

The lease spans duplicate-read → unchanged Research → purchase only while healthy and verified. Reattachment to the same verified endpoint/context is acceptable if Research adapters cannot share the exact Playwright page; preserving identity and ownership matters more than preserving a page object. If endpoint/context/page identity cannot be proven, fail closed instead of forcing reuse. Serialize lease use through the Workflow worker; prevent concurrent GUI run/session ownership.

**Required architecture modification:** adapt the existing Research INSO browser seam to accept an explicit verified context/lease or to reattach only to that exact verified context, and remove browser-closing behavior from attached/reused paths. Keep Research price selection and other V1.1 business rules unchanged.

## 11. UNKNOWN_WRITE_OUTCOME recovery

Persist the state before dispatching Save Data so a crash after dispatch is conservatively treated as unknown. Once dispatch begins, any timeout, disconnected page/browser, process shutdown, missing acknowledgement, or unparseable response yields `UNKNOWN_WRITE_OUTCOME`—not failure-to-save and not permission to retry.

Recovery is read-only:

1. Re-establish safe page/account/context identity.
2. Search/read only using the discovered stable identity strategy and current `inquiry_id` snapshot.
3. If exactly one saved record is found and its identity plus MPN, Brand, Quantity and approved fields match, append reconciliation evidence/event and mark `SAVED`.
4. If a complete, authoritative read proves no matching record exists, record `NOT_SAVED_CONFIRMED`; only then may a human/system re-enter the controlled pre-save state and re-run all checks before a new Save Data action.
5. If identity/read completeness is unknown, several candidates exist, or values disagree, remain blocked, raise/retain `采购录单异常`, and require manual review. No automatic save retry.

The system must preserve the original unknown event and all reconciliation events. A toast, button disappearance, page redirect, or elapsed timeout alone is not proof of saved/not-saved.

## 12. Save Data preconditions

All must pass immediately before dispatch:

- `WRITE_IMPLEMENTATION_ALLOWED` and a separately approved real-save gate are satisfied for the environment; current review grants neither.
- Confirmed duplicate result is `CONFIRMED` and nonduplicate, Research is finished, purchase routing is otherwise eligible, and one durable purchase command exists.
- Page, account/company, endpoint, context, child page, inquiry and control identities pass §§6–8.
- No active unknown-write state, unresolved purchase exception, session challenge, or concurrent writer exists.
- Customer/type/purchaser/input values are fully determined by frozen rules; blank customer follows the explicit missing-data rule and must not be invented.
- AI recognition is deterministically ready; exactly one result set exists; MPN, Brand and integer Quantity read back and match; all required allowlisted fields are readable and correct.
- The unique resolved action is exactly the allowlisted `保存数据` control; all independent Save-and-Send guards pass.
- A durable pre-dispatch operation record exists; evidence/screenshot failure must not weaken any validation or trigger a retry.

Any failure stops the inquiry before Save Data. Never “repair” by clearing or guessing.

## 13. Save Data postconditions and read-back

`SAVED` requires a unique saved-record identity tied to the current inquiry and a read-back of MPN, Brand, Quantity plus all other allowlisted fields that the contract requires. Compare MPN by an explicitly approved canonical exact comparator; Brand by outer trim plus exact equality; Quantity as integer exact equality. Store identity/reference and sanitized verification result, not a full page dump. A toast or navigation can be supplemental evidence only.

The GUI label `已发采购单` is Owner-defined business wording and must be emitted only after these postconditions pass. It does not imply Save-and-Send. Any mismatch or missing read-back field is `UNKNOWN`/exception, never success.

## 14. Screenshot/evidence policy

- Store only under ignored `runtime/evidence/<inquiry_id>/`; validate `inquiry_id` against a strict generated identifier format, reject separators/traversal, resolve the final path and verify containment under the evidence root. Use opaque collision-safe filenames and relative POSIX references in SQLite.
- Minimize capture to the exact relevant control/result region. Redact credential fields, tokens, unrelated customer/order rows, addresses and other personal data before any disk persistence. Prefer in-memory capture and in-memory redaction; do not persist a raw intermediate image.
- Safe capture regions/masks are currently `UNKNOWN`. Until discovery validates them, a screenshot is optional and must be omitted if there is any doubt. Record only a sanitized `reason_code` and evidence-capture outcome.
- Capture failure does not authorize another business click. Redaction failure or uncertain crop means discard the image buffer/file and persist only the reason code; if safe discard cannot be guaranteed, do not attempt screenshot capture on that page.
- Never place screenshots or raw customer/order data in Git, logs, SQLite blobs, fixtures, test output, or releases. SQLite stores a relative reference only.
- Policy retention is 30 days, but V1.2 initial release must not automatically delete evidence. Any later cleanup is a separately reviewed manual/maintenance action.

## 15. SQLite migration and backup safety

Keep V1.1 `workflow_items` schema/rows/meaning intact. V1.2 tables are additive. Do not drop, rewrite, or widen its CHECK constraint. Migration must be idempotent and run under one transaction; write the migration record and `PRAGMA user_version` in that transaction. Detect the exact existing schema before deciding a baseline version; do not assume `user_version=0` alone proves a pristine V1.1 database.

Before the first V1.2 migration, quiesce Workflow workers and close all application DB handles. Create a timestamped backup using SQLite's online backup API (or an equivalently proven SQLite-consistent mechanism), not a raw copy of a live `.db` while WAL is active. Write to a unique temporary backup path; run `PRAGMA integrity_check` on the backup and verify expected schema/version and required table counts; flush/close it, then atomically rename it to the final backup name. Preserve original DB, `-wal`, and `-shm` until backup validation and migration success. Do not delete or overwrite prior backups. If crash leaves a temporary backup, do not treat it as valid; preserve it for diagnosis and create/verify a fresh backup before retry.

Apply schema DDL and version advancement in one explicit transaction. On crash/error before commit, reopen, inspect `user_version` and migration tables, run integrity checks, and retry only if the transaction rolled back and the original/verified backup remains. If state is inconsistent, stop V1.2 orchestration and restore only by a documented operator procedure; never automatically downgrade/drop V1.2 data. WAL/SHM are transient SQLite coordination files, not standalone backups; no migration/restore may copy one without a consistent database snapshot.

Rollback means disable V1.2 orchestration and run the sealed V1.1 source (`release/v1.1`), preserving V1.2 tables and backup. No automatic downgrade or V1.2 data deletion. Before implementation, specify backup naming, location/access permissions, disk-full behavior, restore verification, and operator recovery steps.

## 16. Notification credential boundary

Notification transport consumes only a finalized `NotificationCommand` and sends one recipient at a time. It has no authority to decide duplicate status, A/B/C, thresholds, stock, customer, or purchase routing. Sender `1069599116@qq.com` and intended recipients `linan229@qq.com`, `shawn@inso-hk.com` are non-secret settings; SMTP credential is fetched only through Core Credential Provider `site_id=smtp.qq.com` at send time. Never put the authorization code in source, config, command, SQLite, logs, fixtures, or evidence.

Use a recipient ledger keyed by `(command_id, recipient_id)`. Initial +1/+5/+15 minute retries, maximum four attempts, apply only to transient failures. A recipient already confirmed `SENT` is never sent again when another recipient fails. Permanent/auth/config rejection stops retry but keeps `NOTIFICATION_FAILED` active; purchase continues. An unknown send result requires transport reconciliation or manual review before resend. Recover the alert only when every intended recipient is confirmed `SENT`, preserving append-only failure/retry/success/recovery events.

The adapter should minimize credential lifetime, avoid credential-bearing object reprs, never log raw SMTP protocol/exception output, and clear local references where practical (acknowledging Python strings cannot be reliably zeroized). No SMTP to business recipients is part of this review.

## 17. Production logs and secret/data leakage

Current launcher logging mostly records exception class names, which is a useful safe pattern. However, the existing Workflow `last_error = str(error)` persistence and GUI remark path are unsafe as generic future error channels (B4). New V1.2 logs/events may contain allowlisted reason codes, timestamps, attempt counts, non-sensitive IDs, and sanitized state transitions only. Do not record raw exception text, HTTP/SMTP bodies, cookies, headers, credentials, full customer rows, arbitrary page text, or screenshot bytes. Avoid full URL query strings where they may carry order or session data. Test with unique fake secrets and assert absence from database bytes, rendered DTOs, log buffers, evidence metadata, and exception messages.

## 18. READ_ONLY_DISCOVERY_PLAN

This is a proposed bounded plan for a later CEO/Owner authorization. It is not permission to perform discovery in this review.

**Allowed reads only:** page identity metadata (URL/path, title, stable app attributes); browser endpoint/context/page identity and ownership metadata without cookies/tokens; control semantics and safe selector candidates; history rows' stable record-ID availability and timestamp tie behavior; saved draft/read-back fields if an already existing safe read-only page is made available; screenshot candidate regions/redaction feasibility without writing or saving captured images. Use synthetic notes and non-sensitive selector/attribute descriptions; do not export customer/order records.

**Prohibited:** click `新增` or any mutation-capable control; enter/edit/clear fields; click AI actions; Save Data or Save-and-Send; create/update/delete any record; send mail; write Sheets; bypass login/challenge; run production smoke. No arbitrary navigation through controls. The operator may manually open the intended page after a separate authorization; the inspector is read-only and fails closed if identity is not immediately clear.

**Outputs:** a sanitized discovery report containing observed stable identities, candidate selectors with uniqueness evidence, saved-row ID/read-back feasibility, ownership boundaries, screenshot crop/redaction decision, and unresolved UNKNOWNs. No raw HTML, customer row, credentials, cookies, tokens, screenshots, or production response payloads in Git. If inspection risks exposing unrelated customer data, stop and record the reason only.

**Entry conditions:** separate CEO/Owner authorization naming target environment/account/company and session, an explicit read-only scope, and a human-operated authenticated session. Do not use the current `PlaywrightInsoReadOnlyBrowser` until B1 is corrected or the discovery inspector independently proves and limits ownership.

## 19. Fake/deterministic safety test matrix

| Area | Required deterministic cases |
|---|---|
| Duplicate | `dup-mpn-v1` NFKC/outer trim/ASCII uppercase; internal punctuation and whitespace preserved; exact 168-hour inclusive bound in Asia/Shanghai; latest result; equal timestamps resolved only by proven stable ID else ambiguous; technical failures never become negative. |
| Routing | Duplicate always runs unchanged Research then blocks purchase; confirmed nonduplicate routes; unavailable/ambiguous result blocks post-Research routing; notification async/non-blocking; Research regressions unchanged. |
| Write identities | Wrong page/account/company/endpoint/context, expired session, security challenge, wrong inquiry, stale page, zero/multiple page/control/order candidates, unreadable value, changed DOM all fail closed before dispatch. |
| Save-and-Send | No send enum/public method; forbidden label and aliases rejected by semantic guard; registry deny; unknown action rejected; ambiguous match rejected; direct helper bypass blocked; no coordinates; production gate defaults off. |
| Recognition/save | Deterministic AI-ready signal; MPN/Brand/Quantity exact rules; each mismatch/missing/multiple/unknown prevents Save Data, adds exception alert/event, and stops inquiry; no auto-correction. |
| Unknown save result | Timeout/crash/lost acknowledgement becomes durable `UNKNOWN_WRITE_OUTCOME`; no second Save Data; unique matching record reconciles to SAVED; authoritative absence allows guarded re-entry; multiple/unreadable results remain manual review; toast alone proves nothing. |
| Session ownership | APP_OWNED versus REUSED; exact context routing; unrelated tabs stay open; only owned child closes; reused browser never closes; owned browser closes only after drain; arbitrary first/global page impossible; crash/restart invalidates lease. |
| Evidence | Path traversal, invalid inquiry ID, symlink/containment failures; narrow crop; redaction failure discards/omits image; capture failure only records reason; no raw-image temp file; refs relative only; no automatic cleanup. |
| SQLite | Synthetic V1.1 DB backup through WAL activity; verified backup; crash before/within/after transactional migration; repeat migration; user_version consistency; disk-full/collision; open-handle quiescence; original, WAL/SHM, backup preserved; rollback disables V1.2 without dropping tables. |
| Notification | Per-recipient attempts and schedule; SENT recipient never resent; permanent/auth/config no retry; UNKNOWN not resent; purchase unaffected; alert only recovers after all intended SENT; failure and recovery events remain. |
| Leakage/GUI | Canary credentials/SMTP response/customer strings absent from logs, SQLite V1.2, screenshots/evidence refs, and DTOs; newest active alert displayed while full recovered event history remains queryable. |

All tests above are fake/synthetic. Do not use real SMTP recipients or production INSO for test setup.

## 20. Production smoke approval checklist

Production smoke is **not approved**. A later independent gate review must verify each applicable item with concrete evidence:

- B1–B4 resolved, reviewed code and fake tests pass; no unrelated V1.1 behavior changed.
- Read-only discovery separately authorized and completed; page/account/company/context identity, unique controls, stable history/saved IDs and safe read-back established; UNKNOWNs affecting the proposed action resolved.
- Save-and-Send protections are independent, tested, and production-disabled; exact build/hash and configuration are reviewed.
- Order/control/value identities and Save Data pre/postconditions are proven; unknown-write reconciliation cannot replay a save.
- Evidence capture/redaction is proven safe or disabled; evidence path is ignored and contained; no destructive auto-retention.
- SQLite backup/restore/migration is proven on synthetic copies; verified pre-migration backup retained; no handles/concurrency hazards.
- Notification credential boundary, recipient ledger, retry behavior, secret-canary checks and UNKNOWN send reconciliation are reviewed. Notification smoke is a separate gate from Save Data.
- Explicit CEO/Owner authorization names the specific environment, single inquiry/recipient scope, operator, time window and stop conditions. No authorization for Save Data implies authorization for Save-and-Send.
- Rollback, manual-review contact/steps, and post-action reconciliation are ready before any one-shot smoke.

## 21. Safety gates

| Gate | Current decision | Scope |
|---|---|---|
| `DESIGN_SAFE` | **APPROVED** | Frozen rules and additive contracts may proceed with fake adapters/persistence only, subject to B1–B4 for any affected live-capable path. This is not approval for live writes, mail, discovery, or production smoke. |
| `READ_ONLY_DISCOVERY_ALLOWED` | **NOT APPROVED FOR EXECUTION IN THIS STAGE** | This review approves only the bounded plan in §18. Execution requires separate CEO/Owner authorization specifying target/session/scope. The plan forbids all mutations. |
| `WRITE_IMPLEMENTATION_ALLOWED` | **NOT APPROVED** | Blocked by B1–B4 and live identity/read-back UNKNOWNs. Pure fake contract work may proceed under DESIGN_SAFE; do not wire a live writer. |
| `REAL_SAVE_DATA_SMOKE_ALLOWED` | **NOT APPROVED** | Requires later independent gate review and explicit CEO/Owner approval after discovery and all checklist items pass. |
| `REAL_NOTIFICATION_SMOKE_ALLOWED` | **NOT APPROVED** | Separate later independent gate and explicit CEO/Owner authorization; no real SMTP recipient delivery now. |

## Main Programmer required changes

1. Resolve B1: explicit browser/context/page lease ownership, remove arbitrary first-tab selection and browser close from reused CDP attach; preserve V1.1 Research behavior.
2. Resolve B2: durable unknown-save state, read-only reconciliation, and no automatic retry until authoritative absence is proven; establish stable saved-record identity through separately approved discovery.
3. Resolve B3: implement layered Save-and-Send hard prohibition with closed action enum, narrow API, semantic deny guard, selector deny registry, runtime gate, and static/fake tests.
4. Resolve B4: V1.2 sanitized reason codes only; never propagate raw external exception text to SQLite, logs, GUI, fixtures, or evidence. Add secret-canary tests.
5. Before migration implementation, specify and test the SQLite-consistent backup/restore and crash recovery procedure in §15.
6. Define the AI-recognition MPN comparator explicitly; do not assume the duplicate normalizer is the same contract.

## Remaining UNKNOWN

Live page and authenticated account/company identity signals; stable browser/context identifiers; live safe selector candidates; stable history record ID; latest-timestamp tie behavior; saved draft unique identity and same-row read-back fields; whether the existing Research adapters can safely consume the verified lease; safe screenshot crop and redaction feasibility; exact AI-recognition MPN canonicalizer; V1.2 database backup location/access and operator restore details. None is inferred by this review.
