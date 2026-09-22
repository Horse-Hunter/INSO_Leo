# Research 模块

## Public Contract

跨模块入口为 `ResearchService.execute(ResearchInput) -> ResearchResult`。

`ResearchInput`：

- `inquiry_id`
- `mpn`
- 可选 `brand`
- `quantity`
- `importance_raw`

`ResearchResult`：

- `inquiry_id`
- `status`：`SUCCESS | PARTIAL_SUCCESS | MANUAL_REVIEW_REQUIRED | RETRYABLE_FAILURE`
- 可选 `resolved_brand`
- 可选 `reason_code`
- 可选 `remarks`

V1 不含 `output_ref`。Research 向 Workflow 返回 `resolved_brand`。`importance_raw` 只用于 Excel 展示：严格等于 `A` 或 `B` 时显示 `重要`，其他显示 `普通`；不得影响来源、顺序、价格逻辑、evidence、status、retry 或匹配。

## 来源与 Evidence

已确认的 read-only 来源为 IC.net、Findchips、HQEW、LCSC、Bom.Ai。Findchips、HQEW、LCSC、Bom.Ai 是四个价格源；IC.net 只提供 Brand 解析和市场货量展示。

STRICT MPN MATCH 只去除首尾空白并忽略大小写；不得改变内部空白、标点、前后缀、封装代码，也不得猜测变体。

聚合前，每个价格源返回 `SUCCESS`、`NO_STRICT_MPN_MATCH`、`NO_VALID_PRICE` 或 `SOURCE_UNAVAILABLE`。技术失败必须与业务无结果区分。Evidence 记录 source、query、可选 matched MPN/URL、outcome、采集时间和不可变 typed observations，绝不包含 Secret、cookie 或 token。Price candidate 包含 matched MPN、decimal-safe 原始价格/币种、标准化人民币价格、source、URL 和采集时间。

## 长期来源规则

### IC.net

- 用于 Brand 或货量的每一行都必须满足 STRICT MPN MATCH。
- 非空输入 Brand 原样保留；否则最多检查第一页前 20 行，依次按出现频率、英文优先、较短英文名选择展示 manufacturer；仍并列则保持 unresolved。不得翻译、音译、做别名映射或编造 Brand。
- 汇总第一页严格匹配且带 SSCP 或 ICCP 的库存；同时带两种认证的行只计一次，Brand 不过滤库存。总量 `<= 3 × customer quantity` 显示 `货少`，更大显示 `货多`。必须计入但无法解析的数量是 `SOURCE_UNAVAILABLE`，不是零。
- 登录通过 Credential Provider 获取授权凭据，仅用于有边界的 read-only session。

### 价格源

- **Findchips：**要求严格 MPN 且库存为正。选择不高于客户数量的最大已展示 quantity tier，不得用更高 tier 或区间摘要代替。MOQ 不作为排除条件，也不持久化。只接受 USD tier，并选择最低合格 USD unit price。
- **HQEW：**通过 loopback CDP 复用 Owner 已登录的普通 Chrome，读取第一页云价格；不得导出/持久化 cookie，也不得把匿名 HTTP 作为 production path。不得绕过安全挑战。当前临时策略下，若其他来源已有有效 candidate，安全挑战为 non-blocking，落盘并返回 `PARTIAL_SUCCESS`。
- **LCSC：**只使用官方产品页代表的主产品，并选择不高于数量的最大已展示 tier。已展示的预售或零库存价格仍可用。明确 RMB/CNY 不走 FX；USD 使用已批准 FX boundary。
- **Bom.Ai：**通过注入的 Credential Provider/login 能力访问。价格有效期为一个自然月：取上月同一 wall-clock time，超出月末则钳制到月末。有最近 7 天有效价时取其最低价，否则取自然月窗口最低有效价；更旧价格不可作为 candidate。

USD/RMB 使用 ECB daily reference API：同日 USD/EUR 与 CNY/EUR 推导 `CNY per USD = CNY per EUR / USD per EUR`。数值和计算使用正 `Decimal`；缺失、重复、日期不一致、非正数或非有限值均 fail closed。不得使用 fallback rate 或隐藏舍入。

## 聚合与 Status

- 按标准化人民币 unit price 排序；最低 candidate 是市场参考价。
- 存在第二 candidate 且 `lowest <= second × 0.80` 时，显示最低价，并换行附第二低价格及来源；否则只显示最低价。
- 预计总价为精确的最低 unit price × customer quantity。
- 至少一个 candidate 且任一价格源 unavailable 时为 `PARTIAL_SUCCESS`；有 candidate 且无 unavailable 来源时为 `SUCCESS`。
- 只有四个价格源都查询成功且均无 STRICT MPN MATCH，`NO_MATCHING_PRODUCT` 才映射为 `MANUAL_REVIEW_REQUIRED`。技术失败不等于“无匹配”；Bom.Ai 有严格匹配时，即使价格过期、缺失或不可用，也不属于“无匹配”。
- 没有可用 candidate 且不满足“全部无匹配”时为 `RETRYABLE_FAILURE`。

## Excel 输出

项目本地 `调研价格.xlsx` 是 Research V1 正式持久化输出。可见列为 `型号`、`品牌`、`数量`、`重要等级`、`货量标识`、`预计订单总价`、`市场最低参考价`、`备注`；隐藏 `_inquiry_id` 是幂等键。

retry/crash 恢复不得为同一 inquiry 产生重复正常行。必要输出成功后才能返回 `SUCCESS` 或 `PARTIAL_SUCCESS`，且 `PARTIAL_SUCCESS` 必须有有效价格。Excel load/schema/save 失败按 `RETRYABLE_FAILURE` fail closed；schema 不明确或无法识别时不得猜测。

## 边界与 UNKNOWN

Research 不访问 Google Sheets、不调度全局流程、不执行 INSO、不计算 Quotation。外部访问只对已确认来源 read-only；本地 Excel 是 V1 唯一写入。依赖方向归 `MODULE_INDEX.md`，安全规则归 `BOUNDARIES.md`。

仍为 `UNKNOWN`：更完整的 reason-code catalog、额外输入校验/status 字段规则、Excel 展示精度/保留/并发锁策略，以及未来 INSO 重要性规则。Selector、XPath、session 机制、临时 workaround 和 Task 历史不属于长期 Contract。
