# V1.3 integration / local deployment

RFQ-006 extends the same ProductionBackend poller. One cycle runs all V1.2 worksheets
then all V1.3 worksheets, then the existing interruptible 900-second wait. No overlapping
business worker. V1.2 local pause leaves V1.3 polling; shared faults stop both.
V1.2 reviewed row cooldown/restart/one-click submission behavior remains canonical.
V1.3 read results settle through RFQ-005 immediately, with no ordinary row cooldown.

## Production configuration
Use the existing runtime/production.json. V1.3 frozen releases always require the
quotation configuration; source composition enables it with v13_enabled=true.
V1.3 uses its own production.json/research.json with existing shared resource paths.
V1.2 config remains byte-for-byte unchanged. Required quotation_input keys:
- gid: exact metadata sheetId string for unique title 报价输入 (489913321)
- input_row=1; first_column=1; header_row does not exist
QUOTE_INPUT_GEOMETRY CONFIRMED by Owner, 2026-10-07. Header NONE / NOT APPLICABLE.
The target is '报价输入'!A1:N1, intentionally blank and headerless. QUOTATION_COLUMNS
specifies the INSO raw14 order, never Google header text. Position6 is 供方税点
(native data-field Tax), verified live and explicitly confirmed by Owner on2026-10-07;
the previous 供方返点 spelling was incorrect. Write all14 strings with RAW;
readback preserves leading zeros, decimals, whitespace, newlines and empty cells.
Metadata title/gid is revalidated before each write and before UI opening. Missing/invalid
geometry or metadata mismatch globally stops before write/open/click. No header reads.
Actual fixed Chrome/CDP acceptance confirmed the unique drawing button and existing-price
Script result. Use exact visible 报价工具 menu readiness (30s), then a unique actionable
named 更新报价 control or observed drawing overlay. Ambiguous/missing controls fail closed.
No coordinates, direct Script invocation, new browser, profile or cookie changes.

## Durable state / rollback
V13 holds share the existing workflow DB, with a single additive table. Final ROW_FAILED
only; no-quote and interrupted unfinished quote operations do not create holds.
Holds reconcile strictly by snapshot/identity first. If relocation fails, the original
worksheet/observed position is only an automation barrier and human-status safety anchor,
never business identity. 发给采购 blocks query/update despite edited MPN/brand/quantity;
采购已报价 closes the hold and completes GUI state. Missing/unknown status retains it;
unrelated rows continue. No fuzzy matching or new inquiry is permitted. Unknown operation,
reader/updater or result-contract errors globally stop with V13_INTERNAL_FAILURE, no new hold.
Typed source errors and reviewed RFQ-005 exhaustion remain row-local.
Notification enqueue is recoverable after a crash between hold and outbox commits.
Existing notification ledger/SMTP is reused; operational notifications have NULL inquiry
rather than invented business identities. Operational pending/sending/retry statuses
are ignored by the old V1.2 worker, preserving rollback. Existing business commands remain
unchanged. Migration uses a verified backup, one transaction and unchanged V1.2
user_version; new code still accepts original V1.2 schema. No history table is dropped.

V1.3 has its own runtime/config files using the same production.json/research.json format.
V1.2 config files remain byte-for-byte unchanged. Existing SQLite/history/notification/OAuth/
profile/research output are referenced through resolved absolute paths, without copying a
diverging workflow database. Existing V1.2 logs are retained; V1.3 logs use its own runtime.
V1.2 EXE remains installed. Single-instance mutex is intentionally shared between versions.
Do not run both production GUIs/cycles. The bounded --idle-self-check constructs the real
hidden dashboard with Start disabled, never runs business workers, and exits; it can verify
widgets while the Owner's original V1.2 GUI remains open. It is not a live-business acceptance.

