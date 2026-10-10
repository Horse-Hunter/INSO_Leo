# RFQ-013 — REVIEW_REQUIRED

Owner PDF-upload increment on the existing V1.4 single-click pipeline; no deployment.

- Native attachments tab -> selected email PDF -> 开始上传 once. Original bytes
  are passed in memory to the native file input; no temporary customer file or Git
  artifact is created. Unique unencrypted parseable PDF required before research
  or INSO form mutation. Missing/ambiguous/invalid PDF stops without guessing.
- Success requires one queued original filename, success marker, 共1张/已上传1张
  status and visible matching persisted attachment link. Existing attachments or
  queues stop; unknown dispatch result never gets an automatic second start click.
- Local processed receipt is written only after all existing field readbacks AND
  upload confirmation. Failure remains retryable; Owner should inspect retained
  pages before retry after an uncertain upload. Existing receipts are preserved,
  not automatically reset or backfilled with uploads.
- Button remains single-shot and returns to idle; independently owned protected
  tab stays for manual review/save/submit/close. Older pages and inquiry/procurement
  state are untouched; canonical CDP/login/Vault paths are reused without changes.
- No Save, review-submit, polling, release build/deployment, Sheets/production
  workflow DB changes or real SMTP test. No real mail/customer/PDF data committed.

Verification: final focused145 passed; full safe/offline1831 passed,1 skipped;
Ruff and git diff --check passed. The selected-mail PDF extraction case added
while full regression ran is included in the final focused145 run.
Read-only owned-page DOM inspection confirmed native empty-panel selectors.
No real upload was performed by this increment's development tests; status/link
success predicates are tested with synthetic UI doubles and need Owner live
acceptance. Screenshots support the intended native workflow, not proof of this
code completing a real upload. Optional pypdf available in the source GUI's
bundled environment; unavailable parser stops safely rather than uploading blindly.

Changed implementation: order_mail/inspection, inso/sales_attachment,
launcher/sales_header; corresponding parser/UI/preflight tests and task/module docs.
CEO independent review and Owner actual-button acceptance remain pending.

## Owner header-stop correction — REVIEW_REQUIRED

Retained unique V1.4 page was still at sales list, not a bill form. Exact original
stop reason UNKNOWN because not persisted. Verified readiness race: iframe
attachment was followed by immediate list lookup; iframe navigation/control load
can complete later. Corrected to bounded15s wait for canonical visible list and
enabled unique add button before one add click. Cancellation/ownership rules,
fields/PDF/receipt/other-business logic unchanged. Page failures now distinguish
sales list loading/menu/add/form instead of generic order header.
Focused92 PASS, full1837 PASS/1 SKIP, Ruff/diff PASS; retained live owned list
passed read-only readiness probe. No add/upload/save/submit/SMTP/business replay
performed during correction. Owner source GUI reload authorized; real retry and
end-to-end PDF acceptance still pending, no deployment.
