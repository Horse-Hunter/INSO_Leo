# INSO V1.2 Architecture Spike

Status: CEO-approved architecture baseline; pending Safety Supervisor review. No V1.2 runtime behavior is implemented by this document.

## Scope and verified seams

V1.2 extends the accepted V1.1 Windows application additively. `src/workflow` owns orchestration and durable inquiry state; `src/sheets` owns worksheet-specific record mapping; `src/research` keeps its existing read-only Research contract and price rules; `src/inso` is the boundary for new INSO duplicate reads and controlled purchase-draft entry; `src/gui` consumes public backend contracts only; `src/launcher` composes the runtime and owns browser/session lifecycle. Notification transport is a separate adapter behind a public contract and must not own business decisions.

Existing Research INSO history is a read-only price source. Its current result contract does not include the complete quantity, creator, and quote details required for duplicate review. V1.2 therefore adds a separate duplicate-history query contract and must not repurpose or change Research price selection, MPN matching, stock, FX, or retry rules.

## 1. Canonical order state machine

The existing V1 `workflow_items.status` remains compatible and continues to describe queue/Research execution. V1.2 adds an orthogonal durable business lifecycle (`business_state`) rather than overloading that status or a GUI label.

```text
QUEUED
  -> DUPLICATE_CHECK_PENDING -> DUPLICATE_CHECKING
       | transient/unknown -> DUPLICATE_CHECK_RETRY_WAIT -> DUPLICATE_CHECKING
       | confirmed result -> RESEARCH_PENDING -> RESEARCHING -> RESEARCH_RETRY_WAIT (existing Research retry policy)
            | DuplicateCheckResult.repeated = true -> DUPLICATE_STOPPED
            | repeated = false -> ROUTING
                 | important notification command created (asynchronous, non-blocking)
                 -> PURCHASE_DRAFT_PENDING -> PURCHASE_DRAFTING
                      | deterministic mismatch/unsafe page -> PURCHASE_EXCEPTION (manual follow-up)
                      | retryable infrastructure failure -> PURCHASE_RETRY_WAIT (only for safe, idempotent pre-save steps)
                      | verified save-data result -> PURCHASE_RECORDED (GUI business label: 已发采购单)
```

Duplicate check is attempted before Research. For either confirmed duplicate outcome, Research runs unchanged before routing. If duplicate lookup is temporarily unavailable, that failure is not a negative result: Research is still allowed to run unchanged, but post-Research routing is blocked until a confirmed duplicate result exists. Purchase must never proceed from an unavailable/ambiguous duplicate result.

After Research completes, duplicate orders stop before purchase and create an unconditional duplicate-notification command. Non-duplicates evaluate the important-order rule, enqueue any resulting command, and continue purchase entry without waiting for notification delivery. A failed or pending notification does not block purchase. Notification work can finish or recover after the purchase business state has advanced.

Existing Research status mapping, attempt budget and 15/30/60 minute delays stay unchanged. Duplicate-read retry policy and purchase pre-save retry classification require implementation detail and CEO/Safety review; do not blindly replay a partially executed write.

## 2. Workflow events and proposed public contracts

Contracts below are language-neutral proposal shapes; they are not yet Python runtime types.

### `DuplicateCheckResult`

```text
DuplicateCheckResult {
  inquiry_id: str
  outcome: CONFIRMED | UNAVAILABLE | AMBIGUOUS | INVALID_RESPONSE
  repeated: bool | null                 # non-null only for CONFIRMED
  target_mpn_canonical: str
  historical_date: datetime | null
  historical_mpn: str | null
  historical_quantity: integer | null
  quantity_equal: bool | null
  creator: str | null
  inso_quote: Decimal | null
  currency: str | null
  checked_at: datetime
  evidence_ref: str | null
  reason_code: str | null
}
```

