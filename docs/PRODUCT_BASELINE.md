# 产品基线

本文件只维护产品范围和长期跨模块业务规则。模块规则归 `docs/modules/`，安全归 `BOUNDARIES.md`，依赖归 `MODULE_INDEX.md`；实现状态以 Git `main`、当前 Task 和 Module Final Report 为准。

## 产品目标

- 项目：`INSO_Leo`。
- 已确认 V1 结果：可重复执行“询价 → 市场调研”流程。
- 更广泛的业务目标、主要用户和可衡量结果：`UNKNOWN`。

## 当前 V1 用户流程

```text
Workflow Scheduler（每 15 分钟）
-> Sheets 读取 Google Sheet 中状态为“未发”的记录
-> Workflow 创建或识别 inquiry
-> Research 执行市场调研
-> Research 将结果持久化到本地 `调研价格.xlsx`
```

## V1 包含

- Google Sheet 待处理记录读取，以及已确认的安全 Brand 写回路径。
- Workflow identity/state、duplicate prevention、retry 和 Sheets → Research 编排。
- 五个已确认来源的 Research，以及 Research 自有 Excel 输出。
- 只有必要的 inquiry-idempotent Excel 落盘成功后，`SUCCESS` 或合格的 `PARTIAL_SUCCESS` 才转为 Workflow `COMPLETED`。
- `MANUAL_REVIEW_REQUIRED` 停止自动推进并等待人工；`RETRYABLE_FAILURE` 不生成伪正常价格，由 Workflow retry。
- Sheet C 列 `importance_raw` 由 Workflow 原样透传，只影响 Research Excel 展示，不改变调研行为，也不定义未来 INSO 重要性。
- Research 可返回 `resolved_brand`；Sheets 安全写回发生 Brand conflict 时，不撤销已完成的 Research。

Sheets、Research、Workflow 的详细 Contract 归各自 module doc。

## V1 不包含

- INSO 业务、Quotation、最终客户报价、最终报价写回 Google Sheet。
- 共享 Excel/storage 模块。
- Redis、Celery、Kafka、Docker 或大型 Workflow Engine。

`inso` 和 `quotation` 保留为 Future Version 模块。

## Future Scope / 产品级 UNKNOWN

- INSO 系统定义、访问、询价行为和结果。
- Quotation 公式、舍入、利润、审批、有效期、输出和接收方。
- 产品/服务覆盖、市场、税务、地区、客户数据分类、保留、审计和监管要求。
- 已确认流程之外的 V1 生产运行方式和成功指标。

只影响单一模块的 UNKNOWN 留在对应 module doc 或 Task，不写入本文件。
