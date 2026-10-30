# Workflow 模块

## V1.5 requirement-scoped TP tasks (offline, REVIEW_REQUIRED)

`workflow.tp_research` adds workflow_requirements to the existing SQLite file,
using verified backup and the existing nullable-inquiry outbox upgrade. TP task
identity is independent of V1.4: source spreadsheet/sheet/physical row + requirement
kind. Price and Brief position are not task identity. No workflow_items parent
is synthesized. Ordinary inquiry state and existing Research Excel remain unchanged.

Automatic TP runs once per task; a changed price after completion does not reopen
it. Explicit manual rerun creates a generation after fresh source/Brief checks.
Researching/pending/retryable/unknown delivery blocks manual duplication; the same
existing worker owns send retries. Unknown/SENDING-after-crash remains quarantined.
Crash after enqueue adopts the immutable command key; before enqueue only read-only
research can recover. SQLite BEGIN IMMEDIATE claims arbitrate automatic/manual work.

`TP_RESEARCH` commands have inquiry_id=None and a TP/generation command_id. Owner
now authorizes future messages to linan229@qq.com and shawn@inso-hk.com. Delivery
uses existing recipient_results; any UNKNOWN/SENDING/pending/retryable recipient
blocks manual generation, and completion requires all recipients to settle.
Historical SENT commands keep their original recipients/content. No duplicate
sender/outbox/daemon. `production.json.tp_enabled` opt-in assembles TP in the original poller, after its
ordinary native page scope, using the same 15-minute wait. GUI third action
重跑 TP 价格 uses the existing idle-command condition and same poll thread.
TP-only historical rows are exposed by the existing GUI Order DTO; its legacy
inquiry_id display field holds a tp_ UI key, not a persisted V1.4 inquiry.
The Owner-authorized V1.5 frozen product enables the same TP phase by default;
an explicit false opt-out still wins. Earlier products/source default disabled.
The shared V1.4 production config does not need modification. The same named
mutex prevents simultaneous V1.4/V1.5 process ownership of runtime.

Owner 2026-10-25 TP mail correction: tp_mail supplies escaped HTML plus the
existing plain-text alternative. Opening explicitly compares valid RMB minimum
with TP; dates use Asia/Shanghai calendar days, current prices say 现价. Empty
sources/missing second/invalid prices and verbose windows are omitted; an entirely
empty second column is absent. Queue identities and delivery handling are unchanged.

## RFQ-003 当前 V1.2 恢复边界（2026-10-07）

以 `control-room/RFQ-003/TASK_SPEC.md` 为当前规则，不实现 V1.3。
复用现有 inquiry_id、record_identity、SQLite、notification ledger 和唯一生产链。
单行无报价、数据错误、重复、明确提交前失败、已点击后确认失败及单格状态写回
失败均闭环后继续；真实下一行开始前可中断等待 180 秒，末行/空轮询不等待。
INSO 查询初次加最多三次 fresh-tab 重试，每次间隔可中断 180 秒；不是行间冷却。
IC.net / V1.2 内部异常 MODULE_PAUSED；INSO 认证、查询重试耗尽及共享
Sheets / ledger / CDP 不可用 GLOBAL_STOP，GUI 不退出。SMTP 独立幂等重试。
重启仅只读投影历史中断为红色；正常 Start 只隔离实际执行过的未闭环订单。
仅预入队/预建 pending 事件不算执行证据，尚未开始的后续行按源表顺序继续。
真正中断订单不自动恢复或再采购；可能已发送和已闭环订单的边界不变。
人工将源状态改为发给采购后，原 identity 经唯一 relocate/re-read 自动 HUMAN_COMPLETED。
源码关键字段校验型号、品牌、正整数数量及重要程度；修正的无效输入可后续正常识别。
与以下历史恢复/重试描述冲突时，本段及 RFQ-003 优先。

## 职责

Workflow 负责 Scheduler、`inquiry_id`、持久状态、retry、duplicate prevention 和跨模块编排；只消费模块 Public Contract，不复制模块内部业务逻辑。

## V1

