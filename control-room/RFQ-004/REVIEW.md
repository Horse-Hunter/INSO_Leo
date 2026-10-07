# RFQ-004 CEO Independent Review — 2026-10-07

**Status:** COMPLETE  
**Verdict:** CHANGES_REQUESTED  
**Reviewed Executor HEAD:** `bece24be349c382d6b5703128663382f4549a62e`

## Summary

RFQ-004 的主体方向正确，以下部分经独立代码 Review 未发现新的阻塞问题：

- 从 RFQ-003 REVIEWED_DONE 基线独立创建 `feature/v1-3`；
- V1.2 `未发` 扫描保持原语义，V1.3 新增精确 `发给采购` 只读扫描；
- V1.3 不创建新的 inquiry_id，输出继续携带原 `inquiry_id / record_identity`；
- 复用现有下方 `Stock_VenQuote` 查询、分页、settlement、exact MPN 规则；
- 72 小时窗口使用 Asia/Shanghai aware time，边界为 inclusive；
- 多条记录只按记录时间选择最新，不做价格/品牌/数量等业务筛选；
- `日期 → 制单人` 14 列使用独立 raw payload 保留显示文本，parsed time 不覆盖原日期；
- 查询成功但 72 小时内 0 条正确表达为 `NO_RECENT_QUOTE`；
- 查询失败与 0 条结果分离，复用初次 + 3 次 retry / 180 秒可中断等待；
- V1.3 正常相邻订单没有 V1.2 的 180 秒行间冷却；
- 人工验证仍走共享 INSO GLOBAL_STOP，并保护 human-needed page；
- 未接 Google 写入、更新报价、总调度、GUI/邮件和正式发布，符合 RFQ-004 边界；
- Executor 报告的 focused 48、full safe/offline 1101/1、Ruff、diff 均与提交范围相符。

但当前 V1.3 source identity failure 被错误升级成 GLOBAL_STOP，而且候选在处理前一次性全解析，会导致“一条有问题的报价行阻塞全部报价”。这违反 Owner 已确认的 V1.3 单行隔离原则，因此不能标 REVIEWED_DONE。

## Blocking Finding

### B1 — HIGH — 单行 source identity 问题会 GLOBAL_STOP，并在处理第一条前阻塞整个 V1.3 批次

Owner 已确认的 V1.3 总原则是：

> V1.3 某一行订单遇到问题，只影响这一行；Owner 会单独处理该行报价流程并修改状态，程序继续下一条。只有共享 Google / INSO / CDP / ledger 等基础设施故障才全局停止。

当前 `read_v13_candidates()` 会：

1. 一次性读取全部 `发给采购`；
2. 尝试先把所有 observed rows 与历史 workflow item 绑定；
3. 任意一行匹配数量不是 1，立即抛：
   `V12Fault(FaultScope.GLOBAL_STOP, "SOURCE_IDENTITY_UNRESOLVED")`；
4. 任意一行 MPN 不可用，同样直接 GLOBAL_STOP；
5. 因为解析发生在真正逐行 query 前，所以即使前面已有完全正常的报价行，也不会先处理。

这把“单行 source/identity 数据问题”错误当成了“共享基础设施故障”。

同样地，单行在 query 前 re-read 时出现 `SheetRecordConflict` / ledger identity conflict，当前会经通用异常路径升级为 `V13_READ_UNAVAILABLE` GLOBAL_STOP。

这与 RFQ-004 的“每行独立 closed-loop”以及 Owner 的 V1.3 故障隔离基线不一致。

### Additional concrete identity edge case

当前 `relocate_quotation_source()` 完全复用 `relocate_record()` 的“非 Brand snapshot 必须全表唯一”策略。

因此如果 Google 中存在两笔不同订单，但它们碰巧有相同：

- importance
- MPN
- quantity

并且状态都已变为 `发给采购`，

即使两笔订单仍各自在原来的 row_position、历史 inquiry_id 完全不同，当前 resolver 仍会因为全表存在两个 snapshot match 而将两笔都视为 unresolved。

这种情况不应该变成全局停机。

原 row_position 不能成为新的永久 identity，但在“原位置仍然存在且完整 snapshot/status-transition 可验证”的情况下，可以作为现有 record_identity 的第一安全定位锚点；只有原位置不再匹配时，再进入 unique relocation fallback。若 fallback 仍歧义，则只把该行作为 row-level failure，不能拖死其他 V1.3 行。

## Required Repair

只修 source candidate / identity isolation，不扩大 RFQ-004 范围。

1. V1.3 必须真正逐行隔离：
   - 一条 `发给采购` 的 identity/MPN/source-row 问题 → 当前行 typed row failure；
   - 后续候选继续；
   - 不得 GLOBAL_STOP；
   - RFQ-004 暂未接 GUI/邮件，可先用明确的 result/error DTO 表达，供 RFQ-006 映射“红色 + 229 + 下一条”。

2. GLOBAL_STOP 只保留给共享基础设施：
   - Sheets 整体 read/auth/schema 不可用；
   - workflow ledger 整体不可用；
   - INSO auth/manual verification；
   - INSO query retries exhausted；
   - shared CDP/session infrastructure failure。

3. 不要在真正逐行处理之前，因为某个 later candidate 的 row-local identity failure 让整个 batch 失败。
   - valid row 应按源表顺序正常产出结果；
   - bad row 产出 row-level failure；
   - 后续 valid row 继续。

4. 改进定位顺序：
   - 首先检查 original `record_identity.row_position` 当前是否仍对应同一订单（允许唯一授权的 `未发 → 发给采购` 状态变化，以及现有 persisted UPDATED brand）；
   - 若原位置不再匹配，再使用现有 unique relocation；
   - 不生成新 inquiry_id；
   - 不用 fuzzy matching；
   - 无法可靠定位时只产生当前行 row-level failure。

5. 保持“行移动不是新订单”：
   - 能唯一 relocate 时仍使用原 inquiry_id / original record_identity；
   - DTO 不应改写原 identity。

## Required Regression Tests

至少新增：

1. **valid + bad + valid 三行**
   - 第1行 identity 正常；
   - 第2行 source identity unresolved；
   - 第3行 identity 正常；
   - 结果应为：第1行正常读取 → 第2行 row-level failure → 第3行继续读取；
   - 不产生 GLOBAL_STOP；
   - normal rows 仍各自 fresh tab；
   - bad row 不进入 INSO query。

2. **两个完全相同 snapshot 的不同订单，原位置未移动**
   - same importance / MPN / quantity，可同品牌；
   - 两个不同 original inquiry_id / row_position；
   - 状态均从未发变为发给采购；
   - 两行都必须映射回各自 original inquiry_id；
   - 不能因为 snapshot 非唯一而失败。

3. **原位置已变化但可唯一 relocate**
   - 继续复用 original identity/inquiry_id。

4. **原位置已变化且 relocation 真正歧义**
   - 只当前 row failure；
   - 下一行继续；
   - 不创建新 ID。

5. **Sheets 整体 read failure**
   - 仍然 GLOBAL_STOP，证明没有把共享故障误降级。

6. 保留现有 query retries exhausted / manual verification GLOBAL_STOP 测试。

## Verification Required

修复后重新执行：

- RFQ-004 focused tests；
- full safe/offline pytest；
- `python -m ruff check src tests`；
- `git diff --check`。

仍然禁止：

- 真实 Save / Save-and-Send；
- Google 写入；
- 更新报价；
- SMTP；
- Apps Script；
- 正式 V1.3 打包；
- 覆盖当前 V1.2 EXE。

## State transition

`REVIEW_REQUIRED → CHANGES_REQUESTED`
