# RFQ-019 — execution log (read-only release preparation)

- **Status:** `REVIEW_REQUIRED / READ_ONLY_RELEASE_PREP / NOT_DEPLOYED / NOT_MERGED`
- **Window:** 2026-11-14 21:28– Shanghai
- **Worktree:** `D:\Program_Leo\INSO_Leo\.worktrees\v16-rfq016-stabilization` (reused)
- **Fixed source:** `25894eface6ea622153d1573c19d0ca6b9ad72aa`
- **Document HEAD:** `45621923` (CEO RFQ-018 final Review; docs-only)

## 1. Takeover audit (read-only)

- Read `origin/develop` `AI_START_HERE.md`, `AGENTS.md`, `control-room/CEO_HANDOVER.md`, `control-room/COORDINATION.md`, `control-room/RFQ-018/REVIEW.md`, `RFQ-018/RELEASE_READINESS.md`, `RFQ-018/EXECUTION_LOG.md`, `FINAL_REPORT.md`, `docs/WINDOWS_RELEASE.md`, `docs/CDP_SESSION_POLICY.md`, `docs/BRANCH_POLICY.md`, `docs/SAFETY.md`, `docs/REPORTING.md`.
- Fetched origin; local branch was one docs-only CEO-review commit behind. Fast-forwarded to `45621923`; no source/test changes in that commit.
- `git diff --name-only 25894efa..HEAD -- src tests` is **empty**: the fixed RFQ-018 source is exactly the code at the reviewed SHA.
- `git status --short` clean before edits; no stash; no second worktree; root `main` untouched.
- No test suite was rerun for this RFQ. RFQ-018 CEO-accepted evidence is reused: **4188 collected / 4187 passed / 1 skipped / 0 failed / 341.54s**, 26 original nodeids retained, 28 new regressions. This RFQ did not modify source or tests.

## 2. Current live scene (read-only, not CEO-verified)

| Item | Observed at 2026-11-14 21:28–21:35 |
|---|---|
| Old EXE | `dist/INSO_V1.6/INSO_V1.6.exe`, 8,422,619 bytes, SHA256 `E9E3DA33417414ABAC53F8A88A67D9F053BCDAEAB9730EAE9AD8BD7870DFFAD0` |
| App process | PID 38948, `--start-inquiry`, started 13:47:50 |
| Watcher | PID 34304, `--watch-runtime 716 86030824867e430d81c366c4e6a9f60a …` |
| Runtime state | `runtime-86030824867e430d81c366c4e6a9f60a.state.json`: `phase=gui`, `gui_ready`, `completed=false` |
| Activity | `runtime/logs/INSO_V1.3.log` shows scheduled quotation/tp/inquiry modules completing near 21:34; old program is **actively running business**, not just an idle GUI |
| Chrome/CDP | `127.0.0.1:9222`, owner PID 24164; untouched |
| SQLite | `dist/INSO_V1.2/runtime/production/workflow.sqlite3`, 1,191,936 bytes; `PRAGMA quick_check` = `ok`; 0 active V12 alerts; 3 active V13 holds; purchase states: 26 SAVED / 7 VALIDATION_FAILED / 3 AI_RECOGNIZED / 1 MANUAL_REVIEW |
| Active V13 holds | `inq_71f4a2f5…` `UPDATE_RESULT_UNCONFIRMED`; `inq_d65be9df…` `QUOTE_INPUT_WRITE_FAILED`; `unresolved:0ca37229…` `SOURCE_IDENTITY_UNRESOLVED` |
| Row 221 | `inq_e15970df…`, `PURCHASE_RECORDED`, purchase `SAVED`, receipt `rec_440fafd372440ecf9dacabf660dd155d`; not replayed |
| SHAHAB/115 | `inq_99275e8e…`, `HUMAN_COMPLETED`, purchase `MANUAL_REVIEW / RECONCILIATION_UNREADABLE`, no saved receipt; native INSO `NOT_VERIFIED` |
| Runtime junction | `dist/INSO_V1.6/runtime` → `D:\Program_Leo\INSO_Leo\dist\INSO_V1.4\runtime` |
| Production config | `dist/INSO_V1.4/runtime/production.json`, `google_api.enabled=true`, `v13_enabled=true`, `tp_enabled=true`, `v16_enabled=true` |

