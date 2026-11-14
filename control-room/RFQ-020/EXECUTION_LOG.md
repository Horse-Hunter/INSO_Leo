# RFQ-020 — execution log (isolated candidate build and self-check)

- **Status:** `PASS_BUILD_AND_SELF_CHECK / INSTALL_NOT_AUTHORIZED / NOT_DEPLOYED / NOT_MERGED`
- **Window:** 2026-11-14 22:34–23:00 Shanghai
- **Worktree:** `D:\Program_Leo\INSO_Leo\.worktrees\v16-rfq016-stabilization` (reused; no second worktree)
- **Branch:** `workbuddy/v16-rfq016-stabilization`
- **Fixed source:** `25894eface6ea622153d1573c19d0ca6b9ad72aa`
- **Worktree HEAD:** `505d9590a2726c0ec27f2c090d28616e528a6470`

## 1. Takeover audit (read-only)

- Read `AI_START_HERE.md`, `AGENTS.md`, `control-room/CEO_HANDOVER.md`, `control-room/COORDINATION.md`, `RFQ-019/{TASK_SPEC,EXECUTION_LOG,RELEASE_PREP_REPORT,RELEASE_READINESS,RISK_REGISTER}.md`, `RFQ-018/{REVIEW,RELEASE_READINESS}.md`, `docs/REPORTING.md`, `docs/WINDOWS_RELEASE.md`.
- **Discrepancy recorded:** requested `docs/BRANCH_POLICY.md` does not exist on this branch (only `docs/CDP_SESSION_POLICY.md`, `docs/SAFETY.md`, …); requested `control-room/RFQ-019/REVIEW.md` does not exist (RFQ-019 has `TASK_SPEC`/`EXECUTION_LOG`/`FINAL_REPORT`/`RELEASE_READINESS`/`RELEASE_PREP_REPORT`/`RISK_REGISTER`). No file was invented to fill either gap.
- `git status --porcelain` clean before work; no stash; only the pre-existing `main` and old worktrees besides this one (`git worktree list --porcelain`).
- `25894efa` is an **ancestor** of HEAD. `git diff --name-status 25894efa..HEAD` = 11 files, all `control-room/*` docs and `docs/evidence/rfq019/*.json`; `git diff --name-only 25894efa..HEAD -- src tests scripts packaging requirements-windows-release.lock requirements-windows-release.txt` is **empty**. The reviewed source is therefore exactly the code in this build.
- No test suite was rerun (RFQ-018 evidence reused: 4188 collected / 4187 passed / 1 skipped / 0 failed). No source, test, or config file was modified in this RFQ.

## 2. Pre-build live scene (read-only, not CEO-verified)

| Item | Observed 2026-11-14 22:34–22:37 |
|---|---|
| Production EXE | `dist/INSO_V1.6/INSO_V1.6.exe`, 8,422,619 bytes, SHA256 `E9E3DA33417414ABAC53F8A88A67D9F053BCDAEAB9730EAE9AD8BD7870DFFAD0` |
| Processes | `INSO_V1.6.exe` PID 38948 (app) + PID 34304 (watcher), started 13:47:50–51 |
| Production SQLite | `dist/INSO_V1.2/runtime/production/workflow.sqlite3`, 1,191,936 bytes, mtime epoch **1794667137**; **no `-wal` / `-shm` present** |
| Chrome/CDP | `127.0.0.1:9222` reachable (Chrome/156.0.8078.81), owning PID 24164, **15** pages |
| `runtime` junction | `dist/INSO_V1.6/runtime` → `D:\Program_Leo\INSO_Leo\dist\INSO_V1.4\runtime` |
| Release staging | `build/windows-release-stage-1.6` **absent** before build (only `build/rfq016-cache`, `build/rfq016-candidate` existed) → no unknown staging content, nothing force-cleaned |

No stop, install, Chrome attach, SQL/DB write or external business action was performed at any point.

## 3. Build environment (isolated; lock file untouched)

- Base interpreter `C:\Users\Leo\AppData\Local\Programs\Python\Python312\python.exe` = **3.12.10**, Tcl/Tk **8.6.15**.
- Created `D:\Program_Leo\INSO_Leo\.worktrees\v16-rfq016-stabilization\.venv-release` (gitignored, inside the worktree, not the production tree).
- `pip install -r requirements-windows-release.lock` → 42 packages installed, `pip check` = **No broken requirements found.**
- Verified: `PyInstaller 6.16.0`, `tkinter.Tcl()` → 8.6.15, plus `customtkinter`, `googleapiclient`, `playwright 1.63.0`, `pypdf`, `tzdata`, `openpyxl` import clean.
- **Lock file not modified** (SHA256 `3dc5d7a5dae4387f156b4589259e899e887c607349b111a599911735dc2494ec`); production Python untouched.

