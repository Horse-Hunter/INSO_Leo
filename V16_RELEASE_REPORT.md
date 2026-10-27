# V1.6 unified release and initial production verification

## Current CEO remediation delivery —2026-10-27

**REVIEW_REQUIRED / SOURCE_FIXES_NOT_DEPLOYED. Not all V1.6 requirements complete.**
Remote review71a68f28d90ef96656cb78291c075361cb8112e2 was fetched and inspected,
not assumed present. Existing clean development checkout reused on independent
`codex/v1-6-audit-fixes`; review target remains`codex/v1-6-independent-scheduling`.
Running frozen99dd22c program was never stopped/restarted/replaced. No production
DB/config/browser session or original24h tree access in this round. Only existing
sanitized logs/prior exports and finite native process counters were read.

| Stage | Independent commit | Result |
| --- | --- | --- |
| A context/timing primary repair |a2bc2f01acbde576caf378d625788cd3e31d0d24|PASS offline, requires review; pushed before later work |
| B future cycle receipts and existing-log audit |b6187b5ffa8b279c0fc82c57e1e478a9472e2148|Source PASS offline; real TP900s and current SMTP receipt state NOT_VERIFIED |
| C page concurrency safety design |74f93dd6156d1c1a2fdb6a5d751c80382f7f089f|Design delivered; implementation DEFERRED, actual overlap NOT_VERIFIED |
| A explicit cancellation/cleanup unwind follow-up |6f8dd048248eae8875fba7a036327242b0e92027|PASS offline |
| A failure-cache isolation including identical wall time |04075bc884c9c2927e677edcbddcb43419833aef|PASS offline; final changed application source |
| D resource evidence/checklist and this report |Evidence-only delivery HEAD, full SHA in final handoff|Finite observations PASS; long-term stability NOT_VERIFIED |

### Changes and tests

Backend restores nested cycle/last-poll/research-failure-cache/pending-pause
metadata on every unwind. It never rolls back business/session changes. Each
execution starts with an empty failure cache rather than relying on distinct
wall-clock timestamps; parent cache is restored when nested work exits. Existing
outer pause wins over subsequent local pause. Observer retains ancestor waiting
stages, restores outer focus, and stores each module's own start/end/elapsed in
additive GUI DTO fields, rendered on existing cards. Unsafe cleanup invalidates
the actor; typed shared fault retains original cause; cancellation propagates
through CombinedCycle. No next purchase after STOP/shared failure and no shortened
120s safety wait. Resource ownership and fresh business permissions stay strict.

Changed application files: launcher/backend.py and workbench_snapshot.py;
workflow/service.py and v13_integration.py; gui/contracts.py, workbench.py, main.py.
Tests: launcher/test_v16_nested_context.py and test_v16_cycle_receipts.py.
No business pricing/window/transaction rule, schema, outbox semantics, dependency,
browser launcher or alternate ledger added. Task packet contains single unified
PASS/FAIL/NOT_VERIFIED/DEFERRED checklist; existing reports are historical below.

Frozen99dd22c method negative control: two new real-closure tests fail on incorrect
outer cycle identity, as expected. Repaired real launcher closure -> CombinedCycle
-> durable V12 flow / V13 engines / TpCycle covers32 cases including raw/typed
timeouts, pause, STOP, cancellation, shared DB fault, cleanup failure and pending
outer pause. Only external ports are synthetic; no real mail/site/DB operations.
115 unwind-targeted PASS14.27s; final frozen-wall cache cases32PASS9.55s and
final application source full2802PASS/1SKIP113.81s; Ruff/diff PASS. Additional
existing isolated Tk card assertions1PASS3.29s (no application-source delta)
verify waiting inquiry120s and borrowed quotation10s display independently.
No repeated broad visual simulation was added. One earlier full attempt at the
same application source had2801PASS/1FAIL/1SKIP due to existing Mock Tk initialization
`invalid command name tcl_findLibrary`; isolated existing module2PASS1.59s and the
one fresh full confirmation passed. The intermittent Tcl/global-test-state cause
is UNKNOWN, not called repaired. Skip is existing unavailable symlink capability;
isolated safety module8PASS/1SKIP0.48s confirms it, no permission rule bypassed.

### Real evidence remains qualified

