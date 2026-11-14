# RFQ-016 — recoverable checkpoint after CEO review 04222709

**Branch:** `workbuddy/v16-rfq016-stabilization` (existing worktree, no second worktree). **HEAD before this round:** `04222709295a6a5fbfc9b33f0485cc0ccd9a9aa1` (clean). **Code commit:** `abf95cf0f6db5ae6e6b9624edb4359ffcc1e249e`. **Docs/evidence commit:** this branch head after the docs commit. **No deployment and no new real business action.**

## 1. Takeover audit (read-only, 2026-11-14 15:44–15:50 Shanghai)

- Git: existing worktree `D:\Program_Leo\INSO_Leo\.worktrees\v16-rfq016-stabilization`; `git status --short` empty before edits; no stash; no second worktree; `main` worktree untouched.
- Running production program: `dist/INSO_V1.6/INSO_V1.6.exe`, SHA256 `E9E3DA33417414ABAC53F8A88A67D9F053BCDAEAB9730EAE9AD8BD7870DFFAD0`, 8 422 619 bytes. PID `38948` (`--start-inquiry`) plus its watcher PID `34304` (`--watch-runtime 716 86030824867e430d81c366c4e6a9f60a ...`), started 13:47:50, runtime state `phase=gui`, `gui_ready`.
- SQLite (read-only URI): `dist/INSO_V1.2/runtime/production/workflow.sqlite3`; 60 orders = 35 `HUMAN_COMPLETED` + 24 `PURCHASE_RECORDED` + 1 `INVALID_INPUT_SKIPPED`; **0 active V12 alerts**; **3 active V13 quotation holds** (`inq_d65be9df...`, `inq_71f4a2f5...`, `unresolved:0ca37229...`); WAL/SHM untouched.
- Chrome: only `127.0.0.1:9222`, owner PID `24164`; profile untouched.
- Row 221 preserved: `inq_e15970df104e170d93b4169b` = `PURCHASE_RECORDED`, purchase `SAVED`, receipt `rec_440fafd372440ecf9dacabf660dd155d`. **Not re-ordered, not re-quoted, no mail.**
- **No real action in this round:** no Sheets/INSO/SMTP write, no EXE replacement, no process stop, no Chrome kill, no UNKNOWN/hold clear, no DB restore. No Computer Use and no GUI click were used; every live fact above came from read-only PowerShell/Python and SQLite `mode=ro`.

## 2. P0/P1 source fixes

File list: `src/workflow/v12_flow.py`, `src/workflow/v12_store.py`, `src/launcher/backend.py`, `src/launcher/source_status.py`, `src/gui/contracts.py`, `src/gui/workbench.py`, `src/gui/app.py`.

**P0-1 — manual Sheet status cannot settle an unconfirmed external effect.**
- `_NEVER_AUTO_CLOSED` forbids automatic closure of `INTERRUPTED_POSSIBLY_SENT`, `STATUS_WRITE_PENDING`, `SUBMIT_UNCONFIRMED`.
- `PURCHASE_EXCEPTION` closes automatically only when the durable purchase outcome is settled (`SAVED`/`CONFIRMED_NOT_SAVED`/`VALIDATION_FAILED`).
- An active V13 quotation hold (`V13HoldStore.blocks_inquiry_retry`) blocks the same manual-sheet closure.
- `HUMAN_COMPLETED` now clears only `DATA_QUALITY` alerts, plus `PURCHASE_EXCEPTION` when the purchase is settled. `NOTIFICATION_FAILED`, security, duplicate and any unknown-effect alerts stay active; notification recipients/`SENT`/`UNKNOWN` rows are never changed.

**P0-2 — right-click “按表格恢复状态” revalidates identity and effects.**
- Reads the physical row and requires a completed status.
- Requires the row to match the stored article uniquely: model equal or a documented completion of the model text, same quantity, same importance; brand/status are mutable.
- Refuses a different article, a reused position, a duplicate line, an unresolved purchase (`UNKNOWN_WRITE_OUTCOME`/`READ_ONLY_RECONCILIATION_REQUIRED`/`MANUAL_REVIEW`/`SUBMIT_UNCONFIRMED`) and any active V13 quote hold.
- Re-points the ledger only after those checks; clears only answered alerts; never clears SENT/UNKNOWN.