- 每 15 分钟扫描配置 worksheets；同一时间只允许一个 Sheet Poll。
- 每轮全部 pending records 入队；Research worker concurrency = 1。
- dedup identity：`spreadsheet + worksheet + row_number`；retry 属于同一 work item。
- 状态：`QUEUED | RESEARCHING | RETRY_WAIT | COMPLETED | FAILED`，外加 `MANUAL_REVIEW` 作为**不被自动认领**的静置态（数据异常跳过等）；`claim_due` 只认 `QUEUED`/`RETRY_WAIT`。
- Research：`SUCCESS/PARTIAL_SUCCESS → COMPLETED`，`EXCEPTION → FAILED`，`RETRYABLE_FAILURE → retry`。
- 默认执行机会：initial + 15m + 30m + 60m。
- 数量单元格不是数字：跳过并记明确原因，不发起 Research、不消耗重试预算（`MANUAL_REVIEW` + `last_error='INVALID_QUANTITY_INPUT'`）；表格修正后自动恢复，恢复时从表格刷新快照。
- 崩溃恢复：进程在 Research 中被强杀后，重启在**任何 worker 启动之前**把残留的 `RESEARCHING` 占用释放回 `QUEUED`（`attempt_count` 减 1、不低于 0），Research 只读故可安全重排。
- SQLite 持久化 work item、opaque Sheet identity、attempt/retry 与结果；runtime DB/journal 不进 Git。

## V1.2

V1.2 在独立 additive schema 上保存：
- current business state
- append-only event history
- active alerts
- duplicate result
- notification recipient ledger
- purchase state

核心流程：

`Duplicate Check → Research → post-Research routing`

Duplicate read 技术失败不阻止 Research，但 duplicate 未确认前不得采购。

已完成 Research 但停在「重复待确认」的记录，由正常轮询复用
`confirm_duplicate_and_route` 恢复：只处理本轮 Sheets 仍待处理、识别快照未变、
Research 已 COMPLETED 且最新重复结果未确认的记录。重新读取下方采临时询价；
只有同 inquiry 的 CONFIRMED 结果才接续既有路由。失败继续等待，不再 Research、
不清库、不重置采购状态。已确认、已准备草稿或离开待处理的记录不得再次采购。

业务规则由 `v12_rules.py` 持有：
- rolling 168h exact duplicate evaluation
- important-order notification eligibility
- independent purchase type/purchaser routing
- six-space AI input
- exact AI validation

Notification：
- 重复路由不能重建已创建的同 inquiry/kind 通知；先核对原 command、kind
  和全部收件人 ID/地址，一致时保留原正文与台账。由原通知 worker 处理待发/可重试
  收件人，SENT 不再次外发；存储层原有正文/收件人冲突保护不变。
- A 类必发通知不依赖 Research 成功：完成一次调研尝试且重复检查明确为非重复时，
  即使 Research 需重试也创建原格式通知。未知价格不伪造；重复未知不发重要通知。
  采购仍受原 Research/事实/AI 校验边界约束，不能因通知放行而绕过。
- per-recipient durable ledger
- initial + 1m + 5m + 15m
- 仅 typed transient failure 重试
- SENT / PERMANENT_FAILURE / UNKNOWN 不自动重发
- notification failure 不阻塞 purchase

Save safety：
- Owner 2026-10-02 授权客临时询价单次保存并发送，新增接线沿用当前 purchase state 与事件表，无新 migration。最终提交不在 Executor 测试范围内；Owner Review 后下一笔真订单首次验证。
- 正常路由发现已有任意 purchase state 时不重新建立草稿或再次提交，包括旧版校验完成但未保存的草稿；不批量补发历史测试单。
- 生产 writer 可返回持久化的 SAVED / UNKNOWN / MANUAL_REVIEW，Coordinator 不再把它们折成 AI 校验失败；SAVED → PURCHASE_RECORDED，未确认 → PURCHASE_EXCEPTION，GUI 明示“提交结果待确认（不会自动重发）”。
- Save dispatch 只允许从已验证 AI state 进入
- dispatch 前持久化 `UNKNOWN_WRITE_OUTCOME`
- restart 或 unknown outcome 不得自动再次 Save
- 只读 reconciliation 才能确认 saved/not-saved；ambiguous/unreadable 进入人工 review
- confirmed absence 后重新允许写入需要显式 operator acknowledgement

## 边界

Workflow 不解析 Research Excel 业务细节，不实现 Sheets relocation，不直接操作 INSO DOM，不自行发送 SMTP。模块职责变化看 `MODULE_INDEX.md`；当前阶段 wiring 看 `CURRENT_TASK.md`。

## RFQ-004 isolated V1.3 read cycle

