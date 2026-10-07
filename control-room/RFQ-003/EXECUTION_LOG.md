# RFQ-003 Execution Log

2026-10-07: synchronized feature/v1-2 to CEO PASS commit bf92407;
RFQ-002 is REVIEWED_DONE. Reuse existing active v1-2-design worktree.
Scope is the attached Owner requirements preserved in TASK_SPEC.md, not V1.3.
No real order, submission, SMTP, Sheets writes or live CAPTCHA permitted.
## Baseline and reuse

Started from `bf924076b016433443a731d0ec5c0eec8f90da18` on feature/v1-2;
origin Horse-Hunter/INSO_Leo. Re-fetch before delivery showed the same remote HEAD.
Read entry/governance/module navigation and RFQ-002 packet/review. CEO PASS for
95ce4ca is preserved; RFQ-002 remains REVIEWED_DONE. No V1.3 code or dependencies.
Reused existing active `.worktrees/v1-2-design`, not another implementation.

Existing integration reused: WorkflowStateStore / V12Store identities and SQL
schema, native lower Stock_VenQuote readers, ResearchService/adapters and price
aggregation, targeted Sheets status helper, QQ SMTP worker/notification ledger,
fixed protected CDP/profile, GUI DTOs, build script/spec/deployment asset layout.
Additive TEXT enum states/events require no schema change or new database.

## Implementation evidence

- New narrow `workflow/v12_faults.py` provides V12_PAUSE versus GLOBAL_STOP through
  the existing ResearchPreparationError boundary. Launcher keeps GUI alive.
- Existing coordinator drains current source rows serially in source order;
  invalid/conflicting rows cannot overtake earlier business rows. All closed
  row results settle before interruptible Event.wait(180) for an actual next row.
  Empty/last-row cycles have no added wait. Query wait is independent, not added
  during an unfinished row. Stop interrupts the cooldown without starting a row.
- Model/usable brand/positive integer quantity/tier input errors skip Research
  and procurement, retain durable reason/Owner command, and can run after source
  correction through the existing skipped-input revival. Critical source changes
  stop only that row. Relocation preserves original inquiry_id; no fuzzy matching
  or ID recomputation by new row position.
- NO_MATCHING_PRODUCT remains a real no-quote fact/GUI label, no purchase.
  V1.2 finalizes exhausted row Research failure instead of automatically replaying
  the row; Research aggregate outcomes/FX/stock/price rules themselves unchanged.
  Original important/duplicate notification eligibility/recipients unchanged.
- Typed source observer stops V1.2 for IC.net, globally stops INSO authentication;
  optional Research source exceptions remain failures, not false empty results,
  and other sources/rows continue. Site human-login reminders use Owner 229 only.
  Shared faults thrown during source recovery cannot be swallowed by optional
  source exception fallback.
- Lower duplicate/history queries: initial plus at most three fresh-tab attempts,
  failed owned-tab cleanup, interruptible 180-second wait, same-row retry; clear
  empty is success, untrusted/incomplete query is not. Exhaustion GLOBAL_STOP.
  Existing session/bootstrap recovery uses only the same protected endpoint and
  profile, bounded to three recoveries; failure GLOBAL_STOP. No overlapping INSO
  work is started by row/query cooldown paths.
- Native Save-and-Send still resolves a unique gated control and durably arms
  BEFORE dispatch. SAVE_CLICK_COMPLETED is recorded only AFTER native click
  succeeds. Exactly one arming plus one receipt proves the unique click. Arming
  alone never authorizes status write. Failure to persist state is GLOBAL_STOP.
  Post-confirmation unknown + receipt => independent SUBMIT_UNCONFIRMED, no second
  click, Owner confirmation command, Sheets status attempt, yellow explicit GUI.
  SAVED remains a separate stronger fact. Standalone Save/generic send unchanged.
