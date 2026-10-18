# Diagnose Google web read stops and preserve next-poll recovery

status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-18

## Owner request / scope
After page reuse, investigate two Google failures which stopped the program.
Transient unavailability must retry once, notify229 after exhaustion, then retry
normally next15-minute poll. Reuse existing reader/defer/outbox logic.
Authorized: passive read-only local sanitized logs, code/tests, normal V1.4 Git
publication. No CDP, credentials, production DB writes, real orders/Sheets/script/
SMTP, package or EXE overwrite. Preserve authentication and safety stops.

## Evidence / limits
Installed log records 2026-10-18 14:59:58 and15:18:04, both
SHEETS_READ_UNAVAILABLE. Deepest explicitly logged classes are V12Fault and
UpdateAttemptUnconfirmed. Their underlying page failure/reason was not retained;
actual network/auth/DOM cause remains UNKNOWN. Neither incident can honestly be
called an OAuth or network outage. Code confirms actions._attempt wraps page
load/menu timeouts, retaining exception context. Web range transport recognizes
only directly raised Playwright TimeoutError. Confirmed temporary failures behind
the wrapper thus miss the existing one-retry/next-poll recovery path.

## Acceptance
Translate only positively identified temporary read failures to the existing
reader/defer contract. Unknown wrappers, schema/identity, permission/auth/security
faults and write ambiguity remain closed. Keep fresh-page isolation; never
repeat a script click. Sanitized stage/reason diagnostics only, no HTML/URLs/text
or customer data. Test real actions/web/reader/defer/outbox failure, retry,
notification, next-cycle recovery and negative cases; full offline regression.
REVIEW_REQUIRED after normal V1.4 push. No real incident replay; live UI UNKNOWN.

## Implementation and verified outcome
Only launcher Google web read transport changed. Walk both explicit cause and
implicit exception context, allowing known timeout/connection evidence and a
closed list of Chromium transient network codes behind the existing known
UpdateAttemptUnconfirmed wrappers. Any V12Fault, unknown wrapper, certificate,
schema/identity, login/security fault or unknown intermediate cause remains
non-transient. A failed load leaving its owned page blank/closed can retry;
newly detected auth/CDP/document identity faults still stop immediately.
Write setup/fill/readback/script ambiguity are never reclassified as reads.
Existing GoogleSheetsRowReader still owns exactly two attempts; existing poll
defer/outbox owns the229 notification and next900-second polling interval.
No new scheduler, notification queue, business state or pricing logic.

Failed phases retire their pooled page before any next call: ordinary safe
failed reads close; unsafe/unknown work is quarantined and next phase opens a
fresh page. Existing unsaved/script exclusion and protected Owner tabs remain.
Added reusable existing diagnostics logger records safe stage, exception class
and classified reason, without exception text/HTML/URL/customer data in the
configured runtime file. Prior 14:59 V12Fault subtype and actual site/network
cause of either historical event remain UNKNOWN; no unsupported diagnosis of
expired OAuth or two definite network failures is asserted.

101 focused PASS; retirement/quotation/source/security focused117 PASS.
**Final complete offline regression:2205 passed,1 skipped,74.47s; Ruff PASS.**
Actual synthetic native actions/menu timeout -> web transport -> real Sheets
reader -> production poller -> durable simulated229 mail transport: two failures,
exactly one notification, stop flag unset, virtual900-second next poll succeeds
through both2026/SHAHAB, no work item or browser/Sheets/SMTP production operation.
Negative tests cover unknown errors, wrapper without cause, certificate failure,
auth discovered after timeout by real guard, schema faults and write failures.
Diagnostics are checked through the actual runtime sanitizer. Previous page
reuse's final physical retry-reset boundary is covered by this full run too.

Production endpoints/9222/browser launch-close blocked throughout tests; only
explicit test-owned ephemeral loopback/local synthetic dependencies allowed.
All test-owned runners, synthetic DB/Vault/fixture copies and preliminary logs
removed after resolved path/reparse checks. Only this packet and prior packet
hold durable evidence; no raw production logs/data committed. Local HEAD/index
and unrelated dirty work preserved. No packaging/overwrite, real CDP, credentials,
production DB writes, customer orders, real Sheets or SMTP tested. Live UI and
historical incident replay remain UNKNOWN. REVIEW_REQUIRED; CEO independent
Review next. Installed executable remains the prior Owner-authorized build.

Passive installed configuration check confirms worksheet_titles=2026,SHAHAB.
Both inquiry and quotation loops iterate those worksheets; a failed earlier read
can interrupt a historical poll before SHAHAB. Historical logs cannot prove both
sheets completed in the stopped rounds. Synthetic next-poll test covers both.
Installed EXE SHA256 remains
a791d0f142b8e6260fb7f2ecd7f65aaf71bef8cb05c8cca8a779db7f9dd2d82a.
