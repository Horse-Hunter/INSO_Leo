# RFQ-006 CEO Independent Review — 2026-10-07

**Status:** COMPLETE  
**Verdict:** CHANGES_REQUESTED  
**Reviewed Executor HEAD:** `53746e9268d7be395504df9fe08aa044e3c55475`

## Summary

RFQ-006 的总体集成方向正确，独立代码 Review 已确认以下主体边界基本成立：

- 从 RFQ-004/005 REVIEWED_DONE 基线 `75b6043...` 新建独立 integration 分支；
- canonical ProductionBackend 内串行执行 V1.2 → V1.3，同一 cycle 结束后再进入 900 秒可中断等待；
- V1.2 的 180 秒仍由既有 coordinator 控制，只发生在相邻 V1.2 已闭环订单之间；
- V1.3 正常相邻订单无 180 秒 cooldown；
- V1.2_PAUSE 后 V1.3 可继续，GLOBAL_STOP 会阻止 V1.3；
- RFQ-004/005 查询和更新链路被复用，没有另造浏览器/profile/SMTP；
- V1.3 final ROW_FAILED 有 durable hold、GUI 红态和 229 通知；
- NO_RECENT_QUOTE 不 hold，可在下一轮重新查询；
- V1.3 crash-before-final 不建立永久 interruption quarantine；
- owner completion `采购已报价` 可关闭能够安全定位的 hold；
- notification ledger / SMTP 复用现有 SQLite 基础设施；
- GUI 保留已有 V1.2 黄色/红色状态并增加 V1.3 waiting/completed/failed；
- fixed Chrome/CDP/profile 继续共享；
- V1.3 EXE 与 V1.2 并存，没有覆盖 V1.2；
- read-only discovery 正确确认 `报价输入` gid=`489913321`，并在无法确认 geometry 时选择不猜。

但是当前有两个会破坏 Owner 已确认故障/人工处理语义的 blocking finding，因此 RFQ-006 不能标 REVIEWED_DONE。

## Blocking Finding B1 — HIGH

### Durable ROW_FAILED hold 在“无法重新定位”后会漏掉自动阻断，仍可能重新处理同一条 `发给采购`

`V13IntegratedCycle.run()` 处理已有 hold 时：

1. 先把 bound hold 的 `inquiry_id` 放入 `blocked_ids`；
2. 尝试用 hold 时保存的 observed identity 重新定位 source；
3. 如果 `relocate_quotation_status()` 抛 `SheetRecordConflict`，当前实现只是 log + observe + `continue`；
4. 此时不会加入 `blocked_locations`。

这对 **unbound hold**（例如 `SOURCE_MPN_UNAVAILABLE / SOURCE_IDENTITY_UNRESOLVED`，`inquiry_id=None`）尤其危险：

- 第一次 ROW_FAILED 后 hold 已经建立；
- Owner 或其他人工流程只修改了型号/数量/品牌等关键字段，但 source status 仍然是 `发给采购`；
- 旧 snapshot 无法 relocate；
- 当前代码没有任何 blocked id/location；
- 后面的 `query_quotation_candidates()` 会再次把该行作为候选；
- 程序可能在 Owner 尚未将状态改成 `采购已报价` 前自动重新进入 RFQ-004/RFQ-005。

这违反 Owner 已确认的规则：

> V1.3 一旦明确 ROW_FAILED 进入人工 hold，只要源状态仍为 `发给采购`，后续 cycle 必须自动 skip；只有 Owner 人工完成并改为 `采购已报价` 才解除。

同样的问题也可能发生在 bound hold：如果关键字段变化导致后续 candidate 不再绑定原 inquiry_id，`blocked_ids` 也无法阻止它以 unbound candidate 重新进入。

### Required repair

