# Google poll: one tab per worksheet, at most three

status: in_progress
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
