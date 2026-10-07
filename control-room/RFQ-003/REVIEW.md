# RFQ-003 CEO Independent Review — 2026-10-07

**Status:** COMPLETE  
**Verdict:** CHANGES_REQUESTED  
**Reviewed Executor HEAD:** `448c26c14e48ad12e76c2b1c91182b8490c686b3`

## Owner Summary

RFQ-003 的主要方向正确，以下部分经独立代码 Review 没发现新的阻塞问题：

- V1.2 / future V1.3 的 fault-scope 边界已显式区分为 module pause 与 global stop；
- INSO 人工验证仍保留 human-needed page，RFQ-002 边界没有被明显回退；
- IC.net 与其他 Research 来源的故障隔离方向符合 Task Spec；
- Save-and-Send 新增 durable click receipt，已点击但后确认不明可进入独立 `SUBMIT_UNCONFIRMED`；
- Google `发给采购` 写回失败进入黄色人工处理状态，不触发重新采购；
- INSO 查询采用初次尝试 + 最多 3 次 fresh-tab retry，等待可中断；
- 180 秒 V1.2 行间冷却放在“确实存在下一行”之前，末行/空轮询不额外等待；
- SMTP 失败不作为采购停止条件；
- GUI 新增黄色/红色状态区分；
- Executor 记录的 focused 978/1、full safe 1025/11、Ruff、diff、build/self-check/scan 与提交范围一致。

但启动后的“处理中断恢复”存在一个会直接影响真实批量订单的阻塞问题，因此当前不能标 REVIEWED_DONE。

## Blocking Finding

### B1 — HIGH — 重启会把“尚未开始的后续订单”一起误标为处理中断

Task Spec 明确要求：

> 程序中断后，只把那条未闭环订单标红并跳过；V1.2 从下一笔正常订单继续。

当前实现无法区分“真正开始处理后中断的订单”和“同一轮只是提前入队、尚未开始的后续订单”。

当前路径：

1. `V12WorkflowCoordinator.process_pending()` 会先把本轮所有有效 `未发` 行 enqueue；
2. 在真正串行处理第一行之前，又会把所有新 enqueue 行统一写成 `DUPLICATE_CHECK_PENDING`；
3. 如果程序在第一行处理中、或者第一行闭环后的 180 秒冷却期间退出，后面的第 2/3/... 行仍只是 `QUEUED`，实际从未开始 Research/采购；
4. 下次启动时 `initialize_run_state()` 遍历 **所有** workflow items；
5. `interrupted_business_state()` 对任何非 closed state 都返回 `INTERRUPTED_UNSENT`（除非已有可能发送证据）；
6. 因此那些从未开始的后续 `QUEUED / DUPLICATE_CHECK_PENDING` 行也会被 `mark_interrupted()` 改成 MANUAL_REVIEW，并在 GUI 全部标红、自动队列全部跳过。

结果是：

- Owner 只需要人工处理“崩溃时正在做的那一笔”；
- 但程序会把同批后续尚未开始的正常订单也全部冻结；
- 重启后并不能按 Task Spec “从下一笔正常订单继续”。

这在多行批次中尤其容易出现，因为当前实现本来就会先 enqueue 全部行，再串行处理。

现有 regression 没覆盖这个边界：`test_restart_quarantines_and_sheet_manual_completion_releases_red_only` 只创建了一条 workflow item，因此无法发现“active row + untouched queued rows”的误隔离。

## Required Repair

只做最小修复，不要重构整个队列：

1. 启动 quarantine 必须只针对“有证据证明此前已经真正开始处理且未闭环”的订单。
2. 仅仅 `QUEUED` / 仅仅被本轮预先写成 pending、但从未成为 active row 的后续订单，启动时必须保持可处理。
3. Save-and-Send 已 armed/clicked 或其他已有真实执行证据的未闭环订单仍必须按现有 possible-sent 规则隔离，不能放回自动队列。
4. 增加离线 regression，至少覆盖：
   - 同一批 3 条订单；
   - 第 1 条已经开始但未闭环；
   - 第 2、3 条只入队、尚未真正开始；
   - 模拟重启后只第 1 条变红/被跳过；
   - 第 2、3 条仍能按源顺序继续处理；
   - 再覆盖“第一条闭环后处于 180 秒 cooldown 时程序退出”的场景：后续 untouched rows 不能被误标中断。
5. 原有 `处理中断（可能已发送，请先核对）`、人工改为 `发给采购` 后解除红色、RFQ-002 验证页保护都必须继续 PASS。

## Verification Required

修复后重新执行：

- RFQ-003 focused tests；
- full safe/offline pytest；
- Ruff `src tests`；
- `git diff --check`。

这是生产 `src/` 修复，因此需要重新构建并覆盖 V1.2：

- build；
- frozen/deployed self-check；
- clean staged release scan；
- idle launch only；
- 新 EXE SHA256；
- 新 backup path。

不需要也不允许为了这个修复运行真实订单、Save/Save-and-Send、SMTP、Sheets 写入或真实验证码。

## State transition

`REVIEW_REQUIRED → CHANGES_REQUESTED`
