# RFQ-008: GUI counters, source edits and selected-row rerun
Status: REVIEW_REQUIRED / independent Review REQUIRED
Branch: feature/v1-3-integration
Base: 7e4a63b0f74f4363053e90b12ef1835748a05cff (RFQ-006 CEO PASS)
Authority: Owner 2026-10-08 request and clarifications; canonical packet tasks/2026-10-08-gui-poll-stats-rerun.md.

Each15min cycle resets found/completed projections without dropping history.
Double-click model/brand/quantity/importance edits one original source cell, RAW plus readback.
Right-click purchase/quote actions execute serially only during idle countdown, reread selected
original worksheet/row and reuse existing coordinator / quotation integrated cycle.
Purchase only proven unsubmitted, current未发; quote current发给采购. Never rewrite status for retry.
Owner accepts original row anchor even when model/brand/quantity change; no fuzzy reassignment.
After manual action restart15min countdown. Preserve prior RFQ safety and reviewed records.
Offline tests and BuildOnly allowed; no production, actual mail, credentials or deployment.
Public GUI optional command contract and explicit workflow retry entry require CEO review.


## CHANGES_REQUESTED repair (2026-10-08)
Latest baseline43b9bccea94b71f5727662aaba7fd37f0d5077a1, CEO reviewbbd16d8.
Only B1/B2 lifecycle repair; accepted GUI/edit/counters/timer/CDP/SMTP paths unchanged.
B1: manual_purchase_retry=True only at accepted QUEUED/HUMAN_RESOLUTION event,
recover PURCHASE_EXCEPTION/ai-recognition and DUPLICATE_ORDER/empty scope, preserving
existing invalid-quantity recovery and unrelated alerts/history. New failure can raise new episode.
B2: selected original worksheet/row one-shot hold bypass; old matching keys remain durable active.
Match bound inquiry id or unresolved identity exact worksheet + row_position only, no fuzzy inputs.
Finalize only one selected terminal result: NO_RECENT_QUOTE or UPDATED_* closes old keys;
ROW_FAILED requires durable current hold, excludes its key from old closure; exceptions/stop preserve.
SOURCE_STATUS_NOT_UPDATED matching unchanged model/brand/quantity remains non-repeatable.
Multiple old closures are atomic through existing canonical V13HoldStore.close_many.
Focused/full offline + BuildOnly/self-check/scan required; no deployment/live actions.
CEO REVIEW.md remains exclusively CEO-owned and unchanged.
