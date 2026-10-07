# RFQ-002 CEO Independent Review — 2026-10-07

**Status:** COMPLETE  
**Verdict:** CHANGES_REQUESTED  
**Reviewed HEAD:** `732a4593631457c07660ed950bc11c1c322aedc4`  
**Previous PASS:** superseded; it covered the earlier ProductID checkpoint only.

## Owner Summary

### Review 结论

CHANGES_REQUESTED

CEO 已独立检查自上次 PASS 之后的当前生产改动，重点覆盖：

- 六行批量闭环修复 `c7b77e5`
- 单空白页 CDP 收尾 `7738018`
- 无报价终态 / GUI / 异常邮件修复 `732a459`
- 当前 TASK_SPEC、CEO_REPORT、EXECUTION_LOG、FINAL_REPORT 与相关源码/测试

### 最新无报价修复

**通过代码 Review。**

当前实现与 Owner 最新规则一致：

- 五个价格来源正常但均无报价时仍保持 Research `EXCEPTION / NO_MATCHING_PRODUCT`；
- 新发生的终止 Research 写入 `RESEARCH_FAILED`，不再继续显示为处理中；
- Workflow `FAILED` + 历史 V1.2 `ROUTING` 可只读映射为“调研无报价（未发采购）”，无需改生产数据库；
- 无报价不会进入采购 writer；
- 后续异常邮件明确写“五个价格来源均无报价、未进入采购提交”，只建议核对型号，不宣称型号必错；
- 已存在的异常通知 command 仍按原 ledger 幂等，不会因文案更新重发旧邮件。

提交记录的 focused 440/1、full safe 974/11、Ruff 与 diff check 与当前源码范围一致；本 Review 没有重跑订单，也没有执行真实 INSO / SMTP / Sheets 写入。

### 当前唯一阻塞项

最新 RFQ 还包含上次 PASS 之后新增的“单空白页 CDP”规则，因此本次 Review 必须一起覆盖。这里发现一处与 Owner 明确规则不一致的安全边界。

---

## Blocking Finding

### B1 — HIGH — INSO 人工验证页会在进入 MANUAL_REVIEW 前被关闭

TASK_SPEC 当前明确要求：

> unresolved manual verification is not a closed row: stop and preserve its human-needed page.

但当前生产路径中：

1. 每笔询价以 `fresh_page=True` 新开 INSO 页；
2. `InsoSessionGuard.ensure_authenticated()` 如果发现 CAPTCHA / 手机验证码 / 设备验证，会返回 `DEAD / MANUAL_VERIFICATION_REQUIRED`；
3. 外层 `ensure_inso_authenticated()` 对任何 `DEAD` 都会立即执行：
   `guard.opened_page.close()`；
4. 此时 Backend 尚未进入 `RunState.MANUAL_REVIEW`。

因此，如果人工验证发生在 INSO 新开的 owned tab 上，当前代码会先把人需要处理的验证页关闭，再向上抛错。后面的 `park_shared_cdp` 虽然有 “MANUAL_REVIEW 时不清空” 的保护，但已经来不及。

这与 Execution Log 中“Manual-verification stop ... human-needed page is preserved”的声明不完全一致。现有测试验证了错误码和普通 failed fresh lease cleanup，但没有覆盖“fresh owned page + MANUAL_VERIFICATION_REQUIRED 必须保留页面”。

### Required repair

只做最小修复：

1. `ensure_inso_authenticated()` 在 `MANUAL_VERIFICATION_REQUIRED` 时不得关闭本次新开的 human-needed page；
2. 其他普通认证失败 / 无效 lease 仍按现有规则清理 owned tab；
3. 增加一个离线 regression，明确证明：
   - fresh owned INSO page 遇人工验证后仍保持打开；
   - 浏览器/context/profile 不关闭；
   - run 进入 MANUAL_REVIEW 后不会被 `park_shared_cdp` 清掉；
4. 运行当前 full safe/offline regression、Ruff、diff check。

不要为了这个修复运行真实订单或制造验证码场景。

### Packaging

这是生产源码路径（`src/launcher/inso_session.py` / 可能的 launcher lifecycle）问题。

如果修复修改了会进入 EXE 的 `src/`，需要重新打包 V1.2，并重新记录 EXE hash；不需要重跑真实业务订单，只做 build/self-check/release scan/idle launch 即可。

---

## Independently Verified Current Areas

### Six-row closed-loop changes

从当前代码确认：

- bounded inquiry scope 不会 claim 其他待处理订单；
- 每行 result callback 在下一行前执行状态写回、通知处理和 owned-tab cleanup；
- UNKNOWN / MANUAL_REVIEW / write-back failure 不会重新触发采购提交；
- lower-history fuzzy search 仍完整分页后才按 exact MPN 过滤业务记录；
- final saved record ref 仍转换为 opaque `rec_` 引用；
- Owner-confirmed old-sent recovery 是显式 opt-in，并要求原 dispatch 事件和 typed authoritative evidence。

### Blank-only CDP normal path

正常闭环时 `park_shared_cdp` 会先保留/创建一个 about:blank，再关闭其他页，并且不关闭 Chrome/context。这个正常路径符合 Owner 要求。

问题只在“人工验证发生在 fresh INSO owned page”这一异常路径。

### No-quote terminal path

无报价当前会终止 Research、显示正确 GUI 文案、发送 Owner-only 解释邮件，且不会进入采购 dispatch。

## Safety

本 Review 未：
- 重跑任何历史订单；
- 执行 Save / Save-and-Send；
- 发送真实 SMTP；
- 写 Google Sheets；
- 操作 protected CDP。

## State transition

`REVIEW_REQUIRED → CHANGES_REQUESTED`
