# V1.3 live-readiness + purchase follow-up — CEO Independent Review

Date: 2026-10-08
Status: COMPLETE
Verdict: CHANGES_REQUESTED
Reviewed branch: `codex/v13-readiness-repair`
Reviewed HEAD: `fa8201f05cdad7e30397121e2abecf64facbd463`
Reviewed base: `03f4bf3328b0931b4bdc5dc05865b9f35322cf7e`

## Decision

The CDP readiness repair, Findchips login refinements, manual-login page preservation, working-time arithmetic, reminder threshold, source binding and once-per-episode reminder logic are directionally sound.

However the purchase-follow-up implementation introduces a production rollback blocker in the shared workflow database. The new candidate must not replace the current formal V1.3 release yet.

## B1 — HIGH — New persisted enum values break rollback compatibility with the current formal V1.3 and V1.2 executables

The new increment persists two values that do not exist in the currently reviewed rollback binaries:

1. `EventType.PURCHASE_STATUS_RECORDED` is inserted into the existing shared table `workflow_v12_events`.
2. `NotificationKind.PURCHASE_FOLLOW_UP` is inserted into the existing shared table `workflow_v12_notification_commands`.

The current formal V1.3 baseline `03f4bf...` and current V1.2 branch both have closed enums that do not contain those values.

Their existing persistence readers are strict:

- `V12Store.event_history()` constructs `EventType(row["event_type"])`;
- `V12Store.claim_due_notifications()` constructs `NotificationKind(row["kind"])`.

Therefore, after the new build handles a real purchase and commits a `PURCHASE_STATUS_RECORDED` event, switching back to the currently deployed/reviewed V1.3 or V1.2 can raise while reading that shared DB. A pending/retryable `PURCHASE_FOLLOW_UP` command creates the same incompatibility in the notification worker.

This contradicts the release boundary in this task: the existing `7ECE6917...` formal V1.3 and `340D7F...` V1.2 are being deliberately preserved as rollback paths, and the shared production workflow DB is also being preserved.

The problem is not a SQLite table-version migration. It is a semantic expansion of values stored inside tables consumed by older reviewed binaries.

### Required repair

Do not persist new enum values into existing V1.2-owned columns unless all preserved rollback binaries can parse them.

Use a backward-compatible storage shape for the new follow-up feature. A narrow acceptable direction is:

- keep purchase-follow-up timing/episode state in a new additive V1.3 sidecar table, keyed to the canonical inquiry / sending episode;
- do not insert `PURCHASE_STATUS_RECORDED` into `workflow_v12_events`;
- do not persist `PURCHASE_FOLLOW_UP` as a new notification kind in the old notification table; reuse an existing old-compatible kind such as `PURCHASE_EXCEPTION` with a unique follow-up command ID and follow-up-specific subject/body, while preserving recipient-level retry and once-per-episode dedup;
- project the follow-up-start timestamp to the GUI through an additive DTO/read-only projection rather than a new persisted V1.2 EventType, if the GUI message is still desired.

A different design is acceptable only if it proves the same rollback compatibility and keeps the Owner's requirements unchanged.

### Required compatibility regression

Use a DB produced by the repaired new build and prove all of the following:

1. a newly confirmed `未发 -> 发给采购` episode can be stored and timed;
2. a >3-working-hour follow-up can be pending/retryable in the DB;
3. the same DB can then be opened and read by compatibility fixtures matching the formal `03f4bf...` V1.3 enums/readers without `ValueError` or schema failure;
4. the same DB is likewise readable by the current V1.2 enum/reader contract;
5. old `event_history()`, startup state initialization and notification claiming do not encounter an unknown persisted enum value;
6. an extra V1.3 sidecar table, if used, is ignored safely by old schema verification;
7. rollback compatibility is proven while the follow-up is still pending/retryable, not only after every reminder has been delivered.

No real production order or SMTP delivery is required for this repair.

## Accepted areas

### PASS — CDP readiness diagnosis and bounded attach

The branch keeps the overall attach window bounded at 20 seconds and allows a single attach attempt up to 10 seconds. A Playwright attach timeout is surfaced as `CDP_SESSION_INITIALIZATION_TIMEOUT`, distinct from a missing/unusable CDP endpoint. No code path automatically closes an Owner tab to repair this condition.

The frozen `--cdp-self-check` attaches to an already-advertised fixed CDP endpoint and disconnects without starting business workflow.

Note: because it calls the canonical persistent-session acquire path, a successful diagnostic may refresh the local INSO cookie backup file. It is browser/business non-mutating, but should not be described as literally filesystem-side-effect-free.

