# V1.5-B workbench and lightweight observation

status: REVIEW_REQUIRED
authority: Owner pasted V1.5-B task, 2026-10-25
branch: codex/v1-5-tp-research

## Second-review correction packet (2026-10-26)

Authority: Owner + CEO e984f6bcf55bb56040573e9268f568fd489a90ea.
Only synchronize actual idle/manual window and conservatively project TP hints.
Reuse the existing wait, _next_poll_at, _poll_idle/_poll_gate, canonical permission
checks and TpStore manual states. Publish one shared wall deadline at actual wait
entry/reset; remove pre-TP scheduling timestamp and clear it on wait exit. No new
scheduler/worker/dependency. The wait still uses the original monotonic900 seconds.
Reuse TP task_key plus canonical source identity on the existing projection worker
to link ordinary orders to an existing TP DTO; exact MPN/quantity guard, never MPN
alone. Hint uses only snapshot fields; mirror existing MAIL_QUEUED/FAILED and
delivery None/SENT/PERMANENT_FAILURE states. Fresh durable gates remain unchanged.
Synthetic verification: TP0/5/10/20m at wait boundaries and mid-window, safety
refusal before cleanup/during manual/after stop, reset, UNKNOWN/duplicate guards,
ordinary/unlinked/linked TP hints, SENT/UNKNOWN/in-flight/stale snapshots, full suite.
Window publication derives both displayed and canonical permission time from the
original monotonic deadline, including a synthetic30-second business-lock delay;
only the immutable memory view is updated, no new durable-state scan. Detail
signature includes memory hints so linked TP changes refresh ordinary-row buttons,
while unchanged hints preserve widgets. Canonical can_order_action/request and
purchase/recipient protections remain untouched.32 new test cases; four old full
wait stubs call publication explicitly without weakening their assertions.
No real business, credentials, mail, packaging/deployment. Other business deltas
retain independent review status. Deliver original branch, REVIEW_REQUIRED.

Second-review completion: final targeted119 PASS17.53s; full2733 PASS/1 SKIP105.02s;
Ruff/no-cache and diff whitespace PASS. Both final runs contain no SMTP attempts.
Evidence: docs/evidence/v15b/pytest-review2-{full,targeted}.txt. Intermediate
six wait-stub failures and one10-second exit timeout are disclosed in the report;
timeouts/guards were not relaxed. Final ordinary-detail hint-change assertions
and unchanged-widget reuse both pass. No workflow/research/source algorithm or
RFQ008 test change. Owned review2 temp artifacts retired after evidence collection;
original worktree retained, no deployment/profile/runtime/production DB changes.
revision_authority: Owner/CEO first UI review, 2026-10-26, a7aaf615449b39f9c3b3606b61c4ffed19aa19e0 CHANGES_REQUESTED

## First-review correction packet (2026-10-26)

Only P1-A actual wait countdown, P1-B deferred recovery observation, and P2
nonblocking details. Keep six pages, algorithms, serial900-second wait, actual
manual permission gates, three-hour recovery/safety rules and TP default false.
No production data/browser/mail/build/deployment. Earlier business deltas retain
their independent review status; this task does not approve them.

Reuse audit: _wait_between_polls owns the true monotonic wait and resets it after
manual commands; _next_poll_at also gates manual requests and must remain intact.
Extend existing RuntimeObservation with a read-only actual wait plan; no scheduler.
End observation at entry to that same wait, including deferred failures. Reuse
_site_outages for source text and existing error classification unchanged.
Details currently call SQLite-backed can_order_action four times on Tk. Replace
display checks with an in-memory request hint; actual request_order_action and
execution gates remain authoritative, no cached authorization or new thread.

Verify synthetic TP0/5/10/20-minute durations against actual900-second wait,
two consecutive recovery rounds, manual/reset/stop constraints, delayed permission
and SQLite business-lock contention during detail opening, plus full regression.
Update V15_UI_UPGRADE_REPORT.md, commit/push original branch, REVIEW_REQUIRED.

