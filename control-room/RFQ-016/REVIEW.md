# RFQ-016 — CEO Independent Review (2026-11-12)

## Review 结论

**CHANGES_REQUESTED / HEALTH_HOLD** for RFQ-016 overall business acceptance. The **GitHub handover-only subtask is ACCEPTED** as completed; this does not approve the underlying V1.6 production behavior, a new deployment, repeat business writes, or branch deletion.

### Exact reviewed Git state and evidence scope

- Repository: `Horse-Hunter/INSO_Leo`; branch `codex/v1-6-independent-scheduling`.
- Reviewed immutable commit `9eb342923f7f5ed67474346d3dc92fc005c26c9b`; application delivery parent `d244241eafe564c79812f860b2491c903a4cee1e`; prior remote `635ddfef21302398fcae312936caa3e571331336`. Git compare: 2 commits ahead, 0 behind. The last commit changed only records/evidence.
- Reviewed `src/` tree `c2eda9f71069014c9c8b50c012078b27d7295f04`; `tests/` tree `779514ffd498394194bf7e5c178a221f797acda1`.
- Examined `control-room/RFQ-016/{TASK_SPEC.md,EXECUTION_LOG.md,FINAL_REPORT.md,TEST_REPORT.json}`, `control-room/COORDINATION.md`, `V16_RELEASE_REPORT.md`, `docs/evidence/v16/handover-2026-11-12-{recovered-failures,rerun}.json`, selected current Google read/write, quotation and production composition source, and the failing test assertions.
- **Independent GitHub source/records inspection only.** CEO did **not** access the Windows host, re-run pytest, inspect the local JUnit XML or full log, open a production browser, validate current runtime hashes, modify business data or send external mail. The 2875-file EXE SHA256 comparison, 130-source-file equality, post-install self-check and six per-module cycles are **Executor-reported local evidence**, not independently live-attested.
- Reported installed EXE SHA256: `00ac7d68d88e1a27eb52e3b7457b4192b699211df1b1f5e3efe0be406eef30bd`. The build copy contains no test tree: binary-to-test-tree identity remains `NOT_VERIFIED`.

### Accepted: Git handover deliverable

The remote branch advanced by a non-force fast-forward containing previously uncommitted production-candidate source, tests, RFQ records and the dated test-evidence manifests. Historical failure-list recovery clearly distinguishes unavailable original tracebacks from the **new** rerun. This resolves the Git synchronization blocker and permits a new Executor to work from an immutable review baseline. It does not establish correctness of the installed executable.

### B1 — P0 release blocker: Google unknown-write / cross-operation safety semantics are unproven

The historical **26 failed / 3920 passed / 11 skipped** test IDs are recovered. All 26 reappear in the newly reported **30 failed / 3932 passed / 1 skipped** full rerun. Most failed IDs cover Google read quarantine, unresolved writes, document-level cross-client admission, recovery and linked sales/module resources. Examples: `test_unconfirmed_write_keeps_cross_service_barrier_after_close`, `test_quarantined_read_blocks_write_from_another_service`, `test_closed_read_target_never_clears_separate_unknown_write`, `test_nested_clients_share_document_barrier`.

Independently inspected tests explicitly import `_GoogleDocumentBarrier`, `_document_barrier` or `google_resource_barrier`, which are absent from the current `google_quote_update.py`. Current code instead uses `_GOOGLE_GRID_LOCK`, retained page states, active quote markers and `PageResourceAdmission`, whose shown public behavior is fault admission, not the old document ledger. Thus a real **test/implementation contract mismatch is confirmed**. It does **not** prove the existing system has caused duplicate external writes, and does **not** justify recreating a parallel legacy mechanism simply to make tests pass.

**Required evidence/remedy:** classify all 26 test IDs against the latest Owner-approved business contract and actual production entry paths. For every uncertain write, reconnection, thread/client crossover, read-only quarantine and human-owned page transition, demonstrate fail-closed behavior and original durable SENT/UNKNOWN safety with deterministic fake-Google/fake-INSO/fake-SMTP tests. Show current production wiring, not just isolated helpers. Where current code violates the contract, make the smallest reusable correction to the canonical owner; where a test asserts superseded internals, replace it with a stronger public-behavior regression, preserving its intended safety invariant and recording explicit rationale. Never delete, skip or relax a meaningful protection test merely to make the aggregate green. Do not add a second scheduler/browser/adapter/ledger or a duplicate document barrier.

### B2 — P1: 4 additional timing-sensitive full-suite failures

New rerun reports 4 extra `tests/launcher/test_backend.py` failures around browser readiness, stop-after-cycle and recovery. Executor reports 3 individually passed and one alternated; historical run skipped 11 while new run skipped 1, so exact causality is **NOT_VERIFIED** and the two totals are not directly comparable.

**Required:** retain original test IDs and real assertions, inspect captured current XML/traces and produce deterministic controlled-clock/event tests that distinguish a genuine shutdown/admission regression from collection-load instability. Do not increase production retry/timeout or weaken Stop semantics to make a test pass.

### B3 — P1: purchase-entry incident and full new-order closure remain unresolved

The latest purchase diagnostic patch is logging only. It does not repair the original `SecurityViolation` / stale-session-related incident or prove why purchase preparation failed. Six reported completed polling cycles for each module establish bounded scheduler liveness, **not** one fresh order's read→research→purchase→quote→mail closed loop.

**Required:** preserve privacy and current business data. Diagnose from existing sanitized evidence and deterministic fault injection first; no synthetic live purchase/mail/write or replay of a manually settled order. Any future true live order is observed by its original authorized natural workflow and original identity/SENT/UNKNOWN gates; only then may the relevant business outcome be confirmed. No automatic deployment or previously settled order rerun is authorized by this Review.

### B4 — evidence and production status limits

The historical 26 test names and aggregate result are grounded, but original test tracebacks are `NOT_RETAINED`. New full log and JUnit XML are recorded at local paths with SHA256, but were not published in the repo and were not independently inspected by CEO. The retained build snapshot lacks tests; do not claim the binary contains or certifies test files. Executor-reported 2875-file hash equality is strong build/provenance evidence but not a guarantee of future business correctness.

**Required:** new Executor extracts a narrowly sanitized, complete per-failure result from the current retained JUnit/log and attaches enough reproducible evidence in the RFQ record to distinguish mismatch versus defect, without secrets/customer values or large unneeded artifacts.

### Disposition and ownership

- `RFQ-016` overall: **CHANGES_REQUESTED / HEALTH_HOLD**; source and real business acceptance **not PASS**.
- **No change** to the installed EXE, runtime, Chrome/CDP `9222`, shared profile, production SQLite/WAL/SHM, SENT/UNKNOWN ledger, authorized business state, or previous rollback. The current installed process is not independently evaluated in this review; the verdict alone is neither an order to force-stop nor an approval to keep writing in the face of a confirmed new fault.
- Implementation returns to the **single replacement WorkBuddy/DeepSeek Executor** under the same RFQ; use a new clean development branch from the pinned accepted GitHub baseline, not from stale `main`, and stop prior Executor operations before any new live work.
- CEO reviews the resulting exact commit, code diff, full failure-by-failure disposition, isolated tests and appropriately authorized true business evidence. PASS requires closing meaningful blockers; a green aggregate alone cannot confer production approval.
- Branch/worktree pruning is a separate, **read-only audit first**. Preserve all unique commits, default branch and protected production-dependent old worktrees; no mass branch deletion is authorized.
- CEO Review tools: GitHub connector/file inspection only. **COMPUTER_USE_NOT_USED**.
