# RFQ-016 execution evidence

Status: REVIEW_REQUIRED / SOURCE_ONLY / NOT_DEPLOYED.

## Protected takeover and baseline
- Original root checkout: main c3a597d, dirty/untracked unrelated work preserved.
- Reused existing V1.6 worktree: C:/Users/Leo/.codex/worktrees/v16-independent-scheduling/INSO_Leo.
- Unique local 7574516f18c8ee3225b5039f2eb4aeabd0045bbc preserved as ancestor; contains reports only relative to f8f2c32. Remote requirement be46555471cb78786437d04bf61210a3d384a74e merged without overwriting history.
- GitHub-only proxy was unavailable; fetch succeeded with command-local proxy override. No permanent Git/network configuration changed.
- Installed EXE SHA256 B51C7F66E41A6C3F6266FF772E9EEF8AEB161F986D2705B97320D67CE62B283B matches prior recorded artifact attributed to f8f2c32. Exact frozen source equivalence independently NOT_VERIFIED.
- Read-only OS process inspection found installed V1.6 running. No process stop/kill, installation, browser/CDP connection, credential lookup, configuration edit or real mail was performed. Owner elected to stop automatic business in the original program; actual completed stop NOT_VERIFIED by executor.
- No temporary handoff found. Other dirty/version worktrees retained; no new worktree created, no removal/prune needed.

## Read-only field diagnosis (aggregate only)
Production SQLite opened URI mode=ro plus PRAGMA query_only; no business rows or raw output copied into Git. Observed recipient outcomes: IMPORTANT_ORDER SENT32; DUPLICATE_ORDER SENT2; TP_RESEARCH SENT6; PURCHASE_EXCEPTION SENT133. Exception command families: runtime42, purchase-exception40, quotation16, website2, other19. Fifteen GOOGLE_READ_RETRY_EXHAUSTED commands recorded from 2026-10-18 to 2026-10-30. No pending/retryable exception recipients at inspection instant. These are observations, not a claim that every historic message was false.

## Root causes and reuse audit
- backend._defer_google_read_poll creates runtime mail even when the next normal cycle can recover. Runtime incident keys include run/cycle identifiers.
- Website/source observers emit warnings before final business completion. Direct operator SMTP bypasses durable outbox.
- V12 durable queue has no common age admission. V13 only customer-quoted rows had age gating; other automatic quote states bypassed it. TP had no calendar-month admission.
- Task center projects durable procurement history and caches DTOs; ordinary source reads did not independently update current customer status.
- Reuse existing coordinator, independent scheduler, source reader callbacks, SQLite notification commands/recipient ledger and SMTP worker. No new dependency, scheduler, database, browser or mail transport.
- Review metadata and suppression reason extend the existing outbox; SENT/UNKNOWN recipients are never reset. Existing quiesced migration owns additive upgrade. Legacy false alerts are suppressed before SMTP, not deleted.

## Red evidence
Two correctly initialized offline regressions failed before fixes: recoverable Google read warning reached fake SMTP (1 call), and a31-day-old durable queued item reached research (1 call). Initial test preparation errors were corrected before recording this business reproduction. Baseline command: python -m pytest tests/workflow/test_rfq016_regressions.py -q -p no:cacheprovider --basetemp <task-owned sandbox>. Result2FAILED in0.93s. After initial gates:2PASS in0.81s.

## Final source verification
- Full suite:3272PASS /0FAIL /1SKIP /129.68s;3273 cases. RFQ016-specific49cases PASS. Machine-readable summary and exact acceptance case names: TEST_REPORT.json.
- Existing skipped symlink test: Windows environment cannot create symlinks. This is not a product PASS and was not hidden or removed.
- Command: Python3.12.10 -X utf8 -m pytest tests -q -p no:cacheprovider --basetemp <task-owned sandbox> --tb=short --junitxml=<task-owned report>. Existing release site-packages supplied through process-local PYTHONPATH; existing frozen Tcl/Tk data supplied through process-local TCL_LIBRARY/TK_LIBRARY. No packages installed. Earlier default-environment collection errors and intermediate failing suites were repaired; only the final full run is acceptance evidence.
- Ruff all src/tests PASS; git diff --check PASS; inspected source/test diff and ancestry. Both7574516 andbe46555 remain ancestors. No unrelated root dirty work was staged.
- Actual QQSMTPTransport exercised with injected ScriptedSMTP/FakeCredentials. False, stale, recovered, invalid, expired and legacy already-SENT/UNKNOWN samples:0SMTP attempts. Confirmed manual login, native unknown write and fully qualified persistent incident:1notification at most per ongoing incident across restart. Current important-order/TP mail retained. Global test SMTP floor prevented real outbound connections.