Existing sanitized logs as of11:23:59 contain purchase5/quotation4 distinct cycle
tags:8SOURCE_CHANGED,104NO_RECENT_QUOTE,3PRICE_UNCHANGED,4unresolved identities.
Because the running code has the reviewed nested-context defect, these are
**log tag counts, not proof of independent correctly attributed module cycles**.
No newly confirmed procurement or quote Sheet-write/readback success was found.
No identity/state was changed to force success. Current production TP900s run
begin/end receipts are absent: NOT_VERIFIED, not inferred from four historical TP.

Future-source logging now records every module begin/terminal phase, cycle,
monotonic elapsed and next-delay on the existing bounded rotating log, including
empty TP. Strict allowlists suppress raw bodies/identifiers/nonfinite values.
Three real empty TpCycle engine invocations900s apart PASS offline; no historical
SENT used as proof. `completed` means cycle ended, not successful external orders.
This instrumentation is not in the running EXE and cannot backfill its history.

Prior exported SMTP evidence as of10:25:26:139SENT, historical138 unchanged then;
one new PURCHASE_EXCEPTION recipient accepted by transport. Current SMTP/UNKNOWN
state was not reread from productionDB, mailbox final delivery not established,
and real restart idempotency DEFERRED because restart is prohibited this round.
Existing offline SENT/UNKNOWN/atomic claims remain covered by full regression.

True webpage parallelism is not implemented. Separate design
`docs/V16_PAGE_CONCURRENCY_DESIGN.md` identifies exact-target page-event correlation,
same-URL reuse, sync-object thread affinity, shared auth/pacing, per-order exclusion
and callback/context gaps. Preferred bounded independent sync-client actors share
one protected Chrome; INSO/Google/writes remain exclusive. Broad async migration
cost is higher. No locks removed, profile duplicated or fake overlap timeline
submitted. Actual browser validation cannot commandeer live session under this
round's explicit prohibition; C remains open.

### Finite resource evidence, not a stability certificate

Read-only GetProcessTimes/memory/handle/process-tree observations only. Main window
11:29:31–11:35:31:360.36s,7samples/60s; application CPU0.20361–0.24420%host,
RSS138.45–141.42MiB,Private108.61–111.36MiB,9native threads. Handles5586→5700→
5708→5736→1111→1133→1121. A type snapshot confirms owning applicationPID74176
5770→1131handles and5196→576semaphores (4620released). This repeats earlier transient
release evidence; exact allocating Python/library/native objects remain UNKNOWN.
No speculative code fix or forced collection was introduced.

Observer:0%observedCPU/~20.75MiB RSS/1thread/128handles. Playwright driver observed
in5samples, then absent; surviving-cohort CPU0–0.06024%host. Missing/exited cohorts
do not mean zero total cost. First inventory matched inherited9222 flags on child
commands, so Chrome root attribution there was ambiguous and not used. A separate
60.375s/3sample ancestry-resolved window proves one canonical browser root and
separate browser/GPU/renderer/utility/crashpad process groups; all reported0CPU in
those two short comparable intervals. This is not active Research/game evidence.
Process-role memory counters are included in JSON; RSS sums can double-count
shared physical pages. No raw process command lines, page/customer data saved.
Offline regression ran on the same host during part of collection; this is not
an isolated idle benchmark. GPU utilization, frame rates, per-site attribution,
strict continuous multi-cycle bounds and unattended V1.6 stability NOT_VERIFIED.

New EXE real menu/tray/normal exit, real stop/restart recovery,100%/150%systemDPI,
and GUI/live-ledger consistency remain DEFERRED/NOT_VERIFIED per checklist.
Original9f/70956 result is deliberately not collected by this task and cannot
certify V1.6. Existing V1.5/V1.4 rollback assets/compatible-ledger strategy retained;
not re-certified against a newly installed program because no program installed.

### Proposed later deployment (not executed; separate Owner permission required)

1. CEO review P1 and observability commits, with C explicitly deferred. They are
   source fixes, not permission to overwrite running production.
2. Obtain a normal stop/install window; drain current effects, verify UNKNOWN,
   take fresh verified current ledger/config/vault backup and exclusive mutex.
3. Build only reviewed source using the single existing Windows flow; frozen
   selfcheck/scan/assets PASS. Preserve working V1.6 and V1.5/V1.4 rollback assets.
4. Asset-only install; no assumed schema migration or order-state reset. Verify
   current ledger/SENT/immutable commands before/after. Start idle first.