The INSO adapter returns only the newest qualifying same-model record. It does not return a hit count. `quantity_equal` compares the current integer order quantity with the historical integer quantity. The seven-day window is a rolling 168-hour interval in the INSO site timezone (Asia/Shanghai, UTC+8), inclusive at the lower boundary: `record_time >= now_site - 168h` and `record_time <= now_site`. Persist/compare timezone-aware timestamps. MPN matching uses duplicate normalizer version `dup-mpn-v1`: Unicode NFKC, trim leading/trailing whitespace, and ASCII case normalization to uppercase, followed by exact equality. Do not remove or rewrite internal separators/punctuation, internal whitespace, suffixes, prefixes, slashes, hyphens, dots, or other model characters; do not call Research's broader source matcher or guess.

No confirmed exact match means `repeated=false`; a technical failure, missing required fields, or more than one indistinguishable latest record is not a negative result and must fail closed. Where latest timestamps tie, use an INSO-provided stable record identity only if the read-only discovery proves one exists and is stable. If no such identity is available, return `AMBIGUOUS`; never use row order, DOM order, API response order, or an arbitrary first row as the tie-breaker.

### `NotificationCommand`, recipient, result and event

Main Programmer/Workflow decides whether and why to notify and renders business-ready content inputs. The Notification adapter only validates/delivers the command and reports delivery outcomes; it never decides duplicate/importance/customer tier/threshold/stock/pricing rules.

```text
NotificationRecipient { recipient_id: str, address: str }
NotificationCommand {
  command_id: str                         # stable idempotency key
  inquiry_id: str
  kind: IMPORTANT_ORDER | DUPLICATE_ORDER
  recipients: tuple[NotificationRecipient, ...]
  subject: str
  text_body: str
  html_body: str | null
  created_at: datetime
  payload_version: integer
}
NotificationResult {
  command_id: str
  recipient_results: tuple<RecipientDeliveryResult, ...>
  completed_at: datetime
}
RecipientDeliveryResult {
  recipient_id: str
  outcome: SENT | RETRYABLE_FAILURE | PERMANENT_FAILURE | UNKNOWN
  attempt: integer
  provider_message_id: str | null
  reason_code: str | null                 # sanitized, no credentials/raw SMTP secrets
  next_attempt_at: datetime | null
}
NotificationEvent {
  event_id: str
  inquiry_id: str
  command_id: str
  recipient_id: str | null
  type: COMMAND_CREATED | DELIVERY_FAILED | RETRY_SCHEDULED | DELIVERY_SUCCEEDED | ALERT_RECOVERED | PERMANENT_FAILURE
  occurred_at: datetime
  detail_code: str | null
}
```

Idempotency is per command and recipient. Use a stable `command_id` derived from `(inquiry_id, kind, business decision version)` and a unique persisted `(command_id, recipient_id)` delivery row. Persist `SENT` before acknowledging completion; subsequent retries send only recipients not already `SENT`. Provider idempotency may be used if available but does not replace the local uniqueness/recipient ledger. Initial delivery plus retries after 1, 5, and 15 minutes gives at most four attempts. Retry only transient errors; authentication/configuration failure and permanent recipient rejection stop retry for that recipient. Unknown transport outcome must be reconciled or held for review before resend to avoid duplicates.

Important-order trigger and content:

- A: always; no stock or threshold condition.
- B: estimated total `> 50,000` and the canonical Research stock result is `货少`.
- C: estimated total `> 300,000` and canonical Research stock is `货少`.
- Notification consumes Research's canonical stock, minimum market reference price, and estimated total; it does not calculate stock or prices. A-level mail shows the actual stock result, including `货足`.
- Subject: `【重要订单】【{tier}】{customer}｜{mpn}｜¥{estimated_total}｜{stock}`. Body is structured HTML plus plain-text fallback with customer, tier, MPN, brand, quantity, stock, market minimum reference price, estimated total, trigger reason, and `请及时人工跟进该订单`.

Duplicate mail is unconditional when `repeated=true`, independent of tier, amount, stock, or need-full-price. It includes current order customer/model/brand/quantity/Research stock and available market reference price/estimated total; latest history date/quantity/equality/creator/INSO quote; current quantity × INSO quote total; and a human follow-up request. Currency and missing-value display are explicit; no invented amount is allowed.

