# Task: V1.5 RFQ_BRIEF discovery and inquiry identity alignment

status: DISCOVERY_REVIEW_REQUIRED
phase: DISCOVERY_ONLY
owner: Codex
created: 2026-10-25
updated: 2026-10-25

## problem / goal
Owner requests safe read-only Brief discovery and real source/order identity evidence for both 2026 and SHAHAB, using reviewed V1.4 infrastructure in an isolated V1.5 worktree. Preserve UNKNOWN and stop at discovery.

## current_facts / authority
- Owner request in this chat supplies the bounded task requirements.
- Baseline: 124e39ca17dcf4a59e7e72b97a40331609d955e8, with explicit CEO code-review PASS. Later remote tip 4f58926 contains REVIEW_REQUIRED INSO recovery; intentionally excluded.
- Owner separately approved once-only read-only extension of the exact Brief title in the existing configured Spreadsheet, preserving existing browser/auth/document/gid guards and TSV limits, complete column inspection, no production code/schema/write change.
- Exact title is RFQ_BRIEF; Owner explicitly confirmed correction of RPF_BRIEF and application of that authorization to RFQ_BRIEF.
- Initial business/browser conflict stopped interactive discovery. Owner subsequently stated the program was stopped and CDP available; preflight repeated before resuming. Existing manual pages preserved; own pages only.
- Owner requested evaluating model+quantity+reverse ordering, then model+quantity+rfq_date. Discovery verified those alternatives and retained the two-to-two current pointer/order alignment separately from unique business keys.

## scope / non_scope
Read existing relevant navigation/safety/module/source/config wiring; reuse canonical CDP 9222 and native TSV. Full schema, raw price format, direct IDs first, compound-key uniqueness, real samples for each source, existing local identity/Research linkage read-only. No Google edits, email, ERP/procurement, quotation calculation, polling, production SQLite writes, browser launch/login/close/profile cleanup, dependencies, builds or deployment. No raw TSV/table/customer/account/order values/screenshots in Git or report. No real business data in test DB.

## acceptance / evidence
- [x] Owner-approved isolated branch/worktree and reviewed baseline; unrelated dirty work preserved.
- [x] A-I sanitized report: V15_RPF_BRIEF_DISCOVERY.md (requested filename retained; actual target correction explicit).
- [x] 17-column schema/header/85-record/target-price discovery and limitations documented.
- [x] Real unique source and existing inquiry_id/Research samples for both 2026 and SHAHAB; no regenerated ID.
- [x] Ambiguous/unmatched/current two-to-two pointer-aligned cases distinguished; repeated keys and descending-date evidence recorded without arbitrary one-to-many selection.
- [x] Existing 185 synthetic tests pass; no new implementation/test files.
- [x] Discovery stops; CEO review required. No follow-on business task.

## completion
- Read and identity proof achieved for both sources, subject to the explicit snapshot and unresolved-contract limits in the report. This is not CEO PASS or production-processing approval.
- Changed: two sanitized Markdown files only. Product code and production state unchanged.
- Checks: 185 PASS; final diff/sensitivity review and publication receipt in Git/chat. Initial timezone collection failure resolved by reusing bundled tzdata, no dependency installation.
- Limitations: 2026 date provenance, stable external ID and pointer/sort lifecycle, field conflicts, and unmatched local ledger/Research remain documented UNKNOWN. Current two-to-two order/pointer alignment is not a permanent unique business key.
- Retain this single V1.5 managed worktree for CEO review. No handoff created. Retire owned ignored helpers and synthetic test artifacts only; preserve all other worktrees/runtime/CDP/browser/Profile.
