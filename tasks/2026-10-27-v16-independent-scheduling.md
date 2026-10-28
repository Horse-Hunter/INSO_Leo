# V1.6 independent scheduling and Owner-authorized production release

status: REVIEW_REQUIRED — native login fix + Stage E isolated owner integration submitted;3001PASS/1SKIP; no production change; default actor assembly OFF; real E/F acceptance open
owner: Owner; executor Codex
baseline: 669fe6ada3a450eaef5f74532a371d6fb55ffd01
branch: codex/v1-6-independent-scheduling

## Authority and goal
Owner2026-10-27 explicitly authorizes development, offline/readonly/live checks,
canonical build/install, verified compatible migration, production config changes
needed for V1.6, and all three modules' real configured business, Sheets writes,
procurement inquiries, quotation follow-up and existing recipients' SMTP. No
per-order approval/count cap/staged rollout is introduced. Missing identity or
transaction authority blocks that task, never guesses authorization. Payment,
unconfigured recipients, challenge bypass and historical SENT replay excluded.
Keep V1.5 installed/runtime and70956's immutable test tree intact during dev.

## Reuse audit and minimum design
| Existing owner | Reused contract | Necessary extension |
| --- | --- | --- |
| workflow.service.WorkflowRuntime | existing poll/worker threads, stop event | per-module in-memory monotonic deadlines and resource ownership; no second business ledger |
| launcher.backend | canonical composition, poll gate, manual condition, browser lifecycle | select due module instead of CombinedCycle; cooperative yield during completed-row safety waits |
| workflow.v12_flow / v13_integration / tp_research | existing inquiry/quote/TP paths and IDs | no business rules duplicated; exact same execution gates |
| workflow.v12_notifications | SQLite atomic recipient claims, UNKNOWN and SENT protection, QQ transport | defer dispatch to existing notification worker so mail can overlap browser work |
| launcher.workbench_snapshot / gui | immutable observation, bounded caches/logs, five pages | each module next due/fault, visible version |
| existing Windows script/spec and app_paths | one release path and shared mutex/runtime | allow version1.6, isolated install and verified V1.5 rollback |

One owner thread serializes all shared CDP/Playwright/Sheets/Excel browser work;
resource-conflicting tasks queue, never share pages or sync clients across threads.
Independent SMTP/local projection uses the already-existing background worker.
During existing completed-inquiry120s cooldown, due quotation/TP may borrow idle
browser on the same thread; original safety minimum is never shortened. No new
daemon, browser manager, dependencies, arbitrary throughput/order-count limit.
All three periods independently configurable; default existing900s each, measured
from each module's own completion, no combined15m wait. Local failures/backoff
isolated, durable ledger/security/ownership failures retain shared-stop semantics.
Manual actions reuse original condition/gate and fresh permission checks.

## Acceptance and verification
- [x] independent deadlines/fairness, safe resource arbitration, shutdown and manual races (offline)
- [x] SMTP parallel with browser, same-order serialization, SENT/UNKNOWN protection (offline; real notification accepted)
- [x] per-module failures/backoff and GUI schedules/version (offline; live resource short-check only)
- [x] full offline and synthetic race/fault regressions, real read-only adapters
- [x] canonical frozen selfcheck/scan/manifest, rollback and database/config/vault backup
- [x] stop V1.5 normally, verified V1.6 shared-runtime install, three-module configuration/start
- [ ] external outcomes checked, truthful counts/failures/UNKNOWN and final CEO audit

## Verified facts and unresolved risks
Original70956 running source9f5522d7; never edit its worktree or interrupt it.
V1.5 latest visible programDA217696...9A4A, current runtime preserved. Historical
fourTP/sixTP-SENT immutable. Previously configured recipients229 and Shawn.
Existing ERP authority is only validated procurement-inquiry Save-and-Send, not
purchase payment or supplier contractual orders; audit exact gates before live.
UNKNOWN: current production pending quantities, website state, final new runtime
CPU/game impact and transaction constraints beyond existing narrow gate.

## Execution log
Branch/worktree isolated from exact baseline. No V1.5/longsoak files changed.
Initial source/governance audit completed; early no-live state SUPERSEDED below.

2026-10-27 pre-build: implementation extends only existing WorkflowRuntime,
launcher composition, notification worker and five-page observation. Fixed actor
ownership and atomic outbox claims tested; closed-row cooldown cooperatively
yields to quotation/TP and invalidates the outer source snapshot on return.
Idle observation preserves each module's own deadline, no shared-time overwrite.
Canonical configured empty-poll composition covered for both legacy and V1.6.
Final full regression: 2759 PASS/1 SKIP,100.86s; Ruff src/tests/changed entry PASS.
Earlier full runs exposed intermittent5s legacy readiness-test timeout and worker
leak after assertion failure. Tests now shut down all owned backend instances
before monkeypatch restoration and retain failure-only thread-stack diagnostics;
isolated backend53PASS and two subsequent full runs passed. No timeout weakened.
Historical timing root cause remains NOT_REPRODUCED; do not call a business fix.
Synthetic UI:45layouts/90recovery cycles/100,500,1000orders; zero callback errors,
version visible. Widget scaling is not system DPI certification.
Real canonical six sources SUCCESS; INSO quotation readonly parsed63rows;
Google configured sources/quotation metadata and read/RFQ anchors PASS. Sources
pending3/0; four validTP candidates already_processed, no historical replay.
These probes prohibited SMTP/write operations; original tabs preserved.
Fresh verified backup protects configuration, opaque vault, entire ledger;
V1.6 migrations on copy produced no schema/row delta, production migration NOT_NEEDED.
FourTP/sixTP-SENT and138totalSENT preserved; V1.5 rollback assets2875 verified.
Owner normal V1.5 exit2026-10-27T01:32:46Z code0. Protected70956 unaffected.
Build/install/live acceptance next; no production side effects executed yet.

2026-10-27 release/live update (supersedes pre-build next step): source99dd22c
built using canonical script, RELEASE_SCAN_OK and frozen selfcheck PASS. New EXE
16E38F30E253041F7ED41E0447DEF744F6912D7B310F6DBDF616556CDBDC8B82 installed at
dist/INSO_V1.6;2875asset comparison, installed self/idlecheck PASS. Existing mutex
held for verified backup/install; ledger zero delta pre-business. Owner-authorized
config sets v16/tp true, preserves quotationtrue, independent periods900each.
V1.4/V1.5 remain intact; runtime junction unchanged. Real EXE74176/observer84608
started09:54:40 --start-inquiry. Source conflicts held per task; no forced writes.
As of10:27: fourSOURCE_CHANGED results across2orders/3logged inquiry cycles;
quote1cycle31NO_RECENT_QUOTE/1PRICE_UNCHANGED/1SOURCE_IDENTITY_UNRESOLVED;
onePURCHASE_EXCEPTION notification command, one newly acceptedSMTP recipient.
Historical138SENT, fourTP/sixTP-SENT/immutable commands unchanged, integrityok.
No new procurementSAVED or quoteSheet-write confirmed. TP enabled, preflight4
already_processed/0new candidates; independent live TP completion NOT_VERIFIED.
Real UI window version enumerated; live control inspection blocked by app-approval
timeout, so newEXE menu/tray/exit NOT_VERIFIED (synthetic/oldV1.5 not substituted).
Two121s finite resource samples: hostCPU0.33085%/0.28956%; handles3982..5118 then
933..1041 after batch. Peak is transient, not established unbounded leak; longer
V1.6 soak/game impact UNKNOWN. Full report and allowlisted evidence linked in
V16_RELEASE_REPORT.md. No speculative business/resource fix made after build.
Owned267925710-byte stage retired after asset verification; exact owned exited
test trees, production compatibility copy and temporary real research workbook
retired. Protected original70956/testtree, live runtime, rollback/config/vault/DB
backups and V1.5 report tree retained; no new handoff or duplicate V1.6 worktree.
CEO final audit next. Source frozen at99dd22c; subsequent commits evidence only.


## CEO independent final audit — 2026-10-27

**Verdict: CHANGES_REQUESTED (source-level nested execution context);
PRODUCTION_INSTALLED_RUNNING is executor-reported, not full production
E2E PASS. Audit-only: no live process, configuration, database, browser
or business operation was changed.**

Review anchor: baseline
`669fe6ada3a450eaef5f74532a371d6fb55ffd01`;
application code
`99dd22c43fd83852dc1d45d13c4cfed46b0ebe0d`;
evidence head
`df6646c7542bea98f2aaeb8218e9254c7873a9c2`.
The exact GitHub comparison consists of one application/test/
packaging commit followed by one documentation/evidence commit.
Reviewed changed application source (`src/workflow/service.py`,
`src/launcher/backend.py`, `src/launcher/workbench_snapshot.py`,
`src/workflow/v12_notifications.py`,
`src/workflow/v13_integration.py`), published synthetic tests,
the release report, actual-production ledger/log summaries,
installation and native-resource counters. The review did not
independently execute Windows EXE, inspect local sensitive
SQLite bytes or remotely control the live instance.

### Accepted findings / retained guardrails

- The added WorkflowRuntime module clocks are monotonic,
  independently configured and claim/complete one shared
  browser resource from a fixed owner thread. This provides
  independent *scheduling*, NOT simultaneous browser/CDP
  queries. Existing outbox worker delivery can overlap the
  browser actor. No new browser service, persistent business
  state system or concurrent Playwright sync object use
  was introduced by this change.
- Existing durable purchase/quotation/TP identity checks,
  SMTP recipient claim semantics, SENT/UNKNOWN protection
  and normal rollback strategy remain present. Original
  cooldown does not get shortened by the yielded work;
  nested work may extend elapsed cooldown. Existing
  test report: 2759 PASS / 1 SKIP. These facts do not
  amount to full live business E2E acceptance.
- Executor-reported install at
  `D:/Program_Leo/INSO_Leo/dist/INSO_V1.6/INSO_V1.6.exe`;
  SHA256
  `16E38F30E253041F7ED41E0447DEF744F6912D7B310F6DBDF616556CDBDC8B82`,
  asset-count 2875, backup and current ledger compatibility
  checks were submitted. Owner authorized existing configured
  production business; this review does NOT revoke or
  expand that authority. Preserve V1.5/V1.4 backups and
  always roll back program/config against **current**
  durable ledger, never an older DB snapshot after effects.
- Evidence as of ~10:27 +08 reports source identity
  `SOURCE_CHANGED` refusal, quotation
  `NO_RECENT_QUOTE`/identity refusal/unchanged price,
  one new PURCHASE_EXCEPTION SMTP recipient marked SENT,
  stable historical four TP/six TP-SENT and 138 pre-live
  historical SENT. No newly confirmed purchase SAVED or
  quotation Sheet-write; no new TP candidate and TP
  completed-cycle independent receipt is NOT_VERIFIED.
  SMTP SENT means transport accepted, not mailbox delivery.
- Two ~121s resource intervals show 0.33085% and
  0.28956% whole-host application CPU on 16 logical CPUs;
  handles reached >5,000 during a query and fell to
  <1,041 at a subsequent batch boundary. Do not label
  a proven persistent leak, nor pronounce it safe for
  unattended multi-cycle use. Browser child CPU/GPU
  and gameplay impact not included. Existing long soak
  PID70956 uses old 9f source and cannot certify V1.6.

### P1 — nested module overwrites caller's execution identity

`src/launcher/backend.py`: V1.6 `execute(module)`
sets instance-wide `self._cycle_id` and
`self._last_poll` at the start of every module.
`_wait_between_rows` yields the inquiry's browser
resource and directly invokes
`_run_independent_job(other)` for due quotation/TP,
then resumes the *same* outer inquiry invocation.
There is no save-and-restore of those per-execution
fields when the inner job exits. Subsequent outer
purchase results/alerts and `_complete_inquiry`
log using `self._cycle_id`; the Research
preparation-failure cache also keys against
`self._last_poll`. Hence a borrowed nested module
can cause a later outer inquiry event/cache to be
associated with the **inner** run identity.
This is source-provable control-flow risk, NOT a
claim that an actual incorrect purchase was made.
Existing test
`test_completed_row_cooldown_runs_due_modules`
mocks `_module_execute` and does not assert the
real nested run identity is restored. P1 requires
a deterministic offline real-closure regression,
a minimally scoped identity/context repair if
reproduced, and corresponding review before
claiming final source PASS.

### P2 — nested module alters outer observation/timing context

`RuntimeObservation.begin_module` rewrites
shared `cycle_started_at` and
`cycle_started_monotonic`;
`stage` closes other modules' active stages.
When inner quotation/TP borrows the browser during
outer inquiry's row cooldown, observation can lose
the original inquiry waiting-stage accounting,
and `finish_module` assigns one shared
`cycle_finished_at`. This risks GUI timing and
audit timeline misrepresentation. Test the exact
nested wait → inner module → resume → outer
completion sequence, with exception and stop
variants; preserve the old 120s safety minimum
and immutable business state.

### Additional acceptance gaps (not invented defects)

- Only one browser actor is permitted by design.
  There is no actual CDP site-level parallel
  browser execution yet, despite Owner's earlier
  interest in independently owned short-lived
  tabs. It must be described as serialized
  browser operation plus independent deadlines
  and parallel SMTP, not three parallel CDP
  site workers. Treat further tab-level parallelism
  as a separately reviewed feature, not a
  permission to share sync Playwright across threads.
- Independent actual TP cycle completion/log proof
  is missing; do not treat four already-processed
  tasks as new TP success. Real production
  procurement/Sheet-write success is likewise
  not demonstrated, though safe refusals are
  meaningful. Synthetic new-EXE UI tests do not
  replace unverified live control/tray checks.
- Release/long-term stability, 100/150% OS DPI,
  Chrome/gaming performance and native semaphore
  lifetime attribution remain NOT_VERIFIED.

### Disposition

**CHANGES_REQUESTED for unconditional V1.6 source/release sign-off.**
Do NOT represent current V1.6 as a full three-module
external-write success or stable unattended PASS.
No emergency rollback is inferred from the currently
submitted evidence; no live-process changes were
made or authorized by this audit. Preserve the
running program/ledger and original protected
soak. First reproduce P1/P2 offline against the
frozen V1.6 source and return a minimal patch +
tests as a separate review, plus independent
read-only evidence of TP cycle execution and
multi-cycle resources. If actual integrity/
idempotency faults appear, escalate for explicit
Owner operational decision rather than changing
running production from this review.

## Unified remaining acceptance — Owner2026-10-27 (current authority)

This instruction supersedes this packet's earlier release authority for this
round: no stopping/restarting/replacing live V1.6 EXE, no production DB/config/
browser or protected24h-tree operations. Only isolated code/tests and existing
sanitized evidence. Reuse clean V1.6 development checkout on independent branch
codex/v1-6-audit-fixes from remotely verified71a68f2; do not create duplicate trees.
PhaseA is independently committed before B/C/D; any future install requires a
separate deployment proposal, not an automatic consequence of source fixes.

| Item | Current result | Evidence / remaining requirement |
| --- | --- | --- |
| A nested execution identity, pending pause and cache | PASS reviewed/deployed |04075bc installed; real parent ID restored across nested quotation/TP; edge paths offline |
| A independent GUI timing and waiting | PASS reviewed/deployed | Reviewed module timing source included; full live menu/phase interaction still NOT_VERIFIED |
| A cleanup/shared fault, STOP and120s minimum | PASS offline reviewed | Existing targeted real-closure tests; no unsafe live fault manufactured |
| A full regression | PASS | Final source2802passed/1skipped113.81s; frozen-wall32PASS9.55s; isolated cards1PASS3.29s;Ruff/diff PASS; earlier Tk initialization flake retained as UNKNOWN |
| B real TP independent900s begin/end | FAIL timely independent execution; PASS receipts |2 real completedTP cycles; nextbegin1354.210s after finish,454.210s beyond900 due single browser actor |
| B future-source TP cycle receipts | PASS (offline only) | Three actual empty TpCycle calls at independent900s; no orders/mails used as substitute |
| B new purchase success | NOT_VERIFIED | Prior source-conflict holds are not successful procurement |
| B quote/Google write/readback success | NOT_VERIFIED | Prior no-recent/unchanged/identity refusals, no forced writes |
| B SMTP transport acceptance in prior export | PASS acceptance only | New runtime fault1SENT, current140SENT; historic139 full receipt rows unchanged |
| B SMTP current UNKNOWN/final mailbox delivery | NOT_VERIFIED final delivery/live UNKNOWN | Current coherent readonly DB0UNKNOWN/PENDING/SENDING; no live UNKNOWN case to exercise |
| B real restart idempotency | PASS historical preservation | Normal authorized stop/install/restart;108oldcommands,139oldSENT,4TP fullrows unchanged; no historical replay |
| C concurrency reuse/design and blocker audit | PASS | Independent docs/V16_PAGE_CONCURRENCY_DESIGN.md; preferred bounded same-CDP clients vs broad async conversion |
| C page concurrency implementation | DEFERRED actors; new source20fda49 isolated | Native identity now verified after navigation; full actor integration still NOT_IMPLEMENTED |
| C actual webpage overlap/same-order queue timeline | PASS native ownership/navigation only; NOT_VERIFIED business/order exclusion | SameChrome/two own pages HQEW0.109s/ICnet0.219s; before/after identity and precise cleanupPASS; full actors not enabled |
| D strict continuous multi-cycle stability | NOT_VERIFIED | New6min and earlier2x121s intermittent samples; release observed, no proven unattended upper bound |
| D finite current process counters | PASS finite30min |31samples/1800.063s, avg0.28961%host; handlespeak5646→1004; RSSgrowth remains open |
| D native semaphore owner/release | PASS | MainPID74176:5196→576semaphores, total5770→1131handles |
| D exact allocating objects and long-run upper bound | NOT_VERIFIED | Repeated transient release is not proof of bounded unattended use |
| D Chrome active workload/game impact | NOT_VERIFIED | Short process-role counts are not active Research GPU or frame-rate acceptance; no game launched |
| D live EXE menus/tray/normal exit | NOT_VERIFIED current interactive suite | Installedself/idlePASS; prior99ddnormalexit0; new GUI screenshot timeout, no guessed input |
| D100%/150% systemDPI | DEFERRED | No Owner display-setting changes; prior widget scaling not substitute |
| D GUI/ledger, recovery/manual consistency | NOT_VERIFIED | Offline checks do not certify current production state |
| D long-term V1.6 unattended stability | NOT_VERIFIED | Old9f/70956 cannot certify V1.6 |
| D V1.5/V1.4 rollback preservation | PASS fresh verification | V14/V15 manifests unchanged; reviewed install rollback and fresh compatible ledger backup verified |

Reuse: existing module scheduler ownership, observation locks/DTOs, exception
classification and canonical domain engines. Minimal scope stacks save only
execution metadata, not mutable business/session results. Failed cleanup latches
actor invalid and pauses all resource dependents; ownership checks remain strict.
Per-module observation fields are additive, no new state ledger or GUI pages.

PhaseA execution: `_run_independent_job` now scopes cycle/last-poll/research-failure
cache/pending-pause metadata. Context finally restores ancestors on all unwind
paths; never copies back sessions or mutable business results. Observation scopes
retain ancestor waiting time and restore global focus while keeping child results.
Independent DTO cycle start/end/elapsed has its own fields, rendered in same cards.
Cleanup failure exposed by real-path tests now invalidates actor and rejects any
subsequent claim instead of masking the original fault with a resume error.
Regression follows actual launcher closure -> CombinedCycle -> real durable V12
flow, V13IntegratedCycle/V13QuotationCycle and TpCycle, with only external ports
synthetic; uses independent test ledgers. Includes timeout/local pause/STOP/shared
DB fault/cleanup failure, and outer pending pause for both inner module types.
Captured real purchase log records retain outercycle; child mail attempts <=2;
no manufactured procurement, no real SMTP attempt in passing tests. No production
file/process/config/DB/browser/protected-soak operations performed this round.

