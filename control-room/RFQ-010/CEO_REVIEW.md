# RFQ-010 CEO Independent Review

Date: 2026-10-10  
Status: CHANGES_REQUESTED  
Reviewed branch: `codex/v1-4-order-mail-inspection`  
Reviewed HEAD: `22bd9c760de118bd38332a9fb589657a96f38eff`  
Base: RFQ-009 REVIEWED_DONE `b85d9c1a957938553da885ec3ed8b0feab45b283`

## Verdict

**CHANGES_REQUESTED**

Phase 2 的页面字段定位、PI 提取、独立销售标签页、Owner-review 保留和不保存边界总体正确；两份授权样本的 live evidence 也与报告一致。

但独立 Review 发现两个必须修复的业务/会话 blocker。二者都不需要推翻 Phase 2 架构。

---

## B1 — reused V1.4 sales tab bypasses the canonical INSO re-authentication rule

### Finding

`src/launcher/sales_header.py::acquire_sales_tab()` 只有在第一次创建 V1.4 sales tab 时才执行：

`InsoSessionGuard(...).ensure_authenticated()`

当已经存在唯一 `v14-sales` owned tab 时，代码直接：

`return handle, candidates[0], True`

因此第二次及后续 Phase 2 执行会直接操作旧页面，而不会重新打开/验证 INSO session。

这与当前已审核 V1.3 的 canonical INSO session invariant 冲突：

> every INSO entry opens the page again and re-establishes the session

现有 `InsoSessionGuard` 明确说明旧 ERP 页面可能继续正常渲染，但后台 session 已失效；“页面还在”不能作为登录有效证据。

### Risk

Owner 检查完成并返回销售订单列表后，隔一段时间再次运行自动录单时：

- 页面 DOM 可能仍存在；
- V1.4 会认为它可直接使用；
- 但 INSO 后端 session 可能已经失效；
- 后续下拉、异步请求或保存阶段会基于 fossil page 工作。

Phase 2 当前还没有 Save，所以这次没有造成不可逆业务后果；但如果这个缺口带入后续明细/附件/保存阶段，会成为高风险基础缺陷。

### Required repair

保留独立 V1.4 tab，但每一次新的录单 invocation 在真正改字段前必须重新证明 INSO session。

同时不能为了认证覆盖 Owner 尚未复核的页面：

1. 如果 sales tab 仍处于 `WAITING_OWNER` 的 bill 页面，保持现状，返回等待 Owner，不导航；
2. Owner 已人工返回销售订单列表后，下一次 invocation 必须通过 canonical `InsoSessionGuard` 重新建立/证明 session；
3. re-auth 后再进入销售订单并点击新增；
4. ownership marker 必须继续保留；
5. challenge / OTP / captcha 仍 fail closed，并保留人工处理页；
6. 不允许只用当前 DOM / URL / cookie existence 当 session proof。

可以在 owned sales tab 上重新认证，也可以用独立临时认证页刷新共享 session；但最终必须满足 canonical guard 的真实导航 + authenticated-control proof。

增加回归覆盖：

- existing owned sales list + expired/fossil session -> guard runs before header mutation；
- WAITING_OWNER bill -> never reauth/navigate/overwrite；
- restored/authenticated result -> ownership survives and sales flow resumes；
- auth DEAD/manual verification -> zero header mutation。

---

## B2 — RMB behavior does not match the Owner's actual rule

### Owner rule

Owner 的原始要求是：

> 币种那里要确认是 RMB，不是的话要点击然后选择 RMB。

也就是：

- 先读取；
- 已经是 RMB：不操作；
- 不是 RMB：点击下拉选择 RMB；
- 最后读回确认 RMB。

### Current implementation

`src/inso/sales_header.py::fill_sales_header()` 当前无条件执行：

`page.select("currency", "RMB")`

即使页面已经是 RMB，也会再次点击并重新选择一次。

这来自之前 CEO 给 Codex 的指令表述过度，我在本次独立 Review 中纠正该要求。

### Risk

币种属于可能联动汇率/价格的业务字段。已经正确时再次选择没有业务收益，而且可能触发页面 change handler、汇率刷新或其他联动。

Owner 明确要求的是“不是 RMB 才切换”，所以必须按最小变更原则实现。

### Required repair

改为：

1. 读取 currency；
2. 若 == `RMB`：不点击币种控件；
3. 若 != `RMB`：精确下拉选择 `RMB` 一次；
4. 再读回确认；
5. 不主动修改汇率或其他联动字段。

测试至少覆盖：

- initial RMB -> zero currency selection calls；
- initial USD/non-RMB -> exactly one RMB selection；
- both paths final readback RMB；
- exchange/rate field remains untouched by our code。

---

## Other reviewed areas

除上述两个 blocker 外，本轮没有发现新的 Phase 2 blocker：

- PI No. 仅从 Excel 的 PI label 位置读取，缺失/多值/公式/结构不明 fail closed；
- 当前 Phase 2 仅限定两份已确认样本，没有假装泛化到未来所有邮件；
- 客户通过真实下拉结果按页面顺序筛选“包含阿尔克”的候选，并选择其中第一条；
- 付款方式、运费承担、国内交货、快递发货、广东惠州、客户订单号均有即时读回 + 最终总读回；
- 页面字段不一致即停止，不循环乱点；
- 没有明细、PDF、Save、提交审核接口；
- V1.4 worker 不改变 V1.2/V1.3 run state；
- V1.4 owned tab 有 browser-visible ownership marker，shared parking/login discovery 已排除/保护该 tab；
- worker 结束后 tab 保留供 Owner 复核；
- 当前未部署；
- 完整真实询价业务混跑仍为 UNKNOWN，报告没有过度声称。

### Concurrency note

V1.4 与询价并行的产品方向接受。

本次不要求为了 Review 人为执行真实采购/SMTP 混跑测试；但后续正式部署前，应继续保持：

- 两个模块拥有不同 tab；
- 任一模块不能 close/navigate 对方 owned tab；
- shared session recovery 仍使用 canonical authentication proof；
- Owner-review sales tab 在等待人工时永不被 parking/cleanup 关闭。

---

## Regression evidence received

Executor reports:

- focused: **248 passed**
- full safe/offline: **1715 passed / 1 skipped**
- Ruff: **PASS**
- no deployment

这些证据可以保留，但 B1/B2 修复后需要重新运行相关 focused + full safe/offline regression。

## Required next state

只修 B1/B2，不扩 Phase 3：

- 不填明细；
- 不上传 PDF；
- 不保存；
- 不提交审核；
- 不加 15 分钟轮询；
- 不部署。

修复后重新提交 `REVIEW_REQUIRED`，提供新的完整 HEAD SHA。

## Final state

`REVIEW_REQUIRED -> CHANGES_REQUESTED`
