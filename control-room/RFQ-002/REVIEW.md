# RFQ-002 CEO Independent Review

**Status:** COMPLETE  
**Verdict:** CHANGES_REQUESTED  
**Reviewed HEAD:** `0cb0a90c47fe65320f500b7e68f4c03d443afd60`

## Owner Summary

### Review 结论

CHANGES_REQUESTED

### 发生了什么

CEO 已按 `CEO_REPORT.md` 的索引独立核对当前源码、提交记录、执行记录和发布证据。

最终「保存并发送」没有被重跑或测试；这是 Owner 明确要求保留给下一笔真实新订单的首次验证，**本 Review 不把“尚未实测最终提交”作为失败项**。

当前实现的关键保护链本身已经接上：最终动作只通过 Owner 明确授权的「保存并发送」按钮；单独保存和 generic Send 仍关闭；点击前先落 UNKNOWN；结果不确定不会自动重发；下方七天重复历史仍完整分页，上方提交确认只读已结算首页首行；V1.2 独立 EXE 的构建、自检、安全扫描和启动证据也与报告一致。

但仓库里仍有两条旧自动测试明确断言“`save_and_send` 方法不存在”，而当前生产代码按最新 Owner 授权已经明确存在该方法。也就是说，当前代码和当前测试互相矛盾，执行记录里那次 926 passed / 11 skipped 又发生在最终提交改动之前，因此现在不能真实声称回归仍然通过。

### 影响什么

这不是要求重新跑旧订单，也不是要求执行真实「保存并发送」。

问题只在仓库内部的验证基线没有跟上最新授权：如果现在直接跑安全离线回归，这两条旧断言本身就会与当前代码冲突。RFQ-002 因此暂时不能关闭为 REVIEWED_DONE。

### 接下来做什么

Executor 只需做最小收尾：

- 修正这两条已经过期的测试断言，使其反映最新边界：`save_and_send` 可以存在，但默认生产 gate 不能授权它，单独 Save 和 generic Send 仍保持关闭；
- 运行不触碰真实订单/真实浏览器提交的离线回归与静态检查；
- 更新执行记录为真实结果后重新提交 Review。

**不要重跑任何旧订单，不要执行真实保存并发送，不要为了补证据触碰生产提交。**

---

## Independent Review Record

CEO independently reviewed:

- `control-room/RFQ-002/CEO_REPORT.md`
- `control-room/RFQ-002/TASK_SPEC.md`
- `control-room/RFQ-002/EXECUTION_LOG.md`
- `control-room/RFQ-002/FINAL_REPORT.md`
- `control-room/RFQ-002/FINAL_SUBMISSION_REVIEW.md`
- merge HEAD `0cb0a90c47fe65320f500b7e68f4c03d443afd60`
- implementation checkpoint `5b219338ccb4899b0fc520f92652ee538dd58b95`
- indexed source paths for write authorization, purchase dispatch, reconciliation, duplicate history, workflow state, session ownership, GUI and Windows packaging
- current repository tests relevant to the changed final-submission boundary

The Review intentionally did **not** run an old order, open a production submission flow, click Save-and-Send, or create a real external write.

## Verified implementation properties

### 1. Narrow Save-and-Send authorization

Verified.

- Default `ProductionWriteGate` still rejects both ordinary Save and Save-and-Send authorization.
- `OwnerAuthorizedSaveAndSendGate` changes only the narrow Save-and-Send authorization.
- Production binds the final action to the exact `button#btnSave2` / 「保存并发送」 semantics.
- Generic send control `#bcSend` is not bound as the authorized final action.
- Standalone `SAVE_DATA` still requires the closed general write gate.

### 2. Durable-before-dispatch and no automatic resend

Verified from code.

- The purchase state must already be `AI_RECOGNIZED`.
- `begin_save_dispatch(..., save_and_send=True)` persists `UNKNOWN_WRITE_OUTCOME` and `SAVE_DISPATCH_ARMED` before the irreversible click.
- Once that state exists, the normal routing path does not reopen the purchase attempt.
- Submission exceptions do not retry the irreversible action.
- Restart reconciliation refuses to use the old legacy lookup for a Save-and-Send marker whose in-memory first-row baseline is unavailable.

### 3. Lower duplicate history vs upper submission confirmation

Verified from code.

- Seven-day duplicate history uses the lower `Stock_VenQuote` source and native pagination until the complete record count is collected.
- The final submission baseline/reconciliation opts into first-page settlement only.
- First-page confirmation requires a new first-row stable ID, exact model match and submission-time window.
- The default complete-set reconciliation contract remains separate.

### 4. Browser/session ownership

Verified from code.

- Reused Owner Chrome is not closed by normal lease release.
- Only an app-created operation tab may be closed by `close_owned_operation_tab`.
- Protected persistent CDP handles detach instead of owning/terminating the session browser.

### 5. Packaging evidence

Consistent with the submitted records.

- Existing release pipeline/spec is reused and version-parameterized.
- V1.1 remains the default and is not overwritten.
- V1.2 has a distinct artifact name/path.
- Submitted evidence records build success, frozen self-check exit 0, release scan PASS and stopped GUI startup.
- Per Owner instruction, packaged startup did not execute an order or final submission.

## Blocking Finding

### B1 — Current regression tests contradict the authorized production API

**Status:** OPEN / BLOCKING

Current production code intentionally exposes `InsoPurchaseWriter.save_and_send(...)` behind the narrow Owner-authorized gate.

However, `tests/inso/test_v12_purchase_writer.py` still contains old Phase-A assertions:

- `test_production_gate_is_closed_and_send_methods_do_not_exist` asserts that `save_and_send` is absent from `dir(writer)`;
- `test_non_ai_recognized_store_state_never_dispatches_save` asserts `not hasattr(writer, "save_and_send")`.

Those assertions cannot both be true with the current authorized implementation. They are not skipped and therefore make the repository's claimed regression contract stale.

The execution log correctly states that the earlier `926 passed / 11 skipped` run predates the final submission/packaging change. The current checkpoint therefore has no valid post-change regression result, and `CEO_REPORT.md` / `FINAL_SUBMISSION_REVIEW.md` must not imply these tests were fully aligned when the checked-in file still contains the old assertions.

### Required repair

Keep this repair narrow:

1. Update/remove only the stale “method must not exist” assertions. Preserve tests that the default gate is closed, standalone Save remains closed, generic Send is unavailable, and no unauthorized dispatch occurs.
2. Do **not** add or execute a real Save-and-Send test, do not replay an old order, and do not touch production submission.
3. Run the safe/offline regression and static checks that do not create external side effects; record the actual result.
4. Update RFQ-002 execution/final records if needed so they describe the checked-in test state accurately.
5. Return RFQ-002 to `REVIEW_REQUIRED` for CEO re-review.

## Explicitly deferred by Owner — not a Review failure

The following remains intentionally unverified and must stay that way until the next genuine new order:

- the real Save-and-Send click;
- the real five-second post-submit wait against a genuine order;
- the real upper-list new-record confirmation after that submission;
- actual downstream delivery semantics beyond the visible INSO record.

First validation belongs to Owner's next real order. An uncertain result must remain non-retriable/manual-review; do not manufacture a test order to close this item.

## State transition

`REVIEW_REQUIRED → CHANGES_REQUESTED`