All website SOURCE_UNAVAILABLE results enqueue sanitized owner229 alerts via the existing
notification ledger/QQ SMTP worker. Keys include inquiry/site/fixed failure category; repeated
polls/restarts deduplicate. Provider exception/HTML/tokens never enter the message. Website,
inquiry, known MPN and a fixed reason are included, with 请人工检查网站登录/可用性.
INSO authentication globally stops; IC.net pauses V1.2 and lets V1.3 continue; other websites
continue Research. Existing IC/INSO manual/fault alerts are suppressed for the same incident.
Delivery retry remains pending without changing business scope.

## Owner quotation policy and bounded completion
Exact MPN + inclusive rolling72h selects the lowest positive eighth-column 供方未税价
(InPrice), comparing supported currencies in RMB through the existing ECB USD/HKD provider.
Ties prefer newest, then first capture. Invalid/negative values are skipped; if valid prices
are all zero, select newest zero without FX. Preserve raw14, source dates and currency.
Unknown currencies fail row-locally; unavailable official FX stops globally.

Result dialog waits30s independently of click/navigation10s. The parser accepts observed
更新完成 / 成功填入 / 已有价跳过 and reviewed legacy aliases, with strict single-row counts.
Reject stale/ambiguous results before click. A confirmed inserted1 or skip1 is Script success.
After unique 确定, wait up to30s for Script running notice to end before advancing; retain the
page and stop globally on unconfirmed settlement. Script owns input cleanup; never clear it.

Both successful result types then require the original source row to become 采购已报价 within
30s. If it remains unsettled, log a warning, project the existing pale-yellow warning style,
and enqueue the existing durable owner229 SMTP notification. SOURCE_STATUS_NOT_UPDATED retains
its automation barrier; no second Script click or forced source status write. Owner correction
closes the hold. Other failures retain reviewed semantics and other rows can continue.

## Evidence and release boundary
One previously authorized DRV8833PWR existing-price path actually produced 更新完成 / 成功填入0行 /
已有价跳过1行. Exact 确定 was dismissed, Script ended, source remained manually restored 发给采购.
Owner confirms delayed Script cleanup. No repeat live acceptance was performed for these fixes.
First-insert live status transition and real SMTP delivery remain UNKNOWN; offline regressions
cover both result kinds, delayed status at30s, warning/hold/dedup and interruptible waits.
BuildOnly and frozen self-check produce a review candidate. This new increment needs independent
review; do not overwrite the installed release before review. See RFQ-006 FINAL_REPORT for checks.

## Research no-result recipient
Only RESEARCH / NO_MATCHING_PRODUCT exception mail additionally targets shawn@inso-hk.com.
Other phases/reasons/recipients are unchanged. Reuse existing recipient ledger/worker/SMTP;
version only this changed immutable command payload. No historical replay or real test mail.

## Owner interval correction — 2026-10-07
Normal V1.2 Research/purchase row cooldown is120 seconds, replacing the previous180-second
row policy. Canonical V12FlowCoordinator passes120 to the existing interruptible backend
wrapper; GUI derives the same deadline and starts at 冷却02:00. No trailing last-row cooldown.
Owner expanded scope: INSO query/duplicate-history/quotation retries also become120s;
quotation normal rows retain0s; scheduler900s.
Prior180s fixed-wait clauses are historical and superseded by this request.
Chrome bootstrap maximum allowed configured timeout180s is a validation limit, not a fixed
180s wait; existing default30s and browser configuration/protection are unchanged.

## Idle Research login keepalive — 2026-10-07
Owner requests independent V1.3 maintenance after consecutive empty Research polls and actual
30 minutes. Base d8204b5; previous120s interval, quote selection/update/status warning and
Research-only Shawn recipient changes retained. New increment remains REVIEW_REQUIRED.

Canonical V12FlowCoordinator observes pending未发 records across all worksheets without an
extra Sheets read; begin_poll_cycle resets observation. Any pending row resets idle window,
including invalid/preexisting rows, avoiding false empty detection. Failed reads never reach
the maintenance boundary; purchase pause/manual/global/stop conditions skip maintenance.
V1.3 backend runs maintenance serially AFTER completed combined business work and BEFORE
notifications/next900s countdown. Two empty polls AND elapsed30min are required; the immediate
startup poll cannot cause a15min refresh. Restart begins a fresh idle window.

