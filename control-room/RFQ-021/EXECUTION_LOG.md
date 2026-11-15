# RFQ-021 — execution log (final release candidate)

## RFQ-021-R3 — CHANGES_REQUESTED follow-up (2026-11-15 late morning)

- **Status:** `PASS_SOURCE_SCOPE / RELEASE_HOLD / NOT_DEPLOYED`
- **Reviewed base:** `1314da5d` → **source commit built:** `1ef20c81`
- **Candidate:** 8,459,010 B / `faa3166d41db5a738348dc57f6adebbfcda0b3dbf29eb99f3549cf0d0d2596c1`, 2,872 files
- **Manifest:** `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256` (`accd463a…`); r1 and r2 manifests kept as `-r1` / `-r2`. **One candidate only.**
- **Self-checks:** `--self-check` 0, `--idle-self-check` 0, `--preview-self-check` 0 (two rounds, 3 s, `ok: true`), `RELEASE_SCAN_OK` ×2
- **Manifest recomputation:** 2,872/2,872 matched, 0 missing / 0 mismatch / 0 unexpected, `VERIFY_RESULT = PASS`
- **Tests:** full suite **4,248 collected / 4,245 passed / 2 failed / 1 skipped in 661.77 s** (`pytest-report-r3.xml`).
  Failed nodeids (identical to the untouched parent baseline `e59ce62f`):
  `test_backend_closes_only_owned_browser_after_runtime_thread_exits[False]` and `[True]`.
  Captured cause: `V12Fault(WORKFLOW_LEDGER_UNAVAILABLE) <- sqlite3.OperationalError(attempt to write a readonly database)` on the pytest temp database. No test deleted, skipped or deselected.
- **New tests:** `tests/launcher/test_rfq021_r3_scope_effects.py` (11). One R2/R3 test was **rewritten** (same intent, new contract): explicit `inquiry_ids` conflicting with `RunScope` is now refused.
- **Fixed in this round:** background `retry_saved_statuses`/`process()` scoping; conflict rejection; login sweep refused in any enforced scope; per-action audit (`edit` and `purchase` need the google target; quotation/tp refused); installer fail-closed on rollback integrity + verified DB backup; manual corrected (source SHA, single candidate, removed the old-EXE `--safe-preview` assumption; cold rollback and post-rollback restart are separate approvals).
- **Incident verdict:** `FAULT_CLASS_CONFIRMED / UNDERLYING_CAUSE_NOT_VERIFIED`; 10:40 read-only re-collection recorded in `INCIDENT-20261115.md`.

---

## RFQ-021-R2 — CEO review follow-up (2026-11-15 morning)

- **Status:** `PASS_SOURCE_SCOPE / RELEASE_HOLD / NOT_DEPLOYED`
- **Source commit built:** `1314da5d` (base `8cded532` + three P0 fixes)
- **Candidate:** 8,457,679 B / `74586eb29ed19e037e2045f481d4ed2226aa555a8f6ef7951028c873fa68d0ed`, 2,872 files
- **Manifest:** `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256` (`74ae29c7…`); the r1 manifest is kept as `…-manifest-r1.sha256`
- **Self-checks:** `--self-check` 0, `--idle-self-check` 0, `--preview-self-check` 0 (two rounds, 4 s), `RELEASE_SCAN_OK`
- **Manifest recomputation:** `verify_release_candidate.ps1` → 2,872/2,872 matched, 0 missing / 0 mismatch / 0 unexpected, PASS
- **Tests:** full suite **4,237 collected / 4,234 passed / 2 failed / 1 skipped** in 424.76 s (`pytest-report-r2.xml`). The two failures are the same `test_backend_closes_only_owned_browser_after_runtime_thread_exits[False|True]` nodeids that fail on the untouched parent commit `e59ce62f`; captured cause is `V12Fault(WORKFLOW_LEDGER_UNAVAILABLE) <- OperationalError(attempt to write a readonly database)` in the pytest temp directory. Isolated reruns pass; no test was deleted or skipped.
- **New tests:** `tests/launcher/test_rfq021_p0_scope_binding.py` (15) plus one UI-refusal test in `test_rfq021_safe_preview.py`.
- **Capability reduction:** quotation / TP / notification and the `smtp` target are now refused by scope validation because none of them can prove per-order isolation. See `REVIEW_FOLLOWUP.md`.
- **Incident:** see `control-room/INCIDENT-20261115.md`. The running program was the old `E9E3DA33…` EXE; the morning stop was `SHEETS_READ_UNAVAILABLE` caused by `SSLEOFError`, not a crash and not these code paths.

---

## RFQ-021-R1 — first delivery (superseded)