## Material implementation decisions
- Common date admission uses original bound RFQ date first; exact immutable intake is explicitly approximate. Brief identity/date conflicts never fall back to a recent guessed date. Missing optional Brief read/schema can only fall back to that pre-existing exact ID; new undated rows are excluded without queue creation.
- V12 gates discovery, durable retries, continuation, post-Research brand write, procurement and status-write recovery. V13 all automatic statuses and revalidation before update are gated; TP discovery, existing claims/recovery, continuations and enqueue are calendar-month gated. Owner age exemption is scoped to one invocation; no automatic retry privilege is minted.
- Source projection uses original source-read observations and invalidates cached DTOs; failed reads explicitly stale. Customer status and procurement/UNKNOWN history remain separate. No database alteration or external write was used to fake customer-status synchronization.
- Distinguish pre-click timeout from possible dispatched quotation effects. A missing/unconfirmed response cannot be settled by a human-edited Sheet status. The existing hold JSON keeps a bounded native-effect marker in the already discarded quotation slot, not raw quote data; old reader regression remains compatible. Manual rerun/close cannot clear UNKNOWN; known pre-effect problems retain original manual retry capability.
- One existing outbox with additive review_json/suppression_reason and verified pre-upgrade backup. Legacy false pending alerts become auditable SUPPRESSED at dispatch, not deleted. Original SENT/UNKNOWN rows remain immutable; stable incident keys and exact legacy aliases stop restart/format-change replay. No second scheduler/database/mail system or interval workaround.
- Recipient allowlist and native/current-source review run before SMTP. Temporary loss of current source proof defers qualified business commands for the next original source read; unverified anomaly commands are suppressed. Corrupt/unavailable ledgers cannot safely provide durable deduplication or truthful delivery: business remains protected/stopped and local UI/logs remain authoritative; no bypass SMTP fallback is allowed.

## Remaining UNKNOWN / release isolation
- Installed/frozen source equivalence beyond matching recorded artifact hash, current Owner-completed stop state, real latest customer status, Google read/write availability, historical external write outcomes and real delivery after a future release remain NOT_VERIFIED. No claimed production fix.
- Existing production SENT/UNKNOWN/outbox rows were inspected read-only and not edited. A future separately authorized release must use original safe stop/drain, verified backup/migration, preserved profile/session and original account/recipients; review pending queue through this same gate. No automatic RFQ016 installation is authorized.
- No temporary handoff, extra worktree, release staging, build or helper service was created. Task-owned synthetic test sandboxes/logs are retired after retaining this bounded report; existing runtime, release/rollback, CDP, Vault, Git and unknown dirty assets are protected.


COMPUTER_USE_NOT_USED. Methods: Git, PowerShell/Python source tools, read-only OS process/hash inspection, read-only SQLite aggregate queries, synthetic tests. Production outcome remains NOT_VERIFIED; RFQ-016 install is not authorized.

## Cleanup audit
Cleanup verified each resolved absolute target under D:/Program_Leo/INSO_Leo/.tmp and inspected reparse points before removal. Known task-owned log/XML files retired. Some individually identified pytest sandbox directories reject filesystem enumeration/deletion with access denied; retained without changing ACLs, forcing locks or following links. The exact retained names are recorded in TEST_REPORT.json. No production/build/release/profile/Git or unknown paths were removed. This filesystem limitation does not affect the verified source tests.

Final completion audit found and reproduced one normal-mail lifecycle concern: a temporary final-review exception suppressed a legitimate business message permanently. The focused red regression failed1case in0.86s. It now defers without an SMTP attempt until the original source reviewer can validate it; actual stale/invalid anomaly evidence is still suppressed. No retry interval or new worker was introduced. Final full suite after this last source change:3272PASS/1SKIP in129.68s; all49 RFQ016 regressions pass.

## Completion audit before source submission
Original objective and latest Owner steering rechecked twice against implementation, native fake-SMTP evidence, complete regression, Git ancestry, pending production operations and cleanup. Authorized source work is complete and ready for CEO independent review. Pending: CEO source verdict and any separately authorized release/live business acceptance. No installation/restart/real messages or follow-on business task is scheduled or implied.

