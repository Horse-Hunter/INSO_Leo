# Research 模块

## Owner full-query correction (2026-10-25)

All six source searches send the original complete source model (URL encoding
only). Shared core.mpn.lookup_mpn_query generalizes the existing full INSO query;
inso_lookup_query remains an alias. Two-character removal/normalization applies
ONLY to comparison of returned models. IC.net/HQEW/Findchips/BOM/LCSC no longer
truncate retrieval; normal 1–6 and TP 1–12 windows, stock, price legality and
identity rules remain unchanged. This supersedes earlier prefix-query wording.
Reproduced inherited loss using both canonical clients: prefix search omitted
IC reference and HQ offers, full query returned valid results. No live values
or source HTML are stored in repository evidence.

## TP currency correction (2026-10-25, REVIEW_REQUIRED)

BomAiPriceRecord.currency_confirmed records row-scoped currency evidence. The
shared parser normalizes fullwidth currency symbols and corroborates a matched
cloud row's displayed bom_showunit_price unit/amount against its data price.
Missing/conflicting/ambiguous proof is excluded by TP; page-wide form currencies
are not evidence. Legacy bare-number RMB compatibility remains for ordinary
Research, with confirmed=False; ordinary 1–6-month policy is unchanged. TP uses
the existing ECB conversion for confirmed USD and retains original currency.
LCSC NO_MATCHING_PRODUCT is a TP NO_STRICT_MPN_MATCH, not a website outage.

## V1.5 independent TP research (offline, REVIEW_REQUIRED)

`ResearchService.execute_tp(task_id, order, now=...)` is independent of ordinary
execute/Excel output. It reuses the same six adapter instances, their existing
clients/parsers, source retry/session callbacks and shared ECB provider. New
`research.tp` projects raw candidates because ordinary SourceResult discards
all but one price and does not preserve every quotation date. No second network,
browser, login, FX feed or collector is introduced. Ordinary search(), its
1–6 month windows, PriceCandidate contract and INSO-preferred reference stay intact.

TP expands cumulative calendar windows 1..12 until two distinct positive RMB
price levels exist or month12. Each stock bucket is independent; duplicate equal
prices are ties, not a fictitious second price. Per-site quotes retain raw price,
currency and real quotation date; current prices have no quotation date. BOM
`is_current` preserves the original parser's explicit current-price marker while
leaving legacy observed_at behavior unchanged. LCSC and IC.net remain current
price observations, never dated from capture/update time. No promised website
history coverage beyond existing captures; real 12-month visibility is UNKNOWN.

Global actual minima use the selected normal-price pool; no-stock fallback only
when there are no normal quotes and no technical uncertainty. No INSO preference
or V1.4 reference-price override applies to factual TP ranking. Same ECB provider,
Decimal legality and current conversion snapshot are used. No quotes means absent
prices/totals, never zero. Selection semantics require CEO independent review.

## RFQ-003 来源故障隔离（2026-10-07）

复用 ResearchService 和现有全部 adapters；聚合/价格算法不变。
生产组合注入 typed source observer / query recovery，不新增第二套调研。
本节故障策略以 PRODUCT_BASELINE.md 中 2026-10-22 网站持续三小时故障规则为准；
旧版 IC.net/INSO 故障立即全局停止的表述已被该规则取代。本次价格调整不修改故障恢复流程。
人工登录/验证提醒仍走既有通知账本至 Owner 229。无报价仍保持真实无报价，
Workflow V1.2 将本行调研失败安全终结而非自动重跑；重要/重复通知规则不变。
共享 CDP/认证等技术异常仍向原恢复流程报告，不能伪装成正常零价。

## Public Contract

入口：`ResearchService.execute(ResearchInput) -> ResearchResult`。

- Input：`inquiry_id`、`mpn`、可选 `brand`、`quantity`、`importance_raw`。
- Status：`SUCCESS | PARTIAL_SUCCESS | EXCEPTION | RETRYABLE_FAILURE`。
- Research 不决定采购类型、通知资格或 V1.2 路由。

## 来源

正式六价格源：IC.net、Findchips、HQEW、LCSC、Bom.Ai、INSO。