Sender and recipient settings are non-secret runtime configuration. The Owner-specified sender is `1069599116@qq.com`; the initial recipients are `linan229@qq.com` and `shawn@inso-hk.com`. Treat these as runtime config values, not code constants. SMTP credential is retrieved through the approved Credential Provider at runtime and is never part of this contract, config file, event, log, or test fixture. WorkBuddy's Notification implementation owns SMTP transport; this spike defines only the integration contract.

### `PurchaseDraftCommand` and result

```text
PurchaseDraftCommand {
  command_id: str                         # stable per inquiry and draft revision
  inquiry_id: str
  customer_name: str
  customer_tier: A | B | C | OTHER
  mpn: str
  brand: str
  quantity: integer
  inventory_status: canonical Research stock value
  estimated_total: Decimal | null
  market_minimum_reference_price: Decimal | null
  quotation_type: NEED_FULL_PRICE | NORMAL_INQUIRY
  purchaser: str                          # 颜浩坚 or 陈熙
  ai_input: str                           # MPN + six U+0020 spaces + Brand + six U+0020 spaces + quantity
}
PurchaseDraftResult {
  command_id: str
  outcome: AI_RECOGNIZED | VALIDATION_FAILED | SAVED | RETRYABLE_PRE_SAVE_FAILURE | UNKNOWN_WRITE_OUTCOME
  recognized_mpn: str | null
  recognized_brand: str | null
  recognized_quantity: integer | null
  field_checks: map[str, PASS | FAIL | UNKNOWN]
  saved_record_ref: str | null
  evidence_ref: str | null
  reason_code: str | null
  completed_at: datetime
}
```

Quotation type is separate from important mail: full-price iff A, or B and estimated total `> 50,000`, or C and estimated total `> 300,000`; stock does not affect this rule. Otherwise use ordinary inquiry. Purchaser is `颜浩坚` for full-price and `陈熙` for ordinary.

If the canonical estimated total is unavailable where a B/C threshold decision is required, do not assume the order is ordinary; hold purchase routing for manual review until the input is determinate.

AI input is exactly `MPN + six U+0020 spaces + Brand + six U+0020 spaces + quantity`. Wait on an explicit ready state such as button `重新识别`; a fixed delay alone is insufficient. Verify MPN canonical exact equality, Brand after trimming surrounding whitespace with exact comparison, and integer quantity equality. Any mismatch/unknown blocks Save Data, captures redacted evidence, records a security event, and raises active alert `采购录单异常`.

## 3. Business state, event history and active alerts

Keep three separately queryable concepts:

- **Business state:** current order progression (`business_state` and `business_state_updated_at`). It does not encode mail delivery or red-alert status.
- **Event history:** append-only, timestamped order events, including workflow transitions, security events, every notification attempt/retry/result, and recovery. Never overwrite old events.
- **Active alerts:** keyed open alerts with `alert_id`, `inquiry_id`, `alert_type`, `raised_event_id`, `active`, `raised_at`, optional `recovered_at`, and `recovered_by_event_id`. Multiple alerts can be active for one order.

Examples: `DUPLICATE_ORDER` remains active after a duplicate notification failure is recovered; `NOTIFICATION_FAILED` closes only when every intended recipient for that command has a confirmed `SENT` result. If any recipient ends in `PERMANENT_FAILURE` or unresolved `UNKNOWN`, the notification alert remains active even though the business/purchase flow is non-blocking. A later explicitly approved/manual resend that produces `SENT` for the remaining recipient may recover the alert; prior failure events stay in history. Preserve failure → retry → retry success events even after alert recovery. `PURCHASE_EXCEPTION` raises `采购录单异常` and remains until an explicit human resolution event.

Dashboard contract: for each inquiry, show the newest still-active red alert by `(raised_at, alert_id)`; if none remains, show the normal business label. Detail view returns the complete event history, including recovered alerts. Do not collapse active alert list or event history into one `status` string.

## 4. Workflow event/state additions

