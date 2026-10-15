# Owner increment: pending status, tray close and site retries

status: REVIEW_REQUIRED
created: 2026-10-15
owner: Codex

## authority / boundaries
Owner requests diagnosing many pale-yellow pending-Sheets statuses, checking all
research-site login retries and notifying only after three retries still fail.
Owner confirms window X means hide to system tray/remove taskbar entry while
business continues; only tray Exit performs existing graceful application exit.
Inspect existing source/tests and scoped read-only installed runtime metadata,
pending-state counts and matching current Google source statuses via existing
cached read-only grant if needed. No raw customer/model/price/mail output in Git.
No live Sheets/DB writes, SMTP, business replay, credential changes, CDP attach,
browser navigation, package or deployment. No new dependency; preserve dirty work.

## reuse / plan
Reuse PurchaseCompletionActions/source-status identity checks and current GUI
projection; distinguish real pending writes from stale local state, never hide a
real failure or resend procurement. Reuse existing source_query and site login
sweep/recipes, stop-aware waits and outbox; add initial+three bounded retries for
transient login/read failures before source failure observation/mail. Preserve
manual security-challenge and rejected/missing-credential safeguards.
Reuse GUI event queue and existing graceful close for tray commands; implement
only missing native tray capability with standard-library Windows APIs.

## acceptance
Evidence-based explanation of pending rows; read-only confirmed advanced status
can settle safely without writes/replay. Window close hides with active tray,
restore returns window, Exit drains workers and removes icon. Site retry coverage
includes all research sources, recovers without premature mail, interrupts on
stop, preserves human verification and no empty-result retry. Focused/full offline
tests, scoped Ruff/diff, retire only known disposable test artifacts; REVIEW_REQUIRED.

## Findings / implementation
Read-only production metadata: 7 pending-status inquiries, all purchase outcomes
SAVED. Existing status-write notification history:8 SheetRecordConflict and1
GoogleSheetsAuthorizationError (history counts, not7 new failures). Scoped source
read confirmed all7 matching model/quantity/importance rows are now 已报价给客户.
No model/customer/price/body or raw row persisted. Initial sandbox grant-unprotect
failed; authorized read-only context succeeded, no cache/token writes or new consent.

Root cause: purchase-status satisfaction recognized only 发给采购 / 采购已报价;
later approved statuses could not settle the durable local warning. Extended only
the read-only completed-status whitelist, preserving unique snapshot/brand checks,
pending-row holds and unknown-submit safeguards. No live ledger repair was run.

New gui/tray.py supplies the missing native icon/menu/window message loop using
ctypes only. GUI X hides only after successful icon setup; restore/exit commands
travel through the existing Tk main-thread queue. Exit reuses the old drain and
shutdown; icon/window/thread cleanup handles normal exit and initialization errors.
Stock application icon; custom branding is not required for this functional fix.

Site retry audit: old source_query retried CDP failures only; login sweep attempted
each site once; INSO query called failure observer before exhausting its existing
retry loop. Added shared closed retry classification and bounded2/5/10-second
interruptible waits for ICNET/Findchips/HQEW/LCSC/Bom.Ai. INSO retains original
initial+three120-second read retries without nested login retries or premature
transient-failure observation. Genuine no-match/no-price and FX remain unchanged.
Manual challenges and known missing/rejected credentials remain immediate.

## Verification and limitations
Scoped GUI/site/status/resilience:268 passed in20.00s. Full safe/offline suite:
1949 passed /1 skipped in97.66s. Final icon resource-cleanup hardening followed
the full run; final native smoke created/destroyed two self-owned test icons,
windows and message threads successfully. No actual installed GUI was operated.
All selected Python Ruff and diff checks pass. Initial focused run had a missing
parent basetemp (79 passes/51 fixture errors); parent creation fixed the test
environment and all scoped cases passed; no product failures hidden or disabled.

No package/deploy or real source/DB writes, SMTP, order replay or CDP attachment.
Installed behavior is unchanged until separately authorized packaging/overwrite.
Live tray menu clicks, actual installed-GUI taskbar hiding, real transient login
recovery, and all7 original brand/identity proofs at next deployed poll remain
unverified. Do not claim every historical yellow warning is already cleared.

