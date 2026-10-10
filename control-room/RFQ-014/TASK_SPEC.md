# RFQ-014 SMTP message clarity review
Status: REVIEW_REQUIRED
Owner: 2026-10-10 requests all mail to229/shawn, including single-recipient mail.
Base79a4ee1a5a244425f43ea26e726fa7d6b6b69fd0.
Scope: inspect all SMTP entry points/templates, simplify subjects/bodies, remove
internal IDs/reason codes/English implementation labels/repetitions. Preserve
necessary business identity/location, factual uncertainty, actual status and action.
No triggers/rules/recipient/dedup/retry/transport/SMTP credentials/schema changes.
No queue rewriting, production access, live email, deployment or GUI auto-start.
Keep immutable already-created messages; edits apply to future messages after reload.
Task context supersedes earlier no-old-code-edit solely for mail copy authorized here.
Focused rendering/routing/dedup and full safe/offline regression, preview/report,
review diff, commit/push on existing V1.4 branch; REVIEW_REQUIRED.

Completion:11 categories/19 synthetic previews audited; focused292 PASS plus8
final action-copy cases; final full1845 PASS/1 SKIP; Ruff/diff PASS. CEO independent
review pending. No current GUI reload/release or already-created-message rewrite.
