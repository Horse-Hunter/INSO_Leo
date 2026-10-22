# Task: Release browser automation during the inquiry countdown

status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-22

## problem / verified facts
Owner reports five manually opened research sites stalled during inquiry countdown
and recovered after stopping inquiry. The exact stalled-page state was not captured
and remains UNKNOWN. Read-only CDP inspection later succeeded with seven pages.
Code has a concrete lifecycle gap: worker-thread BrowserHandle.disconnect queues
Playwright teardown for its owner, but the owner's countdown wait does not drain
that queue. Existing Oct13 diagnosis independently reproduced the resulting sync
client reattachment failure offline. Do not claim this proves all past page stalls.

## scope / authorization
Owner authorizes a minimal fix, verification and canonical V1.4 build/replacement.
Also inspect today's application exits/crashes read-only and report evidence.
Reuse existing owner-thread release/deferred-stop facilities and wait loop; no
new runtime module, dependency, timer, browser profile or business policy changes.
Commit/push original codex/v1-4-order-mail-inspection; REVIEW_REQUIRED.
No production credentials, website login/query, source/order/Sheets/SMTP writes,
browser shutdown or automatic business start as tests. Preserve manual/security/
uncertain-result pages and installed runtime; no forced process termination.
Actual Playwright start/stop without a browser and synthetic offline fixtures are
authorized. Read-only process, Windows error events, sanitized lifecycle logs and
CDP metadata are authorized; original program/profile data remain untouched.

## acceptance / verification
- Owner-thread idle release completes promptly during countdown, including work
  previously deferred by another thread, without waiting for a whole poll interval.
- Thread affinity, explicit stop/manual actions and subsequent cycle attachment
  remain correct; in-flight work is not disconnected. Protected pages/browser
  stay open and existing Google tab/write and INSO hold rules remain intact.
- Reproduce before correction with real Playwright client plus bounded countdown;
  add targeted regression and run the relevant existing backend/browser/site suites.
- Scan/self-check canonical frozen build, replace only program assets with rollback,
  verify protected hashes, safely launch only idle if needed; retain REVIEW_REQUIRED.
- Retire this task's owned disposable test/build copies; retain compact receipts
  and rollback. Historical cause / real-world UI acceptance stay UNKNOWN if not seen.

## completion
The original three countdown tests failed before correction, including real
Playwright start/stop without Chrome, credentials or network. Production change
is four added lines (two comments and existing release/drain calls) inside the
existing countdown actor. Each wait tick releases an idle handle on its owner
thread and drains teardown queued by workers, including requests arriving after
the wait starts. Existing in-flight guard, stop/manual actor, page preservation,
next cycle reconnect and all business logic remain canonical and unchanged.

New tests cover immediate and already-deferred real-client release, late queued
release, same-thread teardown, subsequent real-client startup and preservation
of pending-order/human-login/local-pause pages without closing shared Chrome.
Initial focused run:187 passed,3 failed. One failure was the base test interpreter
missing pypdf (present in the existing release environment); no dependency was
installed. The other two are stale foreground-creation tests expecting one
attempt despite the pre-existing five-attempt timeout policy; the fixture now
uses virtual waits and checks all five attempts remain background. No production
login/retry change. Final combined regression and release receipts follow below.

Today's crash audit: Windows Application events1000/1001/1002/1026 queried
successfully (five events overall, none matching INSO_V1.4/INSO_Leo); no matching
today's WER archive/queue directory was found. No V1.4 process existed at this
inspection. Current application log has493 today records, last20:47:49.434, no
ERROR/CRITICAL record in those lines. There is no explicit normal-exit/start
receipt in the existing logger, so actual process exit time/cause is UNKNOWN.
No evidence proves a native crash, and absence of WER does not rule out silent
process exit or termination. No speculative crash fix or extra logging added.

Historical manual-page freeze cause remains UNKNOWN; the connection-lifecycle
gap is independently reproduced, not proof every website stall shares this cause.
Combined regression:1691 passed,1 skipped in55.11s, using existing release
dependencies (pypdf/tzdata included) with the normal pytest runner. Supplementary
background/countdown boundary suite:10 passed in2.18s, including all repaired
stale test expectations. Ruff and selected diff checks PASS. Source complete;
Owner-authorized package/replacement completed as recorded below; independent
review and live manual-page countdown acceptance remain outstanding.

## Release / startup / cleanup receipt
Source commit5887d8a7af810a8fbc111cacc06782c7ce000976 pushed to the original
V1.4 branch, parentade1e845dfe87000879f4e6fc308e3635579b371 (preserving the
concurrent independent review of the previous three-hour outage change).
Four selected files,216 insertions/2 deletions including tests/packet; production
diff is only src/launcher/backend.py,+4 lines. All122 tracked build input blobs
match the committed tree and raw hashes match tested bytes before/after build.
Real local Git HEAD/index and unrelated dirty work are preserved.

Canonical existing BuildOnly V1.4 command completed, frozen self-check and
RELEASE_SCAN_OK passed. Confirmed the previous application process absent before
copying; no process/browser force termination. Backed up/replaced only the EXE
and _internal/base_library.zip at the existing root installation. All2875 program
asset hashes match staging; all10 protected runtime/config/data file hashes were
unchanged immediately after copying. Previous and current rollback retained.
New installed EXE SHA256:
fe805ef6d7b051c214cafa0683680a8eec8eaf2c3fb28f384d4ebb25ea0076a0.

Installed dependency and idle GUI self-checks exited0. Opened normal installed
GUI idle; PID217720, start2026-10-22 21:15:03 local, title INSO_V1.4, nonzero
window handle and Responding=True; a later check still confirms that process
responding. Business not started. Read-only CDP snapshots before copy and after
startup both show11 pages and identical anonymous target fingerprint. No manual
page was closed, no browser/profile/login/credential changed, no live business
or site-login verification performed. Historical stall/exit causes remain UNKNOWN.

Retired all six owned disposable directories: five synthetic test roots and the
canonical marked stage, with no reparse point followed; staging alone retired
267826448 bytes. Retained compact ignored test/source/hash/startup/cleanup evidence
and necessary rollback at .tmp/cdp-countdown-release-20261022, preserving prior
rollback/runtime/CDP/unknown dirty work. No generated file or production output
is added to Git. Status remains REVIEW_REQUIRED.