Revision completion: full2701 PASS/1 SKIP104.27s; targeted81 PASS11.64s,
Ruff/no-cache and diff whitespace PASS. Final tests show no SMTP attempts.
Real Tk + synthetic exclusive SQLite/business lock:771.928ms; simulated2s
permission delay:122.675ms, no blocking permission call from detail rendering.
Original safety/outage/manual tests retained; no research/workflow algorithm or
RFQ008 test edit. Old long-performance samples are prior-candidate evidence only.
Final review transcripts retained under docs/evidence/v15b/pytest-review1-*.txt.
Owned review temporary artifacts retired after collection; no production change.
starting_head: 97212f40eb87cad5d0069f0c1f21c4cef71c481b
reviewed_anchor: a29c1466fc5f246636998919a2abd443960894cf

## Scope / provenance

Reuse the current independent worktree; no reset or overlay. Commits since the
anchor contain later currency/mail corrections and Owner-authorized full-query,
dual-recipient integration/local release. Their review status is REVIEW_REQUIRED;
preserve those deltas, do not represent them as newly CEO-approved. Two original
broad-suite failures were changed in earlier ea53706 to assert the independently
reviewed recovery policy and fake SMTP; do not modify those tests in this task
or conceal the original baseline evidence. Starting full suite previously2666
PASS/11 SKIP; rerun and report actual new results.

This task authorizes source, synthetic data/UI/performance tests and Git only.
No production files/config/DB, deployed app, CDP, website, SMTP, purchase, build
or deployment. TP default must be false, including frozen source default; explicit
configuration remains the only opt-in. Already installed release is untouched.
No new dependency, permanent thread, browser or scheduler. State snapshots are
observation, never a second workflow state machine or safety bypass.

## Audit / reuse design (before implementation)

| Existing capability | Direct reuse | Necessary extension | Regression risk |
| --- | --- | --- | --- |
| gui.app / CustomTkinter / ttk | root, action handlers, resizable table, details, safe close/tray | compact nav, page containers, module cards, filters and collapsible details; keep one app | lost actions/resize/DPI |
| contracts.RunSession/Order/HealthReport | existing IDs, statuses, prices and safety enums | additive immutable module/round snapshots and verified source metadata | invented stage/identity |
| MainThreadEventQueue / ring logs | same callback handoff and Tk main thread | bounded queue, status coalescing, bounded drain; event-driven redraw | losing actionable events |
| backend existing poll/manual thread | original execution order, source callbacks and boundaries | thread-safe read-only cached projection, timestamps/monotonic durations | schedule or fault semantics |
| get_status/history/v12 state | existing canonical projections and state APIs | populate presentation cache on existing workers; GUI ticks never query DB/Excel | stale/false success |
| manual actions/login/mail/Excel | can_order_action, request_order_action, existing report feedback | expose same actions in details/settings, no new side effects | bypass UNKNOWN or edit wrong column |
| existing tray and after lifecycle | minimize/restore/stop controls unchanged | reduce hidden visual updates, sync latest snapshot on restore | business paused accidentally |

Observed old layout: header + two operation/count cards + one results/detail
split + health bar. No page navigation; log callback discards display. Tick1s
calls get_status (SQLite all-items/business completion), history (TP SQLite),
then get_v12_order_state for every row, even unchanged. Order-ID changes delete
and rebuild all rows. Status callbacks can duplicate the same refresh each tick.
next_poll_at is set before TP completes, and missing next time renders imminent
polling. Detail reconstructs controls on selection. Unbounded SimpleQueue is a
potential hidden-window backlog. Existing log ring is1000; reuse that bound.

Layout: graphite shell, narrow left nav, overview3 cards + actual active task;
one reusable local order table shared between task/research views, right details,
bounded exception/log views and read-only settings with existing supported actions.
No decorative animation/percentage. Missing historical timing/TP offers remain
unavailable. Unverified identities remain separate. Cache/pagination bound1000
loaded rows,200 rendered rows; filtering never calls backend/network/SQL.

