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

## Owner-authorized package/overwrite and CEO handoff
Owner now explicitly requests package/overwrite for manual testing, followed by
this report for CEO Review. This supersedes historical no-package/no-deploy
instructions for code399eab9 + ea278cca6618114fb1c1394608b8b7cf7bc4d3d5 only.
It does not assert CEO PASS or live business acceptance. Reuse canonical
BuildOnly/spec/scanner and changed-asset backup/deployment; preserve runtime,
DB/config/credentials/CDP/profile/tabs and all unrelated dirty work. Verify source
inputs, staged scan/self-check, installed hashes/idle GUI, then open idle only.
No automatic inquiry/order/Sheets/script/SMTP action. Retire owned stage/work and
transient helper, retain verified rollback/minimal evidence. REVIEW_REQUIRED.

### Installed release / CEO review receipt
Owner-authorized overwrite completed at existing
D:/Program_Leo/INSO_Leo/dist/INSO_V1.4/INSO_V1.4.exe.
Build source: ea278cca6618114fb1c1394608b8b7cf7bc4d3d5, including page reuse
399eab9943685cb005c7100667271c066174912b. All113 executable build-source/icon
inputs match that commit; no unpublished source code included. Canonical
BuildOnly, staged frozen self-check and RELEASE_SCAN_OK passed. All2875 staged
asset hashes match installed assets; only EXE/base_library.zip changed. Verified
old self-check and both changed rollback assets against the prior deployed
manifest; ignored usable rollback retained at
.tmp/v14-page-reuse-release-20261018/rollback/. Prior rollback sets preserved.
New installed EXE SHA256:
03cd1e738060a1eeffbe52b98e90d6008a18e2bc7e7d32bbd995fc98adad2cc2.

Installed self-check and idle GUI check PASS; visible INSO_V1.4 window responding.
Both inquiry and order-mail workers not started; Owner manually starts testing.
All970 protected files unchanged at copy verification; post-start non-log files
unchanged (no existing log file changed either). Existing browser page IDs
unchanged; no CDP WebSocket attach, browser launch/close, credential change,
real order/Sheets/script or SMTP action during release. Existing2026/SHAHAB
configuration unchanged. This is release/idle evidence, not live acceptance.

Exact marked non-reparse canonical stage removed:267809128 bytes retired;
PyInstaller work removed by the canonical script. Temporary deployment helper
removed. Retain only small ignored build/hash/startup evidence and verified
changed-asset rollback. All unrelated dirty work/local HEAD/index preserved.
Offline full suite2205 PASS/1 skipped remains the source-code validation; live
normal-poll reuse, production script behavior and historical incident root cause
remain UNKNOWN pending Owner testing/CEO Review. REVIEW_REQUIRED; no CEO PASS
is asserted merely because Owner authorized deployment. This original task and
../tasks/2026-10-18-poll-page-reuse.md are the review evidence; no duplicate report.


## CEO independent review — 2026-10-18 (deployed)

**CODE REVIEW PASS for scope 399eab9 + ea278cc; LIVE POLL / BUSINESS ACCEPTANCE UNKNOWN.**
Independent GitHub review of `6a09016..2a93aba` covered page-pool lifetimes,
INSO lease reset and reproof, Google wrapped-error classification, poll deferral,
read diagnostics, synthetic regression tests, and the executor's deployment receipt.

- Google grid transport retains a thread-local, poll-bounded session and
  guarded owned page. It still verifies active worksheet/gid/schema and authentic
  document identity for every read/write; ordinary bad-read pages are retired
  before the next attempt and protected/unsaved/script/human pages are not blindly
  re-used. Normal pages close at poll scope exit. The separate INSO quotation
  pool re-establishes login/native menu on page reuse, physically resets the
  failed query page before the existing 120-second retry, and does not close
  protected sales/manual-auth pages on normal cleanup.
- Temporary **read** errors are recognized only from specified wrapped
  Playwright timeout/network/connection causes; auth, schema, unknown wrappers
  and write uncertainty remain fail-closed. GoogleSheetsRowReader retains
  its initial+one retry; exhaustion uses the established durable 229 notice,
  no permanent stop flag, and the ordinary next 900-second poll.
- Reviewed synthetic tests cover 2026+SHAHAB reuse, next-poll new page,
  failure isolation, script/input protection, foreign thread ownership,
  wrapped timeout/network retry, unsafe/auth negative cases, actual simulated
  poller deferral/notification and next cycle. Executor reports full
  **2205 PASS / 1 skipped**, Ruff PASS, frozen scanner/self-check/idle GUI PASS.
  CEO did **not** independently execute the local test suite, inspect the
  installed binary, or attach to real Chrome/Sheets/INSO.
