# RFQ-005 Execution Log — 2026-10-07

## Baseline / reuse audit
Fetch and fast-forward reached exactly 5582df1fbc1d69b70925985cd2646a5882fd9792;
RFQ-004 CEO PASS/REVIEWED_DONE confirmed. Reuse existing clean managed rfq004-v13
worktree and feature/v1-3; no new branch/worktree. Read RFQ-004 records, current
source adapters, row/identity contracts, Google writer/reader/OAuth and launcher
fixed-CDP/session wiring. V1.2 checkout/release unchanged.

Reuse existing passed quote DTO/selector unchanged, Sheets service values API
RAW writer pattern and protected non-interactive cached grant service, original
ledger queries and reviewed anchor/fallback. No existing quotation input geometry,
gid, Google Sheets UI update/popup adapter or confirmed role contract found in
tracked code/docs/config. Do not read credentials or explore production to invent
those facts. Add explicit mandatory geometry configuration and narrow text/role
UI contract with LIVE_SELECTOR_ACCEPTANCE=UNKNOWN. No default A1:N1 or Script URL.
Shared column schema is supplied from RFQ-004 QUOTATION_COLUMNS by launcher wiring,
not copied or imported across forbidden Sheets->INSO dependency.

Only necessary RFQ-004 extension: expose the same read-only anchor/fallback with
explicit accepted statuses so RFQ-005 can verify Script's sent->quoted transition;
existing relocate_quotation_source wrapper stays sent-only and unchanged behavior.
No new state table, identity, retry engine for INSO, browser or credential stack.

## Boundary
Fake/offline only. No real Google input/update/Script, INSO Save/Save-and-Send,
SMTP, order replay, production credentials/browser access, build/deploy or EXE
replacement. Review belongs to CEO. Final integration remains RFQ-006.


## Implementation / reviewed upstream preservation
- src/sheets/quotation_input.py: QuotationInputLocation requires explicit worksheet
  报价输入, header_row, first input_row, first_column, gid and existing spreadsheet
  ID. No default geometry or magic A1:N1. Configured contiguous fourteen-cell header
  range must exactly equal the RFQ-004 columns supplied by launcher composition.
  GoogleQuotationInput writes a complete one-row/14-string values.update with RAW,
  reads UNFORMATTED_VALUE as strings and pads only omitted trailing cells with "".
  Missing/invalid whole schema/response/auth/access/API raises shared
  QuotationInputUnavailable. Targeted write/timeouts/readback mismatch are sanitized
  QuotationInputAttemptFailed. HTTP 400/401/403/404/429/5xx and authorization/refresh
  errors are shared failures, not silently row-only write errors. No source setter.
- src/quotation/update_result.py: pure strict title/label/count parser with whitespace
  normalization solely for popup display. One inserted row or zero inserted/one
  existing row is successful; existing alone one is accepted; duplicate labels,
  conflicting/negative/unexpected counts, generic success and absent text stay
  UNCONFIRMED. No pricing or payload cleaning.
- src/workflow/v13_quote_update.py: consumes QUOTE_FOUND and returns original
  NO_RECENT_QUOTE/ROW_FAILED objects untouched without source/input/UI access.
  Uses original ledger lookup and fresh source reads; validates original identity,
  explicit persisted UPDATED brand, strict original anchor/unique fallback and
  competing history. Missing/changed/ambiguous source is row-only SOURCE_CHANGED;
  external ledger/Sheets reads remain typed GLOBAL_STOP. No INSO query or reselection.
  Input stages get initial+3 complete write/read attempts, with an additional exact
  read immediately before each click to reject overwritten data. Update gets
  initial+3 safe attempts; each failed surface is closed and each next attempt
  reopens fresh, rechecks status, validates schema and rewrites/rereads all cells.
  Four input attempts apply per input-establishment stage; successful stages on
  four update attempts rewrite four times. Google retries have no 180s waits.
- Before any resubmit, source already 采购已报价 => UPDATED_ALREADY_EXISTS without
  another write/click; other status => ROW_FAILED. A successful popup is final
  action proof: even dismiss-control failure only proceeds to status verification,
  never another update. Status verification max3 reads, default1s between reads
  (at most2 waits), injected interruptible wait and stop flag; exhaustion becomes
  SOURCE_STATUS_NOT_UPDATED, not resubmission. V13Stopped propagates shutdown.
  Returned DTO is dataclasses.replace of the upstream, preserving original ID,
  original identity and quotation raw payload. No persistent state/quarantine.
