# Task: V1.4 phase 1 order-mail inspection
status: complete
owner: Codex
created: 2026-10-10

## authority / goal
Owner authorizes split GUI buttons and one-shot read-only inspection of the 229
mailbox and real order attachments. Owner subsequently explicitly authorized
configuration of imap.qq.com in the existing encrypted Vault.

## baseline / reuse
Current repaired baseline: V1.3 REVIEWED_DONE fd7ce8665c65de3f0d1c18cf85369e8eff0a273c.
Original df64762 baseline was rejected by CEO B1 and is superseded. Owner
explicitly authorizes rebase; preserve Phase 1 and all newer V1.3 reviewed fixes.
Existing V1.3 trees/release remain untouched; reuse GUI, Vault and openpyxl.
No IMAP receiver exists. Minimal order_mail boundary owns read-only IMAP and
attachment structure; launcher assembles it and GUI displays sanitized results.

## scope / acceptance
- Equal left/right login and 自动订单录单 buttons; click once, check once.
- Verified TLS imap.qq.com:993; Vault only, exact authorized account.
- EXAMINE INBOX, recent bounded search, at most five candidates, BODY.PEEK.
- Verify before/after FLAGS; never STORE/MOVE/COPY/EXPUNGE/send/reply.
- Inspect header/MIME/body and Excel structure; PDF metadata only; no OCR.
- No raw customer values, subject, filenames, IDs or attachments in Git/logs.
- No INSO, Sheets, production DB, browser or existing SMTP changes.
- Synthetic tests, canonical live inspection, sanitized report; REVIEW_REQUIRED.

## UNKNOWN
Actual two-sample formats verified in control-room/RFQ-009/FINAL_REPORT.md.
Future global contract grammar and business mapping rules remain UNKNOWN.

## verification / completion
- status: complete (implementation); review: REVIEW_REQUIRED
- changed: GUI action row, optional GuiBackend capability, launcher worker,
  order_mail receiver/structure analysis, synthetic tests and scoped records.
- verified: live IMAP and actual GUI result flow; candidate FLAGS unchanged;
  focused128 plus final full1583 passed/1 skipped; Ruff and staged diff PASS.
- limitations: only two samples; PDF parser optional, XLS unsupported; no EXE
  packaging/deployment; global subject grammar and business mapping UNKNOWN.
- safety: no production INSO/Sheets/DB/SMTP operations; real data never staged.
- report: control-room/RFQ-009/FINAL_REPORT.md; independent CEO Review pending.

## B1 repair verification (2026-10-10)
Migration completed; code/test preservation comparisons PASS. Focused534 PASS;
full safe/offline1681 PASS/1 SKIP; Ruff/diff PASS. REVIEW_REQUIRED. Scope is baseline repair only, no functional
rewrite, dependency, real mailbox recheck, deployment or business write.
