# GUI poll counters and manual single-row rerun
status: complete
owner: Integration Executor
created: 2026-10-08

## Goal / authority
Owner requests current15-minute poll counters reset/update and result-row right-click actions
for purchase or quote rerun, only during idle countdown, fresh Google row data before execution,
reuse existing workflows serially, reset15min countdown after completion. RFQ006 approved base
7e4a63b; preserve CEO review files and safety rules.

## Scope / requirements
Cycle counters separate from entire run/history, reset on poll begin and update during work.
Manual rerun is a serial poller command, never an overlapping browser or writer/worker.
No real business test/deployment, dependencies or second workflow/identity/SMTP system.
Owner confirmed unsubmitted-only purchase retry and original worksheet/row anchor.
Status gates preserve existing未发/purchase and发给采购/quote; no automatic status rewrite.
Keep durable Save uniqueness and ambiguous source fail-closed; preserve original audit history.

## Verification
Fake polling/counters/history retention; menu capability and idle-only dispatch; fresh source
binding/model correction; duplicate requests/stop/scheduler serialization; existing shared regression.
Full safe/offline, Ruff/diff and BuildOnly/frozen candidate only. Commit/push clean equality.

## Original implementation completion (bc4c1e4)
Implementation complete; RFQ-008 REVIEW_REQUIRED, previous RFQ006 approval unchanged.
Changed: GUI/contracts/backend/manual source adapter, single-cell writer, canonical explicit retry APIs, tests.
Verified: final focused523 PASS; full safe/offline1475 PASS/1 SKIP; new targeted45 PASS; Ruff/diff PASS.
BuildOnly/frozen self-check/release scan PASS; installed EXE untouched.
Limitations: status gates未发/purchase、发给采购/quote preserved; SHAHAB fixedA; input edits do not
recalculate historical research prices. Google values persist, current-source GUI overrides are session
views; historical audit may show previous inputs after restart until a fresh selected-row action.
No live production/browser/SMTP test or deployment. See control-room/RFQ-008/FINAL_REPORT.md.

## Owner clarification / additive editing
Purchase rerun only unsubmitted/explicit pre-submit failures; sent/unknown/status-write-pending
must not resend. Read selected original worksheet/row, accept corrected model/brand/quantity,
update GUI row. Source status gate uses existing未发/purchase and发给采购/quote pending further
Owner steering. Owner additionally authorizes double-click edits for model/brand/quantity/tier,
single-cell RAW write + readback, same serial countdown-only command boundary. No live test.
SHAHAB tier is fixedA with no physical column, so it cannot be edited through fabricated mapping.

## CHANGES_REQUESTED repair authority (2026-10-08)
Continue from43b9bcc, only CEO B1 alert lifecycle and B2 one-shot hold lifecycle.
Reuse existing recovery event/transaction; recover only manual ai-recognition and duplicate scopes.
Keep matching bound/unbound old holds durable until selected quote result settles.
Full offline/focused, BuildOnly/self-check/scan; no deployment or live business.
CEO REVIEW.md must remain unchanged.

## B1/B2 repair completion
Complete implementation only; RFQ008 REVIEW_REQUIRED, CEO REVIEW unchanged.
Changed:manual alert recovery flag, ManualRetryHolds/finalizer, canonical runner return, atomic close_many.
Focused451 PASS; full1507 PASS/1 SKIP; Ruff/diff/build/frozen/scan PASS.
No new decision conflict; no live business/deployment. New candidate:7ECE6917BF77E263E1E56BC528A63EE0798404DB1D03D494499B94A4A16B663F.