### PASS — Findchips login form reuse and bounded retry

The login routine reuses an already-open Findchips sign-in form instead of needlessly reloading it, waits for page/load readiness, a unique visible enabled submit control and the passive verification token when present, and performs at most two ordinary submits.

Only an unconfirmed ordinary submit is retried. Explicit human verification, credential rejection and typed site refusal stop rather than being bypassed or clicked repeatedly. A successful redirect stops further submission.

### PASS — manual-login page preservation

Manual sweep failures now register their pages with the same protected-target mechanism already reviewed for background keepalive. Later normal parking cannot silently close the human repair surface; Owner closure releases protection.

### PASS — purchase follow-up business rule itself

The reviewed arithmetic correctly uses Beijing UTC+8 working windows Monday-Friday 09:00-12:30 and 13:30-18:00, excluding lunch, nights and weekends, with a strict `> 3 hours` threshold.

The follow-up uses canonical V1.3 source binding, skips ambiguous/changed identities and historical untimed rows, runs before quotation-hold skipping so a held row can still remind, addresses both `linan229@qq.com` and `shawn@inso-hk.com`, and does not add a second scheduler or SMTP implementation.

The once-per-sending-episode idea is also correct; only its persistence representation must be made rollback-compatible.

## Verification evidence reviewed

Executor reports for `fa8201f...`:

- purchase-follow-up focused: **144 passed**;
- full safe/offline: **1550 passed / 1 skipped**;
- Ruff: **PASS**;
- `git diff --check`: **PASS**;
- V1.3 BuildOnly: **PASS**;
- release scan: **PASS**;
- frozen `--self-check`: **PASS**;
- frozen `--idle-self-check`: **PASS**;
- frozen `--cdp-self-check`: **PASS**.

Candidate EXE SHA256:

`22756C738C7DE7DEB278ABB17E8738A4B99C781E0116A71E4A8C1C7FF20E8431`

Current formal V1.3 remains:

`7ECE6917BF77E263E1E56BC528A63EE0798404DB1D03D494499B94A4A16B663F`

Current V1.2 remains:

`340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F`

## Release decision

**DO NOT DEPLOY** candidate `22756C...` to the formal production directory yet.

The current formal V1.3 should remain in place until B1 is repaired and the compatibility test proves that a DB touched by the new follow-up feature can still be consumed by both preserved rollback binaries.

The repair is fully testable offline. No repeat real purchase, Save-and-Send, quotation update, Apps Script or SMTP test is required before resubmission.

## Final state

`PENDING CEO REVIEW -> CHANGES_REQUESTED`

---
# B1 rollback-compatibility repair — CEO Independent Re-Review

Date: 2026-10-08  
Status: COMPLETE  
Verdict: **PASS / REVIEWED_DONE**  
Reviewed repair HEAD: `e3137a6fa280d0b9c649e7f762d4039da7b67ecb`  
Repair base: `e0ea036ca90437e7a31794d5a15323785f450b45`

## Decision

The rollback-compatibility blocker from the preceding review is closed.

The repaired implementation no longer writes either rejected new enum value into V1.2-owned persistence. Purchase-follow-up timing is isolated in an additive V1.3 sidecar table, and the reminder continues through the existing outbox using the old-compatible `PURCHASE_EXCEPTION` notification kind.

No new production blocker was found in the repair diff.

## B1 closure — persisted values remain readable by preserved rollback binaries

PASS.

The repair removes:

- persisted `EventType.PURCHASE_STATUS_RECORDED`;
- persisted `NotificationKind.PURCHASE_FOLLOW_UP`;
- the GUI projection that depended on that new persisted event.

The new table is:

`workflow_v13_purchase_follow_up_episodes`

with only:

- `episode_id`;
- canonical `inquiry_id` foreign key;
- timezone-aware `confirmed_at`.

It does not change the V1.2 schema version. Existing V1.2/V1.3 schema verification permits the additive table.

A confirmed episode is written only after the existing canonical Google status transition returns `changed=True`, which already means the `未发 -> 发给采购` write and readback were confirmed. A row that was already `发给采购` returns `changed=False` and is not backfilled.

If the remote status has been confirmed but the sidecar insert fails, the sidecar store maps the SQLite/ledger failure to `GLOBAL_STOP / WORKFLOW_LEDGER_UNAVAILABLE`. The already-durable SAVED/PURCHASE_RECORDED state and remote `发给采购` state are preserved; the purchase path is not requeued or replayed.

