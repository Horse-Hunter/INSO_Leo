# Control Room — current status (2026-11-14)

**Status is an operational pointer, not live proof.** Owner/CEO own requirement meaning; active Executor updates actual execution status; CEO independently reviews. A disappeared agent is not proof the Windows process stopped. New windows start at [AI_START_HERE](../AI_START_HERE.md) and [CEO handover](CEO_HANDOVER.md).

## Active

| RFQ | Status / active work | Where to resume |
| --- | --- | --- |
| **RFQ-016** | **REVIEW_REQUIRED / REAL_ORDER_PURCHASE_DONE / TASK_CENTRE_CLEARED / QUOTATION_WAITING_SUPPLIER**. 2026-11-14: the authorized single order (`2026` row 221) was purchased through the API path — INSO save+send reconciled `SAVED` (`rec_440fafd3…`), Google `A221` `未发`→`发给采购`, `F221`→`FTDI`; no mail; quotation `NO_RECENT_QUOTE` (0 writes, 0 button clicks). Task centre reconciled to 60 orders / **0 exceptions / 0 active alerts**, status column now shows the sheet's own status; new Owner action 「按表格恢复状态」; six rebuilds deployed, current EXE `E9E3DA33…` with full rollback. Four known non-blocking defects recorded in the checkpoint. | [Task Spec](RFQ-016/TASK_SPEC.md) · [Execution checkpoint](RFQ-016/EXECUTION_LOG.md) · [CEO Review](RFQ-016/REVIEW.md) · [Final report](RFQ-016/FINAL_REPORT.md) |

Remote development branch: `workbuddy/v16-rfq016-stabilization` (read actual HEAD each session); production branch/report lineage also exists at `codex/v1-6-independent-scheduling`. **Do not auto-merge/deploy** from a document-only commit.

**Next safe work:** identify old Windows worker/process + its in-flight effects, production config/API + Sheet Editor, row `INSO_QUOTE/2026/221` identity/date/holds/INSO/mail, and a genuinely bounded one-order entry. Only then resume within explicit real-effect authorization. No unattended full Start as a stand-in for one-order proof.

## Completed historical RFQs

| RFQs | Last recorded classification | Read on demand |
| --- | --- | --- |
| RFQ-001–014 | `REVIEWED_DONE` (separate historical decisions and approvals) | `control-room/RFQ-XXX/{TASK_SPEC,REVIEW,FINAL_REPORT,EXECUTION_LOG}.md` |
| RFQ-015 | `DEPLOYED` historical V1.4 release | `control-room/RFQ-015/` |

Past release/source holds are **historical**, not instructions to automatically roll back current binaries; the current RFQ-016 Review controls acceptance. Owner 2026-11-14 permits Agent Computer Use, but business write/purchase/quote/mail authorization remains separate. No previous historic report may be used as present live status.

[Full pre-cleanup coordination history](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/COORDINATION.md) · [Archive index](../docs/HISTORY.md).
