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

## SQLite、Retry 与恢复

- 本地 SQLite 持久化 work item、opaque Sheet identity、稳定 `inquiry_id`、
  状态、attempt、retry 时间和 Brand update outcome。数据库、journal、WAL、
  SHM 与其他 runtime 文件不得进入 Git。
- 默认共四次执行机会：initial attempt，失败后分别等待 15、30、60 分钟；
  第四次仍失败则转为 `FAILED`。
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
