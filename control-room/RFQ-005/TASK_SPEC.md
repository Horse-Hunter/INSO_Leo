# RFQ-005 — V1.3 Google quotation update pipeline

Owner request 2026-10-07; Executor implementation; independent CEO Review REQUIRED.
Status source: COORDINATION.md. Continue feature/v1-3 and the existing worktree.
Baseline: 5582df1fbc1d69b70925985cd2646a5882fd9792, RFQ-004 REVIEWED_DONE.

## Goal / inputs
Consume RFQ-004 V13QuotationResult only. QUOTE_FOUND proceeds to Google; return
NO_RECENT_QUOTE / ROW_FAILED unchanged without writes or clicks. Never requery
INSO, reselect/re-age quotation, or validate its business contents.

## Required closed loop
For each quote: original inquiry_id/record_identity -> fresh source check ->
write fourteen raw strings to the first quote-input row -> exact fourteen-cell
readback -> Google UI 更新报价 -> parse 报价更新完成 -> verify original source
采购已报价 -> close owned tab -> next result immediately.
Python must NEVER write source 采购已报价: only Apps Script's existing UI action
owns that change. No guessed script endpoint, arbitrary source writes or Save/Send.

## Payload / schema
Date/model/brand/quantity/currency/supplier rebate/quote/untaxed supplier price/
platform quantity/lot/lead-time/remarks/remarks2/creator, in RFQ-004 raw order.
Write all fourteen including empty strings, RAW not USER_ENTERED. Preserve dates,
leading zeros, trailing decimal zeros, whitespace/newlines, Chinese and odd/empty
business fields. Verify exact target headers first. Geometry must be centralized
explicit adapter config with no guessed default; missing sheet/schema/range is
shared failure. Pad omitted trailing readback cells with empty strings, never
trim or coerce. Re-read immediately before the click to prevent stale input.

## Retry / success / fault semantics
- Input write or exact readback failure: initial+3 full write/read attempts;
  exhaustion ROW_FAILED with fixed QUOTE_INPUT_WRITE_FAILED or
  QUOTE_INPUT_READBACK_MISMATCH. Never click on mismatched input.
- Update UI no popup/hang/unknown result: initial+3 attempts; each retry closes
  failed owned surface, opens fresh Google surface, rechecks source, rewrites and
  rereads all fourteen before another click. No 180s Google waits.
- Strict popup title 报价更新完成; parse labels/counts allowing display whitespace.
  成功填入1行 => UPDATED_INSERTED; 成功填入0行/已有报价1行 =>
  UPDATED_ALREADY_EXISTS. Zero/zero or unexpected counts/text is unconfirmed.
  Existing quote is normal idempotent success. Confirmed success never clicks again.
- Before any repeat, source already 采购已报价 => success without write/click;
  sent state may retry; other status/identity conflict => row-only SOURCE_CHANGED.
- After successful popup only read source: max3 reads, short injectable interruptible
  waits, no update retry. Final sent state => SOURCE_STATUS_NOT_UPDATED row failure.
- Use frozen RFQ-004 original-anchor/unique relocation with a minimal read-only
  extension accepting sent/quoted status; preserve original identity and UPDATED brand.
  Ambiguous/moved/conflicting rows are isolated; shared Sheets/auth/grant/schema/
  spreadsheet/ledger/CDP/session failures GLOBAL_STOP. Preserve human-needed page.
- No persistent interruption quarantine, new identity/schema, repair button or
  irreversible V1.2 submit engine. Rescan/repeat is permitted by idempotent Script.

## Boundaries / reuse
Reuse existing Sheets service/OAuth protected grants (non-interactive), row reader,
RAW API pattern, original ledger queries and single protected CDP/profile. Add only
narrow quotation input/UI/parser/service contracts; no generic browser framework.
No production access/write/update/Apps Script execution, SMTP, orders, scheduler,
GUI/mail integration, packaging/deployment or V1.2 EXE replacement during this RFQ.
Only fake/offline tests. Do not redesign RFQ-004 or alter V1.2 behavior.

## Acceptance / verification
All 45 Owner offline cases: input gating; raw14/order/empties; exact readback and
bounded retries; popup inserted/existing/zero/unknown/lost/hang; source status
poll/retry/identity/move/ambiguity; success-bad-success serial isolation; shared
faults; crash idempotency; RFQ-004 and existing V1.2 regressions. Fixed fake waits.
Focused pytest + full `python -m pytest -q tests`, `python -m ruff check src tests`,
`git diff --check`; scoped commit/push and actual local/remote HEAD equality.

## UNKNOWN / completion
Live-only input row/column/header geometry/gid, UI button/dialog DOM, Script delay
and Google session behavior remain UNKNOWN until separately authorized acceptance.
No fake result is live acceptance. Executor delivery ends REVIEW_REQUIRED, never
CEO PASS / REVIEWED_DONE. Exact evidence: EXECUTION_LOG.md / FINAL_REPORT.md.


## Executor delivery — 2026-10-07
Source/offline implementation completed, REVIEW_REQUIRED only. Focused154,
full1207/1, Ruff/diff PASS; exact commands and limits in EXECUTION_LOG.md.
No live actions/deployment. Geometry/UI/session UNKNOWNs remain explicit;
independent CEO verdict is not made by Executor.


## Owner correction / B1-B2 repair — 2026-10-07
真实 Google worksheet title 为 `报价输入`；此前“报价输入子表”为错误名称，
已修正，旧名称不作为 alias 接受。配置 gid 仍必须显式提供，不猜测生产值。
Existing Sheets service `spreadsheets().get` requests only
`sheets.properties(sheetId,title)` with `includeGridData=False`.
Exactly one title must equal 报价输入, its sheetId must be a nonnegative integer
(not bool/string/float), and str(sheetId) must exactly equal configured gid.
Missing/duplicate target, malformed metadata, mismatch or metadata/auth/API failure
raises sanitized QuotationInputUnavailable -> GLOBAL_STOP. Verify metadata before
fourteen headers; both must pass before opening the UI and before each RAW write.
No DOM title guess, business-cell metadata read, new adapter/config/OAuth path or
production gid. Existing RFQ-004 identity/read/retry and V1.2 behavior remain frozen.