- src/launcher/google_quote_update.py: narrow URL/gid + exact text/role contract on
  caller-supplied reused protected BrowserHandle. Independently owned Google tab,
  no Chrome/profile/CDP acquisition, cookie/reset, credential or Script URL code.
  Sole submit is button 更新报价; result dialog 报价更新完成; dismissal 确定.
  Old visible popup cannot be reused as current proof. Login/manual/access pages
  preserve their human-needed tab and throw shared fault. Context/disconnection
  failure is shared; navigation/button/dialog uncertainty permits bounded retry.
  Cleanup closes only owned tab; retain/create blank first if it became last tab.
  build_v13_quotation_updater is a no-I/O factory, injecting RFQ-004 column names,
  existing read/write service, existing source reader/store and protected handle.
  It does not invoke OAuth consent or create another production config. Later
  composition must use the existing cached write builder allow_interactive=False.
- Minimal frozen-RFQ-004 extensions only: Sheets locator's unchanged sent-only
  wrapper delegates the same exact logic with explicit accepted_statuses; RFQ-005
  reads sent/quoted transitions without changing original identity or writing
  status. Add UPDATED_INSERTED/UPDATED_ALREADY_EXISTS and four row reasons to
  existing enums. No INSO selection, B1 fault isolation, raw DTO or retry changes.

Row failure codes: QUOTE_INPUT_WRITE_FAILED, QUOTE_INPUT_READBACK_MISMATCH,
UPDATE_RESULT_UNCONFIRMED, SOURCE_STATUS_NOT_UPDATED, SOURCE_CHANGED (upstream
RFQ-004 failure reasons pass through unchanged). Shared failures preserve existing
FaultScope.GLOBAL_STOP. No GUI/mail implemented. One updater run is serial; final
exact read rejects observed concurrent/stale input before click. No atomicity is
claimed against an external process editing after that final read; shared-input
operational ownership must be enforced during RFQ-006 live integration.

## Offline acceptance / final evidence
82 new RFQ-005 parameter cases across Sheets, pure popup parser, Workflow and
launcher; focused also includes all72 RFQ-004/B1 cases. Synthetic Google UI/API/
Script callbacks only. No production credentials/browser/network/writes used.

Final environment uses existing Python3.12, with existing bundled IANA data via
PYTHONTZPATH as recorded in RFQ-004 (no new installed dependency). All source rows,
popups and waits are deterministic fakes. No actual sleep or 180-second Google wait.

Focused:
`python -m pytest -q tests/sheets/test_quotation_input.py tests/quotation/test_update_result.py tests/workflow/test_v13_quote_update.py tests/launcher/test_google_quote_update.py tests/inso/test_v13_quotation_read.py tests/workflow/test_v13_quotation.py tests/workflow/test_rfq004_b1.py tests/launcher/test_v13_quotation_operations.py --basetemp=.tmp/rfq005-focused-final --tb=short`
**154 passed in 0.87s**, exit0 (82 RFQ-005 +72 RFQ-004/B1).

Full safe/offline:
`python -m pytest -q tests --basetemp=.tmp/rfq005-full-final --tb=short`
**1207 passed / 1 skipped in 47.72s**, exit0. Existing RFQ-001/002/003/004 and
V1.2 regressions included; no outbound SMTP attempt warning.

`python -m ruff check src tests`: PASS. `git diff --check`: PASS.
Scoped/staged diff reviewed before commit, no runtime/generated files/customer
output or secrets. Initial fake fixture counters/type mistakes were RESOLVED:
source status sequence aligned with actual fresh read checks, dialog count returns
boolean count, and same-snapshot edited fake case replaced with distinct orders
rather than weakening approved B1 competition safety. Final tests above pass.

Acceptance coverage includes non-quote passthrough; raw14/date/zeros/decimal tails/
empty overwrite/whitespace/newlines/odd business content; exact RAW request and
padding; schema geometry/shift/shared HTTP failure; write and readback recovery/
four-attempt exhaustion; final stale read rewrite; strict inserted/existing/zero/
unknown popup counts; missing/hung/click timeout/repeated update attempts and full
rewrite; successful popup/dismiss failure never repeats; source short delayed
status and exhaustion; source already quoted/no repeat; retry source conflict;
original/moved/ambiguous sources; shared reader/ledger faults; independent UI tabs,
no old-popup reuse, navigation hang, last-tab preservation, actual UI auth through
updater with human-page retention, shutdown/no-work factory and no quarantine.
Success/bad/success tests PASS for targeted input failures and real source locator
plus fake Script transitions, with normal adjacent rows having zero added wait.

## Safety / UNKNOWN / delivery
No real Google quotation input, 更新报价, Apps Script, Save, Save-and-Send, SMTP,
true business submission, history replay, production credential access, packaging,
release or deployment. No V1.2 source business changes. Current V1.2 EXE remains
`1A49C9650BA531F2299326FFC89761D0391CD5F2C0FE32327DDD0736BD5C3E84`.