- IC.net：严格 MPN；库存只统计严格匹配且带 SSCP/ICCP 标识的行。无合格库存或总量 `<= 3 × quantity` → `货少`；否则 `货多`。技术失败 → `待验证`，不得当作零。
- IC.net 参考价只从同次型号查询页的 `body > div.navigation > div.cankaoPrice > a > span`
  提取人民币单价，复用已有 HTML tree/可见性及型号校验，不重复查询。空/零/非数字/不可解析
  为正常无有效价（Excel 显示0），不生成候选价；品牌、库存及货量逻辑不变。
  加载/登录/验证/结果页解析故障仍为 SOURCE_UNAVAILABLE（Excel 显示暂不可用，备注保留原因）。
- Findchips：读取可见价格档位；分别保留有库存/无库存最低价。
- Findchips 明确空结果页：已核证 `p.alert.alert-info.no-results` 的完整文本
  `No results were found for <当前型号>.` 是正常无结果，即便没有报价表格。
  必须与当前型号一致；空白页、普通文本、脚本中的提示、登录页或错误页不能据此判空。
  表格记录与空结果标记并存按冲突报错。继续复用原有 source outcome/聚合规则。
- HQEW：只读目标型号市场报价，按下述1至6月窗口取价。
- LCSC：取已展示最低 unit price，分别保留有库存/无库存最低价。
- Bom.Ai：只读目标型号报价区域，按下述1至6月窗口取价。
- INSO：只读历史询价“供方未税价”，按下述1至6月窗口取价。

### 历史窗口及日期依据（Owner 2026-10-22）

Findchips/HQEW/Bom.Ai/INSO 各自先查最近1个自然月，无有效报价再逐月扩大至2、3、4、5、6月。
只选第一个存在有效报价窗口中的最低价，不混入更旧窗口的低价。边界使用原
`calendar_month_cutoff`，包含截止时刻，排除未来及六个月前报价；不新增历史查询。
Findchips 在该站第一个有效窗口内继续分别保存有库存/无库存价，整体正常价格池优先，
原无库存兜底不变。月数 `PriceCandidate.age_months` 支持1至6；2至6月在价格备注显示
两个月/三个月/四个月/五个月/六个月，后缀型号和无库存备注保留。首月沿用原显示格式。

以下是现有采集器/离线样本可识别的日期依据，不代表已实盘确认所有站点都提供完整历史：

| 来源 | 可用报价时间/当前价依据 | 未提供日期时 |
| --- | --- | --- |
| Findchips | 报价行 `data-quotedate` / `data-quote-date` | 当前已展示的价格档位按本次现价归首月；通用 `data-date` 不作为历史报价时间 |
| HQEW | `input.list-data` 的 `quotationDate` / `quoteDate`，含原有相对日期解析 | 当前 `quotationPrice` 按现价归首月，不借用商品/库存更新字段 |
| Bom.Ai | 报价块 `quoteDate` | 仅明确文字“实时报价/当前报价/现价”且有采集时间才归首月；无日期且不能证明当前价则不虚构时间 |
| INSO | 原有 `Stock_VenQuote` 行的 `CreateTime`（沿用现有历史报价记录时间）、`InPrice`、`CurrencyID` | 未提供可解析历史记录时间的行不参与；不拿库存更新时间补齐 |
| LCSC | 当前网页显示的商品/合作库存价格档位 | 不作日期过滤；`更新时间`、`updateTime`、`updatedAt` 不作报价日期，日期缺失不舍弃价格 |
| IC.net | 指定位置当前参考价 | 不作日期过滤，无日期也不虚构历史报价 |

本次仅离线验证，当前实站字段覆盖、六个月历史完整性及实盘取价验收仍为 UNKNOWN。
网站只展示现价就只取现价，已有首屏覆盖范围及访问方式不扩大。

Findchips/HQEW/LCSC/Bom.Ai 的型号比较按现有 canonical normalization；禁止模糊猜测变体。INSO Research 复用 launcher 提供的 authenticated `InsoOperationAccess`，不得自行枚举/接管任意浏览器页面。

## FX 与聚合

USD/RMB、HKD/RMB 使用同日 ECB reference；缺失、重复、日期不一致、非正数或非有限值均 fail closed。

正常价格池：
- IC.net 有效当前参考价
- Findchips 有库存最低价
- HQEW 最低价
- LCSC 有库存最低价
- Bom.Ai 最低价
- INSO 最低价

统一 RMB 后先计算六源实际最低有效价，再按下述 INSO 容差规则选最终参考价。
预估订单总价使用最终选中的未舍入 Decimal 单价乘原 quantity。仅无库存价格可在
所有正常来源均无有效价时作为兜底，并返回 `PARTIAL_SUCCESS`。

