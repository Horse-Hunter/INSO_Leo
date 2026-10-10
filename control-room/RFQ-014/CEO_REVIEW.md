# V1.4 RFQ-011～014 CEO Independent Review

Date: 2026-10-10  
Status: COMPLETE  
Verdict: **PASS / REVIEWED_DONE**  
Reviewed branch: `codex/v1-4-order-mail-inspection`  
Reviewed HEAD: `7a5728388fc14cd685521d520e23fbfa19536988`  
Reviewed base: RFQ-010 REVIEWED_DONE `b1a11820bff01e939b63dba0cf0072318787ce1f`

## Scope reviewed

Independent review covered the six commits from the RFQ-010 reviewed base through
`7a572838...`, including RFQ-011, RFQ-012, RFQ-013, the sales-list readiness
repair and RFQ-014 mail-copy/recipient correction.

No new blocker was found within the currently authorized V1.4 development scope.

This review approves the source increments. It does **not** convert documented live
UNKNOWNs into evidence and does not authorize production deployment or automatic
Save/submit-review behavior.

## RFQ-011 — contract details / ICNET packages

PASS.

- Contract parsing requires one unambiguous detail header and the required
  Part Number, L/T, Brand, DC, QTY and Unit Price fields.
- Formula/blank/unsupported values fail closed.
- QTY must be a positive integer; Unit Price must be a positive numeric value and
  is passed as the original RMB untaxed price without FX/tax recalculation.
- Lead time is implemented exactly as Owner clarified:
  `1-3 DAYS -> today + 7`; `X-X WEEKS -> max_weeks*7 + 7`.
- One Asia/Shanghai date is captured per invocation.
- ICNET uses the existing CdpIcNetClient / CoreResearchCredentials / login/search
  path. There is no second ICNET login/search implementation.
- Package parsing reads displayed result rows in DOM order, takes at most the first
  20, performs no secondary MPN filtering, ignores empty package values and uses
  mode with stable first-seen tie behavior.
- Existing Research brand/stock/model-matching code remains separate.
- Sales detail writes are allowlisted to the eleven Owner-authorized fields.
  Amount/total, CONDITION, Save, submit-review and PDF are absent from the detail
  edit surface.
- Native row addition is checked +1 at a time; excess existing rows stop rather
  than delete.
- Immediate, per-row and final whole-table readbacks are enforced.

The historical live evidence for the two authorized samples (one detail row and
four detail rows) is accepted as evidence for those samples only.

## RFQ-012 — one-shot oldest unprocessed order / independent sales tabs

PASS.

- The GUI action remains one-shot; there is no order-mail scheduler.
- Selection uses read-only QQ IMAP and the existing Vault credential.
- INBOX is opened read-only; candidate/body reads use PEEK and FLAGS are audited.
- Candidate ordering is by IMAP INTERNALDATE with UID tie-break.
- Candidate header work is bounded; only the selected message body/attachments are
  loaded.
- Completion identity is stored only as opaque local hashes and timestamp; no raw
  customer/PI/mail body is persisted in the receipt ledger.
- A successful automation pass is recorded only after the currently authorized
  field and PDF verification sequence completes; failed runs are not marked.
- Each invocation gets a distinct V1.4 owned sales tab. Older Owner-review tabs
  remain protected and are not borrowed by inquiry/purchase/quotation flows.
- V1.4 worker state is independent of the inquiry run state.

The documented Message-ID revision/reuse semantics beyond the current identity
model remain UNKNOWN and are not silently generalized by this review.

## RFQ-013 — PDF attachment upload

PASS for the implemented bounded upload action.

- The selected order must have exactly one valid, non-encrypted, parseable PDF.
- PDF bytes remain in memory and are supplied to the native file input; no contract
  file is written into Git/runtime as an attachment cache.
- Existing attachment/queue content causes a stop rather than blind overwrite.
- The native “开始上传” action is dispatched at most once per adapter instance.
- Success requires the uploader count/status, queue success marker, exact filename
  and visible persisted attachment link to agree.
- Unknown upload settlement fails closed and does not automatically click Start
  again in the same invocation.
- The local filled receipt is written after field verification and confirmed PDF
  upload, not before.

