# Task: RFQ-005 Google quotation update

status: complete
owner: Owner/CEO (requirements); Executor (implementation)
created: 2026-10-07
updated: 2026-10-07

Canonical complete Task Packet: control-room/RFQ-005/TASK_SPEC.md.
Goal: consume RFQ-004 quotes, raw14 input/readback, idempotent UI update and
read-only original source status confirmation; row/global isolation.
Non-scope: live writes/submissions, final scheduler/GUI/mail, packaging/deployment.
Verification: all Owner 45 offline cases, focused/full pytest, Ruff/diff, commit/push.
UNKNOWN: live geometry/roles/dialog/Script delay/session. Executor source/offline delivery complete;
independent CEO Review REQUIRED, no executor verdict.


## Owner correction / B1-B2 repair — 2026-10-07
真实 Google worksheet title 为 `报价输入`；此前“报价输入子表”为错误名称，
已修正，旧名称不作为 alias 接受。配置 gid 仍必须显式提供，不猜测生产值。
Existing Sheets service `spreadsheets().get` requests only
`sheets.properties(sheetId,title)` with `includeGridData=False`.
Exactly one title must equal 报价输入, its sheetId must be a nonnegative integer
(not bool/string/float), and str(sheetId) must exactly equal configured gid.
Missing/duplicate target, malformed metadata, mismatch or metadata/auth/API failure
raises sanitized QuotationInputUnavailable -> GLOBAL_STOP. Verify metadata before
fourteen headers; both must pass before opening the UI and before each RAW write.
No DOM title guess, business-cell metadata read, new adapter/config/OAuth path or
production gid. Existing RFQ-004 identity/read/retry and V1.2 behavior remain frozen.
