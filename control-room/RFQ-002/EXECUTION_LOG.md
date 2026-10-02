# RFQ-002 Execution Log — sanitized publication record

## CEO Review B1 repair — 2026-10-02

Synced feature/v1-2 by fast-forward to CEO Review commit 2f89580. Read REVIEW.md,
this log and FINAL_REPORT.md. B1 is addressed for independent re-review, not
self-certified PASS. Reused existing writer, gates, fake form and store fixtures;
only the two obsolete tests in tests/inso/test_v12_purchase_writer.py changed.
The callable Save-and-Send API is allowed to exist, but default production and
ordinary fake gates reject it before store or click dispatch. Standalone Save
remains closed by default; generic send/submit methods remain absent. The
non-recognized store test retains its Save rejection and confirms unauthorized
Save-and-Send makes no additional store calls and no form events.

Actual offline checks:
- Focused: python -m pytest -q tests/inso/test_v12_purchase_writer.py ->
  56 passed in 0.61s. Initial edit incorrectly expected an empty fake-store call
  list after the existing rejected Save attempt; corrected only that test to
  compare its pre-call snapshot, then all focused tests passed.
- Full: python -m pytest -q tests --basetemp=<new workspace .tmp directory>
  --tb=short -> 921 passed, 11 skipped in 34.07s, exit 0. Default OS pytest temp
  directory initially caused 159 setup permission errors (763 passed, 10 skipped);
  diagnostic confirmed WinError 5 at pytest-of-Leo. Reran the entire unchanged
  suite using a newly generated, non-existing workspace temp path, not by
  excluding failing tests or deleting another user's temporary directories.
- python -m ruff check src tests -> All checks passed, exit 0. This scope does
  not include the previously recorded unchanged release-script style findings.
- git diff --check -> PASS.

Only tests and Control Room records changed; no production source, runtime,
dependencies or build tools changed. No repackaging: existing V1.2 EXE retained.
Tests use synthetic/local fixtures and the existing suite-wide SMTP guard;
no real Save, Save-and-Send, SMTP, Sheets writes, production order/browser action
or old-order replay. First real final submission still belongs to Owner's next
genuine order. Prior statements that no new offline regression was run are
SUPERSEDED by these results, not by any real submission or packaged-chain proof.
RFQ returns to REVIEW_REQUIRED; REVIEW.md remains the CEO-owned prior verdict.

## Publication scope

2026-10-02: Owner explicitly requested committing/pushing the current work to
feature/v1-2 so CEO chat can review it through Git. The accumulated WorkBuddy
and executor source/tests/docs are one RFQ-002 implementation checkpoint.
Original local execution/summary records contained raw business evidence;
preserved unchanged under Git-ignored .tmp/rfq002-before-publish before replacing
these publication records with sanitized technical facts. No production data,
credentials, raw probes, EXE, runtime DB/Excel or screenshots are committed.

Remote fetch found nine documentation/rule commits beyond the local baseline
51d17ba3aac6658bad25e468358aa1e6f51186f9. They change governance and the older
RFQ plan, not production code. Preserve them through a normal merge, not force
push; latest Owner submission/packaging decisions remain explicit in TASK_SPEC.
Independent Review remains required; REVIEW_REQUIRED is not a PASS verdict.

## Reuse and prior Phase A integration

- Reused stable V1.1 config, Sheets/OAuth, Research, Workflow, Core Vault,
  Chrome/CDP, GUI, additive/backup-safe SQLite readiness and release tools.
- Normal production entry composes existing V1.2 workflow directly; missing
  adapters fail visibly, not silently V1.1-only. No alternate production path.
- Shared authentication uses native login -> home -> business-inquiry menu;
  no direct list shortcut for purchase forms. CAPTCHA/OTP/device checks remain
  manual, no bypass. Site-login sweep uses the single protected CDP.
- Duplicate checking uses complete LOWER procurement temporary inquiry history,
  true creator, quantity and timestamps; does not use upper business inquiry
  history or Research quote eligibility filtering. Workflow rolling 168h rules
  remain unchanged. Native paging/completeness reused.
- Completed Research waiting for duplicate confirmation rejoins the normal
  routing without redoing Research, clearing queues or forcing purchase resets.
- Existing native draft/customer/type/purchaser, AI preview/client-side handoff
  and parent model/brand/quantity/product identity validation were reused.
- Explicit native Findchips no-result response for the searched model is an
  empty source outcome, not a technical error; generic blank/error/login/script
  pages and conflicting offers do not become valid no-results.
- Notification decisions use original business rules. Created commands remain
  immutable; sent recipient ledger entries are not resent, existing worker owns
  permitted retries. Real SMTP previously authorized and observed as accepted
  for canonical important/duplicate notifications, not proof of inbox delivery.
- Earlier normal source runs reached duplicate-stop and successful unsaved
  parent draft validation. Raw business evidence remains local and is not in Git.