PhaseA independent commit: a2bc2f01acbde576caf378d625788cd3e31d0d24, pushed to
requested V1.6 branch before subsequent source work. PhaseB adds one allowlisted
cycle begin/terminal record on existing rotating log (no separate log/monitor or
ledger), including module/cycle/elapsed/next-delay; zero eligible TP also records
completion. INFO enabled for backend logger only, root warning policy unchanged.
`completed` is cycle completion, never external business-success proof. Unknown
fields/nonfinite values/raw bodies remain redacted. Separate source requires
future reviewed deployment; it cannot backfill current frozen EXE receipts.
PhaseB39 targeted PASS7.45s; final source full2794PASS/1SKIP111.03s, Ruff PASS.
Existing sanitized production log summary as of11:23:59:5purchase/4quotation
cycle IDs;8SOURCE_CHANGED,104NO_RECENT_QUOTE,3PRICE_UNCHANGED,4unresolved identities.
No independent TP receipts. Read-only logs do not establish fresh external writes.
Prior SMTP export as of10:25:26 reports139SENT,138historicalSENT unchanged then;
current SMTP state NOT_VERIFIED because this round forbids productionDB access.
No live restart, no repeat mail, no productionDB/browser/config query; only
existing sanitized logfiles were read as explicitly allowed in phaseB.

PhaseB commit b6187b5ffa8b279c0fc82c57e1e478a9472e2148 is source/log observability,
not deployed instrumentation. PhaseC independently documents existing first-page
event binding race, same-URL reuse, sync thread affinity and shared callback/order
identity gaps. Preferred bounded same-CDP independent sync-client actors reuse
adapters; broad async migration deferred. No unsupported parallel mode wired in,
no callback timing presented as actual webpage overlap. Implementation and actual
timeline remain open; safe acceptance needs a window that does not commandeer
current live browser. The explicit no-production-browser constraint is honored.

P1 unwind follow-up after stageC design: added rawTimeoutError and explicit
V13Stopped cases (32 nested cases total). CombinedCycle must propagate borrowed
cancellation rather than recategorizing it as an inquiry-local failure. Failed
cleanup is now typed GLOBAL_STOP/INSO_OPERATION_NOT_CLOSED with original cause,
so the outer coordinator cannot mask it; unsafe actor remains unclaimable.
An existing outer pause is retained if another local pause arrives.115targeted
PASS14.27s and final full2802PASS/1SKIP112.37s, Ruff PASS. These changes remain
isolated source only; actual production stop/restart not performed.

Final changed application source:04075bc884c9c2927e677edcbddcb43419833aef.
Cache isolation follow-up: each new execution starts with empty preparation-failure
cache, preserving/restoring its caller's cache on nesting. This does not depend
on wall-clock timestamps being different; pending-pause cases freeze wall clock
and still preserve monotonic timing/context.32PASS9.55s. Final same application
source full2802PASS/1SKIP113.81s; added existing isolated Tk card assertions1PASS
3.29s without application source delta. Previous full attempt at that source
2801PASS/1FAIL/1SKIP had existingMockTk tcl_findLibrary init failure, standalone
module2PASS1.59s and fresh full passed; root UNKNOWN, not a claimed runtime fix.
Existing symlink-capability skip independently explained: safety8PASS/1SKIP0.48s.
StageD finite native observations completed, no monitor persists. Six-minute
window11:29:31–11:35:31 shows CPU0.20361–0.24420%host, RSS138.45–141.42MiB,
Private108.61–111.36MiB,9native threads; handles5736peak in samples, then1111.
Type snapshots5770→1131total and5196→576semaphore establish actual release by
same main process, not allocating object origin. Observer remains1thread/128handles.
Chrome root was initially ambiguous because child command lines inherit9222;
first-window Chrome data not attributed. Separate60s ancestry-resolved window
finds exactly one root and browser/GPU/renderer/utility/crashpad cohorts. No raw
command lines saved, no CDP/page/profile access. CPU cohort excludes exited-child
cost; collection overlaps some offline regression; no isolated/game benchmark.
Strict continuous multi-cycle stability, UI live consistency and current SMTP
receipt integrity remain unverified; no fresh productionDB access permitted.
Current frozen99dd22c log IDs can be affected by P1, so logged cycle counts are
only tag counts, not independent correct-cycle proof. Full audit report appended
to V16_RELEASE_REPORT.md; no duplicate completion report. Proposed reviewed later
asset-only replacement is documented but requires a separate Owner install window;
no newEXE built or installed, no config/DB/browser/process mutation, no production
effects or new authority inferred. C remains deferred, not deleted from scope.
Owned isolated test/resource directories retired after process exit and evidence
copy;1091805404bytes removed in two checked passes. Small sanitized test stdout
and committed evidence retained. No production/runtime/rollback/profile/70956
directory cleaned. No permanent sampler remains. Existing development worktree
reused; no new worktree or handoff artifact introduced. Final unified checklist
remains authoritative for open requirements; do not infer all-stage completion.


## CEO independent remediation re-review — 2026-10-27

**Decision: PASS for the explicitly delivered A/B-source/C-design/D-evidence
remediation scope. The prior P1/P2 SOURCE CHANGES_REQUESTED is resolved
at source-review level. This is NOT V1.6 overall release closeout:
`REVIEW_REQUIRED / SOURCE_FIXES_NOT_DEPLOYED`.**

Review basis: originally reviewed commit
`71a68f28d90ef96656cb78291c075361cb8112e2`;
submitted reviewed head
`f023495a89d098ddffc3674e4160be4dba4be678`;
final application source
`04075bc884c9c2927e677edcbddcb43419833aef`.
GitHub branch and 6-commit fast-forward were independently confirmed.
Commit sequence:
`a2bc2f01acbde576caf378d625788cd3e31d0d24`,
`b6187b5ffa8b279c0fc82c57e1e478a9472e2148`,
`74f93dd6156d1c1a2fdb6a5d751c80382f7f089f`,
`6f8dd048248eae8875fba7a036327242b0e92027`,
`04075bc884c9c2927e677edcbddcb43419833aef`,
`f023495a89d098ddffc3674e4160be4dba4be678`.
Exact comparison from 04075 to f023 changed documentation and
allowlisted audit evidence only, not application/test code.
Review accessed GitHub code, test sources, task/report, design
document and allowlisted JSON evidence; no independent Windows
execution, EXE/hash recomputation, local DB inspection,
browser interaction or production modification.

### A — SOURCE_FIX_REVIEW_PASS (prior P1/P2)

- Scoped `_run_independent_job` preserves the outer
  `_cycle_id`, `_last_poll`, preparation-error cache and
  pending pause when a due quotation/TP runs inside the
  120-second closed-row wait. A new job resets only its
  own preparation cache, including when wall-clock values
  are identical. Business/session/recipient state is not
  reverted; original durable authorization remains.
- RuntimeObservation's nested module scope restores the
  caller's cycle focus while preserving the ancestor
  wait stage. Additive immutable per-module start/end/
  elapsed fields are shown on the same five-page workbench.
- Cancellation can propagate through CombinedCycle;
  cleanup failure preserves original exception cause as
  typed GLOBAL_STOP and permanently invalidates browser
  resource admissions for that runtime. Existing module
  ownership, stop, source identity and SMTP protections
  have not been removed.
- Examined `tests/launcher/test_v16_nested_context.py`:
  32 parametrized real launcher closure → CombinedCycle →
  durable V12/V13/TP engines, with synthetic external
  ports and isolated ledgers. Tests verify parent
  cycle/cache attribution, prior pending pause, real
  cooldown lower bound, cleanup and cancellation,
  bounded receipt counts, state/ledger integrity.
  Frozen-old-method two-negative-controls and
  targeted results are submitted. `test_v16_cycle_receipts`
  exercises three real *empty* TP domain-cycle calls,
  with synthetic time 900s apart, and a strict
  sanitized-record allowlist.
- Executor-reported final offline full:
  2802 PASS / 1 SKIP (113.81s), targeted 115 PASS,
  identical-wall nested 32 PASS, isolated UI card 1 PASS;
  Ruff/diff PASS. Reviewer inspected code and tests,
  not independently executed the Windows suite.
  Earlier intermittent Mock Tk `tcl_findLibrary`
  failure remains root-cause UNKNOWN even though the
  later full rerun passed; existing symlink capability
  skip remains disclosed. No reason from this evidence
  to label either failure a production business defect
  or silently call it fully fixed.

### B — SOURCE_LOGGING_PASS, LIVE_TP_NOT_VERIFIED

- Structured rotating logger now emits allowlisted
  per-module begin/terminal phases, bounded cycle UUID,
  module, elapsed and next-delay, including empty TP
  cycles. `completed` is an execution-cycle receipt,
  NOT purchase/Sheet-write/mail success. Logger and
  sanitization source and invalid-field tests were
  reviewed.
- Those new receipts are NOT installed in the frozen
  running `99dd22c` executable. Existing sanitized
  logs to 11:23:59 +08 show five purchase/four
  quotation distinct *tags* and classified refusals;
  the prior P1 defect prevents treating these tags as
  proven accurate individual cycles. Real independent
  TP 900-second begin/end remains NOT_VERIFIED.
  Previously exported 139 accepted SENT recipients
  is historical-as-of evidence, not a fresh DB read
  or actual final mailbox delivery.

### C — DESIGN_PASS_ONLY; PAGE_CONCURRENCY_DEFERRED

- `docs/V16_PAGE_CONCURRENCY_DESIGN.md` explicitly
  identifies existing CDP context-wide first-page
  event race, same-URL reuse, sync-object thread
  ownership, shared site auth/pacing, source-key/order
  lease, callbacks and immutable handoff requirements.
  Bounded same-Chrome independent sync-client actors
  is a reasonable incremental candidate; exact-target
  ownership, verified source-key isolation, INSO/Google
  exclusivity, bounded resource use and real overlapping
  navigation timelines are still required.
- No actual simultaneous browser-source queries or
  Owner-authorized Chrome experiments were delivered.
  Independent deadlines plus overlapping SMTP is
  NOT equivalent to browser-query parallelism. Do not
  promote C to implementation PASS or omit it
  from future required scope.

### D — FINITE_RESOURCE_EVIDENCE_ACCEPTED; SOAK OPEN

- Native counters were taken from the older running
  frozen V1.6 program without process control. Six
  minutes / seven samples show app CPU
  0.20361–0.24420% host, RSS138.45–141.42MiB,
  private108.61–111.36MiB, nine native threads,
  handles peaking5736 before falling1111.
  Same-PID type snapshots confirm semaphores
  5196→576 and total handles 5770→1131.
  Thus real release was observed, not a proven
  unbounded handle leak or a proven perpetual bound.
- Initial Chrome-root attribution was ambiguous
  owing to inherited flags, correctly excluded;
  later 60s ancestry-resolved window identifies
  roles, but does not prove active browser
  workload/game frame-rate performance. Exited-child
  CPU, GPU utilization, continuous multi-cycle
  bounds and the original old-9f soak remain
  explicitly out of the V1.6 stability certificate.
- Executor reports retiring ~1.09GB of marked owned
  temporary artifacts without deleting production,
  rollback, profile, original protected soak or
  current compatible ledger; GitHub review cannot
  independently inspect those local deletions.

### Exact boundaries and disposition

**Accept this remediation delivery** and close prior
P1/P2 **source-review** objections. Do not assert
all V1.6 requirements are complete. The present
production EXE/source remains
`99dd22c43fd83852dc1d45d13c4cfed46b0ebe0d`
as reported. No new EXE was built/installed and
no live business, SMTP, Sheets, DB or browser work
was performed in this remediation round.

Outstanding after this PASS: install/verify reviewed
source at a separately Owner-approved normal window;
observe real empty TP cycle receipts and authentic
900-second timing; natural eligible procurement and
quotation Google write/readback results; current
SMTP/UNKNOWN and restart idempotency; real new
EXE GUI/menu/tray/exit/DPI/ledger consistency;
true independent CDP page-query overlap; long-run
V1.6 and gameplay impact. Do not manipulate
identities/UNKNOWN to manufacture success.
Keep historic SENT and rollback current compatible
ledger: never restore a stale pre-effect DB.

**CEO final classification for this turn:**
`REMEDIATION_REVIEW_PASS`,
`SOURCE_FIXES_NOT_DEPLOYED`,
`V16_OVERALL_REVIEW_REQUIRED`,
`FULL_PRODUCTION_E2E_NOT_VERIFIED`.
This review only writes the task audit note; it
does not deploy, run, stop or modify production.

## Remaining-order continuation2026-10-27 (after CEO PASS)

Owner remaining-order incorporated; no new ledger or worktree. Stage1 source
freeze/preinstall checks PASS: remoteee49203 preserved, src equals04075bc;
existing release runtime Tcl8.6.15/imports ready;43targetedPASS13.91s using existing
zoneinfo command-local override (initial global-Python collection lackedtzdata).
Actual oldEXE hash and74176/84608 presence verified read-only; no live mutation.
One-time install/drain/backup/build/asset-only/idle/resume/current-ledger rollback
plan in V16_RELEASE_REPORT.md. Stage2 WAIT_OWNER_INSTALL_WINDOW, not NOT_DEPLOYED
success. Stage3 realTP/currentSMTP/GUI/long-run still NOT_VERIFIED. Historical
9f soak formally closed at63e635062db9592681c1a16bab674b66cc346441, continuity
PASS / memory drift review required; no oldsoak restart or protected-tree changes.
Page-concurrency increment remains independent from install candidate04075bc;
no actual webpage overlap claimed. Existing unified checklist remains canonical.

### Independent page-ownership increment (not part of reviewed installation)

Source-only first prerequisite: canonical new_background_page now filters a
per-create random blank URL and proves returned Page's native Target.getTargetInfo
targetId equals Target.createTarget's exact response before marking/navigating.
First foreign event or spoofed creation URL cannot authorize a foreign page.
Failure closes only the target created by that request, including owner-tagged
creation failures. No new browser/client/profile/production toggle.
Existing adapter protocol fixtures upgraded, research481PASS3.24s; targeted
ownership11PASS0.54s covers foreign events, mismatched target, proof timeout,
unique creations and invalid owner. ScopedRuff PASS. This is a page factory
prerequisite ONLY, not actor integration, same-order arbitration or true browser
parallelism. No real browser access or overlap claim; full regression pending
before source review. Keep separate from installed04075bc candidate.

## Remaining-order checkpoint — Owner install window AUTHORIZED

Earlier WAIT_OWNER_INSTALL_WINDOW is SUPERSEDED: Owner explicitly approved normal
stop/fresh backup/reviewed-only build/install/idle/resume. Next prerequisite is
normal old74176/84608 exit, not another permission request. Computer Use could
restore correct window but screenshot failed twice and Tk controls unlabelled;
Owner Safe Stop then tray Exit requested, no guessed input or force-kill. At last
metadata check both remain, so no build/backup/DB/config/browser/install occurred.

| Existing item | Current result |
|---|---|
| Reviewed04075bc candidate source freeze | PASS;1b19390 holds exact reviewed src |
| Release environment / lock | PASS;43packages exact,Tcl8.6.15; no new dependency |
| Necessary preinstall targeted |43PASS13.91s |
| Repair install |AUTHORIZED_WAIT_NORMAL_EXIT / NOT_DEPLOYED |
| C exact native target correlation |PASS offline / REVIEW_REQUIRED;49677b7 + f49d785 |
| C blank keepalive/navigation compatibility |PASS offline; full2806PASS/1SKIP110.02s, additional12PASS0.57s |
| C finite client actors / runtime order leases |NOT_IMPLEMENTED |
| C real navigation/request overlap |NOT_VERIFIED; no real browser attached |
| RealTP900s / new mail / restart / GUI / long-run |NOT_VERIFIED; no old receipt reused as new success |

Independent page increment touches only canonicalresearch/cdp_pages.py plus3test
files; no business rule or dependency change, MUST NOT enter reviewed04075bc build.
Failed first full exposed exactblank contract conflicts, corrected before final
full; fixture/environment problems retained, not called production failures.
Full detail and single rollout/rollback plan remain in V16_RELEASE_REPORT.md.
Completed own test dirs391424417bytes retired; production/rollback/oldsoak/Vault/
Profile untouched. Existing one V1.6 checkout reused; no new worktree/handoff.
Remaining whole V1.6 status staysREVIEW_REQUIRED, not DONE or production E2E PASS.


## CEO page factory exact-target prerequisite re-review — 2026-10-27

**Verdict: PAGE_FACTORY_SOURCE_REVIEW_PASS (isolated, offline prerequisite only).**
This is **NOT** a V1.6 actor/concurrent-browser/business-release PASS
and **NOT** a change to the already Owner-authorized 04075bc
reviewed-only installation candidate. Production remains
`AUTHORIZED_WAIT_NORMAL_EXIT / NOT_DEPLOYED` as executor reported;
no production or Chrome operation was performed by CEO.

Independently verified remote branch
`codex/v1-6-independent-scheduling` at
`34d0fd4f6514036065c0222fbe31d5548b3c8e10`.
Diff relative to reviewed CEO
`ee49203dbae39e79eca1f1c90164f643ba2fe03c`:
four commits—documentation-only install freeze
`1b19390298c6151e08d1e513a2a153ddcae2c1cf`;
page-source
`49677b7e658034f687fa0ed73c5bb5ff6bfadf3d`;
blank-URL compatibility follow-up
`f49d78526f6c30cc57b710f466883792ff574e0d`;
report/evidence head `34d0fd4...`.
Only application source delta is
`src/research/cdp_pages.py` (+19/-5);
corresponding fixture/tests are
`tests/research/background_targets.py`,
`tests/research/test_cdp_pages.py`, and
`tests/research/test_icnet.py`.
Independent diff `04075bc..1b19390`
contains documentation/evidence only, confirming
the installation candidate's `src/` remains the
earlier independently reviewed source.

### Reviewed page-factory contract

- Validates owner *before* creation. Creates a
  per-invocation unpredictable `about:blank#INSO_CREATE:<uuid>`
  URL; `expect_event("page")` selects only that event,
  not the first unrelated page. Receives
  `Target.createTarget` targetId and separately
  checks the Page-linked CDP
  `Target.getTargetInfo` targetId against it
  before marking ownership or returning Page.
- On successful proof, preserves the existing
  `window.name` page-owner marker and restores
  the exact `about:blank` URL with
  `history.replaceState` for old keepalive and
  initial-navigation guards; no owner/page
  application business rule or Chrome profile
  lifetime changed.
- On acquisition/proof/marker failure, attempts
  native `Target.closeTarget` using only the
  exact target ID returned by this invocation,
  never by enumerating or closing another
  task's matched Page. This is an important
  safety improvement over a first-page event
  without native identity proof. Note that
  browser protocol teardown can itself fail:
  success of close is **not guaranteed**,
  and a teardown exception could mask an
  earlier failure. Before enabling independent
  actors, add an offline targeted fault test
  for closeTarget or detach failure and ensure
  resource-failure reporting does not authorize
  subsequent unsafe page reuse. Do not
  broaden this into another rewrite of the
  already reviewed installation candidate.
- Source tests inspect foreign/spoofed events,
  per-create uniqueness, native mismatched
  target, proof timeout, invalid owner,
  exact blank restoration and window.name
  retention. Existing adapter tests were
  updated to preserve previous expectations.
  The original pre-fix fragment regression
  against exact `about:blank` has been
  fixed in the second source commit.
- Submitted execution logs report
  2806 PASS / 1 SKIP (110.02s) on final
  application source, plus 12 focused
  positive checks (0.57s), Ruff and diff
  checks PASS. Prior dependency/fixture
  failures and one symlink capability skip
  are disclosed, not passed off as live tests.
  CEO read GitHub code/tests/evidence, did
  not independently execute Windows pytest.
- Playwright supports a browser-context
  page event and Page-linked CDP session,
  and CDP supports creation/target-info
  identity checks. **However** these tests
  use simulated protocol objects only; they
  cannot prove real Chrome initial URL
  event timing, URL reset success, owner
  persistence after subsequent navigation
  or multi-client contention on protected
  Chrome. A dedicated future bounded
  read-only Chrome integration test is
  required before deployment as true
  page-level parallelism; no live/browser
  experiment was performed here.

### Release and outstanding tasks