Verified source/test commit: `77a3e83f499d91242fe8012570f939b09d8c25a0`. Delivery target: `origin/codex/v1-6-independent-scheduling`. Final report and source SHA metadata are documentation-only additions after this source commit.

## 2026-10-30 CEO remediation + Owner detailed-mail extension (IN_PROGRESS)

Fetched and fast-forwarded 6c1ba7f; 7574516 and 77a3e83 remain ancestors. Existing worktree reused; root dirty main and other worktrees untouched. No live CDP/SMTP/production writes. Prior REVIEW_REQUIRED superseded by CEO CHANGES_REQUESTED. New extension tracked in tasks/2026-10-30-mail-research-upgrade.md.

A/B/C red evidence: 4 FAILED in1.26s: missing hold-before-price; stale-source alert SMTP1; completed important SMTP1 and duplicate SMTP1. First green:53 PASS3.47s. Production wiring now commits native hold before baseline; missing persistence capability keeps old baseline and delegates hold to canonical settlement. Notification availability does not authorize price advance. Fresh rows only for current incidents; previous incident proof cannot refresh an unknown source. Important/duplicate business event disallows already quoted statuses at dispatch.

Reuse inspected: ResearchContinuation/TpFx/select_tp_offers/collect_tp_offers; TP report; order_mail IMAP Vault; PageResourceAdmission/market_read_pages/ResearchMarketSession; existing V12 worker/outbox/SMTP and follow-up clock. New independent mailbox lifecycle is expressly authorized; existing TP workflow identity cannot represent email UID without forging an order, so minimum new request/cursor persistence is needed in the same DB. No second SMTP implementation.


### 2026-10-31 implementation audit (full final run pending)

All activity remains SOURCE/OFFLINE ONLY. Re-read EXE SHA256 still
B51C7F66E41A6C3F6266FF772E9EEF8AEB161F986D2705B97320D67CE62B283B;
no installed file, config, Vault, live database, process, Chrome or SMTP changed.
7574516 remains an ancestor; active worktree/dirty root/other worktrees preserved.
No agent CDP or Computer Use, no package/dependency installation.

Additional red evidence: unknown persistence BEFORE commit after dispatched native
click left no hold (1failed/4passed1.81s). Original native hold now commits before
dispatch; exact newly admitted token + native success may finish it. Five injected
crashes (before/after unknown hold, notification, before/after baseline) restart
original integrated cycle without another click, lose no UNKNOWN, send at most1.
No blind close/clear capability is exposed for historical UNKNOWN. Direct helper
without durable guard retains baseline; production always binds the native guard.

Page reuse audit found park_shared_cdp closing unmarked human/read targets. New
red regression failed1/0.92s. Parking now creates/retains a blank without global
sweeping; each creator retires its own exact target. Only corresponding old cleanup
expectations changed. Fake native CDP proves replacement under closure (max3 tries),
no foreign-page adoption/closure, local child admission isolation. Uncertain
creation/ownership persists a local block across restart, preventing accumulation.
It requires deliberate approved reconciliation, not restart-as-proof-of-recovery.

Shared detailed algorithm physically moved once to research/detailed.py; tp.py
exports compatibility only. Shared HTML moved once to research/report.py. Original
TP reports/target decisions retain compatibility. Optional TP report observer and
bounded fresh cache do not alter TP results. Standard inquiry business criteria,
3working-hour follow-up, purchaser/customer quote selection and baseline rules
are unchanged except the required crash protection. Extra market collection runs
only in the independent bounded worker, never synchronous purchase writes.

Runtime composition starts before business buttons and shuts down only on app
exit. Same configured DB/9222, Core credentials and native adapters. Startup joins
local loader, performs the original backed-up migration once before workers; main
Start verifies/reuses it rather than falsely asserting quiescence over live SMTP.
Receiver120second clock continues during research, business stop/pause/manual
priority waits. Reports awaited by SMTP count toward capacity64; complete states
exit indexed scans.24h/720poll fake-clock case verifies bounded live work and
separate per-UID identity. Tables are the minimum capability gap: existing TP rows
encode Google target-price orders and cannot represent UID identity without
forging an order. No second SMTP implementation or standalone monitor was added.

