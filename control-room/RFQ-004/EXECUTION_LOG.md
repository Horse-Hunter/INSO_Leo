# RFQ-004 Execution Log — 2026-10-07

## Baseline and reuse audit
- Fetch completed. origin/feature/v1-2 = c8d514ed7aff2542dda685d476cd6e92ff97a85d, exactly Owner baseline; RFQ-003 REVIEWED_DONE. New managed worktree C:/Users/Leo/.codex/worktrees/rfq004-v13/INSO_Leo; feature/v1-3 from that commit. V1.2 checkout/ref untouched.
- Root main checkout is older and dirty: all pre-existing changes preserved. Other worktrees retain protected runtime/profile or unrelated unique work; no removal/reset. No consumed handoff exists for RFQ-004.
- Read entry/governance, baseline, module ownership, RFQ-001/002 records and RFQ-003 spec/log/report/review. Stable branch uses root AI_START_HERE.md (old main docs/AI_START_HERE.md is superseded).
- Reuse Sheets schema/pending parser/relocate and public workflow all_items/get_by_inquiry_id; never derive V1.3 identity using inquiry_id_for(current row), whose existing V1 key includes row number. Resolve only uniquely relocated existing ledger identities. Orphan/ambiguous rows fail closed; no random or row-based ID.
- Reuse PlaywrightProcurementHistoryPage native lower query, overall deadline, response/grid/pager identity, complete paging; add an optional per-page raw capture seam, unchanged by default. Existing duplicate record converter validates positive quantity and Decimal price: incompatible with Owner raw quotation semantics, so add a narrow raw DTO reader rather than another query/parser/session stack.
- Extract the RFQ-003 prepared-query retry loop into workflow public helper and delegate existing V1.2 checker to it; V1.3 uses the same engine with its stop fault, no row cooldown. Launcher owns existing attach/authentication and fresh tab lifecycle; no config/browser/credential stack duplicated.
- Raw display mapping is discovered by exact header labels and matching data-field cells after settlement, never guessed API keys/column positions. Live 14-column layout/text remains UNKNOWN pending authorized real read verification; no live exploration planned.

## Boundary
Read-only/offline development only. No production access, credentials, real Save/Save-and-Send, Google writes, update quote, Apps Script, SMTP, packaging or deployment. V1.2 EXE unchanged. REVIEW_REQUIRED only at delivery.

## Implementation / public capabilities
- `src/sheets/pending.py`: canonical row parser now serves a public exact-status helper; original query_pending_records still exclusively 未发. query_quotation_candidates is read-only 发给采购. Re-export through Sheets public package.
- `src/sheets/quotation_candidates.py`: read-only relocation via existing relocate_record; normalize ONLY expected 未发→发给采购 status; source must be exact sent status, unique snapshot and unchanged expected brand. Accept only an explicit persisted Research UPDATED brand, never infer edits. Both original and moved row can resolve; original identity object remains unchanged in output.
- `src/workflow/v13_quotation.py`: resolve candidates from existing all_items, then get_by_inquiry_id and relocate/re-read before EACH attempt. No enqueue/ID generation or ledger writes. Orphan/ambiguous/changed identity stops with typed GLOBAL_STOP; no guessed linkage. Normal rows run immediately, no V1.2 inter-row cooldown. Output holds original inquiry_id/identity/queried_mpn plus selected raw quotation object, or normal NO_RECENT_QUOTE.
- `src/inso/quotation_read.py`: immutable V13QuotationRow, fourteen text fields, separately parsed aware quote_record_time; pure exact-MPN rolling inclusive 72h recent/latest selector. Future and stale rows excluded. Equal latest timestamps retain the first equally latest row without content tiebreaking. No price/quantity/brand/currency/creator eligibility checks. Missing cells/invalid technical time are failed reads, present empty business fields are preserved.
- `src/inso/duplicate_history.py`: existing PlaywrightProcurementHistoryPage gains optional capture_page callback AFTER native page settlement and BEFORE paging; V1.2 default remains original payload. Header labels must match the full contiguous 日期→制单人 interval, observed data-field links the cells; textContent keeps displayed cell whitespace and strings. Never guess unverified API keys or include later 平台来源/品名. Existing public timestamp parser and exact dup-mpn-v1 normalization reused.
- `src/workflow/inso_query.py`: RFQ-003 initial + three retry loop extracted; failed attempt is closed before every fake/interruptible 180-second wait, same exhaustion GLOBAL_STOP. Both former launcher query loops delegate to it while retaining their own source-result classification/authentication/database exceptions and V1.2 stop semantics. V1.3 uses this same engine with a distinct non-business shutdown exception. No second retry engine, no concurrent INSO operations.
- `src/launcher/v13_quotation.py`: minimal session adapter accepts the existing reused browser handle/Core-login capability, attaches through canonical RFQ-002 authentication with fresh_page=True and fixed 9222; no browser/credential/config implementation. Existing lease guard detects mid-query invalidation; preserve makes subsequent cleanup/open impossible. Normal owned-tab closure is verified before the next order. No GUI/scheduler/mail wiring.
- No changes to V1.2 duplicate 168h rules, Research sources, AI, Save-and-Send, status-write strategy, notification/SMTP, startup interruption or row cooldown. Existing regressions pass.