Proposed durable event vocabulary: `DUPLICATE_CHECK_STARTED`, `DUPLICATE_CHECK_CONFIRMED`, `DUPLICATE_CHECK_FAILED`, `RESEARCH_STARTED`, existing Research completion/retry outcomes, `DUPLICATE_ORDER_DETECTED`, `IMPORTANT_ORDER_DECIDED`, `NOTIFICATION_COMMAND_CREATED`, `NOTIFICATION_DELIVERY_FAILED`, `NOTIFICATION_RETRY_SCHEDULED`, `NOTIFICATION_DELIVERY_SUCCEEDED`, `ALERT_RECOVERED`, `PURCHASE_DRAFT_STARTED`, `AI_RECOGNITION_READY`, `AI_RECOGNITION_MISMATCH`, `PURCHASE_DATA_SAVED`, `SECURITY_CHECK_FAILED`, and `HUMAN_RESOLUTION_RECORDED`.

Each event has a stable event ID, inquiry ID, event type, occurred-at timestamp, source module, schema version, and sanitized structured payload. Event insertion and the associated business/alert mutation must be one SQLite transaction. Do not store passwords, tokens, full SMTP responses, or screenshot image bytes in SQLite.

## 5. Sheets customer schema without GUI business logic

Extend `WorksheetSchema` with a customer source strategy, not GUI conditionals. Proposed strategies: `FIXED_VALUE("SHAHAB")` for the confirmed SHAHAB worksheet and `COLUMN("D")` for the 2026 worksheet. Normalize customer name into the public `PendingSheetRecord` while retaining original worksheet identity and raw provenance. Schema selection belongs in `src/sheets/worksheet_schema.py`; workflow rules consume `customer_name` and tier inputs; GUI displays returned data only. Preserve the configured original worksheet title and the existing case-insensitive SHAHAB schema selection. Customer source is enabled only for the exact worksheet identity `2026` (preserving the original API title) and case-insensitive `SHAHAB`. Other worksheet titles remain V1-compatible but have no V1.2 customer source unless explicitly added later. For `2026`, D-column blank/unknown customer names are never guessed; use an explicit missing-value marker for notification rendering, raise a data-quality event/alert, and do not infer tier from customer name. Tier continues to come from the existing importance field. Missing customer name does not invalidate Research; purchase/notification routing may continue only where the required business inputs are otherwise determinate and any outward content explicitly shows the customer as missing rather than inventing a value.

## 6. INSO page/session lifecycle

`src/launcher` is the composition root and owns an explicit per-run/per-inquiry `InsoSessionLease`, acquired before duplicate check and released in `finally` after Research and (when eligible) purchase entry. The lease contains explicit browser connection, authenticated context identity, owner (`APP_OWNED` or `REUSED`), readiness, and child page handles. It is passed to adapters; no module reads a global page or discovers an arbitrary first tab. Serialize use through the single Workflow worker.

Duplicate check and Research use the same authenticated browser/context/session lease. Purchase entry reuses it only if the lease remains healthy and the expected authenticated page identity is proven. Each operation owns only its background child page and closes that child in `finally`; it does not close the user's original tab. A session-level close is allowed only for a browser explicitly launched/owned by this application; never close a reused browser. If an adapter cannot operate over an explicit shared lease, do not claim page reuse: reconnect only to the verified same endpoint/context and fail closed if identity cannot be proven. Login expiration, page closure, context ambiguity, changed DOM, or unknown ownership stops the operation, records a sanitized security event and captures evidence where safe. No CAPTCHA/OTP bypass.

This is a design seam: current Research adapters independently attach to CDP and some own their child pages. A bounded integration change is required so V1.2 can share explicit ownership without changing Research's business rules. Safety Supervisor must review browser identity, ownership, target selection, page cleanup and restart recovery before any live use.

## 7. WRITE ALLOWLIST — initial proposal

No write code is authorized by this spike. Before a future operation is allowed, its Safety-reviewed allowlist must bind each action to an authorized page, current `inquiry_id`, uniquely verified control, expected current value, desired value and post-action read-back.

