# INSO LEO — current product contract

**Product:** Windows V1.6 assistant automating verified Google Sheets inquiry intake → market research → INSO procurement follow-up → quotation → TP requirement research → controlled notifications. The business truth is current source row + native INSO outcomes + persistent SQLite, **not GUI optimism**.

## Active policies

- Google: `INSO_QUOTE` with `2026`, `SHAHAB`, `RFQ_BRIEF` and `报价输入`; use exact original physical row/model/quantity/date/worksheet identity. `2026` may have a bounded legacy header block; **do not delete first four rows or shift row numbers**. W1 date-header proof remains authoritative for the dated source.
- Inquiry `未发` and quotation candidate `发给采购 / 采购已报价 / 已报价给客户` are distinct. New inquiry must be identified, researched, checked against prior INSO procurement and settled status **before** next stage. No forced automatic conversion from pending inquiry to quotation.
- Automatic inquiry and quotation: source date within **last 7 Shanghai calendar days inclusive**; automatic TP within previous calendar month with end-of-month clamping. Owner-selected manual single order waives **age only**, never source identity/status, permission or duplicate/UNKNOWN protections.
- Research queries the **original full MPN** across IC.net, Findchips, HQEW, LCSC, Bom.Ai and INSO; short suffix handling is only source-result matching. IC.net SSCP/ICCP eligible quantities at `<= 3 × order qty` are `货少`; otherwise `货多`; unavailable evidence is `待验证`, not 0.
- Each site has provenance/date and valid stock/price rules; valid current quotes and no-price truth stay distinct. No invented market price/stock/fx. TP and regular Research have separate lookback windows.
- Actual INSO Save-and-Send and Google status/brand/input/quotation writes require original authorization, positive receipt and durable fail-closed behavior. A request without independent effect confirmation is `UNKNOWN`, not `SENT/SAVED`.
- Quote input uses **exact 14 fields** and original authorized CDP `更新报价` button, with receipt/proven source and single-click guard. Owner 2026-11-13 removed **pre-click 14-cell readback only**, not cloud-write receipt/identity/UNKNOWN safety.
- Email/TP/independent mail use original persistent notification ledger and recipient policy; avoid duplicate `SENT/UNKNOWN`, false incident warnings and guessed historical reports. Optional detailed market enrichment has bounded wait and truthful reduced-content fallback.
- Existing inquiry, quotation and TP modules have their own 900-second cadence; full Start is **not** a safe single-order experiment. User-facing task center reflects actual source/business state separately from immutable historical effects.

## Where to read only as needed

[Module owner index](MODULE_INDEX.md) · [Sheets](modules/SHEETS.md) · [Workflow](modules/WORKFLOW.md) · [INSO](modules/INSO.md) · [Research](modules/RESEARCH.md) · [Current RFQ-016](../control-room/RFQ-016/TASK_SPEC.md) · [Original product policy chronology](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/docs/PRODUCT_BASELINE.md).

**V1.6 production API and one-order closure are still unverified** as of the last document-only CEO audit. Do not treat this policy summary as proof of live installation.
