# V1.3 approved repair production deployment

status: complete
owner: Codex deployment executor
created: 2026-10-08
updated: 2026-10-08

## problem / goal
Owner authorized "ok，部署打包覆盖吧" following CEO PASS. Deploy the exact reviewed repair candidate while preserving production state.

## authority / source
- CEO PASS: tasks/2026-10-08-v13-live-readiness-ceo-review.md.
- Deployed source HEAD: 4c53c2c1159c7abca36cebf061223b5bbe07e3fb.
- Final production implementation: e3137a6fa280d0b9c649e7f762d4039da7b67ecb.
- Exact approved EXE SHA256: 4777E6000A861EC4E1C881CD9692E18B8B21FB8A1F6672DD82DF2115E5D6E6CC.
- Used the already-reviewed candidate; no rebuild and no business code modification.

## deployment / acceptance
- [x] Formal path: `D:\Program_Leo\INSO_Leo\dist\INSO_V1.3`.
- [x] Full pre-deployment backup: `D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.3_20261008_144623_5b0765e1`; 2183 files verified against the original directory before replacement.
- [x] Only `INSO_V1.3.exe` and `_internal` replaced; all 2179 deployed asset hashes match approved candidate.
- [x] Deployed frozen `--self-check`: PASS.
- [x] Deployed `--idle-self-check`: PASS; real dashboard rendered, STOPPED, no business thread.
- [x] Deployed `--cdp-self-check`: PASS; existing fixed session connected, one context and one page, no business start.
- [x] Release scan: PASS on byte-identical mirror of deployed EXE/_internal, excluding retained production runtime data.
- [x] 3950 protected files checked: zero hash changes (production DB/backups, runtime configuration, OAuth/credentials and previously inventoried protected assets).
- [x] V1.2 before SHA256: 340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F.
- [x] V1.2 after SHA256: 340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F.
- [x] Production workflow DB SHA256 unchanged; no deployment migration.
- [x] Fixed Chrome profile and CDP configuration retained; no new browser, close, cookie clearing or tab cleanup.

## boundaries / completion
No source business changes, historical replay, real procurement, Save/Save-and-Send, quotation input write, update quotation, Apps Script, real SMTP or production business state modification. Only diagnostic logs were written to the deployed runtime. Canonical CDP attachment may refresh its local session backup; no protected hash difference was observed.

Existing offline verification of approved source: focused 760 passed; full 1559 passed / 1 skipped; Ruff and diff check PASS. These were not redundantly rerun for an assets-only deployment.

Evidence: main repository `.tmp/v13-deploy-20261008_144623_5b0765e1/plan.json` and `verification.json`, kept untracked. This deployment validates packaging, idle GUI and CDP attachment; it does not claim a new real purchase or quotation business run.

V1.3 正式生产版本已部署，业务轮询尚未由部署任务启动。