- Post-dispatch owned-tab/surface cleanup failure logs a sanitized step but cannot
  discard the durable result and trigger purchase replay. DB errors still surface.
  Clearly pre-submit errors end the row without status write and allow next row.
- Status write failure => STATUS_WRITE_PENDING, row closed, yellow manual-update
  wording and 229 instruction; no repurchase and no repeated automatic writeback
  for that state. Entire Sheets read/authorization failure still GLOBAL_STOP.
- SMTP settlement is not a purchase prerequisite. Existing durable commands/retry
  worker operate independently, including running worker idle ticks. Legacy direct
  Owner alert is a fallback only when there is no usable inquiry/completion ledger
  or the ledger itself is unavailable; cannot persist a command in a broken DB.
  Normal inquiry faults do not also invoke a duplicate legacy alert.
- Idle startup projects history with SQLite mode=ro, including rows not present in
  Research Excel; no automatic migration/quarantine/write occurs at idle launch.
  Normal Start quarantines unfinished historical rows before workers. Armed/unknown
  outcomes display red possible-send interruption, proven pre-submit rows red
  unsent interruption; queue skips both, no recovery buttons or purchase replay.
  Source remaining 未发 stays held. Unique relocation/re-read of 发给采购 marks
  HUMAN_COMPLETED, never procurement. GUI clears red even without an active alert.
  Legacy PURCHASE_EXCEPTION with armed/unknown submission is NOT a closed row:
  quarantine as possible-send interruption, and exclude it from completed counts.
- RFQ-002 fresh verification-page protection retained. Also tested final release
  of an already-attached session after manual/module/global pause: disconnect only,
  no lease/tab close and no park. Chrome/context/profile/cookies stay untouched.

## Initial delivery offline tests (448c26c; superseded by B1 results below)

Focused:
`python -m pytest -q tests/workflow tests/launcher tests/inso tests/research tests/sheets tests/gui --basetemp=.tmp/rfq003-focused-final-verified --tb=short`

Result: **978 passed, 1 skipped in 35.27s**, exit 0. Final repeated focused run
also verifies the explicit counter assertion added to the same legacy cases.

Full safe/offline:
`python -m pytest -q tests --basetemp=.tmp/rfq003-full-final-ledger --tb=short`

Result: **1025 passed, 11 skipped in 37.68s**, exit 0.
Skipped tests are not claimed as verified live acceptance. Time waits use fake
wait/event seams; no wall-clock three-minute test waits. Suite-wide SMTP guard
prevents real outbound mail; final successful runs had no attempted-mail warning.

`python -m ruff check src tests`: PASS, exit 0.
`git diff --check`: PASS, exit 0 (Git LF/CRLF notices are not whitespace failures).
Reviewed diff for production/control-room/test scope and protected lifecycle.

Additional RFQ-003 regressions prove row ordering/cooldown/interruption; model,
brand, quantity skip; source pause/global/optional failure; duplicate AND Research
history retry success on attempts 1/2/3/4 and exhaustion; native unique-click proof
and no repeat; unconfirmed status write success/failure with next-row continuation;
restart quarantine/manual completion/moved row; yellow/red labels; DB versus
internal fault scope; CDP recoveries 1/2/3/exhaustion; read-only startup; callback
fault propagation; pre-submit source conflict; post-submit cleanup; active-human
page preservation through final release; human completion red removal.
Existing no-quote, important/duplicate notices, SMTP failure/idempotent retry,
AI model/brand/quantity-only validation, gate and RFQ-002 CAPTCHA/OTP/device
preservation regressions continue PASS.

Intermediate runs exposed outdated old stop/replay test expectations and missing
offline fakes. Corrected test expectations to RFQ-003 and injected fake duplicate
reader/transport instead of relying on empty real-page stubs. Initial mail attempts
were blocked locally by suite guard; no actual SMTP connection was made. No test
weakens native query completeness, gates or durable-click proof.

## Initial delivery release / deployment evidence (superseded by B1 below)

