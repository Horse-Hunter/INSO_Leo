# RFQ-016 — Active business contract (2026-11-14)

**Owner objective:** safely complete and verify **one real V1.6 inquiry** using Google Sheets API end-to-end, without processing unrelated orders or repeating unknown external effects. This supersedes historic source-only planning as the **current continuation**, not the past design/implementation history.

## Current target and authority

- Last **reported** target: `INSO_QUOTE / 2026 / physical row 221`, MPN `FT2232H-56Q-REEL`, Qty `105`, blank brand, status `未发`. **Re-read all fields, customer/date/status/unique identity and SQLite before any action.** Prior Owner says old window did **not** complete the order; current external truth is NOT VERIFIED.
- `未发` is an **inquiry pending** state. Quotation candidates have `发给采购`, `采购已报价`, `已报价给客户`; do not claim starting quotation automatically processes row 221.
- Automatic inquiry/quote admission: original source date within **7 Shanghai calendar days inclusive**, exact status/identity and existing holds; TP within last calendar month. Owner's explicit one-order manual entry may **exempt age only**, not identity, permission, status or no-repeat guarantees.
- Agent Computer Use is allowed if actually accessible. It does not grant Editor on the whole workbook or authorize arbitrary purchase, quote-button, mail or release actions. Never bypass human security challenges.

## Required sequence (single Executor)

1. **Recover live scene**: current Git branch/HEAD/dirty worktree; original running EXE/PID/module; logs; SQLite/WAL/SHM `SENT/UNKNOWN` and holds; actual source row, INSO purchases/quotes, Google cell states, mail receipts. If the original worker still runs, **observe, do not launch another**. No duplicate worktree/profile.
2. **Verify API mode**: original external Service Account `rfq016-sheets-test@inso-509314.iam.gserviceaccount.com`; `production.json.google_api.enabled=true`; genuine key path outside Git; `--api-self-check`; actual production Sheets read and Editor access. `TRANSPORT_READY` alone never proves current production API or writing entitlement. Preserve Chrome `9222` and legacy runtime links.
3. **Prove one-order isolation**: inspect original manual one-order entry and all module scheduling. `inquiry_ids` alone restricts inquiry but **not** quotation, TP or notices. If full Start may affect other rows, disclose exact potential effects and obtain one consolidated Owner decision **before** launch. No new parallel purchase script or state-machine bypass.
4. **Authorization**: once-only consolidated request only for missing real permissions/irreversible effects: named source row, whole-file `INSO_QUOTE` Editor grant, allowed INSO Save-and-Send, Google brand/status/input writes, one quote button, SMTP, and any other orders that could run. Read-only investigation and already authorized technical verification proceed without repeated approvals.
5. **Execution**: verify exact row via API; research/brand/stock, INSO duplicate/history and actual procurement receipt; Google brand/status single-cell write and genuine receipt; separate fresh eligibility for later quotation; exact 14-cell quote-input write receipt (Owner explicitly removed **pre-click 14-cell readback** requirement); approved CDP quotation button **at most once**; quote result; SQLite and SMTP final states. Capture before/after each effect. A request is not proof of business success.
6. **Fail closed**: any uncertain Google write, INSO purchase, quote script, SMTP, source identity or cross-module effect persists as UNKNOWN/hold; **stop downstream effects and reconcile externally**, never blindly retry, alter source date, clear history or backfill invented success. No generic start, duplicate Chrome or forced process shutdown.
7. **Delivery**: reconcile Google/INSO/SQLite/mail and unrelated orders, report `DONE / NOT_DONE / UNKNOWN / WAITING_OWNER`, current program PID/state and observed evidence. Keep the **existing** `EXECUTION_LOG.md` recoverable with pre-/post-effect checkpoints and next single action. Final business report uses [seven headings](../../docs/REPORTING.md); CEO independently reviews.

## Immutable constraints

- Do not delete/move 2026 top four rows, offset physical row numbers, relax bounded header identity, or relocate W1 `quote_date` proof. Keep `2026`/SHAHAB exact schema semantics.
- One active Executor; preserve current Windows worktree, live EXE, shared runtime/junction, SQLite/WAL/SHM, one Chrome profile/9222, release rollback and secrets. Build/deploy only if a verified defect requires smallest fix, with safe stop and original release process.
- Unrelated RFQ-016 past source fixes, mail controls, existing 15-minute scheduling, SAFE UNKNOWN, and historic sent mail remain in force. No batch replay or second transport.
- Role handoff is interruption-safe: a new window may start from repo + live evidence **without predecessor chat or final report**.

**Evidence:** [current execution checkpoint](EXECUTION_LOG.md), [Review](REVIEW.md), [release readiness](RELEASE_READINESS.md). **Full original historical Task Spec:** [pinned document](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/TASK_SPEC.md); [long review history](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/REVIEW.md). When a historical policy and this current Owner task differ, resolve by dated Owner authority + actual implemented code, never by guessing.
