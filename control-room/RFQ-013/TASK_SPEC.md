# RFQ-013 Owner PDF upload increment
Status: REVIEW_REQUIRED
Base39cfcfa2564958282074b3fcd5dbfc320a09ea4d; prior RFQs REVIEW_REQUIRED.
Owner2026-10-10 explicitly authorizes native attachments tab -> mail PDF selection
-> 开始上传 -> verify 已上传1张. Supersedes earlier no-PDF boundary only.
No Save/review-submit, auto polling, deployment, other business/Sheets/DB changes.
Exactly one selected mail PDF, validate preflight before INSO mutation; missing,
multiple, invalid/encrypted PDF stops, no guess. Bytes stay memory/no Git.
Existing strict Excel/ICNET/header/detail flow retained; upload only after fields
verify. Native file input and one start click, prove count+filename attached.
Ambiguous post-upload outcome stops without retry; page retained/notify existing
safe path. Local completion only after fields AND PDF upload confirmation.
Read real DOM only on owned page, no other user's tabs; real upload is authorized
but do not blindly reupload existing manually attached files/retro-clear receipts.
Offline focused/full/Ruff/diff, sanitized report/commit/push, Owner acceptance.

Implementation checks complete; Owner live upload acceptance and CEO review pending.
Focused145 PASS; full1831 PASS/1 SKIP (plus newly added selected-mail PDF extraction
case passed in final focused run); Ruff/diff PASS. No real upload/SMTP performed.

## Owner reported header stop: readiness correction
Owner test stopped at header, retained owned page still showed sales list/add,
no bill. Original precise reason was not persisted: UNKNOWN. Correct verified
code gap: attached iframe was treated as loaded list. Add bounded list and enabled
add-button readiness wait, no repeated menu/add; preserve all cancellation rules.
Map page-stage failures to safe specific labels instead of generic order-header.
No live business rerun; Owner retry after source GUI reload remains required.
Follow-up packet: tasks/2026-10-10-v14-sales-list-readiness-fix.md.