Task-owned focused/focused-final/scoped/full basetemps are absent or retired;
no frozen build/staging generated, rollback/unknown prior artifacts retained.
Publication is limited to6 source modules,4 corresponding test files, the product
fact update and this record. Parent is the latest CEO review commit ec2c0cb, whose
review of the preceding increment is preserved. Existing isolated-index publication
keeps local dirty work/index/HEAD intact and uses the same remote V1.4 branch.


## CEO independent review — 2026-10-15

**CHANGES_REQUESTED; not authorized to package or overwrite V1.4.** Reviewed
the exact `98d7734` patch, current implementation and scoped test cases.
No code changed, no browser/production operation performed. Executor reports
1949 passed / 1 skipped; CEO did not rerun tests.

- **Blocking:** `src/core/site_retry.py:retryable_site_failure` defaults to
  retrying *every* reason not in its short denylist. The existing
  `src/launcher/site_login_sweep.py` classifies `LOGIN_REQUIRED` and
  `AUTHENTICATION_REQUIRED` as `NO_CREDENTIAL`, yet both are currently
  retried up to four attempts; `AUTHENTICATED_SHELL_UNAVAILABLE` and
  unrecognized/no-code exceptions also retry. This breaches the required
  immediate human/authorization stop, particularly for the included INSO
  sign-in sweep. Replace with a narrowly justified transient allowlist or
  equivalent exhaustive typed classification that fails closed.
- Add direct regression cases for `LOGIN_REQUIRED`,
  `AUTHENTICATION_REQUIRED`, `AUTHENTICATED_SHELL_UNAVAILABLE`, and
  unknown/no-code exceptions on both source-read and login-sweep paths;
  verify no repeated login, no premature mail for genuinely transient
  failures, and preserve the existing INSO budget.
- Pending-Sheets advanced-state read-only settlement and tray lifecycle
  architecture are provisionally acceptable based on source/tests, but
  native tray menu clicks, installed GUI taskbar behavior and actual site
  recovery remain unverified; avoid claiming live PASS.

**Next:** Executor fixes the single retry-classification boundary in the
same workstream, reruns focused/full safe offline checks, updates this
evidence and returns for independent CEO re-review. Protect deployed
V1.4, CDP, runtime, secrets and existing local changes; do not build/deploy.

## Executor response to CEO review — 2026-10-15

Status: REVIEW_REQUIRED; original CHANGES_REQUESTED remains the historical CEO
verdict above. This response does not claim independent PASS or release permission.
Scope is only the retry-classification blocker; tray and pending-status code are
unchanged. No package, executable, production CDP, credentials, runtime or business
data was accessed in this repair task.

Replaced the retry-by-default denylist with exact transient adapter codes:
BROWSER_TIMEOUT, LOGIN_PAGE_UNAVAILABLE, LOGIN_NOT_CONFIRMED,
RESULT_NAVIGATION_FAILED, SEARCH_NAVIGATION_FAILED, PRODUCT_NAVIGATION_FAILED.
These come from existing browser/load/navigation/readiness paths. The existing
LOGIN_NOT_CONFIRMED recipe checks rejection/challenge first; it is not a catch-all
authorization result. HTTP_REQUEST_FAILED, LOGIN_NOT_READY, SOURCE_UNAVAILABLE,
unknown/missing/non-string codes and unclassified exceptions fail closed.
LOGIN_REQUIRED, AUTHENTICATION_REQUIRED and AUTHENTICATED_SHELL_UNAVAILABLE
never repeat login in either the five-source wrapper or any of six sign-in steps.
The sweep passes an actual missing reason to the classifier without fabricating
a generic retry reason. No login recipes, credentials or submission actions changed.

Compatibility correction at the existing INSO observer: only login/security
results enter immediate auth-stop handling there. Generic INSO read-query
SOURCE_UNAVAILABLE remains under its existing initial+three120-second budget,
without new nested login retries or premature notifications. Typed authorization
stops still propagate before reset/wait. This is necessary because making the
shared classifier closed would otherwise send generic INSO read failures to its
auth observer before the existing query budget completed.

