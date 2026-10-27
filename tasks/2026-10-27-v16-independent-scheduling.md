# V1.6 independent scheduling and Owner-authorized production release

status: IN_PROGRESS — CEO71a68f2 audit corrections; production untouched
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
| A nested execution identity, pending pause and cache | PASS (offline; review required) |24 real-closure cases; frozen-method negative control fails both quote/TP as expected |
| A independent GUI timing and waiting | PASS (offline; review required) | Ancestor waiting interval preserved; additive per-module start/end/elapsed displayed |
| A cleanup/shared fault, STOP and120s minimum | PASS (offline; review required) | Actor invalidated on cleanup failure; no next purchase after STOP/shared fault |
| A full regression | PASS |2783passed/1skipped110.68s;63 targeted11.38s;Ruff/diff PASS |
| B real TP independent900s begin/end | NOT_VERIFIED | Existing deployed source emits no independent TP completion receipt |
| B future-source TP cycle receipts | PASS (offline only) | Three actual empty TpCycle calls at independent900s; no orders/mails used as substitute |
| B new purchase success | NOT_VERIFIED | Prior source-conflict holds are not successful procurement |
| B quote/Google write/readback success | NOT_VERIFIED | Prior no-recent/unchanged/identity refusals, no forced writes |
| B SMTP acceptance vs mailbox delivery | PASS / NOT_VERIFIED | Prior accepted1 recipient; mailbox final delivery unknown |
| B real restart idempotency | DEFERRED | Current command forbids production restart/DB operations; offline safety regression retained |
| C genuine overlapping page work | NOT_VERIFIED | Must not describe serial actor or fake callback as webpage parallelism |
| D multi-cycle resources/semaphore ownership | NOT_VERIFIED | Prior2x121s aggregate samples only; no demonstrated persistent leak |
| D main/observer vs browser/game | NOT_VERIFIED | Existing counters exclude Chrome/game costs; no game launch allowed |
| D live EXE menus/tray/normal exit | DEFERRED | Cannot close or control running production this round |
| D100%/150% systemDPI | DEFERRED | No Owner display-setting changes; prior widget scaling not substitute |
| D GUI/ledger, recovery/manual consistency | NOT_VERIFIED | Offline checks do not certify current production state |
| D long-term V1.6 unattended stability | NOT_VERIFIED | Old9f/70956 cannot certify V1.6 |
| D V1.5/V1.4 rollback preservation | PASS (prior evidence) | No current production/backup modification; retain current compatible ledger |

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
No live restart, no repeat mail, no new production/browser/config query.