Final dispatch review runs before content preparation, then the original transport
review. SQL scopes use CASE/coalesce to preserve legacy NULL/malformed review
compatibility. End-to-end Backend + existing actual QQSMTPTransport + injected
ScriptedSMTP tests verify both business reports, closed-event suppression and
Shawn-only IMAP report delivery. No real SMTP/Vault/IMAP/Google/CDP was contacted.

First full run:3297passed/3failed/1skipped134.65s. Two failures were old TP missing-
source layout compatibility; fixed without changing target algorithm. One was
cached Tk timing1003ms versus1000ms (later standalone1021ms); standalone rerun
passed after diagnostic instrumentation, which was removed. No threshold or
product GUI behavior was relaxed. Final clean whole-suite rerun remains required.
Targeted final preflight:44passed/1deselected4.68s (24hcase separately already33
suite passed51.77s before final scan/cap refinements); Ruff all src/tests PASS.


Second full run:3318passed/1failed/1skipped183.79s; only original Tk timing
(1036.87ms) failed. Profiling then proved0.971s was Tk update/event processing,
including scrollbar/layout/selection callbacks from earlier untimed renders;
actual detail render0.102s and no durable permission/SQL calls. Test fixture now
drains prior native events and warms its display-only hint transition BEFORE
locking/timing a different detail model. Original <1000ms and no-slow-call
assertions remain. No product GUI code or response threshold was changed.
Measured lock/slow-permission updates150.460/151.048ms after isolation. All
profiling/diagnostic instrumentation removed. One final whole-suite rerun follows.

Additional bounded-lifecycle checks: pending SMTP counts toward request capacity;
terminal report states leave indexed scans; one unresolved report-delivery
incident alerts Owner once across distinct UNKNOWN reports; original outbox
SENT/UNKNOWN history is immutable. A runtime-owned native resource quarantine
persists across restart, with IMAP still receiving into bounded capacity. It is
not auto-cleared as proof that browser ownership recovered. Shared-parent resource
waits are deferred locally rather than poisoning main admission or opening targets.
Read-only catalog updates index original source identities/Brief rows instead of
performing quadratic matches on critical source callbacks. Optional catalog/cache
errors cannot prevent original source freshness/UNKNOWN projection updates.


Candidate e786af9de620395a84f2d619ae086759a6da3c1c full suite:3323passed,
1skipped185.68s. During supplementary audit a new fake-IMAP/actual-QQSMTPTransport
regression reproduced temporary [UNAVAILABLE] login response being classified as
manual authorization: fake SMTP1 where0 required. This candidate was not pushed.
Fixed by allowing only explicit [AUTHENTICATIONFAILED]/[AUTHORIZATIONFAILED]
native response codes; maintenance/rate limiting/unclassified LOGIN NO stay local.
The receiver loop now also catches local ledger/incident-enqueue failures so its
own thread cannot fail out and affect the main process. New regression requires
five temporary-login failures to produce0 SMTP attempts. Final exact patched
source full regression is required before delivery.


295fa4411b1369d5b80293ddd702d5be2de9818b full regression:3328passed,
1skipped184.76s (JUnit184.703s). Supplementary24h composed fake-CDP + fake-IMAP
+ original QQSMTPTransport with ScriptedSMTP passed:721checks,720independent
requests/reports,4338created targets including18bounded closed-page replacements,
max1owned live target,0remaining owned targets,2foreign Owner/main targets
preserved,0thread growth,0business-history changes,0technical false-alert commands,
0real network connections. Capacity/foreground priority were exercised together.

Final report-completeness audit added a red case: unmatched MPN with a full-model
native source match and canonical resolved_brand lost that already-verified brand
in the report (1failed0.84s). Preserve this narrow canonical evidence as report-only
metadata; never infer a brand from a partial/unavailable match and never write it
back to the Google order or original workflow history. Quantity remains unknown,
no technical1 appears as customer quantity or fabricated total. No TP algorithm or
original ordinary Research/purchase branding path changes. Exact final SHA and
whole-suite rerun follow this last source delta.


## Final source receipt —2026-10-31

