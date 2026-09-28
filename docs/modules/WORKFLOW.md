# Workflow 模块

## 职责

Workflow 负责 Scheduler、`inquiry_id`、持久状态、retry、duplicate prevention 和跨模块编排；只消费模块 Public Contract，不复制模块内部业务逻辑。

## V1

- 每 15 分钟扫描配置 worksheets；同一时间只允许一个 Sheet Poll。
- 每轮全部 pending records 入队；Research worker concurrency = 1。
- dedup identity：`spreadsheet + worksheet + row_number`；retry 属于同一 work item。
- 状态：`QUEUED | RESEARCHING | RETRY_WAIT | COMPLETED | FAILED`；旧 `MANUAL_REVIEW` 仅兼容读取。
- Research：`SUCCESS/PARTIAL_SUCCESS → COMPLETED`，`EXCEPTION → FAILED`，`RETRYABLE_FAILURE → retry`。
- 默认执行机会：initial + 15m + 30m + 60m。
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

业务规则由 `v12_rules.py` 持有：
- rolling 168h exact duplicate evaluation
- important-order notification eligibility
- independent purchase type/purchaser routing
- six-space AI input
- exact AI validation

Notification：
- per-recipient durable ledger
- initial + 1m + 5m + 15m
- 仅 typed transient failure 重试
- SENT / PERMANENT_FAILURE / UNKNOWN 不自动重发
- notification failure 不阻塞 purchase

Save safety：
- Save dispatch 只允许从已验证 AI state 进入
- dispatch 前持久化 `UNKNOWN_WRITE_OUTCOME`
- restart 或 unknown outcome 不得自动再次 Save
- 只读 reconciliation 才能确认 saved/not-saved；ambiguous/unreadable 进入人工 review
- confirmed absence 后重新允许写入需要显式 operator acknowledgement

## 边界

Workflow 不解析 Research Excel 业务细节，不实现 Sheets relocation，不直接操作 INSO DOM，不自行发送 SMTP。模块职责变化看 `MODULE_INDEX.md`；当前阶段 wiring 看 `CURRENT_TASK.md`。
