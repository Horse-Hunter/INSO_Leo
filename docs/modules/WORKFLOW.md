# Workflow 模块

## 公共职责

Workflow 负责跨模块编排、Scheduler、`inquiry_id`、流程状态、retry、
duplicate prevention 和模块衔接。只消费模块 Public Contract，不承载模块内部
业务逻辑。

## V1 执行

- 每 15 分钟扫描全部已配置目标 worksheets；同一时间只允许一个 Sheet Poll。
- 每轮把所有 pending（`未发`）records 入队，不只处理第一条。
- Poller 与 Research Worker 解耦；Research worker concurrency 固定为 `1`，
  逐条处理 queued 或到期 work。
- Workflow V1 dedup identity 固定为
  `spreadsheet + worksheet + row_number`。同一 identity 在 SQLite DB 生命周期内
  只创建一个 work item；retry 属于同一 work item。
- row number 只用于 Workflow V1 dedup。Sheets 的 `record_ref` /
  `record_identity` 仍作为 opaque identity 完整持久化和透传；Brand 写回不得只
  使用 row number，必须由 Sheets 执行 relocation 与 conflict check。
- V1 不使用 UUID。`inquiry_id` 使用由 dedup identity 确定性派生的非 UUID
  内部格式，持久化到本地 SQLite 并传给 Research，不写入 Google Sheets。
- 状态仅为：`QUEUED`、`RESEARCHING`、`RETRY_WAIT`、`COMPLETED`、
  `FAILED`；旧 SQLite 记录中的 `MANUAL_REVIEW` 仅保留兼容读取。
- ResearchInput 使用 canonical 字段：`inquiry_id`、`mpn`、`brand`、
  `quantity`、`importance_raw`；其中 Sheets 提供的 `importance_raw` 原样透传。
- `SUCCESS` 和 `PARTIAL_SUCCESS` 映射为 `COMPLETED`；
  `EXCEPTION` 映射为 `FAILED` 且不 retry；
  `RETRYABLE_FAILURE` 进入 retry。
- 已有 SQLite 中的 `MANUAL_REVIEW` 状态继续兼容读取，但新 Research 结果不再映射到该状态。
- `resolved_brand` 存在时，Workflow 把原始 opaque identity 和 Brand 交给
  Sheets safe Brand update。Brand conflict 不覆盖人工值，也不撤销已经完成的
  Research 状态。
- Research 的 `SUCCESS`、`PARTIAL_SUCCESS` 和 terminal `EXCEPTION` 都保留既有
  safe Brand update 行为；`EXCEPTION` 仍保持 Workflow `FAILED`，Brand updater
  的 conflict/failure 不改写该终态。`RETRYABLE_FAILURE` 不执行 Brand update，
  即使 retry budget 最终耗尽并进入 `FAILED` 也不执行。

## SQLite、Retry 与恢复

- 本地 SQLite 持久化 work item、opaque Sheet identity、稳定 `inquiry_id`、
  状态、attempt、retry 时间和 Brand update outcome。数据库、journal、WAL、
  SHM 与其他 runtime 文件不得进入 Git。
- 默认共四次执行机会：initial attempt，失败后分别等待 15、30、60 分钟；
  第四次仍失败则转为 `FAILED`。
- Launcher 在 `ResearchService.execute()` 前的 CDP/bootstrap/readiness 准备失败使用
  独立的 preparation error：Workflow 撤销该 transient claim 和 attempt，不创建
  `RETRY_WAIT`，再由 launcher fail closed 到人工处理。此路径不属于 Research retry；
  真正的 Research exception 与 `RETRYABLE_FAILURE` 继续使用 15/30/60 retry。
- 单进程重启后，遗留 `RESEARCHING` 表示上次执行被中断，不使用 stale
  timeout。恢复必须先按 `inquiry_id` 调用 completion-confirmation seam：确认
  已完成则恢复相应最终流程状态，未确认完成才消费 retry budget 并进入
  `RETRY_WAIT` 或 `FAILED`。

## 边界、V2 与 UNKNOWN

Workflow 不直接读取或解析 Research Excel，不复制 Research 业务逻辑，也不
实现 Sheets adapter、relocation 或 conflict rules。V1 只编排 Sheets → Research
→ 本地 Excel；Research 内部可查询 INSO read-only 历史价格，但主动采购 INSO
Module 与 Quotation 属于 Future Version。

UUID、Google Sheet 状态写回与正式订单生命周期属于 V2，本模块 V1 不提前实现。

Research completion-confirmation Public Contract 仍为 `UNKNOWN`。当前 Workflow
只提供窄的可注入 completion-check seam，并可用 test double 验证完整恢复逻辑；
真实 Research wiring 必须等待 Research 模块未来确认该跨模块 Contract。

## V1.2 additive seam (Stage 2A)

`src/workflow/v12_contracts.py` defines the V1.2 contracts and enums. `v12_store.py`
adds an independent SQLite persistence surface for business state, append-only
events, multiple scoped active alerts, duplicate results, notification recipient
delivery ledger, and durable purchase state. Existing `workflow_items` meanings
and CHECK constraints remain unchanged. State/event/alert mutations share one
transaction; event update/delete is rejected by SQLite triggers.

`UNKNOWN_WRITE_OUTCOME` is persisted before a future Save Data dispatch boundary.
Restart cannot dispatch again. Only typed read-only reconciliation can move it;
ambiguous/unreadable outcomes require manual review, and confirmed absence needs
explicit human acknowledgement before rearming. No Save Data adapter is wired.

The Stage 2A worker is transport-injected and tested only with a fake. Delivery
is recipient-scoped with at most four attempts (initial plus 1/5/15 minute
retries); SENT, PERMANENT_FAILURE and UNKNOWN are never automatically retried.
Notification failure alerts are scoped per command and recover only after every
intended recipient for that command is confirmed SENT. Notification failure does
not gate purchase state.

The transport Public Contract is `NotificationTransportResult(outcome,
reason_code)`, where `outcome` is one of SENT, RETRYABLE_FAILURE,
PERMANENT_FAILURE or UNKNOWN and `reason_code` is a `ReasonCode`. The transport
adapter owns provider-specific classification. An unexpected exception at the
Workflow boundary is recorded as UNKNOWN and is never guessed to be transient.
Only a typed RETRYABLE_FAILURE is scheduled again.

Purchase routing returns INDETERMINATE with no quotation type or purchaser when
a B/C tier needs a threshold decision but `estimated_total` is missing. Save
dispatch is accepted only from AI_RECOGNIZED. The ordinary purchase-state
setter permits PRE_SAVE_READY to move to AI_RECOGNIZED or VALIDATION_FAILED;
VALIDATION_FAILED cannot be reset through that setter. After authoritative
absence and human acknowledgement, the validated AI state is retained for a
controlled later attempt.

`workflow_v12_inquiry_state` stores the observed `customer_name` and the Sheets
`CustomerNameSource` value together. A missing name records the existing data
quality event/alert in the same transaction. Production orchestration is not
yet wired to this additive V1.2 snapshot API.

`v12_rules.py` contains deterministic pure decisions: exact `dup-mpn-v1`
rolling-168-hour duplicate evaluation (latest timestamp only, unresolved tie is
ambiguous), post-Research routing that blocks on an unconfirmed duplicate
result, important-order notification eligibility, independent full-price
procurement routing/purchaser selection, six-space AI input formatting, and
exact AI recognition verification under `ai-mpn-v1`.

These seams are not wired into the production launcher. They do not authorize
live INSO, SMTP, Sheets, or production database activity.
