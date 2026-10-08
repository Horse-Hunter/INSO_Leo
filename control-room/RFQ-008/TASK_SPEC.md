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
