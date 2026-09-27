# 产品基线

本文件只维护长期产品范围与跨模块业务规则；当前进度写在 `CURRENT_TASK.md`，实现细节写在 module docs。

## V1.1

稳定流程：

```text
15 分钟 Scheduler
→ Sheets 读取待处理记录
→ Workflow 建立/恢复 inquiry
→ Research 调研
→ 写入 调研价格.xlsx
```

Research 价格源：IC.net、Findchips、HQEW、LCSC、Bom.Ai、INSO（INSO 仅作只读历史价格源）。

V1.1 Research Stability 已 CLOSED，稳定锚点：
`release/v1.1 = 44cd4a4cdb05fc069189801d24c4710bfd9445f3`。

## V1.2

V1.2 在 V1.1 上增量加入：

- INSO 近 7 天重复订单检查；
- 重要订单 / 重复订单通知；
- INSO 采购询价草稿录入；
- GUI 业务状态、事件历史和异常提醒。

关键业务规则：

- 重复检查使用 rolling 168h（Asia/Shanghai），同型号按 `dup-mpn-v1` 精确比较；数量只比较，不参与型号匹配。
- 重复订单仍先完成 Research，再发重复通知并停止采购。
- 非重复订单：A 必发重要通知；B 总额 > 50,000 且货少；C 总额 > 300,000 且货少。
- 采购类型与库存无关：A，或 B > 50,000，或 C > 300,000 → `需要问全价格`，否则 `普通询价`。
- 全价格采购员：颜浩坚；普通询价采购员：陈熙。
- AI 录单输入：`型号 + 6 个 ASCII 空格 + 品牌 + 6 个 ASCII 空格 + 数量`；型号/品牌/数量校验失败不得保存。
- 最终业务动作只允许 `保存数据`；`保存并发送`、发送动作始终禁止。
- Owner 指定：保存成功后的 GUI 业务文案为 `已发采购单`。

V1.2 Production Write Gate 当前 **CLOSED**。

## 长期边界

- Chrome 为生产浏览器基线；Edge 仅备用。
- Core Vault 是唯一凭据源。
- LCSC credential SiteId = `szlcsc.com`；认证 host = `passport.jlc.com`。
- CAPTCHA / OTP / 设备验证一律人工处理，不绕过。
- 不引入 Redis、Celery、Kafka、Docker 或大型 Workflow Engine，除非出现真实需求。
