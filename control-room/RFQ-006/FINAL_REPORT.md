# RFQ-006 Final Report — REVIEW_REQUIRED

Implemented unified V1.2/V1.3 serial cycle in the canonical launcher. V1.2-only pause
continues quotations; shared failures stop both. Reviewed purchase/restart/one-click
behavior retained. Durable V1.3 final-failure holds and deduplicated229 notifications use
existing SQLite/mail infrastructure. GUI shows waiting/completed/red quote states.

## Implementation locations
- src/launcher/backend.py: canonical production composition/poll, shared CDP recovery,
  module status, safe-boundary stop, V1.3 GUI projection and structured cycle logging.
- src/workflow/v13_integration.py: CombinedCycle, V13IntegratedCycle, V13HoldStore.
- src/workflow/v13_quotation.py: optional skip/settle callbacks; default approved path retained.
- src/launcher/v13_integration.py: existing config geometry, GUI and229 notifications.
- src/workflow/v12_store.py / v12_contracts.py: same backup/notification ledger extended
  for new operational context, preserving V1.2 rollback notification states.
- src/gui/contracts.py / app.py / main.py: states, colors, paused-running actions/logging.
- scripts/build_windows_release.ps1 / windows_release_entry.py / packaging/INSO_V1.1.spec:
  V1.3 release selection and bounded no-business idle GUI self-check.
- docs/V1_3_INTEGRATION.md: runtime config/unknowns/migration/release contract.

15-minute cycle: entire A then entire B, followed by existing interruptible900-second wait.
V1.2 zero/one/multiple rows transition immediately into B;180 seconds only between adjacent
closed V1.2 rows. V1.3 has no normal row cooldown; reviewed INSO initial+3 query retry180
seconds retained. Backend tests verify pause continuation, global stop, default wait,
shutdown and scheduler nonoverlap. Full tests retain V1.2 reviewed crash/restart/yellow states.

## Verification
- RFQ-006 focused:52 passed; combined46 (43 workflow +3 actual backend); GUI shutdown/login6.
- V1.3 RFQ-004/B1/005 integration focused:182 passed. Earlier expanded focused284 passed; full release regression covers the final source.
- Full safe/offline:1287 passed /1 skipped,53.02 seconds, exit0.
- Ruff src/tests: clean. git diff --check: clean.
- Build: exit0. Frozen self-check: exit0. Clean staged release scan: RELEASE_SCAN_OK.
- Deployed self-check: exit0. Real hidden idle GUI self-check: exit0, INSO_V1.3 title,
  已停止, 开始询价, no business thread. Original V1.2 running GUI remains untouched.
- Exact commands and early resolved failures: EXECUTION_LOG.md.

## Read-only acceptance / production config
Exact title 报价输入, metadata target count1, gid489913321 confirmed.
A1:AZ40 read returned zero rows; real header row/input row/first column UNKNOWN.
Formal V1.3 existing production config contains confirmed gid and null unknown geometry,
failing closed before polling. BLOCKED LIVE CONFIG. Metadata acceptance PARTIAL;
LIVE_SELECTOR_ACCEPTANCE=UNKNOWN. Fixed CDP reachable/profile unchanged. Actual Google
button/dialog/session, INSO page structure and Script refresh remain live-only UNKNOWN.
No popup assumptions were promoted to verified facts.

One separately Owner-authorized live-order acceptance remains necessary after Owner
establishes/verifies input geometry. No business acceptance was performed by Executor.

## Release and preserved assets
- Deployment: D:\Program_Leo\INSO_Leo\dist\INSO_V1.3\INSO_V1.3.exe
- V1.3 SHA256: FB8AA11FC2B300BA1B56D08FD2AC9B6122405E67C31A0361DF21CC09B700EC16
- Backup: D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-006-before-v13-20261007-144306\INSO_V1.2
- Original and backup V1.2 SHA256:
  1A49C9650BA531F2299326FFC89761D0391CD5F2C0FE32327DDD0736BD5C3E84
- Prior V1.3 backup: D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-006-before-final-closure-20261007-145551\INSO_V1.3
  SHA256 CADF5EA32B2F443D77BC86871714E042DC3E404D37221394131238CB1E1F8B31
- V1.2 EXE still present. Production/research configs byte-for-byte unchanged.
- V1.3 uses its own local config copies in the existing format, referencing original
  runtime SQLite/history/OAuth/profile/research output assets. No second database/session.
- Initially proposed shared-config mutation rejected by automatic approval review;
  not executed. Safer deployment above approved and completed. No blocked approval remains.

未执行未经Owner授权的真实采购、真实报价写入或更新报价。
No SMTP sent during execution/testing; no production Start; no runtime database migration
executed. Source/packaging is delivered for independent review; live business readiness remains
blocked by explicit production configuration and live-only acceptance UNKNOWNs.
Branch feature/v1-3-integration; exact commit/remote equality reported in final delivery.
RFQ-006 已提交 CEO Review。