Reused `scripts/build_windows_release.ps1 -Version 1.2 -BuildOnly`, existing spec,
release Python and dependencies. Final build exit 0; staged frozen `--self-check`
exit 0; **RELEASE_SCAN_OK**. Clean staged scan, not deployed private runtime scan.
Build staging is the existing marked throwaway stage; no production data packaged.

Deployed only EXE/_internal to:
`D:\Program_Leo\INSO_Leo\dist\INSO_V1.2\INSO_V1.2.exe`

Original pre-RFQ-003 backup (EXE + _internal):
`D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.2-20261007-before-rfq003-resilience`

Original EXE SHA256:
`7803C90E5AD34415CDF1BE9FDF4F373364C7955CE916BF16A6BF5BFBC7E1FC0A`

Final EXE SHA256:
`4B412E25C778246E573A9854A1C168ABC1EB443792696375D39AAB1A93BC1766`

Final deployed self-check exit 0; DEPLOYMENT_OK_RUNTIME_PRESERVED.
An intermediate build was idle-launched, then final GUI red-removal correction
was verified/rebuilt. Its assets are separately recoverably backed up at:
`D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.2-20261007-before-rfq003-final-projection`
(intermediate EXE CD731B3008773C88594D0EB95D1607F58AA4A2735D388CD2B32ECAD80F4FEEDE).
Original pre-change backup remains intact, not replaced by the intermediate one.
The GUI-red-removal intermediate (4370281F59158ECCEA55B0974607F97F3B94C3C47EDF33D8B429C199E0DD41BB)
was additionally backed up at:
`D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.2-20261007-before-rfq003-final-ledger`
before the final legacy unproven-submit quarantine/counter correction build.
Every final production change is included in the final self-checked executable.

Runtime junction verified unchanged:
`D:\Program_Leo\INSO_Leo\.worktrees\v1-2-design\dist\INSO_V1.1\runtime`.
No runtime/DB/config/OAuth/grant/profile move/reset/delete or cookie cleanup.
Old GUI closed normally with computer-use, not process kill. Final executable
idle-launched through the same skill; unique INSO_V1.2 window observed, no Start
Inquiry/login sweep/business controls clicked. No real protected business checks.

## Delivery boundary / remaining UNKNOWN

REVIEW_REQUIRED, not executor PASS/REVIEWED_DONE. Final offline/release evidence
does not prove live server delivery, CAPTCHA behavior or Google updates for a new
production order. Those remain UNKNOWN until Owner-authorized actual use/review.
No real orders, Save/Save-and-Send, SMTP, Sheets writes or live CAPTCHA were run.
No historical order replay. No V1.3 added; module fault enum is a future boundary,
not a claim that V1.3 runs today.
Only scoped source/tests/docs are committed; EXE/runtime, private probes and local
deployment helper stay ignored/untracked. Commit/remote equality is verified after
push and reported to Owner, without inserting a self-referential commit SHA here.

## CEO Review B1 repair — 2026-10-07 — current delivery

Synced existing feature/v1-2 worktree by fast-forward to CEO Review HEAD
`55466e64e2f0ea64b108c70945265d0afc49d747`. Read latest REVIEW/TASK_SPEC/log/
COORDINATION. B1 is the only repair; requirement meaning and REVIEW.md unchanged.
CHANGES_REQUESTED -> IN_PROGRESS -> REVIEW_REQUIRED; no executor Review verdict.
Earlier universal unfinished-row quarantine claim is SUPERSEDED by this evidence
gate. No new queue/state/schema/identity/browser/notification implementation.

Root cause: every pending row is pre-enqueued and pre-created with
DUPLICATE_CHECK_PENDING plus DUPLICATE_CHECK_STARTED, before serial active work.
That pending event alone cannot identify the row that really started. Old startup
quarantine and idle GUI projection both treated any nonclosed row as interrupted.