| Area | Allowlisted when separately approved | Explicitly forbidden |
| --- | --- | --- |
| Navigation/read | Open approved INSO business inquiry area; read history; select the unique `新增` action for the verified new inquiry | Guessing page/row, acting on multiple candidates, editing history |
| Draft fields | Select confirmed customer `Win Source Elec. Tech. Ltd`, quotation type and assigned purchaser; enter only current inquiry MPN/Brand/quantity through the approved AI input | Unknown fields, unrelated rows, bulk edits, clearing unknown values, Brand write outside current draft |
| AI review | Click unique `AI智能识别`; read model/brand/quantity; click outside purchaser selector only after target and safe blank area are verified | Saving if any recognition result is missing, ambiguous or mismatched |
| Commit | Click the unique `保存数据` control only after all allowlisted fields and AI checks pass; read back saved result; capture evidence | `保存并发送` under every code path; delete, edit historical inquiry, submit/send/publish, or any unlisted action |

Before every write: verify page and authenticated context identity; current inquiry identity; unique control semantic/visible text; and determinate current/target values. After save, verify a unique saved record identity and field values. Any mismatch, duplicate candidate, DOM change or uncertain write outcome fails closed, stops that inquiry, captures evidence and raises `采购录单异常`. Never retry a save with unknown outcome until read-only reconciliation proves whether the first save created a record.

The owner explicitly authorized `保存数据` for the stated current behavior, while `保存并发送` remains prohibited. This design still requires Safety Supervisor approval of the concrete selectors, identity guards, read-back, recovery and evidence implementation before the authorized control is used in production. Production Brand write remains disabled.

## 8. GUI integration

Preserve existing `GuiBackend` methods and V1 result-history behavior. Add optional/new DTO queries for inquiry summaries, active alerts and event history; do not make GUI import Workflow/INSO/Research internals. The backend/launcher translates persisted events into presentation DTOs. Existing V1 histories remain available during migration; V1.2 order details are additive. Dashboard shows latest active red alert, with multiple active alert data available to details; details show all events and recovered labels. Business label after successful Save Data is exactly `已发采购单`, per Owner instruction, even though `保存并发送` is never used. GUI never calculates thresholds, stock, customer tier, email eligibility, quotation type, or buyer.

## 9. SQLite and migration strategy

V1.1 `workflow_items` schema has no explicit migration registry/version marker and its status CHECK constraint must not be widened in place. Keep its rows and semantics intact. Add a transactionally-created additive V1.2 schema, tracked with `PRAGMA user_version` after first detecting/recording the existing schema baseline. Candidate tables: `inquiry_v2_state` (one row per existing workflow item), `duplicate_check_results`, `workflow_events`, `active_alerts`, `notification_commands`, `notification_recipient_deliveries`, `purchase_drafts`, and optional `schema_migrations`. Use foreign keys where reliable; unique keys for inquiry/command/recipient idempotency; UTC ISO timestamps; JSON only for versioned extensible payloads, not as a substitute for queryable state.

Migration is additive and transactional, repeatable, and backed up through the existing runtime backup policy once defined. Preserve every V1 row and status. Existing terminal V1 rows are never reprocessed or retroactively given duplicate/purchase actions. Existing queued items enter the new gate only after the V1.2 feature is explicitly enabled; interrupted V1 `RESEARCHING` rows follow the existing Research completion-confirmation behavior before any V1.2 routing. Never drop/rewrite tables during upgrade. Rollback disables V1.2 orchestration while preserving its audit tables; V1.1 source remains recoverable at `release/v1.1` (`be9d0a51d0375884dfa3e5e9e4317958899fdc75`). Backup/restore and downgrade mechanics remain for implementation design.

## 10. Notification integration seam

Workflow creates and persists a finalized `NotificationCommand` and schedules recipient deliveries. Notification adapter exposes `send(command, recipient) -> RecipientDeliveryResult` (or equivalent) and has no access to Research, duplicate policy, customer-tier policy, Sheets, or GUI internals. The Workflow notification worker persists each recipient result and retry time, retries due recipients independently, and emits history/alert events. SMTP host/port/TLS/from-address may be non-secret runtime configuration; authentication is obtained from Credential Provider. WorkBuddy can implement the adapter independently against this contract. No SMTP client or credential handling is implemented in this spike.

