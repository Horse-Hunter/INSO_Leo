# RFQ-010: V1.4 Phase 2 sales header Owner review
Status: REVIEW_REQUIRED / independent CEO Review REQUIRED
Created: 2026-10-10
Authority: Owner instructions in this conversation; no deployment.
Base: V1.4 Phase1 REVIEWED_DONE b85d9c1; same development branch/worktree.

## Goal / scope
Read unique Excel-labelled PI No. starting SHAWN from only the two confirmed
229 order messages. Fill and verify sales-order header, stop at Owner review.
Reuse canonical9222/CDP/profile/acquire and InsoSessionGuard/Core Vault. No
new browser/login/credential/config implementation. Explicit page override
pins ordinary authentication to independently owned V1.4 tab.

## Requirements / acceptance
- Reuse exactly one marked V1.4 sales tab; never close it during development.
  Owner returns to sales list. Next invocation clicks native 新增单据; any
  existing-unsaved-document prompt uses 取消, never 确定 to allocate another XS.
- V1.2/V1.3 independent tabs and business execution continue concurrently.
  Parking/keepalive/default authentication must not navigate/close V1.4 page.
  Complete worker and release V1.4 busy state while retaining tab for review.
- Customer dropdown: first rendered candidate containing 阿尔克, not first
  overall candidate; never fill customer input. Fail if none, readback selected.
- Owner correction: always click/select RMB once even when already RMB, then readback.
- Payment款到发货; freight卖方付 + adjacent domestic delivery国内交货;
  shipping快递发货; destination广东惠州; customer order exact Excel PI No.
- Final reread all8 controls (7 logical fields including freight/delivery).
  Any mismatch stops with safe field-specific reason, no repeated correction.
- No lines/models/brand/quantity/price, PDF upload, save, review-submit,
  Google writes, SMTP, workflow DB changes, timer or deployment.
- Live navigation/dropdowns/header field edits authorized for only2 samples;
  minimize XS allocation, use same unsaved page only after Owner returns.
- Never commit customer/PI/contract data/raw mail/browser state/credentials.

## Verification
Synthetic tests for PI absent/multiple/label ambiguity, dropdown first matching,
RMB always-selection, every readback mismatch, prompt cancellation, tab isolation,
worker release and preservation during inquiry cleanup/authentication.
Focused + full safe/offline, Ruff/diff, bounded authorized live header validation.
Report8 requested points, limitations/UNKNOWN and REVIEW_REQUIRED, never CEO PASS.

## UNKNOWN
Live inquiry purchase/notification side effects were not authorized for this task;
concurrency proof uses independent authentication/cleanup and offline business workers.
