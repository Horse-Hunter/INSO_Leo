# Owner-authorized V1.4 Google/INSO recovery release

status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-21

## Owner authorization / scope
Owner requests packaging, overwriting and running after verifying that incidental
faults do not arbitrarily globally stop. Deploy the existing Google read-busy
recovery (08639554945c70e5cc731cfef55b2b2553072537) and INSO login retries
(2a41a6e92ec3ad6859e5332b5a661691836b1c9b). Reuse canonical release script,
environment/spec/install directory. Preserve runtime/config/credentials/CDP
profile; back up changed assets before replacement. Apply Owner's earlier
leave-only-a-blank-page instruction to idle program-owned Google residue after
verified program exit; preserve manual or actually unfinished/protected pages.
No automatic inquiry or order start, actual login or business replay as a test.
No claim that external network/websites can never fail. REVIEW_REQUIRED stays.

## Verified intended policy / acceptance
Google temporary reads including protected/busy pages: existing five attempts,
then one notice and next 15-minute poll; no write replay. Failed read pages can
be retired only when verified idle; three-sheet tab cap remains. INSO transient
authentication handshake: five attempts, 2/4/6/8-second waits, then existing stop
if still unproven. Explicit password/SMS/human verification, unknown/security/
identity faults and uncertain writes do not get blindly retried. Offline tests
must prove both complete failure/recovery paths and these exclusions together.
Confirm old EXE absent before copying, staged/installed self-check and scanner
PASS, changed-asset rollback, all installed asset hashes and protected file/link
manifest unchanged at copy, idle GUI and actual visible startup responding.
Retire owned test/staging copies in this task; retain minimal rollback/evidence.

## Verification / completion
Pending combined regression, canonical build, deployment/startup and cleanup.
No source or retry-policy change is included in this release task.

Combined offline regression: 1471 PASS, 1 skipped in43.83s, Ruff PASS. Includes
the real backend poll loop timeout->busy->retry exhaustion->next-poll recovery,
Google and INSO session/quotation/write exclusions and earlier Findchips tests.
All122 build inputs match source2a41a6e92ec3ad6859e5332b5a661691836b1c9b.
Preflight: old program absent. Existing CDP has one blank and one program-owned
Google page, saved, no visible dialogs or pending refresh. Old package predates
read-failed marking; this residual tab must not occupy a slot in the new pool.

## Installed release / startup
Canonical BuildOnly frozen self-check and RELEASE_SCAN_OK PASS; old installed
self-check, new installed self-check and real idle GUI self-check PASS. Replaced
only INSO_V1.4.exe and _internal/base_library.zip; both old assets copied into
hash-verified rollback. All2875 installed asset hashes match the stage. All10
protected file/link manifest entries unchanged AT COPY; runtime junction targets
were not traversed, copied or overwritten. No credential/config/DB/profile or
Chrome modification. Following Owner's previous blank-page request, retired one
program-owned saved Google residue with no dialog/script/pending markers; the
remaining blank page ID was unchanged during copy/self-check.

Installed EXE SHA256:
1bc94741bc8150e391fe16409e44b6dc289cd061a70ee47e4a3c0e5988f953cc.
Normal visible idle launch at 2026-10-21 21:37:08 Asia/Shanghai: PID209012,
title INSO_V1.4, real main window present and responding. No --start-inquiry,
inquiry/order replay, actual login or SMTP verification. This deploys both fixes;
the earlier packets' source-only/not-installed statements are superseded by this
receipt. Live long-running recovery/business acceptance remains UNKNOWN.
Explicit human/security/identity faults and INSO exhausted recovery can still
pause/stop; no blanket promise that all external failures can be auto-recovered.

Ignored minimal evidence/rollback: .tmp/recovery-release-20261021/. Task-owned
combined test directory retired (64749072 bytes); marked non-reparse frozen
stage retired after verification; PyInstaller work removed by canonical script.
Only small manifests/logs and two rollback assets retained; prior rollback,
runtime/profile/CDP and all unrelated dirty work preserved. Source and retry
policy unchanged by this release task. Independent Review remains required.


## CEO independent review — 2026-10-21

**CODE REVIEW PASS (two scoped recovery fixes). INSTALLED/IDLE REPORTED;
ACTUAL GOOGLE/INSO RECOVERY AND BUSINESS ACCEPTANCE STILL UNKNOWN.**

Independent GitHub inspection of branch range `96ced95..802047a`,
including code commits `08639554945c70e5cc731cfef55b2b2553072537`
(Google busy read recovery), `2a41a6e92ec3ad6859e5332b5a661691836b1c9b`
(INSO login retry), their synthetic regressions and this deployment receipt.

- Reproduced failure chain in executor's sanitized evidence: at
  2026-10-21 13:14:48 Google download read timeout, followed at 13:14:50
  by a protected/busy page classified as unknown. That path previously
  led to `SHEETS_READ_UNAVAILABLE` rather than normal read-only deferral.
  Precise historical busy cause and original site/network cause remain
  UNKNOWN. The revised read-only classifier recognizes the exact existing
  `GOOGLE_QUOTATION_INPUT_BUSY` token; the five-try reader, one queued 229
  warning and 900-second next poll are reused without adding write replay.
- A failed read page receives a browser-visible marker. Retirement checks
  the original Google-owned document and authentication guard and requires
  an idle/non-unsafe surface; uncertain writes never receive a read-failed
  marker. The protected-slot and three-tab cap remain. This is not a
  guarantee that every busy Google surface can be recovered.
- INSO `InsoSessionGuard` now retries identified browser/network timeout
  or not-ready authenticated shell up to five attempts (2/4/6/8-second
  intervals), retaining tab/session ownership and requiring the native
  authenticated shell proof before business use. Confirmed password refusal,
  human/OTP/CAPTCHA, unknown or certificate errors and failed identity
  re-lease remain non-retryable; there is no automatic procurement replay.
  A slow shell may cause more than one ordinary login submit, as allowed
  by the bounded recovery specification; this does not re-submit orders.
- Executor reports 1471 offline tests PASS, 1 skipped, Ruff/scanner,
  staged and installed frozen self-check and idle GUI PASS. CEO inspected
  source and targeted tests, **did not independently run the tests** or
  contact actual production CDP, browser, ERP, Google, SMTP or OS processes.
  This is a combined **selected regression**, not a claim of a complete
  repository-wide test suite.
- Executor reports Owner-authorized overwrite of only EXE/base_library.zip,
  preserved runtime/config/credentials/DB/profile, verified rollback,
  and a responsive idle V1.4 window. Installed EXE SHA256 as reported:
  `1bc94741bc8150e391fe16409e44b6dc289cd061a70ee47e4a3c0e5988f953cc`.
  Production state beyond that report cannot be independently verified
  through this code review.

**Disposition: REVIEWED_DONE for code, LIVE_ACCEPTANCE_PENDING.**
No further code change or repackaging requested solely for review. Observe
the next naturally authorized run and capture sanitized 2026/SHAHAB read,
Google transient retry/defer and INSO login readiness outcomes. Authentication
challenges, unknown/identity faults, repeated recovery exhaustion and uncertain
writes still require the existing stop/manual process. Do not trigger test
orders, replay uncertain procurement, modify the CDP profile, or disturb the
installed rollback in response to this review. No production action executed
by CEO.
