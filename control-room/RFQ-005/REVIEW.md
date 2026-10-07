# RFQ-005 CEO Independent Review — 2026-10-07

**Status:** COMPLETE  
**Verdict:** CHANGES_REQUESTED  
**Reviewed Executor HEAD:** `063321ef2cf5e9aa508b488e50df3e9088a36bf4`

## Summary

RFQ-005 的主体实现方向正确。独立 Review 已确认以下关键边界基本符合 Owner 要求：

- 只消费 RFQ-004 的 `QUOTE_FOUND`；`NO_RECENT_QUOTE / ROW_FAILED` 不写、不点更新；
- 14 列 payload 使用 RAW 整行写入，并做精确 readback；
- 空字符串、前导零、小数尾零、空格/换行等按字符串保留；
- Python 不直接写源状态 `采购已报价`；
- `更新报价` 支持幂等重试，成功填入 1 行 / 已有报价 1 行都视为成功；
- 每次 update retry 前重新确认 source、重新写/读 14 列、重新建立 Google operation surface；
- 成功 popup 后只做 source status short-poll，不再次提交；
- 单行 input/update/source 问题保持 ROW_FAILED，后续行继续；
- 共享 Google / ledger / CDP / auth 问题保持 GLOBAL_STOP；
- V1.3 正常相邻行不使用 V1.2 的 180 秒 cooldown；
- 没有引入 V1.3 永久 interruption quarantine；
- RFQ-004 原 inquiry_id / record_identity 与 relocation 边界被保留；
- 未打包、未部署、未覆盖 V1.2。

但发现一个直接关系到真实更新安全的配置校验缺口，因此当前不能标 REVIEWED_DONE。

## Blocking Finding

### B1 — HIGH — API 写入的 worksheet 名称与 UI 打开的 gid 没有被证明是同一张“报价输入子表”

当前 `QuotationInputLocation` 同时保存：

- worksheet title：固定 `报价输入子表`
- `gid`

但两条生产路径分别使用不同标识：

1. `GoogleQuotationInput` 通过 Sheets API range：`'报价输入子表'!...` 写入/回读 14 列；
2. `GoogleQuotationUpdateActions` 通过 URL：`.../edit#gid=<configured gid>` 打开页面并点击 `更新报价`。

当前 `validate_schema()` 只验证“按 worksheet title 读取到的 14 个表头正确”，而 UI guard 只验证 URL fragment 等于配置的 gid。

**没有任何地方验证：这个 gid 实际属于 title = 报价输入子表 的同一个 worksheet。**

因此存在安全场景：API 正确写入报价输入子表，但配置 gid 错误并指向同一 spreadsheet 的另一张 sheet；UI adapter 仍会认为 URL 正确。如果错误 sheet 也存在可点击的更新报价控件，就可能在错误 surface 上执行 Script。

这是 RFQ-005 的关键“写入 → 更新报价”闭环，不能仅依赖人工保证 gid 永远正确。

## Required Repair

只做最小修复，不扩大 RFQ-005 范围。

1. 在 quotation input / location schema validation 阶段，通过现有 Sheets API metadata 能力验证：
   - spreadsheet 可访问；
   - 恰有一个 sheet title 为 `报价输入子表`；
   - 该 sheet 的真实 `sheetId` 与配置 `gid` 一致。

2. 如果 title 不存在、结构异常、sheetId 与 gid 不一致，或 metadata 无法可靠读取，必须 `QuotationInputUnavailable → GLOBAL_STOP`；不能继续写 input，更不能点击更新报价。

3. 不要通过浏览器 DOM 猜 worksheet title。优先使用 Google Sheets API metadata，只新增窄验证。

4. 保持现有 14 列 header 验证：metadata title/gid 绑定正确 + 14列 header contract 正确，两者都成立后才允许写。

5. 不要 hardcode 生产 gid。gid 仍来自未来 RFQ-006 的显式配置，只是在使用前被验证。

## Required Regression

至少补：

1. title = 报价输入子表，metadata sheetId == configured gid → schema PASS，可继续写。
2. title 正确，但 metadata sheetId != configured gid → GLOBAL_STOP；0 write；0 update click。
3. configured gid 指向同 spreadsheet 的另一张 sheet → fail closed。
4. 报价输入子表不存在 → GLOBAL_STOP。
5. spreadsheet metadata read/auth failure → GLOBAL_STOP，错误信息不得泄漏 provider 内容。
6. 现有 14-header mismatch 测试继续 PASS。
7. full RFQ-005 + RFQ-004/V1.2 regression 继续 PASS。

## Non-blocking note for RFQ-006

当前 live-only selector / actual range / Script refresh latency 仍然 UNKNOWN，这一点记录得正确。RFQ-006 在正式接入真实配置前仍需要 authorized read/live acceptance；不要把 offline fake PASS 当成 live acceptance。

## Verification Required

修复后重新执行：

- RFQ-005 focused；
- full safe/offline pytest；
- `python -m ruff check src tests`；
- `git diff --check`。

仍然禁止真实 Google 报价写入、更新报价、Apps Script、Save / Save-and-Send、SMTP、真实业务提交、V1.3 打包/部署或覆盖 V1.2 EXE。

## State transition

`REVIEW_REQUIRED → CHANGES_REQUESTED`
