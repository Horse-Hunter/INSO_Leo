# V1.4 implementation publication — technical review evidence

Status: REVIEW_REQUIRED (independent CEO Review; no PASS claim)
Authority: Owner explicitly authorizes publishing all business implementation,
fixes and corresponding tests described in the 2026-10-13 CEO phase report, after
sensitivity checks and offline regression. Existing V1.4 branch only. No rebuild,
deployment, credentials, live orders, CDP/session or production-data operations.

## Scope and source of truth
Requirement/report: tasks/2026-10-13-ceo-phase-report.md (already published in
09feea2e0f26854000777db045d6a5743c5281f9). Publish selected src/tests changes,
three updated product/module documents and this single minimal evidence record.
Do not publish individual duplicate diagnosis/release reports or ignored helpers,
test copies, frozen builds, runtime data, grants, logs or attachments.

| Report capability | Implementation | Main regression evidence |
| --- | --- | --- |
| Missing/UNKNOWN brand reaches Research; verified blank-only backfill | workflow/service.py, workflow/v12_flow.py, launcher/backend.py, launcher/v12_composition.py, sheets/brand_write.py | workflow/test_v12_flow.py, workflow/test_workflow_v1.py, sheets/test_brand_write.py |
| Transient Google read retry + original next15min poll | sheets/google_reader.py, launcher/backend.py, workflow/v13_integration.py, workflow/v13_quotation.py, workflow/v13_quote_update.py | sheets/test_google_reader.py, launcher/test_backend.py |
| Clear inquiry/runtime/model-difference mail and truthful health | gui/main.py, launcher/purchase_completion.py, launcher/v13_integration.py, workflow/v12_flow.py | launcher/test_mail_clarity.py, launcher/test_purchase_completion.py, workflow/test_rfq006_integration.py |
| Independent SHAHAB threshold/routing, original A/S preservation | workflow/v12_rules.py, workflow/v12_flow.py, sheets/worksheet_schema.py, sheets/google_writer.py | workflow/test_v12_rules.py, workflow/test_v12_flow.py, sheets/test_pending.py |
| Manual purchase/quotation reconnect deferred-stop drain | launcher/browser_bootstrap.py | launcher/test_manual_order.py (real local Playwright clients, no CDP/network) |
| Completed sales/PDF -> guarded intent status across both sheets | launcher/sales_header.py, launcher/sales_intent.py, sheets/intent_status.py, sheets/google_writer.py | launcher/test_sales_order_preflight.py, launcher/test_sales_intent.py, sheets/test_intent_status.py, sheets/test_google_writer.py |

Paths in this table are relative to src/ or tests/ as appropriate. Brand policies,
canonical Google OAuth/reader/single-cell writer, single CDP/Core login, and GUI
result popup are reused. No new dependencies, config, scheduler or production path.
Operational one-row quote/status recoveries in the report were separately Owner
authorized; their ignored helpers/raw results are not business code or publication.
Specific LCSC failure and invalidated Google grant cause remain UNKNOWN.

## Git protection
Initial local HEAD: 4aa58022e52ebfb119a33c895a86acac5a8324d1.
Latest remote report HEAD: 09feea2e0f26854000777db045d6a5743c5281f9.
Only committed difference beyond the report is an unrelated local disk audit and
its merge. Use the existing isolated-index publication pattern to parent the
selected business snapshot directly on the latest remote, preserving local HEAD,
index and all dirty/unique files without reset/rebase/stash/force push or another
worktree/branch. Remote-only concurrent changes must be inspected before publishing.

## Verification / deployment relationship
Publication whitelist: 39 files —19 src modules,16 test files,3 updated product/
module documents and this evidence record. Existing phase report is inherited
unchanged from the remote report commit, not uploaded as another copy. All code
and test diffs manually reviewed; entire selected files scanned for private keys,
provider tokens, literal OAuth/token payloads and known real production samples.
Zero findings. Fixed notification recipients and Owner-approved customer/buyer
policy labels are application requirements, not raw messages/customer transactions.
No runtime configuration, database, attachments, production logs or secret stores
are selected. Ruff on all selected Python files and git diff --check passed.