5. Resume existing authorized configured business without new per-order approvals.
   Verify real module-cycle receipts, empty TP and actual900s deadlines; confirm
   GUI/ledger and external results only when naturally eligible orders occur.
6. Test live tray/ordered exit/restart in the approved window; run finite multi-cycle
   resource and long-term checks on reviewed source. Never relabel old9f soak.
7. Rollback if necessary uses current compatible ledger, never restores old
   pre-effect DB. Do not resend historical SENT or reset UNKNOWN to manufacture PASS.

Recommendation: a reviewed replacement is needed to deliver P1 fixes/receipts,
but **do not install in this task**. No unconditional V1.6 completion or webpage-
parallel/long-term production PASS is claimed. Evidence `docs/evidence/v16/audit-*`.

---
## Historical initial release snapshot (unchanged facts at original timestamp)

Status: **PRODUCTION_INSTALLED_RUNNING / REVIEW_REQUIRED**.
As of 2026-10-27 10:27 Asia/Shanghai. This is not a claim that all three
external write chains or long-term unattended operation have passed.

## Version and installation

- Owner baseline: `669fe6ada3a450eaef5f74532a371d6fb55ffd01`.
- Built application source: `99dd22c43fd83852dc1d45d13c4cfed46b0ebe0d`.
- Branch: `codex/v1-6-independent-scheduling`.
- Installed: `D:/Program_Leo/INSO_Leo/dist/INSO_V1.6/INSO_V1.6.exe`.
- EXE SHA256: `16E38F30E253041F7ED41E0447DEF744F6912D7B310F6DBDF616556CDBDC8B82`.
- Canonical Windows script/spec reused; dependency selfcheck, release scan,
  installed selfcheck and idle GUI selfcheck PASS. All2875 assets matched.
- Real versioned Windows window enumerated. PID74176, existing exit observer84608;
  started09:54:40 with `--start-inquiry`. No concurrent V1.4/V1.5 business instance.
- Inquiry/quotation/TP enabled; independent configured periods900/900/900s.
  Default values retained independently, not a combined15-minute wait.

## Reuse, implementation and changes

Task packet contains reuse matrix and design. Existing WorkflowRuntime gains
three in-memory monotonic deadlines and fixed browser actor ownership. Same
poller/worker threads, mutex, SQLite business ledgers, adapter composition,
quote/inquiry/TP contracts and notification outbox remain canonical. Shared
browser work queues on one owner thread; existing SMTP worker may overlap it.
Only closed-row120s safety waits lend browser time to other due modules; no
shortened wait or order cap. Local module pauses/backoff are isolated; shared
database, security and ownership errors propagate. Shutdown/manual gates remain.
GUI exposes per-module plans and V1.6 title/sidebar; original five pages retained.

Changed files: workflow/service.py, v12_notifications.py, v13_integration.py;
launcher/backend.py, workbench_snapshot.py; core/app_paths.py; gui/app.py,
workbench.py; existing Windows build script/spec/entry. Corresponding workflow,
launcher and GUI tests plus task record. Paths are relative to `src/` except
tests and packaging/scripts. No Research pricing/window/MPN/FX rule changes,
new dependencies, timer daemon, browser manager or business state system.

## Backup and rollback

Fresh protected backup:
`D:/Program_Leo/INSO_Leo/dist/release-backups/INSO_V1.6-before-20261027T015035Z`.
Canonical verified SQLite backup, full private table fingerprints, config and
opaque encrypted vault verified before install. Canonical migrations executed
on copy: zero schema/row delta; production migration NOT_NEEDED, not executed.
Install before/after full ledger comparison identical. FourTP tasks, sixTP-SENT,
138 historicalSENT and all immutable messages preserved. Ongoing read-only audit
still confirms those exact historical rows/commands unchanged.

V1.5 remains intact at `D:/Program_Leo/INSO_Leo/dist/INSO_V1.5`, EXE
`DA21769649159216BB66604AB601F051C55C192BFA62A3F09991F5EE03BA9A4A`;
2875 assets verified. V1.4 and earlier verified rollback backup remain intact.
V1.6 runtime junction targets the original `dist/INSO_V1.4/runtime`.
Config changes restricted to `v16_enabled=true`, `tp_enabled=true` and independent
periods; quotation already enabled. Research config and vault unchanged.

