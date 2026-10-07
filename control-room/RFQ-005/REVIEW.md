# RFQ-005 CEO Independent Review — 2026-10-07

**Status:** COMPLETE  
**Verdict:** PASS / REVIEWED_DONE  
**Reviewed Executor HEAD:** `df176dd803fc8ebf7e03a9482718302fa1285220`  
**Previous blocking review:** B1 at `d9bbeebdff94261ed7aff7318096202b557cee29`

## Decision

RFQ-005 is approved.

Owner 已纠正真实 Google worksheet title 为 `报价输入`。本次修复同时完成名称纠正和 title↔gid 的 fail-closed metadata 绑定校验；此前错误名称 `报价输入子表` 不再作为生产 alias 接受。

RFQ-005 仍保持 read/update-side source delivery 边界：未接最终15分钟总调度、GUI、229邮件、正式 V1.3 打包部署，也未覆盖当前 V1.2 EXE。

## B1/B2 verification

### PASS — 真实目标名称已统一为 `报价输入`

`QuotationInputLocation` 现在只接受 worksheet title `报价输入`。旧名称 `报价输入子表` 会直接以 `QUOTE_INPUT_LOCATION_INVALID` fail closed。

当前 Sheets range 也统一使用 `'报价输入'!...`；没有保留双名称兼容路径。

### PASS — API worksheet title 与 UI gid 已被证明属于同一张 sheet

`GoogleQuotationInput.validate_location_binding()` 使用现有 Sheets service 的 spreadsheet metadata，只读取：

- `sheets.properties.sheetId`
- `sheets.properties.title`

并要求：

- metadata shape 可验证；
- 恰有一张 title 为 `报价输入`；
- `sheetId` 为非负整数且不是 bool/字符串/浮点；
- `str(sheetId)` 与显式配置 gid 完全一致。

任何 title 缺失、重复、sheetId 异常、gid 不匹配、metadata/API/auth 读取失败都会抛 `QuotationInputUnavailable`，随后由 workflow 映射为 `GLOBAL_STOP`。

因此不会出现“Sheets API 写 A 表、浏览器却在同一 spreadsheet 的 B 表点击更新报价”的配置漂移。

### PASS — 错误 binding 在任何写入或 UI 打开前停止

`V13QuotationUpdater` 在打开 Google operation surface 前执行 `validate_schema()`；该方法先验证 title/gid metadata binding，再验证14列表头。

`write_payload()` 本身也再次执行 schema/binding 验证，因此直接调用 writer 也不会绕过安全边界。

回归覆盖确认错误 gid、gid 指向另一 sheet、目标 sheet 缺失、metadata 结构异常、metadata auth/API failure、14-header mismatch 时均：

- 0 quotation RAW write；
- 0 Google operation page open；
- 0 更新报价 click；
- GLOBAL_STOP。

### PASS — 14列 header 与 RAW 写入边界保持

title/gid binding 通过后仍必须通过精确14列 header contract，之后才允许完整 RAW 写入。

RFQ-005 原有以下边界未被弱化：

- 14列全部写入，包括空字符串；
- 精确 readback；
- 不 trim / 不重格式化报价内容；
- Python 不写源状态 `采购已报价`；
- popup `成功填入1行` => `UPDATED_INSERTED`；
- `已有报价1行` => `UPDATED_ALREADY_EXISTS`；
- 成功 popup 后不重复 update，只短轮询 source status；
- update 未确认最多初次+3次幂等重试；
- 单行 targeted failure 继续下一行；
- 共享 Google / ledger / CDP / auth failure 仍 GLOBAL_STOP；
- V1.3 正常相邻订单无180秒 cooldown；
- 无 V1.3 永久 interruption quarantine。

## Regression / evidence reviewed

Executor reports for repaired HEAD:

- focused: **182 passed**
- full safe/offline: **1235 passed / 1 skipped**
- Ruff: **PASS**
- `git diff --check`: **PASS**

新增/修复测试覆盖包括：

- 正确 title + 正确 sheetId/gid；
- 错 gid；
- gid 指向同 spreadsheet 另一 sheet；
- 目标 `报价输入` 不存在；
- duplicate/malformed metadata；
- sheetId bool/string/float/negative 等非法形态；
- metadata provider/auth/401/403 failure；
- binding 正确但14列表头错误；
- `UPDATED_INSERTED` / `UPDATED_ALREADY_EXISTS` 完整离线闭环；
- RFQ-004 / RFQ-003 / V1.2 回归。

未执行真实 Google 报价写入、更新报价、Apps Script、Save、Save-and-Send、SMTP、真实业务提交、打包或部署。

当前 V1.2 EXE 保持不变：

`1A49C9650BA531F2299326FFC89761D0391CD5F2C0FE32327DDD0736BD5C3E84`

## Residual live-only unknowns

以下仍是 RFQ-006 / authorized live acceptance 前的明确 UNKNOWN：

- 生产 gid；
- 真实输入 row/column 与14列表头布局；
- `更新报价` 按钮实际 DOM/role；
- popup / dismiss 实际 DOM；
- Apps Script 刷新延迟；
- Google 登录、权限和生产会话行为。

这些不阻塞 RFQ-005 的源码/离线验收，但 RFQ-006 不得把 synthetic PASS 当作 live acceptance。

## Final state

`CHANGES_REQUESTED → REVIEW_REQUIRED → REVIEWED_DONE`

RFQ-005 is complete and may be used as the baseline for RFQ-006.
