# CEO CHANGES_REQUESTED B1 repair report

Status: REVIEW_REQUIRED
Base/CEO Review HEAD: e0ea036ca90437e7a31794d5a15323785f450b45
Branch: codex/v13-readiness-repair
The original CEO Review text/verdict is preserved without edits. This is not CEO approval.

## B1 repair

Removed EventType.PURCHASE_STATUS_RECORDED and NotificationKind.PURCHASE_FOLLOW_UP,
including their GUI event mirror/message. Neither new value is persisted in V1.2 tables.
The optional pure GUI timing-start message was removed as permitted by the repair request;
working-time/reminder behavior is preserved.

New V1.3-only additive table in the same workflow.sqlite3:
workflow_v13_purchase_follow_up_episodes

Minimal columns: episode_id (stable primary key), inquiry_id (foreign key to the canonical
workflow inquiry), confirmed_at (UTC aware timestamp). No MPN/brand/quantity/row guessing,
no duplicate business snapshot and no V1.2 schema version change. Startup makes a verified
backup before first additive creation; repeated migration preserves data and is idempotent.
Old verifiers/readers safely ignore this table.

PurchaseCompletionActions calls record_confirmed only after write_purchase_status_safely
returns changed=True with confirmed readback. Already-sent historical rows are not backfilled.
Sidecar persistence is outside the Sheets-write exception handler. A real SQLite insertion
failure propagates GLOBAL_STOP / WORKFLOW_LEDGER_UNAVAILABLE, preserves durable SAVED and
PURCHASE_RECORDED plus remote 发给采购, and never requeues/replays procurement.

Reminders use old-compatible NotificationKind.PURCHASE_EXCEPTION with dedicated
purchase-follow-up:<SHA256(episode_id)> command IDs and follow-up-specific subject/body.
Canonical source binding, strict >3 working hours, weekday Beijing work windows, held-row
checking and both recipients are unchanged. Original outbox/worker/recipient retry is reused.
Repeated polls/restart deduplicate; a new confirmed episode independently restarts timing.

## Rollback compatibility evidence

Compatibility tests extract the actual historical src trees with git archive and run their
own readers and coordinator in separate subprocesses. Assertions ensure imports belong to
those old source snapshots and both old closed enums exclude the prohibited new values.
No current-code substitute is used for the old reader.

Formal V1.3 source: 03f4bf3328b0931b4bdc5dc05865b9f35322cf7e
Fetched current feature/v1-2 source: d75a1fa1db5371b59363bd733538f7fd0fb245e6

For each revision, two cases PASS: reminder PENDING and RETRYABLE_FAILURE.
Each DB is created/touched by current synthetic workflow, durable fake purchase confirmation,
actual canonical 未发 -> write -> readback -> 发给采购 logic, sidecar insertion and reminder
creation. The reminder is not sent successfully before rollback.

Both preserved source contracts prove:
- V12Store initialization and schema verification/migrate_v12 succeed;
- event_history parses all persisted old event values;
- initialize_run_state completes and durable SAVED remains safe;
- claim_due_notifications parses PURCHASE_EXCEPTION and both recipients;
- new sidecar table is present and safely ignored;
- no prohibited event/kind values exist, user_version remains 1201.

Tests: tests/workflow/test_follow_up_rollback.py (6 passing cases, including four rollback
variants plus real sidecar failure and verified/idempotent migration).
Recipient retry proves Owner succeeds once while only Shawn retries; no second command.

## Verification

Focused follow-up/rollback + RFQ-003/004/005/006/008 + GUI/launcher/CDP/Findchips/keepalive:
760 passed in 50.60s.
Full safe/offline: 1559 passed, 1 skipped in 72.00s.
Skip remains the environment's unsupported symlink-creation case.
Ruff src tests scripts/windows_release_entry.py: PASS.
git diff --check: PASS.
V1.3 BuildOnly: PASS. Release scan: PASS.
Final frozen --self-check: exit 0.
Final frozen --idle-self-check: exit 0.
Final frozen --cdp-self-check: exit 0; connected=True, unique_context=True,
business_started=False.

Accepted CDP/Findchips/manual-protection logic was not rewritten in this repair.
Original 120-second purchase cooldown, zero normal quotation row delay, 15-minute scheduler,
B1 quarantine/no replay, script settlement latch, headerless raw14 and rerun hold boundaries
remain covered by the focused/full regressions.

## Candidate / production protection

New candidate EXE SHA256:
4777E6000A861EC4E1C881CD9692E18B8B21FB8A1F6672DD82DF2115E5D6E6CC

Old candidate 22756C738C7DE7DEB278ABB17E8738A4B99C781E0116A71E4A8C1C7FF20E8431
is superseded and must not be deployed. New candidate is not deployed.

Formal V1.3 remains:
7ECE6917BF77E263E1E56BC528A63EE0798404DB1D03D494499B94A4A16B663F
Formal V1.2 remains:
340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F

Production DB hash matches its original deployment baseline. Formal EXE, production config,
research config, local credentials/OAuth cache and INSO cookie backup checked before/after
frozen probes were unchanged. No production database migration/backup was performed.

Canonical persistent CDP attach normally may refresh the local INSO cookie backup. This
repair does not claim it has zero filesystem effects. For this validation only, a copied
isolated config disables that optional refresh; the existing endpoint was attached/detached,
Chrome was not launched/closed, tabs were not cleaned, and production config was untouched.

No real procurement, Save/Save-and-Send, quotation write/update, Apps Script, SMTP,
production Google modification or unguarded production polling was executed.

Scope limit preserved: a crash after remote confirmation but before local episode commit
cannot be used to infer an unrecorded historical time. Untimed rows are skipped.
The previously undeployed bad candidate has never touched production; no production cleanup
or enum migration was performed or required.

Conclusion: after the repaired new feature stores a sending episode and leaves a follow-up
pending/retryable, both preserved V1.3 and V1.2 reader/startup contracts can continue consuming
that same shared workflow DB. Submitted for independent CEO Review; REVIEW_REQUIRED.
