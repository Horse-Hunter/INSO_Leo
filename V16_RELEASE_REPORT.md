# V1.6 unified release and initial production verification

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
