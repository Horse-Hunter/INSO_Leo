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

## Latest Owner recipient correction / 2026-10-10
Order-entry exceptions only go to229, not shawn. Explicit exception to prior
recipient-no-change scope: V1.4 order_notifications only; all other routes unchanged.
Owner-only transport guard blocks historical queued non229 recipients when revised
service loads, without rewriting immutable command payload. No live queue mutation
or mail test. Add routing/legacy queue regressions and consolidated CEO report.
Remain REVIEW_REQUIRED; packaging only after CEO PASS and new Owner instruction.

Recipient correction complete: focused67 PASS, final full1846 PASS/1 SKIP,
Ruff/diff PASS. CEO_REPORT.md is consolidated review packet. No package/deployment,
GUI restart or live SMTP performed. Active loaded code requires later reload.