- Executor's Owner-authorized release receipt records install at the original
  V1.4 path, installed EXE SHA256
  `03cd1e738060a1eeffbe52b98e90d6008a18e2bc7e7d32bbd995fc98adad2cc2`,
  retained changed-asset rollback and original protected assets, and a
  responsive idle GUI. These are **Executor attestations**, not direct
  CEO runtime attestation.
- Logs at 14:59:58 and 15:18:04 only establish earlier
  `SHEETS_READ_UNAVAILABLE` events. Their underlying website cause remains
  **UNKNOWN**; do not claim OAuth, browser outage or any actual recurrence is
  proven. Real page reuse performance, both-tab traversal and Google writes
  remain **NOT YET ACCEPTED**.

**Disposition:** `CODE_REVIEW_PASS` on these two scoped fixes. Deployed
pending Owner-run business observation. No more coding is requested solely
for Review and **no automatic replay** is authorized. Before clicking 开始询价,
Owner should be aware that existing 2026/SHAHAB rows and all three quotation
statuses may be processed (including existing older items), not only a newly
arrived order. Check intended business scope and current Chrome/login state;
retain rollback and baseline. On manual start, record sanitized cycle/status
logs, source-title traversal, whether transient errors recover next poll, and
actual changed cells/script outcomes; no duplicate manual clicks or replays on
an uncertain write. If unexpected writes/auth/sessions occur, stop the business
worker without closing protected tabs and investigate before retry.

No real order, live data, package, process or browser action was performed
by the reviewer.

## Reopened: Owner reports repeat stop after installed manual run
status: REVIEW_REQUIRED (same bounded read-recovery task)
Latest sanitized installed log2026-10-18 17:05:32: google-download-read,
GOOGLE_WEB_READ_UNCLASSIFIED, UpdateAttemptUnconfirmed, then shared stop.
In this phase that typed exception originates at the existing action page guard
before/after native TSV read, not directly from menu timeout. Prior fix does not
classify a wrapper lacking confirmed timeout evidence as transient. Diagnose the
specific guard boundary before changing retry policy. Authorized for this Owner
incident: read-only local logs/config and passive canonical CDP metadata/current
owned Google page inspection if needed, using existing session only. No browser
launch/close, navigation/login, business clicks, writes, downloads, credential or
DB access for diagnosis. Keep real data out of evidence. Patch only a positively
identified recoverable read/entry fault; never bypass wrong-document/auth guards.

Passive metadata after failure contains only the original blank page; the failed
Google page is already gone. A proposed live UI probe was rejected by automatic
approval for lack of explicit live navigation/menu authorization; it was NOT run.
No indirect workaround. Continue safely with existing logs/code and offline
reproduction. Exact closed-page versus changed-fragment trigger is UNKNOWN.
Within _download, the only UpdateAttemptUnconfirmed source is _guard before/after
reading, with typed SURFACE_UNAVAILABLE/SURFACE_UNCONFIRMED. These describe a
lost read surface, not an accepted result. Rejecting that data and retrying a
fresh page is safe without weakening strict auth/document/gid/schema guards.
Unknown UPDATE_RESULT_UNCONFIRMED without temporary evidence remains a stop;
write/click/settlement errors are unchanged. Persist the exact safe surface code
in sanitized diagnostics for future differentiation, never raw exception text.

### Repeat-stop correction / final offline evidence
Treat only the two explicit lost-read-surface codes as retryable during reads,
even without an underlying timeout: discard results and physically retire the
failed page before the existing reader's one fresh-page retry. This does NOT
accept changed gid/range/closed-page data: original auth/document/gid/schema
validation remains strict. After two failures, original229 notification and
next900-second poll resume. Unknown UPDATE_RESULT_UNCONFIRMED without temporary
evidence and all write/click/settlement failures retain their previous policy.
Safe diagnostics now record the exact whitelisted surface code, not only a
generic unclassified label. No authentication or wrong-document bypass added.

144 focused PASS. Full isolated suite: **2220 passed,1 skipped,74.66s**; Ruff PASS.
Real native-action guard -> transport -> reader tests cover both2026/SHAHAB,
closed page, gid drift before/after download, range fragment change, discarded
failed data, deleted temporary downloads and fresh next attempt. Production
poller with simulated pages/mail covers two closed/gid failures, one229 notice,
no stop flag, virtual900-second next cycle recovery across both worksheets.
Wrong document, auth, unknown errors and write guard failures still stop without
read retry. Exact-code diagnostics checked through runtime sanitizer. No live
page probe/download/edit or business replay performed. Exact historical
closed-versus-fragment trigger remains UNKNOWN; the offending read-guard branch
and failure-to-defer behavior are reproduced and corrected.

Owner has confirmed exiting the GUI in response to the announced corrective
package/overwrite and idle-reopen step. Continue the existing authorized V1.4
release procedure; no automatic business start. This supersedes the previous
code-pin-only deployment scope for this narrow correction. Keep runtime/data/
credentials/Chrome/profile and rollback. CEO independent Review still required.