- **Status:** `READY_FOR_CEO_RELEASE_REVIEW` (superseded by R2)
- **Window:** 2026-11-15 02:00–03:05 Shanghai
- **Worktree:** `D:\Program_Leo\INSO_Leo\.worktrees\v16-rfq016-stabilization` (reused; no second worktree)
- **Branch:** `workbuddy/v16-rfq016-stabilization`
- **Source base:** `25894eface6ea622153d1573c19d0ca6b9ad72aa` (RFQ-018 PASS) + RFQ-021 changes
- **Source commit built:** `8cded532221571e99697af7668634afab3ea07af`

## 1. Takeover audit (read-only)

- Read `AI_START_HERE.md`, `AGENTS.md`, `control-room/CEO_HANDOVER.md`, `control-room/COORDINATION.md`, `RFQ-020/REVIEW.md`, `RFQ-019/{REVIEW,RELEASE_READINESS,RISK_REGISTER,RELEASE_PREP_REPORT}.md`.
- **Correction to the RFQ-020 record (CEO review item 2):** `docs/BRANCH_POLICY.md` is absent **on this branch** but present on `develop`; `control-room/RFQ-019/REVIEW.md` does exist — the CEO added it in `64dba150`. RFQ-020's log and JSON are corrected in this commit.
- **Correction to the RFQ-020 record (CEO review item 1):** the "23:00" later-observation timestamp was written from memory and post-dated its own commit. Corrected to the actual read time (~22:47, before `6f1b1d25`); no unauthorized action is implied by the original text.
- `git status --porcelain` clean at takeover; `25894efa` is an ancestor of the branch; no stash; only the pre-existing worktrees.
- Production snapshot at takeover: `INSO_V1.6.exe` SHA256 `E9E3DA33…`, PIDs 38948 + 34304 alive since 13:47, SQLite `dist/INSO_V1.2/runtime/production/workflow.sqlite3` 1,196,032 B mtime `1794679195`, Chrome 9222 reachable, 15 pages.

## 2. What was wrong, and the smallest fix that closes it

### B7 — normal GUI start is not a "view"

`src/gui/main.py` called `backend.start_process_services()` unconditionally, which runs `migrate_v12` / `V13HoldStore.migrate` / `MailResearchStore.migrate` / `recover_abandoned_notification_attempts` and starts the IMAP receive + SMTP outbox worker.

Fix (no new architecture):

- `ProductionBackend(preview_mode=True)` refuses `start()` and returns immediately from `start_process_services()` (defence in depth, even if a caller tries).
- `main()` now treats a plain launch as a **preview**: no process services, no Start, Start button disabled with 「安全预览（不启动业务）」, and a separate `--preview-mutex` (`Local\INSO_V1.2-preview`) so a preview can coexist with the running business instance without fighting over the single-instance lock.
- `--scoped-start` is the only path to business. `--start-inquiry` without it is **refused with a dialog (exit 2)**, never silently downgraded.
- `--preview-self-check` opens and closes the real dashboard twice and records the result.

### B5 — "inquiry_ids" was not a scope

`inquiry_ids` limited row intake only; quotation/TP/notification and every write stayed live.

Fix:

- New `src/launcher/run_scope.py`: `RunScope(inquiry_ids, modules, write_targets, approval_reference)` with validation — non-empty order ids matching `inq_[a-f0-9]{24,32}`, modules ⊆ {inquiry, quotation, tp, notification} and **must include `inquiry`** (it is the poll driver), write targets ⊆ {google, inso, smtp}, and **any write target requires `OWNER-APPROVED:<reference>`**.
- `ExternalWritePolicy` is the one object every adapter asks. Enforced with no scope ⇒ deny everything. `block_all_writes()` is sticky.
- Google writes: the policy is checked inside `PageResourceAdmission.begin_document_write` — the single lease every writer already takes (Sheets API `google_api_service.py:370`, browser fallback `google_web.py:557`, native quote click `google_quote_update.py:1085`). A refusal raises `DocumentWriteBlocked`, a `DocumentWriteHeld` subclass, so existing callers keep their "do not dispatch, do not retry" behaviour.
- INSO writes: `ScopedInsoWriteGate` wraps the **existing** `OwnerAuthorizedSaveAndSendGate`. It only adds a refusal in front; `SAVE_DATA` stays closed exactly as before. `test_scoped_inso_gate_never_reopens_the_production_save_gate` pins that.
- Modules: `_module_allowed()` gates `_v13_enabled` (quotation), the TP cycle, and notification dispatch. `_run_notifications()` is now the single dispatch choke point and stays silent unless **notification module and `smtp` target** are both in scope. All seven previous `coordinator.run_notifications(...)` call sites go through it.