Measurement: same synthetic-only backend/workload and Python/host for old/new
UI. Capture own process CPU/RSS/private bytes/threads/handles/GDI/USER, tick/
page/table timings; sample only in diagnostic harness. Actual10min idle and30min
foreground plus tray,100/500/1000 rows and repeated operations.24h only if truly
completed; otherwise NOT_VERIFIED and later acceptance condition. Keep synthetic
screenshots/evidence only. Final report V15_UI_UPGRADE_REPORT.md; REVIEW_REQUIRED.

## Execution / verification

Implemented six-page workbench, additive immutable snapshot, observed round/site/
phase timing and bounded display. Reused the business actions and safety gates,
browser/source/FX/SMTP/store/scheduler. TP default is explicitly false per this
task. Installed V1.5 and production state untouched. One optional one-shot local
history loader exits after loading; no new resident business thread. Start and
safe close respect its lifetime.

Fixed CTk scaling restoring old grid positions and a bucket-only layout cache
retaining initial tiny wrap widths. Actual size/row/wrap checks cover this
regression. Source frozen for final measurement; no follow-on business development.

Final source full suite2693 PASS/1 SKIP in103.07s; Ruff/no-cache and diff whitespace PASS.
54 page/size/widget-scaling combinations and90 failure/recovery/detail/tray cycles
PASS, zero Tk callback errors. callbacks5, Python threads2, GDI57; USER282->279;
handles320 stable; private bytes plateau after first30 cycles.
Late projection audit reproduced ordinary notification UNKNOWN being admitted to
the completed filter despite Research completion. Display-only correction covers
notification UNKNOWN, save UNKNOWN and ambiguous reconciliation; persisted
business/Research state and delivery gates are unchanged. Full2679-case suite ran
after this correction. Long benchmark predates late typed sorting, two restored
detail labels, UNKNOWN projection, branding and queued explicit startup fixes.
Evidence records hash deltas and reconstructible window-code patch; final-source
smoke and full regression cover the final code, not a new30-minute run.
Static and diff whitespace checks PASS. Original RFQ008 baseline tests unchanged;
earlier failing parameter expectations changed before this task in ea53706, with
provenance retained in the report, not claimed as UI fixes.

Prior candidate completed42min. Final display correction is measured again in
separate600s idle and1800s foreground+120s tray processes. Old UI measured in this
same session/script/source snapshot for comparison. Do not substitute a short run
or sample span for duration.24h, real OS DPI changes and production/browser/game
load NOT_VERIFIED. Evidence is synthetic only, under docs/evidence/v15b.

Observed earlier full-suite stop timeout/22-failure cascade is disclosed in the
report; RFQ008 tests untouched. Launcher tests now inject fake login instead of
default credential lookup. SMTP blocking lasts for the whole test process,
including fixture gaps; no real message sent. Real Tk extra test is isolated in
a subprocess with installed Python Tcl; deployed Tcl and permissions untouched.
Explicit startup queues once through existing GUI tick while history loads;
default idle and close behavior preserved, no new scheduler.

Cleanup complete: all owned D:/Program_Leo/INSO_Leo/.tmp/v15b-* artifacts
retired after evidence collection, no live test Python process remains. Retained
only necessary synthetic screenshots, JSON and final pytest transcript in Git.
Reused original V1.5 worktree; no second worktree, deployment or CDP change.


## CEO independent second review — 2026-10-26

**CHANGES_REQUESTED (one outstanding P1 UX/permission-consistency issue; narrow P2 hint). LIVE RELEASE / REAL SMTP / DEPLOYMENT NOT AUTHORIZED.**

Reviewed exact implementation SHA `c5610953fb77d6c7c8f43bddb3e73bab760e3351` compared to `a7aaf615449b39f9c3b3606b61c4ffed19aa19e0`, the 11 changed file paths, full UI/launcher/observation source and targeted integration tests. The branch matched that commit before review. Executor's transcripts show **2701 PASS / 1 SKIP** full and **81 PASS** targeted. CEO did not rerun Windows/Tk/pytest or real sites, DB migration, SMTP, packaging or game load; old long-performance results do not measure exact current final SHA.

