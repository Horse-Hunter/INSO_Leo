# V1.2 Architecture Baseline

Status: **ACTIVE / PRE_SAVE_READY / REAL_SAVE_GATED**

本文件只保留当前冻结架构与业务契约，不记录 discovery 历史。当前进度见 `CURRENT_TASK.md`。

## 1. 模块职责

- `workflow`：业务编排、持久状态、事件/提醒、retry。
- `sheets`：2026 worksheet 记录映射与安全读写。
- `research`：沿用 V1.1 只读调研规则，不重算库存/价格业务。
- `inso`：7 天重复检查、采购草稿、保存前校验。
- `launcher`：Chrome/CDP/session lease 与 runtime 组装。
- `gui`：只消费 DTO，不计算业务阈值。
- Notification transport 只负责投递，不决定是否通知。

## 2. 业务流程

```text
Sheets
→ Duplicate Check
→ Research
→ post-Research branch

重复：
  无条件重复通知
  → GUI 红色“重复订单”
  → STOP before purchase

非重复：
  重要订单通知判断（异步，不阻塞采购）
  → Purchase Draft
  → AI 校验
  → 保存数据（仅在 Write Gate 打开后）
  → GUI “已发采购单”
```

Duplicate lookup 技术失败不阻止 Research，但在 duplicate 未确认前不得进入采购。

## 3. 重复检查

- 数据源：INSO 历史，rolling 168h，Asia/Shanghai，下界 inclusive。
- 型号：`dup-mpn-v1` = NFKC + outer trim + ASCII uppercase；内部标点/分隔符/空格保持原样；禁止 fuzzy。
- 取最新一条同型号记录；数量仅做 equality 展示/判断。
- latest timestamp 并列时，仅可用已证明稳定的 INSO record id；否则 `AMBIGUOUS`。
- creator 只接受明确的制单人/创建人/创建用户语义；采购员/业务员不能替代。

## 4. 通知

收件人：
- `linan229@qq.com`
- `shawn@inso-hk.com`

发件人：`1069599116@qq.com`；SMTP credential 仅从 Core Vault `smtp.qq.com` 获取。

重要订单：
- A：始终通知；
- B：总额 > 50,000 且货少；
- C：总额 > 300,000 且货少。

重复订单：只要 `repeated=true` 就通知，与等级/金额/库存无关。

投递：
- per-recipient durable ledger；
- initial + 1m + 5m + 15m；
- 仅 transient failure 重试；
- auth/config/permanent recipient failure 不无意义重试；
- 通知失败不阻塞采购；
- 所有 intended recipients 均 SENT 后才恢复通知失败 alert。

## 5. 采购草稿

Quotation type：
- A；
- B 且总额 > 50,000；
- C 且总额 > 300,000；
以上 → `需要问全价格`，否则 `普通询价`。库存不参与此规则。

采购员：
- 全价格 → 颜浩坚
- 普通询价 → 陈熙

固定客户：`Win Source Elec. Tech. Ltd`。

AI 输入：
`MPN + 6 个 ASCII 空格 + Brand + 6 个 ASCII 空格 + Qty`

保存前必须验证：
- MPN：`ai-mpn-v1` canonical exact；
- Brand：trim-only exact；
- Qty：整数 exact；
- parent form read-back 与预览一致。

任一 mismatch / UNKNOWN → 红色 `采购录单异常`，停止，不保存。

## 6. 状态与持久化

分开保存：
- current business state；
- append-only event history；
- active alerts。

SQLite 只做 additive migration；V1.1 表不 drop/rewrite。首次迁移前做 timestamped、校验通过的 SQLite backup。禁止自动 downgrade/drop。

Evidence 仅放 Git-ignored `runtime/evidence/<inquiry_id>/`。默认 30 天保留策略；初版不自动删除。

## 7. Browser / Session

- Production browser：**Chrome only**。
- 重复检查、Research、采购尽量复用同一明确 session lease。
- 仅关闭 app-owned page/browser；reused Owner Chrome 永不关闭。
- 页面、context、order/control identity 不唯一即 fail closed。
- CAPTCHA / OTP / device verification → manual。

## 8. Write boundary

当前 Production Write Gate：**CLOSED**。

未开 Gate 前允许：read-only query、synthetic preview、未保存临时草稿、测试。

真实写入必须满足：
- allowlisted page/control；
- 唯一 inquiry identity；
- 唯一可见语义控件；
- pre-write value 校验；
- post-write read-back；
- unknown outcome 不自动重试。

唯一可能授权的最终动作：`保存数据`。

始终禁止：
- `保存并发送`
- `发送`
- 修改历史记录
- 未列入 allowlist 的写入

CEO/Safety 在首次真实 Save 前做独立 Gate Review。