Source `5ca59a34c796909ae432d38d787de199d9b60404`; src tree `b7ca20fcb34204b62bd6a98f5a0663946de8831d`; tests tree `4bb53b7387ff273fe91a223430cdce1701059afe`.
Final complete offline suite:3329PASS/1SKIP,184.34s console
(184.277s JUnit). 106RFQ016-associated cases PASS. The sole skip
is Windows symlink creation unavailable; no unrelated tests were disabled.
JUnit SHA256 `421a69a7d2aeb574fa2e70986db10fae592704178e6bc986ef1db20f9588d942`. All src/tests Ruff and diff
checks PASS. CLI/API only: COMPUTER_USE_NOT_USED. No installation/build/restart/
kill/CDP attach/real IMAP/real SMTP/credential/config/business-history modification.
A complete result-before-enqueue crash was additionally injected on this final
source: durable READY existed with0outbox commands; original work loop repaired
it, delivered once through injected actual QQSMTPTransport, then a second restart
sent nothing. Supplemental receipt retained compactly in TEST_REPORT.json.

A previous24h composition run on295fa44 exercised actual canonical page-lease
logic with fake CDP, fake IMAP and injected original SMTP:721polls,720distinct
requests,720reports,4338target creations with18safe replacements, max1live owned
target,0remaining owned targets,2human/main pages preserved,0thread growth,
0technical false-alert commands, no real network or original history changes.
Only report-brand metadata changed after that run; final full suite also reran
its720-poll persisted queue simulation. No live physical-browser claim is made.

A/B/C are implemented and tested; previous Executor source review blockers are
addressed for CEO independent re-review, not marked CEO-approved. The detailed
mail/IMAP child task is separately REVIEW_REQUIRED; none is declared production-
accepted. Existing browser profile, runtime DB, Vault and running EXE remain
protected. Same active worktree reused; no new worktree/handoff/dependency/runtime
helper or persistent external watcher created. Other dirty/unique worktrees were
not reset, staged or removed; worktree prune is inapplicable because none removed.
Cleanup and final push receipt follow below.


5ca59a34c796909ae432d38d787de199d9b60404 full suite passed3329/1skip184.34s.
Final date-provenance audit reproduced4failures/3passes2.40s: local intake fallback
was labelled as original inquiry date in three open-order business-mail cases,
and an aware UTC20:30intake displayed the previous date rather than Shanghai.
Propagate the existing LOCAL_INTAKE_APPROXIMATION label into business/catalog
report metadata and format aware inquiry timestamps by Shanghai calendar day.
This changes report labels only, not admission dates, source histories or trading
selection. New red→green regression plus exact final whole suite required.


e3b8cd0606e7c27d2565d3a3701961b362186225 full regression:3330PASS/1SKIP184.40s.
Supplementary synthetic quantity audit reproduced10.5being displayed as10 by an
int()cast in the new read-only catalog. Replace all new report/catalog intake
casts with the existing public sheets.tp_brief.quantity_value parser. It rejects
fractional/bool quantities rather than fabricating an integer, accepts canonical
comma/integral forms, and leaves unavailable identity as unmatched unit-price
research. Invalid latest local records must not cause an older arbitrary match.
No original workflow/trading quantity rules change. Four regression variants
cover10.5,True,1,000and10.0. Exact final source rerun follows.


## Superseding final delivery receipt

Final source `08a00cf6abacc73a4c06b7721f4dfff51fd5e373`; src tree `b229db56c486bc0afe064d3a6cf01f57bd19647e`; tests tree `05f57f1cf1b3fa8fbc7f5e274b30a2edee11d9da`.
Full suite3334PASS/1SKIP183.33s console (183.267s JUnit),111associated
RFQ016 cases PASS. Same Windows symlink skip, no test threshold relaxation or
unrelated exclusion. JUnit SHA256 `4af86bf70c0391c0756a9c65bd1f1ab43911bc36152a091e80c1c5a3f5c60c4c`.
This supersedes earlier candidate receipts as the submitted source identity.
Source and tests are unchanged after this run. Raw test sandboxes/XML are retired
after compact receipt extraction; TEST_REPORT.json retains exact case IDs,
source/test trees, results, hashes, red evidence and separately attributed24h/
crash acceptance. Only documentation/evidence changes follow this source commit.
No live production action or Computer Use. No automatic installation authorization.

Final cleanup receipt: retired 9 explicitly named additional task-owned temporary items; retained 0. First pass retired35. Compact metrics/hashes retained in TEST_REPORT.json. No reparse traversal, permission changes, production assets or prior-task exceptions touched. Source08a00cf unchanged; documentation-only handoff.
Final read-only recheck: initial Ruff default cache write was denied by workspace sandbox (no code finding); reran python -m ruff check --no-cache src tests: PASS. git diff --check: PASS. Source/test trees still match final receipt; preserved7574516 ancestor verified.