`v13_quotation.V13QuotationCycle` binds sent-source rows to original ledger inquiry_id/record_identity, re-reads/relocates before each attempt and processes serial fresh owned operation tabs. Returns ordered QUOTE_FOUND, normal NO_RECENT_QUOTE or typed ROW_FAILED with fixed safe reason codes. Source identity/MPN/re-read conflicts end only that row without tab/retry/wait; later valid rows continue. Missing/ambiguous identity is never invented; current-row location is only an observation. Shared Sheets/ledger read failures remain GLOBAL_STOP. No enqueue/new ID/Google write/SMTP/production scheduling. `inso_query.run_inso_query` is the shared extracted RFQ-003 query retry: initial+3, close then interruptible180s, exhaustion GLOBAL_STOP; both V1.2 launcher readers reuse it with unchanged classification. V1.3 has no normal row cooldown. Protected authentication failures bypass retry and retain the human page. Final integration remains outside RFQ-004.

## RFQ-005 quotation update service

`v13_quote_update.V13QuotationUpdater` consumes RFQ-004 results, preserves no-quote/row-error inputs, serially establishes raw input and invokes the narrow Google UI contract. Full input write/read gets initial+3 attempts per establishment stage; update initial+3 re-established attempts; source already quoted prevents resubmit. Confirmed popup leads only to max3 short interruptible source reads, never repeated clicks. Original identity/competition validation is read-only. Success UPDATED_INSERTED/UPDATED_ALREADY_EXISTS; row failures use fixed codes; shared Sheets/schema/auth/ledger/CDP failures GLOBAL_STOP. No scheduler/GUI/mail/quarantine or source status write.

RFQ-005 B1/B2: Owner corrected the target title to `报价输入` on 2026-10-07;
the former “报价输入子表” is rejected. Each update attempt validates metadata
binding and headers before opening the configured gid. A binding/header fault
becomes GLOBAL_STOP with zero tab opening, writes or clicks. Canonical factory
supplies the same explicit location to Sheets and UI; UI does not guess the title.
Existing four-write/four-update budgets and three short source reads are unchanged.

## RFQ-011 sales exception notifications

OrderExceptionNotifications composes V12Store/V12NotificationWorker/QQSMTPTransport
with existing1069 sender/Core Vault. Two recipients retain independent existing
1/5/15-minute retry classification and dedupe. Payload is only PI, optional model,
one human situation sentence and treatment; no internal diagnostics.
Development persistence is .tmp/v14-notifications/outbox.sqlite3, separated from
production DB. Unchanged old schema requires a V1 FK anchor: notification-only
MANUAL_REVIEW rows, never eligible for inquiry claiming; no V1.2 business state.
Existing PURCHASE_EXCEPTION and EventType are reused. No new enum/schema version,
mail polling or purchase/quotation state changes. Interrupted in-flight sends
recover UNKNOWN through existing policy and are never blindly resent. A later
V1.4 invocation resumes this isolated outbox; retry worker ends on app shutdown.

## RFQ-014 notification copy (Owner 2026-10-10)
All production SMTP message builders to229/shawn were audited, including owner-only
alerts and separately delivered recipients/retries. Mail presents business identity,
useful sheet location, actual status/uncertainty and relevant human action. Internal
inquiry/command/reason/stage codes remain in the ledger but not message text.
No recipient/trigger/dedup/retry/SMTP/queue mutation change. Already-created payloads
remain immutable; future messages use revised copy after source reload/authorized
release. Synthetic previews: control-room/RFQ-014/MAIL_PREVIEWS.md. Review pending.

Latest RFQ-014 Owner recipient exception: V1.4 sales-entry exceptions now go only
to229. An owner-address guard delegates to unchanged QQSMTPTransport and returns
terminal PERMANENT_FAILURE for obsolete non229 recipients before SMTP, including
old queued shawn entries; existing command payloads are not rewritten. This only
applies to isolated V1.4 notification service, not inquiry/quotation/follow-up mail.
Active loaded GUI retains old behavior until next source reload/authorized release.


## Owner correction: missing brand (2026-10-12)

Blank or case-insensitive `UNKNOWN` Brand means no known brand, not invalid
inquiry input. Valid model/quantity/tier records enter the existing Research path
with `brand=None`; existing ICNET resolves the brand. Procurement still requires
a real brand after Research. This overrides the RFQ-003 pre-Research brand gate;
model/quantity/tier checks and procurement validation remain in force. Previously
input-skipped records may resume on the next normal poll without a brand edit.


## Owner brand writeback repair (2026-10-12)

