# RFQ-009: V1.4 phase 1 order email discovery
Status: REVIEW_REQUIRED / independent Review REQUIRED
Owner authority: 2026-10-10 explicit user instruction.

Canonical task packet: tasks/2026-10-10-v14-order-mail-inspection.md.
Scope: equal split GUI action buttons, one-shot 229 read-only IMAP and actual
attachment structure inspection. No polling or business field mapping/entry.
Baseline: V1.3 REVIEWED_DONE fd7ce8665c65de3f0d1c18cf85369e8eff0a273c; codex/v1-4-order-mail-inspection.
Acceptance and safety: see task packet. Owner explicitly authorized storing the
provided IMAP auth code through existing encrypted Vault. Never record the value.
Finish REVIEW_REQUIRED with sanitized ten-answer CEO report; never executor PASS.

## B1 repair authority — 2026-10-10
Owner requests safe rebase/cherry-pick of the existing Phase 1 increment onto the
exact baseline above. Preserve IMAP/GUI semantics and newer V1.3 safety fixes;
never replace new files wholesale with old files. Focused + full safe/offline
regression, no deployment. Preserve CEO_REVIEW.md as historical verdict and
resubmit REVIEW_REQUIRED; no new live mailbox/business verification needed.

## B1 resubmission
Rebase complete. Phase1 code/test preservation and V1.3 inheritance comparisons
PASS; focused534 PASS; full safe/offline1681 PASS / 1 SKIP; Ruff/diff PASS.
No deployment. Historical CEO verdict unchanged; independent re-review pending.
