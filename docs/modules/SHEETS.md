# Sheets 模块

## RFQ-003 当前状态写回边界（2026-10-07）

复用现有 targeted RAW 单格写及唯一 relocate/re-read；不改身份生成方式。
采购 SAVED 或 durable 唯一点击已证明的 SUBMIT_UNCONFIRMED 可写发给采购。
写回失败 STATUS_WRITE_PENDING，本单已闭环且绝不再采购，229 提醒人工更新。
该单格失败不暂停模块；整表读取/授权/结构不可用仍 GLOBAL_STOP。
提交前重新校对源型号、品牌、数量、状态；关键冲突终止本单、不覆盖人工数据。
历史中断行人工改为发给采购后仅同步 HUMAN_COMPLETED，不执行采购。

## Public Contract

Sheets 执行 Workflow 明确调用的单次读/写操作。对外返回标准化记录和 opaque `record_ref/record_identity`；自身不调度、不 polling。

## Mapping

| worksheet | status | importance | MPN | Brand | qty | pending |
| --- | --- | --- | --- | --- | --- | --- |
| 标准表 | A | C | E | F | G | A == `未发` |
| SHAHAB | B | 固定标准化为 A | D | E | F | B == `未发` |

V1.2 customer：
- worksheet `2026`：D 列，trim
- `SHAHAB`（case-insensitive）：固定 `SHAHAB`
- 其他：无配置，返回 `None`

## Identity / safe write

Owner 2026-10-06 authorizes a narrow purchase completion transition:
- Confirm durable INSO purchase SAVED before automatic write-back.
- Reuse existing unique non-brand snapshot relocation, read twice, update only
  status A (standard) / B (SHAHAB) from 未发 to 发给采购, then read back.
- Existing 发给采购 is idempotent success; other statuses/missing/ambiguous rows
  are conflicts. Preserve all other cells. No arbitrary status or row writes.
- If write/read-back fails, retain SAVED, email only Owner, retry only the Sheet
  status in future polls. Never reopen or resubmit a purchase for write-back.

`record_ref/record_identity` 必须保留 spreadsheet、worksheet、原 row position 和 worksheet-specific snapshot；row number 不能单独作为永久写入 identity。

Brand write：
- 标准表 relocation snapshot：A/C/E/G，写 F
- SHAHAB relocation snapshot：B/D/F，写 E
- 写前重读，全表唯一匹配才允许
- 0 或多候选 → conflict
- Brand 已有人工作值 → conflict
- 只 targeted update Brand cell，禁止整行覆盖

其他模块只透传 opaque identity，不实现 worksheet-specific relocation。

后续状态模块接入：保留原 `inquiry_id`，调用 Workflow 的
`get_by_inquiry_id` 取回 `record_identity`，再交给 Sheets 定位；不能反解摘要、
按当前行号重算 ID 或仅按型号写回。该 ID 基于入队时表格/工作表/原行号，
不随排序自动移动，行号复用存在旧身份冲突。状态变化不改变已存 ID。
当前采购状态 helper 只支持未发 -> 发给采购及该状态的幂等确认，不是通用
setter；后续状态需明确授权和预期当前状态，继续唯一匹配/写前重读/单格写/
读回。不能用原快照“未发”覆盖后续业务状态。详见 RFQ-002 CEO_REPORT.md。

## OAuth / safety

Owner 2026-10-06: preserve and reuse the existing CurrentUser DPAPI-protected
Google grants outside Git across ordinary restart/version/build changes. Do not
delete/reset grant caches or change the OAuth client to force fresh consent.
Production purchase status service uses allow_interactive=False: reuse/refresh
the cached write grant; missing/revoked/corrupt grant fails visibly and alerts,
never opens repeated consent inside a worker. First write grant was explicitly
completed by Owner; future recovery needs genuine authorization failure evidence,
not another routine authorization request. Executor protects/reuses cache;
Reviewer verifies this flag and grant exclusion from Git/release artifacts.

读取 scope：`spreadsheets.readonly`；写入 scope：`spreadsheets`；不申请 Drive scope。Refresh grant 使用 Windows CurrentUser DPAPI 加密并保存在仓库外。Token 不进入 Git/log。

真实写入必须遵守 `docs/SAFETY.md`；当前 V1.2 Gate 状态见 `CURRENT_TASK.md`。

## RFQ-004 V1.3 read-only source

`query_quotation_candidates` reads exact 发给采购 through the existing schema/row parser; V1.2 pending entry remains exact 未发. `quotation_candidates.relocate_quotation_source` reuses existing exact relocation with sent-state expectation and explicit persisted expected brand, preserving the opaque original identity. No write, poll or new ID. Workflow binds existing ledger inquiry IDs; orphan/ambiguous sources return a row-level failure. CEO B1: strictly verify original position first; only then use unique exact relocation fallback, including expected brand. Never rewrite the original identity.

## RFQ-005 quotation input/status boundary

`quotation_input.GoogleQuotationInput` consumes an explicit `QuotationInputLocation` (no default geometry), validates the exact fourteen headers supplied by RFQ-004 composition, writes all raw strings with RAW and reads them back without coercion/trim; missing trailing cells are empty strings. Shared schema/auth/API failures differ from targeted attempt failures. `relocate_quotation_status` is the existing reviewed original-anchor/unique-fallback read with explicit sent/quoted status scope; sent-only RFQ-004 wrapper unchanged. No Python source 采购已报价 writer exists. Actual geometry remains UNKNOWN.