## 11. Evidence path and data handling

Failure screenshots are written only beneath Git-ignored `runtime/evidence/<inquiry_id>/`, with opaque validated path components and collision-safe filenames. Store only a relative evidence reference in SQLite. Capture only the relevant page/region when possible, redact credentials, tokens, unrelated customer/order rows and personal data before persistence, and never put evidence in tests, Git, logs, or release artifacts. If safe redaction cannot be guaranteed, record the failure code without a screenshot and require human review. Default evidence retention is 30 days, but V1.2 must not perform automatic destructive deletion in the first production release. Evidence cleanup is a separate explicit/manual maintenance action after review. SQLite migration must create a timestamped backup of the workflow database before the first V1.2 schema change, keep the original file intact until migration succeeds, and use additive/repeatable changes only. V1.1 rollback ignores V1.2 audit tables; no downgrade path may drop data automatically.

## 12. V1.2 verification matrix

All checks below are deterministic/fake-only until separately authorized smoke approval.

| Area | Required cases |
| --- | --- |
| Duplicate contract | exact canonical match; separator/case normalization approved examples; suffix/prefix near-miss; no fuzzy match; exact 7-day boundary/time zone; latest-only selection; quantity equal/unequal; ties/ambiguous; unavailable/auth expired; required history fields missing |
| Routing | duplicate still runs Research then stops purchase; nonduplicate runs Research then routes; duplicate alert remains after mail recovery; duplicate-check failure never treated as nonduplicate; Research rules and existing regressions unchanged |
| Notification rules | A always including `货足`; B/C strict `>` thresholds and `货少`; thresholds independent of full-price stock rule; duplicate unconditional for every tier/stock/amount; HTML/plain text required fields; unavailable canonical price handled without invention |
| Notification delivery | per-recipient successes/failures; initial + 1/5/15 schedule; permanent/auth/config failure no retry; A success/B fail retries B only; idempotent restart; unknown send outcome does not blindly resend; alert active/recovered/history retained |
| Purchase decision | A/B/C × strict amount threshold; stock independent; exact purchaser mapping; six-space format; recognition ready signal; exact MPN/Brand/quantity validation; no save on mismatch |
| Write boundary | page/order/control identity; zero/multiple controls; changed DOM; session expiry; read-back mismatch; `保存数据` allowlisted only after Safety signoff; static/runtime assertion forbidding `保存并发送`; unknown save outcome reconciled without duplicate save |
| GUI | V1 backend compatibility; multiple active alerts; latest active alert selection; recovered alert removed from dashboard; full historical events retained; V1 completed/history rendering unchanged; `已发采购单` label |
| SQLite/evidence | upgrade from real-shaped V1 schema using synthetic data; idempotent migration; rollback/read compatibility; event/alert transactionality; restart/retry idempotency; ignored evidence path; no secret/sample customer data |
| Session lifecycle | explicit same lease across duplicate read/Research/purchase; reused browser stays open; owned browser closes only after work drains; child tabs cleaned; no arbitrary global page; login/page loss fail closed |

## 13. Implementation split and approval gates

1. CEO reviews product decisions and approves the additive module/public-contract design; resolve date-window and MPN normalization choices, 2026 worksheet identification and unknown-customer handling, check-failure/Research ordering, latest-record tie behavior, and evidence retention.
2. Safety Supervisor reviews `WRITE ALLOWLIST`, page/order identity, selector uniqueness, session lease/ownership, save boundary, forbidden action enforcement, read-back, unknown-outcome recovery and screenshot redaction. No live write implementation/smoke before approval.
3. Implement pure contracts/normalization and fake tests; no adapters or runtime wiring.
4. Implement/additively migrate Workflow persistence and event/alert/retry services; verify V1 DB compatibility and V1 Research regression suite.
5. Extend Sheets worksheet schema to return customer name and provenance; test 2026 D / SHAHAB fixed name / unknown handling.
6. WorkBuddy builds Notification adapter against this contract; Workflow integration tests include fake recipient transport; never test with real business recipients during development.
7. After Safety approval, implement INSO duplicate read using approved read-only browser discovery and the explicit session lease; capture no production records into fixtures.
8. After a separate Safety-reviewed write implementation and explicit production smoke gate, implement the allowlisted draft entry and controlled Save Data step; preserve Save-and-Send prohibition.
9. Add GUI summary/alert/history DTOs and verify V1 display compatibility.
10. Stage-gated synthetic integration, local fake-browser tests, review, then separately authorized production smoke. Do not merge `main` as part of this spike.