Minimal production delta, exactly three files:
- `workflow/v12_contracts.py`: extend the existing interruption helper with durable
  execution proof; pending/queued/no business state plus no claim/later event/no
  purchase/no submit evidence returns no interruption. Reuse existing real-phase
  business states and explicit execution-event allowlist; exclude ambiguous
  precreation DUPLICATE_CHECK_STARTED. Keep closed-state priority, existing held
  interruptions and unknown/possibly-sent safety intact.
- `workflow/v12_flow.py`: supply existing persisted RESEARCHING claim/attempt_count
  or real execution events. A released preparation claim can have attempt_count=0,
  so the durable DUPLICATE_CHECKING/later phase still proves actual start. Include
  SAVE_CLICK_COMPLETED alongside SAVE_DISPATCH_ARMED as possible-submit evidence.
  No change to enqueue/drain/cooldown, claim SQL, routing, gates or notifications.
- `launcher/v12_gui.py`: same helper/allowlist, read-only SQL EXISTS event flags
  and claim fields. Do not append untouched pending rows as interrupted/error
  history. SQL mode=ro remains; no production DB writes/migrations at idle launch.

Untouched later rows stay QUEUED, never mark_interrupted, and remain eligible in
original source order. First closed row stays closed during a cooldown exit.
Real active unfinished/armed/clicked/unknown rows stay held, not auto-procured.
No resetting old held rows or cleanup/migration of the production database.

Offline coverage: 18 new parameter cases (2 three-row crash/cooldown scenarios,
7 durable claim/event/submission evidence cases, 9 closed-state cases). Updated
two original tests to seed genuine active-row evidence rather than bare enqueue;
strengthened manual completion test with red removal and another no-replay poll.
Launcher real-composition/fake-data test now asserts the next untouched original
source row runs, while the third row remains queued/pending rather than frozen.
No fake browser/transport operates on real orders; all waits are fake/interrupted.

Actual final validation:
- Focused:
  `python -m pytest -q tests/workflow tests/launcher tests/inso tests/research tests/sheets tests/gui --basetemp=.tmp/rfq003-b1-focused-final --tb=short`
  **996 passed / 1 skipped in 35.76s**, exit 0.
- Full safe/offline:
  `python -m pytest -q tests --basetemp=.tmp/rfq003-b1-full-final --tb=short`
  **1043 passed / 11 skipped in 37.18s**, exit 0.
- `python -m ruff check src tests`: PASS, exit 0.
- `git diff --check`: PASS, exit 0; reviewed three-file production delta.
  Initial new fixture tried a guarded direct purchase-state transition and was
  rejected offline (3 failures); corrected fixture to use existing guarded ledger
  transitions, without relaxing production safety. Final runs all pass, no SMTP
  attempt warning. Existing RFQ-002 page preservation and RFQ-003 policies PASS.

Reused existing build/spec/deploy helper; changed only local ignored backup literal.
`scripts/build_windows_release.ps1 -Version 1.2 -BuildOnly`: exit 0.
Frozen self-check: exit 0. Clean staged scan: RELEASE_SCAN_OK.
Only EXE/_internal overwritten; deployed self-check exit 0 and
DEPLOYMENT_OK_RUNTIME_PRESERVED. New backup, no earlier backup overwritten:
`D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.2-20261007-before-rfq003-b1`
Backup EXE SHA256:
`4B412E25C778246E573A9854A1C168ABC1EB443792696375D39AAB1A93BC1766`.
New deployed EXE SHA256:
`1A49C9650BA531F2299326FFC89761D0391CD5F2C0FE32327DDD0736BD5C3E84`.
Deployed path remains `D:\Program_Leo\INSO_Leo\dist\INSO_V1.2\INSO_V1.2.exe`.
Runtime junction verified unchanged to v1-2-design/dist/INSO_V1.1/runtime.
No runtime/workflow DB/config/OAuth/grant/profile modification/move/delete/reset
or cookie cleanup; no Chrome/context close or new CDP. Old GUI closed normally
using computer-use; rebuilt GUI idle-launched, unique INSO_V1.2 window observed.
No Start Inquiry or login sweep clicked. No real orders, Save/Save-and-Send,
SMTP, Sheets writes, production replay or live CAPTCHA were executed.
Live acceptance remains UNKNOWN; independent CEO Review required. Final SHA and
remote equality are checked after commit/push, reported without self-referential
commit metadata edits.

