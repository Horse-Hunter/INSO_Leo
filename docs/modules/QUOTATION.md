# Quotation — native result classification

This is **not a separate scheduler**. `src/quotation/update_result.py` parses the original native `报价更新完成` result into `INSERTED / ALREADY_EXISTS / UNCONFIRMED`; malformed/zero/ambiguous counts do not prove success.

Workflow coordinates exact source status/identity, original `报价输入` 14 RAW cells, Google receipt, **at most one** approved CDP `更新报价` click, read/parse of the result, durable UNKNOWN hold and later source reconciliation. A `未发` pending inquiry does not by itself qualify as a quotation candidate. Owner 2026-11-13 removed pre-click 14-cell readback **only**, not source identity, receipt verification or unknown write safety.

[Detailed historical result and worksheet naming rules](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/docs/modules/QUOTATION.md) · [Sheets](SHEETS.md) · [Workflow](WORKFLOW.md).