## Offline acceptance / exact commands
Environment: existing Python 3.12 developer installation; no dependencies installed.
Windows developer Python has no IANA database. Fixed-clock tests use existing bundled IANA data by setting:
`$env:PYTHONTZPATH='C:\Users\Leo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\tzdata\zoneinfo'`.
Every time test uses fixed aware ZoneInfo("Asia/Shanghai") (or a fixed other-zone equivalent); waits are faked, never wall-clock 180s.
Production prefers ZoneInfo and, on Windows without IANA data, uses the same explicit contemporary Shanghai UTC+08 contract as existing INSO timestamp parsing. This is not the computer local timezone. Import was additionally verified without PYTHONTZPATH: V13_IMPORT_OK Asia/Shanghai. No new timezone dependency or production configuration was introduced.

Final focused:
`python -m pytest -q tests/inso/test_v13_quotation_read.py tests/workflow/test_v13_quotation.py tests/launcher/test_v13_quotation_operations.py --basetemp=.tmp/rfq004-focused-final --tb=short`
**48 passed in 0.65s**, exit 0.

Final full safe/offline:
`python -m pytest -q tests --basetemp=.tmp/rfq004-full-final --tb=short`
**1101 passed / 1 skipped in 47.89s**, exit 0.
Existing RFQ-002 authentication and RFQ-003 resilience suites included. Different skip totals from old Executor report reflect this host's enabled synthetic Windows/Core tests, not removed coverage. No outbound SMTP attempt warnings.

`python -m ruff check src tests`: PASS. `git diff --check`: PASS.
Final scoped/staged diff reviewed before commit; no generated files/runtime/secret/customer data captured.

Acceptance coverage:
- exact sent-only source; excludes 未发/采购已报价/whitespace status;
- original identities, moved rows, real offline workflow store, unknown/duplicate linkage fail closed, explicit persisted brand update;
- one fresh owned tab per row, serial close-before-next, no normal row wait, closure failure blocks progression;
- exact MPN, native complete multi-page query with latest on later page, old/future/fuzzy exclusion;
- 71h59m / exactly72h / 72h+microsecond / midnight / month / year / aware-zone conversion;
- no quote is normal, single/multiple/latest/ties, raw 14 fields, empty business fields including price/creator, odd currency/notes, leading zeros and whitespace, different quote brand and empty quantity accepted;
- missing structure/incomplete paging/unparseable date stay query failures, never empty results;
- recovery at attempt1/2/3/4, four-attempt exhaustion GLOBAL_STOP, fresh tabs and fake 180s, shutdown interruption;
- actual RFQ-002 fake CAPTCHA/phone/device login through the V1.3 cycle, no next row/no wait, preserved human-needed page/client detach only; mid-query actual lease invalidation preserved;
- all existing V1.2/RFQ-002/RFQ-003 regression tests included.

