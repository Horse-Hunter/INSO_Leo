# Task: Repair quotation-complete purchase-status retry false alarm and deploy

status: complete
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
Offline regressions and controlled final deployment completed. Preserve V1.2, DB/backups, OAuth/credentials/config, fixed Chrome/CDP. Only release assets replaced after ensuring formal program stopped. Local report only, no upload implied.

## Owner steering / canonical brand boundary
Owner clarified brand fuzzy matching is sufficient. Purchase completion injects the existing v12_safety.brand_matches AI_BRAND_V1 policy into the Sheets helper (dependency direction retained); actual source brand expectation still uses the canonical quotation expected_source_brand rule, not arbitrary Research display names. Model/quantity/tier and globally unique source binding remain strict. No new brand alias/synonym policy.

## completion / verification / deployment
- Initial implementation commit 9a01b64168bb2ea5d4fa751dc167959da4653ff2; final source-brand/fuzzy refinement commit 80f9c3776ec15ee212451008e2c7c80df20f41f6.
- Production changes confined to src/sheets/purchase_status.py and src/launcher/purchase_completion.py; src/workflow/v13_quotation.py adds a public wrapper around its unchanged canonical source-brand calculation. No procurement writer, scheduler, browser implementation, quote updater or SMTP transport rewritten.
- Normal unique 未发 status retry is retained. Both 发给采购 and 采购已报价 satisfy the purchase-status obligation after fresh identity proof; no downgrade, writer construction, mail or sending episode for already satisfied rows. Pending recovery requires durable SAVED, changes only V1.2 purchase projection to PURCHASE_RECORDED through existing transaction/event API and leaves quotation outcome independent.
- Unknown/unconfirmed durable purchase outcomes, changed model/quantity/tier or ambiguous rows remain held; real write/read/conflict failure notifications remain. Brand uses Owner-approved existing fuzzy policy, with actual-source expected brand, not arbitrary Research label.
- Genuine write-conflict message now tells Owner to retain already completed statuses and only consider a correction for genuinely 未发 sent purchases. Old immutable delivered email/history is not deleted or rewritten.
- Final focused: **291 passed**; full safe/offline: **1599 passed / 1 skipped** (existing Windows symlink capability skip). Ruff / diff check PASS.
- Final BuildOnly / release scan / frozen self-check / isolated idle GUI PASS.
- Final deployed directory: `D:\Program_Leo\INSO_Leo\dist\INSO_V1.3`.
- Final deployed EXE SHA256: `3A914A5D177EA0629511791364341D20BD628877B1F22C18139A3B306C76A8F1`; all 2179 installed asset hashes match built final candidate.
- Final pre-replacement complete backup: `D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.3_20261008_173001_8f0a0ae5`; 2184 source files verified. First pre-task 6A9D19DA release backup retained at `D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.3_20261008_172012_e9cd065e`. Intermediate 21664241 package was superseded during final brand review, with no business polling by this task.
- Deployed frozen self-check / idle GUI / existing fixed-CDP check / deployed-assets scan: PASS. GUI STOPPED, no business thread, existing one context/one blank page retained.
- V1.2 before/after SHA256 identical: `340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F`.
- Production DB/backups, OAuth/credentials and production/Research/SMTP configs unchanged. Of 3953 inventoried files, 3952 hashes unchanged; only fixed Chrome's running `Local State` file changed while Chrome remained active. Deployment performed no direct profile writes/clear/replace; cookies and other inventoried profile files unchanged. Pre-change contents were not copied, so changed Local State keys remain UNKNOWN; it was intentionally not restored over running Chrome.
- Local production DB was not manually repaired or migrated: existing false STATUS_WRITE_PENDING will resolve on the next Owner-started normal cycle only if fresh source identity and completed status are confirmed. No guessed historical timestamp.
- No live procurement, Save/Save-and-Send, source status write, quotation input/update, Apps Script, SMTP delivery, historical replay or business poll executed. Owner authorized packaging/overwrite; no new CEO PASS claimed.
- Detailed evidence main `.tmp/v13-deploy-20261008_173001_8f0a0ae5/plan.json`, `verification.json`; `.tmp/v13-status-repair-final-build.log`, `v13-status-repair-final-frozen-report.json`, kept local/untracked. No report upload implied.

Bug修复已打包覆盖正式V1.3，部署任务未启动业务轮询。
