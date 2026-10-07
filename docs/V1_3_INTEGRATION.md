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
