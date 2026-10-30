# RFQ-016 execution evidence

Status: REVIEW_REQUIRED / SOURCE_ONLY / NOT_DEPLOYED.

## Protected takeover and baseline
- Original root checkout: main c3a597d, dirty/untracked unrelated work preserved.
- Reused existing V1.6 worktree: C:/Users/Leo/.codex/worktrees/v16-independent-scheduling/INSO_Leo.
- Unique local 7574516f18c8ee3225b5039f2eb4aeabd0045bbc preserved as ancestor; contains reports only relative to f8f2c32. Remote requirement be46555471cb78786437d04bf61210a3d384a74e merged without overwriting history.
- GitHub-only proxy was unavailable; fetch succeeded with command-local proxy override. No permanent Git/network configuration changed.
- Installed EXE SHA256 B51C7F66E41A6C3F6266FF772E9EEF8AEB161F986D2705B97320D67CE62B283B matches prior recorded artifact attributed to f8f2c32. Exact frozen source equivalence independently NOT_VERIFIED.
- Read-only OS process inspection found installed V1.6 running. No process stop/kill, installation, browser/CDP connection, credential lookup, configuration edit or real mail was performed. Owner elected to stop automatic business in the original program; actual completed stop NOT_VERIFIED by executor.
- No temporary handoff found. Other dirty/version worktrees retained; no new worktree created, no removal/prune needed.

## Read-only field diagnosis (aggregate only)
Production SQLite opened URI mode=ro plus PRAGMA query_only; no business rows or raw output copied into Git. Observed recipient outcomes: IMPORTANT_ORDER SENT32; DUPLICATE_ORDER SENT2; TP_RESEARCH SENT6; PURCHASE_EXCEPTION SENT133. Exception command families: runtime42, purchase-exception40, quotation16, website2, other19. Fifteen GOOGLE_READ_RETRY_EXHAUSTED commands recorded from 2026-10-18 to 2026-10-30. No pending/retryable exception recipients at inspection instant. These are observations, not a claim that every historic message was false.

## Root causes and reuse audit
- backend._defer_google_read_poll creates runtime mail even when the next normal cycle can recover. Runtime incident keys include run/cycle identifiers.
- Website/source observers emit warnings before final business completion. Direct operator SMTP bypasses durable outbox.
- V12 durable queue has no common age admission. V13 only customer-quoted rows had age gating; other automatic quote states bypassed it. TP had no calendar-month admission.
- Task center projects durable procurement history and caches DTOs; ordinary source reads did not independently update current customer status.
- Reuse existing coordinator, independent scheduler, source reader callbacks, SQLite notification commands/recipient ledger and SMTP worker. No new dependency, scheduler, database, browser or mail transport.
- Review metadata and suppression reason extend the existing outbox; SENT/UNKNOWN recipients are never reset. Existing quiesced migration owns additive upgrade. Legacy false alerts are suppressed before SMTP, not deleted.

## Red evidence
Two correctly initialized offline regressions failed before fixes: recoverable Google read warning reached fake SMTP (1 call), and a31-day-old durable queued item reached research (1 call). Initial test preparation errors were corrected before recording this business reproduction. Baseline command: python -m pytest tests/workflow/test_rfq016_regressions.py -q -p no:cacheprovider --basetemp <task-owned sandbox>. Result2FAILED in0.93s. After initial gates:2PASS in0.81s.

## Final source verification
- Full suite:3272PASS /0FAIL /1SKIP /129.68s;3273 cases. RFQ016-specific49cases PASS. Machine-readable summary and exact acceptance case names: TEST_REPORT.json.
- Existing skipped symlink test: Windows environment cannot create symlinks. This is not a product PASS and was not hidden or removed.
- Command: Python3.12.10 -X utf8 -m pytest tests -q -p no:cacheprovider --basetemp <task-owned sandbox> --tb=short --junitxml=<task-owned report>. Existing release site-packages supplied through process-local PYTHONPATH; existing frozen Tcl/Tk data supplied through process-local TCL_LIBRARY/TK_LIBRARY. No packages installed. Earlier default-environment collection errors and intermediate failing suites were repaired; only the final full run is acceptance evidence.
- Ruff all src/tests PASS; git diff --check PASS; inspected source/test diff and ancestry. Both7574516 andbe46555 remain ancestors. No unrelated root dirty work was staged.
- Actual QQSMTPTransport exercised with injected ScriptedSMTP/FakeCredentials. False, stale, recovered, invalid, expired and legacy already-SENT/UNKNOWN samples:0SMTP attempts. Confirmed manual login, native unknown write and fully qualified persistent incident:1notification at most per ongoing incident across restart. Current important-order/TP mail retained. Global test SMTP floor prevented real outbound connections.