### B6 — the hold died with the process

`PageResourceAdmission` kept document holds in memory only; a restart forgot that a request might be in flight.

Fix:

- New `src/workflow/write_intents.py`: `workflow_write_intents` table (additive, same DB) with `PENDING / UNKNOWN / SETTLED`. `begin()` commits **before** the caller can dispatch; `settle()` only on evidence; `mark_unknown()` keeps it open.
- `PageResourceAdmission` takes an optional journal. `begin_document_write` asserts the scope, then checks `open_reason(document)`, then commits the intent, all before the caller touches the network. A document with an open intent raises `WRITE_INTENT_PENDING`; an unreadable/unwritable ledger raises `WRITE_LEDGER_UNAVAILABLE` — both block the write.
- `hold_document()` marks its own intent UNKNOWN and **pops** it, so a later `end_document_write` cannot settle what just became uncertain.
- `end_document_write` settles only when the document carries no hold; settlement failure is swallowed on purpose (the row stays open, which is the fail-closed state).
- `_attach_write_journal` runs **after** `V12Store(db)` and refuses a DB file that does not exist yet — the first attempt created an empty file before migration and every poll failed with `V12SchemaMismatch`; that regression was caught by the suite and fixed.

## 3. Files changed

| File | Change |
|---|---|
| `src/launcher/run_scope.py` (new) | scope validation, external write policy, INSO gate narrowing |
| `src/workflow/write_intents.py` (new) | durable write-intent journal |
| `src/research/cdp_pages.py` | policy + journal in the single write lease; `DocumentWriteBlocked` |
| `src/launcher/backend.py` | preview mode, scope enforcement, module gating, notification choke point, journal attach, INSO gate |
| `src/gui/main.py` | plain launch = preview; `--safe-preview` / `--scoped-start` / `--scope-*` |
| `src/gui/app.py` | disabled Start with a clear label when previewing or unscoped |
| `src/launcher/single_instance.py` | optional mutex name + preview mutex |
| `scripts/windows_release_entry.py` | `--preview-self-check` (two real GUI rounds) |
| `scripts/verify_release_candidate.ps1` (new) | recompute every manifest hash |
| `scripts/backup_running_release.ps1` (new) | program+config snapshot, junction-aware, DB recorded not copied |
| `scripts/install_release_candidate.ps1` (new) | guarded switch, never starts anything |
| `tests/launcher/test_rfq021_run_scope.py` (new) | 20 negatives |
| `tests/research/test_rfq021_write_intents.py` (new) | 9 negatives |
| `tests/gui/test_rfq021_safe_preview.py` (new) | 6 launch/button negatives |
| `tests/gui/test_startup.py` | existing start contract updated to require a scope |

## 4. Test evidence

- New negative suites: 35 tests, all pass. They cover: scope validation refusals; policy denial before any intent; scope refusal happening before a journal row; INSO scope narrowing; a crashed write blocking the next process; an unconfirmed hold not being settled by lease release; an unreadable ledger failing closed; preview launch never starting process services; `--start-inquiry` without a scope refused; button state.
- Existing `test_startup.py` was updated (not skipped): an explicit Start now needs `--scoped-start` + a scope. Its original intent is preserved.
- **Affected modules together** (`tests/launcher research sheets inso gui`): **2886 passed, 0 failed, 161.60 s**.

**Full suite, final run** (`pytest tests -q --tb=no`, JUnit in `docs/evidence/rfq021/pytest-report.xml`):

| Metric | Value |
|---|---|
| Collected | 4,223 |
| Passed | 4,220 |
| Failed | **2** |
| Skipped | 1 |
| Duration | 382.18 s |

Both failures are the same test:
`tests/launcher/test_release_infrastructure.py::test_backend_closes_only_owned_browser_after_runtime_thread_exits[False]` and `[True]` — the worker ends in `MODULE_PAUSED` instead of `STOPPED` after `request_stop_after_cycle()`.

**Control run on the unmodified parent commit** (`e59ce62f`, extracted with `git archive`, same interpreter, same command): **2 failed / 4 errors / 4,181 passed / 1 skipped in 388.23 s** — and the two failures are *exactly the same two nodeids*. The 4 extra errors (`tests/workflow/test_follow_up_rollback.py`) appear only in the extracted tree (it has no git or local runtime context) and are not present in the worktree run.

So the failure set **did not change** relative to the baseline; this is the known load-sensitive pair, not a regression from RFQ-021. The same two tests pass individually (repeated 6×) and pass as part of the 2,886-test module run.