Tests cover the closed allowlist, named auth reasons, missing/generic/unknown
reasons, no-code exceptions across all5 source paths and all6 sign-in steps,
fourth-attempt transient recovery without intermediate failure notification,
stop interruption, INSO auth-before-reset and preserved generic INSO query budget.
Focused258 passed in4.68s; selected Ruff/diff passed. Full offline result and cleanup
are recorded below once completed. Changed files limited to core/site_retry.py,
launcher/backend.py, launcher/site_login_sweep.py, the corresponding existing
launcher test file and this original evidence record.

Final verification: full safe/offline2083 passed /1 skipped in77.40s; focused258
passed; Ruff and diff PASS. No real browser/site/security/login acceptance was run.
The full basetemp was retired after absolute-path and reparse checks. The two
task-owned focused basetemps failed enumeration with UnauthorizedAccessException;
retained specifically for that proven access risk without permission changes or
forced deletion. No frozen build/staging was generated. No temporary artifact is
selected for publication. Parent review675308ec4794dcbeda9e45324d037cf986899877
and the original CEO comments above are preserved. Scope is5 files only; source
tray/status files and all other pre-existing local changes remain untouched.


## CEO second independent review — 2026-10-15

**CHANGES_REQUESTED (one narrow INSO observer defect; do not package yet).**
Review of `675308e..e501d84` confirms the shared site-retry allowlist
now fails closed, five-site and sweep tests cover the prior blocker, and
tray/pending-state sources were not touched.

**Actual source-path mismatch:** `src/research/inso_history.py` emits
`AUTHENTICATED_READ_UNAVAILABLE` (transient read exception),
`AUTHENTICATED_READ_EMPTY`, and `AUTHENTICATED_SESSION_REQUIRED`
(explicit `isLogin=false`). `src/launcher/backend.py` `_run_inso_query`
calls `_observe_source_failure` early whenever the code contains
`AUTHENTIC`; the observer can notify for transient authenticated-read
failures **before the INSO query budget finishes**, but its different
`AUTHENTICATION` check does not stop `AUTHENTICATED_SESSION_REQUIRED`.
Existing authorization tests mock the observer to raise, masking this
mismatch.

**Single surgical fix requested:** use explicit, consistent INSO
authentication/security codes for immediate stop; leave known authenticated
read/transient failures under the original initial+three120-second query
budget with at most the final observer notification. Cover both paths with
tests using the real observer behavior (fake ledger/outbox, no live service),
rather than only an observer monkeypatch. Preserve existing approved
`LOGIN_REQUIRED`, `AUTHENTICATION_REQUIRED`, missing-credential and
manual-verification stops; no packaging, CDP, production writes or unrelated
cleanup. All other parts provisionally pass static review.

**Evidence:** GitHub source/diff and Executor offline report (2083 pass,
1 skip); CEO did not independently run tests or live business verification.

## Executor response to CEO second review — 2026-10-15

Status: REVIEW_REQUIRED. The second CEO CHANGES_REQUESTED verdict above is
preserved; no independent PASS or release permission is claimed. The prior
Executor's substring-based INSO classification claim is SUPERSEDED by this fix.

Reuse: retained workflow/inso_query.py's initial+three120-second query budget,
existing source adapter, actual source observer/manual-stop handling and existing
deduplicated notification queue. Only launcher/backend.py, the existing
tests/launcher/test_site_retries.py and this original evidence record change
relative to review parent1329ca5cf975feb59e71acc7e3808309d0a79310.

INSO query and observer now share exact authentication/security stop codes.
AUTHENTICATED_SESSION_REQUIRED, LOGIN_REQUIRED, AUTHENTICATION_REQUIRED,
AUTHORIZATION_REQUIRED, AUTHENTICATED_SHELL_UNAVAILABLE, missing/rejected
credentials, invalid session/lease and explicit human-verification codes stop
before tab reset, wait or another login/read attempt. Typed InsoAuthenticationError
also propagates immediately. These results use the existing authentication mail
category, including the previously missed AUTHENTICATED_SESSION_REQUIRED.
AUTHENTICATED_READ_UNAVAILABLE, AUTHENTICATED_READ_EMPTY and ordinary response
read failures are observed only on exhausted query retries, once at the final
boundary. Recovery and stop interruption do not produce intermediate failure
notifications. Existing FX/no-price handling and query reset/delay budget remain.