## Reminder compatibility

PASS.

Follow-up commands now persist as the already-supported:

`NotificationKind.PURCHASE_EXCEPTION`

with a dedicated deterministic command identity:

`purchase-follow-up:<SHA256(episode_id)>`

The subject/body remain follow-up-specific, both Owner and Shawn remain recipients, and the existing recipient-level worker/retry behavior is reused.

This avoids introducing an unknown notification kind while preserving once-per-sending-episode deduplication.

## Rollback compatibility evidence

PASS.

The new compatibility regression does not emulate the old enums with current code. It extracts the actual historical `src` trees with `git archive` and executes them in isolated subprocesses against a DB produced by the repaired implementation.

Preserved revisions reviewed:

- formal V1.3 source: `03f4bf3328b0931b4bdc5dc05865b9f35322cf7e`;
- current V1.2 branch source: `d75a1fa1db5371b59363bd733538f7fd0fb245e6`.

The current remote `feature/v1-2` HEAD was independently confirmed to be exactly `d75a1fa1db5371b59363bd733538f7fd0fb245e6`.

For both preserved revisions the regression covers outstanding reminder state in both:

- `PENDING`;
- `RETRYABLE_FAILURE`.

The old code successfully performs:

- V12Store construction/schema verification;
- `migrate_v12`;
- `event_history()`;
- startup `initialize_run_state()`;
- `claim_due_notifications()`.

It also proves:

- no `PURCHASE_STATUS_RECORDED` exists in the old event table;
- no `PURCHASE_FOLLOW_UP` exists in the old notification table;
- the follow-up command is parsed as old-compatible `PURCHASE_EXCEPTION`;
- the V1.3 sidecar table is safely ignored;
- `PRAGMA user_version` remains 1201;
- durable SAVED state remains non-replayable.

This directly closes the blocker identified in the previous review.

## Sidecar migration / failure behavior

PASS.

The first sidecar creation takes a verified backup before the additive table is created. Repeated migration is idempotent, foreign-key checks remain clean, and the old schema version is unchanged.

The reviewed failure regression uses a real SQLite trigger to abort the sidecar insert after the source status has already been confirmed. The result is fail-closed global stop with no second purchase write and no reconstructed historical timestamp.

The documented limitation remains intentional: a crash after remote confirmation but before local episode persistence does not guess the missing timestamp on restart; that row remains untimed for this reminder feature.

## Previously accepted readiness repairs

The rollback repair does not rewrite the areas already accepted in the prior review:

- bounded CDP attach and `CDP_SESSION_INITIALIZATION_TIMEOUT` diagnosis;
- frozen `--cdp-self-check`;
- Findchips existing-form reuse, passive-verification readiness and bounded submit retry;
- manual-login protected pages;
- working-time calculation and strict >3-hour threshold;
- canonical source binding and held-row follow-up check;
- RFQ-003 through RFQ-008 reviewed safety boundaries.

## Verification evidence reviewed

Executor reports for `e3137a6...`:

- focused: **760 passed**;
- full safe/offline: **1559 passed / 1 skipped**;
- Ruff: **PASS**;
- `git diff --check`: **PASS**;
- V1.3 BuildOnly: **PASS**;
- release scan: **PASS**;
- frozen `--self-check`: **PASS**;
- frozen `--idle-self-check`: **PASS**;
- frozen `--cdp-self-check`: **PASS**.

New candidate EXE SHA256:

`4777E6000A861EC4E1C881CD9692E18B8B21FB8A1F6672DD82DF2115E5D6E6CC`

The rejected candidate `22756C738C7DE7DEB278ABB17E8738A4B99C781E0116A71E4A8C1C7FF20E8431` remains superseded.

## Live / release boundary

The repair candidate remains undeployed. The formal V1.3 `7ECE6917...` and V1.2 `340D7F7E...` remain unchanged.

No new real procurement, Save/Save-and-Send, quotation write/update, Apps Script, SMTP delivery, production Google mutation or unguarded production poll was required for this repair.

## Release decision

**PASS / REVIEWED_DONE.**

Candidate `4777E600...` is approved for the controlled formal V1.3 deployment step.

Deployment must still preserve the existing V1.2 release, production workflow DB, credentials/OAuth, production/research/SMTP configuration and fixed Chrome profile/CDP assets, with a backup of the current formal V1.3 release before replacement.

## Final state

`CHANGES_REQUESTED -> REVIEW_REQUIRED -> REVIEWED_DONE`
