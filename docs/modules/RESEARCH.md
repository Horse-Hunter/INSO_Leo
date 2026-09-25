# Research 模块

## Public Contract

入口为 `ResearchService.execute(ResearchInput) -> ResearchResult`。

- `ResearchInput`：`inquiry_id`、`mpn`、可选 `brand`、`quantity`、`importance_raw`。
- `ResearchResult`：`inquiry_id`、`status`（`SUCCESS | PARTIAL_SUCCESS | EXCEPTION | RETRYABLE_FAILURE`），以及可选 `resolved_brand`、`reason_code`、`remarks`；V1 不含 `output_ref`。
- `importance_raw` 在 Excel 原样显示（预期 `A | B | C | D`），不得改变来源、顺序、选价、status、retry 或型号判断。

## 来源与共同规则

IC.net 只负责 Brand 与货量，不是价格源。五个价格源为 Findchips、HQEW、LCSC、Bom.Ai 和 INSO；INSO 在 Research 中仅作 read-only 历史市场价格查询。

Findchips、HQEW、LCSC、Bom.Ai 的 target/observed 型号比较前去除 `-` 和所有空白并忽略大小写；规范化后只接受完全匹配，或网站型号等于完整搜索型号再加最多 6 个尾随字符。禁止内部/前缀变化或猜测变体；使用后缀型号时在对应来源单元格附实际网站型号，完全匹配不标。IC.net 继续使用下述严格匹配。

上述四个网页价格源有日期字段时只使用最近 1 个自然月；无日期字段时不做时间过滤。自然月边界为上月同日、同一 wall-clock time，遇短月钳制到月末。INSO 使用下述 1/2/3 月阶梯。

每个价格源必须区分业务无结果与技术失败。Evidence 记录 source、query、可选 matched MPN/URL、outcome、采集时间和 typed observations，不得包含 Secret、cookie 或 token。价格使用正 `Decimal`，保留原币种和标准化人民币值。

## 来源规则

### IC.net

- 用于 Brand 或货量的每一行仍必须满足 STRICT MPN MATCH：只去除首尾空白并忽略大小写，不允许内部空白、标点、前后缀或封装代码变化。
- 非空输入 Brand 原样保留；否则最多检查第一页前 20 行，按出现频率、英文优先、较短英文名依次选择 manufacturer；仍并列则 unresolved，不翻译、映射或编造。
- 汇总第一页严格匹配且实际认证标识区域带 SSCP 或 ICCP 的库存；供应商说明中的文字不算标识。同一行两种认证只计一次，Brand 不过滤库存。没有合格库存或严格型号行时显示 `货少`；总量 `<= 3 × quantity` 显示 `货少`，否则 `货多`。访问或解析失败时显示 `待验证` 并在备注保留技术失败，不得当作零。
- 登录凭据只通过 Credential Provider 获取，用于批准的 read-only session。

### 五个价格源

- **Findchips：**`quantity` 不参与选价；以页面逐档可见价格和币种为准，避免隐藏属性与显示币种不一致；每个 tier 先按对应的 ECB 参考汇率换算 RMB，再分别选有库存、无库存最低价；原始币种、汇率和标准化人民币价保留在 evidence。
- **HQEW：**不使用页面上方“市场参考价”；只读允许型号匹配的历史市场报价，取最近 1 个自然月最低价，不区分库存。
- **LCSC：**`quantity` 不参与选价；取已展示最低 unit price，分别保留有库存、无库存最低价。RMB/CNY 直接使用，USD 转 RMB。
- **Bom.Ai：**只读网页下方目标型号报价区域，不混入页面上方其他型号；取最近 1 个自然月最低价，不区分库存。RMB 直接使用，USD 转 RMB 后比较；登录能力由 Credential Provider 注入。
- **INSO：**路径为“业务询价 → 采购临时询价 → 输入型号 → 查询”，只读该区域下方历史询价结果，使用正数“供方未税价”；零为无有效报价。USD 转 RMB，不判断库存，也不做型号匹配过滤。先取 1 个自然月最低价；无有效价再依次扩大到 2、3 个自然月，来源单元格分别标 `（两个月）`、`（三个月）`；3 个月仍无正数则无结果。2/3 月价格正常参与聚合。