## CEO second review50dfe3d — D/E/sender remediation (2026-10-31)
IN_PROGRESS / NOT_DEPLOYED. Prior delivery receipt is SUPERSEDED for current source approval only; prior A/B/C and age/status/UNKNOWN protections remain accepted baselines and were not rewritten. Reused same active worktree, native collectors/market_read_pages, original source reader, original request JSON/outbox/worker/QQSMTPTransport. No new dependencies, browser/profile/port, scheduler, table or sending system. No takeover/handoff was required. Preserved7574516 history; no production assets/credentials/live services accessed. COMPUTER_USE_NOT_USED.

Baseline: fast-forwarded clean worktree from e296564 to CEO50dfe3d981bddc4c5a61865123f590d16b68f1cc. REVIEW.md does not exist; canonical review is the final section of TASK_SPEC.md plus subtask audit. Read these and module boundaries. Red run on unchanged application source:7FAIL/1.74s (2cached-customer assertions,2background-first250ms assertions,3forged exact From/provider-header assertions). JUnit stored temporarily as rfq016-second-red.xml; compact receipt will retain hash before cleanup.

D: Removed history preload as current-source proof. Catalog requires explicitly configured full worksheet universe, every successful non-discovery full A1:G live read begun after local request receipt, age0..120seconds. Uses read start rather than completion time so a long failed/stale read cannot look new. Failed/discovery/partial reads cannot certify latest; restart/configuration clears evidence. Original source reader owns this optional readonly observation; no additional Google connection, no independent source poll or main Start dependency added. Missing/ambiguous/stale/unknown source returns MPN-only, including restored progress. Fresh complete unambiguous view restores enrichment. At actual SMTP preparation, expired/changed latest proof strips cached customer/brand/count/date/total and renders confirmed market unit quotes through the same renderer; quote capture dates remain truthful. No source/market I/O on sending path. Original business notices do not use this independent matching gate.

E: Foreground never acquires background's whole-read lock. Its own reentrant foreground serialization is retained. At most one background read can be in flight; a foreground generation invalidates that background lease even after foreground completes. Background checks before read/new owned target/recovery and after read; stale result is deferred without checkpoint/source-success/SMTP/attempt increment. Safe cleanup still uses exact native target on owner thread. Already in-flight sync I/O may drain while main proceeds; no cross-thread page close/Playwright call, timeout-kill, Chrome reset or extra client/thread is introduced. Tests measure original foreground decorator progress within250ms while background is deliberately held by Event; this is an offline admission bound, not an OS/physical shared-Chrome performance guarantee. A forever-hung provider can retain one read/target until native timeout; main/IMAP continue, no replacement accumulation. Physical Chrome/CPU/network contention and actual latency remain NOT_VERIFIED.

Sender: parser remains syntax-only. New provider verification boundary defaults to false (NO production verifier/override/risk acceptance). It is not represented as real sender authentication. Exact From plus arbitrary Authentication-Results/Received-SPF/Return-Path is rejected before queue admission. Local SENDER_AUTH_UNVERIFIED keeps UID cursor, continues120s polling, emits no technical email. Persisted old unverified tasks are blocked/suppressed without market or SMTP, SENT/UNKNOWN protections unchanged. Synthetic verified fixtures explicitly inject proof; they do not constitute a QQ implementation. This intentionally leaves live IMAP-command execution SECURITY_ENABLEMENT_BLOCKED until a reviewed trusted provider contract or explicit narrowly scoped Owner risk acceptance; original important/follow-up/TP mails remain functional.

Intermediate checks: initial focused run57PASS/2FAIL57.28s exposed test-helper wiring and removed baseline initialization; restored original WorkflowStateStore initialization and corrected synthetic helper call. Expanded run16PASS/1FAIL2.82s exposed fake discovery capability wiring, corrected fake service (production get_discovery contract unchanged). Follow-up42PASS2.62s; combined84PASS58.87s. No production connection or credential reading. Ruff no-cache PASS and git diff check PASS. Final source/full regression follows.


First immutable remediation source8526523c7dfaee55bd132b5690eed20dce5ee4e9: final focus24PASS/2.39s; full3352PASS/1SKIP192.04s. Additional sender-boundary check reproduced an actual local regression: two auth rejections, then successful login/header read with unknown sender, then one rejection incorrectly retained3auth failures (1FAIL/1.03s). The successful read now resets/locally resolves the old auth incident even though sender execution remains blocked. No sender acceptance or mail recipient policy change. This source is superseded by the following small correction and final full rerun.