The canonical V1.2 inquiry worker now uses the existing safe BrandUpdater.
Resolved missing/UNKNOWN brands are written to only the uniquely relocated
Brand cell using the existing cached noninteractive write service, then read back.
An existing real source brand is never overwritten. The post-Research source
check accepts the resolved brand only when the ledger records confirmed UPDATED;
other source changes remain conflicts. Completed procurement is never rerun for
brand writeback. Executor deployment does not independently write live cells.


## Owner Google transient-read correction (2026-10-13)

Transient source Google GET failures get one retry at the existing read boundary.
If both attempts fail, skip the current poll and notify229 once per failed cycle,
then use the existing15-minute poll wait and continue normally when reads recover.
No new timer/state machine, business retry, write retry or V1.4 order polling.
Permanent auth/permission, schema, database and INSO failures retain stop guards.
This supersedes GLOBAL_STOP only for identified exhausted transient Google reads.


## Owner SHAHAB / inquiry-mail correction (2026-10-13)

SHAHAB is an independent customer rule, overriding the old normalized A default.
Estimated RMB total >=20,000 (including equality) uses 颜浩坚 / 需要问全价格
and important inquiry notice; below uses 陈熙 / 普通询价 without important notice.
Inventory does not alter this rule. Unknown total does not guess ordinary routing
or send important notice. Other A/S, B/C and duplicate-stop rules remain unchanged.
Source snapshots/IDs and existing submission/dedup guards stay intact; no replay
or migration. New SHAHAB sheet records display SHAHAB instead of invented A.
Important/duplicate/exception email copy uses 询价; model-difference email subject
is 【INSO】采购报价差异. Historical outbox payloads remain immutable.

## Owner procurement-price refresh (2026-10-18)

Reuse the V13 cycle/updater/holds and existing15-minute scheduler. Candidates now
include 发给采购 / 采购已报价 / 已报价给客户. Carry the observed source status
through candidate/result/hold serialization; old serialized holds default to
initial sent mode. Do not settle refresh failures by seeing unchanged quoted
status. Preserve the original inquiry ID and reviewed exact relocation.
ProcurementPriceStore is one additive workflow table (inquiry FK, Decimal RMB
price), backed up through existing verified migration support, without changing
V12 user_version or copying quotation/customer payloads. Missing historical
baseline => record only; lower positive or zero-to-positive => existing updater.
Owner CEO整改: possible refresh-click delivery plus uncertain result advances
the existing comparison minimum and enqueues a deduplicated229-only notice with
old/new RMB net prices. Return BASELINE_RECORDED + UPDATE_RESULT_UNCONFIRMED, not
ROW_FAILED/Google success; no blocking Hold or same-run re-click. Pre-click
failures retain baseline. Shared input busy returns QUOTE_FOUND for later poll,
not a durable barrier. Initial sent-mode behavior remains unchanged. Customer-sale prices are
never read as a baseline. INSO exports a shared pure procurement_price_rmb helper
from the existing selector; conversion/72h/payload rules are unchanged.
Initial status advancement remains required; later source status must stay exact
and a skip popup cannot prove overwrite. Counts/follow-up remain sent-only.
See tasks/2026-10-18-quotation-price-refresh.md for evidence and live UNKNOWNs.


## Customer-quoted automatic refresh age (2026-10-28; source-only)

Historical policy, superseded by RFQ-016 below.

`WorkflowStateStore.inquiry_intake_at(inquiry_id)` returns the existing immutable
created_at only for that exact ID (timezone-aware, or None). No schema/migration.
The audited event set has no customer-send timestamp. `quotation_age` therefore
uses an already-cached uniquely source-bound Brief rfq_date inquiry-day proxy,
otherwise this intake-time proxy; neither is a true customer-send date.
V13QuotationCycle checks only automatic 已报价给客户, after original source/status/
uniqueness checks and before Operations.open. Inclusive Shanghai calendar7-day
or rolling168h cutoff; future/invalid/missing date returns QUOTE_AGE_UNVERIFIED.
Expired returns QUOTE_AGE_EXPIRED. Fixed skip counters/result codes only, no
hold/mail/updater/price baseline. Safe no-effect results retain Option A closed
boundary. Explicit original manual composition disables only this age filter;
all realtime permissions/identity/SENT/UNKNOWN/Stop gates still run.
发给采购/采购已报价/TP and supplier72h selection are unchanged. Not deployed.


## Task-center display intake (2026-10-29)
WorkItem.created_at adds an optional immutable read-only intake projection from
an already existing column on canonical all_items/get/claim reads. No schema,
migration, new query, or business scheduling order. Unknown/malformed/naive
historical intake uses the same None policy as inquiry_intake_at; item reads
must retain previous business behavior. GUI Order.received_at is display only.
Idle startup read_startup_interruptions may collect the same dates through an
optional intake_times map in its existing query, without changing returned
interruption DTOs, authorization, quarantine or making writes.


