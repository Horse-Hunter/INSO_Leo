# INSO — authenticated native procurement

**Owner:** `src/inso/` and original launcher session composition. Reuse one Chrome `127.0.0.1:9222`/protected profile, authenticated shell and existing page ownership; never build another UI or HTTP purchase path.

1. **Login/readiness:** navigate through original INSO login/home and native business-inquiry menu (do not jump directly to inner `List.aspx`, which lacks purchase dialog owner). Verify correct site, authenticated list frame, fresh session and exact MPN. Human verification/OTP stays human; preserve their pages and do not silently bypass.
2. **Duplicates:** original `采临时询价` lower area, not upper business history, provides seven-day procurement duplicate evidence. Iterate native pages and validate complete result/ID count; incomplete/history-error ≠ no duplicates.
3. **Draft:** original full source MPN, approved Brand, Qty and identity; review the AI generated row. ERP fills native part fields/product code via original client-side `保存数据`; do not manually write server purchase cells or treat that UI button as final save.
4. **Effect:** only reviewed original native `保存并发送` gate is allowed for a specifically authorized real order. Durable pre-dispatch uncertainty protection precedes native action. Distinguish client preview, Save click ack, independently confirmed saved purchase and any `SUBMIT_UNCONFIRMED/UNKNOWN`. Timeout/restart is not permission to click again.
5. **Reconcile:** original query/receipt/record ID, source-row status and SQLite ledger; if the result is ambiguous, preserve hold and halt downstream effects. Do not report a successful purchase from a button click alone.
6. **Session interruption:** predecessor's agent window ending does not stop the INSO browser or application. Check live process/owned tabs and external purchase history before taking action.

**History and implementations:** `src/launcher/inso_session.py`, `src/inso/purchase_writer.py`, `src/inso/duplicate_history.py`. [Detailed historical native contract](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/docs/modules/INSO.md) · [CDP](../CDP_SESSION_POLICY.md) · [RFQ-016](../../control-room/RFQ-016/TASK_SPEC.md).