The real-site control structure was inspected, but the branch does not contain
independently reproducible evidence that both sample PDFs completed the entire
real upload confirmation path. That remains **UNKNOWN**, exactly as the executor
report states.

## Sales-list readiness repair

PASS.

The earlier iframe-attachment/readiness race is corrected by a bounded readiness
wait for one canonical sales-list frame and one visible enabled native add button.
The repair does not loop menu/add clicks and preserves ownership/prompt safeguards.

## RFQ-014 — SMTP copy and latest V1.4 recipient rule

PASS.

The changes to existing V1.2/V1.3 mail paths are presentation-only:

- command identity/dedup behavior remains unchanged;
- recipient routing remains unchanged for important order, duplicate, quotation,
  website/runtime, model-difference and purchase-follow-up paths;
- purchase/quotation trigger and retry logic are unchanged;
- internal identity/reason codes remain in durable keys/ledger where required but
  are removed from human-visible copy.

The latest Owner rule for **V1.4 order-entry exceptions** is correctly isolated:

- new V1.4 exception commands contain only `linan229@qq.com`;
- `shawn@inso-hk.com` is no longer a recipient for this category;
- the owner-only transport wrapper exists only inside the isolated V1.4
  `OrderExceptionNotifications` service;
- old V1.4 queued non-owner recipients are blocked before SMTP and settled with an
  existing terminal outcome without rewriting the immutable command;
- other notification services do not pass through this wrapper.

The V1.4 exception body is concise: order, optional model, situation and treatment.
No stack trace, provider error, internal reason code, UID or implementation detail
is inserted into the visible mail.

## Existing V1.3 regression review

PASS.

The reviewed range modifies existing V1.3 production source only where required for
the approved mail-copy refresh and V1.4 tab integration. Independent diff review did
not find changes to the established V1.2/V1.3 purchase, quotation, duplicate,
cooldown, hold, Google-write or Research business decisions.

Existing recipient exceptions remain intact, including the two-recipient
NO_MATCHING_PRODUCT/model-difference/purchase-follow-up paths where previously
approved.

## Evidence accepted

Executor reports at final reviewed HEAD:

- latest recipient-focused suite: **67 passed**;
- full safe/offline: **1846 passed / 1 skipped**;
- Ruff: **PASS**;
- `git diff --check`: **PASS**;
- no real SMTP test in this final increment;
- no production DB/Google write;
- no V1.4 package/deployment.

Earlier scoped evidence within this reviewed range includes RFQ-011/012/013 focused
and full regressions and the two-sample detail-entry observations described in
their reports.

## Live / product UNKNOWNs retained

The following are **not** converted to PASS claims by this review:

1. a complete real simultaneous inquiry + V1.4 order-entry run with business side
   effects;
2. independently reproducible full PDF-upload confirmation for both real samples;
3. behavior for future Excel layouts outside the two approved samples;
4. Message-ID reuse/revision business semantics beyond the current local identity
   model;
5. the final production order lifecycle after Owner review.

## Future production gates

These are not RFQ-011～014 blockers, but they remain required before claiming the
original V1.4 end product complete:

- final Owner-approved Save / submit-review boundary;
- final decision on automatic 15-minute order-mail scheduling;
- final per-order tab lifecycle/closure after the approved terminal state;
- production duplicate/recovery behavior around an interrupted or discarded
  Owner-review order;
- any additional business-level contract duplicate rule the Owner chooses to add.

Current source intentionally leaves Save and submit-review to the Owner and keeps
the reviewed sales tab open. Therefore this review is **not** authorization to call
V1.4 a completed production release.

## Release decision

**RFQ-011, RFQ-012, RFQ-013 and RFQ-014: PASS / REVIEWED_DONE.**

A build/package may only be created after a new explicit Owner instruction.
Production deployment remains separately gated and must not be inferred from this
review.

## Final state

`RFQ-011 REVIEW_REQUIRED -> REVIEWED_DONE`  
`RFQ-012 REVIEW_REQUIRED -> REVIEWED_DONE`  
`RFQ-013 REVIEW_REQUIRED -> REVIEWED_DONE`  
`RFQ-014 REVIEW_REQUIRED -> REVIEWED_DONE`