## Material implementation decisions
- Common date admission uses original bound RFQ date first; exact immutable intake is explicitly approximate. Brief identity/date conflicts never fall back to a recent guessed date. Missing optional Brief read/schema can only fall back to that pre-existing exact ID; new undated rows are excluded without queue creation.
- V12 gates discovery, durable retries, continuation, post-Research brand write, procurement and status-write recovery. V13 all automatic statuses and revalidation before update are gated; TP discovery, existing claims/recovery, continuations and enqueue are calendar-month gated. Owner age exemption is scoped to one invocation; no automatic retry privilege is minted.
- Source projection uses original source-read observations and invalidates cached DTOs; failed reads explicitly stale. Customer status and procurement/UNKNOWN history remain separate. No database alteration or external write was used to fake customer-status synchronization.
- Distinguish pre-click timeout from possible dispatched quotation effects. A missing/unconfirmed response cannot be settled by a human-edited Sheet status. The existing hold JSON keeps a bounded native-effect marker in the already discarded quotation slot, not raw quote data; old reader regression remains compatible. Manual rerun/close cannot clear UNKNOWN; known pre-effect problems retain original manual retry capability.
- One existing outbox with additive review_json/suppression_reason and verified pre-upgrade backup. Legacy false pending alerts become auditable SUPPRESSED at dispatch, not deleted. Original SENT/UNKNOWN rows remain immutable; stable incident keys and exact legacy aliases stop restart/format-change replay. No second scheduler/database/mail system or interval workaround.
- Recipient allowlist and native/current-source review run before SMTP. Temporary loss of current source proof defers qualified business commands for the next original source read; unverified anomaly commands are suppressed. Corrupt/unavailable ledgers cannot safely provide durable deduplication or truthful delivery: business remains protected/stopped and local UI/logs remain authoritative; no bypass SMTP fallback is allowed.

## Remaining UNKNOWN / release isolation
- Installed/frozen source equivalence beyond matching recorded artifact hash, current Owner-completed stop state, real latest customer status, Google read/write availability, historical external write outcomes and real delivery after a future release remain NOT_VERIFIED. No claimed production fix.
- Existing production SENT/UNKNOWN/outbox rows were inspected read-only and not edited. A future separately authorized release must use original safe stop/drain, verified backup/migration, preserved profile/session and original account/recipients; review pending queue through this same gate. No automatic RFQ016 installation is authorized.
- No temporary handoff, extra worktree, release staging, build or helper service was created. Task-owned synthetic test sandboxes/logs are retired after retaining this bounded report; existing runtime, release/rollback, CDP, Vault, Git and unknown dirty assets are protected.


COMPUTER_USE_NOT_USED. Methods: Git, PowerShell/Python source tools, read-only OS process/hash inspection, read-only SQLite aggregate queries, synthetic tests. Production outcome remains NOT_VERIFIED; RFQ-016 install is not authorized.

## Cleanup audit
Cleanup verified each resolved absolute target under D:/Program_Leo/INSO_Leo/.tmp and inspected reparse points before removal. Known task-owned log/XML files retired. Some individually identified pytest sandbox directories reject filesystem enumeration/deletion with access denied; retained without changing ACLs, forcing locks or following links. The exact retained names are recorded in TEST_REPORT.json. No production/build/release/profile/Git or unknown paths were removed. This filesystem limitation does not affect the verified source tests.

Final completion audit found and reproduced one normal-mail lifecycle concern: a temporary final-review exception suppressed a legitimate business message permanently. The focused red regression failed1case in0.86s. It now defers without an SMTP attempt until the original source reviewer can validate it; actual stale/invalid anomaly evidence is still suppressed. No retry interval or new worker was introduced. Final full suite after this last source change:3272PASS/1SKIP in129.68s; all49 RFQ016 regressions pass.

## Completion audit before source submission
Original objective and latest Owner steering rechecked twice against implementation, native fake-SMTP evidence, complete regression, Git ancestry, pending production operations and cleanup. Authorized source work is complete and ready for CEO independent review. Pending: CEO source verdict and any separately authorized release/live business acceptance. No installation/restart/real messages or follow-on business task is scheduled or implied.

Verified source/test commit: `77a3e83f499d91242fe8012570f939b09d8c25a0`. Delivery target: `origin/codex/v1-6-independent-scheduling`. Final report and source SHA metadata are documentation-only additions after this source commit.
