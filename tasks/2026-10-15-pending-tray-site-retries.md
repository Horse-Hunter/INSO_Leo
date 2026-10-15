# Owner increment: pending status, tray close and site retries

status: REVIEW_REQUIRED
created: 2026-10-15
owner: Codex

## authority / boundaries
Owner requests diagnosing many pale-yellow pending-Sheets statuses, checking all
research-site login retries and notifying only after three retries still fail.
Owner confirms window X means hide to system tray/remove taskbar entry while
business continues; only tray Exit performs existing graceful application exit.
Inspect existing source/tests and scoped read-only installed runtime metadata,
pending-state counts and matching current Google source statuses via existing
cached read-only grant if needed. No raw customer/model/price/mail output in Git.
No live Sheets/DB writes, SMTP, business replay, credential changes, CDP attach,
browser navigation, package or deployment. No new dependency; preserve dirty work.

## reuse / plan
Reuse PurchaseCompletionActions/source-status identity checks and current GUI
projection; distinguish real pending writes from stale local state, never hide a
real failure or resend procurement. Reuse existing source_query and site login
sweep/recipes, stop-aware waits and outbox; add initial+three bounded retries for
transient login/read failures before source failure observation/mail. Preserve
manual security-challenge and rejected/missing-credential safeguards.
Reuse GUI event queue and existing graceful close for tray commands; implement
only missing native tray capability with standard-library Windows APIs.

## acceptance
Evidence-based explanation of pending rows; read-only confirmed advanced status
can settle safely without writes/replay. Window close hides with active tray,
restore returns window, Exit drains workers and removes icon. Site retry coverage
includes all research sources, recovers without premature mail, interrupts on
stop, preserves human verification and no empty-result retry. Focused/full offline
tests, scoped Ruff/diff, retire only known disposable test artifacts; REVIEW_REQUIRED.

## Findings / implementation
Read-only production metadata: 7 pending-status inquiries, all purchase outcomes
SAVED. Existing status-write notification history:8 SheetRecordConflict and1
GoogleSheetsAuthorizationError (history counts, not7 new failures). Scoped source
read confirmed all7 matching model/quantity/importance rows are now 已报价给客户.
No model/customer/price/body or raw row persisted. Initial sandbox grant-unprotect
failed; authorized read-only context succeeded, no cache/token writes or new consent.

Root cause: purchase-status satisfaction recognized only 发给采购 / 采购已报价;
later approved statuses could not settle the durable local warning. Extended only
the read-only completed-status whitelist, preserving unique snapshot/brand checks,
pending-row holds and unknown-submit safeguards. No live ledger repair was run.

New gui/tray.py supplies the missing native icon/menu/window message loop using
ctypes only. GUI X hides only after successful icon setup; restore/exit commands
travel through the existing Tk main-thread queue. Exit reuses the old drain and
shutdown; icon/window/thread cleanup handles normal exit and initialization errors.
Stock application icon; custom branding is not required for this functional fix.

Site retry audit: old source_query retried CDP failures only; login sweep attempted
each site once; INSO query called failure observer before exhausting its existing
retry loop. Added shared closed retry classification and bounded2/5/10-second
interruptible waits for ICNET/Findchips/HQEW/LCSC/Bom.Ai. INSO retains original
initial+three120-second read retries without nested login retries or premature
transient-failure observation. Genuine no-match/no-price and FX remain unchanged.
Manual challenges and known missing/rejected credentials remain immediate.

## Verification and limitations
Scoped GUI/site/status/resilience:268 passed in20.00s. Full safe/offline suite:
1949 passed /1 skipped in97.66s. Final icon resource-cleanup hardening followed
the full run; final native smoke created/destroyed two self-owned test icons,
windows and message threads successfully. No actual installed GUI was operated.
All selected Python Ruff and diff checks pass. Initial focused run had a missing
parent basetemp (79 passes/51 fixture errors); parent creation fixed the test
environment and all scoped cases passed; no product failures hidden or disabled.

No package/deploy or real source/DB writes, SMTP, order replay or CDP attachment.
Installed behavior is unchanged until separately authorized packaging/overwrite.
Live tray menu clicks, actual installed-GUI taskbar hiding, real transient login
recovery, and all7 original brand/identity proofs at next deployed poll remain
unverified. Do not claim every historical yellow warning is already cleared.

Task-owned focused/focused-final/scoped/full basetemps are absent or retired;
no frozen build/staging generated, rollback/unknown prior artifacts retained.
Publication is limited to6 source modules,4 corresponding test files, the product
fact update and this record. Parent is the latest CEO review commit ec2c0cb, whose
review of the preceding increment is preserved. Existing isolated-index publication
keeps local dirty work/index/HEAD intact and uses the same remote V1.4 branch.


## CEO independent review — 2026-10-15

**CHANGES_REQUESTED; not authorized to package or overwrite V1.4.** Reviewed
the exact `98d7734` patch, current implementation and scoped test cases.
No code changed, no browser/production operation performed. Executor reports
1949 passed / 1 skipped; CEO did not rerun tests.

- **Blocking:** `src/core/site_retry.py:retryable_site_failure` defaults to
  retrying *every* reason not in its short denylist. The existing
  `src/launcher/site_login_sweep.py` classifies `LOGIN_REQUIRED` and
  `AUTHENTICATION_REQUIRED` as `NO_CREDENTIAL`, yet both are currently
  retried up to four attempts; `AUTHENTICATED_SHELL_UNAVAILABLE` and
  unrecognized/no-code exceptions also retry. This breaches the required
  immediate human/authorization stop, particularly for the included INSO
  sign-in sweep. Replace with a narrowly justified transient allowlist or
  equivalent exhaustive typed classification that fails closed.
- Add direct regression cases for `LOGIN_REQUIRED`,
  `AUTHENTICATION_REQUIRED`, `AUTHENTICATED_SHELL_UNAVAILABLE`, and
  unknown/no-code exceptions on both source-read and login-sweep paths;
  verify no repeated login, no premature mail for genuinely transient
  failures, and preserve the existing INSO budget.
- Pending-Sheets advanced-state read-only settlement and tray lifecycle
  architecture are provisionally acceptable based on source/tests, but
  native tray menu clicks, installed GUI taskbar behavior and actual site
  recovery remain unverified; avoid claiming live PASS.

**Next:** Executor fixes the single retry-classification boundary in the
same workstream, reruns focused/full safe offline checks, updates this
evidence and returns for independent CEO re-review. Protect deployed
V1.4, CDP, runtime, secrets and existing local changes; do not build/deploy.