UNKNOWN: actual first input/header row and starting column, gid and schema geometry;
Google 更新报价/dismiss/dialog roles and DOM; actual Script refresh latency;
Google login/security/permissions and real operational behavior. All configured
geometry in tests is explicitly synthetic, not a production claim.
LIVE_SELECTOR_ACCEPTANCE=UNKNOWN. No live acceptance is claimed from offline tests.
Range contract must be supplied/confirmed before future real use; missing location
fails closed. Final scheduler/GUI/229/module integration/live acceptance/package
are RFQ-006 scope, not silently enabled by this source delivery.

Existing V1.3 worktree reused and retained for CEO review; no handoff or duplicate
worktree created, other worktrees/protected assets preserved. RFQ-004 review/spec/
records untouched. RFQ-005 REVIEW_REQUIRED only; no REVIEW.md or PASS verdict.
Commit/push and actual local/remote HEAD equality are verified after committing
these records, without inserting self-referential commit metadata.


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


## Repair implementation / reuse / scope
Fetched and fast-forwarded feature/v1-3 to CEO review commit
b4c1ea6; reused the existing rfq004-v13 managed worktree. No new branch/worktree.
Full-name search across src/tests/docs/control-room/RFQ-005/tasks found current
wrong-name references only in quotation_input, its fake fixture/range assertions,
and the previous execution/final report. All current configuration references now
use 报价输入; CEO REVIEW.md remains byte-for-byte unchanged as historical evidence.
This correction paragraph documents the prior name error explicitly.

Reuse GoogleQuotationInput/QuotationInputLocation, canonical factory's same location,
existing service/OAuth, raw14/readback, workflow error mapping and retry/UI/source
contracts. No parallel path or new dependency. Source changes limited to:
- src/sheets/quotation_input.py: exact correct title; minimal metadata binding
  helper; metadata -> headers -> write ordering, including direct write calls.
- src/workflow/v13_quote_update.py: pre-open validation, so invalid gid never opens.
Tests use synthetic metadata service plus existing fake UI/source, not production.
Existing RFQ-004 source/tests/control-room and V1.2 source/release are unchanged.
No production credentials, browser, Google API or other business access performed.
Metadata request exceptions become QUOTE_INPUT_METADATA_UNAVAILABLE without raw
provider text; malformed properties become QUOTE_INPUT_METADATA_INVALID; absent,
duplicate or mismatched target becomes QUOTE_INPUT_LOCATION_BINDING_MISMATCH.
All map to GLOBAL_STOP, never row-only faults. No cached permanent validation token:
every direct write repeats metadata/header checks, protecting against stale reuse.

## Repair verification
28 additional cases; focused182 (110 RFQ-005 +72 RFQ-004/B1).
Focused command:
`python -m pytest -q tests/sheets/test_quotation_input.py tests/quotation/test_update_result.py tests/workflow/test_v13_quote_update.py tests/launcher/test_google_quote_update.py tests/inso/test_v13_quotation_read.py tests/workflow/test_v13_quotation.py tests/workflow/test_rfq004_b1.py tests/launcher/test_v13_quotation_operations.py --basetemp=.tmp/rfq005-b1b2-focused --tb=short`
182 passed in 0.88s, exit0. Existing PYTHONTZPATH to bundled tzdata reused;
no dependency installation. Added actual API adapter through workflow cases for
wrong gid, gid on another sheet, absent/duplicate title, malformed response/sheets/
properties/title/ID, missing ID, bool/string/float/negative ID, metadata provider/
auth/401/403 failures, correct binding but bad14 headers, inserted/existing success.
Fault cases assert zero writes, UI opens and clicks; metadata faults also zero
header reads. Direct writes prove minimal metadata request -> header -> RAW write,
and repeat validation rejects a changed binding. Correct sheetId0 accepted;
noncanonical gid027 fails exact string binding. Old title constructor rejected.
Full safe/offline:
`python -m pytest -q tests --basetemp=.tmp/rfq005-b1b2-full --tb=short`
1235 passed, 1 skipped in 47.70s, exit0. Includes V1.2/RFQ-004 regressions.
`python -m ruff check src tests`: PASS. `git diff --check`: PASS.
No new business UNKNOWN; only documented live geometry/gid/DOM/Script delay/session
UNKNOWNs remain. No live acceptance or self-issued CEO verdict. REVIEW_REQUIRED.
Scoped final diff checked, historical REVIEW.md and frozen RFQ-004 unchanged;
no generated runtime output, dependency or secret added. Commit/push with actual
local/remote equality verified after recording these non-self-referential results.