**PASS is scoped strictly to the offline page
factory identity prerequisite.** It does not
approve installation of
`49677b7...` / `f49d785...`, which remain
separate from approved 04075bc build.
Missing: bounded independent sync actors,
per-source order leases, same-site auth
pacing/locking, callback/thread isolation,
real navigation overlap, and true
actor cancellation/shutdown. Those are
`NOT_IMPLEMENTED`/`NOT_VERIFIED`.

Owner authorized the normal stop/backup/build/
install/idle/resume window for the earlier
reviewed-only 04075bc source. Executor reported
current old EXE/PIDs still live because safe
GUI exit could not be automated. Do not
force-kill the protected browser, guess
unlabelled Tk controls or bypass normal
purchase/SMTP draining. Continue installation
only after independently verified normal
main/observer exit and current-ledger backup;
there is **no need to repeat the already
given Owner installation authorization**.
Never restore a pre-live database or replay
SENT/UNKNOWN. Real TP cycles, current SMTP
status, naturally eligible purchase/Sheet
success, updated UI, long-term stability
and gameplay remain unverified.

**Final:** `PAGE_FACTORY_OFFLINE_PASS`,
`PARALLEL_ACTORS_NOT_IMPLEMENTED`,
`LIVE_BROWSER_OVERLAP_NOT_VERIFIED`,
`APPROVED_04075BC_INSTALL_STILL_SEPARATE`,
`V16_OVERALL_REVIEW_REQUIRED`.

## C prerequisite follow-up to CEO83bfdfd (not deployed)

CEO requested closeTarget/detach failure evidence before actors can be enabled.
Canonical page factory now reports typedCDP_PAGE_CLEANUP_UNCONFIRMED with original
acquisition failure as cause, records only cleanup exception class names, and
latches this attached browser client unusable. Subsequent page acquisition on
that client is refused before issuing any protocol call. Both root-session and
page-linked proof-session teardown faults covered; a detach failure on success
never returns a usable page and attempts only its exact native target cleanup.
CloseTarget must return positive success; false/missing confirmation is a fault.
No global Chrome close/reset, no arbitrary page cleanup or fallback reuse.
Tests cover close-only/detach-only/both, proof-session detach with/without original
mismatch, success-path detach, false/missing native confirmation and denied reuse.
**664targetedPASS6.46s**, ownership20PASS0.58s, scopedRuff/diffPASS. Prior full2806
applies to f49d785 application, not mislabeled as full of this new follow-up.
Future actor coordinator still must promote this client latch/fault across all
resource admissions even when an adapter wraps errors; that integration is not
implemented by this prerequisite. No new true parallelism/real-browser PASS.
Installed04075bc frozen program was not rebuilt or changed by this follow-up.

## Current continuation — reviewed installation and native prerequisite (2026-10-27)

Owner install-window authorization and normal old-program exit supersede earlier
WAIT_NORMAL_EXIT/NOT_DEPLOYED notes. Application04075bc installed, EXE696E732B...
verified2875assets; canonical build, backup-copy compatibility, frozen/idle checks
PASS. Fresh backup/rollback retained, runtime/config/vault/V14/V15 unchanged.
Actual main85528/observer85924 restored three-module business; real module cycles
and ledger evidence in reviewed-* JSON and current V16_RELEASE_REPORT section.
TP second cycle454.210s late despite900s policy: NOT full independent cadencePASS.
No new verified purchase/Googlewrite; historical4TP/6TP-SENT preserved.
Google runtime alerts09:57old/14:56new are distinct per-cycle commands, not replay;
new alert follows5busy reads. No exact DOM root cause or final delivery proof.

Owner separately granted safe-stop/GUI-retained/at most2own CDP tabs window and
confirmed stop. Same existing9222, independent thread-local sync clients; no new
Chrome/profile, no credentials/Google/INSO/write/testmail. Native exacttarget,
initialowner, own cleanup and preservation PASS. Real same-MPNHQEW navigation
intervals overlap0.125/0.532s; postnavigationowner not verified due navigation/load
errors. No claim of full actors/source extraction/sameorder queue acceptance.
No new EXE installation from this unreviewed source. Restoration via GUI pending
Owner Start confirmation because screenshot FrameArrived timeout/unlabelled Tk.

30min finite exactprocess sampling complete, no new monitor:0.28961%hostCPU,
RSS114.96→137.50MiB, Private86.67→107.32MiB, handlespeak5646→1004→1138.
Memoryupperbound/semaphore attribution/games/longrun remainNOT_VERIFIED.
Unified checklist above updated, not a replacement business state system.
Overall **REVIEW_REQUIRED / PAGE_PARALLELISM_NOT_READY**; independent cleanup
commit67be3f748f80daff0dfca2f3d64998ce41f53c16 remains uninstalled.

Additional bounded native IC.net pair: HTTP200, navigationoverlap0.204s, native
IDs/blankowners/cleanup PASS. Postnavigationowner evaluation contextdestroyed;
unknown actual marker survival, no challenge bypass or retry of production work.
Existing1page retained. Combined native evidence closes only creation/cleanup
capability, not full ownership across navigation or moduleactor integration.
Current finite collector exited0, owned test scratch retired; production GUI
retained, restoration via original Start awaiting Owner confirmation.

Final full offline regression on67be3f7 application: **2815PASS/1SKIP109.85s**;
no source change during/after run, docs/evidence only. No live SMTP/write tests.


## CEO independent V1.6 continuation review — 2026-10-27

**Review verdict: PARTIAL_PASS / CHANGES_REQUESTED_FOR_OUTSTANDING_V1.6.**
Accept evidence of the specifically reviewed `04075bc` installation,
real module-cycle observability, historic receipt preservation and
the narrow `67be3f7` known-target cleanup-failure source increment.
Do **not** issue overall V1.6 PASS: 900-second timely TP scheduling
**FAIL** (454.210s late); complete safe multi-actor browser execution,
post-navigation ownership and external purchase/Sheet E2E remain open.
No live program, GUI, browser, Chrome profile, SMTP, SQLite, config or
deployment was touched by this independent GitHub review.

**Review references and exact diff.** Prior CEO review
`83bfdfd2ae6fcc63316c802341ffa28f4b894f77`
→ submitted branch HEAD
`40b16ae3fff53dae63e44ccd610f2615edea88d8`
(two commits: `67be3f748f80daff0dfca2f3d64998ce41f53c16`
source/tests and `40b16ae...` documentary evidence).
Only changed application module
`src/research/cdp_pages.py`, with tests in existing
`tests/research/test_cdp_pages.py`; no production
pricing, source identity, purchase, SMTP, database,
scheduler or config policy changed by this incremental source fix.
Separate frozen reviewed install checkout
`1b19390298c6151e08d1e513a2a153ddcae2c1cf`
still differs from approved source
`04075bc884c9c2927e677edcbddcb43419833aef`
by documents/evidence only, not `src/`.
All later page-source code is NOT in the approved installed EXE.

### 1. Installed reviewed executable: EVIDENCE_ACCEPTED

Executor-published installation and frozen-code evidence records
original PID74176/observer84608 normal exit, an Owner-authorized
drain/build/install/idle/resume window, release-locked dependencies,
Tcl8.6.15, verified 2875 assets, matching application freeze,
and installed EXE SHA256
`696E732B3B697EBDAE6267118959D11C8C87BE4A2B76DAFD7F17C2EA7127189A`.
Fresh rollback program and compatible ledger/config/vault backups
are documented; migration on copy unchanged, production migration
not requested, runtime junction plus V1.4/V1.5 rollback retained.
Frozen installed-code checks show scoped P1 restoration and per-module
cycle logging, with old page factory rather than unreviewed patch.
GitHub review independently checked the evidence and source commit
separation; it did **not** recompute local EXE bytes or inspect
protected local copies.

Live ledger snapshot reports `integrity=ok`, 108 historical
commands immutable, full rows for 139 prior SENT and 4 historical
TP tasks unchanged (including 6 historical TP-SENT), total SENT
now 140 with exactly one new PURCHASE_EXCEPTION recipient.
No PENDING, SENDING or UNKNOWN in the submitted snapshot;
purchase SAVED remains 23. This is durable receipt preservation
and naturally occurring SMTP transport acceptance, not confirmed
mailbox delivery or an externally successful new purchase.
No new procurement SAVED/Google write-readback was independently
substantiated.

### 2. Real module scheduling: TP deadline FAIL

Accepted structured business receipts show:
- TP cycle1 completed 14:57:05.219 +08 with
  next planned at 15:12:05.219.
- TP cycle2 began 15:19:39.429; actual start
  occurred 1354.210s after previous completion,
  **454.210s later** than the configured 900s.
- Between those times quotation used the
  serialized browser actor 15:11:49.311–15:19:39.320.
  Independent monotonically computed due dates,
  real TP begin/end and the corrected nested inquiry
  cycle identity are observed; no evidence of
  independent **timely actor** execution.
- Inquiry next observed begin ~900.010s after its
  completion; quotation deferred-to-retry
  ~900.020s. These good individual periods do not
  erase the TP starvation/deadline problem.
  Nothing proves all modules will run within their
  deadlines under sustained contention.

Disposition: `TP_REAL_CYCLE_RECEIPTS_PASS`,
`TP_900S_TIMELY_EXECUTION_FAIL`. Require
bounded fair resource admission/safe yield
or separate read-only browser actor isolation
without weakening protected INSO/Google/order
claims, 120s completed-row cooldown or
SENT/UNKNOWN guards. Test a real long quotation
while TP becomes due; record delay and recovery.
Do not reduce safety or force a transaction
merely to obtain a good timing result.

### 3. Uninstalled page-factory cleanup fault fix:
KNOWN_TARGET_SOURCE_SCOPE_PASS, actor safety open

Reviewed `67be3f7` source/tests: a typed
`CDP_PAGE_CLEANUP_UNCONFIRMED` reports
closeTarget confirmation errors and root/proof
CDP-session detach errors. It preserves the
original acquisition failure as cause,
carries bounded exception class names,
attempts to close only the exact known created
target, marks that Playwright Browser wrapper
unusable on failed cleanup, and blocks subsequent
page acquisition on **that wrapper**. Tests cover
close-only/detach-only/both, success-path detach,
proof-session teardown and missing/false native
close confirmation. Executor-reported
2815 PASS / 1 SKIP (109.85s), 664 targeted PASS,
20 ownership PASS, Ruff/diff PASS; review
inspected actual code and tests, not rerun
Windows test suite.

Two explicitly **unresolved safety boundaries**
remain before actor integration:
1. If `Target.createTarget` executed in Chrome
   but the send/response fails **before targetId
   is returned**, current code cannot know the
   target to close. Because `target_id` is
   still None, a successful session detach
   allows another acquisition on that wrapper:
   an ambiguous target creation is not latched
   as uncertain browser state. Test this precise
   failure model and fail closed for further
   admissions until ownership is reconciled.
   Never close a guessed/human tab.
2. The latch is attached to an individual
   Python Browser wrapper; a newly connected
   actor/client on the same Chrome can obtain
   a different wrapper. No shared coordinator
   currently promotes the cleanup fault
   through adapters to all affected admissions.
   `CDP_PAGE_CLEANUP_UNCONFIRMED` is not in
   the current launcher global-fault reason
   allowlist, and source adapters can wrap
   exceptions. Require explicit propagation
   before enabling multi-actor production;
   do not treat a local latch as a system-wide
   stop.

These forward-looking blockers do **not**
retroactively invalidate the narrow already
tested known-target cleanup fix, but preclude
a safe parallel-actor release.

### 4. Genuine native CDP prerequisite:
creation and navigation overlap only

Executor's bounded Owner-authorized tests use
the original9222 Chrome, at most two own tabs,
thread-local sync Playwright clients and no
new profile/INSO/Google/business write.
Published HQEW pairs overlap 0.125s and
0.532s navigation intervals; IC.net pair
overlaps 0.204s. Each reports HTTP200, exact
native initial target and blank owner and
owner-only cleanup with pre-existing one
human page preserved. These are meaningful
real CDP navigation overlap observations,
not just callback/sleep overlap.

However, after navigation the ownership
evaluation failed (timeout or destroyed
execution context). Neither marker survival
nor the required safe post-navigation lifecycle
is proven. Real module actors, source extraction,
shared source/order exclusion, site auth/pacing,
fault admission and resource-limited scheduling
remain NOT_IMPLEMENTED / NOT_VERIFIED.
The current experiment was authorized only
with business safely stopped; it does not
authorize deploying the new source as a
concurrent production feature.

### 5. Current errors, mail and resources

Review of `reviewed-google-alerts.json`
shows two different source-run cycle commands
(09:57 old / 14:56 new), each attempt1 and
same configured recipient, not historical
resend. New quotation cycle has
5 GOOGLE_WEB_READ_BUSY observations and
eventual deferral; later cycle completed.
This supports transient/recoverable busy,
**not** a permanent whole-Sheets outage.
Exact underlying DOM/lock cause remains
UNKNOWN. Future wording/cross-cycle
notification noise is an optional separate
review, not permission to suppress real
faults or bypass state protection.

Finite 1800.063s/31sample same-PID app
counter window: average host CPU0.289605%
(16 logical CPUs), RSS114.96→137.50MiB
(+22.54MiB), private86.67→107.32MiB
(+20.65MiB); handles peak5646 and fall
to1004 before ending1138; GDI136–138
and USER258. This **supports transient
handle release**, but a 30min rising-memory
window does not establish a stable memory
plateau or prove a permanent leak. Cause,
semaphore allocation attribution, continuous
multi-cycle upper bound, Chrome/GPU and
gaming FPS remain NOT_VERIFIED. Old V1.5
six-page 9f soak is NOT a V1.6 certificate.
No new monitor or speculative repair required
by this review.

### Disposition / next bounded execution scope

- **Accept** reviewed 04075bc installation evidence,
  P1 in-live cycle attribution, current ledger
  preservation, source-only 67be3f7 known-target
  cleanup remediation and real dual-client
  initial navigation/cleanup observations.
- **CHANGES_REQUESTED for overall completion**
  because TP timely dispatch FAIL, genuine actor
  coordination + post-navigation ownership not
  verified, ambiguous create-target outcome and
  cross-client fail-closed propagation remain.
  No production source hotpatch is authorized.
- **Current operational status:** per executor,
  Owner safely stopped business but kept GUI
  open for isolated CDP verification; original
  Start action was requested but **resume
  confirmation is pending**. Do not label
  current business RUNNING without new evidence.
  Do not use inaccessible Tk labels as
  authorization to guess controls; do not
  force-kill Chrome or create a new profile.
  Owner has already authorized existing
  business, but the review cannot assert it
  resumed.
- Required next work: on an isolated development
  branch, prove post-navigation ownership
  using verified native target ID (with safe
  execution-context lifecycle), globalized
  fail-closed admission for uncertain creations
  and cleanup errors, per-source order identity
  leases and paced website login; then bounded
  fair scheduling with TP deadline instrumentation.
  Keep current reviewed EXE separate until new
  source is independently reviewed and installed.
- Retain open: naturally eligible verified
  purchase/quotation Google writes, external
  readback, TP fresh delivery, SMTP delivered
  evidence, V1.6 live new EXE GUI/tray/DPI/
  restart and long-term/game performance.

**Final status:** `REVIEWED_04075BC_INSTALL_EVIDENCE_ACCEPTED`,
`67BE_KNOWN_TARGET_CLEANUP_SOURCE_PASS_ONLY`,
`TP_TIMELY_START_FAIL`,
`CDP_PAGE_OWNER_AFTER_NAV_NOT_VERIFIED`,
`MULTI_ACTOR_NOT_IMPLEMENTED`,
`V16_OVERALL_REVIEW_REQUIRED`.

## Execution after CEO59f0628 — native identity and shared fail-closed admission

Remote59f0628529ca830bc4dbdafc596e164db863516e fetched and fast-forwarded;
no prior P1/installed04075bc redo, no production replacement. Reused canonical
research.cdp_pages/shared_playwright_factory, Research composition, backend
source-query gate, WorkflowRuntime.abort_module_resource and existing teardown.
No separate browser manager/scheduler/outbox/DB/dependency or new Profile.

Minimum delta (isolated source only):
- Attempted Target.createTarget with lost/missing/invalid native response is
  CDP_PAGE_CREATION_UNCONFIRMED even if Chrome created a page. No guessing or
  enumeration-close; latch resource uncertainty, preserve orphan/foreign pages.
- Inject one PageResourceAdmission through backend and canonical Research factory,
  including fallback clients, same guard across all bound wrappers. Reconnect or
  rebind cannot clear it; inconsistent guard binding invalidates both. Metadata
  only, thread-safe; exception objects/Playwright objects never shared via guard.
- Source-query before/finally gate defeats translated SOURCE_UNAVAILABLE results;
  module before/finally gate defeats softened completion. New faults abort all
  runtime resource admissions, become GLOBAL_STOP, retain exact reason and are
  not attributed to last historic order. No blind retry/website deferral.
- On uncertainty, old close/park sweeps are refused before touching pages;
  release detaches only its client. Known-target factory failure still closes
  only exact created target, preserving primary cause and cleanup fault details.
- Explicit native_page_owner for factory-created read-only actor pages proves
  Page-linked Target.getTargetInfo against original target ID, without evaluating
  a changing document. Existing page_owner marker checks intentionally unchanged:
  Google/INSO marker loss must still quarantine the write surface. New API is
  NOT a bypass for write auth/document/gid/status/settlement gates.

Owner confirmed prior Start action (actual name开始运行). Independent new cycles
were observed15:59:46 inquiry /16:02:35 quotation /16:03:20 TP, TPcompleted16:03:37,
inquirycompleted16:12:24. Latest readonly ledger check before this experiment:
141SENT total, old139SENT/108commands/4TP fullrows unchanged,0pending/sending/unknown.
Two postinstall runtime alerts, not TP/price mail or historical replay. Existing
Googlebusy behavior persists; no notification suppression or identity relaxation.
Owner then explicitly authorized and confirmed a NEW safe-stop window, GUIkept.

Native verification under this window: same9222, no newChrome/Profile/context,
max2own background tabs, independent thread-local sync clients sharing admission.
HQEW andICnet pairs: eachHTTP200, exacttarget/owner beforeANDafter navigationPASS,
actual navigationoverlap0.109s /0.219s, precise closeTarget positive confirmations,
original1page preserved/final1page, every own target absent. No JS-based ownership
assumption, rawDOM/account/screenshot/credentials retrieval/login/Google/INSO/
write/purchase/testSMTP. Native evidence predates only stronger rebind/terminal/
teardown/attribution hardening; navigation proof itself unchanged. Final source
must still pass offline regression; not falsely exact-hash live deployment proof.

Regression first found a real legacy safety compatibility issue: replacing
page_owner by native identity would close a marker-cleared Google review page.
Fixed by EXPLICIT independent native API; old marker-quarantine regression nowPASS.
Do not change that test into an acceptance of unsafe ownership fallback.
296targetedPASS12.00s; legacy/source combined389PASS14.22s; newedge71PASS10.37s;
final source-safety/teardown309PASS13.04s. Intermediate full2834/2836PASS each1SKIP
are not mislabeled final latest-source full; final full result recorded below.

Current boundary: native ownership prerequisite positive live proof and shared
admission safety source increment only. No actual module actor pool, per-order
arbitration/siteauth pacing or timelyTP scheduling delivered by this increment.
Guard lifetime is one runtime; no claim of automatic cross-process orphan
reconciliation. No failed-resource reset API or auto-reuse. Human-preserved page
handoff across disconnected clients remains a separate required actor contract.
Current production EXE04075bc unchanged, program installation not authorized here.
Owner asked to click开始运行 after own pages closed because Windowsscreenshot
FrameArrived still timesout/unlabelled controls; no guessed click or process kill.

Final full offline regression of this application increment: **2840PASS/1SKIP113.03s**, scopedRuff/diffPASS. No source change after this run. InstalledEXE not rebuilt or replaced.

Source safety increment committed20fda49c4573a0c59917d8ddf009655d220a41a2.
Evidence/report follow-up records current proof and qualifications; no new production installation.


## CEO independent page-admission isolation re-review — 2026-10-27