Final source `71f3e06301d3a62ac8a22b2510163f85b19437d2`; src tree `2bb1a4153faf4a5add95471daa7b118da5266738`; test tree `41be687c133a0e1e237db53bbfd7b184f53da3f5`. Final targeted30PASS3.32s; final full3353PASS/1SKIP191.39s (symlink creation unavailable). JUnit SHA256 `9d8a81f460a9d148435cddd1ccbfac562d399b804d5371444373abc7a5ab9490`; case IDs SHA256 `4538afe0fd788f1b8999112435c3866fe84c319e954ef526f4c3d6d4c065996b`.19new review cases passed. Original protected source blobs unchanged as enumerated in TEST_REPORT.json; whole prior regression retained. Source/test working diff empty. Ruff --no-cache PASS, git diff --check PASS,7574516 ancestor retained, remote50dfe3d unchanged. Original public domain docs only; no live account/Google/Chrome/SMTP operation. Sender authenticity remains explicitly unimplemented/blocked for real commands, not mislabelled PASS; legitimate business mail paths still pass. Authorized source work complete; physical/live verification, risk acceptance and installation remain unauthorized/NOT_VERIFIED. Cleanup and final push follow.

Second-review cleanup: retired 20 explicitly named owned test directories/XML files; retained 0. Checked absolute containment and every subtree for reparse points before native PowerShell deletion; no permission changes, protected runtime, browser/profile, Git, credentials, unknown dirty assets or prior-task exceptions touched. Compact run statistics/case IDs/hashes retained in TEST_REPORT.json. No processes/tests remain running.


Receipt-time edge found in final D audit: poll_once previously captured now before TLS/login/header FETCH. A source observation during a slow connection could predate actual request receipt yet pass the post-request test. Deterministic T0poll/T1source/T5external-new-row/T10header-receipt regression failed1case/1.12s on71f3e06. Request created_at now uses clock AFTER successful header read, before the existing atomic accept_scan; all proof comparisons retain that actual local receipt bound. No schema/new clock/scheduler or main path change.71f3e06 full3353PASS/1SKIP191.39s remains historical evidence, superseded for final source; final focused/full rerun follows. Prior20owned temp items retired with0retained; new final run has separate owned names.

Superseding final source receipt: `1dd31b283ec34126637e173830dbc3c321b7c89d`; src tree `593bde76eb764b4e3ccb39e625800d07c7166704`; test tree `3f5bab1ebd34fb543b8b6d39f967657bc011662a`. Final targeted31PASS/3.17s; full3354PASS/1SKIP199.89s;20new cases pass. JUnit SHA256 `b89118d5f9beb11e4f0ee1c4cd4170fd659787b2a9ac9fbe107a14202ab0ba64`; case IDs SHA256 `d053feb2c712db47bc20177270efc7757ddfe6e8ddf0ceba2b4b8601121dee1d`. The older71f3e06 receipt above is SUPERSEDED; its statistics/hashes remain historical evidence. No src/tests changes after this run. Final report and original Task Spec/subtask updated to exact current source. Sender enablement remains explicitly blocked; no live test/production installation authorized. Final owned cleanup/push follows.

Final second-review cleanup: retired 6 additional explicitly named owned temporary test items; retained 0. First pass20retired/0retained. No reparse traversal, permission changes or production/unknown assets touched. Final source/test trees unchanged; no test processes pending. Authorized implementation/evidence work complete, live provider verification/physical overlap/SMTP/install remain NOT_VERIFIED and unauthorized. Next Owner action: Review RFQ-016.


## CEO third-review F-only remediation (2026-10-31)
IN_PROGRESS / NOT_DEPLOYED; prior delivery is SUPERSEDED for current approval. Clean active worktree reused; fast-forwarded0f33b97 to8a0d121cbb722a9a981e64fa6380904dac5ca12e. Read latest Task Spec/source review, subtask, module contracts, Backend startup/preparer/final reviewer, canonical important/follow-up producers, V12 worker/store/SMTP, existing business-report tests. A/B/C/D/E and QQ security hold are accepted baselines, not redesign targets. No handoff/new worktree/dependencies/production access.