### INSO 优先与显示精度（Owner 2026-10-23）

| INSO 首次有价窗口 | 允许高出实际最低价 |
| --- | --- |
| 1个月 | 12% |
| 2个月 | 10% |
| 3个月 | 8% |
| 4个月 | 6% |
| 5个月 | 4% |
| 6个月 | 2% |

INSO 有有效价且 `INSO价 <= 六源实际最低价 × (1 + 容差)`（包含边界）时优先 INSO，
否则使用实际最低价；INSO 本身最低时仍选 INSO。无加权平均、原价修改或筛选变化。
`市场最低参考价` 只写最终选中单价；此前20%差价时追加次低价的多行显示由本条取代。
不新增决策价/权重说明列，六源各自价格列、Excel schema/旧表迁移不变。
内部实际最低/次低候选及原始候选池保留，次低价追加显示标志关闭。

计算和容差判断始终使用原始 Decimal，写出时沿用两位小数显示；如果有效正数会因此
变成0，则保留该正数自身的十进制位（如0.001、0.00001）。这项修复同时覆盖各站价格、
最终参考价和总价的显示，不修改实际计算值。真正的0仍显示0，不生成有效价格候选。
该规则仅离线验证；仍不授权打包、部署或生产业务。

Status：
- 有正常价格且无技术失败 → `SUCCESS`
- 有正常价格但存在技术失败 → `PARTIAL_SUCCESS`
- 无正常价格且存在技术失败 → `RETRYABLE_FAILURE`
- 所有价格源正常完成且无任何有效价格 → `EXCEPTION / NO_MATCHING_PRODUCT`

## 页面生命周期与登录（Owner rule 2026-10-01）

每个来源**每次调用**一律：**新开页面 → 先把登录搞定 → 干活 → `finally` 关掉页面**；下一次调用重新打开、重新登录。不变量：

- 绝不复用上一次调用留下的标签页。已渲染的旧文档看着像新结果，是一整类误判的来源。
- 登录墙是**会话问题**，不是业务结论。站点要求登录就先登录，绝不用“今天没有报价”冒充结果。
- 登录失败一律 fail closed 并给出原因码（`LOGIN_REQUIRED` / `LOGIN_NOT_CONFIRMED` / `MANUAL_VERIFICATION_REQUIRED` / `CREDENTIAL_REJECTED` / `LOGIN_CONTROL_AMBIGUOUS` / `LOGIN_FORM_UNAVAILABLE` / `LOGIN_SUBMIT_FAILED`），绝不用坏结果冒充业务结论。
- **站点怎么答，就立刻怎么报**：挑战（滑块/验证码）和“密码错误”都远早于 settle 超时出现，必须当场抛出，不许拖到超时再给一句含糊话。判据是 `LoginForm.challenge_text` / `LoginForm.rejection`（`await_login_outcome` 每轮先查这两项）。
- **一个控件只有在它是该选择器唯一的可见匹配时才允许被填/被点**（`LOGIN_CONTROL_AMBIGUOUS` 就是这个不变量被破坏时报的码）。隐藏的重复元素可以容忍，真正的歧义必须停下。`page.fill`/`page.click` 不是 strict 的：多匹配时它默默用 DOM 顺序里的第一个。
- 只在 `navigate=False`（attach 模式）下读页而不导航，且该模式不拥有页面、不关页。

六个站点共用 `src/research/site_login.py`——同一份“填表 → 绝不盲提交 → 等站点自己跳走 → 由调用方证明”的实现。此前这段流程被抄了三遍（`CdpIcNetClient`、`CdpBomAiAuthenticatedBrowser`、`CdpLcscClient`），现在只有一处。凭据仍只走 Core Provider，`site_login` 自己不留存任何密钥。

### 实战记录：`text="登录"` 点到标题上（2026-10-01）

立创登录一直“没登进去”，现场看是**点了「账号登录」页签，但从来没点登录按钮**。实测 `passport.jlc.com`：页签打开后 `text="登录"` 匹配到**两个可见元素**——页面自己的 `<h2>` 大标题（DOM 顺序在前）和提交按钮里的 `<span>`。`page.click` 非 strict，就点了标题；按钮没被按到，表单没提交，30 秒 settle 超时后只报一句 `LOGIN_NOT_CONFIRMED`，看不出断点。

