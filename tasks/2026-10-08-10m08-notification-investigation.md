# Task: Investigate 10M08 order-processing exception mail

status: complete
owner: Codex
created: 2026-10-08
updated: 2026-10-08

## authority / scope
Owner reports receiving a new order-processing exception mail for a model starting 10M08, asks whether it was sent incorrectly. Read only the relevant local production logs, notification ledger, inquiry/event/purchase state and deployment history; compare notification trigger to source code. Local SQLite must be opened mode=ro/query_only. No remote Sheets/browser access, credentials, SMTP, purchase replay, business DB changes or deployment in this investigation.

## acceptance
Locate matching orders and mail timestamps/reasons/delivery outcomes; explain whether a current failure, delayed historical alert or misclassification is supported by evidence. Preserve UNKNOWN if local evidence cannot establish remote result. Keep raw business rows/body/log dumps untracked; commit only sanitized investigation scope/conclusion if needed.

## conclusion / verification
The reported new mail is a false procurement status-write alarm after successful quotation completion, not a newly failed purchase or a delayed replay of an old email.

Sanitized timeline (Asia/Shanghai):
- 2026-10-08 17:00:28.795: matching inquiry logged V1.3 UPDATED_INSERTED. The canonical quotation updater emits this after checking source status equals 采购已报价.
- 17:01:36.256622: a new SHEETS_WRITE_BACK / SheetRecordConflict notification was created and V1.2 local business projection changed to STATUS_WRITE_PENDING.
- 17:01:40.409674: recipient owner delivery marked SENT, attempt 1.
- Local irreversible purchase outcome remained SAVED from the previously confirmed purchase. Earlier save-outcome alert had already recovered; the new command is distinct.

Root cause: launcher poll loop calls PurchaseCompletionActions.retry_saved_statuses() after quotation processing. The restart-local _settled_status_ids set does not contain old saved inquiries. Purchase status locator accepts only 未发 / 发给采购, so a correctly advanced 采购已报价 row is rejected as SheetRecordConflict; _write_back() misclassifies that progress as a status-write failure, records STATUS_WRITE_PENDING, and enqueues the exception email. The source write guard blocked a backwards write, so the new alarm did not itself overwrite source status.

Evidence: read-only SQLite notification/events/purchase/alert ledger, installed runtime quotation log and source inspection of src/launcher/purchase_completion.py, src/sheets/purchase_status.py, src/workflow/v13_quote_update.py and src/launcher/backend.py. Database opened URI mode=ro and PRAGMA query_only=ON. Full mail/body/customer payloads were not saved in tracked source.

Offline reproduction with existing synthetic actions/SAVED fixture and source 采购已报价: retry_saved_statuses creates one SheetRecordConflict email and STATUS_WRITE_PENDING, with zero writer calls. No real mail/purchase/source mutation was used.

Correction boundary identified for a subsequent explicitly requested repair: validate current canonical identity/status before V1.2 completion retry, regard uniquely confirmed forward quotation completion as no-op for purchase status write, retain true source-conflict alerts and never reset source to 发给采购 or replay purchase. Historical local false STATUS_WRITE_PENDING recovery requires its own authorized policy; investigation did not alter production ledger.

Remaining UNKNOWN: current remote sheet status after the recorded success (no remote query performed); successful status was verified at the recorded quotation update. Browser focus repair is unrelated to this trigger; same V1.2/V1.3 boundary existed earlier.

No implementation/deployment changes, workflow replay, production writes, real SMTP or credential access. Local investigation only; no external report upload.