Reuse _run_login_sweep/sweep_sites and all existing site login recipes. Borrow active poller
CDP rather than creating a second Playwright; otherwise attach fixed Chrome using existing
acquirer. No new scheduler/worker, login recipe, browser/profile/cookie or SMTP system.
Background sweep does not publish SiteLoginReport/callback/popup or bring failed tabs to front.
Site failures continue other sites, generate sanitized operational owner229 outbox commands,
and never produce business hold/pause/global stop. Notification insertion errors log warning.
Stop checked between sites and immediately after sweep, respecting existing bounded site waits.

All-success cleanup uses existing park_shared_cdp with a blank background tab. Failed/manual
or preexisting nonblank pages are preserved; successful owned sweep page is closed, Chrome stays
open. Existing manual one-click report/foreground behavior remains intact. New idle window begins
after sweep completion, followed by ordinary15min countdown; failure does not block that countdown.

Exact verification: focused273 PASS16.49s; final maintenance20 PASS1.17s;
full safe/offline1414 PASS/1 SKIP55.90s; Ruff/diff PASS. BuildOnly/frozen self-check/scan PASS.
Latest candidate EXE6FE03F2442377CA49A1A919A1715C401F83B8C481033F98802017AE8F11157B9,
superseding earlier candidate hashes. Installed release/configs not overwritten pending Review.
No real login/SMTP/order replay/quotation update/purchase; real keepalive login and SMTP delivery
remain UNKNOWN. No dependency added; CEO review files unchanged.

## CEO CHANGES_REQUESTED repairs and Owner S-as-A — 2026-10-08
Base c596adafd4e14881e292851e51c7375841e92c20 (CEO review265d6e9 retained).
Only B1, B2 and Owner tier interpretation are changed. Previous passed quotation/mail/wait/
scheduler contracts remain canonical. This section supersedes historical "S invalid; Owner must
change S to A" statements; raw source S is never rewritten.

B1: before exact确定 click, arm a read-only MutationObserver and click-capture latch on that
button. PREPARED→CONFIRM_CLICKED→RUNNING_OBSERVED→SETTLED. Observe visible正在运行脚本 after
confirmation; keep start and end evidence even if the API click returns after DOM transitions.
Wait start max30s then end max30s. Absent initially is not settled. Any observation/DOM/CDP
uncertainty raises GLOBAL_STOP GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED, pending stays true,
owned Google page remains open, no next open/write/click, no automatic resubmit or input clear.

B2: minimal protected target-ID set in ProductionBackend; register pre-existing nonblank pages
and failed/manual keepalive pages. All backend park sites (_close_inso_order_tab poll finally,
_open_research_session, _run_login_sweep) use preservation-aware wrapper. Live protected targets
survive cleanup; detach/unready cleanup never closes their browser/pages. Owner-closed targets
are pruned from current context, then canonical one-blank park resumes. Stable CDP target IDs
survive new Playwright page wrappers after detach. Existing protected boundary suppresses another
login sweep; detached page checks use canonical attach in check-only mode without early relogin.
Business operations still own their normal page closures. No second browser/page manager.
Real poll-loop regression runs two cycles, borrowed keepalive, poll-finally and Owner-close
cleanup, proving human/preexisting pages survive and business continues with229 notification.

S: existing _tier normalization maps rawS to effectiveA, otherA/B/C unchanged. All routing,
important-order, duplicate handling and procurement use that single effective tier. Pending
records, WorkItem and identifying_snapshot preserve rawS. Legacy skippedS naturally resumes
same inquiry through existing _resume_after_input_fix/alert recovery; customer-name remains
active. D/blank/UNKNOWN remain invalid. No DB migration/replay or Sheets tier writeback.

Verification results and new candidate hash are recorded below after final checks.
No new live action is authorized or executed; first-insert live/SMTP acceptance remains UNKNOWN.
