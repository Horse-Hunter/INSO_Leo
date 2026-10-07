# RFQ-006 CEO B1/B2 repair and Owner S-as-A
status: complete
owner: Integration Executor
created: 2026-10-08

Base remote/local c596ada, includes CEO review265d6e9 and CHANGES_REQUESTED status.
Read RFQ006 spec/log/report/review and RFQ007 review; CEO files must remain untouched.
Only three production tasks: B1 arm read-only Script start/end latch before confirmation,
bounded30s start and30s end, fail GLOBAL_STOP GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED retaining
page/pending and preventing next row; B2 protected keepalive pages survive all backend parks
and poll finalization, prune closed references, avoid accumulating failed pages, recover normal
one-blank parking when Owner closes pages; S raw source remains S with canonical effective A.
Legacy S skip naturally resumes same inquiry through normal poll and existing alert recovery.
No second architecture, browser manager, recovery API or per-module S branches.
No production access, replay, live Save/Send/quotation/Script/SMTP, DB/config/profile edits or
installed EXE overwrite. Focused/full offline, Ruff/diff, then BuildOnly/frozen/scan newcandidate.
Commit/push current branch clean local==remote; RFQ006 REVIEW_REQUIRED, never REVIEWED_DONE.

### Final repair verification / candidate
B1 regression PASS: visible→hidden; initially absent→delayed start→end; never starts and
never settles GLOBAL_STOP; CDP settlement error maps to the fixed settlement reason; pending
preserves page/blocks reopen and re-click; updater two-row batch makes only first open/write/click.
Verified actual popup0 inserted/1 existing alias remains PASS. Backend GLOBAL_STOP/manual
release with no INSO session detaches only, preserving Google/human operation pages.
B2 PASS: real production poll loop executes combined→keepalive→finally→next cycle with borrowed
CDP; NEEDS_HUMAN/preexisting pages survive, business remains RUNNING,229 command enqueued,
no hold; all-success ends exactly one blank. Owner close prunes IDs/restores canonical park;
new CDP wrappers retain same target protection; check-only attach does not relog early.
S PASS: freshS Research; S/A equivalent duplicate/important-order/routing/type/purchaser;
PendingSheetRecord/WorkItem/identity rawS preserved; oldS skip auto-resumes same inquiry and
invalid-input alert recovers while customer-name alert remains. D/blank/UNKNOWN invalid;
B/C threshold suite unchanged. RFQ003 B1 and RFQ004/005/006/007 regressions PASS.
Focused459 PASS15.66s; full safe/offline1431 PASS/1 SKIP57.05s. Ruff src/tests PASS;
git diff --check PASS. BuildOnly/frozen self-check/RELEASE_SCAN_OK PASS (exit0).
New candidate EXE SHA256:
77A861A40AE042BDC75A6AB1FBA7E6A5C0794052B9A972A28DEEAFBECC9CA126.
Candidate path: build/windows-release-stage-1.3/dist/INSO_V1.3/INSO_V1.3.exe.
Not deployed; no installed V1.2/V1.3/config/DB/OAuth/credential/profile/CDP asset changes.
No new real procurement, Save/Save-and-Send, quote write/update, Apps Script or SMTP.
CEO review SHA256 unchanged:15D43DE42795A6D11FAB2E8FAC13F508E2762627896C35E02E099630D5AF1955.
No new decision conflict found. RFQ006 CHANGES_REQUESTED→REVIEW_REQUIRED; RFQ007 unchanged.
Source fixes verified offline, not a new live Script/login/SMTP acceptance claim.