Read-only installed EXE SHA256:
ad9207243cb69af35b0d26f9ce8b786e83dbfee8543a0035538eb28eb657e577
This equals the deployed hash in the phase report. All19 selected src modules
match their embedded installed code objects after normalizing only source filename
metadata and compiling with the same optimize=1 setting. No code execution, build,
GUI restart, production-data read or CDP attachment was needed for this comparison.

Current tests (2026-10-13):
- All16 corresponding changed test files: 469 passed in25.38s.
- Full safe/offline suite: 1921 passed,1 skipped in78.27s.
- Tests use synthetic transports/data. Real local Playwright-client regressions
  start/stop clients only, without browser launch, CDP attachment or websites.
- No tests changed/disabled to hide failures; no product code edits in this task.

## Artifact retirement / retained state
Retired the current focused/full basetemps, two earlier task-owned complete
intent-regression copies and the exact marked canonical V1.4 build staging after
validating its EXE hash. Approximately506 MiB of known disposable files retired.
Root/child reparse-point checks preceded deletion; no links followed or permissions
changed. Three older focused test directories could not be enumerated even in the
authorized context (UnauthorizedAccessException / PermissionDenied), so they are
specifically retained without forced cleanup. Active release, approved rollback
backup, minimal audit evidence, unknown dirty files, Git, runtime and CDP untouched.
Only small ignored publication manifest/audit summaries are retained for local
reproducibility; none are uploaded.

## CEO review and remaining live UNKNOWN
Review this commit's diff against09feea2e0f26854000777db045d6a5743c5281f9, the
existing phase report and the tests cited above. No duplicate implementation
reports, operational helper, binary, test copy or unrelated local disk-audit commit
is part of this publication. Remote branch/ref and selected blobs are verified
after normal non-force push; local HEAD/index/dirty-file hashes remain protected.

No new real-business acceptance was performed. Still unverified: a real Owner
single click exercising INSO/PDF completion followed by intent writeback across
both source sheets; real missing/duplicate matches, expired grants and uncertain
write popup; long-running simultaneous inquiry/quotation/order behavior and future
network/CDP stability. Prior separately authorized operational recoveries are
historical evidence only. Google read-then-write is not cross-client atomic CAS;
observed conflicts/uncertain writes require manual repair, never blind replay.


## Independent CEO Review — 2026-10-13

**Verdict: PASS — published code and offline-evidence scope only.** This review
does not assert live production acceptance or certify current runtime state.
Review range: `09feea2e0f26854000777db045d6a5743c5281f9..413f3108d752779fdedc8983e8d59823b08b3356`.

- Independently inspected GitHub code diffs for production launcher, workflow,
  Sheets, SHAHAB routing, missing-brand writeback, Google read retry and V1.4
  sales-intent, plus corresponding new/changed synthetic test coverage.
- Sales intent is reached only after verified fields/PDF and durable local receipt;
  two configured sheets are scanned for exactly one model+numeric-quantity match
  in the approved quoted/intent statuses. Re-read, fixed single-cell update,
  readback and no blind retry/manual-repair fallback are present.
- No duplicate release pipeline, second CDP, interactive grant flow, automatic
  INSO Save/Submit or background order polling was introduced in this diff.
- Executor reports 469 focused and 1921 full safe/offline tests passing
  (1 skipped); reviewer inspected code/tests and publication scope, **did not
  independently run the local test suite or exercise production business**.
  GitHub commit has no reported CI statuses.
- Residual limits: actual Owner single-click order/PDF→intent live acceptance,
  duplicate/missing/source-change failures on real Sheets, expired grants,
  simultaneous long-running jobs, and network stability remain unverified.
  The read/compare/write sequence is not cross-client atomic; a concurrent
  Sheets edit remains a manual-review risk, not a proven fixed race.

**Disposition:** Code review PASS; deployment was already Owner-authorized and
reported separately. Keep existing runtime/CDP/rollback untouched; do not
manufacture live orders or trigger duplicate submissions for review. Accept a
genuine future Owner order as the appropriate live acceptance opportunity.
No new RFQ status or live-acceptance claim is created here.