修法两处：提交选择器改成账号表单自己的按钮 `button.submit`（JLC 自己标记为 `spm=login.account.submit`，页面上是唯一带 `submit` 类的 `<button>`）；以及把“唯一可见”变成共享实现里的硬不变量——判据太松和“在不在 DOM ≠ 有没有渲染”是同一类事故。

| 站点 | 登录入口 | 挑战 | 拒绝凭据的文案 |
|---|---|---|---|
| IC.net | `member.ic.net.cn/login.php`（`#username`/`#password`/`#btn_login`） | `#loginCode`，提交后判定 | `REJECTED_PASSWORD_TEXT` |
| Bom.Ai | 浮层内 `账号登录` 页签 → 配置化选择器 | 可见文案判定 | `REJECTED_PASSWORD_TEXT`（实测「密码错误」） |
| LCSC | `passport.jlc.com` 的 `账号登录` 页签，提交 `button.submit` | `challenge_text`：`安全验证`/`请按住滑块`；`_reject_lcsc_challenge` 兜底 | `REJECTED_PASSWORD_TEXT` |
| HQEW | `passport.hqew.com/login`（`#J_loginName`/`#J_loginPsw`/`#J_btnLogin`），提交前确认隐私协议 | `#J_verifyCode`/阿里云验证触发器，默认隐藏；`#J_uislider` 是广告轮播，不是 CAPTCHA | `REJECTED_PASSWORD_TEXT` |
| Findchips | `/signin`（`#email-address`/`#password`/`#j-signin button.signin`） | 无 | `REJECTED_PASSWORD_TEXT` + `incorrect password`/`invalid password` |

### 实战记录：判决拖到超时才给，等于没给（2026-10-01）

Owner 要求“所有网站的登录功能都应该健壮”。逐源重放研究腿后发现两处**都是真失败、但都被报成了含糊结论**：

| 站点 | 站点实际说了什么 | 修复前 | 修复后 |
|---|---|---|---|
| LCSC | 提交后出现滑块：`安全验证 / 为了您的账号安全，请完成验证 / 请按住滑块，拖动到最右边` | 55.0s → `INTERACTIVE_CHALLENGE_REQUIRED` | **12.7s** → `MANUAL_VERIFICATION_REQUIRED` |
| Bom.Ai | 提交后浮层显示 `密码错误`（约 1.5s 即出现） | 55.6s → `LOGIN_NOT_CONFIRMED` | **7.6s** → `CREDENTIAL_REJECTED` |

`LOGIN_NOT_CONFIRMED` 把“密码是错的”说成了“会话没确认”，指向完全不同的修法；而这两条信息都在 2 秒内就摆在屏幕上，只是没人看。于是 settle 循环（现名 `await_login_outcome`）每轮先查挑战与拒绝文案，命中即抛。`LoginForm` 因此多了 `challenge_text`（站点用文字说的挑战）与 `rejection`（站点拒绝凭据的文案）两个字段；只允许填**提交前实测不存在**的文案，否则就会拒绝一个还没试过的表单（立创提交前 body 212 字符，两个滑块标记都不在，已实测）。

`_failure_reason` 也改为显式命名这几个共享判决码：`CREDENTIAL_REJECTED` → 「账号或密码被站点拒绝」、`CREDENTIALS_UNAVAILABLE` → 「没有可用的登录凭据」、`LOGIN_FORM_UNAVAILABLE`/`LOGIN_CONTROL_AMBIGUOUS` → 「站点登录表单已变化」。此前它们都落进含 `CREDENTIAL`/`LOGIN` 的通用分支，四种不同故障说同一句话。

**上述是早前实盘记录，不是当前登录状态**。2026-10-01 后续六站复验已全部通过；
立创/正能量未再出现上述失败，华强协议漏勾与广告误判修复后也登录成功。
未来出现真实 CAPTCHA/OTP 或密码拒绝仍须按实际站点判决处理，不能用旧失败代替当前检查。

HQEW 与 Findchips 的登录在 V1.1 里**从不存在**（只有“检测到登录页就放弃”）。这次是补上，不是重写既有实现。

## 独立登录检查与会话中断（Owner 2026-10-01）

