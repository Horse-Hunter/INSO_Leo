# Sheets — current V1.6 contract

**Owner:** `src/sheets/`; production wiring: `src/launcher/backend.py`, `src/launcher/google_web.py`, `src/launcher/google_quote_update.py`. One configured transport (API when explicitly enabled, otherwise old CDP), not two independent writers.

## Source and identity

- `2026` and `SHAHAB`: exact schema/status/model/brand/quantity and original physical row; preserve all raw data including empty/`None` normalization and model leading zeros. Bounded legacy top-header detection in both adapters; do not remove top 2026 rows or rebase row numbers. `2026` W1 `quote_date` proof remains attached to correct physical source row.
- `RFQ_BRIEF`: independently bound dated/target-price evidence, no invented identifiers. `报价输入` is the **only** correct worksheet name for quotation input; 14 strict cells and actual known gid/range.
- Pending inquiry status exactly `未发`; quotation status exactly `发给采购 / 采购已报价 / 已报价给客户`. Current state is reread; immutable purchase history does not prove current source status.

## Writes and transport

- API requires `production.json.google_api.enabled=true` and `service_account_file` outside Git. `--api-self-check: TRANSPORT_READY` is **only** import/auth construction; read actual production doc and test Editor/whole-workbook permissions separately. SA Reader in prior report was only Viewer.
- A single-cell brand/status write is tightly scoped (fresh identity + blank/status gate), with matching document/range/cell-count receipt and independent readback where required. Uncertain outcome = persist hold, no automatic rewriting.
- Quotation input: exactly 14 RAW cells; check correct workbook/gid/range, positive write receipt/cloud save, and safe browser handoff. Owner removed **pre-click 14-cell readback**, *not* the exact write receipt or single-click/UNKNOWN protection. The only CDP operation retained for Google quotation is original `更新报价` button.
- Read-only transient Google/CDP errors recover within original bounded policy without unsupported website-wide stops or false SMTP alerts. Unknown writes, ambiguous target ownership, missing identity or script effects always fail closed. No broad retries after a potentially dispatched API write.
- Preserve original protected Chrome `9222` for remaining button/legacy code; API itself creates no second Chrome. Credentials/tokens must never enter Git or logs.

**Tests / source:** `tests/sheets/`, `tests/workflow/test_rfq016_api_chain.py`. [Active RFQ-016](../../control-room/RFQ-016/TASK_SPEC.md) · [current Review](../../control-room/RFQ-016/REVIEW.md) · [historic detailed Sheets rules](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/docs/modules/SHEETS.md).
