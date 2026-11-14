# RFQ-016 — live execution checkpoint (not historical diary)

**Last refreshed: 2026-11-14 12:20 (Asia/Shanghai) by the single Executor after a live single-order run.** Everything in §1 was re-observed on the production Windows host during 11:17–12:07 today by this window; nothing below is inherited from an earlier report. Historical diary: [immutable reference](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/EXECUTION_LOG.md).

## 1. Current facts (live-observed)

| Area | Now |
| --- | --- |
| Git / source | Branch `workbuddy/v16-rfq016-stabilization`, based on `9ad9ccb8` (CEO doc compaction) with this run's three fixes on top. Original worktree reused; `main` worktree's pre-existing untracked material untouched; no second worktree created. |
| Installed EXE | `dist/INSO_V1.6/INSO_V1.6.exe`, SHA256 `197EC23B951D0E8B4579B3598DC7A7DC7770F0EBCBFFC2215D647E7233558BE9`, 8 415 515 bytes. Program **running**, PID `26604`, window title normal. Rollbacks: `dist/release-backups/INSO_V1.6-customer-20261114T113817Z` (old EXE `b357889d…`) + `_internal.prev-20261114T113817Z / T114438Z / T115600Z`. |
| Production API | `runtime/production.json` has `google_api.enabled=true` with the key outside the repo; `--api-self-check` on the deployed EXE = `TRANSPORT_READY`; reads and writes both travelled the Service Account, never CDP. |
| Google ACL | Owner granted **Editor** on `INSO_QUOTE` at ~11:19; measured by probe (403 at 11:04 → real `UpdateValuesResponse` at 11:20 on a proven-empty cell). |
| Source row | `2026` row `221` `FT2232H-56Q-REEL` qty `105`, class `C`, customer `Customer`, W quote date `2026-11-13` (inside the 7-day window). **Now status `发给采购`, brand `FTDI`** (was `未发` / blank). |
| External results | INSO purchase **saved and reconciled** (`SAVED`, `rec_440fafd372440ecf9dacabf660dd155d`); Google status+brand written; **no mail** for this order; quotation evaluated `NO_RECENT_QUOTE` → no `报价输入` write, `更新报价` clicked **0** times. |

## 2. Mandatory check before any further effect

1. Re-read `git branch --show-current`, `git rev-parse HEAD`, `git status --short`, `git worktree list --porcelain`; keep the existing worktree and any unknown dirty state.
2. Confirm PID `26604` is still the only INSO process and read its fresh log before starting anything; keep Chrome `9222` / `chrome-profile` untouched.
3. SQLite read-only: `workflow_items`/`inquiry_state`/`purchase_state`/`v13_holds`/notifications for `inq_e15970df104e170d93b4169b`; Google row 221 and `报价输入`; INSO purchase record.
4. Any new external effect still needs its own authorization; a tool/Computer-Use permission is **not** a business permission.

## 3. Checkpoint

**Pre-action (11:57:38).** Authorization: Owner's 10:33 config note (`quotation_live_acceptance`, single controlled order, 2026 row 221, API path) plus explicit Owner scope choice at 11:10 (**whole-program run, quotation included**). Pre-state: row `未发`, brand blank, no purchase, no hold, no mail, no SQLite row 221 before 11:17; INSO session freshly restored by the Owner; SA Editor proven. Plan: one single-order purchase retry through the canonical entry, then let the scheduled quotation cycle evaluate the row.

**Receipt (11:59:10–11:59:19).** `AI_RECOGNITION_READY` → `SAVE_DISPATCH_ARMED` → `SAVE_CLICK_COMPLETED` (**one** click) → immediate read inconclusive, so the program raised `SAVE_OUTCOME_UNKNOWN` instead of assuming success → `RECONCILIATION_STARTED` → **`RECONCILIATION_CONFIRMED_SAVED`** → `PURCHASE_DATA_SAVED` → `ALERT_RECOVERED`. Independent observation: Google `A221` = `发给采购`, `F221` = `FTDI` (API read-back), ledger `SAVED` with the record ref above.

