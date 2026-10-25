# Task: Minimal INSO recovery when no INSO page remains

status: IN_PROGRESS
owner: Codex
created: 2026-10-25

Owner authorizes a minimal source fix after read-only investigation in
2026-10-25-inso-unavailable-investigation.md. Confirmed potential deadlock:
manual-wait recovery demands a pre-existing authenticated shell even when no
INSO page remains. Historical first authentication failure remains UNKNOWN.

Only allow the existing fresh authentication/business path to resume when a
connected single context positively proves there are NO live INSO-origin pages.
This is not authentication or business success; retain the outage clock until
existing successful necessary business read. Any existing INSO login, challenge,
home/list page, disconnected/multiple/ambiguous context or unreadable page keeps
existing manual-wait/protection behavior. No credentials, retry budgets, human
challenge handling, submit/write replay, outage thresholds, Google/Research or
GUI changes. Reuse current poll and session guard; no new module/dependency.

Change only INSO session predicate, existing backend recovery condition, targeted
offline tests and task documents. Verify missing-page recovery, intact challenge
wait, unknown/disconnected cases, next ordinary guarded authentication, no direct
login/write in recovery, site clock retained, normal authenticated recovery and
existing session/quotation/poll/shutdown regressions. Commit/push original V1.4
branch preserving unrelated work/index/HEAD, REVIEW_REQUIRED. No build/install/
restart/production browser, login, order or business-data operations in this task
unless separately authorized below.

## verification / release authorization

Minimal change: public predicate in existing inso_session proves absence only
for a connected, unique, readable context. Existing backend manual recovery gate
permits the canonical fresh session path on that proof, retaining its original
outage start; no authentication/business success is fabricated. Existing INSO
pages, challenge/ordinary-login/landing/list and ambiguous contexts keep waiting.
No changes to AUTHENTICATION_REQUIRED classification, retries, guard or submission.

569 offline tests PASS in26.15s: site outage/session/V1.3 operation/backend/RFQ006,
tests/inso, workflow V1.3 and GUI. Six new cases cover missing/other-site pages,
existing login/home/list, clocks retained, and disconnected/ambiguous/unreadable
context. Existing human-page preservation, authenticated recovery, ordinary guarded
login, no repeated submission, three-hour boundary and shutdown suites pass.
Scoped Ruff/diff checks;123-input source manifest changes only two launcher files.

Further read-only log check confirms same fault chain: Oct25 00:53:45 waiting,
15-minute authentication failures through03:38:55, then03:53:56
INSO_OUTAGE_THREE_HOURS. This is not proof that the website was down continuously;
historical first failure reason and actual in-memory flags remain UNKNOWN.

Owner subsequently explicitly requests fix/build/replace/run and reports app
exited. This supersedes the earlier source-only restriction for deployment only:
reuse canonical BuildOnly/spec, self-check/scan and existing installation. Confirm
old process absent before copy; no force termination. Verify rollback and every
program asset, preserve protected config/data hashes and links AT COPY. Installed
dependency/idle GUI self-check, normal visible idle launch and observer receipt.
No automatic inquiry/order/login, production CDP/tab/profile/data operation. Retire
only owned staged artifacts, keep compact evidence/rollback. Source and release
receipt stay REVIEW_REQUIRED; no claim of fixing historical initial auth cause.

Completion: source verified; commit/build/deployment/startup pending.
