# RFQ-016 — live execution checkpoint (not historical diary)

**Last refreshed: 2026-11-14 document-only takeover.** Everything below marked `REPORTED` is prior Executor evidence, **not a new Windows observation**. **No active production executor/process can be inferred from chat silence.** New Executor must update this card from real live state before any external effect.

## 1. Last known facts (do not elevate to current)

| Area | Previously reported | Real-time status |
| --- | --- | --- |
| Git / source | Dev branch `workbuddy/v16-rfq016-stabilization`; product fix `24b73be70feb407a85fd25c3af9178430bdaf508`; prior CEO review `71a67012e2d0f31b505c2f17aecd407d9cebc951` | Current branch/HEAD/dirty status/worktrees **NOT_VERIFIED on Windows** |
| Installed EXE | `D:\\Program_Leo\\INSO_Leo\\dist\\INSO_V1.6\\INSO_V1.6.exe` SHA256 `b357889d48e5abe6ec6504eddd610442c877e438018f156c4c932477070814f6`; rollback `dist/release-backups/INSO_V1.6-header-block-20261114T021508Z` | Process, current EXE hash, binary/config match **NOT_VERIFIED** |
| Production API | `production.json` reported missing `google_api` key; `--api-self-check` reportedly DISABLED on production config | Enabled, key path, real reads/writes **NOT_VERIFIED** |
| Google ACL | `INSO_QUOTE` reported **Viewer** for original test SA `rfq016-sheets-test@inso-509314.iam.gserviceaccount.com` | Current Editor entitlement **NOT_VERIFIED** |
| Source candidate | `2026` physical row `221`, `FT2232H-56Q-REEL`, Qty `105`, Brand blank, status `未发`; customer/date not verified here | Source identity, age, INSO, Google, SQLite, mail **NOT_VERIFIED** |
| External results | Owner said old DeepSeek quota exhausted before order completed; no subsequent authoritative live receipt in Git | No safe claim of zero in-flight operations or no partial effect |

## 2. Mandatory next check (read only)

1. Inspect `git branch --show-current`, `git rev-parse HEAD`, `git status --short`, `git diff`, `git worktree list --porcelain`; preserve all unknown dirty state and reuse original working tree.
2. Check live INSO EXE PID, module/start/stop status and fresh logs; never start another on an unconfirmed old process. Keep protected Chrome 9222/profile.
3. Inspect SQLite in read-only mode including WAL/SHM with locks/holds/new order/purchase/quote/SMTP SENT/UNKNOWN; inspect Google current row/date and SA sharing; inspect actual INSO purchase and native quotation state when safely possible.
4. Verify production API config/self-check/read/Editor and a **genuinely isolated** one-order entry including all other modules.
5. If business effect/Editor authorization is missing, ask Owner **once** with precise scope. Otherwise proceed per [Task Spec](TASK_SPEC.md).

## 3. Checkpoint record for every meaningful boundary

Use this **same file** (replace this section's current entry with newest fact plus concise references, not endless diary). **Before any external effect**: record timestamp/time zone, executor/window, worktree/HEAD/dirty files, process PID/mode, authorized workbook/sheet/physical row/identity, original Google/INSO/SQLite/SMTP states, durable idempotency hold, exact next effect and other-module scope. Persist actual native guard before dispatch; commit/push safe checkpoint when possible.

**After receipt:** record exact operation attempted, response/ack, independent observed external result, `DONE / NOT_DONE / UNKNOWN / WAITING_OWNER`, SQLite/Google/INSO/mail consistency, other-order impact, whether original process still running, next **single** action and any Owner decision. Do not put credentials, customer private data or raw mail into Git.

**Current checkpoint:** `TAKEOVER_REQUIRED / LIVE_NOT_VERIFIED / NO_EXTERNAL_ACTION_THIS_DOCUMENT_UPDATE`. Last action of this document-only CEO: shorten/reroute docs, no app run, no Google write, no INSO save, no quote click and no mail sent. **Next:** live scene read-only verification by single Executor.

**Crash/quota rule:** a successor trusts only last persisted pre-action guard + actual external reconciliation, never a missing final report. A previous window may have left a process still running. Unknown = do not replay.

## 4. Historic evidence (immutable links)

[Full original execution log (988 lines)](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/EXECUTION_LOG.md) · [Historical final reports](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/FINAL_REPORT.md) · [API feasibility](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/GOOGLE_API_FEASIBILITY_2026-11-13.md) · [latest header/read evidence](../../docs/evidence/v16/rfq016-phase3-production-parity-2026-11-14.json) · [current Review](REVIEW.md) · [CEO takeover card](../CEO_HANDOVER.md).