**Verdict: ISOLATED_SOURCE_SAFETY_REVIEW_PASS /
NATIVE_PAGE_OWNER_PREREQUISITE_PASS /
NOT_DEPLOYED / V16_OVERALL_REVIEW_REQUIRED.**
This is a scoped independent review of the isolated page
creation/cleanup/admission and native read-only owner
safety increment, NOT a review reopening previously
accepted P1 or the installed `04075bc` artifact.
No production/Chrome/UI/SMTP/Sheets/SQLite configuration
or process action was performed by this reviewer.

**Verified provenance.** Prior CEO
`59f0628529ca830bc4dbdafc596e164db863516e`
→ application source commit
`20fda49c4573a0c59917d8ddf009655d220a41a2`
→ evidence HEAD
`12e77749ec93e8c5c7a8845a8614e3ee4811a59f`.
Remote branch points exactly to evidence HEAD and
comparison shows one isolated source/test commit
plus one documentation/evidence commit. New source
delta is limited to `src/research/cdp_pages.py`,
`src/research/runtime.py`,
`src/launcher/backend.py`,
`src/launcher/browser_bootstrap.py`, with matching
tests and task notes. Evidence head changes reports,
design and allowlisted `page-admission-*` JSON,
not application source. Reviewer fetched and
inspected actual source, changed tests, structured
proof and GitHub diff, but did not independently run
the Windows suite or replay protected Chrome.

### Source findings — PASS for submitted prerequisite

1. `Target.createTarget` sets
   `creation_attempted` before the protocol send.
   A thrown/lost, absent or unusable returned target ID
   becomes typed `CDP_PAGE_CREATION_UNCONFIRMED`.
   No arbitrary tab is guessed closed; wrapper and
   the bound PageResourceAdmission latch failure.
   Other bound wrappers/reconnect paths subsequently
   fail `require_open`. When native target is
   positively known and cleanup fails, typed
   `CDP_PAGE_CLEANUP_UNCONFIRMED` remains fail-closed.
2. A single thread-safe `PageResourceAdmission`
   is created by ProductionBackend and passed through
   canonical Research composition,
   `shared_playwright_factory`, reuse and private
   fallback attachment, browser reacquisition and
   the source/module before/finally gates.
   Conflicting rebind invalidates both admissions;
   uncertain state is not reset on reconnect.
   Metadata only (exception classes/type) is
   shared, not Playwright/exception instances.
   `_run_independent_job_scoped` and
   `_runtime_error` propagate typed faults into
   resource abort / GLOBAL_STOP rather than website
   retries or attaching the fault to an unrelated
   historic inquiry.
3. Under page uncertainty, source cleanup/park
   boundaries refuse generic browser-page sweep
   before enumerating/closing pages.
   `_release_idle_browser` detaches the
   attachment only. Legacy write surface
   `page_owner` and its marker-loss quarantine
   remain in place; no native target proof can
   itself authorize Google/INSO writes.
4. New explicit `native_page_owner` verifies a
   factory-issued original target lease through
   Page-linked `Target.getTargetInfo` on each
   call without document JavaScript, allowing
   read-only identity checks through document
   navigation/context changes. Target mismatch
   and CDP proof session teardown failures
   fail closed on a bound client. It is explicitly
   **not** a substitute for existing write-authority
   markers or business idempotency.

### Evidence accepted, bounded correctly

- Submitted final unchanged source
  `20fda49c...` reports full offline
  `2840 PASS / 1 SKIP` in113.03s,
  final targeted `309 PASS` in13.04s,
  Ruff/diff PASS. Existing earlier full
  run identified a marker-quarantine regression;
  test/source correction restored the old
  marker safety rule before final full PASS.
- Native Owner-authorized two-client/two-own-page
  read-only tests at existing9222 report
  HQEW overlapping navigation by0.109s and
  IC.net by0.219s, HTTP200, native ID and
  owner proof both **before and after**
  navigation, exact owned target closure and
  original one page preserved. This resolves
  the earlier **narrow postnavigation native
  identity proof gap**; it is NOT proof of
  business source parsing, shared runtime
  fault handoff, three actual module actors,
  per-order exclusions, authentication pacing,
  900s timely TP or production parallelism.
- Native probe source hash differs from the
  final hardened source because live proof
  preceded final rebind/terminal/teardown
  changes; `native_page_owner` implementation
  was reported unchanged. Final full offline
  regression complements but does not
  replace a complete final-source live test.
  No page-source increment has been installed.
- Older installed reviewed executable remains
  `04075bc884c9c2927e677edcbddcb43419833aef`
  per the submitted report. Actual subsequent
  business cycles around15:59 inquiry,
  16:02 quotation,16:03 TP were observed
  following an Owner-confirmed **prior** Start.
  Current read-only ledger evidence reports
  108 historical immutable commands,139
  historical SENT,4 TP task full rows unchanged,
  new current141 SENT with no
  PENDING/SENDING/UNKNOWN (two new
  runtime fault notices, not fresh TP or
  quote success). This latest browser test
  took place after **another safe stop**;
  Owner confirmation of *resuming after
  this newest window* was still pending at
  the evidence timestamp. Do not assert
  currently RUNNING merely from earlier
  post-resume cycles.

### Explicit remaining actor-integration safety contracts

These do **not** invalidate the scoped source
PASS but MUST precede an actual actor rollout:

- Every future actor/fallback and callback
  must be bound to the *same* runtime
  admission **before** browser operations.
  Reject unbound work, prevent races between
  admission checks and foreign-client
  invalidation, and propagate global fault
  stop across actor ownership boundaries.
  The current guard is runtime-scoped,
  not process-global or cross-process
  orphan recovery.
- The explicit read-only `native_page_owner`
  currently throws typed
  `CDP_PAGE_OWNERSHIP_UNCONFIRMED`
  for a missing native lease without access
  to any bound browser/admission to invalidate.
  Actor orchestration must treat this as a
  hard failure, never swallow it into a
  normal unavailable answer or proceed with
  page navigation or a business result.
  Continue to distinguish read-only native
  identity from legacy writable marker
  identity. Test this path in an integrated
  actor terminal and teardown scenario.
- Build and verify existing WorkflowRuntime's
  **canonical source-row order lease** across
  inquiry, quotation and TP, site authentication
  pacing and protected INSO/Google exclusive
  operations. Resource fairness/preemption
  must address the previously demonstrated TP
  start 454.210s late. Independent monotonic
  timers are not sufficient proof of timely
  execution. Include actual thread/target/
  request time overlap and conflicting-order
  serial timelines with bounded resources.
- No code or mock tests here implement a
  bounded multi-actor production worker,
  durable cross-module source lease,
  independent page-query business result
  handoff, resource fair scheduler or final
  business E2E. Those stay NOT_IMPLEMENTED/
  NOT_VERIFIED; do not deploy a partial
  read-only page prerequisite as complete
  parallel execution.
- Open operational acceptance remains:
  naturally eligible purchase + Google
  Sheet write/readback, eligible TP mail,
  current SMTP unknown/restart behavior,
  100/150% system DPI, actual GUI/tray,
  V1.6 sustained memory/Chrome/game impact.
  The earlier old-9f V1.5 soak is not a
  V1.6 certificate.

**Disposition:** Accept current isolated
source-safety increment without reopening
P1 or reinstalling `04075bc`.
Continue independent development of
source-row order leases and actor integration
in separate reviewable commits; do not
deploy, restart or assert production
completion from this review. Overall
`REVIEW_REQUIRED` persists.


## 2026-10-27 continuation — bounded original-source order leases (not deployed)

CEO98ffd2ea0688c37b67811f02593b29ee3ef0a27e accepts the prior20fda49
shared CDP admission/native ownership increment only. Installed04075bc remains
unchanged; Owner restored business and new17:01–17:04 cycles confirm running.

Reuse audit: WorkflowRuntime already owns the module RLock/resource lifecycle;
WorksheetIdentity supplies canonical spreadsheet+worksheet identity. Existing
V12/TP stores remain the durable business/receipt authority. Their separate task
IDs cannot alone exclude simultaneous work on the same original row. Extend
that runtime with bounded ephemeral source-row admission; no second ledger,
scheduler, dependency or business identity. Capacity bounds resource requests,
not business order throughput. Default admission is closed, not wired into
production dispatch. Rejected admissions consume no persistent work.

Same original spreadsheet/sheet/physical row queues FIFO across requirement
tokens; differing snapshot/MPN does not bypass that lock. Exact granted lease
and admitting scheduler thread required for release; forged/copy/foreign/double
release fails closed. Stop cancels undispatched requests only; active leases
remain until known completion/drain. Shared resource abort closes admission;
backend treats typed ownership faults as GLOBAL_STOP, never a historic-order
failure. Existing transaction/identity/amount/SENT/UNKNOWN gates stay mandatory.

Targeted64PASS10.66s; final exact application-source full2861PASS/1SKIP115.96s;
scoped Ruff and git diff checks PASS. Tests cover FIFO, independent sources,
finite admission, cancellation, stop/drain, foreign/forged release, reconfigure
refusal and backend global fault attribution. These are isolated resource tests,
NOT integrated module actor/real browser business concurrency acceptance.

| Unified remaining item | Current status |
| --- | --- |
| Previous P1 / reviewed04075bc installation | PASS; not reworked/reinstalled |
| Native read-only target ownership after navigation | PASS scoped live prerequisite |
| Shared CDP fault admission | PASS scoped CEO98ffd2e source review |
| Original-source FIFO resource lease component | PASS offline; REVIEW_REQUIRED |
| Actor dispatch using these leases + existing durable claims | NOT_VERIFIED / not implemented |
| Site auth/pacing and protected Google/INSO actor integration | NOT_VERIFIED / not implemented |
| Fair module result handoff / TP timely900s actual start | FAIL prior454.210s delay; not fixed |
| Actual business-page overlap and same-order serial timeline | NOT_VERIFIED |
| Naturally eligible new purchase, Google write/readback, TP mail | NOT_VERIFIED; not manufactured |
| Sustained V1.6 memory,100/150% systemDPI, Chrome/game impact | NOT_VERIFIED |
| Deployment of new concurrency source | DEFERRED; current production preserved |

No replacement, browser experiment, production DB/config mutation or test mail
performed by this resource component. Overall REVIEW_REQUIRED persists.


## CEO independent original-source row lease review — 2026-10-27

**Decision: CHANGES_REQUESTED for one source-proven abort/rearm lifecycle bypass;
FIFO/exact lease semantics and the reuse-first architectural direction are
accepted as isolated prerequisites, NOT a business-actor or product PASS.**

**Scope/provenance:** reviewed source and evidence commit
`0e0495a4dd27bca50466266d7a14ebe29ec2c4a0`, exact parent
`98ffd2ea0688c37b67811f02593b29ee3ef0a27e`. GitHub branch
`codex/v1-6-independent-scheduling` pointed to this exact head.
One commit touches existing `src/workflow/service.py`, narrow launcher
fault propagation, tests, report/task, design and
`docs/evidence/v16/order-resource-regression.json`; no new ledger, business
adapter, dependencies, or production runtime changes. Submitted
2861PASS/1SKIP115.96s, targeted64PASS10.66s, Ruff and diff checks PASS
are executor-run evidence; reviewer examined source and test logic without
running Windows tests or touching production.

### Verified source behavior

- Default order admission is CLOSED. Optional
  `configure_order_leases(capacity)` establishes a finite total
  outstanding-request budget. Canonical `WorksheetIdentity`
  (spreadsheet, worksheet) plus physical row index is the
  **in-memory resource exclusion key**; snapshot/model variation
  cannot bypass a matching source-row lock. Source identity must
  still be freshly verified at the existing domain boundary
  immediately before external effects; physical position alone
  does not establish permanent business identity.
- Per-key FIFO is enforced by queue head. Duplicate queued
  token admission is idempotent; once active it is refused.
  Distinct source keys can hold concurrent leases. The granted
  immutable lease object's **identity**, not merely matching
  fields, together with the admitting scheduler thread is
  checked on release; copied/foreign/double releases fail with
  `OrderResourceOwnershipError`. Active work cannot be canceled
  through a waiting-request cancellation path.
- `close_order_admissions` cancels only waiting, not active,
  leases. Successful active release remains possible after
  ordinary Stop. `abort_module_resource` uses the existing
  reentrant module lock and closes admission. Backend maps
  typed ownership faults found in exception chains to
  resource abort/GLOBAL_STOP and avoids attributing the
  shared failure to the most recent historic order.
  This was exercised with isolated tests; no actual
  cross-thread actor completion/error handoff exists yet.

### Required correction before integrating an actor coordinator

**P1 integration-blocking, source-provable:** an aborted runtime can
silently clear the abort latch using existing
`WorkflowRuntime.configure_modules`. Minimal reproduction from
current code (all on the original owning thread):

1. `runtime.configure_modules({"inquiry": 900})`, then
   `runtime.configure_order_leases(2)`.
2. `runtime.claim_due_module()`; call
   `runtime.abort_module_resource()`. This marks the shared
   resource failed and closes order admissions.
3. With no active order requests (or after draining and releasing
   them), `runtime.configure_modules({"inquiry": 900})`
   passes its only running/request guards and sets
   `_module_resource_failed = False`.
4. `runtime.configure_order_leases(2)` now succeeds and
   reopens order admission, allowing new
   `request_order_lease(...)` even though no explicit browser
   resource reconciliation/new-runtime authorization occurred.

A plain `close_order_admissions` followed by a completed drain
also allows `configure_order_leases` to rearm admission.
Whether ordinary stopping permits an intentional new lifecycle
must be explicit; a fatal resource abort must never be reset by
ordinary reconfiguration.

**Required minimal fix/test:** define one-way terminal abort
for this `WorkflowRuntime` instance or an explicitly guarded
fresh-runtime/new-generation transition. In particular, module
interval reconfiguration must not clear a faulted order-admission
resource for the same unsafe generation. Preserve the ability
to drain/release already active leases. Add regression for
abort -> drain -> configure_modules -> configure_order_leases ->
attempted new claim, plus normal Stop -> drain -> attempted
implicit rearm. Do not rewrite the original scheduler or invent
a second ledger.

**Additional integration risks to close in follow-up (not a
failure of the current isolated FIFO unit tests):**
- A *claimed* lease is considered active before worker dispatch.
  If Stop happens in that gap, it survives waiting cancellation;
  actor coordinator must either safely complete/drain it or
  release it on the admitting scheduler thread, otherwise it
  leaks a slot indefinitely. Add this exact interruption test
  during dispatch integration.
- Finite capacity counts both active and waiting requests.
  Two pending requests for one busy key can occupy the entire
  budget while a separate source key could otherwise use a
  free market slot. This is bounded and not incorrect-source
  behavior, but can create head-of-line delays and undermine
  the previously failed TP deadline. Scheduler needs a
  non-starving admission strategy and measurable due-time
  latency, not just a FIFO for each key.
- A typed release/claim ownership error raised on a worker
  is *not* automatically delivered to the current single
  Backend thread. Future actor results must carry terminal
  fault metadata across immutable ports, trigger
  GLOBAL_STOP and all bound PageResourceAdmission/resource
  gates, and never leave an active lease orphaned.
- `WorksheetIdentity + physical row` is a **resource key**,
  not stable durable business identity; row movement/
  deleted/reused sheets, different source snapshots, and
  Sheet IDs/row-index coordinate semantics must be
  reconciled by existing fresh identity and durable claims
  before any effect, not by trusting a mere lease.
  If module-source record keys differ, prove canonical
  equivalence in the Public Contract first.

### CEO MODULE_INDEX Public Contract decision

**Conditionally approve the proposed minimum integration direction,
without approving implementation or release.** Reuse existing
`workflow.WorkflowRuntime` for bounded, fair scheduling and
canonical source-row leases; Launcher remains composition owner,
Chrome/CDP lifecycle and protected INSO/Google write owner;
Research remains read-only owner of six canonical collectors and
result parsing/FX; GUI consumes immutable bounded progress DTOs,
and existing V12/TP/SMTP stores own durable claims/receipts.
The only new cross-module surface is versioned/typed immutable
module/cycle/source-key request/result/progress + fault/completion
messages, with explicit admission/teardown ownership. Do not
pass Backend closures or mutable/sync Playwright objects across
threads. Exactly bounded fixed-thread market-read clients may
use the same already-running9222 Chrome, each with its own
sync Playwright connection and target ID, sharing the existing
runtime PageResourceAdmission plus canonical source row lease
and site auth/pacing rules. Keep Google, INSO and external writes
on original exclusive owner thread with verified idempotency.
No unbounded queue, new daemon, Profile/Chrome clone or
parallel ledger.

**Timing contract:** do not block original scheduler waiting for
an entire Research batch. It must admit/cancel/complete individual
bounded requests, deliver immutable results asynchronously to
their correct module cycle and allow due TP to progress without
waiting for an unrelated long quotation query, subject to
declared site/auth/order mutual exclusions and 120s order
cooldown. Validate with a real long quotation and due TP,
actual parsed source intervals, order-source conflict timeline,
stop/timeout/UNKNOWN and preserved human pages. The observed
TP 454.210s lateness remains FAIL/open; no numeric guaranteed
zero delay is asserted.

**MODULE_INDEX governance:** CEO approves the intended *boundary*
as a staged Public Contract extension, not an already existing
contract implementation. Executable interfaces, authority/
payload safety, versioned canonical identities, bounded queue,
scheduling fairness and release evidence must be independently
reviewed before rollout. No repeat approval of pre-authorized
ordinary business is needed; a separate safe deployment window
remains necessary for new production source.

**Current production:** executor records Owner restored Start and
real inquiry17:01:44, quotation17:04:01, TP17:04:34–17:04:51
(+08), but currently installed executable remains the already
reviewed `04075bc`. The present source increment is not
installed and does not change running permissions or status.
No production intervention, browser experiments or monitoring
occurred in this CEO review.

**Disposition:** `ORDER_RESOURCE_FIFO_ISOLATED_TESTS_PASS`,
`ABORT_REARM_LIFECYCLE_CHANGES_REQUESTED`,
`MODULE_PUBLIC_CONTRACT_DIRECTION_CONDITIONALLY_APPROVED`,
`ACTOR_BUSINESS_PARALLELISM_NOT_IMPLEMENTED`,
`TP_TIMELY_DISPATCH_STILL_FAIL`,
`V16_OVERALL_REVIEW_REQUIRED`.


## Stage A — terminal lease lifecycle correction (2026-10-27)

CEO4c40ba4 / architecture3d77a67 followed. Minimum delta in existing
WorkflowRuntime: configure_modules refuses a faulted runtime and never resets
its fatal latch. Order admission close is terminal even before first configure;
configure_order_leases cannot reopen it after Stop/drain. An explicit new
WorkflowRuntime is required for a new safe lifecycle; construction alone does
not verify a browser or grant business authority. Exact active lease release
still works after close/abort; pending entries are canceled. Existing same-row
FIFO, capacity and foreign/forged/double-release protections remain unchanged.
No new scheduler/resource manager/ledger, no deployment or production changes.

Tests:65PASS11.15s targeted; full2864PASS/1SKIP112.70s; Ruff --no-cache and
git diff checks PASS. Added fatal abort/drain/reconfigure refusal, ordinary
Stop/drain implicit rearm refusal, fresh runtime separation and close-before-
configuration. Existing wrong-thread and copied-lease regressions retained.
Initial Ruff cached invocation hit write permission; no-cache succeeded without
ACL changes. Stage A source ready for independent Review. Stages B–F still open;
this does not implement business actors or correct TP454.210s delay.


## Stage B — Stop/dispatch boundary and bounded source fairness

Extends the same WorkflowRuntime, not a worker pool or business execution path.
Exact scheduler-owned lease has an atomic begin_order_dispatch transition under
existing lock. Stop-before-transition returns False: scheduler must cancel its
reserved lease without dispatch; Stop-after-transition drains acknowledged work.
Only scheduler owner can cancel a never-dispatched reservation. Committed work
cannot be canceled through reservation API; duplicate dispatch, copied/wrong-
thread handles are rejected. Future coordinator must acknowledge submit failure,
worker cancellation or completion before releasing; this API alone is not an
integrated queue/worker proof. No in-flight business result is fabricated.

