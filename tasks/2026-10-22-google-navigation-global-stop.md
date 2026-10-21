# Google navigation failure must preserve read recovery evidence

status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-22

## Problem and evidence
Owner reports global stop again after the authorized recovery release. Installed
EXE hash still matches the Oct21 release. Process remains alive; sanitized log
at Oct22 03:20:03.934 records google-open-sheet V12Fault,
GOOGLE_SPREADSHEET_UNAVAILABLE, then SHEETS_READ_UNAVAILABLE. No retry occurs.
Only blank page remains in read-only CDP inventory. Historical navigation URL,
HTTP response and original exception are UNKNOWN: the old diagnostic conflates
host/path/ownership failures. Do not claim a proven network root cause.

## Scope and reuse
Inspect and reproduce opening/navigation recovery gaps in the existing Google
actions/web reader/backend. Reuse five read attempts and 15-minute deferral;
keep auth, wrong document, unknown/security errors and uncertain writes guarded.
Add narrow sanitized cause distinctions for the conflated document guard.
Do not weaken document identity based on an assumed historical explanation.
No production data/credential/profile changes, business replay or browser kill.
Preserve unrelated dirty work; commit/push selected changes on original V1.4
branch and maintain REVIEW_REQUIRED. Prior release authorization permits a
verified follow-up package; do not replace a running executable.

## Acceptance / verification
Reproduce a genuine navigation transport exception leaving Chrome error page,
prove full bounded retry/exhaustion/next-poll recovery; verify certificate,
unknown, different document and authentication still stop without replay.
Review scoped diff, proportional offline regressions, record exact limitations.
Deployment and true long-running acceptance must be reported separately.

## Owner expanded audit (same task)
Owner asks what other gaps remain and why fixes keep missing them. Audit the
whole Google read/navigation/selection/metadata/cleanup/outer poll chain rather
than only the latest log reason. Confirmed gaps to reproduce: metadata reads
bypass source-reader retries and become shared-stop; hidden login text counts
as authentication failure; missing worksheet DOM is immediately treated as a
permanent mismatch; Playwright attach failures occur outside normalization.
Preserve bounded policy and no business/write replay; no generic framework.
Creation/cleanup/CDP ownership failures require separate distinction from
ordinary Google read outages, not a blanket catch-and-ignore.

## Verified source repair (not installed)
Opening transport exceptions now retain their original evidence when Chrome
lands on chrome-error://chromewebdata/. Only known read transport failures use
the existing read retry; TLS/unknown/wrong-document/auth and writes stay guarded.
Rows and metadata now share the same existing five-attempt helper; metadata
exhaustion reaches the backend as typed read-unavailable instead of permanent
input metadata stop. Lazy CDP attachment normalizes proven transport failures
before operations start. Await delayed worksheet DOM and ignore hidden login
markers; visible authentication still stops under the old policy. Sanitized
step distinctions identify host/path/ownership/error-page causes without URLs.

Initial navigation regression reproduced THREE failures (including the real
backend stopping without a next poll) before correction. Focused 331 PASS;
combined Google/INSO/backend/workflow/Findchips/site retries 1489 PASS,1 skipped
in41.28s; Ruff PASS. Includes network/certificate/unknown/auth/wrong document,
read-only metadata through actual quotation updater (zero input opens/clicks),
three complete synthetic backend recovery paths (navigation, attach, metadata),
visibility, delayed worksheet and no write replay. No actual business actions.
Historical Oct22 exact navigation/ownership cause is still UNKNOWN; this proves
repair of reproduced gaps, not proof that the original outage was networking.
Installed process209012 still uses the Oct21 package; no replacement/restart.
Owner then expanded policy: audit INSO/all fault routes and prohibit website
GLOBAL_STOP before continuous3h outage. That new explicit policy supersedes
this packet's older immediate website-stop acceptance and is a separate active
increment, not yet implemented or deployed by this source repair.