GUI「一键登录所有网站」调用 launcher 的 `SiteLoginSweep`，依次复用
IC / Findchips / HQEW / LCSC / Bom.Ai 的既有登录函数，以及 INSO 的
`InsoSessionGuard`；不另建登录实现。唯一浏览器为固定 9222 CDP，唯一
profile 为 `D:\Program_Leo\INSO_CDP\chrome-profile`（见 `CDP_SESSION_POLICY.md`）。
无论版本、阶段或站点失败，都不得用另一 CDP/profile 排障。

- 每站给出已登录、登录成功、人工验证、拒绝凭据或不可用结果；GUI 汇总弹窗。
- 登录页空白或 HTTP 错误不得判已登录；共享等待逻辑到期仍在表单上必须报
  `LOGIN_NOT_CONFIRMED`，不能正常返回让华强/Findchips 误判成功。
- 验证码控件检查复用全部可见匹配的公共判据，隐藏的第一个匹配不能遮住
  后面的可见验证码。提交前已有人工挑战时不得先填写凭据。
- 成功站点复用一个临时页；失败页留在同一 Chrome 供人工处理，后续站点
  换标签页而不换 CDP/context。登录检查结束仅断开客户端，绝不关闭 Chrome。
- CAPTCHA / 滑块 / OTP 由 Owner 手工处理；立创不自动拖动验证滑块。
- 登录检查与询价互斥。人工完成后可关闭多余标签页，再开始询价；如果
  Owner 自行正常关闭 Chrome，只能恢复同一受保护 profile/9222，不能建新 session。
- 询价中的登录异常停止当前流转和后续订单/工作表；失去登录的部分 Research
  结果不得进入业务路由/采购。复用既有队列释放机制保留未完成询价，恢复后重跑。
- 采购阶段 `SESSION_STALE` 同样停止后续流转。正常「本轮完成后停止」仍按原规则
  排空本轮，不与登录异常的立即停止混淆。
- 登录警告复用 QQ SMTP；仅收件人 `linan229@qq.com`，每轮最多一次，失败在 GUI
  日志显示。不修改重要/重复订单通知的原有收件人和规则。
- 有持久化 cookies 不代表服务器 session 仍有效，INSO 必须沿用新导航与控件验证。

本功能不开放 INSO 最终保存/发送或 Sheets 写入，也不触发 EXE 打包。

## Excel

正式输出：`调研价格.xlsx`。

可见列：
`型号 | 品牌 | 数量 | 重要等级 | 货量标识 | 预估订单总价 | 市场最低参考价 | INSO | Findchips | 华强 | 立创 | 正能量 | IC.net | 备注 | 处理时间`

隐藏 `_inquiry_id` 用于幂等，隐藏 `_research_status` 保存结果状态。Excel load/schema/save 失败 → `RETRYABLE_FAILURE`。技术失败详情只进备注，不伪装成业务“无结果”。

五价格源旧表及原有更早 schema 均可按列名兼容读取；首次写入沿用原原子迁移，
保留历史各字段、来源价、隐藏状态/身份及单元格样式/批注，新增 IC.net 列。
旧记录 IC.net 留空，不回填虚构价格；新采集无参考价显示0且不进入最低价池。

## 边界

Research 只做调研与本地 Excel 持久化；不读写 Google Sheets，不执行主动采购，不决定 V1.2 通知/采购业务规则。Credential 只走 Core Provider。普通 browser/session readiness 复用共享 runtime；CAPTCHA/OTP/设备验证才需要人工。

Owner 2026-10-08: all source MPN filtering now delegates to core.mpn.lookup_mpn_matches; native query URLs use lookup_mpn_prefix exactly once, result parsers retain the full original target. INSO history records retain observed PartNo for filtering/evidence; records without an observed model cannot supply a price. Existing source-specific windows/stock/price rules remain. Research native first-page coverage limits remain unchanged.

## RFQ-011 ICNET package-read extension

`parse_icnet_packages`/`select_icnet_package` reuse the existing HTML tree and hidden
text handling. They use first20 displayed product rows in DOM order, require one
visible result_pakaging column per row, ignore empty text, mode/first-seen tie.
No secondary MPN matching, manufacturer or stock filtering in this capability.
`CdpIcNetClient` default login/search/prefix/cooldown remain unchanged; optional
tab_owner reserves V1.4 query tabs against parallel inquiry parking. Only the
client's own query tab is closed in its existing finally path. Launcher reuses
CoreResearchCredentials, shared9222 attachment and this client, no second login
or search implementation. Exact repeated contract models cache per invocation.