Rollback: stop V1.6 normally, restore backed-up config (including TPfalse), then
launch unchanged V1.5 against the **current compatible ledger**. Never restore
the pre-live database after new mail/submissions; that would forget receipts.

## Actual production results and limits

| Module | Actual evidence | External result |
| --- | --- | --- |
| Inquiry procurement | Three logged cycle IDs; four SOURCE_CHANGED outcomes across two protected orders | Conflicting source identities stopped; no new SAVED procurement confirmed |
| Quotation follow-up | One logged cycle:31 NO_RECENT_QUOTE,1 PRICE_UNCHANGED,1 SOURCE_IDENTITY_UNRESOLVED | No fabricated prices or guessed identity; no new quotation Sheet write confirmed |
| TP | Enabled in canonical three-module runtime; preflight found4already_processed,0new candidates | Four historical tasks/sixSENT unchanged; no new TP mail. Independent current-cycle completion receipt NOT_VERIFIED |

One new PURCHASE_EXCEPTION notification command, one recipient recordedSENT
(138→139 total). This means existing SMTP transport accepted the notification;
mailbox delivery/read receipt is NOT_VERIFIED. No new UNKNOWN/PENDING recipients
observed. No ad-hoc test mail, historical replay, payment or expanded transaction
authority. Existing ERP gate covers procurement inquiries, not payment/contractual
purchase orders. Existing identity exceptions are per-task stops; healthy checks
continue. Normal future eligible tasks remain authorized under Owner's rules.

Real canonical read-only preflight: six sources SUCCESS, INSO quotation read63
rows, Google source/quotation metadata and payload read PASS. Pending sources3/0;
RFQ85rows, fouralready_processed TP. Existing tabs preserved, no leftover owned
probe tabs; protected Chrome/profile not restarted. These results are connectivity
evidence, not successful real purchase/Sheet-write/TP-mail acceptance.

Runtime diagnostics exist in shared `runtime/logs`, current receipt
`runtime-e3408661f02d4adc965f62ce67f97a01.state.json`; sanitized rotating business
log retains inherited filename `INSO_V1.3.log`. Source includes bounded GUI logs,
bounded views and existing file rotation. Do not infer application version from
that inherited logfile name. No fatal native receipt or DB integrity error seen.

## Tests and short performance

Full offline regression2759PASS/1SKIP,100.86s; Ruff and diff check PASS.
Independent deadlines/thread ownership, SMTP overlap/atomic races, SENT/UNKNOWN,
stop/manual safety, source snapshot invalidation, website isolation and individual
UI deadlines covered. Existing legacy readiness timing test failed intermittently
in earlier runs; cleanup now prevents leaked workers after failures and diagnostic
assertion retains exact stacks. Backend53PASS and subsequent full runs PASS;
historical timing cause remains NOT_REPRODUCED, not called a business fix.

Synthetic UI45layouts/90recovery cycles and100/500/1000orders PASS; zero callback
errors. Synthetic screenshot supplied, no real customer contents. Versioned live
window exists; current Windows control read hit application-approval timeout.
Live menu/tray/exit interactions on this newEXE NOT_VERIFIED, not replaced by
synthetic evidence or prior V1.5 Owner tray confirmation.

Two finite native-counter samples, no permanent monitor:

| Period | Duration | HostCPU | RSS MiB | Private MiB | Threads | Handles | GDI/USER |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Active quote queries |121.313s|0.33085%|131.46–135.02|101.13–105.11|9–11|3982–5118|136/258 |
| Later batch boundary/next check |121.75s|0.28956%|135.23–137.87|105.63–107.93|10–11|933–1041|136/258 |

One finite type snapshot between windows5327handles, chiefly4762semaphores;
later fall below1041 rules out extrapolating the earlier rise as proven unbounded
leak. Root lifetime attribution and multi-cycle/long-run bounds NOT_VERIFIED.
Observer0%CPU,~20.75MiB RSS,1thread/128handles. Excludes Chrome/site process costs;
does not prove game FPS or idle/tray performance. No source fix was invented to
hide the transient peak. Original V1.5 high-CPU root cause also remains UNKNOWN.

