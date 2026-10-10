# RFQ-014 — REVIEW_REQUIRED

Owner authorized copy review of ALL mail to229/shawn, including single-recipient.
Audited every production NotificationCommand and operator-alert builder/SMTP call.

| Category | Recipient path | Result |
| --- | --- | --- |
| Important order | configured229 + shawn | Short subject, keep business fields/prices; remove tautological rule note |
| Duplicate order | configured229 + shawn | Chinese copy; preserve history/quantity/quote facts and manual follow-up |
| Order/purchase exception (6 stages + uncertain submit) |229; no-price also shawn | Remove internal ID, phase/reason code; keep location and safety guidance |
| Quotation exception |229 | Clear known/unknown update result and conditional next step |
| Runtime fault |229 | Human situation + relevant action; no code/module version |
| Website issue |229 | Site/model + human reason; no ID/code/raw provider text |
| Quotation model difference |229 + shawn | Both original models/location, update unconfirmed; remove implementation detail |
| Login/operator stop |229 | Short instructions; distinguish generic infrastructure stop from login need |
| Idle login maintenance |229 | Reviewed, already concise; unchanged |
| Purchase follow-up |229 + shawn | Keep working-hour threshold/location/time, remove calendar boilerplate/ID |
| V1.4 sales-entry exception |229 only | Latest Owner rule; historical non229 queued recipients blocked before SMTP |

No separate production shawn-only builder found. Dual-recipient commands are sent
one recipient at a time; independent retries/recipient scope outside V1.4 sales exceptions are unchanged and
covered by existing delivery/routing tests. Internal identity/reason remains in
command keys and ledger; only visible subject/body changes.

19 synthetic examples in MAIL_PREVIEWS.md, including owner-only messages and
purchase phases. No customer mailbox read or real SMTP/email sent for this task.
No production DB/queue rewriting or trigger/retry changes; only V1.4 sales-exception
recipient scope changes to229 as explicitly authorized,
new dependencies, EXE build or deployment. Already-created messages keep original
payload; current running GUI retains loaded code until restart. Official V1.3 is
not updated by this development branch; future release needs independent review.

Verification: focused292 PASS + final action-copy8 PASS; final full safe/offline
1845 PASS/1 SKIP; Ruff/diff PASS. CEO independent review required.

## Latest Owner recipient change
New V1.4 sales-entry exception commands contain only229. The isolated service's
transport guard also prevents non229 old queued recipients from SMTP dispatch;
they settle as PERMANENT_FAILURE using the existing enum/code (policy retirement,
not a claim of SMTP rejection). Immutable command payloads stay intact. No live
queue operation or real mail was performed. Other mail paths unchanged. Active
GUI must load revised source before this rule takes effect.
Focused67 PASS; final full1846 PASS/1 SKIP; Ruff/diff PASS. Consolidated CEO_REPORT.md supplied.
Owner explicitly requires independent Review before asking for packaging;
no build/deployment/release replacement has been performed.