Safety Supervisor must approve before any real INSO write, `保存数据` click, real production smoke, selector/allowlist rollout, live evidence retention, or real notification delivery. `保存并发送` is prohibited regardless of approval.

## CEO decisions and remaining UNKNOWN

CEO decisions are now frozen for implementation:
- Seven-day duplicate window: rolling 168 hours, inclusive lower boundary, INSO site timezone Asia/Shanghai (UTC+8), timezone-aware comparisons.
- Duplicate MPN normalizer: `dup-mpn-v1` = Unicode NFKC + outer trim + ASCII uppercase, then exact equality; preserve all internal separators/punctuation/whitespace and never fuzzy-match.
- Customer source: exact worksheet `2026` -> D column; case-insensitive `SHAHAB` -> fixed `SHAHAB`. Unknown/blank customer is explicit missing data, never guessed.
- Duplicate lookup failure does not prevent unchanged V1.1 Research from running, but post-Research routing/purchase remains blocked until duplicate result is confirmed.
- Latest-history tie: stable INSO record ID if proven by read-only discovery; otherwise `AMBIGUOUS`.
- Notification alert recovers only after every intended recipient is confirmed `SENT`; permanent/unknown recipient failure remains an active notification alert but never blocks purchase.
- Evidence: Git-ignored `runtime/evidence/<inquiry_id>/`; 30-day default retention policy, with no automatic destructive cleanup in initial V1.2.
- SQLite: additive transactional migration with a timestamped pre-migration database backup; no automatic downgrade/drop.

Remaining UNKNOWN requiring Safety-reviewed read-only discovery, not CEO product invention:
- INSO live DOM/control identities and unique selectors.
- Stable historical record identity available for timestamp ties.
- Exact saved-draft identity/read-back fields after `保存数据`.
- Whether the authenticated CDP context can support the proposed explicit shared session lease without weakening V1.1 Research isolation.
- Screenshot regions/redaction masks that are actually safe on the live page.

No real write, real notification delivery, or production smoke is authorized by this architecture approval.


## CEO Safety Review decisions

Safety commit `72b60c72738ed19c05e010bb592d9301a6af74d3` is accepted. B1-B4 are implementation blockers for any live-capable path and are mandatory Main Programmer work, not optional recommendations.

Frozen implementation decision for AI-recognition MPN comparison:
- define a separate policy/version `ai-mpn-v1`;
- normalization semantics are Unicode NFKC + outer trim + ASCII uppercase, then exact equality;
- preserve every internal separator, punctuation mark and whitespace character;
- no fuzzy/suffix/prefix guessing;
- it may share low-level normalization primitives with `dup-mpn-v1`, but it remains a distinct named/versioned contract so either policy can evolve independently.

Approved development scope after this review:
- fake-only/public contracts, additive SQLite persistence, event/alert state, migration/backup implementation against synthetic databases, deterministic safety guards/tests, and browser/session ownership refactoring are allowed;
- B2 may implement the durable `UNKNOWN_WRITE_OUTCOME` state and reconciliation interface, but no live Save Data implementation can be enabled until discovery proves a stable saved-record identity/read-back contract;
- no live INSO write, no real SMTP delivery, no production smoke, and no live read-only discovery is authorized by this decision.

A future read-only discovery execution remains a separate gate. Main may prepare the inspector and deterministic tests, but must not run it against production until CEO/Owner explicitly authorizes the target/session/scope.