## Owner current-batch follow-up — 2026-10-07 — IN_PROGRESS

Owner explicitly requested fulfillment of four current genuine unsent orders,
confirmed-bug repair, V1.2 rebuild/overwrite, and CEO report for downstream V1.3
sync. This live fulfillment authorization is distinct from the preceding B1
offline-only repair; no historical replay or fabricated input is authorized.
Owner started the existing deployed loop. Executor observes read-only DB/events
and existing Sheets reader, does not separately click Start or dispatch orders.
Cached Google authorization reused with allow_interactive=False, no new consent.
No production SQL updates, new CDP, profile/cookie cleanup or customer-data commit.

Remote CEO approval commits 36a2aee/c8d514e fast-forwarded into the existing dirty
worktree; REVIEW.md left unchanged. Reviewed B1 baseline remains approved. This
new incremental follow-up requires fresh Review, not executor self-approval.

Confirmed issue: invalid S tier correctly skipped under existing A/B/C rules;
Owner corrected source to A and the original queue resumed and purchased. Old
invalid-input DATA_QUALITY warning remained active, falsely showing a saved order
red. Reused existing recover-alert transaction on validated input revival. Narrow
read-only GUI compatibility filter handles older already-saved/repaired rows,
without clearing customer/security/submit/notification alerts or editing DB.
Second issue: row cooldown was displayed as imminent polling. Added optional
RunSession row_cooldown_until and thin wrapper around existing stop.wait; GUI now
shows cooldown remaining or active processing. No change to 180 seconds, source
order, stop, last-row/empty-poll policy, purchase gates or notifications.

Production files: gui/app.py, gui/contracts.py, launcher/backend.py,
launcher/v12_gui.py, workflow/v12_store.py. Three offline regressions added to
tests/workflow/test_rfq003_resilience.py. No dependency/schema/second main chain.
Actual exact-source tests:
- focused six related module suites: 999 passed / 1 skipped in 36.75s.
- full safe/offline tests: 1046 passed / 11 skipped in 37.51s.
- python -m ruff check src tests: PASS. git diff --check: PASS.
- existing build_windows_release.ps1 -Version 1.2 -BuildOnly: exit 0;
  frozen self-check and clean staged RELEASE_SCAN_OK passed.
Live four-order completion and deployed hash/idle launch still pending at this
entry; do not treat offline tests or build as production acceptance.

Follow-up completion evidence, Asia/Shanghai 2026-10-07 evening:
Existing Owner loop processed the first three genuine rows to PURCHASE_RECORDED,
each with exactly one SAVE_CLICK_COMPLETED, one confirmed-saved reconciliation,
two important-notification successes. Source read-only check verified all three
are 发给采购. Fourth row added after the prior poll entered the next poll queue;
normal inter-row cooldown, duplicate check and Research proceeded. Fourth ended
NO_MATCHING_PRODUCT / RESEARCH_FAILED. Existing Excel result has all five price
sources 无结果; no SAVE_DISPATCH_ARMED/SAVE_CLICK_COMPLETED, exception notice
delivered, source remains 未发. This is a normal safe no-quote terminal state,
not a procurement control bug. Owner asked to confirm model or explicitly decide
no-quote treatment. Four successful purchases remains BLOCKED on that business
decision; never report 4/4 or bypass the existing requirement. No historical replay.
Old empty-brand dummy row is not one of these four genuine current orders.
Read-only probes are ignored .tmp helpers, not new production implementations.

