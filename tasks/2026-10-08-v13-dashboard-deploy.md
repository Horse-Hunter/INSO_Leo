# Task: Deploy approved V1.3 dashboard source counts

status: complete
owner: Codex deployment executor
created: 2026-10-08
updated: 2026-10-08

## authority / goal
Owner explicitly authorizes backing up the current formal V1.3 and deploying the DB11A02B candidate. CEO PASS / REVIEWED_DONE is recorded at df64762ae6ad0893879814e847888246f5b5a93f in tasks/2026-10-08-v13-dashboard-source-counts.md.

## facts / requirements
- Source HEAD: df64762ae6ad0893879814e847888246f5b5a93f; production implementation 91299e1dafaa14d8f449beae8191b4901e098bd3.
- Approved SHA256: DB11A02BCB4929EA9B45A973AD086A163D4FE1ED09AF72ED9AB0C222A8819E5E.
- Existing formal SHA256: 4777E6000A861EC4E1C881CD9692E18B8B21FB8A1F6672DD82DF2115E5D6E6CC.
- Reuse reviewed candidate, no rebuild/code changes. Fresh timestamped complete backup verified before replacement.
- Replace only formal EXE/_internal. Preserve V1.2, DB/backups, OAuth/credentials/config, Research/SMTP, fixed Chrome profile/CDP.
- No formal V1.3 process was running at initial deployment check; verify again immediately before replacement.

## scope / acceptance
- [x] Candidate and installed asset hashes match.
- [x] Fresh full backup verified.
- [x] Deployed frozen self-check, idle GUI and asset release scan pass.
- [x] Protected state hashes unchanged.

## non_scope
No business polling, procurement, Save/Save-and-Send, quote write/update, Apps Script, SMTP, historical replay or business DB mutation. No source changes; no rebuilt binary. Deployment audit record remains local unless separately authorized for upload.

## completion
- Source / CEO reviewed HEAD: df64762ae6ad0893879814e847888246f5b5a93f.
- Deployed path: `D:\Program_Leo\INSO_Leo\dist\INSO_V1.3`.
- Deployed SHA256: `DB11A02BCB4929EA9B45A973AD086A163D4FE1ED09AF72ED9AB0C222A8819E5E`; exact approved candidate, no rebuild.
- Fresh full backup: `D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.3_20261008_155555_e50fac00`. All 2184 original files verified before replacement; retired assets also retained.
- Installed manifest: 2179 assets match approved candidate byte for byte.
- V1.2 before SHA256: `340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F`.
- V1.2 after SHA256: `340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F` (identical).
- Protected manifest: 3953 files checked, zero changes. Production DB/backups, OAuth/credentials/config, Research/SMTP and inventoried fixed Chrome assets retained.
- Deployed --self-check: PASS; --idle-self-check: PASS (real GUI rendered, stopped, no business thread); --cdp-self-check: PASS (one context, one existing blank page, no business start).
- Release scan: PASS against byte-identical deployed-assets mirror, excluding preserved runtime/config files.
- Idle GUI exited automatically; fixed Chrome was not launched, closed or cleared. Canonical CDP attachment can refresh its session backup; no protected hash changes observed.
- No business code modified. Only this deployment task document changed in tracked source.
- No real procurement, Save/Save-and-Send, quotation input/write/update, Apps Script, SMTP, replay, remote source changes or production polling executed.
- Detailed inventories: main `.tmp/v13-deploy-20261008_155555_e50fac00/plan.json` and `verification.json`, retained untracked. Deployed self-checks only wrote diagnostic logs.
- Deployment document is saved locally; no automatic remote upload is part of this task.

V1.3 GUI统计修复正式生产版本已部署，业务轮询尚未由部署任务启动。