Fairness delta: capacity bounds distinct original-source slots/active leases.
Same-row FIFO waiters no longer consume independent-row slots. Each source
queue is bounded by configured module count (at least1); overflow remains in
existing domain work, not dropped. Total transient requests <= capacity times
module count; active leases <= capacity. This is browser resource budgeting,
not an order-processing limit. Still no fair module deadline dispatch integration
or numeric TP timeliness claim; observed454.210s delay remains open.

Tests69PASS10.47s targeted; final full2868PASS/1SKIP112.36s; Ruff/diff PASS.
Exact Stop-before/after-dispatch, reserved rollback, active drain, duplicate,
foreign/copy dispatch and independent-row progress under busy-row waiters added.
No production DB/config/EXE/browser access by implementation or tests.

### Google fault notices — existing production log only, no browser experiment

Available sanitized logs2026-10-27 show retry exhaustion at09:57:23,14:56:49,
16:03:20,17:04:34 (+08). Each group has5google-open-sheet failures classified
QuotationInputBusy/GOOGLE_WEB_READ_BUSY. This proves failure before TSV download,
not that Google cannot open or that every site operation is down. Existing code
can raise busy for protected pooled entry, unsafe pending/dialog surface, or
>=3owned operation pages. Logs lack branch-specific detail; which condition
actually fired remains UNKNOWN. A manually openable Sheet does not clear these
settlement/ownership guards. Existing notices deduplicate by cycle, so repeated
failed cycles can generate new notices; these log observations are not fresh
SMTP receipt/final delivery proof. No test SMTP, cleanup of protected pages or
production notification change performed. Minimum follow-up is branch-specific
sanitized diagnostics, retaining all existing protection and bounded retries.


## Stage C — immutable Public Contract, isolated and uninstalled

Implements CEO3d77a67 approved boundaries without enabling business actors.
Research owns MarketReadQuery/Result: five market sources only (INSO excluded),
ordinary canonical SourceResult/IcNetResult or TP raw TpOffer tuple; IC.net TP
context retains stock/brand. TP raw handoff deliberately avoids independent FX
snapshots per worker; existing owner-side TpFx/ranking remains canonical.
Workflow owns version1 task identity using existing SheetRecordIdentity and
real domain task ID, module/cycle/request IDs, monotonic due/admission times,
immutable completion/cancel/fault and bounded enum progress. No fabricated
inquiry ID, new business ledger, callback, browser or session in payload.

Exact canonical deeply immutable payload validation rejects mutable evidence,
noncanonical objects, wrong source/mode, invalid identity/version, NaN times,
protected INSO, naive reference date and free-text faults. Resource fault reasons
cannot use non-global scope. Default repr excludes source snapshot/MPN/result.
These are in-memory ports, not external logs/export or authority for effects.
40PASS0.57s (message+lease tests), scoped Ruff/diff PASS. Prior A/B full remains
2868PASS1SKIP112.36s; no new full claim for this separate additive port commit.
Actor lifecycle, actual source handoff and fair module continuations still not
integrated; real browser proof and TP lateness remain open. Production unchanged.
## CEO independent Stage A/B source review — 2026-10-27

**Scoped CEO decision: STAGE_A_PASS /
STAGE_B_ATOMIC_STOP_SOURCE_PASS /
STAGE_B_DISTINCT_SOURCE_SLOT_BOUND_PASS /
STAGE_B_CROSS_MODULE_FAIRNESS_CHANGES_REQUESTED.
ACTOR_NOT_IMPLEMENTED; TP_TIMELY_900S_STILL_FAIL;
V16_OVERALL_REVIEW_REQUIRED.**

**Provenance and scope.** Actual remote branch HEAD fetched:
`42a881231da1221343aa1766ca732a0c5fe96d5d`;
Stage A `4a669daea75ad4ba8227787de1dc1c8e265e9abe`
followed the previous CEO source review, and B is one
fast-forward commit on A. Reviewer compared both changes and
read `src/workflow/service.py`,
`tests/workflow/test_order_resource_leases.py`,
unified report and `docs/evidence/v16/order-resource-regression.json`.
The final B source is not installed; current production remains
the previously reviewed `04075bc`.
Executor-reported offline A:65 targeted PASS/
2864PASS+1SKIP full (112.70s); B:69 targeted PASS/
2868PASS+1SKIP full (112.36s); Ruff/diff PASS.
CEO reviewed source/test design and committed evidence, did
not independently run Windows pytest or touch production.

### A: source-reviewed PASS / prior abort/rearm finding CLOSED

`configure_modules` no longer resets a fatal
`_module_resource_failed` latch and refuses
reconfiguration on that same failed runtime.
`_order_terminal` is set on ordinary Stop or
shared abort; `configure_order_leases` cannot
reopen it, including after active leases have
drained or Stop preceded initial configuration.
The exact scheduler-thread lease may still
release safely after closure. Separate fresh
runtime creation is a distinct lifecycle and
is NOT automatic authorization to reuse unsafe
Chrome. A's prior reproducible
abort → drain → configure_modules →
configure_order_leases bypass is closed by
source and regression tests.

### B: precise local contracts that PASS

- `begin_order_dispatch` validates exact
  granted object and admitting scheduler thread
  under the same runtime RLock. A competing
  `close_order_admissions` either precedes
  the transition (returns False; scheduler
  cancels reserved lease) or follows it
  (committed lease survives for completion).
  Duplicate dispatch/forged or copied/foreign
  handles are rejected in tests.
- Distinct source keys, not total same-key
  waiting tokens, consume the finite
  `capacity` reservation budget. Same-key
  queued requests are bounded to configured
  module count, and per-key FIFO plus
  cross-key simultaneous claims were tested.
  This fixes the previously demonstrated
  "same-row waiters consume other-row slot"
  issue in the isolated component.
- No module actor, asynchronous result
  handoff, worker terminal acknowledgment,
  scheduler fairness or real browser/TP
  deadline acceptance was implemented.
  In particular, the in-memory
  `_order_dispatched` flag is **not** evidence
  of actual worker submission/completion;
  `release_order_lease` can currently
  be called after the flag is set without
  proof of worker terminal acknowledgment.
  That handoff must be modeled and tested
  by the Stage C coordinator; do not treat
  these local stop-boundary tests as end-to-end
  drain safety.

### B cross-module fairness issue: CHANGES_REQUESTED before actor integration

Current `request_order_lease` caps the queue for
one source key by
`max(1, len(self._module_periods))`, but
the request's *module identity is not stored
or verified* and `request_token` is just
an arbitrary nonempty string. Thus, with
three modules configured, three requests from
inquiry to the same source row can exhaust
that row's three slots, causing a newly due
quotation or TP on the same source row to
return False. The source comment
"At most one queued request per configured
module per source slot" is not implemented
as stated. Even though mutual exclusion
prevents concurrent same-row processing,
this is not a cross-module non-starvation
guarantee. The existing B tests use three
different token labels and do not assert
a verified module identity; they therefore
do not refute this counterexample.

**Required minimal follow-up:** under the
already CEO-approved immutable Public
Contract, carry a validated `module_id`
(or otherwise enforce one pending slot per
actual module/cycle on a source row) rather
than interpreting the token text. Test
multiple cycles of one module trying to fill
a same-key queue, then another module's
arrival and eventual admission; preserve
per-source FIFO, different-source progress,
exact owner release, finite budget and
pending-work preservation. Do not invent
a second scheduler or durable ledger.
Where business policy truly permits multiple
requests per same module, implement explicit
fair scheduling rather than merely using
module count as a queue-length proxy.
A bounded request budget is not an absolute
start-deadline guarantee: continue to
measure actual TP due-to-start latency.

**Further Stage C integration gates:**
- Reserve→begin_order_dispatch→worker submit
  failure or Stop in between must have an
  exact scheduler-owned rollback/drain
  acknowledgment; never free an active
  lease while worker may still touch its
  source. Use immutable terminal result
  and fault receipt, not arbitrary local
  release timing.
- Ensure source identity is validated
  against fresh spreadsheet/snapshot data
  before write effects. Physical sheet row
  is a resource key, not durable identity.
- Preserve single Chrome, bounded
  independent sync market readers, shared
  PageResourceAdmission, site auth/pacing,
  exclusive Google/INSO owner and original
  SENT/UNKNOWN/120s barriers. Do not block
  the owner scheduler synchronously on a
  whole quotation Research batch. Show a
  real due-TP/long-quotation timeline.
- No deployment or production behavior
  changes are authorized by this review.

### Google notification: READ_ONLY_FINDINGS, ROOT_CAUSE_UNKNOWN

Read-only record shows four separate
`QuotationInputBusy` /
`GOOGLE_WEB_READ_BUSY` exhaustion groups
(09:57:23,14:56:49,16:03:20,17:04:34
+08, five open-sheet attempts per group).
These indicate a protected quotation-input
page could not be safely acquired/reused
before TSV reading, **not** that Google
is wholly unreachable. Current sanitized
logs do not differentiate protected pooled
entry vs unsafe pending/dialog surface vs
three-owned-pages capacity. Exact branch
cause UNKNOWN; manually opening Sheets
does not bypass owner/settlement safety.
Repeated cycles may generate separate
fault notices; the groups alone do not
prove four successfully delivered emails.
Next bounded change may add sanitized
branch-specific codes/count bands under
existing tests/observability only, without
page closure, guard bypass, SMTP test send
or arbitrary production intervention.

**Final:** `A_PASS`,
`B_LOCAL_STOP_AND_DISTINCT_SLOT_PASS`,
`B_FAIRNESS_CHANGES_REQUESTED`,
`GOOGLE_BUSY_BRANCH_UNKNOWN`,
`PARALLEL_BUSINESS_ACTORS_NOT_IMPLEMENTED`,
`PREVIOUS_TP_454_210S_DELAY_OPEN`,
`CURRENT_PRODUCTION_04075BC_UNCHANGED`,
`V16_REVIEW_REQUIRED`.


## CEO393a892 follow-up — actual module-aware source FIFO admission

A terminal lifecycle and B local stop boundary accepted by CEO. Correct the B
comment/behavior gap before actor use: request_order_lease now REQUIRES explicit
validated MarketModule from approved immutable contract, verifies it is configured,
stores it with scheduler owner/source key, rejects same-token module substitution,
and admits at most one outstanding request per actual module per source row.
It never infers module from token labels. Repeated inquiry cycles cannot reserve
TP/quotation's positions; those cycles remain in canonical domain work for later
retry. Existing FIFO and distinct-source budget retained. This changes an unused
isolated API; no production caller or feature enabled. Tests updated to provide
real module argument rather than illustrative token labels.

88PASS10.39s targeted across leases/messages/backend fault tests; Ruff/diffPASS.
Initial2failures were test loops still passing inquiry instead of loop module;
corrected fixtures and final88PASS. Prior B full2868/1SKIP belongs to earlier
source only. Added each module's100repeated cycles vs other modules' admission,
eventualFIFOclaim and independent-source progress, module forgery/type refusal.
No actual deadline/worker acknowledgment/business parallelism PASS inferred.


## Stage D — optional bounded read actors and canonical source handoff (PARTIAL)

Not connected to ProductionBackend's running module loop and NOT deployed.
Extends one WorkflowRuntime with bounded request registration, earliest-due
eligible selection, per-source module-aware FIFO leases, dispatch transition and
exact immutable terminal acknowledgment. A coordinator-dispatched lease cannot
be released through the raw lease API before terminal acknowledgment. Stop
cancels waiting/reserved work and retains submitted requests until acknowledged.
Late/different-cycle/source results are rejected. No additional durable queue.

Launcher MarketReadActors explicitly starts at most2fixed non-daemon threads;
blocking inbox wait creates no idle monitoring loop. Each thread constructs,
uses and detaches its own ResearchMarketSession. No Backend/WorkflowRuntime,
Page/Browser/credential/session object is sent into worker arguments. Transport
inboxes1peractor, terminal outbox2peractor, bounded enum observations4peractor;
no unbounded executor. No synchronous whole-batch wait on dispatch_ready.
Known submit refusal gets scheduler-owned canceled terminal; Stop/initialization/
teardown and typed native-lease failures have explicit terminal/fault messages.
Faults close shared admission, latch Runtime; Backend accept_market_fault port
uses original GLOBAL_STOP/notification path without blaming a historic order.
The port must still be consumed by future production composition, not a worker.

Research reuses all canonical parsers/adapters. collect_tp now calls extracted
collect_tp_offers then the SAME selection/FX logic; ordinary service unchanged.
New single-source interface performs no Excel writes, business mutation or
Backend callbacks. TP raw offers retain currency/date and IC.net stock/brand;
existing task owner keeps its one TpFx snapshot. ResearchMarketSession attaches
only same9222, IC.net configured CDP only, navigation to own pages, no login
providers. Four market sources usable in optional port; BOM auth and INSO remain
on existing owner path, not removed from six-source normal/TP research. BOM
actor requests explicitly hand back MARKET_OWNER_REQUIRED, never no-price.

Canonical factory supplies task-scoped native target ownership. Canonical source
finally blocks use close_research_page: legacy behavior outside optional scope;
inside, prove exact request-created native target before retirement, preserve
changed review markers, neutral blank protects last tab, shared uncertainty
stops without sweeping. Missing native lease explicitly invalidates common
admission even if adapter translates fault. No browser/Profile clone/launch.

Same-site actor queries conservatively serialize. Shared IC.net fence reuses
canonical90s rule across clients, checked by Runtime without a sleeping timer;
other source tasks remain dispatchable. Existing owner login/recovery coordination
and module-level protected operation handoff are NOT yet wired (Stage E open).
Normal inquiry/quotation query mode cannot silently use TP offer/month profile.

Tests: final targeted60PASS0.37s; earlier integrated parser/scope/backend58PASS
10.63s and first actor5PASS0.21s. Intermediate full2901PASS/1SKIP115.24s belongs
to pre-final mode/init-latch hardening only; final full to follow. Tests use actual
Python worker/queue paths + Events and existing synthetic HTML parsers, NOT real
Chrome or business success. They verify independent TP read can dispatch/return
while synthetic quotation read is unfinished, source-row serial completion,
Stop, initializer/native fault, terminal lease and existingIC90s pacing. No sleep/
Mock interval is claimed as web overlap or corrected real TP latency.

Remaining integration is material: current lease spans a READ REQUEST, not an
entire pending procurement/quotation/TP transaction. Existing synchronous domain
flows and Excel/FX finalization must resume on original owner with the same
real identity and a lease held across the full business continuation; no writes
can be enabled using this optional query bridge alone. All six source results,
owner auth recovery and GUI cycle/state handoff must remain canonical. Payload
bounds reject oversized data without truncation; owner fallback/chunk handling
needs review before broad use. Real browser Stage F not authorized this round.
Thus actual BUSINESS_ACTORS_NOT_INTEGRATED / TP454.210s_DELAY_OPEN persists.


## Google busy observation follow-up (separate from actor deployment)

Only adds fixed sanitized step labels immediately before the SAME existing
QuotationInputBusy raises: refresh-surface, refresh-uncertain, protected-entry,
pooled-unsafe and page-budget. No text/URL/account/worksheet value or screenshot
logged, no guard bypass, no retry/mail-policy change, no page mutation/cleanup.
122PASS1.99s Google transport/update regressions; new3branches assert unchanged
exception and original page set/human-page preservation. The two refresh paths
retain original recovery tests. This source is NOT installed, so prior current
production notices still have UNKNOWN precise busy branch; do not infer a cause
from new diagnostics that have never run there. Four observed retry-exhaustion
groups each failed before TSV download; manual Sheet access can coexist with
these operation ownership/settlement guards. No new production browser/DB access.

Stage E actor auth/owner recovery integration remains OPEN; this observation
increment is not full Stage E completion. New executable/install/browser test
requires existing independent Review and separately authorized safe windows.


## Stage D terminal race correction — isolated pre-deployment follow-up

Inspection found a real submit/exit race in the optional uninstalled actor bridge:
worker fatal/Stop could finish final empty inbox check before an already reserved
producer enqueued, leaving no terminal. Added one short launcher transport RLock
shared by submission, normal Stop signal and worker final inbox reconciliation.
No Research/browser call is under that lock; page reads still overlap. A producer
cannot enqueue after the worker's final retirement without Stop being visible,
and committed cancellation reaches scheduler terminal acknowledgment. No second
resource manager or business ledger. Same-runtime latch remains irreversible.

Final32actor tests PASS0.29s, including20Stop/submit interleavings and a barrier-
controlled initializer fault in the commit/enqueue gap, assert no real read and
no active lease residue. Combined actor/parser/backend62PASS10.45s before the
last additional tests. Previous full2907PASS/1SKIP113.12s belongs to0d77be2 source;
full final race-corrected source is running and must be recorded separately.
No production access, deployment or browser experiment. Actual module business
continuations, auth-owner recovery and Stage F remain OPEN, TP lateness not fixed.
## CEO independent B/C/D optional actor and Google diagnostic review — 2026-10-27

**CEO verdict:** `B_REAL_MODULE_FIFO_PASS`,
`C_V1_IMMUTABLE_PORT_SOURCE_PASS`,
`D_OPTIONAL_BOUNDED_ACTOR_FOUNDATION_CONDITIONALLY_ACCEPTED`,
`D_AUTH_CLASSIFICATION_CHANGES_REQUESTED`,
`GOOGLE_SANITIZED_BUSY_DIAGNOSTICS_SOURCE_PASS`,
`BUSINESS_CONTINUATION_NOT_IMPLEMENTED`,
`FINAL_D_FULL_REGRESSION_NOT_YET_EVIDENCED`,
`TP_TIMELINESS_FAIL_OPEN`,
`V16_OVERALL_REVIEW_REQUIRED`.

**Scope/provenance:** Independently fetched GitHub branch at
`0d77be23fe1bd1c56b9478f9059be453b93c6ef0`
and compared to CEO `393a89244d20c235b5de76623d7fd2defd51b1ec`.
Five commits: independent C
`c71ac4f9c22edd9587f710d086f23db95b576efa`,
merge `9ef130a...` containing both C and CEO review,
B fix `583f1c07412671670d9d9522de493d296f51c03a`,
optional actor `18320d6bfd288369c9bb75211359465310b5bb26`,
and Google labels
`0d77be23fe1bd1c56b9478f9059be453b93c6ef0`.
Checked actual `src/workflow/service.py`,
`src/workflow/market_messages.py`,
`src/research/market_contracts.py`,
`src/research/runtime.py`,
`src/research/service.py`, `src/research/tp.py`,
`src/research/cdp_pages.py`, canonical changed site
adapters, `src/launcher/market_actors.py`,
`src/launcher/backend.py`,
`src/launcher/google_quote_update.py` and focused tests.
No current production browser/DB/config/SMTP/Google/sales
operations or installation in this review. Installed production
remains reviewed `04075bc`, as executor reported.

### B: prior fairness finding CLOSED in isolated API

`request_order_lease` now REQUIRES a real
`MarketModule`, checks it is configured, stores the
module with canonical source key, token and owner thread.
A second request from the same module/source row is
refused regardless of its cycle-token text. Different
modules retain per-source FIFO, other source rows retain
independent slots; forged module substitution with same
token fails. Reviewed parametrized100-repeat-per-module
tests and reported88 targeted PASS. This closes the
CEO393a892 module-identity queue-slot finding, not
any guarantee of business-level deadline scheduling.

### C: bounded immutable v1 message contract accepted

Research's `MarketReadQuery/Result` carries source,
ordinary vs raw TP-offer mode, bounded parameters and
canonical read-only result types. Workflow's v1
`MarketTaskIdentity` wraps real
`SheetRecordIdentity`, module, cycle, request and
domain task IDs. Typed bounded completion, progress,
fault and terminal states reject mutable/unrecognized
payload shapes, unbounded string fields,
nonfinite timestamps and protected INSO source.
Resource ownership faults cannot be converted into
ordinary non-global errors. Default repr excludes
sensitive source snapshot and result fields. These
are in-memory ports, not durable claims, serialization
guarantees, external write authority or a second
ledger. Submitted40 focused PASS belongs to C and
must not be counted as a complete D suite.

### D: optional isolated actor foundation accepted, NOT actor E2E