- Active hold 是一个 fail-closed automation barrier；不能因为 hold identity 无法安全 relocate，就自动放行当前 source queue。
- 不要把 row number 当成新的业务 identity，但可以把 hold 保存的 source row position 作为**仅用于禁止自动动作的保守 safety anchor**：
  - 若严格 relocate 成功：按现有 identity/location 阻断；
  - 若严格 relocate 失败，但原 observed row_position 当前仍存在且状态还是 `发给采购`：必须继续 block 该位置，不做 INSO query / Google update；
  - 若该位置已经明确 `采购已报价` 且能满足安全的人工作结条件，再按规则关闭 hold；
  - 若无法证明是哪一行，宁可保留 hold/人工告警，也不要自动重试一个可能就是 held row 的候选。
- 不生成新 inquiry_id，不做 fuzzy identity matching。

### Required regression

至少新增：

1. unbound ROW_FAILED hold → 下一 cycle 同一 row 的 MPN 被人工修改但 status 仍 `发给采购` → **0 quote query / 0 update / 0 duplicate mail**，hold 仍 active。
2. bound ROW_FAILED hold → 关键 snapshot 字段改变导致无法 bind 原 inquiry → 仍不能以 unbound candidate 自动重跑。
3. held row 原位置仍 `发给采购` 且 relocate 失败 → conservative skip。
4. held row 被删除 → hold 保留，其他明确无关 row 继续。
5. Owner 将 held row 改为 `采购已报价` 的正常解除路径继续 PASS。

## Blocking Finding B2 — HIGH

### RFQ-006 把 RFQ-004/005 的未知异常过度降级成 ROW_FAILED，破坏 shared-vs-row fault boundary

RFQ-004 REVIEWED_DONE 时，`V13QuotationCycle.run()` 对未知异常是 fail closed / propagate；RFQ-006 改成：

`except Exception -> ROW_FAILED / SOURCE_CHANGED`。

另外 `V13IntegratedCycle.settle()` 对 updater 的未知异常也做：

`except Exception -> ROW_FAILED / UPDATE_RESULT_UNCONFIRMED`。

这相当于把任何没有被提前包装成 `V12Fault` 的异常都默认为“当前行问题”。

但 Owner 的规则不是“V1.3 所有未知异常都行级化”，而是：

- **明确局限于当前 row 的业务/adapter问题** → ROW_FAILED；
- **Sheets / ledger / INSO / CDP / Google auth/schema 等共享设施问题** → GLOBAL_STOP；
- 无法证明是 row-local 的未知异常不能被静默伪装成 `SOURCE_CHANGED` 或 `UPDATE_RESULT_UNCONFIRMED` 后继续业务。

当前 broad downgrade 会让未来某个未被 typed wrapper 捕获的共享浏览器/session/API故障，或者代码/contract corruption，被持久化成某一行红 hold 后继续处理其他订单。

### Required repair

- 恢复 RFQ-004 已 Review 的 typed fault boundary；不要 broad `except Exception` 自动变 row failure。
- 只有明确的 `V13SourceRowError`、`QuotationInputAttemptFailed`、`UpdateAttemptUnconfirmed` 等已证明 row-local 的类型/结果才能转成 ROW_FAILED。
- 已知 shared types 继续 `V12Fault(GLOBAL_STOP, ...)`。
- 其余真正 unknown：默认 fail closed，向上抛给 integration/runtime shared classifier；不要伪造 `SOURCE_CHANGED`。
- RFQ-005 updater 本身已经把正常的可重试 UI/input 问题转换成 typed row result，integration 不需要再用一个大网兜吞掉所有异常。

### Required regression

至少新增：

1. quotation reader/operation 注入未知 `RuntimeError`，且不是已知 row-local typed failure → 不能得到 ROW_FAILED；必须停止/向上 fail closed。
2. updater_factory/update_one 注入未知 `RuntimeError` → 不能建立人工 hold 后继续下一行。
3. 已知 `V13SourceRowError` 仍 ROW_FAILED。
4. 已知 `UpdateAttemptUnconfirmed` / input readback exhaustion 仍由 RFQ-005 正常形成 ROW_FAILED。
5. `V12Fault(GLOBAL_STOP)`、DB、Sheets、CDP、auth 回归继续 PASS。

## Required follow-up — website alert coverage

