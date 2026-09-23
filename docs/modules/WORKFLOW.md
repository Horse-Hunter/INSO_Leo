# Workflow 模块

## 公共职责

Workflow 负责跨模块编排、Scheduler、`inquiry_id`、流程状态、retry、duplicate prevention 和模块衔接。只消费模块 Public Contract，不承载模块内部业务逻辑。

## V1 执行

- 每 15 分钟触发一次 Sheets 待处理记录查询；同一时间只允许一个 Sheet Poll。
- Poller 与 Research Worker 解耦；Research concurrency 为 `1`。
- 将 Sheets 提供的 `record_ref` / `record_identity` 视为 opaque identity；不得从 row number 推导永久身份。
- 创建 `inq_<UUIDv4>` 格式的 `inquiry_id` 并持久化到本地 SQLite；不得写入 Google Sheets。
- 状态：`QUEUED`、`RESEARCHING`、`RETRY_WAIT`、`COMPLETED`、`MANUAL_REVIEW`、`FAILED`。
- 按 `RESEARCH.md` 的 canonical input 调用 Research，并原样透传 `importance_raw`。
- Research 确认幂等 Excel 落盘后，才把 `SUCCESS` 或合格的 `PARTIAL_SUCCESS` 映射为 `COMPLETED`；`MANUAL_REVIEW_REQUIRED` 映射为 `MANUAL_REVIEW`；`RETRYABLE_FAILURE` 进入 retry。
- 将 `resolved_brand` 传给已确认的 Sheets Brand 更新；Sheets Brand conflict 不撤销已完成 Research。

## Retry 与恢复

默认一次 initial attempt，加 15、30、60 分钟后的三次 retry；耗尽后转为 `FAILED`。不使用固定 stale timeout。重启时，先通过 Research Public Contract 检查遗留 `RESEARCHING` 是否已完成，再恢复完成状态或安排 retry。

## 边界与 UNKNOWN

V1 只编排 Sheets → Research → 本地 Excel；Research 内部可查询 INSO read-only 历史价格，但主动采购 INSO Module 与 Quotation 属于 Future Version。未来主动采购不得从 `MANUAL_REVIEW` 自动发布采购需求。依赖方向归 `MODULE_INDEX.md`；Workflow 不嵌入协作模块的 adapter 或业务逻辑。

仍为 `UNKNOWN`：SQLite schema/migration、duplicate-prevention algorithm、详细状态转换 guard、Scheduler 机制、Research completion-confirmation Contract 和运行恢复细节。
