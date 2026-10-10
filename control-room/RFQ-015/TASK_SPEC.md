# RFQ-015 V1.4 authorized release
Status: DEPLOYED / COMPLETE
Owner2026-10-10 states review complete and authorizes packaging/deployment of
7a5728388fc14cd685521d520e23fbfa19536988. Prior no-package gate superseded.
Record Owner confirmation and synchronized independent PASS in RFQ-014/CEO_REVIEW.md.
Reuse canonical build/spec/entry; add1.4 version, frozen diagnostics and include
existing development pypdf6.10.0/tzdata2026.4 in isolated local build venv. Copy
trusted existing release venv and bundled libraries; no other project env changes.
No business logic rewrite. Build staged generic onedir artifact, self-check and
secret/runtime scan; verify idleGUI/CDP/Vault readiness without business clicks.
Deploy independent D:/Program_Leo/INSO_Leo/dist/INSO_V1.4, retain V1.3/V1.2 assets.
Reuse protected existing credentials/profile/production ledger via resolved local
config paths; preserve V1.4 local receipt/outbox data with safe SQLite snapshots.
Allowed local release/config/shortcut/diagnostic writes, not production DB/workflow
writes, SMTP, Sheets, Save/submit or auto-start business. Never kill active worker.
Create new V1.4 desktop shortcut, open idle app. Verify protected hashes and rollback
paths, report executable hash/sourceSHA/limitations, commit/push release records.

Checks: build venv lock matches/pip check PASS; focused122/full1848+1skip/Ruff/diff;
generic scanner PASS; frozen self/idle/Vault+IMAP/CDP checks0;2875 asset hashes match;
4396 protected hashes unchanged, V1.4 receipt counts preserved. New shortcut and
idle release launched. V1.3/V1.2 retained for rollback; no automatic business run.
