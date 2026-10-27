# V1.6 independent scheduling and Owner-authorized production release

status: IN_PROGRESS
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
- [ ] independent deadlines/fairness, safe resource arbitration, shutdown and manual races
- [ ] SMTP parallel with browser, same-order serialization, SENT/UNKNOWN protection
- [ ] per-module failures/backoff and GUI real schedules/version, bounded resources
- [ ] full offline and synthetic race/fault regressions, real read-only adapters
- [ ] canonical frozen selfcheck/scan/manifest, rollback and database/config/vault backup
- [ ] stop V1.5 normally, verified V1.6 shared-runtime install, all-module production
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
Full source/governance audit in progress; no production writes or new execution.

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
