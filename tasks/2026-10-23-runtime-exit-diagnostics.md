# Task: Diagnose silent GUI/process exits without business replay

status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-23

## problem / authorization
Owner reports the application disappeared without an intentional exit and asks
to complete exit monitoring so future failures can be investigated. Read-only
Windows Application/WER/reliability checks found no matching failure, no current
process, no normal-exit receipt; past cause remains UNKNOWN. Absence of Windows
reports is not proof of a clean exit. Existing main catches selected Exceptions,
but no lifecycle receipt/Tk callback/thread/system exception coverage, native
fault trace or external exit-code observation exists.

## reuse / scope
Reuse canonical source/frozen entry, GUI close/tray, single-instance guard and
runtime/logs location. Core owns minimal process-diagnostic infrastructure (stdlib
only), exposed through existing Core package; GUI/entry integrate it. This is a
real missing capability, not another launcher/business scheduler/login framework.
Add durable per-run start/requested-close/app-finish records, safe exception type
and code-position traces without message/locals/source text, native faulthandler
stack-only output, Windows helper waiting on an inherited handle to THIS process
and recording actual exit code, plus next-launch incomplete-receipt reporting.
No restart/kill/business replay/Chrome/CDP/credential/production-data operations.
Never write full-memory crash dumps. Bound retention of owned diagnostic files.
Do not call user-requested exit normal unless actual exit and request receipts
support it; unexplained zero-code exit is still unexpected. Missing observer or
write permission must not be hidden as successful monitoring.

## acceptance / verification
Synthetic subprocesses only: normal requested exit, zero-code forced os._exit,
nonzero forced exit, caught app error, real background thread exception, real Tk
callback exception, native fatal stack generation where safe, hooks restored,
duplicate-instance no overwrite, no secret message/local/source line in logs,
old incomplete/dead receipt vs still-live process, malformed diagnostics and
I/O failure do not change business behavior. Windows observer must record actual
codes without PID-reuse guessing; never wait for observer while parent is alive.
Relevant offline GUI/Core/release/backend/Research regressions, Ruff/scoped diff.
No deliberate failure of the real app/browser and no real business acceptance.
Retire owned test artifacts, preserve compact evidence and unrelated work. Push
original V1.4 branch, REVIEW_REQUIRED. Earlier release authorization was explicitly
conditional on proving no crash, not yet satisfied; no packaging/replacement in
this source task without further Owner direction. Past cause stays UNKNOWN;
power loss/monitor also killed/pre-Python boot failures can remain unclassified.

## completion / verification

Implemented Core runtime_diagnostics.py and public exports; GUI main/app and
existing Windows entry only. Existing package specification already collects all
src submodules, including dynamically loaded GUI; no spec/dependency change.
Core/Product Baseline document behavior and limits. Added targeted Core/GUI tests.
No backend, procurement, Research, Sheets, browser or business behavior changed.

- Targeted final offline regression:164 passed (21.41s):
  `tests/core/test_runtime_diagnostics.py tests/gui tests/launcher/test_release_infrastructure.py`.
- Expanded offline regression:2117 passed,1 skipped,2 failed (85.63s):
  `tests/core tests/gui tests/launcher tests/research tests/sheets tests/workflow`.
  The two failures are existing `test_unsettled_manual_attempt_preserves_durable_old_hold_and_automatic_barrier`
  variants `[False-failure0]` and `[True-failure0]`, expecting a GLOBAL_STOP raise
  from CDP failure where current backend defers recovery. Both reproduce unchanged
  against pristine prior remote55e7af3b915b0937248c2c5e0c6c3d321b6bb239
  (2 failed,25 deselected). No unrelated business/test change to hide the failure.
  Existing test SMTP guard blocked both attempted connections locally; no mail sent.
- Real synthetic Windows subprocess observer tests cover requested/duplicate exit,
  unexplained main return, forced zero/nonzero/native-pattern exit, and corrupted
  final state. Actual inherited process handles and DWORD/hex codes verified.
  Native stack-only output verified with dump_traceback and handler-enabled check;
  native-pattern0xC0000005 was a synthetic exit status, NOT a deliberately induced
  access violation. No native crash of the real application was performed.
- Real synthetic thread failure and Tk callback failure; subsequent callback still
  runs. Logs exclude private exception message/local/thread name. Restored hooks,
  distinct duplicate receipt, safe retention, corrupt previous receipts, permission
  failure, observer/native startup failure, source-loader failure and SystemExit
  codes verified. GUI hide/actual-close behavior and degraded-monitor notice pass.
- Scoped Ruff passed; final selected diff checked. Previous122-input release
  manifest differs in only4 intended tracked files; new Core module is input123.
  Preserve prior CEO review55e7af3 and local dirty worktree/index/HEAD.

Evidence: ignored `.tmp/runtime-exit-diagnostics-20261023/` compact verification,
tested-input manifest and publication receipt. Task-owned synthetic test trees
retired after checks; no production output/secrets included in Git.

Past disappearance remains UNKNOWN. Source-only pending independent CEO review,
no build/overwrite/launch, no real business validation. Earlier conditional
deployment is still unfulfilled; these diagnostics only protect a future installed
version. Next action: CEO review this source change (REVIEW_REQUIRED).


