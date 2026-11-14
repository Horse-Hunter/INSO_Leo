# RFQ-018 — execution log

- **Status:** `REVIEW_REQUIRED / OFFLINE_REPAIR_DONE / NOT_DEPLOYED / NOT_MERGED`
- **Window:** 2026-11-14 17:25– Shanghai
- **Worktree:** `D:\Program_Leo\INSO_Leo\.worktrees\v16-rfq016-stabilization` (reused)
- **Branch / starting HEAD:** `workbuddy/v16-rfq016-stabilization` / `aad3b122`
- **Business source baseline:** `b45e870e` (RFQ-016 final P1-E)
- **TASK_SPEC:** [TASK_SPEC.md](TASK_SPEC.md)

## 1. Takeover audit (read-only)

- Read `origin/develop` `AI_START_HERE.md`, `AGENTS.md`, `control-room/CEO_HANDOVER.md`, `control-room/COORDINATION.md`, `RFQ-017/REVIEW.md`, `RFQ-017/RELEASE_READINESS.md`, `RFQ-017/AUDIT_REPORT.md`, `RFQ-017/TASK_SPEC.md`, `docs/BRANCH_POLICY.md`, `docs/SAFETY.md`, `docs/REPORTING.md`.
- Fetched `origin/develop` and `origin/workbuddy/v16-rfq016-stabilization`; local branch was one docs-review commit behind and was fast-forwarded to `aad3b122` (CEO RFQ-017 Review). No source/test changes in that commit; no merge, no branch creation.
- `git status --short` empty before edits; no stash; no second worktree; root `main` worktree untouched.
- Live scene: `dist/INSO_V1.6/INSO_V1.6.exe` SHA256 `E9E3DA33…`, app PID 38948 (`--start-inquiry`), watcher PID 34304; Chrome `127.0.0.1:9222` owner PID 24164.
- SQLite read-only: 60 orders = 35 `HUMAN_COMPLETED` + 24 `PURCHASE_RECORDED` + 1 `INVALID_INPUT_SKIPPED`; 0 active V12 alerts; 3 active V13 holds (`inq_71f4a2f5…`, `inq_d65be9df…`, `unresolved:0ca37229…`).
- Row 221: `inq_e15970df104e170d93b4169b`, `PURCHASE_RECORDED`, `SAVED`, receipt `rec_440fafd372440ecf9dacabf660dd155d`; not re-ordered.
- SHAHAB/115: `inq_99275e8e72b43fd6616fd686`, `HUMAN_COMPLETED`, `MANUAL_REVIEW / RECONCILIATION_UNREADABLE`, no saved receipt; left isolated.
- No real Sheets/INSO/SMTP/Google/CDP write, no deployment, no restart, no hold clear, no DB write. Only read-only PowerShell/Python and local fake pytest.

## 2. Authorization and design checkpoint

Owner authorized **offline source modification and simulated tests only**. No deployment, real business operation or version promotion. This round may edit `src/` and `tests/`, but must not touch live assets.

Reuse decision:

- **Single shared mechanism:** extend the existing `PageResourceAdmission` (`src/research/cdp_pages.py`) with a process-local **document write hold** map. No second database/file/scheduler/manager.
- Root admission owns the holds; child admissions inherit/see parent holds; a hold recorded via any child propagates to the root so sibling services cannot bypass it.
- Holds are **not automatically released**. A process restart/new runtime is the in-memory release boundary; existing durable V13 quotation holds remain independent and authoritative for the same quotation.
- Reads remain allowed; only writes to the same Google document are blocked.
- Cover three write paths: CDP quote/script actions, browser `GoogleSheetsWebService` fallback writes, and Sheets API writes.
- Sales/order-mail: require the same admission before `acquire_cdp_browser`; bind it before page creation; backend passes `self._page_admission`.

Planned red regressions (to be written before implementation):

