# Windows release

## Current RFQ-003 V1.2 refresh (2026-10-07)

Owner-authorized resilience update, REVIEW_REQUIRED; not V1.3 or live acceptance.
Existing build/spec/deploy path reused. Final EXE SHA256:
`4B412E25C778246E573A9854A1C168ABC1EB443792696375D39AAB1A93BC1766`.
Original pre-update EXE/_internal backup:
`dist/release-backups/INSO_V1.2-20261007-before-rfq003-resilience`.
Only frozen assets overwritten; runtime junction, DB, config/grants/profile preserved.
Build, frozen/deployed self-check, clean staged scan and idle launch PASS. GUI stays
idle: no inquiry, submission, SMTP, Sheets write or real challenge tested.
Current rules and full evidence: `control-room/RFQ-003/EXECUTION_LOG.md`.
Older build descriptions below are historical when conflicting with this update.

## Current V1.2 refresh (2026-10-06)

Owner authorized rebuilding and overwriting the same V1.2 application path.
Reused `scripts/build_windows_release.ps1 -Version 1.2 -BuildOnly`; staging
self-check and RELEASE_SCAN_OK passed. Built production source
`a1bed4094af8a834483c8f9f7852f6e7de0c7ac4`. Replaced only EXE/_internal after
moving old assets into `dist/release-backups/INSO_V1.2-20261006-before-completion-update`.
Runtime junction/target and protected grants were preserved; V1.1 untouched.
Deployed frozen self-check exit 0; EXE SHA256:
`FDAA40FEF27AB83C7C014F2C3BC0FB5072207882DFB1F748AD08050E9597482D`.

Current build includes Oct 6 AI/confirmation fixes and purchase completion
status/mail features. The narrow successful status transition 未发 -> 发给采购
is now Owner-authorized; previous blanket Sheets-write statements below are
historical, not current. Ordinary Save/generic Send remain closed.
No orders, submission, mail or Sheets update executed during packaging.
GUI launch attempt did not complete (Computer Use app approval timeout);
no bypass. Owner can double-click the existing EXE path below. Build/self-check
does not prove the new packaged full order chain; only test a genuine new order.
Earlier startup/first-submit statements below apply to the old Oct 2 build.

## V1.2 Owner-authorized build and local deployment (2026-10-02)

Owner explicitly approved packaging after personal Review discussion. Reuse the
existing build script/spec, not a parallel release pipeline:

`powershell -ExecutionPolicy Bypass -File scripts\build_windows_release.ps1 -Version 1.2`

Default version remains 1.1; version 1.2 uses distinct artifact/staging names.
The generic artifact is scanned and self-checked BEFORE local runtime deployment.
The existing V1.1 directory is never replaced.

Owner executable on this machine:

`D:\Program_Leo\INSO_Leo\dist\INSO_V1.2\INSO_V1.2.exe`

Local `runtime` is a junction to the already-used
`.worktrees\v1-2-design\dist\INSO_V1.1\runtime`, preserving config, SQLite,
Research results and historical purchase state without copying customer data
into the generic package. This local deployed directory is NOT a portable clean
distribution; keep its runtime target intact. Do not archive that worktree
before migrating its live runtime safely.

Frozen dependency check, artifact safety scan and actual stopped GUI startup
passed. Smoke instance closed normally; no Start Inquiry, credentials/readiness
probe, order replay, SMTP or Save-and-Send was executed. Final submit remains
untested by explicit Owner instruction. Double-click the executable, then only
start inquiry when Owner has a genuine new order. A qualifying new order now
performs REAL Save-and-Send; Sheets write/standalone Save/generic Send stay closed.

## Phase A source startup

Run from the repository root:

`powershell -ExecutionPolicy Bypass -File scripts\start_v12_phase_a.ps1`

This starts the V1.2 production source candidate against the existing V1.1 local runtime configuration, so it reuses the already-working Sheets, Chrome/CDP and Core Vault setup. It initializes the V1.2 database additively and keeps the Production Write Gate closed. EXE packaging is Phase B and requires separate Owner approval.

## Runtime files

Release 不包含生产数据。部署时在 release root 下提供 Git-ignored：
- `runtime/research.json`
- `runtime/production.json`

Chrome bootstrap 只使用显式 approved 配置：

```json
{
  "browser_bootstrap": {
    "executable": "C:/Approved/Chrome/Application/chrome.exe",
    "profile_dir": "D:/Program_Leo/INSO_CDP/chrome-profile",
    "debug_port": 9222,
    "ready_timeout_seconds": 30
  }
}
```

Profile 必须已存在且固定为上述唯一 profile；程序不猜路径、不创建替代 profile。CDP 已可用时复用；否则只启动同一 approved Chrome/profile。受保护 Chrome 永不关闭，只按 ownership 清理程序自己的标签。

INSO ordinary authentication 使用共享 runtime helper + Core Vault 自动恢复；只有 CAPTCHA / OTP / device verification 等人工安全挑战需要 Owner。

## Secrets / diagnostics

不要把 runtime config、OAuth client/grant、browser profile、SQLite、Excel 或 credential 放进 release artifact。

Launcher 日志位于 `runtime/logs/INSO_V1.2.log`，只允许 sanitized diagnostics。缺少 V1.2 production adapters 时应用会明确停止，不会静默退回 V1.1-only processing。报告只能包含 site/config readiness 与安全错误类型，不包含 credential value。