**P1 — status column truth.**
- Removed the “any single row at the old physical position is fresh” fallback.
- Display attributes a status only through exact relocation or one unique article match across the worksheet; two orders cannot claim one line.
- Otherwise the DTO carries `source_link_unproven=True`, `source_status=None`, and the GUI shows **「来源待核对」** instead of another order's status.
- Calm/settled rows older than 15 minutes are no longer counted as “需核对” while painted calm; unproven links are counted and painted `warning`.

## 3. Tests and baseline reconciliation

The baseline was run on the untouched `04222709` tree before any edit:

- Command: `python -m pytest tests/workflow tests/sheets tests/inso tests/launcher tests/gui -q --junitxml=.tmp/baseline-tests.xml`
- Result: **3376 collected, 3349 passed, 1 skipped, 26 failed** (308.5 s).
- The exact 26 node IDs are stored in `docs/evidence/v16/rfq016-ceo-fix-2026-11-14.json`.

The final run after the fixes (frozen tree):

- Result: **`3397` collected, `3370` passed, 1 skipped, 26 failed**.
- The 26 failed node IDs are byte-for-byte the same as the baseline. They are the pre-existing `_document_barrier` / `_GoogleDocumentBarrier` / `google_resource_barrier` / `google_resource_holds` / shared page-admission baseline; none is in a module changed by this round, and no new failure was introduced.
- New regressions: **21 cases** covering unknown purchase closure, active quote hold, failed-mail alert retention, settled-purchase closure, resync rejection of a replaced row/unknown purchase/quote hold, pre-save exception, unproven/moved/duplicate/missing source rows, and GUI “来源待核对”.
- `python -m ruff check src tests` and `git diff --check` pass.
- The prior safety tests were tightened, not deleted/skipped: the armed `INTERRUPTED_POSSIBLY_SENT` case now asserts it stays open and red; the four owner-reconciliation cases use a safe state, with the unsafe ones moved to the new P0 regressions.

## 4. Historical risk found, not modified

`inq_99275e8e72b43fd6616fd686` (SHAHAB row 115, model `550BG125M000DG`, qty 8) has durable purchase `MANUAL_REVIEW` / `RECONCILIATION_UNREADABLE` with `SAVE_DISPATCH_ARMED` (2026-10-06), but its V12 state is `HUMAN_COMPLETED` and its `SAVE_OUTCOME_UNKNOWN` alert was recovered at `2026-11-14T04:39:40.712712+00:00` by the previous auto-close. This is the exact class of unsafe closure the CEO flagged. It predates this round; **this Executor did not write production data**. The new code would not close this pattern automatically. A separate read-only reconciliation / Owner decision is required before any state change.

- Residual limitation: a Google Sheet has no stable row ID. If the old line is replaced in place by an identical model/quantity/importance line, the cell snapshot cannot distinguish it; duplicate candidates are treated as ambiguous when the original anchor no longer matches. No such case was observed this round.

Also preserved and not cleared: the 3 active V13 holds, the old `inq_d65be9df...` quote-input failure, and the previously recorded orphan blank CDP tab, quotation-rerun refusal, GUI freeze interval and paused-module close defect (not re-inspected this round).

## 5. Resume / next action

1. This worktree, branch and source commit are authoritative; do not create a second worktree or touch the running EXE without separate authorization.
2. Re-run the exact command above and compare the 26 baseline node IDs before any new change.
3. If a new failure appears, stop and review; do not “fix” by deleting/skipping tests.
4. Real deployment, INSO/Google/SMTP effects, UNKNOWN resolution or reopening the historical row need a new explicit Owner authorization.
5. **Next single action:** CEO independent review of the source/test/evidence, then decide whether to build a new EXE for a trial run.

Immutable prior logs: [41a96f0d execution log](https://github.com/Horse-Hunter/INSO_Leo/blob/41a96f0dd31e815065dce379fadc02aa6c0f86f8/control-room/RFQ-016/EXECUTION_LOG.md) · [988-line diary](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/EXECUTION_LOG.md).
