# Sheets 模块

## Public Contract

Sheets 每次只执行一个由 Workflow 明确调用的 Google Sheets 操作：读取待处理记录，或执行明确命令下的安全字段更新。`query_pending_records` 返回结构化 Record 和 `record_identity`；自身不调度、不 polling。

## V1 读取

| Column | 含义 |
| --- | --- |
| A | 状态 |
| C | 重要等级原始值 |
| E | 型号 / MPN |
| F | Brand |
| G | 数量 |

仅当 A 严格等于 `未发` 时 Record 才待处理。Workflow 将 C 原样作为 `importance_raw` 接收。

## Identity 与写入

- Record identity 由 worksheet identity、row position，以及 A/C/E/F/G identifying snapshot 组合；row number 不得单独作为永久身份。
- Brand 写入先尝试原行完整 snapshot，随后必须以 A/C/E/G 唯一重定位并再次读取；F 不参与 relocation 消歧。缺失或不唯一时返回 conflict，且不写入。
- V1 不新增 stable Sheet ID 列。
- 只有 F 仍为空时才允许写 Brand。写前立即重读 F；人工已填写时返回 conflict，绝不覆盖。
- 当前 writer 只以 RAW targeted update 更新单个 F 单元格；不得为更新一个字段而整行覆盖。

当前 adapter 使用 Google Sheets API + OAuth User Authorization。读取使用 `spreadsheets.readonly` scope，写入使用 `spreadsheets` scope，不申请 Drive scope；OAuth helper 不持久化 token。所有真实写入同时遵守 `BOUNDARIES.md`。

历史 live-read smoke 已完成；live Brand write 因当时没有可安全唯一定位的 candidate，尚未成功执行真实写入。

## 边界与 UNKNOWN

Workflow 负责 15 分钟触发、全局状态、retry 和 duplicate prevention。依赖方向归 `MODULE_INDEX.md`。

仍为 `UNKNOWN`：生产 spreadsheet/worksheet 配置、长期 OAuth token storage/refresh 策略，以及 Brand 以外的可写字段。
