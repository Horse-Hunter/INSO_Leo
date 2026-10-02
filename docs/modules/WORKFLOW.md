# Workflow 模块

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
