# Task: Repair quotation-complete purchase-status retry false alarm and deploy

status: in_progress
owner: Codex
created: 2026-10-08
updated: 2026-10-08

## authority / root cause
Owner explicitly requests diagnose, fix, package and overwrite. Investigation identified post-quotation V1.2 saved-status retry rejecting the higher source status 采购已报价, sending SheetRecordConflict mail and projecting STATUS_WRITE_PENDING.

## requirements / acceptance
- Extend canonical purchase status write/readback idempotency to accept uniquely identified 采购已报价 without writing backward, mail or new sending timestamp. Retain model/quantity/tier/brand checks and ambiguity refusal.
- On normal future poll, durable SAVED + STATUS_WRITE_PENDING may recover to PURCHASE_RECORDED only after fresh read-only confirmation of corresponding source 发给采购/采购已报价. Never retry purchase, write 未发 pending rows, guess identity, clear unrelated alerts, delete events/mail or conflate purchase and quotation completion.
- Fix mail instructions for genuine write conflicts so they never blindly instruct downgrade of an advanced state.
- Offline regressions/focused/full/Ruff/diff; BuildOnly/frozen/scan. Explicit Owner-authorized controlled deployment with fresh backup and full protection inventory, no separate CEO approval asserted.
- No live purchase, SMTP, source writes/replay or business polling in this task. Do not repair production DB directly; next Owner-run normal poll performs guarded reconciliation.

## acceptance
Pending tests and verified deployment. Preserve V1.2, DB/backups, OAuth/credentials/config, fixed Chrome/CDP. Only release assets replaced after ensuring formal program stopped. Local report only, no upload implied.

## Owner steering / canonical brand boundary
Owner clarified brand fuzzy matching is sufficient. Purchase completion injects the existing v12_safety.brand_matches AI_BRAND_V1 policy into the Sheets helper (dependency direction retained); actual source brand expectation still uses the canonical quotation expected_source_brand rule, not arbitrary Research display names. Model/quantity/tier and globally unique source binding remain strict. No new brand alias/synonym policy.