Initial test setup defects RESOLVED: developer Python lacked tzdata lookup; reused already-installed IANA data for tests. A missing parent .tmp and duplicate pytest module basename were repaired, then reran final focused/full checks. Early failure is not reported as passing evidence.

## Safety / worktree / remaining UNKNOWN
No live INSO/Google/CDP/credential access, real Save, Save-and-Send, Google writes, quote update, Apps Script, SMTP, real business submission or historical replay. No build/release/deployment work. Read-only local EXE SHA256 remains
`1A49C9650BA531F2299326FFC89761D0391CD5F2C0FE32327DDD0736BD5C3E84`.
Original dirty main checkout, local feature/v1-2 ref (241fd48), and reviewed remote V1.2 (c8d514e) preserved; no reset/overwrite/force-push. Managed rfq004-v13 worktree is the sole active RFQ-004 implementation worktree and stays attached for CEO review. v1-2-design carries deployed runtime, hotfix worktree is unrelated, main carries unknown dirty files: none can be safely retired by this task. No RFQ-004 temporary handoff was consumed or created; no stale RFQ-004 worktree removed.

UNKNOWN (live-only): actual current contiguous header/display layout (including virtual/fixed-column DOM behavior), exact live text rendering and raw Date formatting, real session/query behavior and latest quotations against authorized production records. Synthetic fakes prove adapters/boundaries, not live DOM acceptance; reader fails closed on unrecognized structure. Actual authentication/security challenge/server behavior is not claimed from offline tests. Live validation is intentionally deferred under RFQ-004 safety boundary; final scheduler/GUI/mail/writeback/EXE are RFQ-005/006 scope.

Delivery: REVIEW_REQUIRED, not REVIEWED_DONE; no executor REVIEW.md or PASS verdict. Commit/push feature/v1-3 and local/remote equality are verified after this record is committed; no self-referential commit SHA in tracked documents.


## CEO B1 repair — 2026-10-07 — current delivery

Synced the existing clean feature/v1-3 worktree by fast-forward to CEO Review
`3872c63b88a3778ccedd4d2fbd42f7d0ade25e80`. Read current REVIEW/TASK_SPEC/log/report/
COORDINATION and module boundaries. Only B1 is repaired. REVIEW.md and Owner
TASK_SPEC remain unchanged; no executor Review verdict. CHANGES_REQUESTED ->
IN_PROGRESS -> REVIEW_REQUIRED. The earlier claim that orphan/ambiguous/changed
source identity must GLOBAL_STOP is SUPERSEDED by this row/global split.

Root cause: read_v13_candidates raised global faults during batch binding, before
first-row query; re-read row conflicts were also converted by a broad exception
handler into V13_READ_UNAVAILABLE. Global snapshot uniqueness further rejected
two distinct original-position orders with identical fields.

Production changes only:
- src/sheets/quotation_candidates.py: strict original-position-first verification
  with current sent status, schema-specific importance/model/quantity and the
  original or persisted UPDATED expected brand. Validation reuses relocate_record
  on the anchored row. Only a failed original anchor enters existing unique
  relocation fallback, with exact expected brand filtering. Zero matches remain
  row conflict; multiple matches carry a typed QuotationSourceAmbiguous with safe
  source row positions. Original inquiry_id/record_identity are never regenerated,
  modified or persisted. Standard and SHAHAB schemas reuse existing semantics.
- src/workflow/v13_quotation.py: source scan returns ordered candidate-or-error
  entries; cycle returns each bad row at its source position and processes later
  valid rows. ROW_FAILED plus fixed RowErrorReason codes SOURCE_IDENTITY_UNRESOLVED,
  SOURCE_IDENTITY_AMBIGUOUS, SOURCE_MPN_UNAVAILABLE, SOURCE_CHANGED is the future
  RFQ-006 red/log/229 boundary, without GUI/mail integration here. Unbound results
  have inquiry_id/record_identity=None, and retain only worksheet/current-row
  observation for locating the failure; that location is NOT a new business ID.
  Bound row errors keep original identity. No row-error wait, tab open or retry.
