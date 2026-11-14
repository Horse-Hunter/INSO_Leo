# RFQ-017 — execution log (read-only test audit)

- **Status:** `REVIEW_REQUIRED / READ_ONLY_AUDIT / NO_SOURCE_OR_TEST_CHANGE / NOT_DEPLOYED / NOT_MERGED`
- **Window:** 2026-11-14 17:01–17:30 Shanghai
- **Worktree:** `D:\Program_Leo\INSO_Leo\.worktrees\v16-rfq016-stabilization` (reused)
- **Branch / HEAD:** `workbuddy/v16-rfq016-stabilization` / `95e9b186`
- **Audited code:** `b45e870e` (RFQ-016 final P1-E)
- **TASK_SPEC:** [TASK_SPEC.md](TASK_SPEC.md) · **Report:** [AUDIT_REPORT.md](AUDIT_REPORT.md)

## 1. Takeover audit (read-only)

- Read `docs/AI_START_HERE.md`, `AGENTS.md`, `control-room/CEO_HANDOVER.md`, `control-room/COORDINATION.md`, `RFQ-016/REVIEW.md`, `RFQ-016/RELEASE_READINESS.md`, `RFQ-016/TASK_SPEC.md`, `RFQ-016/TEST_REPORT.json`, `docs/BRANCH_POLICY.md`, `docs/SAFETY.md`, `docs/REPORTING.md` from the current worktree/`origin/develop` as appropriate.
- `git fetch origin develop` was run only to read the current develop docs; no merge, rebase, checkout or branch movement.
- `git status --short` empty before edits; no stash; no second worktree created; root `main` worktree untouched; running EXE untouched.
- Running production scene: `dist/INSO_V1.6/INSO_V1.6.exe` SHA256 `E9E3DA33…`, app PID 38948 (`--start-inquiry`), watcher PID 34304; Chrome `127.0.0.1:9222` owner PID 24164.
- SQLite read-only: 60 orders = 35 `HUMAN_COMPLETED` + 24 `PURCHASE_RECORDED` + 1 `INVALID_INPUT_SKIPPED`; 0 active V12 alerts; 3 active V13 holds.
- Row 221: `inq_e15970df104e170d93b4169b`, `PURCHASE_RECORDED`, `SAVED`, receipt `rec_440fafd372440ecf9dacabf660dd155d`; not re-ordered.
- SHAHAB/115: `inq_99275e8e72b43fd6616fd686`, `HUMAN_COMPLETED`, `MANUAL_REVIEW / RECONCILIATION_UNREADABLE`, no saved receipt; left isolated.
- No Sheets/INSO/SMTP/Google/CDP write, no deployment, no restart, no hold clear, no DB write. Only read-only PowerShell/Python and local pytest fakes were used.

## 2. Reproduction of the 26 failures

- Input: exact 26 nodeids from `docs/evidence/v16/rfq016-ceo-third-review-2026-11-14.json` (`final.failed_nodeids`). The audit JSON stores that dotted form verbatim plus `file_nodeid` for readability; pytest was invoked with the equivalent file form (`tests/launcher/*.py::...`), which pytest resolves to the same tests.
- Command: `python -m pytest <26 nodeids> -q --tb=short -p no:cacheprovider`
- Result: **26 failed in 4.76 s** (26 collected, 0 passed, 0 skipped).
- Failure classes: 7 `ImportError`, 1 `ModuleNotFoundError`, 3 `AttributeError`, 15 behavioral assertion failures.
- Determinism: repeated runs produced the same nodeids and same failure classes; no flaky/port/network/timing behavior.
- External I/O: none. Tests use local fakes (`SimpleNamespace`, synthetic `Page`, local sqlite tmp); no real Chrome, Google, INSO, SMTP or production DB.

## 3. Full-suite control run