Two transparency notes:

- An earlier full run under the sandbox produced 4 failures, all with `sqlite3.OperationalError: attempt to write a readonly database`; those tests pass when the run is allowed to write its temp directory, and the baseline shows the same class of instability. No test was deleted, skipped or deselected to improve the number.
- One intermediate full run was stopped by the operator after 16 minutes at ~20 % (it hung while showing clustered failures); it is not used as evidence.


## 5. Candidate build

- Environment: reused `.venv-release` (Python 3.12.10 / Tk 8.6.15 / PyInstaller 6.16.0); lock file unchanged (`3dc5d7a5…`).
- Command: `scripts/build_windows_release.ps1 -BuildOnly -Version 1.6`, exit 0, script-internal `--self-check` and `RELEASE_SCAN_OK` both passed.
- Output: `build/windows-release-stage-1.6/dist/INSO_V1.6/` — staging only; `dist/INSO_V1.6` untouched.

| Item | Value |
|---|---|
| Source commit | `8cded532221571e99697af7668634afab3ea07af` |
| EXE | 8,455,788 B, SHA256 `63bcd6cea66003f84ce016cfa8742dc479a9d67ce3f579a92b5b7c398bf4465b` |
| Files | 2,872 (EXE + 2,871 under `_internal`) |
| `runtime/` in artifact | absent |
| Manifest | `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256`, 2,872 lines, digest `d5cc3d4cc41fff16bf0316e0799305b31269201a5728bb7a207b8220d6a2aa7a` |

Build input hashes: build script `ab35565a…`, lock `3dc5d7a5…`, spec `d7574c20…`, icon `8f0e07dc…`, scanner `f2517340…`, entry `ae4eafa5…`.

**RFQ-020's `b358f687…` is not used as evidence for this source.** It was produced from `25894efa` and has been replaced in staging by this build.

## 6. Self-checks on the candidate

| Check | Result |
|---|---|
| `--self-check` | exit 0 |
| `--idle-self-check` | exit 0, state 已停止, no business/order thread |
| `--preview-self-check` (new) | exit 0, 3 s, **2 rounds**, both `blockers=["PREVIEW_ONLY"]`, Start disabled, `business_thread_started=false`, `mail_service_started=false`, `process_services_consumed=false` |
| `scan_release_artifact.py` | `RELEASE_SCAN_OK` (script-internal and standalone) |
| `verify_release_candidate.ps1` | 2,872/2,872 matched, `missing=0`, `hash_mismatch=0`, `unexpected=0`, `VERIFY_RESULT=PASS` |

Reports: `docs/evidence/rfq021/v16-preview-self-check.json`, `docs/evidence/rfq021/v13-idle-self-check.json`.

The self-check byproducts (`runtime/logs/*.json`) were removed from the staging artifact after their content was copied into evidence, so the manifest describes the build output exactly (2,872 files).

## 7. Production invariance

| Item | Before | After |
|---|---|---|
| Production EXE | `E9E3DA33…` | `E9E3DA33…` |
| Processes | PID 38948 + 34304 | same PIDs, never stopped |
| Production SQLite | 1,196,032 B, actively written by the running program | **not opened, not copied, not modified by this RFQ** |
| Chrome 9222 | reachable, 15 pages | never attached; page count changed by the running program itself |

The database size and mtime move on their own while the old program runs; this RFQ only ever read file metadata there.

## 8. Switch materials (prepared, not executed)

`control-room/RFQ-021/INSTALL_AND_ROLLBACK.md` covers: offline verification, program+config snapshot, bounded stop with abort conditions, post-stop consistent DB backup, guarded install, first launch as safe preview, business enablement conditions, rollback that never overwrites newer business data, and the failure states (`WRITE_INTENT_PENDING`, `WRITE_LEDGER_UNAVAILABLE`, `EXTERNAL_WRITE_NOT_IN_SCOPE`).

## 9. NOT_VERIFIED

1. Nothing was installed, stopped, or started against the production directory in this RFQ.
2. The candidate was never launched as the real product beyond the three self-check modes.
3. `sqlite3.exe` availability and `.backup` duration on this host are unverified (documented as a manual step).
4. Old-program Stop timing, GUI refresh stall and residual Chrome pages remain unmeasured.
5. PyInstaller output is not bit-reproducible: `63bcd6ce…` identifies this build only.
6. The running `E9E3DA33…` EXE still has no proven source lineage.
7. Business UNKNOWN state (221 / SHAHAB-115 / 3 V13 holds) untouched and unresolved.
8. A real scoped business run (even read-only) was not executed; scope behaviour is verified by unit/negative tests, not by a live run.
