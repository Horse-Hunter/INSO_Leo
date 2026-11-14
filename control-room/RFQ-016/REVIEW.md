# RFQ-016 — CEO independent Review (2026-11-14)

**Verdict: `CHANGES_REQUESTED / PARTIAL_BUSINESS_EVIDENCE_ACCEPTED / PRODUCTION_TRIAL_NOT_PROMOTED`.** Reviewed source branch `workbuddy/v16-rfq016-stabilization` at **`41a96f0dd31e815065dce379fadc02aa6c0f86f8`** (13 commits after `9ad9ccb8`). This is independent **GitHub source/test-code/report inspection**, **not** a live Windows/Google/INSO/SMTP session or independently run test suite. The Executor's reported real receipt is material evidence, not a CEO-observed live fact.

## Accepted as Executor evidence (not blanket production PASS)

1. **Row 221 business outcome reported**: `INSO_QUOTE/2026/221`, `FT2232H-56Q-REEL` qty105: exactly one native Save-and-Send, inconclusive first response then original reconciliation `RECONCILIATION_CONFIRMED_SAVED` / receipt `rec_440fafd372440ecf9dacabf660dd155d`; API `A221=发给采购`, `F221=FTDI` readback; ledger `SAVED/PURCHASE_RECORDED`. No quote available → `NO_RECENT_QUOTE`, no quotation-input write, zero quote-button clicks; no mail for this C-class order. This is a legitimate stage outcome, **not** proof of future quotation completion.
2. Production API `google_api.enabled=true`, Service Account Editor and later deployed EXE `E9E3DA33417414ABAC53F8A88A67D9F053BCDAEAB9730EAE9AD8BD7870DFFAD0`, PID `38948` are **Executor-observed/reported** at 14:55, **not independently rechecked now**; previous `197EC23B...`/PID `26604` in the detailed log was superseded by six later rebuilds.
3. Submitted code really contains customer ID `4526000` exact-option guard, bounded native menu retry, purchase button hint fix; task-centre reconciliation, right-click resync, source-status column and calm-row styling; related tests were added. The Executor reports **3349 pass / 1 skip / 26 fail**, but current raw JUnit/failure-ID matrix/build manifest are **not committed**: `TEST_REPORT.json` still reflects older releases, and no independent run was possible.
4. No new real external effect was performed by the CEO Review. Original production, shared Chrome 9222, SQLite/UNKNOWN, rollback and all Git worktrees remain untouched. Agent Computer Use is now permitted; Executor reported using GUI screenshot and two task-centre clicks, not forbidden.

## Blocking code findings (Executor fixes in the existing branch, no forced live rerun)

**P0 — automatic human closure can suppress uncertain effects / real alerts.**
- `src/workflow/v12_flow.py:65-77,306-343` includes `INTERRUPTED_POSSIBLY_SENT` and `STATUS_WRITE_PENDING` in automatic `_OWNER_RECONCILABLE_STATES`, then sets `HUMAN_COMPLETED` based on a source status. But manually changed Google status does **not** prove previous INSO/Google/quote/SMTP uncertain effects settled.
- `src/workflow/v12_store.py:270-303` unconditionally recovers **every** `AlertType` when entering `HUMAN_COMPLETED`, including `NOTIFICATION_FAILED` and purchase/unknown alerts. Immutable events/recipient ledger remain, but the GUI warning and active incident evidence can disappear. The narrower `PURCHASE_RECORDED → DATA_QUALITY only` rule is good; the broader rule is not proven safe.
- **Required:** preserve original durable purchase/outbox/quotation holds and unresolved effects; separate “Owner updated source sheet” from “external result reconciled”; do not auto-clear effect-unknown or notification alerts. Add deterministic UNKNOWN/SENT/failed-mail tests and keep their visible review signals. Do not clear real production historical holds to make the task centre show zero.

**P0 — right-click resync can attach an order to another article and erase alerts.**
- `src/launcher/backend.py:2150-2188` uses **only the old physical row position + completed status** and calls `rebind_identity`, `set_business_state(HUMAN_COMPLETED)`, `recover_stale_alerts`. It does **not** check model/quantity identity, old purchase/quote/SMTP UNKNOWN, existing holds, or atomicity of the two state stores.
- `tests/launcher/test_manual_order.py:45-61` explicitly tests `OLD` → entirely different `FIXED-PART`/Qty7→19 and treats it as success. That is a concrete cross-order binding risk if rows shift/reuse.
- **Required:** original identity/historical effect check, block unsafe UNKNOWN, unique exact row proof (or separate explicit high-risk Owner reconciliation without rebind), no blanket alert recovery, and a cross-row replacement + UNKNOWN regression. Never use this action to override an already dispatched purchase/quote.

**P1 — displayed “source status” may belong to another row.**
- `src/launcher/source_status.py:92-103` marks a status as fresh/verified from the original physical row when exact source relocation fails, **without comparing model/quantity/identity**. A moved/reused line can display an unrelated item's status as this order's “表格真实状态”.
- **Required:** preserve no-write separation but also use identity-aware, nonambiguous observation; when unprovable, display “来源待核对” instead of falsely assigning a sheet status; test moved/deleted/replaced/duplicate rows and stale snapshots.

**P1 — evidence and long-running reliability not yet closed.**
- Commit current run's machine-readable failure IDs, before/after baseline comparison, frozen EXE ↔ source/changed modules manifest, last five rebuild receipts and final PID/SQLite read-only sample. Currently `FINAL_REPORT` is newer than `EXECUTION_LOG` header and `RELEASE_READINESS`, risking bad handoff.
- Existing recorded defects remain: quotation manual refusal without reason; 12:00–12:04 GUI stale display; paused-module window close fails to drain (multiple forced stops); orphan `about:blank#INSO_CREATE`; old `inq_d65be9df…` recurring quotation input failure. Diagnose in bounded follow-up without clearing old holds/replaying writes/closing original tabs.
- Task-centre status filter in `src/gui/workbench.py:206-216` still treats any nonfresh state as `需核对` even if settled and row colour calm; test filter/count/display consistency after 15 minutes.

## Return criteria and CEO decision

- **Business substage:** `PURCHASE_SAVE_AND_GOOGLE_SYNC_EXECUTOR_REPORTED`; **quotation:** `NO_SUPPLIER_QUOTE / NO_CLICK_EXPECTED`; **GUI:** observed Executor screenshot; **independent live verification:** `NOT_VERIFIED`.
- **Overall:** `CHANGES_REQUESTED`, **not** `REVIEWED_DONE`, and **not** permission to promote `develop → main`. Owner approval after trial remains mandatory under [branch policy](https://github.com/Horse-Hunter/INSO_Leo/blob/develop/docs/BRANCH_POLICY.md).
- Single Executor should first write 4–6 focused failing regressions for the P0/P1 paths, then minimum source fix and positive/negative regressions; do not force stop the running program, release a new EXE or rerun row 221 just for Review. New live effect/release safety still requires scoped Owner authority.
- On next request `Review RFQ-016`, independently recheck fixed diff, all focused tests and 26-failure comparison, production scope/unknown holds, review handoff and current trial. If a production fix was installed, it is **still 前瞻试运行**, never automatically main.

[Executor final report](FINAL_REPORT.md) · [recoverable checkpoint](EXECUTION_LOG.md) · [original 12:20–14:55 detailed log](https://github.com/Horse-Hunter/INSO_Leo/blob/41a96f0dd31e815065dce379fadc02aa6c0f86f8/control-room/RFQ-016/EXECUTION_LOG.md).