RFQ-006 TASK_SPEC 还要求“任何网站问题发送 229 提醒；其他 Research 网站失败不停止模块”。请补一个直接 regression，证明 FINDCHIPS / HQEW / LCSC / BOM_AI 的 `SOURCE_UNAVAILABLE` 在不暂停 V1.2/V1.3 的同时会产生一次 229 通知且同一 episode 不重复。当前 `_observe_source_failure()` 只对 IC.net 以及带 login/auth token 的其他站点显式通知，普通 `SOURCE_UNAVAILABLE` 路径没有看到这项保证。

如果现有更下游机制已经覆盖，请用测试证明并在执行日志指出具体路径；否则做最小补齐。

## Live configuration / release status

Executor 对 live discovery 的处理是正确的：

- 已确认 `报价输入` gid=`489913321`；
- `header_row / input_row / first_column` 仍 UNKNOWN；
- Google update button/dialog/session、Script latency、INSO live reader acceptance 仍 UNKNOWN；
- 没有猜 geometry，也没有执行真实报价写入/更新。

因此当前部署的 `INSO_V1.3.exe` **不是可启动真实业务的 production-ready release**。现阶段必须继续保持 `BLOCKED LIVE CONFIG`。

这本身不是要求 Executor 猜值；代码 blocker 修好后，仍需要 Owner 提供/确认 `报价输入` 实际布局，之后再做单独授权的受控 live acceptance。

在 geometry 未确认前，不得把 RFQ-006 标成“生产业务验收完成”。

## Evidence reviewed

Executor 报告：

- RFQ-006 focused：52 passed
- combined：46 passed
- V1.3 focused：182 passed
- full safe/offline：1287 passed / 1 skipped
- Ruff：PASS
- `git diff --check`：PASS
- build / frozen self-check / staged scan / deployed self-check / idle GUI：PASS
- V1.3 EXE SHA256：`FB8AA11FC2B300BA1B56D08FD2AC9B6122405E67C31A0361DF21CC09B700EC16`
- V1.2 baseline EXE reported unchanged。

这些证据支持 build/offline integration，但不能覆盖上面的 fault/hold blockers，也不构成 live-business acceptance。

## State transition

`REVIEW_REQUIRED → CHANGES_REQUESTED`

## Owner screenshot addendum — 2026-10-07 15:15 +08:00

Owner supplied a current screenshot of the real Google worksheet and thereby resolved the quotation-input geometry that was previously marked UNKNOWN.

Confirmed from Owner-provided production screenshot/business instruction:

- active worksheet title: `报价输入`;
- URL gid: `489913321`;
- this worksheet is intentionally blank input surface — there is **no header row**;
- quotation payload is written into the **first row**;
- 14 values occupy **A1:N1** in the canonical RFQ-004 order:
  `日期、型号、品牌、数量、币种、供方返点、报价、供方未税价、平台数量、批号、货期、备注、备注2、制单人`;
- therefore `input_row=1`, `first_column=1 (A)`;
- the visible `更新报价` control is outside the A:N input area; screenshot proves visible text only, not its DOM role/selector.

This corrects the earlier RFQ-005/RFQ-006 assumption that `报价输入` contains a 14-column header row. It does not.

Required implementation correction:

- keep metadata binding `title=报价输入` ↔ configured `gid=489913321`;
- remove the requirement to read/validate a Google header row for this worksheet;
- do not invent a fake `header_row=0/1` merely to satisfy the old model;
- preserve the 14-field order contract in code and exact RAW write/readback for `A1:N1`;
- production config may now carry the confirmed `gid`, `input_row=1`, `first_column=1`; `header_row` must no longer be required for V1.3 quotation input;
- read-only browser inspection may verify the real `更新报价` locator/session without clicking it; popup/Apps Script post-click behavior remains live-only until separately Owner-authorized.

Because geometry is now Owner-confirmed, `BLOCKED LIVE CONFIG` due solely to geometry may be removed after this code/config correction. Production business execution is still not authorized by this addendum.