Protected original24h PID70956 still running source9f; last heartbeat here
~22h52m, zero guards/callbacks, maxgap60.11s. Not24h PASS. That test cannot certify
V1.6. System100%/150%DPI, Chrome gaming impact and V1.6 long-term operation remain
NOT_VERIFIED. No current fatal integrity/resource blocker established, but full
three-module external-success acceptance is incomplete for lack of eligible
successful actions and independent TP completion telemetry.

## Audit recommendation

CEO review implementation and actual rejection/notification evidence, especially
browser-resource serialization, SMTP worker ownership and known identity holds.
Keep truthful distinction: installed and live checks running; zero newly confirmed
purchase/quotation writes, no new TP candidate. Do not mark all end-to-end live
chains PASS or V1.6 long-term unattended acceptance PASS. Owner need not approve
ordinary configured tasks again. Required correction of held source identities
must use existing fresh verification; never reset their state to force a result.
Evidence: `docs/evidence/v16/`; task record provides detailed scope/test log.

## 2026-10-27 remaining execution — reviewed-source installation preparation

Current instruction is the Owner's remaining-needs order, superseding the prior
round's blanket evidence-only restrictions while preserving the explicit live
replacement boundary. Remote CEO PASS ee49203dbae39e79eca1f1c90164f643ba2fe03c
fetched and fast-forwarded in the existing clean checkout; no new worktree.
`git diff 04075bc..HEAD -- src` empty. P1 is accepted and is NOT reopened.
Reviewed application04075bc remains the **only proposed installation candidate**;
future page-parallel increments must not be included without independent review.

Preinstall check: existing release Python at
D:/Program_Leo/INSO_Leo/.worktrees/v1-4-order-mail-inspection/.venv-release/Scripts/python.exe
imports PyInstaller/customtkinter/playwright and initializes Tcl8.6.15. No dependency
installed. Ordinary global Python first lacked tzdata during test collection;
reused release environment's existing zoneinfo via command-local PYTHONTZPATH,
then targeted reviewed-path43PASS13.91s. Prior reviewed full2802PASS/1SKIP remains
applicable because source unchanged; no repeated full suite without source delta.
Canonical scripts/build_windows_release.ps1 -Version1.6 -BuildOnly with explicit
PythonExecutable is the sole build path; no new launcher/release system.

Read-only installed identity: main74176 / observer84608 still present, actual
D:/Program_Leo/INSO_Leo/dist/INSO_V1.6/INSO_V1.6.exe SHA256
16E38F30E253041F7ED41E0447DEF744F6912D7B310F6DBDF616556CDBDC8B82.
No stop/restart or production config/SQLite/browser access. V1.5/V1.4 EXE paths
and before-20261027T015035Z backup are present; presence is not a fresh full rollback
integrity certification. Fresh backup and full manifest verification wait for stop.

### One-time proposed installation window (NOT AUTHORIZED yet)

1. Stop admissions using existing normal UI stop/drain, let in-flight effects
   settle, then normal exit and confirm both process exit and exclusive mutex.
   If current effects cannot settle/UNKNOWN or ownership uncertain, preserve state
   and stop affected installation step; never force-kill Chrome or replay effects.
2. Fresh canonical SQLite backup after exclusive access; integrity_check, full-table
   and immutable-command/recipient fingerprints; preserve SENT/UNKNOWN/PENDING,
   original4TP/6TP-SENT, all newer naturally produced effects. Opaque credential
   and config backups verified locally without exposing contents. Record junction.
3. Canonical single formal build from exactly reviewed04075bc, frozen dependency
   selfcheck, artifact scan/asset hashes. No page-parallel code in this artifact.
   Do not assume migrations; test existing canonical compatibility on backup copy.
4. Asset-only EXE/_internal replacement after verified rollback backup. Keep runtime
   junction/current compatible ledger, V1.5/V1.4 programs and protected Chrome.
5. Installed selfcheck, safe idle startup, version/assets/GUI/log/ledger comparison,
   single-instance check. Restore already-authorized existing three-module business
   only after these checks; no expanded recipients/permissions/forced old tasks.
6. Observe real per-module receipts, especially emptyTP900s start/end and UI,
   natural eligible outcomes, current SMTP and finite multi-cycle resources.
   External success requires result/readback, SMTP acceptance is not delivery.
7. If startup/integrity/safety fault: stop affected work normally and restore
   prior verified **program assets only against current compatible ledger**;
   never restore stale pre-effect DB or reset historical mail statuses.