## 4. Build inputs (recorded for traceability)

| Input | SHA256 |
|---|---|
| `scripts/build_windows_release.ps1` | `ab35565ab9d42fd831eb6c59461f745400d14872145a3e60cec7d0d7b24cbdf1` |
| `requirements-windows-release.lock` | `3dc5d7a5dae4387f156b4589259e899e887c607349b111a599911735dc2494ec` |
| `packaging/INSO_V1.1.spec` | `d7574c2011917ff2c81007dc2271fd6d62d769d783d21d3098355a2d56d6e80c` |
| `packaging/assets/inso-v1.1.ico` | `8f0e07dc4a78f982c58015430029a8c901b2705a4869ebbcc6d8a0f24e4e2028` |
| `scripts/scan_release_artifact.py` | `f251734088b2506aaec21088a8c31d6c62f201fb277b232ed6e06e60fb883e29` |
| `scripts/windows_release_entry.py` | `abd9f0186fd554fbb65a66df8a16caf044ac5f2e4d85abd958f3e1f4368abb5f` |

## 5. Candidate build (`-BuildOnly`, staging only)

Command (canonical script, explicit isolated interpreter):

```
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows_release.ps1 `
  -BuildOnly -Version 1.6 -PythonExecutable .venv-release\Scripts\python.exe