Regression uses real InsoHistoryAdapter failure results, real backend source
observer, real manual-stop behavior and real notification formatter against an
in-memory deduplicating outbox. No observer-to-raise mock is used in the replaced
auth regression. Cases cover17 explicit auth/security codes, read recovery on
attempt2/4, exhaustion across4 real adapter read codes, typed auth propagation
and stop interruption. Assertions check queue silence at every read/reset/wait,
one final mail on exhaustion, authentication classification, immediate global
stop and no auth-page reset/reopen. Focused298 passed in4.47s; scoped Ruff and
whitespace checks passed.

Validation caveat / incident: the first full collection with the system test
interpreter lacked existing release tzdata/PDF dependencies (11 collection
errors). After adding the existing release-library path, full execution returned
2110 passed /1 failed /1 skipped in79.41s. The failure was the unchanged
test_cdp_launches_only_explicit_existing_profile_and_closes_owned: its fake
process cleanup still calls real localhost9222 HTTP/WebSocket code when the
release websocket library is available. The fake process was not terminated;
source inspection shows this can follow a real Browser.close send path. This
was an unintended validation isolation failure; the current production-session
state is UNKNOWN and was not inspected or recovered. Owner was informed. Do not
interpret this run as proof of no CDP contact. No real order, Sheets write, SMTP,
Vault/runtime read, packaging or EXE replacement was intentionally performed.

Subsequent full regression blocks socket connections before suite import:
external and pre-existing local endpoints (explicitly9222) are refused; only
ephemeral listeners bound by the test process are allowed. This is a temporary
execution harness, not a change to CDP/product/test-suite modules. The pre-existing
test isolation defect is recorded for CEO; it is outside this surgical source
repair scope. Five-site allowlist, login sweep, tray/pending and browser bootstrap
files were compared to the reviewed remote base and remain unchanged.

Final guarded full result:2111 passed /1 skipped in76.85s. No live authentication,
real query recovery or business acceptance was verified. Focused298 passed;
selected Ruff/whitespace PASS. Both full-run temporary directories were retired
after absolute-path/reparse checks. The task-owned focused and focused-final
directories could not be enumerated (UnauthorizedAccessException) and remain
specifically retained; no permission changes, forced deletion or unknown cleanup.
No build/staging was generated; no temporary harness, output or log is published.

Publication uses the existing isolated-index procedure on the reviewed remote
parent, selecting exactly the above3 files; it preserves the older local HEAD,
actual index and unrelated dirty work. No reset, force push, replacement branch
or duplicate report. Scope/sensitive-content review contains only synthetic
test data and technical evidence, not credentials, raw mail, customer records,
attachments or production databases. CEO next action: independent re-review of
this INSO observer correction, with the validation caveat above retained.


## CEO third independent review — 2026-10-15

**INSO code REVIEW PASS; RELEASE HOLD (separate pre-existing CDP isolation defect).**
Reviewer checked `1329ca5..9655b40` directly. INSO auth/security outcomes
now use explicit codes for immediate stop. Authenticated read failure uses
existing 1+3 query budget, with no intermediate failure notification and
final observation on exhaustion. Added tests exercise actual observer,
manual-stop path, adapter error classification and an in-memory outbox.
Executor reports 298 focused and 2111 guarded full passing (1 skipped);
CEO did not independently run the local suite or live business.

**Release blocker—credible production-session interference during tests:**
`tests/launcher/test_release_infrastructure.py::
test_cdp_launches_only_explicit_existing_profile_and_closes_owned`
constructs a fake process but calls real `handle.close()` with
`http://127.0.0.1:9222`. `src/launcher/browser_bootstrap.py:
_close_owned_process` may resolve that real port's `/json/version` and
send `Browser.close` via WebSocket **without proving the endpoint belongs
to the owned Popen process**. The first full test did exercise this path,
failed its fake-process assertion, and may have affected real Chrome.
Actual production Chrome/CDP/session state is **UNKNOWN**, not verified
untouched or confirmed closed. A guarded rerun cannot retroactively
prove the earlier attempt harmless.

