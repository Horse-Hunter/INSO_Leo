# RFQ-011 V1.4 Phase3 unsaved sales details
Status: REVIEW_REQUIRED / independent CEO Review REQUIRED
Base: b1a11820bff01e939b63dba0cf0072318787ce1f REVIEWED_DONE
Authority: Owner pasted Phase3 request, 2026-10-10.

Only GUI-selected one of the two confirmed mails per invocation; no polling.
Complete in-memory PI/details validation and serial existing ICNET queries before
any INSO mutation. Required PART NUMBER/L/T/BRAND/DC/QTY/UNIT PRICE, unique header,
positive integer qty/positive original RMB untaxed price, no amount/total input.
One Shanghai today per invocation: 1-3 DAYS +7; X-X WEEKS max*7+7; otherwise stop.
Reuse canonical ICNET credentials/CDP/login/search/parser; count packages in first
20 displayed rows without secondary model matching; first-seen wins ties, cache
exact duplicate model only within invocation. Preserve Research default rules.
Reuse approved Phase2 development sales tab/header, never redesign lifecycle.
Add exactly one native row per click with +1 readback until N, stop if existing>N.
11 fields per row, immediate/row/full readback, no JS forced values; fixed values
全新拆封/无/1/是. No CONDITION or total. Retain page for Owner review.
Any natural business failure notifies 229/shawn through existing outbox/1069 SMTP,
independent retry/dedupe, old enums only; no deliberate real failure test.
No Save/submit/PDF/delete/Sheets/purchase/quotation-state/deploy/secondmail.
Owner gates live1-row then manual return then live4-row. Offline fake transports.
Focused/full safe-offline/Ruff/diff, sanitized report12 points, commit/push, verify
remote/local HEAD and clean. No Phase4. UNKNOWN full live procurement/notification concurrency and future template formats.
Notification persistence if needed isolated development ignored DB using existing
V1/V1.2 schema/worker, no production business DB or enum/migration alterations.

Live acceptance: 1-row GUI check -> Owner 已返回 -> 4-row GUI check; both
WAITING_OWNER, all reads equal, same unsaved XS and protected tab retained.
Old-schema notification FK uses isolated MANUAL_REVIEW anchor, never production
inquiry/purchase/quotation-state writes. See EXECUTION_LOG and FINAL_REPORT.