## CEO independent review — exit diagnostics (2026-10-23)

**CHANGES_REQUESTED — P1 classification correctness; DO NOT PACKAGE/DEPLOY.**
Independently inspected commit
`de9adac283af87df9ffe5bd078411d0316e1f53f`, including the new
Core observer/lifecycle module, frozen/source entry integration, Tk
close/callback handling, synthetic tests and existing launcher
interfaces. Source files are limited to Core diagnostics, GUI and
Windows entry; no backend, browser, purchase, Research, Sheets or
business replay changes. The observer's inherited Windows process
handle, recorded raw exit DWORD/hex, missing-exit UNKNOWN policy,
thread/Tk exception redaction, and user-close-vs-tray distinction
are directionally correct. Owner's previous disappearance cannot be
retroactively diagnosed.

**P1 defect — unexpected clean `SystemExit(0)` is forged into an explicit
command exit.**
In `src/core/runtime_diagnostics.py::run_monitored`, the broad
`except SystemExit as exc` clause calls
`diagnostics.request_exit("command_exit")` whenever the exit code is
zero. This manufactures a supposedly intentional command-exit receipt
without a user action or recognized explicit command. If an imported
library, Tk callback or the application's own internal code unexpectedly
raises `SystemExit(0)`, the wrapper also calls `finish(0)`;
`watch_runtime` then sees `exit_code==0`, `completed==True`,
`exit_reason=="command_exit"`, classifies the disappearance
`normal`, and suppresses the very unexpected-zero-code evidence the
Owner requested. This contradicts the stated normal-exit
classification contract.

**Required minimal repair:** Do not infer `command_exit` solely from
`SystemExit(0)`. Record a zero-code SystemExit with no already
verified explicit owner/duplicate/recognized-command intent as
**unexpected**; preserve actual exit code and sanitized exception type
and stack position. Only a genuine separately established command-exit
intent may be labeled `command_exit` (or simply omit that category if
not used). Keep prior explicit owner-exit and duplicate-instance
behavior and process-handle watcher unchanged. Add a **real Windows
synthetic-process observer test** executing a main function that raises
`SystemExit(0)` without an exit request, asserting exit code zero and
`classification=="unexpected"`; include a positive normal
owner/duplicate-exit countertest. No new framework or broader scope,
and no real production process or browser tests.

Executor reported targeted 164 PASS; broad suite 2117 PASS, 1 skipped,
2 pre-existing failures reproduced against prior remote
`55e7af3b915b0937248c2c5e0c6c3d321b6bb239`, relating to
manual CDP recovery / legacy GLOBAL_STOP expectation. The prior
baseline reproduction is an **executor attestation**, not independently
rerun by CEO. CEO reviewed sources and code tests only; no testing of
actual installed EXE, native Windows faults, protected Chrome, live
business, customer data or deployment. Windows WER absence remains
insufficient proof of previous cause.

**Disposition:** `REVIEW_REQUIRED / CHANGES_REQUESTED` until the
small SystemExit classification fix is committed and independently
reviewed. No packaging, installation or business activity authorized
by this review.


## CEO minimal correction — execution (2026-10-23)

Owner authorizes only removal of inferred command-exit intent for SystemExit,
redacted type/code-position evidence, synthetic-process tests and necessary offline
regression. Preserve separately established owner/duplicate/command intent, raw
exit codes, inherited-handle observer and GUI close flow. No packaging, install,
running-app replacement, production orders/browser/data operations.
Execution: complete; final review status remains REVIEW_REQUIRED.

Changed only run_monitored's SystemExit branch: preserve its existing code
conversion, remove inferred command_exit, and record sanitized main_exception
type/code positions through the existing exception recorder. Previously explicit
exit intent remains untouched. Windows observer/handle/code/GUI flow unchanged.
Only source module, corresponding Core test and this original Task Packet changed;
CEO review4b40e30652d331616045f423d1ace9134dc58263 preserved verbatim above.

Verification:268 passed in33.41s, offline on Windows:
`python -m pytest tests/core tests/gui tests/launcher/test_release_infrastructure.py -q -p no:cacheprovider`.
Scoped Ruff passed; selected diff reviewed/checked. Nine new synthetic-process
cases execute run_monitored through actual inherited-handle observation: no-intent
SystemExit(0)/SystemExit(None) =>code0/unexpected; explicitly requested owner,
duplicate and command SystemExit(0) =>code0/normal; SystemExit(7), including an
owner request, =>code7/unexpected; string-code SystemExit and RuntimeError =>
code1/unexpected. Event type, code position and retained explicit intent asserted;
synthetic private exception arguments and locals absent from every receipt.
Existing forced/native-pattern exits, GUI close/tray, duplicate guard, threads/Tk,
failure degradation and startup regressions pass. No live business/real-app tests;
no broader business suite rerun for this three-line branch correction.

Prior123-input manifest differs only in src/core/runtime_diagnostics.py. Publish
exactly3 files on the original branch, preserving local HEAD/index/unrelated work.
Compact evidence: ignored `.tmp/runtime-systemexit-review-20261023/`; retire only
this task's synthetic test tree after checks. No package/install/replacement or
production process/browser/order/data access. Past disappearance remains UNKNOWN.
Next: CEO independent review of the minimal correction, REVIEW_REQUIRED.
