# Sheets 模块

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
