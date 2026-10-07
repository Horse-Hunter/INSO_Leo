# RFQ-006 CEO repair submission — 2026-10-07

Status: REVIEW_REQUIRED. Branch: feature/v1-3-integration.
Updated from CEO commit 80d8f3b6ae45ecd3c418896d5c4168637e8c0d30 with fetch / pull --ff-only.
No new branch or architecture. REVIEW.md unchanged (SHA256
2432263F4E89B57CCBFD610156B52BBA86567429A387B12F4AB098B59D662B79).

## Repairs
- B1: src/workflow/v13_integration.py:222. Strict relocation first; original worksheet/observed
  position only blocks automation or reads Owner completion status. Snapshot mutations while sent
  cannot trigger query/update/new hold/mail or new inquiry. Quoted closes hold; missing/unknown retains
  hold while unrelated orders continue. No fuzzy or business identity fallback.
- B2: src/workflow/v13_quotation.py:176 /258; src/workflow/v13_integration.py:261.
  Unknown reader/operation/factory/update/close/result-contract failures globally stop with fixed
  V13_INTERNAL_FAILURE. No row hold or later query. Typed V13SourceRowError and normal RFQ-005
  retry exhaustion stay row-local; shared DB/Sheets/CDP/auth faults keep reviewed global scope.
- Website229: src/launcher/v13_integration.py:103; src/launcher/backend.py:945.
  Every SOURCE_UNAVAILABLE site is notified via the existing ledger/QQ SMTP worker. Closed categories,
  inquiry/site/category durable dedup, known MPN, owner linan229@qq.com; no raw provider error/HTML/token.
  IC.net pauses V1.2, INSO authentication stops globally, other sites continue. Existing IC/INSO duplicate
  manual/fault alerts suppressed. Pending SMTP retry changes no business scope.
- Headerless input: src/sheets/quotation_input.py:21 /86 and src/launcher/v13_integration.py:15.
  Removed header_row/header_range and header reads/equality checks. RAW14 order remains INSO canonical
  QUOTATION_COLUMNS. Metadata binding remains mandatory before every write and UI open; malformed
  title/gid globally stops with zero write/open/click. Exact blank/leading zero/decimal/whitespace/newline
  payload and readback remain verified offline.

## Configuration and read-only evidence
QUOTE_INPUT_GEOMETRY CONFIRMED; header NONE / NOT APPLICABLE.
Target: 报价输入!A1:N1. Own V1.3 production config: gid=489913321, input_row=1,
first_column=1, header_row absent. Existing V1.2 config bytes unchanged.
Read-only API metadata again proved unique title 报价输入 and sheetId=489913321.
Only spreadsheets.get metadata requested; no grid reads/writes in this acceptance.
更新报价 DOM UNKNOWN: native Chrome window inventory only about:blank; browser DOM surfaces
expose Edge/IAB, not fixed production Chrome. Edge is not substituted. No UI input/click/navigation.

## Exact-source checks
- Hold mutation regression:12 status/mutation cases + deleted/unrelated-row continuation PASS.
- Unknown exceptions:12 RuntimeError/ValueError reader/operation/factory/update/contract/close cases PASS;
  typed row-local updater error remains ROW_FAILED; no new hold/mail/inquiry for unknown errors.
- Website229 regression:24 six-site/four-reason cases PASS, durable dedup, fake retry transport,
  fixed recipient and sanitized body, preserved scope. Research optional-site continuation PASS.
- RFQ-004:47 passed0.67s. RFQ-005:93 passed0.59s.
- Combined RFQ-006 workflow/backend/GUI:102 passed6.97s.
- Focused read/update/integration total:242 passed across the three disjoint suites above.
- V1.2 workflow/RFQ-003/backend:243 passed,1 skipped16.86s.
- Full safe/offline:1334 passed,1 skipped58.66s; exit0, no outbound-mail attempts.
- Ruff src/tests PASS; git diff --check PASS.
- Canonical build_windows_release.ps1 -Version1.3 -BuildOnly exit0.
- Frozen/deployed self-check exit0; staged RELEASE_SCAN_OK.
- Idle GUI exit0: INSO_V1.3, 已停止, gui_rendered=true, business_thread_started=false.
  Start was disabled by the diagnostic; no business worker was invoked.

## Local deployment and rollback
New V1.3 EXE SHA256: 96765BB7BD59E627A33CC5621BECAEEC03D0BE677B628085969C2AA3C5DAFDD0
Backup: D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-006-before-ceo-repair-20261007-153211\INSO_V1.3
Backup old EXE SHA256: FB8AA11FC2B300BA1B56D08FD2AC9B6122405E67C31A0361DF21CC09B700EC16
Deployed executable/_internal only;2178 internal files verified against staged hashes.
V1.3 own runtime configs retained during asset replacement; shared DB/OAuth/profile paths unchanged.
V1.2 EXE SHA256 unchanged:1A49C9650BA531F2299326FFC89761D0391CD5F2C0FE32327DDD0736BD5C3E84.
V1.2 production/research JSON byte hashes match pre-repair values.
No dependencies installed. No credentials, generated release files or production payload committed.

未执行真实 A1:N1 报价写入、更新报价、Apps Script、Save、Save-and-Send或真实采购。
Live-only UNKNOWN: actual INSO quotation DOM, 更新报价 role/locator uniqueness, Google login/session,
Apps Script execution/popup, inserted/already-existing feedback, source-status transition and refresh delay.
Separate Owner authorization is still needed for one controlled live acceptance.
The previous geometry BLOCKED LIVE CONFIG conclusion is superseded by Owner confirmation;
live business acceptance itself remains UNKNOWN. CEO review is required; no follow-on task started.