- Earlier full regression: 926 passed / 11 skipped. This precedes the final
  submission/packaging changes and must NOT be used as their regression proof.

## Latest Owner-authorized submission delta

Owner accepted the unsaved draft results, removed automatic screenshot scope,
authorized a single final 客临时询价 Save-and-Send, relaxed ten-line ceiling and
requested personal Review. Owner expressly forbids executor testing of this
final step; first actual verification is the next genuine Owner order.

Nine existing source files implement this bounded connection; detailed inventory
is FINAL_SUBMISSION_REVIEW.md. No new browser/workflow/config/dependency/migration.
Automatic production draft screenshot hooks and screenshot-only tests removed;
old local evidence preserved.

Sequence: read settled upper first-row ID before draft; existing draft and
AI/parent validation; durable AI_RECOGNIZED; exact authorized final form control;
transactional UNKNOWN + SAVE_DISPATCH_ARMED before one click; Playwright five-
second wait; native surface dismissal; same upper query and first-row new-ID,
model and current-time confirmation; existing saved/manual-review transitions.

Owner confirms native newest-first order: final confirmation uses only page 1,
rows[0]. Adapter first_page_only opt-in retains request/HTTP/JSON/sequence/pending
checks and response/cache/DOM identity and order; proves first-page expected row
count, not complete history. Default complete-set query remains unchanged.
Upper history exceeding one page does NOT block submission. Lower seven-day
procurement history still requires full pagination.

Timestamp parsing reuses Asia/Shanghai parser. Minute-resolution lower bound is
the submission minute; upper bound is post-query observation. Changed first-row
stable ID excludes the previous top row. Missing/stale/wrong first row or lookup
failure -> manual review, never confirmed absence or automatic resend. Record
appearance does not prove delivery to downstream suppliers.

ProductionWriteGate.require_open remains closed. Only explicit normal production
composition injects OwnerAuthorizedSaveAndSendGate. Standalone Save Data, generic
Send and Sheets writes stay closed. Default/Fake gates do not enable the new
action. Unique visible/enabled control, exact ID/role/caption/scope and final
identity recheck precede dispatch.

Any existing purchase state prevents repeated routing/submission, including old
accepted unsaved test drafts. No automatic historical backlog submission. Submit
exceptions do not enter pre-submit session retry. UNKNOWN persists through
restart; baseline is in-memory, so legacy old-record reconciliation refuses new
submission markers on restart. Uncertain outcome requires actual INSO inspection.

Only app-created operation tab is returned after operation contexts end; Owner
tab and protected browser/context stay open. Profile and port remain canonical.

## Packaging and local deployment

Owner explicitly authorized EXE packaging after Review discussion, superseding
prior Phase B deferral. Reused build_windows_release.ps1 and existing spec with
Version parameter, default 1.1 retained and distinct 1.2 staging/artifact names.
Same icon/assets/hooks/scanner/self-check. V1.1 directory never replaced.

Command: powershell -ExecutionPolicy Bypass -File
scripts/build_windows_release.ps1 -Version 1.2. PASS.
Sandbox Tcl initialization failed; same installed Python under Owner identity
returned Tcl 8.6.15. Build collected Tcl/Tk runtime correctly without reinstall.
Clean artifact RELEASE_SCAN_OK; frozen --self-check exit 0.

Deployed EXE: D:\Program_Leo\INSO_Leo\dist\INSO_V1.2\INSO_V1.2.exe.
SHA256: 99F131DBDFC69C961121FF896FF8C9573C0BC0CBAB3D73B1BEFF60455E095D7C.
Local runtime junction points to the active worktree's existing V1.1 runtime;
preserves configs, SQLite, Excel and historic purchase state without copying
business data into the generic artifact. Deployed private runtime directory is
NOT a portable clean distribution. Do not archive its target worktree before
safe runtime relocation.

Normal EXE launch smoke: window INSO_V1.2, responding, nonzero window handle;
default ProductionBackend remains STOPPED. Own smoke instance PID 36596 closed
normally with exact-path validation, no force kill. No Start Inquiry action or
packaged business-chain execution. Protected CDP not accessed by build/smoke.

## Checks and limitations

- Source Ruff PASS; scoped changed-source/test Ruff PASS; PowerShell parse errors
  zero; git diff --check PASS (pre-existing CRLF warning only).
- Expanded Ruff on unchanged windows_release_entry.py found three existing
  style findings; do not claim full-repository Ruff PASS.
- No new pytest/fake dispatch/replay/final-submit test under Owner restriction.
- No production order, SMTP/Sheets/INSO write, credential readiness probe or
  browser interaction during final implementation/packaging/publishing.
- New final submit and packaged complete business chain are NOT verified.
- Publishing this checkpoint does not establish acceptance/Review PASS. CEO must
  review current diff; first genuine final submit remains Owner's responsibility.
- Raw local probes/test output/runtime/EXE are excluded, not deleted. Source
  merged/pushed through normal history; inspect CEO_REPORT.md for Review scope.