`MarketReadActors` is *not* wired into
`ProductionBackend` module execution. It explicitly
starts at most two fixed non-daemon market-read threads,
with one bounded inbox per worker, a bounded terminal
queue and coalescible progress. Worker constructs and
tears down its own `ResearchMarketSession`, its own
sync Playwright/CDP client on that very thread,
reuses the existing9222 Chrome and canonical factory/
source parsers. No Browser/Page/Backend closure is sent
across a worker boundary; the shared runtime admission
is metadata-only. BOM and INSO continue to require
original owner-side protected flow; no actor login,
credential retrieval or external write was authorized.
Page-scoped native target proof and per-request
cleanup preserve review pages and latch uncertain
resource states. An explicit immutable `MarketFault`
port exists for the original Backend's
GLOBAL_STOP path but is not yet consumed by live
production composition.

The canonical `WorkflowRuntime` arbitrates per-source
module-aware FIFO and at most two active clients,
does not make the original scheduler synchronously
wait for the full Research batch, enforces same-site
conservative serialization plus IC.net's shared90s
pacing and checks exact terminal/cycle/source
acknowledgment before releasing coordinator-dispatched
leases. Synthetic real Python threads/queues
exercise long unrelated quotation read concurrent
with TP completion, same-row serial progression,
Stop/reserved/submit/cancel/drain, mismatched
terminal, setup fault and shared native ownership
fault. Submitted D final targeted60PASS;
earlier focused58PASS, while offline full
2901PASS/1SKIP was explicitly on an *intermediate*
source. At this reviewed head **no final-source
full regression evidence was supplied**; do not
upgrade it to final full PASS until the executor
supplies an exact SHA + full result.

### D source-proven blocking classification bug before actor integration

**Fix a concrete auth/manual-guard misclassification in
`src/launcher/market_actors.py`.** The
`_requires_auth` evidence-field check and
`_fault` direct-exception check use substring
heuristics `LOGIN/AUTH/CHALLENGE/CAPTCHA/CREDENTIAL`.
Existing canonical site/auth guard reasons also include
`MANUAL_VERIFICATION_REQUIRED`, `SESSION_STALE`,
`SECURITY_EVENT`, `OTP_REQUIRED`,
`VERIFIED_SESSION_LEASE_REQUIRED` and related manual
verification cases. Several of these do NOT contain
the tested substrings. Hence a canonical ordinary
`SourceResult(SOURCE_UNAVAILABLE)` with
`failure_code=MANUAL_VERIFICATION_REQUIRED`
may incorrectly produce
`MarketCompletion(SUCCEEDED, result=...)`;
the same reason as a directly raised adapter
exception may be downgraded to
`MARKET_SOURCE_FAILED` rather than
`MARKET_AUTH_REQUIRED`. This is source-provable
classification drift; it is *not* evidence of an
actual live login bypass, as this optional bridge
is uninstalled. Use canonical explicit safety
reason semantics, not broad exception-text
matching or a second login recipe. Targeted
tests must cover both returned typed unavailable
and directly raised cases for manual verification,
stale/unknown session, security event and OTP;
no worker may log in or reinterpret manual
verification as no valid price. A legitimate
site-defer must be handed back to original owner
for safe recovery, not silently treated as a
terminal ordinary source success.

### Integration blockers still OPEN (Stage E/F)

1. Current lease protects **one market read**, NOT
   whole inquiry/quotation/TP source-row business
   continuation. Acknowledgment removes that lease
   before the original owner resumes FX, aggregation,
   Sheets read/revalidate and any external action.
   Design explicit owner-side continuation/transaction
   exclusion and fresh durable validation before
   all writes; never let another module mutate the
   same logical source row in the gap. A read lease
   alone grants no business authority.
2. Existing `MarketReadActors` bridge has not been
   connected to the three module state machines,
   protected original-owner Google/INSO operations,
   auth recovery/GUI progress, or the production
   `accept_market_fault` entrypoint. Actor
   SITE_DEFER currently accumulates a blocked source
   without a proven reviewed safe resume signal.
   Correlate immutable results with the correct
   task/cycle/source snapshot; reject stale or wrong
   result, and ensure owner sees any shared global
   fault *before* applying returned success.
3. Bounded queues/Stop semantics are scoped to
   test clients: final source must prove
   submit-failure, delayed terminal, worker
   teardown failure, cancellation and bounded
   timeout (returning false from `close` is not
   guaranteed process shutdown) against the
   actual orchestrator. No forced thread/Chrome
   termination and no speculative page cleanup.
4. C's bounded payload validation rejects
   oversized legitimate parser output rather
   than truncating it; the owner requires a
   documented safe deferral/chunking behavior,
   not an automatic invented truncated price.
   Confirm TP owner's single FX snapshot and
   ordinary source-result equivalence with
   golden tests across all canonical source
   modes before introducing external effects.
5. The demonstrated prior TP due-to-start
   delay454.210s is still **FAIL/open**.
   Synthetic event overlap and real earlier
   native navigation overlap do not constitute
   independent live module business concurrency.
   Stage F needs Owner-approved safe window,
   real parsed-source timelines, same-order
   serial proof, source auth/pacing, bounded
   CPU/Chrome handles, actual TP deadline,
   GUI/restart/UNKNOWN and long-term stability.

### Google fixed-code observation: source-only PASS

`0d77be23` inserts exactly five static,
sanitized `log_step` tags at existing
`QuotationInputBusy` guard branches
(refresh surface/uncertain, protected entry,
pooled unsafe and page budget), with no
extra DOM/customer values, browser action,
guard weakening, retry change or
SMTP behavior change. Executor reports
122 targeted Google tests PASS; the new
three branch tests verify unchanged error
and page preservation. This is an uninstalled
diagnostic, so current live four historical
Google read-busy groups have exact underlying
branch **UNKNOWN**. Manual ability to open
the spreadsheet does not establish the protected
operation surface is reusable. Do not close
human review pages or test-send to "prove"
a cause.

**Final review scope:** B module-aware fairness
and C v1 interface accepted as isolated sources;
D optional actor transport/lease foundation
accepted with the precise auth-classification
repair **CHANGES_REQUESTED before enabling
module continuation**, and final-source full
regression evidence outstanding. Stage E
business integration and Stage F authentic
parallel/timeliness/soak remain entirely
`NOT_IMPLEMENTED/NOT_VERIFIED` as specified.
No old P1 or installed04075bc redo; no new
deployment or browser experiment approved.


## CEO8fb3f50 auth/manual classification correction (not deployed)

Prior frozen actor correction is287e23830dfd4aa226b3162464084ae1e969a4c7,
full2929PASS/1SKIP117.29s (src tree efe1f4d096d7c8e32e90f6a50cfd365b7356febf).
This closes the earlier missing final-source full evidence for that increment.

Fix the newly reviewed classification drift without a login recipe or text
matching. Move exact existing Backend INSO reason set to public Research
site_login.AUTH_SESSION_STOP_REASONS; Backend's old private name aliases the
IDENTICAL set, preserving ordinary behavior. Public SITE_AUTH_RECOVERY_REASONS
extends it only with explicit existing market/site_login emitted codes. Actor
returned evidence and direct exceptions both use set membership, not substring.
Manual verification, stale/unverified session, security event, OTP and required
verified lease defer the site to original owner; no source success/no-price or
worker login. Authenticated READ_EMPTY/READ_UNAVAILABLE stays a read failure.

304PASS1.30s targeted actor/site retry/login/sweep suite. Includes18 positive
returned/direct safety-reason cases and4negative non-auth cases. Initial targeted
command referenced a nonexistent filename and ran no tests; corrected to real
canonical test files, no dependency or production change. Final full on this
new classification source follows separately; old2929 is not reused as its PASS.
Still no module continuation/protected recovery/live callback integration or
real-browser/TP timeliness/long-term acceptance. Current04075 production unchanged.


## Latest execution status — Actor remediation / final offline evidence

Overall REVIEW_REQUIRED. Production04075bc is unchanged by this task; Owner's
previous开始运行 confirmation and17:01–17:04 module logs supersede old temporary
safe-stop/pending-resume statements below. No current real process state is
inferred from an old PID. No production EXE/config/Vault/SQLite/SMTP/browser
operation or installation was performed by this continuation.

| Stage / issue | Result and exact scope |
| --- | --- |
| A terminal lifecycle | PASS; source4a669daea75ad4ba8227787de1dc1c8e265e9abe; CEO393a892 accepts |
| B Stop + actual module FIFO | PASS scoped;42a881231da1221343aa1766ca732a0c5fe96d5d then583f1c07412671670d9d9522de493d296f51c03a; CEO8fb3f50 accepts |
| C immutable typed ports | PASS scoped;c71ac4f9c22edd9587f710d086f23db95b576efa; CEO8fb3f50 accepts |
| D optional read-actor foundation | PARTIAL;18320d6bfd288369c9bb75211359465310b5bb26, not enabled; scoped foundation accepted |
| D submit/final exit race | Fixed287e23830dfd4aa226b3162464084ae1e969a4c7; final owner terminal still required; REVIEW_REQUIRED |
| D manual/auth classification | Fixedf7d70baa51f942f27064ee9f84684549f1795d7b using canonical exact reason sets; REVIEW_REQUIRED |
| E full business continuation/owner auth/GUI binding | NOT_IMPLEMENTED; ports are prerequisites only |
| F real business-page overlap / TP due-to-start | NOT_VERIFIED; prior454.210s lateness remains FAIL/open |
| Google busy diagnostics | Source-onlyPASS0d77be23fe1bd1c56b9478f9059be453b93c6ef0; live precise branch UNKNOWN |
| Deployment/current production replacement | NOT_AUTHORIZED this round / not performed |
| V1.6 long run,100/150%DPI, Chrome game impact | NOT_VERIFIED; old9f soak cannot substitute |

Final application source **f7d70baa51f942f27064ee9f84684549f1795d7b**;
Git src tree **18bde855d3323b1a3aa1585ff0e983cdc28cea6a**.
Exact final full **2951PASS /1SKIP /114.03s**, scoped Ruff --no-cache and diffPASS.
Auth/retry/site login focused304PASS1.30s; actor Stop/submit32PASS0.29s;
Google transport122PASS1.99s. Tests use synthetic data/HTML and real local Python
threads/queues only, with no network/business/SMTP. This is NOT actual website
concurrency or repaired live TP scheduling proof. Previous failed commands/test
fixture corrections remain historical and are not counted as successful runs.
15existing completed task-owned test directories retired by checked explicit
absolute names, no reparse traversal/ACL change; small stdout/summary evidence
retained. No persistent monitor or worker left by tests.

Changed production-source files grouped by purpose: workflow/service.py owns
lease lifecycle/fairness/read handoff; workflow/market_messages.py and
research/market_contracts.py own immutable ports; launcher/market_actors.py owns
optional bounded thread transport; launcher/backend.py adds explicit fault port
and reuses unchanged old auth-stop set; research/runtime.py creates thread-local
read session; research/service.py and tp.py expose existing source acquisition;
research/cdp_pages.py and five market source finally blocks verify own cleanup;
research/icnet.py shares its existing90s constant; research/site_login.py exports
existing safety semantics; launcher/google_quote_update.py only logs fixed busy
branches. Corresponding workflow/launcher/research tests and existing report/
task/design/evidence updated. No price algorithm/month window/SMTP/production DB
schema/120s wait or procurement permission change, no new dependencies.

Recommended next work: keep current reviewed production installed. Integrate
owner-side business continuations with one lease held across read, FX/projection,
fresh source/durable validation and external effects; bind actor global faults
before consuming success and bridge original owner's auth recovery/GUI events.
Do not enable this single-query optional bridge as if it protects a whole order.
Then request a separate authorized safe real-browser window for parsed-source
and due-TP timelines, without using normal production as an experiment.


## CEO independent terminal race and explicit auth reasons re-review — 2026-10-27

**Verdict: TERMINAL_SUBMIT_EXIT_RACE_SOURCE_PASS /
AUTH_SITE_REASON_CLASSIFICATION_SOURCE_PASS /
FINAL_OFFLINE_REGRESSION_EVIDENCE_ACCEPTED /
OPTIONAL_ACTOR_FOUNDATION_ONLY /
BUSINESS_CONTINUATION_NOT_IMPLEMENTED /
V16_OVERALL_REVIEW_REQUIRED.** This is a narrowly scoped
independent review; accepted A/B/C fixes, existing reviewed
P1 and installed `04075bc` are not reopened.
Reviewer accessed GitHub code and executor-submitted
regression evidence only. No protected Chrome, production
EXE/SQLite/config/Vault, SMTP, Google or purchase operation.

**Precise provenance.** Remote
`codex/v1-6-independent-scheduling` HEAD
`d9bfaefbe7581c500b132c84ba61d4478cdf3169`,
parent application source
`f7d70baa51f942f27064ee9f84684549f1795d7b`.
The two commits have the identical Git `src/` tree
`18bde855d3323b1a3aa1585ff0e983cdc28cea6a`;
evidence commit alters only
`V16_RELEASE_REPORT.md`,
`tasks/2026-10-27-v16-independent-scheduling.md` and
`docs/evidence/v16/order-resource-regression.json`.
Prior terminal-race source
`287e23830dfd4aa226b3162464084ae1e969a4c7`
was merged with existing CEO
`8fb3f504e5537f5951e64467dbb4a033248a4af6`
via `ba54598f...`; `f7d70ba` then made the
explicit auth classification fix.
No parallel implementation or unreviewed production
installation is accepted here.

**Review of the exact Stop/commit/enqueue/final-exit race
(`287e238`): PASS in source/isolated thread tests.**
Previously the worker's final `get_nowait` could
finish before a coordinator with an already-committed
lease enqueued the request; this had no terminal
receipt and stranded the slot. The narrow
`MarketReadActors._transport_lock` now serializes
`dispatch_ready` reservation+enqueue, thread-safe
`request_stop` and worker finally's queued
job cancellation. A worker fatal sets stop before
final lock reconciliation; either submission wins
then final draining acknowledges cancellation, or
final retirement wins and subsequent dispatch sees
stop. The lock is **not held during browser reads,
source parsing or external operations**. The existing
scheduler-owned immutable `MarketCompletion`
acknowledgment releases the exact resource.
Regression directly tests submit refusal, twenty
stop-in-the-gap interleavings and a barrier-controlled
initializer exception between commit and queue
insertion; each asserts no read and zero surviving
active leases. Executor reported32 focused actor
PASS (0.29s). This is a bounded invariant proof
in supplied test execution, not a guarantee about
future business owner continuation or every
possible external-client failure.

**Review of explicit auth/manual safety reasons
(`f7d70ba`): PASS for scoped actor classification.**
The prior `_INSO_AUTH_STOP_CODES` frozen set from
Backend was moved **without member changes** to
`src/research/site_login.AUTH_SESSION_STOP_REASONS`,
with Backend's original identifier aliasing it.
Research also declares
`SITE_AUTH_RECOVERY_REASONS` as that canonical
set plus exact pre-existing market login codes.
Actor `_fault` for thrown typed site codes
and `_requires_auth` for returned
`SourceEvidence.failure_code` now use
exact set membership, not substring/free-text
parsing. Existing
`MANUAL_VERIFICATION_REQUIRED`,
`SESSION_STALE`, `SECURITY_EVENT`,
`OTP_REQUIRED`, `VERIFIED_SESSION_LEASE_REQUIRED`,
`SESSION_IDENTITY_UNVERIFIED`,
`LOGIN_REQUIRED` and explicit market login
codes yield `SITE_DEFER / MARKET_AUTH_REQUIRED`
with no successful source result; known read
failures such as `READ_EMPTY` and
`AUTHENTICATED_READ_UNAVAILABLE` remain
ordinary read failures. This preserves
worker no-login and owner-only recovery.
Executor reported304 targeted auth/site PASS
(1.30s) including18 positive returned/raised
cases and4 negative cases. No login
or credential operation was exercised by CEO.

**Final exact-source test evidence:** published
`order-resource-regression.json` records
`2951 PASS / 1 SKIP` in114.03s,
Ruff/diff PASS, actor race32 PASS,
auth/site304 PASS, Google122 PASS.
Unlike earlier `2907`, `2929` or
`2901` runs, this record binds explicitly
to `f7d70ba` and the exact verified
`src/` tree. Tests were run by Executor
on Windows, **not independently rerun by
CEO**. Reported15 owned finished test
scratch folders were retired; untouched
production/rollback/unknown paths
were not independently inspected.

**Unresolved actor-integration/release gates:**
- `MarketReadActors` remains optional and not
  attached to the running module business
  loop. Authentication `SITE_DEFER` marks a
  site blocked and awaits the original
  browser owner; safe owner-side recovery,
  re-admission and protected/manual page
  preservation are NOT IMPLEMENTED here.
  Classification PASS is not login-recovery PASS.
- Current source-row lease spans only an
  individual market read, not the complete
  procurement/quotation/TP business
  continuation. Add one canonical owner-side
  continuation, fresh source identity and
  existing Google/INSO/write/SENT/UNKNOWN
  gates before any effects. No duplicate
  ledger or extra Chrome/Profile.
- Unbound actors, application GUI progression,
  fault port consumer, terminal reconciling
  of unusually delayed/stuck native worker,
  authentication pacing, request/result
  collection across all six canonical sources,
  and long-term memory/Chrome/game benchmarks
  need separate code and acceptance. A
  `close(timeout)` returning False does not
  guarantee OS thread exit; do not force
  Chrome/thread shutdown to pass tests.
- The previous genuine TP start lateness
  `454.210s` is still FAIL/open. Synthetic
  actor test overlap is not proof of actual
  live page-source/result concurrency.
  Stage F safe browser acceptance had no
  authorization or execution in this round.
- The Google fixed-code busy branch
  diagnostics remain **uninstalled**, so
  the precise trigger for historical
  `GOOGLE_WEB_READ_BUSY` notifications
  remains UNKNOWN; no fault test SMTP
  was sent.
- Production is still executor-reported
  reviewed `04075bc`; current historical
  SENT/UNKNOWN/commands and rollback
  protections were not touched or
  independently read live. Do not claim
  new deployment/business success.

**CEO release posture:** Scoped correction findings
from `8fb3f50` are CLOSED; continue Stage E
canonical owner business continuation and
recovery with separated evidence. No reapproval
of prior ordinary business is requested, and no
deployment permission is inferred from this Review.
`D_FOUNDATION_NOT_PRODUCTION_READY`,
`E_NOT_COMPLETE`, `F_NOT_RUN`,
`V16_OVERALL_REVIEW_REQUIRED`.

## CEO supplemental independent review — direct canonical login exception gap (2026-10-27)

**Verdict update (precisely bounded):** STOP_COMMIT_FINAL_EXIT_RACE_SOURCE_PASS
remains accepted. Exact-name `SourceEvidence.failure_code` and adapter
`.code` / `.reason` auth-classification paths remain accepted.
**DIRECT_SITE_LOGIN_ERROR_CHANGES_REQUESTED** for the advertised
"direct exceptions" coverage of `f7d70baa51f942f27064ee9f84684549f1795d7b`.
V1.6 overall **REVIEW_REQUIRED**; no new deployment/Stage F authorization.

**Independently source-proven missing route:** The canonical
`src/research/site_login.py` `SiteLoginError.__init__` stores its immutable
safe reason in `error.reason_code` (not `.code` or `.reason`).
`src/launcher/market_actors.py::_fault` currently obtains only
`getattr(error, 'reason', None) or getattr(error, 'code', None)`.
Thus a directly raised `SiteLoginError('MANUAL_VERIFICATION_REQUIRED')`
(or `SESSION_STALE`, `OTP_REQUIRED`, `LOGIN_NOT_CONFIRMED`, etc.) from
`session.read` is deterministically mapped to
`MarketFault(FAILED, 'MARKET_SOURCE_FAILED')`, **not**
`SITE_DEFER / MARKET_AUTH_REQUIRED`; the source will not be blocked.
The new parametrized direct-exception tests create a synthetic exception
with `.code`, so they do not exercise the actual canonical
`SiteLoginError.reason_code` interface.

**Impact/scope:** The current optional `ResearchMarketSession` sets
`login_provider=None` and canonical CDP clients usually translate
`SiteLoginError` to adapter errors carrying `.code`; therefore this
is a **provable classifier/API coverage gap**, not proof that the
currently installed `04075bc` has hit it or that any real browser
login was bypassed. The actor remains uninstalled. No change to the
previously accepted Stop race, Backend's identical auth-stop set, or
final-source test attribution follows from this finding.

