# Bounded recovery before declaring INSO authentication unavailable

status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-21

## Owner scope
Owner asks to fix incidental INSO login failure by adding retries, like Google.
Existing incident 2026-10-20 18:24:00 reports only INSO_AUTHENTICATION_REQUIRED;
its underlying reason is UNKNOWN, so do not claim a confirmed expired password
or a reproduced historical network error. Reuse the one InsoSessionGuard and
the existing page, native login/menu proof, Core-supplied credential and CDP.
No alternate browser/profile/login recipe, business write or procurement replay.

## Requirements / reuse
The common authentication handshake retries transient loading/navigation timeout,
connection failure and unconfirmed authenticated-shell readiness at most five
times, waiting 2/4/6/8 seconds. Reuse the same tab during recovery; do not leak
fresh login tabs or change operation leases before authentication is proven.
Success returns to the existing caller; only exhaustion returns the existing
failure/notification path. This is bounded login recovery, not Google-style
automatic resumption of procurement after an uncertain write.
Missing credentials, explicit password rejection, human/SMS/device verification,
ambiguous context, unknown errors and identity/lease failure remain immediate.
Reuse existing shared rejection-text/visibility helpers and existing transient
site codes rather than inventing another login framework. Preserve raw-error
classification only internally; never output credential-bearing exception text.
Do not add retries around business actions or Save-and-Send.

## Acceptance / delivery
Offline tests: first transient then success, five-attempt bound/backoff, page
reuse and ownership, no premature lease/business continuation, challenge/password
rejection/unknown/identity failures do not retry, unchanged successful login.
Commit/push only scoped files to original V1.4 branch; REVIEW_REQUIRED.
No live authentication, credentials, runtime changes, package/deployment/restart
unless separately requested. Preserve all unrelated local dirty work.

## Implementation / evidence
Extended only existing InsoSessionGuard and its ordinary-login field/error
handling. Proven browser/network transient errors retain BROWSER_TIMEOUT or
LOGIN_PAGE_UNAVAILABLE instead of collapsing into AUTHENTICATION_REQUIRED.
Authenticated-shell not yet ready can retry. Same-tab retry preserves owned
versus supplied-page identity and leases the business page only after success.
Existing shared visible rejection text is checked on the login form and during
post-submit settlement. Missing credentials, unknown/certificate errors,
human verification and post-login lease/identity failures remain immediate.
After five failed transient attempts, preserve the existing stop/notification
policy; this task does not introduce automatic 15-minute business replay.
No business operation, query retry policy, saved-state or submission code changed.

Verification: final **688 passed in 13.59s**, Ruff PASS, scoped diff reviewed. Includes
existing session and quotation-operation tests, site retries, real backend,
RFQ006 integration, INSO and V1.2 flow/rules. Nine new offline cases cover
transient-then-success, exact 2/4/6/8 backoff and five-attempt exhaustion,
certificate/unknown no retry, delayed native-shell readiness, password/challenge
after a transient, single fresh owned page and no premature re-lease.
Two old at-most-one-submit expectations changed only for repeatable shell
readiness failure. Test clocks avoid real retry sleeping; native-menu render
poll waits remain separately exercised. No network, live INSO credentials,
production browser/profile, SQL/Sheets writes, notifications or business actions
were used. Real 18:24 incident subcause and live acceptance remain UNKNOWN.
Installed V1.4 remains unchanged pending an explicitly authorized replacement.

Retries recheck human verification/rejection BEFORE revisiting the login page;
navigation reopens even if a prior timeout already changed the URL to /login,
so a partially loaded form is not trusted. Regression models this partial-URL
landing. All task-owned test artifacts retired (initial18452182 bytes); no
worktree/build/release copies created. Keep original HEAD/index and other dirty
files. Final verification/cleanup receipt updated after the partial-URL check.
Partial-URL regression models both Playwright's page.url and frame URL. Terminal
five-attempt failure logs one sanitized INSO_LOGIN_RETRY_EXHAUSTED reason, so
future logs can distinguish exhausted recovery from a first failure; no raw
login exception text or credentials are added to logs.
Final log-only delta: 64 focused session/retry tests PASS in0.69s, Ruff PASS.
Final task-owned test directories removed after checks; no release artifacts
created. Commit/push only inso_session.py, its existing/new tests and this packet.

## Owner-authorized installed release
The prior not-installed delivery limit is superseded: Owner explicitly requested
packaging/overwrite/run after combined verification. Installed with Google busy
read recovery on2026-10-21;1471 combined tests PASS/1 skipped, scanner and staged/
installed/idle GUI checks PASS, normal idle startup responding. Canonical
receipt/rollback/limits: tasks/2026-10-21-recovery-authorized-release.md.
REVIEW_REQUIRED remains; no actual business run or long-running acceptance claim.
