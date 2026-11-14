# RFQ-016 — production API single-order release gate

**Status: `SOURCE_FIX_ACCEPTED / PRODUCTION_API_NOT_VERIFIED / REAL_ORDER_NOT_COMPLETED`.** This is a bounded checklist, not a second implementation plan or a license to run all modules.

| Gate | Evidence / next action |
| --- | --- |
| Existing V1.6 source fix | `24b73be70feb407a85fd25c3af9178430bdaf508` accepted at source; prior EXE replacement **reported**, hash/live binary still recheck |
| Synthetic API | Previous Service Account synthetic write + readback reported; no need to repeat approved synthetic tests |
| Production transport | Inspect actual `production.json.google_api.enabled`, external key and frozen `--api-self-check`; `TRANSPORT_READY` only checks construction |
| Production Google | Read exact document/sheet/row and Editor role **live**; earlier SA Viewer is not sufficient to write. Editor grants entire workbook access |
| Eligibility | Target row `2026/221` last `未发` = inquiry; prove current date, source identity/brand, SQLite orders, INSO and SMTP; preserve 7-day or approved age-only manual path |
| Isolation | Existing `inquiry_ids` is not a global filter; prove quotation/TP/mail won't touch unrelated orders or disclose and authorize their effects |
| External operations | Only after one consolidated Owner authorization for needed Editor + INSO purchase + Google write + quote button + mail; record pre/post receipts and durable UNKNOWN |
| Acceptance | Read→research→INSO→Google→eligible quote→native button→SQLite/mail; independently show what succeeded, what is UNKNOWN, other affected orders, current process |

**Stop immediately:** another live worker; uncertain INSO/save or Google write; source/date/identity mismatch; unknown quote button result; SENT/UNKNOWN mail conflict; unexpected extra order; unsafe Chrome tab ownership. No raw DB replacement or old top-row removal.

**Resume after any agent interruption:** [CEO handover](../CEO_HANDOVER.md) → [Execution checkpoint](EXECUTION_LOG.md) → verify real Windows process/DB/Google/INSO/SMTP → next authorized single step. [Full historical readiness analysis](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/RELEASE_READINESS.md).