**Quotation (12:05:46).** Scheduled cycle evaluated the row and returned `NO_RECENT_QUOTE` — INSO has no supplier quote yet, so there is nothing to write. `报价输入` untouched; `更新报价` never clicked. This is `NOT_DONE_BY_BUSINESS_RULE`, not a failure.

**Other orders.** No order received a confirmed quotation write today (no `UPDATED_*` result at all; only age-skips, "no new quote", "price unchanged"). The six `QUOTE_INPUT_WRITE_FAILED` results all belong to the pre-existing held order `inq_d65be9df…` and remain an unresolved earlier incident. The task centre's red/amber rows are all historical (2026-10-01…2026-11-13); today updated exactly one order — this one — and it is now a normal `PURCHASE_RECORDED`.

**Status:** `DONE` for inquiry+purchase+Google sync, `NOT_DONE_BY_BUSINESS_RULE` for quotation, `NO_UNKNOWN_EFFECT`. **Next single action:** let the running program's quotation cycle re-evaluate row 221 after INSO receives a supplier quote; if it does, the existing safeguards write `报价输入` and click `更新报价` once.

**Owner-resolved backlog reconciled (12:33–12:39).** The Owner reported having already advanced most red/amber rows by hand in the sheet and asked for them to clear automatically. Root cause of why they never did: the only reconciliation rule accepted exactly `发给采购` **and** an unchanged brand, via `current_purchase_status`, and it was limited to `INTERRUPTED_*`. Live check: **32 of 36** review rows already carried a completed status (`发给采购/采购已报价/已报价给客户/成交`). Fix: `owner_resolved_status` narrows the worksheet to completed-status rows, restores the status cell, and reuses the canonical relocation (which already ignores Brand and matches one unique importance/model/quantity snapshot) — so a manual status/brand edit and a moved row are tolerated, while an ambiguous or changed article still fails closed. `discover_pending` now applies it to every state parked for a human decision, closes them as `HUMAN_COMPLETED`, and `set_business_state` recovers the alerts that close answered. A second, narrower rule clears alerts a finished order can no longer act on (`HUMAN_COMPLETED`: all; `PURCHASE_RECORDED`: `DATA_QUALITY` only — never a mail/notification alert). Measured effect on the first cycle: review rows **33 → 5**, `HUMAN_COMPLETED` 1 → 30, active alerts **16 → 0**. Build `D4281F48…` deployed with rollback `_internal.prev-20261114T123900Z`; `tests/workflow + tests/sheets + tests/inso` = 1636 passed / 1 skipped, ruff clean.

**The five that stay open, and why.** `2026` r101 — the sheet holds **two rows** with the identical model/quantity (`PI7C9X2G404EVAZXAEX`, 1000), so relocation is ambiguous and the program refuses to guess; r146 — a table header row (`MPN`) was once admitted as an order and can never be proven resolved; r204/r205/r206 — the sheet's model text moved on (`N6210` → `CELERON-N6210`, `I7-12700TE` → `I7-12700TE/I7-12700T`, `4210` → `XEON-SILVER-4210`), so the ledger cannot prove the article. These need a human decision, not a wider matcher.

**Known, not fixed here.** `重跑报价流程` refused at 12:00:42 with no persisted reason; the GUI stopped refreshing its display between 12:00 and 12:04 (process alive, UI stale); `request_stop_after_cycle` does not set the stop flag while `MODULE_PAUSED`, so closing the window in that state never drains (forced stop three times); one orphan `about:blank#INSO_CREATE:…` page remains in the browser; the `inq_d65be9df…` quote-input failure recurs every cycle.

## 4. Historic evidence (immutable links)

[Full original execution log (988 lines)](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/EXECUTION_LOG.md) · [Historical final reports](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/FINAL_REPORT.md) · [API feasibility](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/GOOGLE_API_FEASIBILITY_2026-11-13.md) · [header/read evidence](../../docs/evidence/v16/rfq016-phase3-production-parity-2026-11-14.json) · [current Review](REVIEW.md) · [CEO takeover card](../CEO_HANDOVER.md).
