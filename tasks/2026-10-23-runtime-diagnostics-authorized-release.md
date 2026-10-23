# Task: Owner-authorized V1.4 diagnostics release

status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-23

## authorization / scope

Owner explicitly requests packaging, replacement and running V1.4 after the
SystemExit fix. CEO source review124e39ca17dcf4a59e7e72b97a40331609d955e8
passes code6089686d791c92cfaccf0b2e614a11f1f0dde122 and permits separately
Owner-authorized release preflight. This request supplies release authorization;
earlier source-only prohibitions are superseded solely for this release.

Reuse canonical BuildOnly V1.4 script/spec and existing root installation.
Verify all123 tested source input hashes and committed blobs; no source change.
Build/scan/frozen dependency checks, minimal asset replacement with verified
rollback, preserve runtime/config/customer/business data hashes and junctions
without following links. Confirm installed app absent before replacement; no
forced process stop. Launch normal GUI idle, verify responding/ready and hidden
observer handshake. No automatic inquiry/order/login, credential probe, production
business/network/browser/CDP operation, tab closing or profile change.

## acceptance / verification

- Canonical build/self-check/scanner passes and exact tested source retained.
- Replace program assets only; rollback hash verified; protected files unchanged
  at copy. Installed self-check and idle render check pass before normal launch.
- Verify GUI main process responding and its per-run state/gui_ready,
  observer_started and matching observer target receipt; no monitoring-failure
  event. No live crash injection, business start or claim of old-cause recovery.
- Retire only task-owned marked staging; retain compact source/deploy/startup
  receipts and rollback. Publish this task receipt on original V1.4 branch,
  preserve local dirty work/index/HEAD and independent CEO review history.
- Maintain REVIEW_REQUIRED for release receipt/live acceptance. Past disappearance
  remains UNKNOWN; diagnostics cannot guarantee a cause after power/storage loss
  or simultaneous parent/observer termination.

## completion

Source6089686d791c92cfaccf0b2e614a11f1f0dde122, reviewed in
124e39ca17dcf4a59e7e72b97a40331609d955e8, packaged through unchanged
`scripts/build_windows_release.ps1 -BuildOnly -Version 1.4`. All123 raw tested
input hashes and reviewed Git blobs match; hash equality rechecked before copy.
Build, bundled dependency self-check and RELEASE_SCAN_OK passed. No source change.

Frozen staged `--help` executed the canonical run_monitored path without a
business backend: observer ready handshake and native capture enabled, actual
exit0/unexpected with no invented exit intent; SystemExit type/code evidence
recorded. This deliberately verifies a zero-code command with no separately
recorded intent, not a production crash. Synthetic stage runtime retired before
deployment; no protected production runtime was used for that check.

Installed old process absent before copy, no forced shutdown. Replaced only
INSO_V1.4.exe and _internal/base_library.zip after verifying rollback hashes.
All2875 program assets match stage and all10 protected files are unchanged AT
COPY. Configuration, data and browser/profile not modified by deployment. Minimal
rollback and ignored receipts retained at
`.tmp/runtime-diagnostics-release-20261023/`. Installed EXE SHA256:
9ae1b248fbd9aea1a43175ebc8b2f974307ba80a0571bb553dea3de33354ae2d.

Installed dependency and idle GUI self-checks both exit0; idle check verifies no
inquiry/order thread. Normal visible installed GUI launched with no business-start
arguments on2026-10-23 16:41:39 Asia/Shanghai, PID238984, title INSO_V1.4,
nonzero window handle, Responding=True; later verification still responding.
Run dd5e0a03249043c7b07411f0c62e3a91 records start/gui_ready/observer_started,
phase gui/completed false; observer PID246880 matches main target, native capture
file exists and no monitoring/application/thread/Tk failure event. Hidden observer
is expected and does no business. Actual exit receipt will be written on exit;
running app was not closed merely to test it. Owned marked stage retired after
verification, no runtime/reparse path followed; compact evidence/rollback retained.

This receipt supersedes earlier source-only/not-installed statements for these
reviewed changes. No inquiry/order/login/browser/CDP/SMTP/credential probe or
business replay performed. Past disappearance and long-running live acceptance
remain UNKNOWN. Code review PASS already recorded; release receipt stays
REVIEW_REQUIRED for independent review. No promise of all-cause crash prevention.