**Executor minimum remedy, under the SAME Stage D task (no new architecture):**
1. In the single existing `_fault` classifier, recognize the typed
   canonical `SiteLoginError.reason_code` (and, if warranted by actual
   adapter wrapping, inspect documented typed causes) while using the
   existing `SITE_AUTH_RECOVERY_REASONS` exact allowlist. Never parse
   exception text, URL, credential or arbitrary page content; do not
   broaden a login recipe, launch a worker login, or change original
   Backend safety-gate behavior.
2. Regression must **raise actual `SiteLoginError` instances directly**
   from an actor test session, not merely a fake exception with
   `.code`: exercise manual challenge, stale/unverified session, OTP,
   security event and at least one market login code. Assert
   `SITE_DEFER / MARKET_AUTH_REQUIRED`, no result/success, site blocked,
   shared runtime not falsely globally stopped, and exact resource
   lease released on terminal acknowledgment. Retain adapter `.code`
   and returned-evidence positives, non-auth negatives, plus
   initialization failure GLOBAL_STOP and cleanup/resource GLOBAL_STOP.
3. Run the focused suite and the exact post-fix full offline regression;
   bind both to the **new final application SHA and src tree**, keep
   deterministic tests and no production/browser/SMTP/SQLite use.
   Report newly identified safety reason tokens separately if any,
   without blindly labeling normal READ_EMPTY/READ_UNAVAILABLE as auth.

**Evidence quality:** The existing `d9bfaef` JSON asserts
2951PASS/1SKIP/114.03s against the verified `f7d70ba` Git src tree;
it is Executor-produced output, not an independent CEO Windows rerun.
No GitHub commit status checks were returned for `f7d70ba`.
Those numbers are not deleted or reassigned, but do **not** cover the
specific native exception case above.

**Stage E/F remains unchanged:** Complete the original owner-side
business continuation, same-source-row end-to-end exclusion,
site recovery and original Google/INSO/SMTP safeguards before enabling
actors. TP historical 454.210s lateness, real query overlap, long-term
resource stability and Stage F authorization stay OPEN.


## Direct canonical SiteLoginError supplemental remediation (isolated)

CEO basis06ed60feb7ce9a56e83e3b251760ef8ba8cad037; only newly requested route
changed. Application68e1a2d2aa2b289c1fd38da33686851ff90bec7d, exact src tree
0de681c1f7590779f647a17841230b498ff35aef. _fault recognizes reason_code ONLY
on actual Research SiteLoginError instances; existing .code/.reason and returned
SourceEvidence paths and EXACT SITE_AUTH_RECOVERY_REASONS are unchanged. No
new safety tokens, exception-text parsing, login recipe, worker credential,
Stop/Public Contract or original Owner permission change.

92PASS1.13s actor/site_login focused. Actual SiteLoginError raised by actor test
session covers manual challenge, stale/unverified session, OTP, security event,
market login-not-confirmed. All yield SITE_DEFER/no result, blocked site, exact
terminal lease release, shared runtime remains open. Native/untyped non-auth
negatives and native initialization GLOBAL_STOP tested; existing adapter/evidence
positives, resource/cleanup and Stop races retained. Exact frozen-source full:
2961PASS/1SKIP113.55s. Ruff/diffPASS. Executor Windows offline evidence only,
not CEO independent rerun or real browser/production validation.

Overall REVIEW_REQUIRED; E/F and historical454.210s TP lateness remain open.
Owner asked to complete BOTH supplemental remediation and isolated continuation;
prior E work is preserved in local codex/v1-6-e-continuation-isolated, not mixed
into this scoped fix. Continuation resumes in separate increments. Final combined
report goes to Owner for forwarding; never sent directly to CEO.


## Stage E execution — E-0 verified / E-2 first dependency increment

Remote4b6018b (CEO latest scoped PASS) fast-forwarded; its src tree equals
18bde855d3323b1a3aa1585ff0e983cdc28cea6a and prior2951/1SKIP evidence. No A/B/C
rewrite or production reinstall. Owner now requires ALL reports via Owner only;
Executor must not send reports/messages to CEO tools. Current phase authorizes
isolated source/tests only, not production browser/runtime/config/DB/SMTP.

Reuse: extend existing Runtime OrderResourceLease/RLock/FIFO, not a parallel
lock/ledger. New BusinessContinuationLease retains that SAME original-source
resource across sequential reads, Owner FX/source check and effects. Query
terminal clears query dispatch metadata but DOES NOT release business lease.
Exact scheduler owner + immutable matching BusinessTerminalReceipt required
for release. Active query/effect blocks release; UNKNOWN latches global abort
and holds lease for canonical durable reconciliation, never inferred safe by
Stop/timeout. Source-row lease still grants no write/purchase/mail authority.
New query transport IDs are runtime-nonce+sequence, preserving actual domain IDs
and rejecting old query terminals without an unbounded tombstone history. Pending
FIFO identity is retained; Stop cancels undispatched pending requests. Optional
D single-read compatibility remains; E business continuation uses explicit bound
read port and cannot use raw release to bypass full-business acknowledgment.

89PASS0.94s focused leases/actors/continuation; Ruff/diffPASS. Tests cover three
modules same row, independent row, query→effect gap, Stop/drain, unknown effect,
exact/foreign/copy release and old completion. No new full-regression claim yet;
full after integration. E1 real module bindings, E3 recovery, E4 GUI/scheduler and
E5 comprehensive regression still OPEN. This E2 resource contract alone is not
business success, fresh domain verification or real-browser/TP timing proof.

### E1 canonical Research continuation — executor increment

Reuse-first: extract existing ordinary completion and TP ranking without a
second parser/aggregation policy. Both old synchronous paths drive the same
owner continuation. Actor payload consumption preserves source order, original
domain task ID, Owner observation/protected INSO context and TP FX snapshot.
197PASS8.51s on tests/research/{test_continuation,test_aggregation_service,
test_six_price_sources,test_tp}.py and tests/workflow/test_tp_research.py.
E1 PARTIAL: domain claim/finalize integration follows; scheduler/live timing
not accepted. E3/E4/E5 still OPEN. No production operations; Owner-only reports.

### E1 three original-domain ports — source increment / not deployed

Extracted canonical V12 prepare/settle and worker claim; V13 per-candidate
protected query/settle; same TP outbox. Each holds canonical source transaction
through original business finish; immutable results reject wrong module/cycle/
domain/source. Original purchase rules, duplicate guards, SENT/UNKNOWN and120s
row wait remain authoritative.5 new isolated domain testsPASS0.91s, original
137 testsPASS11.07s and quote93PASS5.29s. E3/E4/final E5 remain open; real timing/
web overlap NOT_VERIFIED. Scope strictly offline, default installed program
unchanged; report to Owner only. Direct login patch separately68e1a2d.

### E3 source increment — original Owner recovery / no truncation

Explicit recovery reuses original login sweep at quiescent owner boundary, exact
successful site verdict only. Typed over-budget legal source results hand back
to canonical Owner collector; no truncation/no-price substitution. Single Runtime
retires only proven undispatched read reservations.83PASS2.92s focused; native
SiteLoginError cases independently6PASS0.25s. No auth token addition, worker login,
production use, browser validation or deployment. E4/final E5 remain OPEN.

### E4 implementation increment — actual original Backend assembly (isolated)

Canonical Backend owns per-module bounded continuation contexts, existing
Runtime deadlines/FIFO/resources own decisions, existing fixed actors own market
queries. No new timer/worker pool/ledger. Explicit market_actor_factory test/
review assembly; DEFAULT OFF, installed04075bc untouched. Source reservations
(max3 configured modules) do not consume the two real market execution slots.
Original fault/defer/three-hour policy, source fresh checks,120s closed waits,
SENT/UNKNOWN and original owner-only INSO/Google/purchase writes retained.
Owner protected read phase closes before yield and rebinds real task before
INSO/purchase. Google write settlement cannot pump another owner operation.
Three module stages/cycles/elapsed/deadlines and current-source progress stay
separate, unchanged notifications coalesce. Shared fault precedes results.

Source tests include actual Backend/Runtime/domain paths with isolated SQLite,
canonical selectors and thread transport; clients/senders synthetic. Do not call
this real business/browser or TP wall-clock PASS. Final exact source full/evidence
next. Scope: E1/E2/E3/E4 OFFLINE_IMPLEMENTED_REVIEW_REQUIRED; E5 full pending;
F real page overlap/TP deadline/long-run NOT_VERIFIED. No production changes.

### E5 first full findings and minimal corrections

b35e606 full:2996PASS/2FAIL/1SKIP132.11s, NOT PASS. Restore exact legacy quote
wait callback for default composition; explicit actor assembly alone uses closed
retry pump. Original RFQ006 tests unchanged. Recheck shared safety after original
business callbacks and before TP enqueue, quarantine canonical pending Google
write outcome, immediately signal existing actor Stop from original Backend.
87PASS8.23s affected canonical backend/domain/purchase-completion regression.
Final-source full next; no production/browser/SMTP use, overall REVIEW_REQUIRED.


## Combined Owner handoff — direct login correction and Stage E final offline evidence

Latest requirement: Owner forwards ALL reports; Executor must never message CEO.
Both requested source tasks delivered together in existing V16_RELEASE_REPORT.md
(top combined summary), not a second report or task ledger. Current round permits
isolated source/tests ONLY. Historical broad production authorizations do not
permit install/restart/Chrome/DB/config/Vault/SMTP activity in THIS round.

Final application3547c4162d0b5c0308c84ae8a7feba23a39f6a70;
exact src5ce508705c7e4099d41ae5c9456eaf19a80e427b.
3001PASS/1SKIP120.81s;87PASS8.23s focused. Skip is Windows symlink creation
unavailable, not waived safety checks. Direct-only68e1a2d remains independently
reviewable with2961/1SKIP evidence. Initial b35 two legacy callback failures are
recorded, source-corrected and unchanged old tests now pass. No auth allowlist,
SMTP sender, old accepted Stop protocol or business permission broadening.

| Unified requirement | Executor status / exact limit |
| --- | --- |
| DIRECT_SITE_LOGIN_ERROR | PASS offline; actual native reason_code, pending independent CEO review |
| E1 original three domain continuation ports | PASS offline; same Backend optional assembly, default OFF |
| E2 full source transaction / FIFO / actual IDs | PASS offline; canonical Runtime only, two market slots |
| E3 original owner recovery and over-limit return | PASS offline; no worker login or result truncation |
| E4 module contexts / Stop / terminal / bounded GUI | PASS offline; actual original call paths with synthetic clients |
| E5 final full regression | PASS offline3001/1SKIP; source/tree bound in existing JSON |
| Real browser overlap / actual TP start delay | NOT_VERIFIED; prior454.210s remains acceptance-open |
| Long-term resource/DPI/game/actual new GUI | NOT_VERIFIED; old9f soak not reused or inspected |
| Production replacement / enabling new assembly | DEFERRED; no authorization/execution this round |
| Google prior exact busy branch | NOT_VERIFIED/UNKNOWN; no new production access |

37 finished owned test scratch directories retired after boundary/reparse checks;
no new dependencies/daemon/scheduler/browser/profile/ledger. No production data,
credentials, real screenshots/mail bodies or raw TSV committed. Do not interpret
new actor default-OFF as a change to existing production TP authorization/config.
Next Owner action: forward the ONE combined report to CEO source review. Future
real browser/production acceptance needs its own explicit safe window; no current
production stop requested. Overall V1.6 REVIEW_REQUIRED, not a self-issued PASS.

## CEO independent review — unified direct login + Stage E offline delivery (2026-10-28)

**Review source identity.** Remote branch HEAD at prewrite check:
`8a271b9b66b53d3e89e6d10270653d151d0ce095` (docs-only child of
application `3547c4162d0b5c0308c84ae8a7feba23a39f6a70`).
Independently fetched Git tree `src/` =
`5ce508705c7e4099d41ae5c9456eaf19a80e427b`, which equals the
report/JSON claim. Executor-submitted final3001PASS/1SKIP120.81s,
targeted87PASS8.23s, Ruff/diffPASS are correctly attributed to that
exact application source; **not rerun by CEO on Windows**. JSON is
self-reported test evidence, not independent live Chrome, production,
SMTP, SQLite or real Google evidence.

**Verdicts (precise and non-overlapping):**
- `DIRECT_SITE_LOGIN_ERROR_SOURCE_PASS`. The change
  `68e1a2d2aa2b289c1fd38da33686851ff90bec7d` uses the actual
  `SiteLoginError.reason_code` ONLY on typed canonical instances in
  `src/launcher/market_actors.py::_fault`, retaining exact
  `SITE_AUTH_RECOVERY_REASONS`; the native raised exception tests cover
  manual verification, session stale/unverified, OTP, security and
  market login readiness plus non-auth negatives, initialization
  GLOBAL_STOP, no worker login. Prior narrowly scoped CEO finding
  CLOSED (source-level only).
- `E1/E2/E3_SOURCE_FOUNDATION_REVIEWED`: actual original V12/V13/TP
  continuation ports, unchanged per-module original domain write
  guards, single WorkflowRuntime source-row exclusion across query and
  owner effects, bounded actor transport, exact receipt/cycle identities
  and owner-only recovery are visible in the committed source and
  synthetic domain regression. No real successful business claim.
- **`E4_OWNER_POLL_PARITY_CHANGES_REQUESTED`** on the new optional
  `src/launcher/business_continuations.py` owner loop. This is
  source-provable functional parity loss, not a test count mismatch.
  `E5_EXECUTOR_OFFLINE_EVIDENCE_ATTRIBUTED` does not close this gap.
  Overall V1.6 `REVIEW_REQUIRED`, production unchanged/uninstalled.

**Required fix 1 — canonical dashboard counts omitted (confirmed).**
`ProductionBackend.start()` initializes/resets `_dashboard_counts=None`.
Only `ProductionBackend._refresh_dashboard_counts` sets that field.
The original independent loop calls it when inquiry/quotation cycles
start (`src/launcher/backend.py` around lines1175-1179), whereas the
new optional owner path branches to `run_business_continuations`
(around lines1163-1167) and has **no call** to the method.
`Backend` workbench snapshot reads this field to populate
`new_orders`, `awaiting_quotation`, `overdue_quotation`
(around lines2639-2641), so those displayed values remain None in
a newly started optional assembly despite its active domain cycles.
`_cache_workbench` cannot replace the missing canonical count read.

**Required fix 2 — cycle projection never reset (confirmed).**
Old independent inquiry entry calls `_begin_poll_projection`; this
clears `_poll_inquiries` and `_poll_quotation_completed` at each
new original inquiry poll. New E owner loop does not call it anywhere.
Without a per-cycle reset, these sets aggregate prior cycles and
misrepresent the current round in summary counts. Reuse the original
backend projection reset at the correct inquiry boundary; do not
clear after observing a cycle or while a protected operation is active.

**Required fix 3 — prior site recovery entry lost (confirmed).**
Old independent loop enters `_check_site_recovery(rc, cfg)`
before each module. The new optional loop does not.
`_check_site_recovery` is the original owner path which checks the
manual INSO verification gate (`_site_manual_wait`), safely
confirms `authenticated_inso_shell_available`, clears that wait
only on actual success and handles existing V12 paused-state
recovery/Browser CDP containment. New actor
`recover_sites_on_owner` only covers its separate deferred
IC.net/Findchips/HQEW/LCSC market sources; it does **not**
replace this original INSO/manual recovery function. Reinstate
the old gate on a safe original-owner boundary before eligible
work, preserving its exact safety semantics; do not auto-confirm
login, touch credentials from worker, close human pages, or add a
second recovery mechanism.

**Executor smallest change/test contract (same task, no re-architecture):**
1. Reuse those **three existing Backend methods**, preserving
   original module cadence and ownership. Add their missing
   invocation at safe owner module/cycle boundaries of the existing
   optional E loop; avoid polling heavy Sheets counts on every
   50ms tick, while a protected operation is open, or as another
   worker's action. Preserve current actor Stop, FIFO and source
   lease behavior. No parallel dashboard counter implementation.
2. Add deterministic isolated integration tests using an actual
   `ProductionBackend` optional assembly with controlled module
   dates and canonical snapshot: assert populated/updating
   `new_orders/awaiting_quotation/overdue_quotation`, accurate
   current-cycle projection reset across two inquiry cycles, and
   no repeated extra writes. Assert owner INSO manual wait remains
   blocked when session remains unverified and is cleared ONLY on
   canonical verified success; retain original site-outage and
   V12 resume behavior. Use no real browser/Google/SMTP/purchase.
3. Run narrow affected regressions plus exact new-source full
   offline suite. Record full SHA, `src/` tree and skipped test
   reason in original report, task and evidence JSON. No use
   of old3001 as a PASS for modified source. Scope Ruff/diff.
4. Keep approved single runtime, two worker clients, original
   Chrome9222/profile, Backend credential/Google/INSO/SMTP/
   SENT-UNKNOWN gates, 120s closed-row wait, default OFF and
   approved prior P1/A/B/C/D unchanged. No actual install,
   production access or Stage F browser use.

**Open beyond this change:** Real safe-window browser overlapping
parsed reads, full same-order transactions, observed TP
due-to-start delay (historical454.210s FAIL/open), recipient
delivery evidence, GUI100%/150%DPI, long-term RSS/handles and
Chrome/game impact still need separate authorized Stage F/soak
acceptance. A synthetic test or submitted pass count cannot close
these gates.


## Executor E4 owner poll parity remediation — 2026-10-28 / Owner handoff only

Based on formal remote review85b24f09f1a912345d78a640dbc666d0cc0d28d1,
fast-forwarded without overwriting source. Native login SOURCE_PASS remains
closed; no auth set/Stop/Public Contract redesign. E4 pending CEO re-review.

Source `bfa835b7eda1c71ddf4f4d7f383f2f4d2b7a2234`; src tree `d5024ea81060ef4285d8bf7d7453a2a305f1b71d`.
Only7 source lines restore original Backend `_check_site_recovery(rc,cfg)`,
`_refresh_dashboard_counts` for inquiry/quotation, and `_begin_poll_projection`
for inquiry. These run once when the original-owner cycle generator starts,
inside existing context/scope before domain claims, never per50ms tick.
No second stats/recovery mechanism, no new worker/timer, no production changes.

Tests: same actual Backend/Runtime/three domain ports, synthetic clients and
isolated SQLite/outbox. Existing13 cases retained, new3 cases cover two-plus
cycles with canonical get_status counts(1,1,1)→(0,0,0), exact per-cycle call
counts, stale projection clearing, no repeated business writes/TP command,
verified/unverified original manual-INso recovery and V12 resume/outage safety.
Actual owner-thread and no-open-protected-operation assertions retained.
First new projection assertion omitted IDs produced by real completion callback;
corrected to compare its whole observed set, without removing original cases.

173PASS20.81s focused across loop, site outage recovery, dashboard, safety/UI,
nested context, actors, business leases and owner recovery. Exact source full:
3004PASS/1SKIP128.29s. Skip tests/workflow/test_v12_evidence_and_safety.py:56,
symlink creation unavailable; no permission change. Scoped Ruff/diffPASS.
Four completed owned test scratch dirs retired after boundary/reparse checks.
Only report/task/JSON follow-up changes after tested source; same src hash.

| Requirement | Executor evidence status |
| --- | --- |
| E4 original dashboard refresh | PASS offline; canonical counts update, no per-tick reads |
| E4 inquiry cycle projection reset | PASS offline; prior round fully clears |
| E4 original safe site recovery | PASS offline; original verification gate preserved |
| Prior source leases/two Actor cap/auth/120s/Stop/idempotency | PASS affected/full offline; mechanisms unchanged |
| Final source full suite | PASS offline3004/1SKIP128.29s |
| Google newly reported notices | NOT_VERIFIED / UNKNOWN cause; NOT_FIXED in production |
| Real overlap/TP454.210s lateness/long-term stability | NOT_VERIFIED / OPEN; no synthetic closure |
| Installation / production / live browser | DEFERRED; not authorized/executed this round |