**Disposition:** No INSO business-code rework requested. Before any more
non-isolated full tests or packaging/deploy, harden this **specific**
test/owned-close seam permanently: never send `Browser.close` to a
pre-existing/unverified CDP endpoint; restrict any owned process shutdown
to proven-owned process identity and mock the close/network path in tests.
Add an explicit guard regression confirming no network I/O to 9222,
no existing Chrome shutdown and only fake-owned cleanup. Re-run only
isolated/offline tests. Separately perform **passive, read-only** OS/process
and listening-port checks on current Chrome/CDP, without attaching a CDP
client, opening browser tabs, restarting Chrome, manipulating profiles,
credentials, runtime or business. If continuity cannot be proven,
retain UNKNOWN and report for recovery planning, not an automatic fix.

Keep existing V1.4 installed version and rollback untouched, do not
package/overwrite until isolated-test fix and passive operational
preflight are reviewed. No live orders or Google writes. This is a
separate safety gate, not another INSO retry revision.


## Executor response to CEO third review — 2026-10-15

Status: REVIEW_REQUIRED; INSO business-code REVIEW PASS and RELEASE HOLD above
remain the CEO verdict. No business-code revision, packaging, deployment, browser
start/stop, active CDP connection, profile/login/runtime/database change or real
order was performed in this task. Scope: browser_bootstrap.py, its existing
release-infrastructure tests and this evidence only; review parent
`a421dc2e6eab467c4e6f9074d9992779dcb3266a`.

Reuse / safety correction: removed CDP discovery and WebSocket Browser.close
entirely from owned cleanup. A matching endpoint/port is never ownership proof.
The close callback captures the original launch-returned child object. Cleanup
requires an actual Popen child and, on Windows, its retained OS process handle;
Popen.terminate addresses that handle, not a rediscovered endpoint or naked PID.
Unverifiable objects/missing handles skip cleanup; exit/timeouts/OSError never
fall back to CDP, taskkill or PID-based shutdown. Never-ready launch cleanup
reuses this same guard instead of a second PID-based cleanup implementation.
Persistent/shared and already-attached browser ownership rules are unchanged.
This safety-first fallback may retain an unconfirmed child instead of forcing a
browser-tree kill; no live owned-Chrome shutdown acceptance was attempted.

The named historical test now injects a cleanup function which accepts only its
exact fake child, records that cleanup and leaves an unrelated fake process
untouched. Module-wide socket connect/connect_ex/create_connection guards fail
before network I/O. Direct production-cleanup regressions use Popen-spec mocks
and cover live/exited child handles, PID-only objects, missing child/handle proof,
cleanup timeout and both normal/never-ready cleanup. They forbid real HTTP and
PID/taskkill fallback. The original launch-timeout fake cleanup signature was
adapted to the endpoint-free API. No real Chrome process is created by these tests.

Passive operational snapshot (2026-10-15 approximately15:02–15:04 +08:00):
- Elevated Win32_Process plus independent Get-Process queries found no Chrome
  and no INSO-named process. Formal V1.4 running: ANOMALY / not observed.
- OS listening table returned zero9222 listeners. Chrome/CDP availability:
  ANOMALY / absent at snapshot; no TCP/HTTP/WebSocket probe was made.
- LastBootUpTime:2026-10-13 22:05:04. This alone cannot prove session continuity.
- Prior failed fake-process assertion is credible evidence of possible earlier
  interference, not proof of exact real-process closure. Cause, original-process
  continuity, tabs and login/session impact remain UNKNOWN. No automatic recovery
  was attempted; existing EXE/profile/login/runtime/DB and dirty work were retained.