## RFQ-016 source-only implementation (2026-10-30)

The common automatic_admission contract owns Shanghai calendar7d and previous-calendar-month gates, exact source binding, trustworthy RFQ date and explicit LOCAL_INTAKE_APPROXIMATION fallback. Missing/conflicting/invalid/future dates exclude automatic work locally; brand writes, existing queues/retry/continuations, quotation effects, TP claims/recovery and reminders use the same policy. Owner single-order scope is bounded to that one original invocation and does not revive automatic retries or unknown effects.

Existing outbox adds review_json/suppression_reason through the existing quiesced migration with verified backup. SUPPRESSED is a known non-send outcome, not SENT/UNKNOWN or a transport failure. Generation and dispatch both review evidence; original SMTP transport is reused, direct operational SMTP bypass is closed. Stable incident keys use fixed module/reason/original event, bounded cycle evidence and actual successful recovery; original SENT/UNKNOWN delivery is immutable, including exact legacy command aliases. No new queue/table/timer/client.

Native quotation effect uncertainty is distinct from pre-click failure. Hold JSON stores only a bounded effect proof marker in its previously discarded quotation slot, retaining legacy-reader compatibility; never raw prices. Sheet status alone and manual rerun cannot settle UNKNOWN. Source observations update GUI DTO current-status/freshness alongside immutable procurement history and active protections, without additional source reads or writes.

Source tests are not deployment evidence. RFQ-016 remains NOT_DEPLOYED until separately authorized release and business verification.


### RFQ-016 CEO remediation and detailed-mail subtask (NOT_DEPLOYED)

Unknown quote attempts now commit a write-ahead barrier in the original hold
before the native click. The same newly admitted attempt may close it only after
positive native completion. Ordinary close/manual retry cannot clear an old
UNKNOWN. Unknown-result hold persistence precedes notice and price baseline;
missing mail credentials/evidence cannot remove protection. Baseline policy stays
unchanged for production; an unwired standalone updater conservatively retains
the old baseline. Crash-after-intent-before-click may therefore require manual
verification even if the click never occurred; safety takes precedence over blind
retry. No raw quotation data is added to the hold.

Persistent order alerts require a fresh current source snapshot at enqueue AND
SMTP. Prior incident proof/last_success cannot certify an unreadable current row.
Important/duplicate notices reject completed customer states before sending.
Purchase follow-up additionally checks the exact original episode, current
`发给采购` and the unchanged strict three-working-hour rule.

The new process-lifetime mail service polls read-only229 IMAP every120seconds,
independently of business Start/Stop/Pause/manual operations. One receiver and one
research/delivery worker are bounded; active capacity64 includes reports awaiting
SMTP. First mailbox epoch establishes UIDNEXT baseline; changed UIDVALIDITY
establishes another baseline, preserving previously accepted task/outbox records.
Identity uses account+UIDVALIDITY+UID; Message-ID is ancillary. Same-model distinct
UIDs remain distinct requests. Strict standard sender and decoded subject matching
ignore bodies/attachments. Matching uses full normalized MPN equality and unique
latest verified dates; ties/conflicts degrade to unit-price-only research.

`workflow_mail_cursor` and `workflow_mail_research` are additive in the existing
DB, backed up before creation, with scoped transactions. Ordinary business and
mail-only dispatch/recovery use disjoint claims in the same V12 outbox/worker/SMTP.
No recovery loop can mark the other live sender abandoned. Results commit before
enqueue; restart repairs that gap; SENT/UNKNOWN never replay. Terminal deliveries
leave active scans. Actual resource ownership uncertainty persists a local block
across restart; no automatic global reset or unknown-target cleanup is permitted.
Temporary transport/closed-page errors stay local. Confirmed IMAP auth intervention
requires three completed native auth failures; verified resource protection and
SMTP UNKNOWN need accurate immediate owner action, deduplicated by the original
incident ledger. Report delivery uncertainty is one unresolved service incident,
not a fresh owner alert per report. Shawn gets reports only;229 gets technical
intervention notices only. Missing Vault configuration is a local instruction.

All-source acquisition outage fails IMAP tasks after three attempts without an
empty success report. A still-valid important/follow-up business notice can retain
its original purpose with explicit six-source unavailable content after bounded
recovery; it never claims that the market has no offers or invents values.