Confirmed display fixes and offline/build work complete. Empty application closed
normally via computer-use; deploy helper verified no running EXE, made new backup,
replaced only EXE/_internal and completed deployed self-check exit0:
DEPLOYMENT_OK_RUNTIME_PRESERVED.
Backup D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.2-20261007-before-input-alert-cooldown-fix.
Backup hash 1A49C9650BA531F2299326FFC89761D0391CD5F2C0FE32327DDD0736BD5C3E84.
New EXE 340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F.
Runtime junction target remains v1-2-design/dist/INSO_V1.1/runtime. Chrome survives
with original blank window; no profile/config/grant/DB migration or reset.
Computer-use idle-launched rebuilt application; unique final V1.2 window returned.
Window capture timed out twice; no stale-coordinate use or fabricated screenshot
evidence. No Start Inquiry clicked, no new replay/submission or test mail/write.
Owner live operations preceding replacement are explicitly documented above,
so earlier B1 'no real business' statements apply only to that historical repair.
Current increment REVIEW_REQUIRED; original CEO PASS at241fd48 stays unchanged.
CEO_SYNC_REPORT.md gives exact files and V1.3 reuse boundaries, no V1.3 code change.
Commit/push equality will be verified externally; no self-referential SHA edit.

## Owner report clarification — documentation only

Owner confirmed the fourth no-quote order must not enter procurement and its
existing exception mail is correct. Prior business-decision blocker is RESOLVED:
four handled per rules, three sent, one no-quote; no retry/model change needed.
Owner requested explicit reuse instructions for V1.3. CEO_SYNC_REPORT now pins
f515a145360d0eb72c4ffd7b8988a6cea6ae7ed2 as the implementation diff, specifies
file-level merge limits, prohibits reimplementation/blind whole-file copy, and
requires equivalent-existing/minimal-adaptation evidence plus offline regression.
FINAL_REPORT synchronized; old B1 history/CEO REVIEW unchanged. No src/tests,
EXE, runtime, DB or business actions changed. No rebuild or pytest rerun for this
documentation-only update; prior code results are historical, not rerun numbers.
git diff --check and staged diff reviewed before commit/push.
Later requested Start action could not observe screenshot/button; no blind click,
no verified polling start. Owner canceled it. Current polling must not be claimed.

## Owner-requested single unsent typo archive cleanup — 2026-10-07

Owner corrected a customer model typo in the source sheet and requested removal
of the old no-quote item before personally rerunning. Explicit one-time runtime
maintenance, not a code change or general replay/reset capability.
Read-only checks found exactly one FAILED / NO_MATCHING_PRODUCT item with
RESEARCH_FAILED state, zero purchase/armed/clicked/saved evidence, zero active
Research and zero referencing V1.3 hold. GUI closed normally via computer-use;
EXE absence verified. No source Sheets writes or credential/profile changes.
Full SQLite backup verified: runtime/production/maintenance-backups/
owner-typo-20261007T141925Z/workflow-before.sqlite3 (private local, not Git).
First delete attempt hit append-only protection and completely rolled back.
For explicit Owner archive purge, only the event-delete trigger was temporarily
removed inside BEGIN IMMEDIATE; identical definition restored before commit.
Both original triggers compared equal afterward; audit history retained in backup.
Removed exactly one work item/business state/duplicate result, ten events, two
notification commands and three recipients; zero purchase rows. All unrelated
table rows compared equal, foreign_key_check unchanged, integrity_check OK,
target absent. No whole DB reset. Research Excel history unchanged; existing upsert
replaces it on Owner rerun. Original deployed GUI idle-launched, unique window
confirmed; no Start, Research, INSO action, SMTP or Sheets write executed here.
No src/tests/EXE change or rebuild. TASK_SPEC records narrow authorization;
private helper/backup excluded from Git. Documentation diff check passed.