- Command: `python -m pytest tests -q --tb=short -p no:cacheprovider --deselect <26 nodeids> --basetemp .tmp/rfq017_basetemp`
- Result: **4133 passed, 1 skipped, 26 deselected in 332.76 s** (exit 0).
- Collected total: 4160. The 1 skip is the pre-existing Windows symlink-permission skip, unrelated.
- This is the key control: outside the frozen 26, the current source tree has **no other failures**.
- RFQ-016's earlier 3408 count is a five-directory subset; this run additionally covers `tests/core`, `tests/research`, `tests/order_mail`, etc. (752 more passing tests).

## 4. Git archaeology / common root cause

- `git blame` on every one of the 26 test definition lines: **all 26 introduced by `d244241e` (2026-11-12)**, one distinct commit.
- `d244241e` subject: `fix(rfq016): capture installed V1.6 candidate source and handover records`.
- Its own message: “Tests are not part of the build copy, so test-tree correspondence to the built binary is not proven.”
- `git log --all -S "def google_resource_barrier" -- src` → empty; same for `def _document_barrier`, `class _GoogleDocumentBarrier`; `git log --all -- src/workflow/google_resource_holds.py` → empty.
- `Select-String` over `src/**/*.py` for `google_resource_barrier|_document_barrier|_GoogleDocumentBarrier|google_resource_holds` → no matches; only tests reference them.
- `ProductionBackend._prepare_google_resource_store` also does not exist.
- Therefore the 26 tests were never satisfiable against any committed source; they are not a regression from RFQ-016 fixes, and their identical nodeids across rounds are explained by the missing subsystem, not by “known flaky”.

## 5. Per-test classification

Full table in [AUDIT_REPORT.md §5](AUDIT_REPORT.md#5-逐项判定). Summary:

| Class | Count | Risk | Release meaning |
|---|---:|---|---|
| 旧测试不适用 — 引用从未提交的 API/模块 | 11 | none | 不阻断；测试导入即失败，生产源码无引用 |
| 旧测试不适用 — 测试已废弃的 document barrier 设计 | 10 | low | 不阻断；当前有页面身份/持久 hold/API 路径等替代 |
| 真实代码缺口 — 防御纵深未实现 | 5 | medium | 不阻断受控试运行；阻断“全量绿/无条件发布” |
| 环境问题 | 0 | — | 无 |

Five real gaps: cross-service document barrier after unconfirmed quote write (2 parametrized cases), cross-sheet write during busy close (1), order-mail missing `page_admission` propagation (1), sales preflight missing admission gate (1). No duplicate purchase/quote/mail or data-corruption path was reproduced.

## 6. Release risk conclusion

- **No functional regression proven** from RFQ-016 fixes.
- **Overall risk: MEDIUM** — 21 test-baseline items plus 5 defense-in-depth gaps.
- **Does not block a controlled trial** of the RFQ-016 source on the basis of these 26 alone, provided the known-red list is frozen, tests are not deleted/skipped, no “full green” claim is made, and existing holds/UNKNOWN are preserved.
- **Does block** “full regression PASS”, unconditional production release, or `main` promotion while 26 tests remain red and unaccepted.
- If CEO/Owner require zero failures before deployment, this is a hard blocker.

## 7. Preserved effects / no external action

- No source/test file modified; no test deleted, skipped or weakened; no requirement relaxed.
- No deployment, EXE overwrite, process stop/restart, Chrome/profile action, branch merge or `main`/`release/previous` change.
- No real purchase, Google write/Editor, quote click, SMTP or mail.
- Row 221 purchase receipt preserved; 3 V13 holds preserved; SHAHAB/115 UNKNOWN/isolated; 0 active V12 alerts unchanged.
- Only new repo content is this RFQ's docs and the machine-readable audit JSON.

## 8. Resume / next single action

- This log and `AUDIT_REPORT.md` are the durable checkpoint; a replacement window can resume from them plus the Git/test evidence.
- **Next single action:** CEO independent review of RFQ-017. No test repair/quarantine, deployment, merge or real effect is authorized by this task.
- If CEO requests changes, the next Executor should first re-run the exact 26 nodeids and confirm they are still the same set before editing anything.