```

- Result: exit 0 in **1 min 33 s**; PyInstaller 6.16.0 / Python 3.12.10 / Windows-10-10.0.19045; script printed `RELEASE_SCAN_OK` and `Built staging artifact …` — the script's own built-in `--self-check` gate passed.
- Output: `build/windows-release-stage-1.6/dist/INSO_V1.6/` (PyInstaller work tree auto-removed by the script).
- **`dist/INSO_V1.6` was not touched** (script refuses non-`BuildOnly` replacement; staging marker `.inso-release-stage` present).

| Artifact | Value |
|---|---|
| Candidate EXE | `build/windows-release-stage-1.6/dist/INSO_V1.6/INSO_V1.6.exe` |
| Size | **8,436,056** bytes (prod 8,422,619; formal `b357889d…` 8,414,556) |
| SHA256 | **`b358f68715f9e1dadeae19d5ad5b0f517664756105ebf1fcea1b843dc482d29c`** |
| File count | **2,872** (EXE + 2,871 under `_internal`) |
| Tree size | 261 MB |
| `runtime/` in artifact | **absent** (generic build, no local config/DB) |
| Manifest | `docs/evidence/rfq020/INSO_V1.6-artifact-manifest.sha256`, 2,872 lines, SHA256 of the manifest file `c8806aea1b4d9f3df1d39261bc4aa81a213ab3ea9c335b4a40970f12c57d5b65` |

Artifact-set comparison with the running program: `prod-only = 0` files; `candidate-only = 1` file (`_internal/tzdata-2026.4.dist-info/REQUESTED`, a packaging marker emitted by this dependency set). No file is missing from the candidate relative to the running `_internal`.

**Manifest byte stability:** the repo has `core.autocrlf=true`, which would rewrite the manifest with CRLF on checkout and change its own digest. Added a scoped `.gitattributes` rule (`docs/evidence/**/*.sha256 -text`); the staged blob hash equals the recorded manifest hash `c8806aea…`, so the manifest can be re-verified byte-for-byte after clone.

## 6. Self-check evidence

Safety basis (code read, not assumed):

- `scripts/windows_release_entry.py::_self_check` = imports + `tkinter.Tcl()` + `customtkinter` + `src.gui.main` import + `ZoneInfo("Asia/Shanghai")` + in-memory pypdf write/read. **No file writes, no network, no config read.**
- `_idle_self_check` constructs `ProductionBackend()` with default `root = app_root()`, which for a frozen EXE is **the executable's own directory** → staging. It does **not** call `start_process_services()`, does **not** acquire CDP, does **not** read production `production.json`/`research.json`, and writes only `<staging>/runtime/logs/v13-idle-self-check.json`.

| Check | Result |
|---|---|
| `INSO_V1.6.exe --self-check` | **exit 0** |
| `INSO_V1.6.exe --idle-self-check` | **exit 0**, **3 s**, within the 120 s bound; no app/watcher left behind |
| Idle report | `{"title": "INSO LEO V1.6 — Procurement Automation Control Center", "state": "已停止", "business_thread_started": false, "order_thread_started": false, "order_action": "自动订单录单", "gui_rendered": true, "start_action": "开始运行"}` |
| `scan_release_artifact.py` (re-run independently) | `RELEASE_SCAN_OK`, exit 0 |

The idle check created `<staging>/runtime/logs/v13-idle-self-check.json`. Its content is quoted above; the file and the empty `runtime/` directory were then removed **only inside staging** so the recorded artifact equals the build output (2,872 files). This is our own byproduct, not unknown third-party content.

**`--api-self-check` was NOT run** — outside the authorized minimum and unnecessary for artifact identity. `--cdp-self-check` was NOT run (would attach to protected 9222).

**Production invariance proved for the whole window:**

| Item | Before | After |
|---|---|---|
| Production EXE SHA256 | `E9E3DA33…` | `E9E3DA33…` (identical) |
| Production processes | PID 38948 + 34304 | PID 38948 + 34304 (same PIDs, never stopped) |
| Production SQLite | mtime epoch `1794667137`, 1,191,936 B | **same epoch, same size** |
| WAL/SHM | none | none |
| Chrome 9222 pages | 15 | 15 |

## 7. Read-only rollback asset inventory (no backup taken, no DB touched)

| Asset | Read-only observation |
|---|---|
| Running program | `dist/INSO_V1.6/INSO_V1.6.exe` `E9E3DA33…` + `_internal` **2,870 files / 253 MB** |
| Config | `dist/INSO_V1.4/runtime/production.json` `65658fba…`; `.bak-20261114T1030` `e6fd95e8…`; `research.json` `bdd15f42…` |
| Database | `dist/INSO_V1.2/runtime/production/workflow.sqlite3` 1,191,936 B, SHA256 `ab7574f646988d44203fb152eb03c26cfc02ab8fc7a372d85a82ef7c002d59ce` (file hash of a **live** DB — identity only, not a consistent backup) |
| `runtime` junction | `dist/INSO_V1.6/runtime` → `dist/INSO_V1.4/runtime` (must be preserved, never replaced) |
| `_internal.prev-*` | **16** directories (RFQ-019 reported 17 — pre-existing difference, not modified by this RFQ; they are program remnants, **not** a complete rollback set) |
| Backup `INSO_V1.6-header-block-20261114T021508Z` | 2,875 files / 262 MB, EXE `00ac7d68d88e1a27eb52e3b7457b4192b699211df1b1f5e3efe0be406eef30bd` — older program, not the running version |
| Backup `INSO_V1.6-customer-20261114T113817Z` | **EXE only** (1 file), `b357889d48e5abe6ec6504eddd610442c877e438018f156c4c932477070814f6` |
| Backup `INSO_V1.6-before-diagnostics-20261112T212500` | 5,759 files / 524 MB (program + data + manifests) |
| Backup `INSO_V1.6-shahab-liveness-20261109T061911Z` | 2,993 files / 269 MB (program + data + install receipt) |

**Conclusion unchanged from RFQ-019/B3:** there is still **no complete, hashed rollback snapshot of the currently running `E9E3DA33…` program + config + consistent DB**. Taking it requires a clean stop (B4) and Owner authorization; this RFQ did not do it.

## 8. Preserved / not done

- No install, no stop/restart, no EXE replacement, no normal GUI launch, no business Start.
- No Chrome/CDP operation, no Google/INSO/SMTP effect, no production SQLite/WAL/SHM write.
- 221 SAVED receipt, SHAHAB/115 `MANUAL_REVIEW`, 3 V13 holds, 0 active V12 alerts — untouched (not re-read this round either).
- No source/test/config change; no branch merge/promotion. Only RFQ-020 docs + evidence added.

## 9. NOT_VERIFIED / limits

1. Candidate was **never installed or launched as the production program**; only `--self-check` and `--idle-self-check` ran.
2. Normal GUI startup side effects (B7: DB migration + IMAP receive + SMTP outbox) remain unverified and unauthorized.
3. `Stop`/`Exit` timing, GUI refresh stall, residual Chrome pages (N1–N3) remain unmeasured for the candidate.
4. Build reproducibility: PyInstaller output is not bit-reproducible; `b358f687…` identifies **this** build, not any rebuild of the same source.
5. Running EXE `E9E3DA33…` still has **no proven source lineage** (it matches neither `b357889d…`/`24b73be7` from `V16_RELEASE_REPORT` nor this candidate).
6. Business UNKNOWN state (221 / SHAHAB-115 / 3 V13 holds) untouched and still open; B5/B6/B7 still block business trial.
