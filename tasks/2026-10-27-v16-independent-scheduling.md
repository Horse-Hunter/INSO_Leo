# V1.6 independent scheduling and Owner-authorized production release

status: REVIEW_REQUIRED — reviewed04075bc installed; real cycles recorded; true parallel actors incomplete; current read-only window safely stopped
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
| C page concurrency implementation | DEFERRED actors; isolated prerequisite implemented |67be3f7 cleanup fault follow-up; exact target proof native PASS; navigation ownership NOT_VERIFIED |
| C actual webpage overlap/same-order queue timeline | PASS native navigation overlap only; NOT_VERIFIED business/order exclusion | SameChrome/two own pages overlap0.125/0.532s; full actor arbitration NOT_IMPLEMENTED |
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
