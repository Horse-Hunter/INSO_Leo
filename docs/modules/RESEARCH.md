# Research 模块

## Public Contract

入口：`ResearchService.execute(ResearchInput) -> ResearchResult`。

- Input：`inquiry_id`、`mpn`、可选 `brand`、`quantity`、`importance_raw`。
- Status：`SUCCESS | PARTIAL_SUCCESS | EXCEPTION | RETRYABLE_FAILURE`。
- Research 不决定采购类型、通知资格或 V1.2 路由。

## 来源

IC.net 只用于 Brand 与货量，不是价格源。价格源为 Findchips、HQEW、LCSC、Bom.Ai、INSO。

- IC.net：严格 MPN；库存只统计严格匹配且带 SSCP/ICCP 标识的行。无合格库存或总量 `<= 3 × quantity` → `货少`；否则 `货多`。技术失败 → `待验证`，不得当作零。
- Findchips：读取可见价格档位；分别保留有库存/无库存最低价。
- HQEW：只读目标型号历史市场报价，最近 1 个自然月最低价。
- LCSC：取已展示最低 unit price，分别保留有库存/无库存最低价。
- Bom.Ai：只读目标型号报价区域，最近 1 个自然月最低价。
- INSO：只读历史询价“供方未税价”；先 1 个自然月，无有效价再扩大到 2、3 个自然月。

Findchips/HQEW/LCSC/Bom.Ai 的型号比较按现有 canonical normalization；禁止模糊猜测变体。INSO Research 复用 launcher 提供的 authenticated `InsoOperationAccess`，不得自行枚举/接管任意浏览器页面。

## FX 与聚合

USD/RMB、HKD/RMB 使用同日 ECB reference；缺失、重复、日期不一致、非正数或非有限值均 fail closed。

正常价格池：
- Findchips 有库存最低价
- HQEW 最低价
- LCSC 有库存最低价
- Bom.Ai 最低价
- INSO 最低价

统一 RMB 后取最低价作为市场最低参考价，乘 quantity 得预估订单总价。仅无库存价格可在所有正常来源均无有效价时作为兜底，并返回 `PARTIAL_SUCCESS`。

Status：
- 有正常价格且无技术失败 → `SUCCESS`
- 有正常价格但存在技术失败 → `PARTIAL_SUCCESS`
- 无正常价格且存在技术失败 → `RETRYABLE_FAILURE`
- 所有价格源正常完成且无任何有效价格 → `EXCEPTION / NO_MATCHING_PRODUCT`

## Excel

正式输出：`调研价格.xlsx`。

可见列：
`型号 | 品牌 | 数量 | 重要等级 | 货量标识 | 预估订单总价 | 市场最低参考价 | INSO | Findchips | 华强 | 立创 | 正能量 | 备注 | 处理时间`

隐藏 `_inquiry_id` 用于幂等，隐藏 `_research_status` 保存结果状态。Excel load/schema/save 失败 → `RETRYABLE_FAILURE`。技术失败详情只进备注，不伪装成业务“无结果”。

## 边界

Research 只做调研与本地 Excel 持久化；不读写 Google Sheets，不执行主动采购，不决定 V1.2 通知/采购业务规则。Credential 只走 Core Provider。普通 browser/session readiness 复用共享 runtime；CAPTCHA/OTP/设备验证才需要人工。