Impact: automatic checks pause during drain/build/installation/idle verification;
no duplicate production instance. Window length is measured, not guaranteed.
Unique Owner action: authorize this normal stop/install/resume window. If existing
UI cannot be normally exited by available tools, Owner uses tray Exit once.
No production replacement, migration or backup was performed by preparation.

## 2026-10-27 execution update — installation AUTHORIZED, awaiting normal exit

Owner explicitly authorized the proposed single stop/backup/build/install/idle/
resume-business window. The earlier "NOT AUTHORIZED yet" deployment boundary is
**SUPERSEDED by that authorization**, not by source tests. Actual replacement has
**NOT occurred**: last exact process check still shows74176(main)/84608(observer),
installed EXE16E38F30...DC8B82 unchanged. Windows skill tool found/restored the one
correct V1.6 window, but screenshot failed twice and accessibility exposes only
unlabelled Tk panes. No guessed click, force-kill or alternate UI automation.
Owner asked only to Safe Stop, allow drain, then tray Exit; authorization itself
need not be requested again. Once clean exit is verified, continue the approved
single installation workflow; do not ask approval at each normal check.

Reviewed artifact must use **04075bc application / 1b19390298c6151e08d1e513a2a153ddcae2c1cf
checkout**. No P1 rewrite. All43release-lock packages match in existing release
Python, Tcl8.6.15 ready. Necessary43targetedPASS13.91s; prior reviewed2802PASS/1SKIP
still applies to unchanged candidate. No replacement build has been made while
normal exit is outstanding; no production backup/migration/state change performed.
V1.4/V1.5 and existing backup assets are retained, current-ledger-only rollback
strategy unchanged. Fresh integrity/recipient/immutable-command verification is
still required after drain; old139SENT statistics are not current receipt proof.

### Independent C prerequisite — exact native page identity (NOT installed)

Separate source49677b7e658034f687fa0ed73c5bb5ff6bfadf3d, compatibility follow-up
f49d78526f6c30cc57b710f466883792ff574e0d. Only production-source change is
research/cdp_pages.py: random per-create marker filters foreign page events,
then page-specific CDP Target.getTargetInfo must match the exact createTarget
response before assigning ownership. Failure closes only that exact created
native target. Never selects first same-site page or clears other actor pages.
After proof, remove creation fragment using history.replaceState; preserve
window.name ownership and exactabout:blank used by existing initial-navigation
failure and last-tab guards. No Chrome launch, context/profile clone, adapter
pricing/FX/month-window/outbox/transaction change, source allowlist expansion,
new dependency, timer, daemon or production toggle.

Initial full test exposed real compatibility issues in this **uninstalled** delta:
creation fragment broke exact-blank guards; fixed in follow-up before delivery.
Test fixture event/native-target protocol updated in tests/research/background_targets.py,
test_cdp_pages.py and test_icnet.py. Final full **2806PASS/1SKIP110.02s**;
additional positive ownership/blank tests **12PASS0.57s**; scoped Ruff/diff PASS.
One additional test-only positive case was added after full run; no further
application-source change. Native browser behavior is not yet tested.
Global interpreter initially lacked tzdata/pypdf; reused existing release packages
with command-local PYTHONPATH, without installing anything. First release-Python
full also lacked pytest in a subprocess; corrected inherited environment, not
product source. All earlier failed attempts remain classified in small evidence.

**This closes only an offline ownership prerequisite.** Finite independent sync
actors, cross-module order/resource arbitration, auth/pacing integration, actual
web navigation overlap timeline and real-browser acceptance remain **NOT_IMPLEMENTED /
NOT_VERIFIED**. No claims based on thread/callback/sleep overlap. This independent
increment cannot be mixed into already approved04075bc installation. It requires
its own CEO source review and later safe browser acceptance window.

Existing unified checklist remains authoritative. Stage2 is now
**AUTHORIZED_WAIT_NORMAL_EXIT / NOT_DEPLOYED**, stages3/5 not falsely passed;
TP900s real receipts and currentSMTP/restart/GUI/long-run evidence wait for the
reviewed deployment. Old9f soak remains closed and is not restarted. Small new
summary docs/evidence/v16/remaining-preinstall.json; final/failed test stdout
retained locally,391424417bytes of completed owned test scratch retired under
original test-owner identity, no ACL changes or protected-directory cleanup.
