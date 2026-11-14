# RFQ-016 — CEO Review (2026-11-14)

**Verdict: `CHANGES_REQUESTED / REAL_ORDER_EXECUTOR_REPORTED / NOT_PROMOTED`.** Independently inspected GitHub source/tests/reports through `41a96f0d` (13 changes since `9ad9ccb8`); **no direct Windows, Sheet, INSO or SMTP session; no CEO test run**. Full technical review with rationale: [pinned detail](https://github.com/Horse-Hunter/INSO_Leo/blob/9d9181bdd876046e055d2122b6412012c7b41cf9/control-room/RFQ-016/REVIEW.md).

## What can be accepted as reported evidence

- **Inquiry 2026 / row 221:** `FT2232H-56Q-REEL`, Qty105. Executor recorded one INSO Save-and-Send followed by `RECONCILIATION_CONFIRMED_SAVED` / `rec_440fafd372440ecf9dacabf660dd155d`; API `A221:未发→发给采购`, `F221:空→FTDI`, SQLite `SAVED/PURCHASE_RECORDED`. No supplier quote: `NO_RECENT_QUOTE`, **0 quote-input writes, 0 quote clicks**; no mail for this order. No reason to rerun row 221.
- Deployed trial: Executor reports Google API enabled + production Editor, final EXE `E9E3DA33…` PID38948 and GUI 60 rows = 35 human-completed +24 purchased +1 invalid/header, 0 active V12 alerts. **3 legacy V13 quote holds remain**. These are *Executor observations*, not CEO live verification.
- Code contains bounded exact ERP customer row (ID4526000), purchase-action hint repair, source reconciliation, manual resync, calm GUI display, status column update and related tests. Executor reports `3349 PASS / 1 SKIP / 26 FAIL`; latest raw JUnit/failure-ID baseline and final EXE↔source manifest **not committed**; `TEST_REPORT.json` concerns older runs.

## P0: do not approve the new closure/recovery as safe

1. `src/workflow/v12_flow.py:65-77,306-343`: automatic “Owner finished in Sheet” reconciliation includes **`INTERRUPTED_POSSIBLY_SENT` and `STATUS_WRITE_PENDING`**, and calls `HUMAN_COMPLETED` without independently settling the underlying purchase/quote/outbox UNKNOWN. A human Sheet status change does not establish success of an uncertain external action.
2. `src/workflow/v12_store.py:270-303`: `HUMAN_COMPLETED` recovers **all** alert types, including `NOTIFICATION_FAILED`, regardless of ongoing real external-effect uncertainty. Historical rows remain, but active incident/GUI signal can vanish. `PURCHASE_RECORDED → DATA_QUALITY-only` is the safer pattern.
3. `src/launcher/backend.py:2150-2188`: right-click `resync` uses old physical row+completed status to `rebind_identity` (rewrites stored model/qty), sets `HUMAN_COMPLETED`, clears all alerts; no old-identity, quote/purchase/mail UNKNOWN or atomic cross-store guard. `tests/launcher/test_manual_order.py:45-61` **explicitly expects an entirely different part (OLD→FIXED-PART) to be rebound**. Row reuse can close the wrong order or hide a held effect.

**Fix:** add focused fake-ledger regressions first: UNKNOWN purchase and uncertain quote still held with active alerts after manual Sheet edit; failed-mail alert remains visible; resync rejects different article, reused position and old effect-hold; never clear real `SENT/UNKNOWN`. Reuse native guards; do not invent a second ledger. No production replay or forced stop merely to demonstrate tests.

## P1: status truth and evidence

- `src/launcher/source_status.py:92-103`: after exact relocation fails, display fallback accepts **any single row at the original position** as fresh/verified without model/qty/identity proof. If source row moves/is replaced, status may belong to another order. Test moved, replaced, duplicate and missing rows; show `来源待核对` when linkage unproven. Display-only does not make a false attribution harmless.
- `src/gui/workbench.py:206-216` still classifies settled but >15min old source as `需核对`, while its row colour can be calm; verify filter/count consistency.
- Commit raw final test IDs/baseline comparison, EXE provenance/release receipts and latest read-only operating state. No claim that 26 failures are irrelevant until verified.

## Residual run issues, action and governance

Open: quotation rerun refusal reason unrecorded; 12:00–12:04 GUI stale; paused-module close hangs (forced exits); orphan Chrome blank tab; old `inq_d65be9df…` recurrent quote-input failures. Preserve old V13 holds, Chrome9222, SQLite/WAL/SHM and rollback.

**Next single Executor:** inspect live PID/effects read-only, write 4–6 negative regressions, narrowly repair P0/P1 on existing `workbuddy/v16-rfq016-stabilization`; test and provide machine-readable evidence; then request `Review RFQ-016` again. Source code is **not yet merged into `develop`**. No automatic new EXE/real effects or `develop → main`: per [Owner branch policy](https://github.com/Horse-Hunter/INSO_Leo/blob/develop/docs/BRANCH_POLICY.md), deployed/long-running trial ≠ accepted current version.

[Executor report](FINAL_REPORT.md) · [live checkpoint](EXECUTION_LOG.md).