- The cycle still get_by_inquiry_id/re-reads before every actual attempt. A missing
  individual inquiry, changed identity/status/snapshot or ambiguous source becomes
  ROW_FAILED, continuing next row. All historical bindings are checked for
  competition both at scan and at fresh re-read: one current row cannot be claimed
  by two original inquiries or silently rebound to a different inquiry. Only
  related rows fail. Identical stationary orders resolve their own original anchors.
- Shared reader/schema/ledger failures are sanitized GLOBAL_STOP in narrow external
  read boundaries, including all_items/get_by_inquiry_id database failures. The
  broad cycle catch no longer invents a GLOBAL_STOP classification for arbitrary
  Python errors: it only cleans up and re-raises unexpected errors. INSO retry,
  auth/manual verification and CDP faults retain existing semantics unchanged.

No browser/CDP/session, duplicate_history, retry engine, V1.2 flow, Save-and-Send,
GUI, notification, schema/migration or persistent identity table changes. No new
worktree or dependencies. Existing worktree remains attached for independent Review;
other worktrees/runtime and all prior execution records remain preserved.

Tests: tests/workflow/test_rfq004_b1.py adds 25 parameterized cases: source-ordered
valid/bad/valid with separate closed tabs/no waits; identical stationary orders;
replaced original position with unique relocation; genuinely ambiguous fallback
with later valid row; competing historical identities; four missing/non-string MPNs;
five re-read status/model/brand/quantity/importance conflicts; scan/re-read shared
Sheets failure; both ledger database access failures; individual missing identity;
row conflict after one INSO retry wait; competition introduced at fresh re-read;
standard/SHAHAB strict anchor/persisted brand; changed ledger identity; attempted
re-binding to another inquiry. Existing old global row-failure expectations updated
to current row outcomes, while INSO exhaustion/manual protection tests retained.
The old blanket duplicate-snapshot fail-fast parameter is superseded by the explicit
original-anchor/true-ambiguity B1 cases, not by relaxed identity matching.

Final verification, existing developer Python 3.12 and existing bundled IANA data
via the same PYTHONTZPATH recorded above (no installed dependencies):
- `python -m pytest -q tests/inso/test_v13_quotation_read.py tests/workflow/test_v13_quotation.py tests/launcher/test_v13_quotation_operations.py tests/workflow/test_rfq004_b1.py --basetemp=.tmp/rfq004-b1-focused-final --tb=short`:
  **72 passed in 0.68s**, exit 0.
- `python -m pytest -q tests --basetemp=.tmp/rfq004-b1-full-final --tb=short`:
  **1125 passed / 1 skipped in 47.78s**, exit 0. Existing RFQ-002/RFQ-003/V1.2
  regressions included; no outbound-mail attempt warnings.
- `python -m ruff check src tests`: PASS. `git diff --check`: PASS.
  Scoped diff reviewed; no unrelated source changes or generated files staged.

Both required centerpiece cases PASS: valid/bad/valid preserves source output order
and queries only the two valid rows; same-snapshot original rows10/11 map separately
to their own inquiry IDs and exact original identity objects. All clocks fixed aware
ZoneInfo; all retry waits fake. Existing no-quote/72h/latest/raw14/no-content-validation,
full paging/owned-tab/shutdown/INSO global-stop and verification-page tests PASS.

Safety: no live systems, credentials, real Save/Save-and-Send, Google writes,
quote update, Apps Script, SMTP, true business submission or historical replay.
No build/deploy or V1.2 EXE overwrite. Read-only EXE hash remains
`1A49C9650BA531F2299326FFC89761D0391CD5F2C0FE32327DDD0736BD5C3E84`.
Remaining live-only UNKNOWNs unchanged: actual fourteen-column/header/raw display
layout and Date format, real INSO quotations/query/session/security behavior.
Offline proof is not production acceptance. RFQ-006 GUI/email/manual-completion
integration remains out of scope. Commit/push and actual local/remote HEAD equality
are verified after committing these records; CEO REVIEW.md is left intact.
