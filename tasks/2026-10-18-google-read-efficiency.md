# Bounded discovery reads and five-attempt Google recovery

status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-18

## Owner scope / reuse audit
Reduce repeated full TSV downloads within a poll; ordinary recoverable reads
must fail five attempts before the existing 229 notification / next-poll defer.
Reuse GoogleSheetsRowReader, native GoogleSheetsWebService, existing page pool,
quotation source checks and outbox. No alternate reader, API/OAuth or state DB.
No packaging/deployment or real business writes are authorized in this task.
Passive installed-log inspection only; no CDP navigation, credentials or runtime
changes. Preserve all unrelated dirty work and current installed EXE.

## Evidence / diagnosis
Installed sanitized log at 17:33 on 2026-10-18 shows a rejected read surface,
then later quotation progress (recovery worked). At 17:37 two reads failed at
sheet readiness / surface validation; existing retry exhausted and notified.
At 17:57 a new poll progressed again. This is not evidence of authorization
expiry or a permanent stop. Exact cause of surface drift remains UNKNOWN.
Source confirms repeated default-gid reloads and per-candidate full downloads.

## Requirements / acceptance
- Poll-local, thread-local discovery snapshots: dashboard/inquiry share one
  source scan per sheet; quotation starts with new snapshots for both sheets.
  Read-only quote searches reuse that stage snapshot. No stale data crosses a
  poll, stage reset, manual worker or thread. Failed reads are never cached.
- Actual brand/status/quote writes, baseline commits and hold reconciliation
  retain fresh source identity/status checks and verified server readback.
- Keep direct quote-input navigation strict. Web transport may reuse a proven
  same-document safe page, then explicitly select/verify the target worksheet.
- Recoverable read failure: five attempts total, bounded interruptible backoff
  in production, existing once-per-cycle notification after exhaustion, next
  normal 15-minute poll retries. Auth/security/schema/unknown errors stop at once.
- Focused synthetic tests, actual offline poll orchestration, necessary full
  offline suite with CDP/network/browser launch and close isolated. No live writes.
- Update this evidence, inspect sensitive information/diff, normal push to the
  existing V1.4 branch; REVIEW_REQUIRED. Clean own test artifacts in this task.

## Implementation / verification
Reused the existing reader with immutable, ContextVar-bounded discovery rows.
Only discovery queries opt in; ordinary read_rows never returns cached data.
Successful mandatory live checks refresh discovery; failed checks invalidate it.
Backend owns the poll scope; CombinedCycle clears it before quotation. Follow-up
and hold reconciliation remain fresh, seeding subsequent quotation discovery.
Unchanged/higher procurement prices skip without another scan or side effect;
initial baseline commits and actual lower/zero-to-positive updates still use
the original live source binding/status checks. No business price rule changed.

Web range operations now retain a verified safe same-document page and select /
prove the requested worksheet, avoiding the previous redundant gid=0 reload.
Direct quote-input navigation and every auth/document/gid/ownership/settlement
guard remain unchanged. No cache or downloaded attachment survives the poll.

Recoverable source reads now make five attempts total. Production uses the
existing stop event for bounded 2/4/6/8-second backoff; stopping cancels further
attempts and does not send an exhaustion alert. Known transient read failures
reject their data and retire the page before re-entry. Auth/security/schema and
unknown failures still stop immediately. Existing outbox/dedup, once-per-cycle
notice and next-900-second poll behavior are reused; mail now says five failures.
No retry of uncertain writes or repeated script clicks was introduced.

Focused synthetic suite: initial **459 PASS, 2 fixture failures**, corrected the
new test's Owner blank-page accounting and missing result argument; **108 PASS**.
First full suite: **2229 PASS, 1 skipped, 1 test-double signature failure** in an
existing pending-count test; its stub now accepts the optional discovery keyword.
Final focused (including stage-change / fifth-attempt real-guard checks):
**88 PASS, 3.50s**. Final full offline: **2234 PASS, 1 skipped, 93.44s**. Ruff PASS.

Evidence is in committed tests:
- tests/launcher/test_google_web.py: 24 query-only candidates across 2026/SHAHAB
  require four downloads total including dashboard/inquiry discovery; native
  worksheet proof precedes every read, repeated reads cause just one navigation.
  Stage reset sees inquiry changes on both sheets. Actual live source checks
  reject changed quantity on either sheet despite cached discovery.
- Same file: actual backend poll loop, real read guards + simulated grid/outbox,
  five consecutive transient failures produce exactly one 229 notice; virtual
  next poll reads both sheets and recovers (four downloads); no permanent stop.
  Four failures then fifth success recovers; fifth authentication failure stops
  with the verification page retained. Existing security/unsafe-page tests pass.
- tests/sheets/test_google_reader.py: five attempts, exact backoff, stop
  cancellation, immutable snapshots, phase/poll/thread isolation, invalidation
  on failed live read, no unknown/auth retry.
- tests/workflow/test_v13_price_refresh.py: unchanged price skips all source /
  write/baseline effects; first baseline and lower prices require live checks.

All tests ran with production network / CDP connection / browser launch and
Browser.close blocked. Only local synthetic fixture resources were permitted.
No production business writes, credentials, SMTP, CDP navigation or packaging.
Installed EXE remains SHA256
2b691bf25f918958c670e10cf6b54001e4106a26502266e11e7cff2245407925.
Live performance and elimination of all external Google/network failures remain
UNKNOWN; root of the observed surface drift cannot be established from the
sanitized historical log alone. No claim of deployed/live acceptance.

Task-owned test runner/copies/logs are retired after verification in this same
task. Keep this packet, module contract and targeted tests as minimal evidence.
Publication preserves local HEAD/index and all unrelated dirty work through an
isolated index based on the synchronized remote branch. No reset/force push.

Owner later authorized release and explicit inquiry start on 2026-10-19. This
discovery/five-attempt change is included with the follow-up native-write and
lost-export corrections in source fe6f9767ec6bf091d4cd249232e8222e945b3a46.
Installed/start/cleanup receipt: 2026-10-19-purchase-status-web-repair.md.