Reuse audit: original NotificationCommand.created_at is already durable and never refreshed by recipient defer/restart. Original worker already rechecks source/event/recipient before content and only dispatches pending recipients. Original preparation supports cached/READY six-source data; original renderers/algorithms and shared-CDP budget need no changes. Sole implementation patch is launcher/mail_research_composition.py preparation/fallback: wait at most120s from original notice creation (existing mail polling budget), then at the next eligible ordinary send opportunity render verified order summary plus explicit detailed-data-unavailable note. No new timer, loop, table, outbox, scheduler, browser or SMTP. Full valid detailed content wins even after deadline. No source/market call or blocking sleep in preparation. Missing source/identity/current state still cannot send; expiry is not an authorization bypass.

Fallback uses freshly bound customer/model/brand/count/date, original follow-up confirmed timestamp, and original business purpose. Historical market price/stock/estimated totals are not copied; fallback is plain escaped text/HTML, not another price algorithm/template. Optional startup failure, persisted local quarantine, ineligibility, full queue, stale/malformed result or preparation exception cannot reset the wait. Exceptions stay sanitized local warnings, not technical mail. Original subject, recipients, final review, SENT/UNKNOWN, event/age and main business paths remain unchanged. QQ real sender verifier remains false/SECURITY_ENABLEMENT_BLOCKED.

Red at8a0d121 application source:10FAIL2.46s, actual Backend final reviewer+preparer+V12 outbox+QQSMTPTransport injected fake SMTP; two original notice types across build/start exception, persistent quarantine, ineligibility and optional cache exception all remained0SMTP after120s when2required. First green10PASS3.95s. Expanded30PASS8.38s; static check identified only unused synthetic fixture variable and Decimal literal style, corrected without changing assertions. Final matrix/rerun follows. All data synthetic; no real socket/Vault/Google/CDP/SMTP operation. COMPUTER_USE_NOT_USED.

Focused integration (37new F cases plus existing mail/composition tests):80PASS68.18s. Added explicit fake-successful Backend service startup before persisted resource quarantine, and two non-target notification preparation guards; no source behavior expansion. Source diff inspected: only original mail_research_composition.py content preparation/120s fallback changed. No prior Backend reviewer, A/B/C/D/E, resource ownership, sender verifier, queue, SMTP or main business path changed. Final source receipt/full regression follows.

Immutable F source55ba0f230ce4a42eeda78d4aa942e9065bfc4ba3; src tree555f1ddf94cd9cb3cbec3643976ba25ff9f4444c; tests tree49c68dafc92ec8586a118edd46fccca009347bf6. Final targeted39PASS11.79s, Ruff all src/tests --no-cache PASS, staged diff check PASS. Full suite now executing on this exact source with reused release venv/Tcl/Tk, no installation. No source/test changes will be made while verifying this candidate. Branch target remains codex/v1-6-independent-scheduling; same existing worktree used,7574516 history retained.

Final F receipt: source `55ba0f230ce4a42eeda78d4aa942e9065bfc4ba3`, src tree `555f1ddf94cd9cb3cbec3643976ba25ff9f4444c`, tests tree `49c68dafc92ec8586a118edd46fccca009347bf6`.39targetedPASS11.79s; full3393PASS/1SKIP211.28s. JUnit SHA256 `3b70d51a1b26c20f47294197b76e46479e467412435c9dc4eec730b0613e64a5`; case IDs SHA256 `43cd10b07cc92a1eb8b0471443063ab61356a9ce5b5825adfff996a701732757`. Original3354test files unchanged; only new39case file added. Only source path changed is launcher/mail_research_composition.py; its startup/append functions unchanged by AST comparison; all other source blobs unchanged from CEO8a0d121. No src/tests working diff. Ruff all --no-cache and git diff check PASS. All authorized implementation/test work complete; original reports updated. No production/Chrome/mail/credential action; live validation and deployment remain unauthorized/NOT_VERIFIED. Final owned cleanup and push follow.

F cleanup: retired 12 explicitly named owned temporary directories/XML files, retained 0. Absolute containment and subtree reparse checks completed before native PowerShell removal; no ACL changes, reparse traversal, protected runtime/profile/CDP/Git/credentials or unknown assets touched. Prior-task exceptions not revisited. Compact run/case/hash evidence retained. No pending tests or operations. Next Owner action Review RFQ-016; NOT_DEPLOYED; QQ SECURITY_ENABLEMENT_BLOCKED.
