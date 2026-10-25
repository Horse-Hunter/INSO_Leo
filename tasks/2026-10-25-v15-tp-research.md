# V1.5 TP independent research

status: REVIEW_REQUIRED
owner: Codex
authority: Owner request 2026-10-25; discovery review d67ebfe150340ea90760f5a2e44dcd7b92f8dac4

## Scope and safety

Offline source implementation and synthetic verification only. No real Sheets/CDP,
mail, production DB, procurement, build or deployment. Existing V1.5 worktree;
no copying dirty V1.4 work or merging later unreviewed commits. Owner confirms
original source physical positions do not change by insertion. Source anchor
must still corroborate exact model, quantity and available brand; conflicts hold.

## Reuse matrix / minimal design (recorded before implementation)

| Existing module | Reused public capability | Minimum extension | V1.4 effect |
| --- | --- | --- | --- |
| launcher.google_web / sheets | protected native TSV, document/gid guards, reader retry, schema and source rows | exact RFQ_BRIEF A:Q **read only**, strict header adapter, explicit source pointer validation | default source ranges and write whitelist unchanged |
| research six adapters / runtime | same clients, parsers, MPN/stock/price validation, authenticated sessions and typed errors | TP-only raw candidate projection via existing adapter instances; no second collector/login | ordinary search and 1–6 month selection unchanged |
| research.source_contracts | calendar_month_cutoff | independent TP quote DTO with real quotation date vs current-price provenance | existing PriceCandidate 1–6 contract unchanged |
| research.ecb_fx / fx | same ECB provider and Decimal conversion | TP currency parsing; same-day quote validation; actual min/second without INSO preference | ordinary aggregation unchanged |
| workflow.v12_store / notifications / smtp | same nullable-inquiry outbox, claim, retry, UNKNOWN quarantine, QQ SMTP | TP notification kind, task-linked command key with inquiry_id=None | no fake V1.4 inquiry; same worker/transport |
| workflow SQLite / V13 migration | additive tables, verified backup; existing nullable-outbox upgrade | requirement-kind/source-position task key, generations and CAS claim, durable completion/outbox recovery | no ordinary inquiry state changes |
| launcher.backend | existing poll thread, fifteen-minute wait, manual condition/gate, source recovery callbacks | opt-in TP phase after existing cycle; manual TP action on the same thread | disabled by default; no new daemon/scheduler |
| gui.app / contracts | existing context menu and order action dispatch/history DTO | third action 重跑 TP 价格; expose TP-only historical rows | purchase/quotation actions retain old path |

Independent TP task key includes Spreadsheet/source worksheet/source row/requirement
kind, not price or Brief row or old inquiry_id. Automatic generation runs once;
TP edits do not automatically reopen it. Explicit manual generation revalidates
fresh Brief and source, blocks while any delivery is pending/unknown. CAS prevents
duplicate claims; crash before durable outbox may requeue read-only research,
crash after enqueue reuses immutable command. No synthetic V1.4 parent inquiry.

Selection decision: second-lowest means the next **distinct positive RMB unit
price**, not a duplicate equal-price row. For each site expand calendar months
1..12 until two distinct eligible prices exist (or month 12), then take the two
lowest from that cumulative window. Current prices remain explicitly undated;
unknown historical dates are not replaced with capture time. Preserve stock
classification; global pool uses in-stock/ordinary quotes first, no-stock only
when no ordinary quotes and no technical uncertainty, matching existing fallback.
Global ranking has no INSO preferential override. These choices require CEO review.

The four real TP rows are **not re-read** in this offline phase. Synthetic cases
cover their documented missing-brand/known-brand and existing/no-old-ledger
states, plus conflict/ambiguity variants; no assertion that all four live orders
are presently READY. Live four-row gate stays pending before later activation.

## Acceptance / verification

Cover historical no-inquiry orders, pointer duplicates/conflicts, USD/RMB, stale
FX, month 1..12 boundaries, real dates/current prices, missing/invalid quotes,
per-site/global distinct minima, repeated polls, TP edits, restart and outbox crash
windows, failed/unknown delivery, manual-auto exclusion and existing regressions.
Document actual file/interface changes, results, limitations, full commit SHA.
Final status REVIEW_REQUIRED; no release/live authorization inferred.

## Completion / execution evidence

- Implemented the source-to-TP independent lifecycle, same-adapter TP research,
  same-outbox mail and original poll/manual GUI wiring. Default tp_enabled=false;
  no real configuration, DB or external operation was performed. Actual interfaces,
  changed-file list and risks: V15_TP_RESEARCH_IMPLEMENTATION.md.
- Final targeted: **73 PASS /2.59s** with synthetic Sheets/native UI/source captures,
  DB, transport and poll/manual tests. Same old GUI row and TP-only row can both
  dispatch only the selected TP generation; actual concurrent DB claims have one
  winner. Existing source policy/aggregation/SMTP implementation files remain intact.
- Full tests: **2544 PASS,11 SKIP,2 FAIL /86.48s**. Both failures are the unchanged
  unsettled-manual CDP/GLOBAL_STOP expectations documented in the report. Independently
  reran with all82 src imports loaded from d67ebfe Git blobs, **6 PASS/2 same FAIL/
  19 deselected /4.86s**. No baseline files/branch were changed or tests suppressed.
- Commands: `python -m pytest tests/sheets/test_tp_brief.py tests/research/test_tp.py
  tests/workflow/test_tp_research.py tests/launcher/test_tp_integration.py
  tests/gui/test_manual_order.py -q -p no:cacheprovider --basetemp <owned-temp>`;
  full `pytest.main(['tests','-q','-p','no:cacheprovider','--tb=short',
  '--basetemp',<owned-temp>])` after appending existing V1.4 release site-packages.
  Command-local PYTHONDONTWRITEBYTECODE, PYTHONTZPATH, TCL_LIBRARY and TK_LIBRARY
  reused existing dependencies. Initial missing-PDF/Tcl environment failures were
  resolved without installing anything or changing machine/runtime configuration.
- Existing SMTP test guard blocked two legacy test attempts; no mail left the
  machine. Ruff over all src + changed tests and git diff checks PASS. Only
  synthetic data in tests; no real data fixtures, screenshots, TSV, IDs or prices.
- Automatic approval rejected the first shared-whitelist proposal before applying
  it. Replaced by dedicated read-only interface with unconditional write rejection;
  old range/title/action/write lists remain unchanged and rejection tests pass.
- Retired all six owned helper/test directories after absolute-path/reparse checks,
  **110783232 bytes**. No permission changes, runtime/profile/CDP cleanup, worktree
  deletion, handoff, package or deployment. Original V1.4/main dirty work untouched;
  same V1.5 managed worktree retained for CEO review.
- Remaining limits: two reproducible baseline failures; four live TP rows require
  a separately authorized preflight; actual12-month site coverage/date fidelity,
  future SMTP/migration acceptance and 2026 date provenance remain UNKNOWN.
  Independent TP identity does not require old inquiry_id or Research records.
  No production/live PASS claim. Stop at this review-required delivery.