1. `PageResourceAdmission` root/child document hold blocks `require_document_writable`; read path unaffected.
2. Quote action with an unconfirmed click/script holds the document; a second client/new scope cannot open a writable page for the same document, including another sheet.
3. Browser fallback write is blocked after a document hold.
4. API write is blocked after a document hold and holds on an uncertain write.
5. Sales preflight without admission returns `STOPPED` before `acquire_cdp_browser`.
6. Sales preflight with invalid admission returns `STOPPED` before `acquire_cdp_browser`.
7. Sales preflight with valid admission binds it on the browser before `new_background_page`.
8. Backend order-mail worker passes `self._page_admission`.
9. Existing RFQ-017 gap repros (#13/#14/#15/#21/#26) pass or are superseded by the stricter tests above.

## 3. Test-first checkpoint

**Baseline retained:** the exact 26 RFQ-017 nodeids (dotted form) are in `docs/evidence/rfq017/...json` and `docs/evidence/rfq018/...json`; no nodeid was deleted or skipped.

**Red run before wiring (new tests only):**

```text
python -m pytest tests/research/test_shared_document_admission.py tests/launcher/test_rfq018_shared_safety.py -q --tb=short
7 failed, 6 passed
```

The 6 passing were the admission unit tests after the minimal admission methods were added; the 7 wiring/gap tests failed exactly as expected (no shared hold, no sales gate, no backend propagation). The additional 3 API/browser hold tests also failed red (constructor lacked `page_admission`; browser write was not blocked):

```text
tests/sheets/test_google_api_service.py::test_api_write_is_blocked_by_shared_document_hold
tests/sheets/test_google_api_service.py::test_uncertain_api_write_records_the_shared_document_hold
tests/launcher/test_google_web.py::test_browser_write_is_blocked_by_shared_document_hold
3 failed
```

Total new tests: 16 (10 red before wiring, 6 admission unit).

**Implementation (minimal, existing mechanisms):**

- `src/research/cdp_pages.py`: one root-owned `_document_holds` map on `PageResourceAdmission`; `hold_document` / `release_document` / `document_hold` / `require_document_writable`; child→root propagation; page-closed pruning; `DocumentWriteHeld`; canonical Google document keys.
- `src/launcher/google_quote_update.py`: every write action requires the shared admission; unresolved click/result/settlement/page-protected paths publish a document hold; close-time protected entry publishes/retains it; settlement releases only the exact owned page; owner adoption/identity mismatch cannot release.
- `src/launcher/google_web.py`: browser fallback writes bind the admission and are blocked by a document hold; a dirty uncertain write publishes the hold.
- `src/sheets/google_api_service.py`: API writes bind the production builder's admission, check the document hold before writing, and publish it on an uncertain/receipt-unproven write.
- `src/sheets/quotation_input.py`: `DocumentWriteHeld` maps to existing `QuotationInputBusy` (defer, not a new `UNKNOWN` write).
- `src/launcher/sales_header.py`: mandatory `page_admission`; missing/invalid returns `STOPPED` before `acquire_cdp_browser`; valid admission is bound before page creation and passed to the CDP client factory.
- `src/launcher/backend.py`: order-mail worker passes `self._page_admission`; API service builder receives it.

No new database, scheduler, file store, browser or second hold manager.

**Green run (targeted):**

```text
python -m pytest tests/launcher/test_google_quote_update.py tests/launcher/test_google_web.py \
  tests/launcher/test_read_page_recovery.py tests/launcher/test_sales_order_preflight.py \
  tests/launcher/test_order_mail.py tests/launcher/test_backend.py \
  tests/sheets/test_google_api_service.py tests/research/test_shared_document_admission.py \
  tests/launcher/test_rfq018_shared_safety.py -q
426 passed
```

**Original 26 after fixes:**

```text
python -m pytest <RFQ-017 26 nodeids> -q --tb=short -p no:cacheprovider
26 passed in 0.72s
```

**Remaining failures:** none in the targeted scope; full-suite result below.

## 4. Full-suite and mapping

```text
python -m pytest tests -q --tb=short -p no:cacheprovider
4175 passed, 1 skipped in 320.88s
```

- Collected 4176 = 4175 passed + 1 skipped; **0 failed**.
- The single skip is the pre-existing Windows symlink-permission test; no deselect, no hidden failure.
- RFQ-017 equivalent baseline: 4160 = 4133 passed + 1 skipped + 26 deselected; RFQ-018 adds 16 new tests and turns all 26 original nodeids green.
- 26/26 original nodeids retained: **6 unchanged** (owner adoption, two unconfirmed-write, busy-close, order-mail, sales-no-admission) and **20 rewritten** to current mechanisms. Full intent table: [TEST_MAPPING.md](TEST_MAPPING.md).
- No test was deleted, skipped or weakened by omission; the 20 rewrites are documented one-by-one with the original intent and current equivalent/stricter assertion.

## 5. Preserved effects / no external action

- No source/test change was deployed; no EXE overwrite, process stop/restart, Chrome/CDP attach, production SQLite/WAL/SHM write, or branch merge.
- Live snapshot at audit end: EXE `E9E3DA33…`, app PID 38948, watcher PID 34304; Chrome 9222 owner 24164; 60 orders (35 `HUMAN_COMPLETED` + 24 `PURCHASE_RECORDED` + 1 `INVALID_INPUT_SKIPPED`); 0 active V12 alerts; 3 active V13 holds; row 221 `SAVED` receipt `rec_440fafd372440ecf9dacabf660dd155d`; SHAHAB/115 `MANUAL_REVIEW / RECONCILIATION_UNREADABLE`.
- No real Google/INSO/SMTP/Chrome operation; all tests used local fakes. No UNKNOWN/SENT/hold cleared.

## 6. Resume / next action

- This log, `TASK_SPEC.md`, `TEST_MAPPING.md`, `FINAL_REPORT.md` and the evidence JSON are the durable checkpoint.
- **Next single action:** CEO independent review of RFQ-018. No deployment, trial run, `develop` merge or `main` promotion is authorized by this task.
- If changes are requested: first re-run the 26 original nodeids and the 16 new tests; do not remove or skip any test to obtain a green result.