**P1-A (visual scheduling): ACCEPTED.** The existing monotonic 900-second `_wait_between_polls` remains the actual scheduler. It now enters a separately observed read-only `planned_check_at` at the real wait boundary, after TP/cleanup; `scheduling` uses this read-only plan, ceil()s positive fractional seconds and does not claim an imminent poll during unclosed work. Synthetic tests cover TP delays of 0/5/10/20 minutes, actual virtual wait loop and stop/manual reset.

**P1-B (recovery wait): ACCEPTED.** The same actual wait-entry observation closes execution timing on deferrable Google/INSO failures, reports a recovery site drawn from the existing outage state, and leaves the underlying deferral, three-hour policy, and GLOBAL_STOP policy unmodified. Tests cover two consecutive deferred rounds and recovery.

**P2 (nonblocking detail): ACCEPTED for I/O isolation and authoritative submit gate.** `WorkbenchView.render_detail` and the context menu now call in-memory `order_action_hint` rather than SQL-backed `can_order_action`. The real `request_order_action -> can_order_action` gate remains authoritative. A synthetic exclusive SQLite + business-lock window paints without the blocking authority lookup, and delayed permission lookups do not block the UI. UI hint is a display affordance, never durable authorization.

### Remaining P1 blocker: real idle manual-action window expires before visible countdown

`backend.poll_loop` assigns the **legacy** `_next_poll_at = utc_now()+15m` before TP runs. The correction intentionally leaves that timestamp unchanged, but `_wait_between_polls(900)` now displays an independently computed 15-minute `planned_check_at` **after** TP. `_manual_idle` (used by both `can_order_action` and `order_action_hint`) still checks `_next_poll_at > utc_now()`. Therefore after TP takes 10 minutes, manual actions become unavailable 5 minutes into the **15-minute visible idle countdown**, and for TP duration >=15 minutes they are unavailable throughout actual idle. This discrepancy is deterministic from the source; the added test `test_tp_duration_never_shortens_actual_wait_or_ui_countdown` intentionally asserts `_next_poll_at == legacy_deadline` and does **not** test manual-action enablement in the later idle window.

Required narrow fix: synchronize the existing permission-window deadline with actual entry to `_wait_between_polls`, **without bypassing** `_poll_idle`, `_poll_gate`, `_manual_busy`, stop state, `can_order_action`, and existing SQLite/TP/UNKNOWN purchase/email gates. Preserve one worker and the original full 900-second wait and manual action reset. Do not grant permission before TP/cleanup finishes or after actual wait ends. Add virtual-time UI + canonical `can_order_action` regression for TP taking 0/5/10/20 minutes and for recovery/manual-reset/stop. Ensure an in-flight/UNKNOWN purchase or TP send is still rejected.

### P2 important: TP hint may show impossible/unsafe rerun

`order_action_hint(..., "tp")` returns true whenever `self._tp is not None` and the shared idle flag is true, **before** verifying that the selected item is a TP-capable task or checking its in-memory `business_status` and `delivery_status`. Thus unrelated ordinary orders and TP tasks with an already UNKNOWN/in-flight delivery may have an enabled “重跑 TP 价格” button, while the canonical `TpStore.manual_allowed` correctly denies it. This is not an authorization bypass but creates misleading buttons. Use only the existing in-memory projection to conservatively suppress known-ineligible/UNKNOWN/in-flight TP hints, while preserving the real fresh gate at submit. Do not add UI-thread SQL or permanently cache grants. Test ordinary unrelated order and known TP UNKNOWN/PENDING versus safe SENT/FAILED states.

**Disposition:** retain `REVIEW_REQUIRED`, scope the next patch strictly to the above tiny consistency issues and synthetic tests, re-run targeted + full suites and return new SHA. Current source direction, six-page UI, bounded snapshots, lightweight rendering and original business safety are otherwise accepted in this code-review scope. 24-hour, real OS DPI, production Chrome, live end-to-end and game interference remain NOT_VERIFIED, and unrelated post-`a29c1466` business commits have not received sign-off through this UI review.