USD/RMB 使用 ECB 同日 daily reference：`CNY per USD = CNY per EUR / USD per EUR`。缺失、重复、日期不一致、非正数或非有限值均 fail closed；不得 fallback 或隐藏舍入。
HKD/RMB 同样使用 ECB 同日 daily reference：`CNY per HKD = CNY per EUR / HKD per EUR`；价格计算保持原始 Decimal 精度，仅业务展示保留两位小数。

## 聚合与 Status

正常价格池只包含：Findchips 有库存最低价、HQEW 最低价、LCSC 有库存最低价、Bom.Ai 最低价、INSO 最低价（含 2/3 月兜底）。统一 RMB 后，池中最低价为市场最低参考价；预估订单总价为该价乘 `quantity`。Findchips/LCSC 无库存价通常只展示，不进入正常池。

- 有正常价格且五个价格源无技术失败：`SUCCESS`。
- 有正常价格且任一价格源技术失败：`PARTIAL_SUCCESS`。
- 无正常价格且任一价格源技术失败：`RETRYABLE_FAILURE`；不得提前判断客户型号错误。
- 五个价格源均正常完成、无正常价格但有无库存价格：用无库存价格作为兜底池计算最低价与总价，返回 `PARTIAL_SUCCESS`，备注 `仅找到无库存报价`。
- 五个价格源均正常完成且无任何有效价格：返回 `EXCEPTION`，原因 `NO_MATCHING_PRODUCT`，备注说明五个来源均无报价，型号可能填写有误。Research 不产生等待人工复核状态。

存在第二个正常或兜底 candidate 且 `lowest <= second × 0.80` 时，市场最低参考价换行附第二低价格及来源；否则只显示最低价。

## Excel 输出

`调研价格.xlsx` 是 V1 正式持久化输出。可见表头严格为：

`型号 | 品牌 | 数量 | 重要等级 | 货量标识 | 预估订单总价 | 市场最低参考价 | INSO | Findchips | 华强 | 立创 | 正能量 | 备注 | 处理时间`

隐藏 `_inquiry_id` 作为幂等键；隐藏 `_research_status` 保存正式 Research 结果状态。`处理时间` 为带 UTC offset 的 ISO-8601 更新时间；retry/crash 不得产生重复正常行。已存在历史行迁移时处理时间保持空值，不推断时间。`ResearchExcelOutput.read_history()` 是 Research-owned、只读、不迁移的历史读取 Contract；按处理时间新到旧返回，缺失/无效时间记录在后并维持原 Excel 行序。未保存 Research 状态的旧行不推断结果状态。必要落盘成功后才能返回 `SUCCESS`、`PARTIAL_SUCCESS` 或 `EXCEPTION`。Excel load/schema/save 失败按 `RETRYABLE_FAILURE` fail closed。旧文件中已保存的 `MANUAL_REVIEW_REQUIRED` 状态仍可作为历史记录兼容读取，并按异常展示；新执行不再写入该状态。

五个来源列只显示业务结果：价格；价格加 `（无库存）`、实际后缀型号或 `（两个月）`/`（三个月）`；同一来源有库存/无库存价可分行；无业务结果或技术失败均显示 `无结果`。技术失败详情只写备注，格式为“网站名称 + 简洁失败原因”。

## 边界与 UNKNOWN

Research 不访问 Google Sheets、不调度流程、不执行主动 INSO 采购、不计算 Quotation。它可直接使用已批准的 INSO read-only Research adapter，但不依赖 `inso` 模块；本地 Excel 是 V1 唯一写入。

仍为 `UNKNOWN`：完整 reason-code catalog、额外输入校验、Excel 保留/并发锁策略，以及 Future INSO Module 的重要性规则。Selector、XPath、session、workaround 和 Task 历史不属于长期 Contract。

## V1.2 shared-session safety seam

Research 的价格选择、MPN、stock、FX、retry 和输出规则没有改变。其 INSO
history browser adapter 已移除任意 first-page 选择及 attached-browser close；
必须注入经 composition root 验证的 `InsoOperationAccess`，每次只打开并关闭
自己的 child page。当前 production composition root 尚未提供该 lease，故该
Research source 在未接线时 fail-closed。不得通过恢复旧 CDP page enumeration
绕过此要求；真实兼容验证须等待单独授权的只读 discovery。
