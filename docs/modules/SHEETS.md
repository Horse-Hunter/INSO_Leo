# Sheets 模块

## Public Contract

Sheets 执行 Workflow 明确调用的单次操作：按 worksheet-specific schema 读取待处理记录，或按原始 opaque `record_ref` / `record_identity` 安全更新目标字段。对外返回统一的 `status`、`mpn/model`、`brand`、`quantity`、`importance_raw`；自身不调度、不 polling。

## V1 Mapping

| worksheet | status | importance_raw | MPN | Brand | quantity | pending |
| --- | --- | --- | --- | --- | --- | --- |
| 标准表 | A | C | E | F | G | A 严格等于 `未发` |
| `shahab` | B | 无源字段；标准化为 `A` | D | E | F | B 严格等于 `未发` |

SHAHAB 的默认 `importance_raw = "A"` 只属于标准化输出，不代表源 worksheet 字段，也不得进入 source snapshot 或 relocation。

实现中的 source snapshot 继续使用统一语义字段承载源值：标准表的
`importance_raw` 保存 C；SHAHAB 的 snapshot `importance_raw` 为 `None`，
只有对外 `PendingSheetRecord.importance_raw` 标准化为 `"A"`。

## Provenance 与 Identity

标准化不得丢失来源。`record_ref` / `record_identity` 必须保留 spreadsheet identity、worksheet identity、original row position 和 worksheet-specific identifying snapshot；row number 不得单独作为永久 identity，V1 不新增 stable Sheet ID 列。

- 标准表 snapshot：A/C/E/F/G；Brand relocation 以 A/C/E/G 唯一匹配，再独立重读 F。
- SHAHAB snapshot：B/D/E/F；Brand relocation 以 B/D/F 唯一匹配，再独立重读 E。Brand 不参与 relocation 消歧。

两种 mapping 均 fail closed：0 或多个 candidate 返回 conflict；写前重新读取；Brand 已由人工填写则 conflict，绝不覆盖。写入必须是对应 Brand 单元格的 targeted update，不得整行覆盖。

原始 row position 只保留为 provenance；即使原位置仍匹配，也必须满足全表
worksheet-specific relocation snapshot 唯一，不能以原位置绕过唯一性检查。

Workflow、Research、INSO、Quotation 只透传 opaque reference。未来任何写回均为 `result + original record_ref -> Sheets`，由 Sheets 识别来源 worksheet 并选择 mapping/safe writer；其他模块禁止出现 `if customer == "shahab"`。

## 集成与 UNKNOWN

当前集成使用 Google Sheets API + OAuth User Authorization。读取 scope 为 `spreadsheets.readonly`，写入 scope 为 `spreadsheets`，不申请 Drive scope；OAuth helper 不持久化 token。真实写入遵守 `BOUNDARIES.md`。

仍为 `UNKNOWN`：生产 spreadsheet/worksheet 标识配置、长期 OAuth token storage/refresh，以及 Brand 以外的可写字段；SHAHAB 未来报价写回列不得提前设计。
