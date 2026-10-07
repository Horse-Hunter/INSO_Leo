# V1.3 live closeout and robustness

status: review_required
owner: Integration Executor
created: 2026-10-07

## Goal
Finish previously authorized V1.3 work in feature/v1-3-integration: preserve reviewed RFQ-006
and approved RFQ-007 increment, finalize Owner-directed supplier-net selection and actual
Google button/result path, verify robustness, build and deliver reviewable source/release.

## Approved baseline
RFQ-007 reviewed HEAD2c9f704 (implementation7f8f58e, CEO PASS bfcae14) fast-forwarded
from RFQ-006 reviewed2a32007; prior live changes restored without conflict. No redesign.

## Current Owner requirements
- Exact MPN within real inclusive72h: lowest strictly-positive eighth-column supplier net price
  converted through existing official FX; newest tie, first stable equal-time tie.
- If only valid zero prices, use newest zero. Skip invalid/negative; raw14 preserved unchanged.
- Sixth field is actual 供方税点. No production test-clock override or date mutation.
- Verified unique visible drawing on metadata-bound headerless 报价输入!A1:N1; fixed Chrome/CDP.
- Bounded readiness30s before writing/clicking; result modal wait30s, no fixed sleeps/coordinates.
- Actual modal 更新完成 / 成功填入 / 已有价跳过, strict single-row counts.
- Latest Owner rule supersedes unconditional existing-price completion: inserted1 or skip1
  confirms Script success, then both require source 采购已报价 within30s. Otherwise retain
  SOURCE_STATUS_NOT_UPDATED durable barrier, log warning, pale-yellow GUI and owner229 mail.
  No source status write or repeated update to force closure.
- Dismiss result, then wait for Script running notice to end before next row; Script alone clears
  input. No agent clear/delete. Unconfirmed settlement globally stops and preserves page.
- Preserve RFQ-007 alert/cooldown, B1, holds, shared fault safety, websites229, identities,
  durable purchase receipt/no resend, V1.2-only180s, combined15min and manual challenges.

## Boundaries
Previously authorized one existing DRV8833PWR live update was verified once; do not repeat it,
run full scheduler, replay history, buy, Save/Send or send SMTP as acceptance. No Script editing
or direct invocation, credentials/profile/cookie changes or new browser/architecture.
New-insert live behavior remains UNKNOWN unless separately Owner-authorized. Source/release
verification may proceed; preserve existing runtime/config and V1.2 bytes during any release work.
Independent review of this new incremental code remains REQUIRED, never self-mark REVIEWED_DONE.

## Verification
Focused quotation read/update/button/parser/workflow/backend/GUI; full safe/offline with SMTP guard;
Ruff, diff review/check; canonical BuildOnly, frozen self-check and release scan; delivery hashes,
source/remote equality and clean worktree. Record actual live skip separately from offline tests.

## Delivery evidence
Implementation complete. Final focused462 PASS; full1393 PASS/1 SKIP; Ruff/diff PASS.
V1.3 BuildOnly/frozen/scan/idle PASS, no installed release overwrite pending independent review.
See control-room/RFQ-006/FINAL_REPORT.md for scope, actual live evidence and remaining UNKNOWN.
