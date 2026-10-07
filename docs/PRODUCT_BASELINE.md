# 产品基线

本文件只维护长期产品范围与跨模块业务规则；当前进度与任务状态写在 `control-room/COORDINATION.md` 和对应 RFQ Task Spec，实现细节写在 module docs。

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
- Owner 2026-10-02 明确：历史数据从业务询价页**下方采临时询价**查询取得，不能使用上方业务询价列表；核对 `CreateTime`、`PartNo`、`Qty` 和真实制单人 `UserName`，完整读取分页。Research 价格筛选不得丢弃零报价的重复历史。
- 重复订单仍先完成 Research，再发重复通知并停止采购。
- 非重复订单：A 必发重要通知；B 总额 > 50,000 且货少；C 总额 > 300,000 且货少。
- 采购类型与库存无关：A，或 B > 50,000，或 C > 300,000 → `需要问全价格`，否则 `普通询价`。
- 全价格采购员：颜浩坚；普通询价采购员：陈熙。
- AI 录单输入：`型号 + 6 个 ASCII 空格 + 品牌 + 6 个 ASCII 空格 + 数量`；型号与数量必须精确一致，品牌只需部分匹配（ERP 会把品牌归一成自己的规范码，如 `HRS(hirose)`→`HRS`）；任一校验失败不得保存。
- Owner 2026-10-02 最新授权：草稿及 AI/parent 校验通过后，允许客临时询价表单的「保存并发送」单次提交；等待五秒，再以**上方业务询价列表**同型号、本次时间的新记录确认结果。不明结果不得自动重发。首次真实提交只由 Owner 在下次真订单运行，Executor 不做提交测试、不自动重启上线；本次源码改动先交 Owner Review。此明确例外取代此前对保存并发送的绝对禁止；单独「保存」、其他 INSO 发送及 Sheets 写入仍不开放。
  - 命名澄清（2026-10-01 线上核证）：AI 录单面板页脚还有一个「保存数据」（`#win_btn__dialog11`），它是**纯客户端**的识别结果回填（`pasteImport` → `AiImport.doImport` → `ai_appendRow` 重载明细表），不写服务端，**不是**最终保存动作。两者不得混称。
- Owner 指定：保存成功后的 GUI 业务文案为 `已发采购单`。
- Owner 决定（数量数据异常）：待处理记录的数量单元格**不是数字**时（列名图例如 `Qty`、空白、文本占位），**跳过该行并记明确原因**，不发起 Research、不进入采购。该行在 GUI 显示为一类"已跳过"业务状态，并产生醒目的数据质量提醒；跳过不消耗重试预算，且表格修正为数字后该 inquiry 可自动恢复，无需人工清库。
- Owner 决定（崩溃恢复）：查价（Research）过程中进程被强杀后，重启必须把残留的"查价中"占用**自动释放回队列**并重新排队；Research 只读，故释放占用是安全恢复，不产生重复写入。

V1.2 Production Write Gate 当前 **CLOSED**。

## 长期边界

- Chrome 是唯一支持的生产浏览器；Edge 支持已废弃。
- Core Vault 是唯一凭据源。
- LCSC credential SiteId = `szlcsc.com`；认证 host = `passport.jlc.com`。
- CAPTCHA / OTP / 设备验证一律人工处理，不绕过。
- 不引入 Redis、Celery、Kafka、Docker 或大型 Workflow Engine，除非出现真实需求。

- Owner2026-10-07：正常 Research/采购订单行间隔由180秒缩短为120秒，GUI按同一期限倒计时（冷却02:00）。Owner随后补充：查询失败重试亦由180秒改120秒；报价正常行间0秒和15分钟循环不变。
