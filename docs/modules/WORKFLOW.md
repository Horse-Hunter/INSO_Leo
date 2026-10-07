# Workflow 模块

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
