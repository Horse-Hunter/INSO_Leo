# Google poll: one tab per worksheet, at most three

status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-19

## Owner scope / acceptance
Owner reports accumulating Google spreadsheet tabs. Final instruction supersedes
the earlier one-page-per-poll requirement: use one tab each for 2026, SHAHAB and
报价输入 (Owner's final clarification); reuse each within a poll; at most three program Google tabs, then close
normal pages at poll end. Diagnose and fix accumulating tabs, preserving existing
credentials/session/document/worksheet/write checks and unrelated dirty work.
No business replay, Sheets edits, browser/profile reset or unrequested release.
Real authentication/unsaved/script-pending work must not be blindly closed.

## Verified diagnosis / reuse
Read-only CDP observation found 23 tabs of the same document, all marked as
google-operation. 22 have a Google callout with role=dialog, one nonzero layout
rectangle and CSS visibility:hidden. Playwright confirms they are not visible.
All 23 have saved-to-cloud state and no refresh-pending/script-running marker.
The original _UNSAFE_POLL_PAGE checked rectangles alone, so the hidden callout
made pages protected, skipped poll cleanup, and forced repeated replacement.
Reuse GoogleQuotationUpdateActions/GoogleSheetsWebService and existing
google_operation_scope; key the existing page pool by document plus worksheet.
Metadata discovery uses the 2026 slot; quotation UI and range transport share
the 报价输入 slot. A truly protected slot is not repeatedly replaced, and new
program pages are capped at three for that document. Do not touch manual tabs.

## Verification / delivery
Targeted offline regressions include actual visibility predicate,
three independent source/input pages, repeated access, normal/error cleanup,
fresh next poll, real protected-page retention and no fourth owned page.
Live read-only diagnosis only; no rows or customer values persisted.
Keep REVIEW_REQUIRED for independent review.

## Owner-authorized release / cleanup
Owner explicitly requests solving the bug, packaging/overwriting/running V1.4,
closing the accumulated tabs and leaving only a blank page; Owner confirms the
program has exited. Reuse existing build/deploy/rollback paths, protect data,
configuration and Chrome profile/session, then normal idle GUI launch. This
supersedes the earlier source-only boundary. No automatic inquiry or order run.

## Implementation / offline evidence
Updated only existing GoogleQuotationUpdateActions and GoogleSheetsWebService.
Pool keys now include the worksheet; metadata uses 2026 and both quotation
controllers share the 报价输入 slot. Hidden dialog layout alone no longer marks
a page unsafe. Poll-final cleanup rechecks each page in case real unsaved work,
authentication, ownership loss or dialogs appeared after its last operation.
Protected slots are not repeatedly replaced; physically closed failed-read tabs
can still be retried through the original reader, and the program cannot open a
fourth owned page for the same document. Existing external/manual tabs stay out
of the production pool and cap.

Offline verification: 383 PASS in 6.74s across Google web/actions/pool tests,
Sheets, quotation update/discovery and backend tests. Actual JavaScript predicate
executes in Playwright's bundled Node with no browser/network: hidden callout
with nonzero rectangle is ignored; visible dialogs, pending refresh and unsaved
state still block. No dependency added. System Python lacked timezone data for
some cross-module tests; PYTHONTZPATH points to the existing release environment's
tzdata/zoneinfo (no configuration change). Initial old-one-page expectations were
updated to Owner's three-page contract. Ruff PASS; scoped source/test diff reviewed.
Live three-slot verification, release and cleanup receipt follow below.

## Live verification / installed release receipt
Owner-exited program was verified absent. Closed 22 residual tabs as explicitly
requested, keeping the existing blank page and the same protected browser.
Using the real existing actions and native worksheet selection (no row download,
cell editing or Script click), opened 2026/SHAHAB/报价输入 once each and visited
each twice. Actual peak: three Google pages; all three reused; poll-scope exit
closed all three; exactly one about:blank remained. This directly verifies the
corrected lifecycle on the live Google page, not business processing acceptance.

Source commit e49181908a1222c0fd7e9d7186d2e2ed8820ddf5, pushed normally to the
original V1.4 remote branch while preserving local HEAD/index/unrelated files.
All 122 canonical build inputs match that commit. Existing release script,
environment and spec reused with -Version 1.4 -BuildOnly. Frozen self-check and
RELEASE_SCAN_OK PASS. Old installed self-check, new installed self-check and
idle GUI self-check PASS. All 2875 installed assets verified; only EXE and
base_library.zip changed, with both prior assets hash-verified in rollback.
Copy-time protected file/link manifest (10 entries; runtime links not traversed)
unchanged. No configuration/credentials/DB/profile overwrite or Chrome stop.

Installed EXE SHA256:
119ca69058c6f16f48e064f97165acdba20de1f0562732ac2edcfc3d4d644915.
Visible normal launch at 2026-10-19 14:42:14 Asia/Shanghai: PID161128,
title INSO_V1.4, window present and responding. Launched idle, with no inquiry
or order run. Exactly one blank browser page verified immediately before launch.
Full business-poll/quotation write acceptance remains UNKNOWN; no live writes,
source replay, inquiry or email was initiated by this verification.

Ignored evidence/minimum rollback: .tmp/google-three-tabs-release-20261019/.
Task-owned test directories retired (12126021 bytes), live helper removed,
exact marked non-reparse stage retired (267813388 bytes); canonical script
removed PyInstaller work. Retained only small manifests/logs/receipts and two
old changed assets. All older rollback/runtime/CDP and unknown dirty work kept.


## CEO independent review — 2026-10-19

**CODE REVIEW PASS; DEPLOYED/IDLE ATTESTED BY EXECUTOR; BUSINESS-POLL ACCEPTANCE STILL UNKNOWN.**
Independently checked branch changes `c5879f4..1a31d41`,
core source commit `e491819`, the full current Google operation-page
pool, web range integration, the new predicate test and changed Google tests.

- Existing Google scope now retains separate slots keyed by document +
  worksheet: 2026, SHAHAB and 报价输入. Reused actions still validate
  existing document/ownership/gid and unsafe-state markers before borrow.
- The exact leak root cause (hidden Google role=dialog with nonzero rectangle)
  is addressed: the unsafe predicate now requires non-hidden, displayed
  dialog, while pending refresh, visible script running and unsaved state
  remain protected. The poll-final sweep re-verifies slot state and closes
  only unprotected owned operation pages.
- A protected same-worksheet slot is not silently replaced; existing
  owned pages for the same document are counted and a fourth is refused,
  limiting repeat tab accumulation. Real auth/dirty/script pages may remain
  intentionally and block that scope; this is a protected exception, not
  a normal-poll leak.
- Offline tests include a directly executed JS visibility predicate,
  distinct three-tab reuse, terminal cleanup, owned-tab cap, and protected
  dialog behavior. Executor reports focused **383 PASS**; full 2205+
  regression on this exact source commit was not reported. CEO did not run
  local tests or inspect live Chrome. Executor's live read-only three-slot
  verification and installed-binary receipt are credible evidence but are
  **not independent CEO observation**.
- Executor states Owner-authorized EXE overwrite was completed; installed
  SHA256 `119ca69058c6f16f48e064f97165acdba20de1f0562732ac2edcfc3d4d644915`,
  verified two-asset rollback, protected runtime/profile/DB/config preserved,
  idle GUI responsive, remaining browser tab blank. CEO cannot independently
  verify current running process from remote source review.

**Disposition:** Scoped code `REVIEWED_DONE`. No further code change requested
solely for this bug. Real inquiry/quotation/script/write behavior and whether
future polls leave exactly one blank page are **PENDING LIVE BUSINESS OBSERVATION**.
Owner may allow the next naturally due business run with normal vigilance:
do not manually replay uncertain orders; if tabs grow, auth prompts appear,
or writes look ambiguous, stop business processing without destroying
protected browser/profile and capture sanitized evidence. No further
packaging/action was performed by CEO.