Owner again reports Google unavailable mails hours earlier. No new live logs,
receipt, process hash or browser accessed, therefore not proof of a false alarm
or fresh duplicate command. Existing archived evidence shows busy protection
before TSV download and per-cycle notification dedup; successive failed cycles
can each notify. Manual opening does not satisfy automation ownership/settlement.
Archived production baseline04075bc and uninstalled diagnostic0d77be23 are NOT
a fresh live-version check. This E4 patch does NOT fix the current notifications;
no mute/guard/retry change made. Minimum proposed follow-up: separately authorized
installation/diagnostic window for reviewed sanitized branch labels, then narrow
cause repair and review of transient-read wording/incident dedup. Preserve
serious safety/UNKNOWN/manual notifications; no speculative suppression.

Overall REVIEW_REQUIRED. New optional assembly still default OFF, not a claim
that existing production TP is OFF. Production/runtime/config/Vault/Chrome/
SENT/UNKNOWN/old soak untouched. Owner forwards updated V16_RELEASE_REPORT.md;
Executor must not send to CEO. No new Owner action or production stop requested.

## CEO independent scoped Review — E4 parity + Owner 60-second Google snapshot requirement (2026-10-28)

**Verified review base:** remote `codex/v1-6-independent-scheduling`
HEAD `af23afb2f36c32037e37602105da5448d887d993` is a docs-only
child of tested application commit
`bfa835b7eda1c71ddf4f4d7f383f2f4d2b7a2234`. The Git `src/`
tree is `d5024ea81060ef4285d8bf7d7453a2a305f1b71d`.
Executor evidence (not independently rerun on Windows) states 173
targeted PASS/20.81s, full 3004 PASS/1 SKIP/128.29s, Ruff/diff PASS;
the sole skip cites unsupported symlink creation.

**Scoped verdict: `E4_OWNER_POLL_PARITY_SOURCE_PASS`.** Only seven
application-source lines were added to
`src/launcher/business_continuations.py::orders`, reusing the exact
Backend `_check_site_recovery(rc,cfg)`,
`_refresh_dashboard_counts(...)` (inquiry+quotation) and
`_begin_poll_projection()` (inquiry). They run at the lazy generator's
one-time per-module-cycle entry in the existing Owner context/scope,
not at every 50ms dispatch tick. New original-Backend offline
integration tests assert counts changed1/1/1→0/0/0, full prior-cycle
projection cleared, original INSO manual verify guard and verified
recovery, no repeated purchase/quotation/TP effects. The prior three
`E4_OWNER_POLL_PARITY_CHANGES_REQUESTED` findings are CLOSED for
the inspected source. No source change authorizes production install,
live parallel, real TP900s timing or Chrome performance. Overall
`V16_REVIEW_REQUIRED`; archived Google Busy branch UNKNOWN.

### Owner's new business requirement — common Google worksheet snapshots, not a warning-suppression fix

**Trigger / intent.** The Owner now requests a *program-wide shared*
60-second reuse window for the **2026**, **SHAHAB**, and **Brief**
Google worksheet contents so each separate order/module need not
download the same TSV attachment again. The canonical actual Brief
title is **`RFQ_BRIEF`**, read by `BriefReader` via
`GoogleSheetsWebService.read_brief`; `2026`/`SHAHAB` are read by
`GoogleSheetsRowReader` via `GoogleSheetsWebService.get`.
`报价输入` is a separate protected write/readback surface,
**not an approved cache member**.

**Source-read findings relevant to safety.**
- `src/launcher/google_web.py::_execute` opens and verifies the same
  protected Google UI tab/gid and downloads temporary TSV through
  `_download`. The file is deleted; no second OAuth/API/export URL,
  browser/Profile, or credential path should be introduced.
- A single `GoogleSheetsWebService` is already shared by the
  original Backend for Google reads/writes/TP; extend that canonical
  service rather than build a second service/timer/scheduler.
  Existing `_GOOGLE_GRID_LOCK` serializes UI operations and
  `GoogleSheetsRowReader.discovery_scope` has a **per-cycle**
  discovery snapshot, which is insufficient for Owner's
  *cross-cycle/cross-module* 60s reuse.
- Crucially, `GoogleSheetsRowReader.read_rows` explicitly documents
  that it **ALWAYS re-reads** for source safety. Original
  `write_brand_safely`, `current_purchase_status`,
  `write_purchase_status_safely`, quotation settlement and
  `TpCycle._revalidate` require exact current source identity/status.
  Protected `google_web._execute(write=True)` also performs its
  prewrite header check and **postwrite TSV readback**.
  Blindly replacing those reads with a 60s snapshot would weaken
  existing authorization/identity/proof against duplicate writes.
- A firm wall-clock prohibition of **all** protected reads (including
  prewrite/readback) for 60 seconds conflicts with these existing
  safety guarantees, especially the two TSV checks within one write
  transaction. CEO does **not** approve weakening readback, claiming
  cached content as newly live, or suppressing Busy/auth/UNKNOWN
  notices to meet a numerical rate. The safe minimum scope below
  applies to *ordinary read-only snapshot acquisition*; write
  verification remains mandatory, separately accounted. A literal
  hard cap including protected readback requires a separately reviewed
  schedule/settlement design and is **not implemented/approved** here.

**CEO-approved minimum implementation contract for Executor (new isolated source task, NOT Stage F):**
1. **Owner and single source of truth:** the existing
   `GoogleSheetsWebService` owns one bounded, memory-only verified
   tabular snapshot per **(spreadsheetId, exact title)** among
   `2026`, `SHAHAB`, `RFQ_BRIEF`, shared by the module reads in
   this Backend process. A single controlled monotonic clock starts
   each sheet's TTL on **successful complete validated acquisition**;
   `age < 60.0s` may reuse data for ordinary read-only discovery;
   `age >= 60.0s` permits one coalesced new acquisition on demand
   (not a timer/poller). Each sheet has independent expiry; no
   cross-spreadsheet/profile/branch mixing. No persisted TSV/SQLite,
   disk cache, credentials, personally identifying source details in
   logs or evidence.
2. **Read contracts:** introduce an explicit cache-eligible
   *read-only discovery* route while leaving mandatory original
   `read_rows`, `BriefReader.read` where used for domain
   revalidation, and write/readback contracts demonstrably live and
   unchanged. If TP discovery uses cached Brief, the later Brief
   and exact 2026/SHAHAB source identity/target must still be
   verified by the original fresh Owner gates before durable
   `MAIL_QUEUED`. A cache hit must not fabricate an authenticated
   Google session success, clear a current outage, or bypass any
   shared resource safety latch. Use copies/immutable data to
   prevent caller mutation poisoning.
3. **Protected changes/failures:** any attempted/uncertain local
   Google write affecting a cached title invalidates its snapshot
   before effects; after a confirmed write only the actual
   original readback is authoritative. Schema/worksheet/gid
   mismatches, missing/too-large TSV, expired TTL, an auth/Busy/
   protection fault, cancellation or Stop never return stale
   contents as success. Do not cache failed/partial/ambiguous
   results, and keep original bounded retries, manual protection,
   target-tab ownership and original fault/notification/UNKNOWN
   semantics. Explicitly document safe critical-read exceptions
   separately from ordinary 60s hits/misses.
4. **Bounded acquisition:** concurrent module requests for the
   same title and same process must share an existing in-flight
   ordinary refresh (single-flight) under the canonical ownership
   and UI locking policy. Never hold a market Actor worker,
   protected INSO operation, SQLite transaction or the Runtime
   source-row lease solely while sleeping for a cache timer.
   No new background thread, Playwright client or timer.
5. **Acceptance tests and evidence:** synthetic clock at
   0/59.999/60.000s; three independent sheet keys plus different
   spreadsheet IDs; same-sheet cross-module/next-cycle reuse and
   concurrency (one ordinary TSV download), mutation isolation,
   schema and malformed export rejection, failed/Busy/auth/
   protected-page invalidation, Stop, and expiry no-stale-fallback.
   Revalidate actual unchanged prewrite/postwrite/readback paths:
   change MPN/status/brand/row/Brief target inside 60s and assert
   no purchase, quotation update, TP mail or duplicate send on
   stale data. Verify old `GoogleSheetsRowReader.read_rows`
   still reads fresh where it is a mandatory guard and `RFQ_BRIEF`
   discovery/revalidation are correctly distinguished. Include
   ordinary download counts versus mandatory verification downloads
   as separate metrics, and a test proving cache hits **do not**
   repair or silence an already protected Google read failure.
   Rerun original Google Busy/TSV/protected page, Google write,
   V12/V13/TP domain, actor and full offline regressions; bind
   results to exact new app SHA + `src/` tree.
6. **Safety/deployment status:** new feature defaults uninstalled
   pending CEO Review. Do not touch live Chrome9222, manual tabs,
   production config/Vault/SQLite/SMTP or existing EXE. A reduced
   download count may *reduce* read pressure but is NOT proven to
   solve the existing Google Busy notices (historical protection
   branch unknown and `0d77be23` diagnostic not installed).
   No production diagnostic, alert suppression, release, restart or
   browser test is authorized by this Task Spec.

**Review enforcement / evidence owner:** Executor owns the minimal
reused-source change, focused and full offline tests, original
`V16_RELEASE_REPORT.md` and `docs/evidence/v16/order-resource-regression.json`
updates and same-task retirement of owned temporary test material;
CEO independently reviews exact source/diff/tests and checks
protected-write parity. Do not declare a whole-program absolute
TSV read cap or Google-warning remediation PASS when mandatory
safety readbacks remain exceptions. Stage E4 scoped PASS above
remains separate from this **`GOOGLE_SHEET_TTL_CACHE_REVIEW_REQUIRED`**.

**Overall:** `V16_REVIEW_REQUIRED`, existing installed
`04075bc` unchanged to knowledge of archived evidence (no
independent fresh production check), historical TP lateness
454.210s OPEN, Stage F NOT AUTHORIZED/NOT_RUN.


## Executor Google60s snapshot delivery — 2026-10-28 / isolated / not installed

Fetched exact remote review161e5113f5c299739afc4f6443ed656b160a34f0.
E4_OWNER_POLL_PARITY_SOURCE_PASS and native login SOURCE_PASS remain closed.
Only new GOOGLE_SHEET_TTL_CACHE_REVIEW_REQUIRED addressed; same E architecture.

Application `bb04d92f08a0ceca2075a2c17b153f2921803765`; src tree `d5f270aa8c392e9b374bfdef396d229af2d4e1e6`.
Five source files: launcher/google_web.py (ONE bounded verified snapshot cache,
original native transport); launcher/backend.py (bind original admission/Stop,
canonical live revision for outage recovery); sheets/google_reader.py and
sheets/tp_brief.py (explicit discovery/live routes); workflow/tp_research.py
(ordinary discovery reuses snapshot, manual and original revalidation live).
Two test files and original docs/modules/SHEETS.md contract; original report and
this task/JSON hold evidence, no duplicate system or completion report.

Memory-only max6 LRU entries per existing shared Backend service, exact
(spreadsheetId,title), titles2026/SHAHAB/RFQ_BRIEF only. A:G and A:Q original
schemas unchanged;报价输入excluded. Successful full validated native acquisition
finishes before monotonic TTL starts: age<60 hit, age>=60 demand miss. Same
canonical grid lock coalesces simultaneous ordinary requests; no timer/thread/
TTL sleep, no Playwright sharing. Copy results prevent poisoning. Old per-cycle
reader snapshot cannot extend service TTL. No cross-profile/service lifecycle
reuse; same process Backend modules use ONE existing service.

Mandatory get/read_rows/read_brief/BriefReader.read, owner TP _revalidate and
manual TP selection always native. Complete successful fresh source reads may
seed discovery; never consume it. Attempted writes invalidate before effects;
original prewrite/header and postwrite TSV proof retained; no optimistic cache
seeding from write return. Failure including schema/gid/missing/oversize/Busy/
auth/protection/Stop/cancellation clears all snapshots, never stale-fallback.
Shared admission/Stop checked on hits. Cache hits do not invoke recovery or
advance live revision; canonical dashboard cannot clear an outage from a hit.
No retry or notification policy change; SENT/UNKNOWN/leases/Actor bound unchanged.

Metrics (synthetic native UI, separately counted):24 query-only rows/two sheets
cross-stage2ordinary downloads (old4);4same-sheet concurrent requests1ordinary
acquisition;0/59.999s1download,60.000s2downloads. Write example1ordinary prewarm
+2mandatory prewrite/readback+1ordinary post-invalidation=4. A purchase guard has
1ordinary+1mandatory fresh; never advertise an absolute60s protected-read cap.

463PASS20.77s affected combined suite before final2Brief schema cases; final
cache suite36PASS1.19s. Exact final application full3040PASS/1SKIP123.99s.
Skip tests/workflow/test_v12_evidence_and_safety.py:56: symlink unavailable.
Ruff/diffPASS. Full src frozen; followup docs only. Initial compatibility10FAIL/
197PASS exposed recovery revision/live-seeding and old cache test expectations;
fixed source and modeled real write invalidation without weakening original
retry/mail-count assertions. New fixture import/manual-state/status assumptions
corrected to canonical contracts; no new TP business rule.10completed owned
scratch dirs retired after process exit and boundary/reparse checks.

| Requirement | Executor status / evidence boundary |
| --- | --- |
| Shared independent60s cache / demand refresh / single-flight | PASS offline36cache cases + full suite |
| Fresh purchase/quotation/TP and native write readback | PASS offline; original gates execute, no cached permission |
| MPN/status/brand/qty/row/Brief target edits inside TTL | PASS offline; original corresponding action gates reject conflict |
| Cache hit cannot heal known fault / auth or Stop bypass | PASS offline; original shared admission, no hit success callback |
| Original Busy/protected page/retry/SMTP UNKNOWN/Stop/lease/Actor regressions | PASS offline full3040/1SKIP |
| Actual production download reduction / Busy warning cause | NOT_VERIFIED / UNKNOWN, NOT a warning-fix claim |
| Install / browser / production operation | DEFERRED, no authorization and none executed |
| Stage F overlap / actual TP timing / long-term stability | NOT_VERIFIED / OPEN |

No live Chrome/Google/SQLite/config/Vault/SMTP or current EXE inspection/change.
Only isolated synthetic SQLite/migrations and fake clients/senders used in tests.
Historical04075bc version reference is archived, not newly checked. Old9f soak
untouched. No notifications suppressed or test mails sent. No new Owner browser
window/stop requested. Owner forwards original V16_RELEASE_REPORT.md for CEO
independent Review. Overall V16_REVIEW_REQUIRED; do not self-declare PASS.

## CEO independent Review — shared Google 60s ordinary snapshots (2026-10-28)

**Exact-source review basis:** GitHub branch `codex/v1-6-independent-scheduling`
at `b04d3cd5bbf412ada939e078a5f07e73f852787b`.
Its parent is application commit
`bb04d92f08a0ceca2075a2c17b153f2921803765`;
the independently retrieved application `src/` tree is
`d5f270aa8c392e9b374bfdef396d229af2d4e1e6`.
The delivery commit modifies only report/task/evidence. Independently
read `src/launcher/google_web.py`, `backend.py`,
`src/sheets/google_reader.py`, `tp_brief.py`,
`src/workflow/tp_research.py`, relevant original source/write
gates, changed tests, exact `V16_RELEASE_REPORT.md`,
`docs/modules/SHEETS.md` and JSON evidence.
Executor-submitted test results: cache 36 PASS/1.19s,
affected combined 463 PASS/20.77s (before two final Brief cases),
final complete 3040 PASS/1 SKIP/123.99s, Ruff/diff PASS.
The sole reported skip is Windows symlink availability.
These are **version-bound executor artifacts, not a CEO Windows test rerun**.

**Scoped CEO verdict: `GOOGLE_SHEET_TTL_CACHE_SOURCE_PASS`.**
- One existing `GoogleSheetsWebService` owns a six-entry
  memory-only `OrderedDict`, exact `(spreadsheetId,title)`
  keys, titles `2026`/`SHAHAB`/`RFQ_BRIEF` only;
  no `报价输入` cache. `_GOOGLE_GRID_LOCK` guards hits,
  misses and invalidation, and serialization is compatible
  with the original one-Owner browser path. Successful
  completed TSV/headers/gid proof starts monotonic TTL;
  `0 <= age < 60` is reusable, `age >= 60` triggers
  on-demand native acquisition; no background timer/thread.
  The result copy and immutable tuple rows prevent caller
  mutation from changing the cache. Existing temporary
  TSV deletion/size/row checks remain.
- Only explicitly marked discovery routes consume cache:
  `get_discovery`, `read_discovery_rows`,
  `read_brief_discovery`, `BriefReader.read_discovery`,
  normal TP discovery. Existing `get`/`read_rows`,
  `read_brief`/`BriefReader.read`, TP
  `_revalidate`, manual TP selection and original
  source-row/brand/purchase/quotation write gates remain
  live. Write attempts evict before effects; original
  mandatory prewrite/header download and native postwrite
  TSV readback are NOT replaced by snapshots.
- Cache hits call the injected shared
  `PageResourceAdmission.require_open` and original
  immediate-Stop check; never invoke `on_read_success`
  or advance `live_read_revision`. The original Backend
  dashboard outage recovery requires evidence of a
  new live read. Any observed exception (including Busy,
  invalid protected page, auth, missing/oversize export,
  schema/gid mismatch, Stop or cancellation) clears
  the service cache; no stale-on-error fallback.
  Real-source writes are still authorized solely by
  the original independent durable identity and readback
  controls, not by discovery contents.
- Changed tests include three titles, separate document IDs,
  59.999/60.000 boundaries, single-flight synthetic
  concurrency, brief schema, failed download/Busy, live
  pre/postwrite checks, in-TTL row/MPN/brand/status/qty/
  Brief target mutation, TP mail refusal, source safety,
  no fault-healing by hit, and existing integration
  download-count expectation from four to two.

**What SOURCE_PASS does NOT certify:** (1) User's phrase
"at most one read per minute across the entire program"
is **safely narrowed** to ordinary read-only discovery.
Mandatory live identity checks, prewrite and postwrite
readbacks still perform additional TSV downloads and
must remain exempt; source/evidence says this honestly.
(2) Cache-hit ordinary discovery may be up to60s old,
with original live pre-effect revalidation mitigating
wrong-row/duplicate side effects. It does not prove
Google's protective Busy warning is fixed; historical
branch is UNKNOWN and current EXE has not been inspected
or updated. (3) A max-six *entry* LRU is not an independently
measured low-memory budget: each eligible native TSV has
an existing32MiB raw-file upper limit, so worst-case
resident parsed Python rows and transient copies may
significantly exceed those file bytes. This is a
**Stage F resource-observation risk, not a current
source-code acceptance failure**; use representative
large source data during the separately authorized
long-term RSS/handles acceptance, and review a byte
cap only if measured necessary. (4) The concurrency test
uses synthetic clients, not real cross-thread Playwright.
(5) Real site/TP 900s timeliness (historic454.210s late),
full source browser overlap, SMTP delivery, prolonged
soak, DPI/game impact and actual release installation
remain NOT VERIFIED/OPEN.

**Release/state boundary:** `GOOGLE_SHEET_TTL_CACHE_SOURCE_PASS`
closes only the independently inspected cache source
implementation contract and does not reopen accepted
native login/E4 fixes or turn V1.6 into a production PASS.
Overall **`V16_REVIEW_REQUIRED`**; existing installed
version according to archived evidence remains separate,
no fresh live-process/EXE assertion. No actual
production/Chrome9222, Google, config/Vault, SQLite,
SMTP or sent state was touched by CEO; no altered
notification policy, no executable released. Executor
may proceed only to next separately scoped authorized
acceptance, not self-deploy.

**Evidence/cleanup/review enforcement:** Executor
owned the above focused and full offline runs, report
and JSON, and reports retiring ten bounded owned
scratch dirs after guarded checks. CEO review verified
Git source/evidence attribution, not runtime logs or
Windows filesystem cleanup independently. Retain the
original report and task as canonical records. If later
large-sheet memory, retained page, stale data effect,
Busy warning or source identity issues are observed,
return to **this same task** with exact sanitized
evidence instead of installing another Google client
or suppressing alerts.
