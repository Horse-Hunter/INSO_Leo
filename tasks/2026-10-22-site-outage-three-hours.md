# Website outage recovery before three-hour global-stop threshold

status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-22

## Explicit Owner policy
Owner asks for INSO gap audit and all other global-stop routes; no more global
faults for websites unless a website remains wholly unusable for over3hours.
This supersedes earlier immediate global stop on website/auth/read failures.
The previous source repair is15b2015a3567dddfb27ce5de3eb4dce4d60c451f;
installed process209012 remains Oct21 package, business currently stopped.

## Scope / requirements
Audit all backend global-stop entry points (poll, research/manual callback,
manual action, preparation, worker, startup), INSO login/query and confirmed or
uncertain purchase writes, Google read/write/script, other research sites.
A website fault before continuous3h must leave the scheduler alive and retry
safe read/session checks. Track each website separately; proven recovery resets
only that site's outage period. Repeated intermittent failures must not add up
to3h continuous outage. Do not automatically repeat uncertain writes/submits,
bypass CAPTCHA/SMS, use credentials or production business operations as tests.
Local configuration/schema/database/invariant errors are NOT proof of a website
outage: preserve necessary affected-business pause and report honestly; no
cosmetic hiding of an actual stopped scheduler. No Chrome/profile changes,
new scheduler, dependency, parallel adapter or generic recovery framework.
Reuse current backend poll wait, INSO/query/session recovery, workflow ledger
and holds, Google bounded reads and outbox. Commit/push original V1.4 branch,
REVIEW_REQUIRED; only package after combined policy regression is proven.

## Verification
Use synthetic clock and existing fake site/page/backend/mail fixtures. Prove
short failure then recovery, same-site3h threshold, independent sites, reset on
real success, manual verification isolation, no uncertain-submit replay, all
entry points and local data safety. Record remaining UNKNOWNs explicitly.

## Implementation / audit results
One backend routing boundary now owns website deferral and escalation for poll,
worker, manual callback/action and procurement-local pause. GLOBAL_STOP state
has one assignment, gated by an observed same-site failure after3h monotonic
elapsed time. Existing900-second poll and source retry budgets are retained.
INSO/Google/IC.net/FX have separate timers; proven necessary read success clears
only its site. Mere login-page availability cannot clear INSO query outage.
Browser/CDP connection trouble defers safely without being mislabeled a3h site
outage. Explicit Owner stop wins; a new explicitly started run resets unobserved
idle time. No timer or scheduler thread is added and no new dependencies/modules.
Local DB/schema/config/invariant failures still pause affected/shared business
when safety requires it, but are not proof of a website outage; the UI does not
claim that paused business is running. If an uncertain purchase's review page
cannot even be identified/protected, shared business pauses locally rather than
risk closing it or repeating submission. This is a deliberate data-safety limit.

INSO initial login/research callback/query exhaustion/operation cleanup now feed
recovery instead of immediately setting global state. Explicit human challenges
preserve the original page during poll cleanup AND idle detach; later checks
attach to the same CDP and only inspect authenticated controls, with no login/
credential/business action in that check. An old authenticated DOM cannot hide
another still-present login/challenge page. Genuine query success resets INSO,
even if subsequent ECB conversion fails. Typed auth/shared query errors no longer
get swallowed by duplicate-query fallback or close a human page during reset.

Google source/metadata/attach/navigation fixes from prior packet remain. Repeated
authentication polls retain the same owned failed-read page instead of adding
new login tabs. Successful reads (not writes or attempts) signal recovery.
Unknown native initial update click acknowledgement/popup now uses only existing
bounded source-status readback; no second payload write or button click. A source
model change rejects settlement. Unconfirmed updates and script/input writes
become the existing per-order hold; refresh uncertain baselines keep their
previous rule. Shared pending/unsaved input remains occupied across poll scopes.
Uncertain purchase dispatch remains durably protected by existing ledger rules;
the affected review page is pinned through the original keepalive target IDs,
and other safe rows continue. No automatic purchase/submission replay was added.

