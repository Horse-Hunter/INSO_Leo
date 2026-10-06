# RFQ-002 CEO Independent Review — 2026-10-06

**Status:** COMPLETE  
**Verdict:** CHANGES_REQUESTED  
**Reviewed HEAD:** `169aa583844695b6faeef62e5ec9193eef64991f`  
**Production EXE source baseline:** `a1bed4094af8a834483c8f9f7852f6e7de0c7ac4`  
**Previous CEO PASS:** superseded; it covered only the earlier checkpoint.

## Owner Summary

### Review 结论

CHANGES_REQUESTED

### 已确认

CEO 已按最新报告独立检查 `e585e88`、`c30e96a`、`a1bed40`、`169aa58`，以及当前 Task Spec、CEO report、execution log、final report 和实际源码。

本轮生产逻辑的主要方向与 Owner 最新要求一致：

- AI 录单生产主链已不再把 ProductID 当作前置校验条件；生产判断只落在型号、品牌、数量。
- 提交后确认仍与下方七天重复历史分离：下方继续完整分页；上方只做已结算首页首行确认。
- 上方确认要求新 BillID、匹配型号和提交时间 ±30 分钟；确认失败不自动再次提交。
- Google 状态写回只在流程结果和持久化采购状态都为 `SAVED` 时进入；写入只允许 `未发 → 发给采购`，并重新定位、重读、单格写入和读回。
- 状态写回失败不改变采购成功状态，也不会重新进入采购提交。
- 新采购异常通知只发 Owner 邮箱，复用现有 notification ledger/worker；同一 inquiry/阶段/原因的已创建命令不会重复创建。
- 非交互 Google 写入只复用或刷新已有受保护授权，不在后台主动弹授权。
- 新 EXE 构建、自检、安全扫描、runtime 保留、旧版本备份和 protected CDP 边界与交付记录一致。

按 Owner 要求，本 Review **没有**重跑已经发送的订单，没有触发真实 Save / Save-and-Send / SMTP / Sheets 写入，也没有为了 Review 制造新订单。

### 为什么还不能 PASS

当前仓库的测试基线没有跟上 10 月 6 日的 ProductID 规则变化，而且这不是“缺一份报告”，而是**当前测试代码与当前生产代码确定性冲突**。

因此最新源码还没有一个可信的完整离线回归结果，RFQ-002 不能在这一检查点关闭。

---

## Blocking Finding

### B1 — HIGH — ProductID 旧测试与当前生产契约冲突，当前 full regression 不能成立

**Status:** OPEN / BLOCKING

生产代码在 `e585e88` 后明确改为：

- AI preview 不要求 ProductID；
- `AiRecognitionResult.product_id` 仅保留兼容字段，生产 reader 返回空字符串；
- parent grid 通过 `wait_for_model(...)` 等待并最终只校验型号、品牌、数量。

但当前测试仍保留旧 ProductID 契约。

独立检查到至少以下确定性冲突：

1. `tests/inso/test_v12_purchase_writer.py::test_ai_reader_returns_only_ready_single_row_result`
   仍断言 `result.product_id == "P216328"`，而当前 production reader 明确返回 `""`。

2. `tests/inso/test_v12_purchase_writer.py::test_ai_reader_requires_the_product_code_the_erp_resolved`
   仍断言 ProductID 为空时 reader 必须返回 `None`，与 Owner 2026-10-06 最新规则和当前实现直接相反。

3. `tests/launcher/test_v12_composition.py` 的 `_ParentFields` 仍只有 `wait_for_row(product_id,...)`，没有当前生产 coordinator 调用的 `wait_for_model(...)`；相关正常 prepare 测试仍断言 `wait_for_row("P216328")`。

4. 同一文件还保留“wrong product code must fail”“parent-id-mismatch”等已经被当前 Owner 规则取消的旧行为测试。

执行记录也明确承认：
- 本轮只跑了 152 项专项；
- 最新 full pytest 没有重跑；
- 早前 921 passed / 11 skipped 不覆盖 10 月 6 日生产修改。

所以当前不是“尚未证明 full regression 通过”，而是从已提交测试源码即可确认：**测试契约尚未收敛，直接跑完整套件会遇到与当前实现不一致的失败。**

### Required repair

只做最小收尾：

1. 把 ProductID 相关测试更新为 Owner 当前契约：
   - preview / parent 主链只校验型号、品牌、数量；
   - ProductID 可以作为兼容读取能力保留，但不能再作为成功条件；
   - parent wait 测试改为 `wait_for_model`；
   - 删除/改写 `parent-id-mismatch` / “wrong product code fails” 等过期断言。
2. 不要重新设计生产流程；如果测试对齐后没有暴露真实生产缺陷，不要修改 `src/`。
3. 跑最新完整 **safe/offline** regression，并记录真实 pass/skip 数字。
4. 重新跑 Ruff 与 `git diff --check`。
5. 更新 EXECUTION_LOG / FINAL_REPORT 的最新验证结果并回到 `REVIEW_REQUIRED`。

### Packaging rule

如果修复只涉及 tests / Control Room 文档，**不需要重新打包**，当前 EXE 仍对应同一生产源码 `a1bed40`。

只有完整离线回归发现真实生产源码问题、导致 `src/` 再次修改时，才需要重新打包并重新记录 EXE hash。

---

## Verified Areas

### AI 三要素规则

Production implementation matches the latest Owner rule: ProductID is not used as a preview or parent success prerequisite. Final validation still applies the existing MPN/brand/quantity validation function.

### Upper confirmation vs lower duplicate history

The two paths remain separate.

- Lower seven-day procurement history retains complete-set pagination semantics.
- Upper post-submit confirmation opts into first-page settlement only.
- Response/cache/DOM identity and ordering checks remain required.
- New first-row BillID and MPN checks remain required.
- Submission timestamp uses the Owner-authorized ±30 minute tolerance.
- Unknown result remains non-retriable for the irreversible submission.

### Purchase-success Sheets write-back

The production launcher wires a separate completion side effect after the V1.2 flow result. A sheet status write is attempted only when the returned outcome is `SAVED` and the durable V1.2 purchase state independently reads `SAVED`.

The Sheets helper:
- requires the original snapshot to have been `未发`;
- relocates by existing identity rules;
- accepts only current `未发` or already-`发给采购`;
- writes only the schema status cell;
- reads back the result;
- treats already-`发给采购` as idempotent success.

No purchase resubmission path is called from write-back retry.

### Exception notifications

`PURCHASE_EXCEPTION` reuses the existing V1.2 command/recipient ledger. New exception commands use only the Owner recipient and are keyed by inquiry + phase + reason. Unknown submission wording explicitly warns that the order may already have been sent and must not be directly replayed.

### OAuth / release / runtime

Write-scope OAuth with `allow_interactive=False` fails closed when no protected write grant exists, while an existing invalid/expired grant follows the normal refresh path.

The refreshed V1.2 artifact was built from `a1bed40`; `169aa58` is documentation-only. Submitted records show frozen self-check and release scan succeeded, V1.1 was not overwritten, runtime junction and local state were preserved, and protected CDP was not touched during packaging.

---

## Explicitly not treated as failure

The refreshed EXE's complete real business chain has not been replayed after packaging. That remains explicitly unverified and must not be manufactured by replaying the already-sent order.

The Review does not require another real submission, SMTP send, Sheets write, or old-order replay.

The blocking item is purely the stale offline regression contract and the missing current full safe regression.

## State transition

`REVIEW_REQUIRED → CHANGES_REQUESTED`