Verification uses the existing release libraries and a temporary pre-import
socket guard: deny all external/pre-existing endpoints, including9222; allow only
an ephemeral listener actually bound by the test process for the existing socket
unit test. The lifecycle test module has its additional permanent fail-fast guard.
Full isolated offline regression:2123 passed /1 skipped in76.20s. Selected Ruff
and diff whitespace PASS. An intermediate focused run identified a stale mock
signature (fixed); a restricted-sandbox rerun had one frozen self-check resource
failure, while the same final code passed that test in the full elevated isolated
run. Final targeted result and cleanup are recorded below.


Final targeted isolated result:297 passed in7.92s. The passive Application crash
history query returned unavailable/no usable events; no causal conclusion is
possible. Current operational ANOMALY and historical session impact UNKNOWN are
separate conclusions. Do not restart/repair the session automatically on this
report's authority.

Cleanup: retired focused, focused-final, focused-verified and full task-owned
basetemps after absolute-path/reparse checks. Only focused-last could not be
enumerated (UnauthorizedAccessException), so it is specifically retained without
ACL changes/force deletion. Retire the tiny ignored execution/publication helpers
after push; no harness, log, build or staging is selected for Git. No protected
production artifact or unknown dirty work was deleted.

Publication: sensitive-content/diff review selects exactly the3 files above on
the CEO review parent. Uses the established isolated-index normal push to the
existing V1.4 branch, preserving local HEAD/index and all other uncommitted work;
no reset, force push or duplicate branch/report. Evidence is synthetic tests and
sanitized passive counts only. No EXE/release/config/profile changes are included.
Next: CEO independently reviews this safety seam and the operational UNKNOWN;
release remains on hold until that review, with no deployment performed here.


## CEO fourth independent review — 2026-10-15

**CODE REVIEW PASS; DEPLOYMENT ON HOLD — operational preflight anomaly.**

Independently inspected `a421dc2..53a9746` on GitHub:
`src/launcher/browser_bootstrap.py`, its release-infrastructure tests,
and this existing evidence record. Only these three files changed.
The owned-process cleanup no longer performs CDP discovery, WebSocket
`Browser.close`, arbitrary PID/taskkill fallback, or endpoint-based shutdown.
It requires the original `subprocess.Popen` child and Windows retained process
handle; unknown ownership skips cleanup. The historic fake-process test now
mocks cleanup and blocks direct socket connections; dedicated tests cover
owned/unowned, exited, invalid-handle and timeout branches. Protected
persistent/shared browser is not assigned an owned close callback.
This closes the specific prior unsafe shutdown path in code.

Executor reports focused 297 PASS, isolated full 2123 PASS / 1 skipped,
Ruff/diff PASS; CEO reviewed source and test cases but did not run a local
test suite or perform business/browser checks. This code review does not
establish live tray behavior or authentication acceptance. A verifiable owned
Chrome child might leave descendants on Windows after handle-only termination;
avoid risky fallback and assess only if operational symptoms arise.

**Operational hold, not a further code change request:** Executor's passive
15:02–15:04 +08 snapshot did not find the formal V1.4 process, any Chrome
process or a 9222 listener. This is an operational ANOMALY as observed, but
historical causation and preserved session/login status are UNKNOWN.
No current run-status claim is independently verified by CEO. A successful
isolated test cannot prove the earlier live browser was unaffected.

**Next release gate:** do not package/overwrite, relaunch Chrome or EXE,
attach CDP, repair profile/login, replay business, or alter DB on review
authority. First use passive read-only inventory to confirm formal EXE
presence/hash, protected profile/session backup and runtime junction/DB
integrity **without reading/exporting secrets**, plus application and
Windows event logs if available (record only sanitized conclusions).
Then arrange a controlled Owner-attended restoration of the *existing*
approved Chrome/profile and V1.4 (not a duplicate instance), with explicit
Owner authorization before launch, checking session/auth and normal app
behavior without creating test orders. Keep original rollback and
unknown dirty state intact. If any prerequisite is unsafe, hold and escalate
only that concrete issue.

**Disposition:** all 2026-10-15 fixes including INSO retry and CDP test
isolation have completed static code review; no new business changes
requested. Do not confuse CODE PASS with DEPLOYMENT PASS.