No stop, deploy, Chrome attach, SQL/DB write or external business action was performed.

## 3. Build / rollback readiness checks

- Canonical build script `scripts/build_windows_release.ps1` requires `.venv-release/Scripts/python.exe` and a Tcl/Tk-capable PyInstaller environment. **`.venv-release` does not exist** in the worktree or candidate root; global Python has **no PyInstaller**. The canonical candidate build cannot run as-is.
- `requirements-windows-release.lock` exists and pins `pyinstaller==6.16.0`, Playwright, Google API, customtkinter etc.
- Existing candidate staging at `D:\Program_Leo\INSO_candidate_V16_RFQ016` has an EXE 8,414,556 bytes from 10:14, but **not** built from fixed `25894efa`; its source hash is not proven.
- Latest full backup `dist/release-backups/INSO_V1.6-header-block-20261114T021508Z` contains `_internal` + EXE (older, 10:15). Latest `INSO_V1.6-customer-20261114T113817Z` contains **only** the EXE (8,414,556). Neither is a verified full snapshot of the currently running `E9E3DA33…` program + config + DB.
- Current `dist/INSO_V1.6` has 17 `_internal.prev-*` directories; they are program remnants, not a complete, hashed rollback set.
- `release/previous` = `d244241e…` (unverified rollback source); `main` = `be9d0a51…` (historical V1.1); `develop` = `a18abe7f…` (docs only). No branch movement.
- `V16_RELEASE_REPORT.md` reports formal EXE `b357889d…` from source `24b73be7`, while current running EXE is `E9E3DA33…`. Current EXE↔source provenance is **NOT_VERIFIED**.
- **Normal GUI launch is not side-effect-free:** `src/gui/main.py` calls `backend.start_process_services()` before any Start. That path runs DB migration/recovery and starts IMAP receive + SMTP outbox (`src/launcher/backend.py:733-758`, `mail_research_composition.py`, `mail_research.py:467-495`). There is no “GUI only, no mail/no DB change” switch. `--self-check`/`--idle-self-check` are the existing safe alternatives; `--mock` is not the real backend. This is B7 in the risk register.

## 4. Risk analysis and conclusion

- Three release risks evaluated: restart UNKNOWN isolation, old/new EXE switch/rollback, GUI/exit/browser residual risks.
- Full risk classification and evidence: [RISK_REGISTER.md](RISK_REGISTER.md).
- Release plan: [RELEASE_PREP_REPORT.md](RELEASE_PREP_REPORT.md).
- Final verdict: [RELEASE_READINESS.md](RELEASE_READINESS.md).

**Verdict summary:** `BLOCKED` for **normal GUI and business trial**. Only candidate build, `--self-check`/`--idle-self-check`, and a full rollback snapshot may continue as preparation. Normal GUI is not a safe “no-effect launch” because it starts process services (DB migration/recovery + IMAP + SMTP outbox, B7); business Start also lacks a scoped single-order mode (B5) and cannot inherit cross-service document holds after restart (B6). This is not a downgrade: no normal GUI/Start is approved.

## 5. Preserved / no external action

- No deployment, EXE replacement, process stop/restart, Chrome/CDP attach, Google/INSO/SMTP write, SQLite/WAL/SHM write, or branch merge.
- 221 SAVED receipt, SHAHAB/115 UNKNOWN, 3 V13 holds and 0 active V12 alerts unchanged.
- No source/test/config change; only RFQ-019 docs/evidence (to be committed).

## 6. Next single action

CEO final review of RFQ-019. If approved, the **first** authorized action is the Phase 0 build/rollback preparation only; stopping the old EXE and installing the candidate requires a separate, explicitly bounded Owner authorization and a clean-stop window. No business Start.