Diagnostics distinguish waiting, local pause and prolonged outage. Operational
waiting mail no longer says stopped; local ledger/config notices do not invent
a website-login problem. Legacy non-V1.3 mailbox fallback avoids trying to insert
unbound operational mail into a non-null inquiry schema. Cleanup does not mask a
primary failure; diagnostic output stays closed codes/types, not provider text.

## Verification and current deployment limit
Final combined offline suite:1580 PASS,1 skipped in41.23s; Ruff PASS. Synthetic
actual backend tests show6 site/dependency fault types reach the next poll with
thread alive; actual INSO and Google sustained-failure loops perform twelve
virtual900-second waits and stop only on the thirteenth failed observation at3h.
Boundary10799/10800, independent sites, success reset, explicit stop, manual-page
lifecycle, initial delivered-click timeout, delayed status/no re-click, held
order continuation, FX cross-site reset, metadata retry and safe notices covered.
Three-hour duration is virtual; no actual3h outage, production login, query,
script, SMTP or order/Sheets write is used as verification. Historical03:20 exact
URL/ownership/navigation cause remains UNKNOWN, but its documented fault route
is now included in the shared recovery policy rather than immediate global stop.

The source-only deployment limit above is SUPERSEDED by the completed release
receipt below. Keep REVIEW_REQUIRED; independent review remains outstanding.

Final review additionally verifies the real JavaScript idle predicate: a quiet DOM
cannot release an initial dispatched update whose settlement is still unconfirmed.
The existing settlement observer carries an initial-mode bit; only proved
settlement/dismissal or human closure releases that shared input. Refresh-mode
recovery policy is preserved. Node evaluates the actual predicate in3 offline
states; the native delivered-click timeout regression has no dialog or running
text and still cannot open/write the next input. This prevents an unconfirmed
initial update from later consuming another order's payload.

Current frozen build input manifest contains122 tracked src/scripts/packaging
assets; final regression source bytes will be matched to the committed source
and rechecked after packaging. No normal source changes after this test receipt.

## Authorized release / startup receipt (2026-10-22)
Implementation commit:81a757d18fd71bd72d47f5dc174318c9a3c0cd42 (21 files,
932 insertions/177 deletions, including tests/docs). All122 frozen build input
hashes match the tested source before replacement. Canonical existing command
`scripts/build_windows_release.ps1 -Version 1.4 -BuildOnly` completed; frozen
self-check and RELEASE_SCAN_OK passed. No parallel package pipeline was added.

The previous process had exited before replacement; no force termination was
used. Replaced only `INSO_V1.4.exe` and `_internal/base_library.zip` at the existing
`D:\Program_Leo\INSO_Leo\dist\INSO_V1.4` installation. Verified all2875 program
assets against staging; all10 protected non-program files had identical hashes
immediately after copying. Config/credentials/runtime/database/CDP profile were
not replaced. Only the two previous program assets were backed up locally;
the Oct21 rollback is retained separately. Installed EXE SHA256:
`5ff5e5cab799dcf8fcbd9335182d03ddef3192a7a767b49af30c9eb6603254d2`.

Installed dependency check and actual idle GUI check both exited0. Launched the
normal visible installed EXE; PID230216, title INSO_V1.4, nonzero window handle,
Responding=True, and a later independent process check still passed. No Start
action, business polling, order processing, production site login/query, SMTP
or Sheets write was performed. This is genuine packaged idle-start evidence,
not live business-chain or actual three-hour outage acceptance.

Read-only CDP metadata checks, including outside the sandbox, found port9222
unreachable at this time. Current tabs are UNKNOWN; do not claim only a blank
page remains. No Chrome process/profile/port/config was started, stopped or
modified to obtain an apparent passing result. Browser availability remains
an operational prerequisite for later business start, not a package failure.

Retired23 owned disposable directories (748442695 bytes), including the canonical
marked stage and this task's synthetic test directories after verification;
no reparse points were followed. Retained only compact release/test/hash receipts
and necessary rollback at ignored `.tmp/site-outage-release-20261022/`, plus
existing protected prior rollback/runtime/unknown dirty work. Source, deployment,
startup, browser and cleanup receipts are local only, without production output
in Git. No further source changes after the1580 PASS/1 skipped regression.
Status remains REVIEW_REQUIRED. Owner may start ordinary business when ready;
external site availability and actual long-running acceptance remain UNKNOWN.
