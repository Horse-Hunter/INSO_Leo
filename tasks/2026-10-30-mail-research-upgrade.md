# RFQ-016 subtask: detailed mail research and independent IMAP

Status: REVIEW_REQUIRED / NOT_DEPLOYED. F source `55ba0f230ce4a42eeda78d4aa942e9065bfc4ba3`;39targeted PASS,3393full PASS/1SKIP. Existing3354tests and A/B/C/D/E preserved. QQ real IMAP commands remain SECURITY_ENABLEMENT_BLOCKED. Production effects NOT_VERIFIED. See original RFQ016 TEST_REPORT.json/EXECUTION_LOG.md.

Scope: fix A/B/C first; extract canonical TP detailed collection/report without changing TP target selection or purchase/quote behavior; enrich important/follow-up mail; process new authenticated-sender IMAP research requests independently of business buttons. Same Chrome9222, per-task owned pages, no production operations. Reuse Core Vault, native six adapters, FX, SQLite outbox and SMTP protection. Offline fakes only. Owner separately authorizes installation after CEO review.

Acceptance: all Owner attachment cases, bounded polling/research, durable UID/outbox protection, read-only unique latest order match, recovery without cross-owner page effects, targeted red/green and full suite. COMPUTER_USE_NOT_USED.

## Full Owner requirement (source: attached request, 2026-10-30)

# INSO_Leo — RFQ-016整改 + 详细调研邮件升级 + 独立IMAP调研服务

你是新的Codex Executor。请完整阅读以下要求，不要拆成多个相互覆盖的任务。

项目：`Horse-Hunter/INSO_Leo`

分支：`codex/v1-6-independent-scheduling`

最新CEO审核SHA：
`6c1ba7fa850583515bc78798301c4a4139d0c0d8`

先阅读：
- `AGENTS.md`
- `AI_START_HERE.md`
- `control-room/RFQ-016/TASK_SPEC.md`
- RFQ-016末尾的CEO Review
- TP调研相关的现有模块、邮件格式和浏览器资源管理代码

历史未推送提交`7574516`不得丢失，不能盲目reset、覆盖或清理未知文件。

## 第一部分：完成RFQ-016原有整改

保留已经实现的功能：

1. 自动询价、自动报价只处理询价日期最近7个自然日的订单。
2. 自动TP及未来个性化需求模块只处理最近一个自然月的订单。
3. Owner明确发起的单笔手工重跑不受年龄限制，但仍须遵守原身份、当前状态、权限、防重复及UNKNOWN写入保护。
4. 任务中心正确显示最新已确认的Google客户状态，不再让历史“已发采购单”遮盖当前“已报价给客户”。
5. 异常邮件严格审核，不允许暂时性Google读取超时、已恢复故障、历史订单等产生误报警。

优先修复CEO指出的三个缺陷：

**A. 报价未知写入崩溃窗口**

目前`_uncertain_refresh`存在通知凭据缺失时直接返回、价格基线可能先于durable hold更新的问题。必须保证外部写入UNKNOWN先可靠持久化保护，再推进价格基线。

使用故障注入和重启恢复测试验证，不可重复报价，不可丢失UNKNOWN，不可重复发邮件。

**B. 持续Google异常邮件使用旧快照**

禁止使用过期的`last_success`冒充当前订单状态。如果程序未能确认订单现在确实仍需处理，不得向Owner发送这笔订单的异常邮件。

真正经过验证、持续阻断业务、必须人工处理的故障仍应准确通知一次。

**C. 已完成订单收到历史重要询价邮件**

重要询价、重复询价等业务邮件在实际发送前，须核对原事件是否仍适用。如果客户已经手工报价完成，旧的“重要询价待跟进”不得继续发送。

保留合法的正常业务通知以及原SENT/UNKNOWN幂等保护。

三个问题必须有先失败后修复的定向回归。

## 第二部分：统一升级详细调研能力

现有普通Research报告信息量较小，而TP具备六个来源的完整报价采集、筛选、货币换算和邮件HTML展示能力。

要求把TP的**详细调研能力抽取为可复用公共代码**，而不是复制一份TP代码。

复用：
- IC.net、Findchips、华强、立创、正能量、INSO六来源采集
- 原完整MPN匹配及各网站原生解析器
- 当前价格、有效历史报价、库存情况
- 原TP的历史报价窗口、最低/次低有效报价选择
- 汇率换算及价格格式化
- 原SMTP/outbox/幂等安全能力
- 原报告HTML布局与每个来源的报价明细

普通业务、TP业务及新IMAP业务可以使用同一套详细报价采集与报告组件，但不同业务必须具有独立的任务身份和运行资源。

原TP业务的目标价判断逻辑保持不变。

**对于普通调研邮件，不需要TP目标价。**

邮件内容不出现“高于TP”“低于TP”“等于TP”“目标价是否达标”等文字。

应展示：
- MPN及品牌（有可信数据时）
- 客户、原询价日期、询价数量（匹配到订单时）
- 库存情况
- 六来源的报价及原币种
- 折算人民币单价
- 现价或报价日期
- 各来源最低、次低有效报价
- 全局参考最低、次低报价
- 数量已知时的预计订单总价
- 来源缺失、价格无效、资料不完整等准确说明

不能伪造任何报价、数量、品牌或日期。无报价应明确显示“未取得有效报价”。

不要因此改变原采购下单或客户报价的选择、价格基线及写入逻辑。

## 第三部分：升级两个现有业务邮件

**1. 重要询价通知**

保持原有A/B/C/SHAHAB等级、金额、库存判断条件，收件人仍为Owner229和Shawn。

当符合发送条件时，附带第二部分的完整六来源详细调研报告，不再仅显示几项粗略市场参考数据。

使用已获取的有效详细调研结果；需要补采时，不得同步阻塞关键采购写入路径，不得抢占生产浏览器的受保护页面。

必须在最终发送前重新审核客户订单当前状态和有效性。历史已完成订单不补发。

**4. 采购报价待跟进**

保持原有“发采购后超过3个工作小时、原表仍为发给采购”的业务条件，收件人仍为Owner229和Shawn。

邮件升级为完整的六来源详细市场调研报告，并显示客户、型号、数量、原发采购时间及需跟进的原因。

原状态已经变更、客户已报价或跟进条件不再成立时禁止发送旧提醒。

两个邮件共用同一套报告组件，不复制TP HTML模板、采价算法、汇率计算或网站适配器。

## 第四部分：全新独立IMAP邮件调研服务

**这是一个与现有询价、报价、TP主业务独立的后台模块。**

只要INSO_Leo主程序进程运行，独立服务就应持续工作，**不受主业务开始、暂停、停止、手工重跑按钮影响**。

主程序退出时，该服务正常安全退出。主业务模块的故障、暂停或等待人工处理不能直接停止它。

### 4.1 邮件监听

- 读取229邮箱的IMAP收件箱。
- 每120秒检查一次新邮件。
- 使用`imap.qq.com:993`，TLS安全连接。
- 使用已有Core Credential Provider / Windows Vault管理授权，不在源码、日志或配置文件写入邮箱密码。
- 检查现有229邮箱是否已经具备IMAP授权。没有则仅报告需要Owner配置，不自行猜授权码。
- 严格匹配真实发件人地址`sal​​es2@inso-hk.com`（代码使用不含任何隐形字符的标准地址`sal`+`es2@inso-hk.com`）。
- 邮件主题必须以“调研”开头，后面是一个完整MPN，例如：`调研 STM32F103C8T6`。
- 允许“调研”与MPN之间有或没有空格。
- 解码RFC邮件主题，不把邮件正文当执行指令，不执行附件或链接。
- 无效标题、不可信发件人或空MPN不执行调研。
- 邮件唯一键使用邮箱身份、UIDVALIDITY、UID，辅以Message-ID记录；不因为重启或同一邮件仍处于未读状态就重复处理。
- 初始化时先建立收件基线，不能把一个月前的旧“调研”邮件全部重新执行。
- 同型号的两封不同新邮件是两次独立请求，不应按MPN全局去重。
- IMAP检查本身有独立周期，即使上一笔调研还没完成，也不能停止收件检查；新请求进入有界队列等待。

### 4.2 自动匹配最近询价

收到新调研请求后，仅提取完整MPN。

先使用现有可信的Google/本地询价记录来源，查找**该完整MPN最近的一笔真实询价**。

匹配要求：

1. 按已有完整MPN标准化及严格匹配规则，不用宽泛子串或相似型号猜测。
2. 优先可信原询价日期，必要时使用已经验证的本地订单日期，按真实日期从近到远。
3. 同一最新时间出现多个不同订单、身份不唯一、来源记录冲突时，视为无法可靠匹配，不随意选一笔。
4. 找到唯一可信的最近订单，提取客户、品牌、数量、询价日期等，作为调研报告补充信息。
5. 使用匹配到的真实订单数量计算参考总价，且总价必须明确标记为市场参考估算，而非客户正式报价。
6. 匹配不到订单时，**依然正常调研**。只查完整MPN和市场单价，不要求用户提供数量、品牌、TP或其他字段。
7. 现有网站适配器若必须输入正整数数量，可以在内部使用1作为技术查询参数，但报告不得把这个1伪装成客户询价数量，也不能计算虚假的客户订单总价。
8. 未匹配时品牌缺失须优雅降级；某个来源无法在缺品牌时查询，就诚实标记该来源资料不足，其他来源正常进行。
9. 邮件显式请求的调研不受主业务7天/1个月自动轮询年龄限制，但不能因此触发旧订单询价、采购、报价或TP写入。

**匹配过程必须只读，绝不能更改Google订单状态或本地已有业务历史。**

### 4.3 详细调研与发送

使用第二部分的公共详细调研组件完成六来源查询。

- 发信对象：**仅Shawn，`shawn@inso-hk.com`**。
- 不自动回复原发件人。
- 报告体现“邮件指令调研”，并显示请求MPN、来源邮件时间和匹配情况。
- 匹配到询价则附客户、数量、品牌、参考订单总价；未匹配则只显示MPN报价信息。
- 无TP目标价判断。
- 邮件成功发送后以持久化记录阻止重复发送。
- SMTP发送结果UNKNOWN时不得重新盲发。
- 单站失败不妨碍其他来源收集，最终按已确认数据生成准确报告。
- 全部采集无法取得可信结果时，不要把空报告伪装成成功；在独立任务日志中记录失败并按规定进行安全处理。

### 4.4 浏览器与CDP：本次强制要求

**使用同一个现有Chrome和同一个CDP端口9222。**

禁止再启动第二个Chrome进程、创建第二套Chrome Profile或占用第二个CDP端口。

但新增邮件调研服务必须有**完全独立的标签页所有权和生命周期**：

- 主业务的标签页归主业务所有。
- 新服务只创建、管理、关闭自己拥有的标签页。
- 禁止执行关闭所有页面、清理整个context、重建整个CDP、关闭主业务Chrome等全局清理动作。
- 不得误关Owner手工页面、Google页面、INSO受保护页面或主业务Research页面。
- 共享原CDP并不代表可以跨线程直接复用原Playwright对象；必须遵守线程所有权和既有PageResourceAdmission/lease安全约束。
- 可以使用安全的、独立生命周期的CDP连接客户端指向同一端口，但必须先验证不会干扰现有浏览器Owner及页面清理机制；优先复用既有安全的浏览器资源管理接口，而不是新建不受管控的Playwright控制体系。
- 独立浏览器任务串行或严格有界并发，不抢夺主业务受保护资源；主业务始终优先。
- 对新服务的页面添加明确的所属模块/任务身份，严格检查标签页归属，不仅凭URL或标签标题判断。

**标签页误关闭的恢复要求：**

1. 在页面操作前后检查独立标签页是否仍然存在。
2. 如果被Owner误关或网站自行关闭，只影响本邮件调研任务。
3. 在确认只是只读价格采集、没有不确定外部提交效果后，使用同一CDP创建新的专属标签页。
4. 恢复对应网站的安全读取上下文，从最后可靠的采集步骤继续。
5. 限制恢复次数并记录原因；不能无限循环开标签页。
6. 原页面关闭时，不能去接管与其URL相同的Owner手工页面。
7. 即使单个标签页恢复失败，也不能停止主业务、重置全局Chrome或误发一封Google运行异常邮件。
8. 恢复过程禁止重复发送调研报告；邮件必须由独立的持久化发信状态控制。
9. 如果整个Chrome/CDP不可用，不得以影响主业务的方式重启浏览器；新服务局部退避恢复并留下状态，只有确认持续无法处理且需要人工干预时才按原严格告警规则通知229。

新模块发生严重故障时，**仅向Owner229发送经严格复核、同一事故最多一封的异常邮件**；不向Shawn发送技术告警。

## 第五部分：独立生命周期

新服务应有自己的：
- 120秒IMAP检查时钟
- 持久化请求与发送幂等状态
- 有界待处理队列
- 单任务研究状态及失败重试
- 浏览器标签页租约与清理
- 日志与健康状态
- 正常程序退出时的安全回收

尽量复用原SQLite持久化和通知基础设施，但独立任务身份、数据库事务和发送保护必须清晰，绝不能把邮件指令伪装成原Google询价订单。

主业务的Start、Stop、Pause、手工报价、手工TP不会影响该服务的运行开关或任务进度。即使不增加UI模块，也必须能从本地日志可靠查看收件、调研、发信、失败情况。

两个模块共享同一Chrome，所以要通过页面所有权、优先级和资源预算隔离，不能声称物理资源绝对独立。

不能因为共享CDP就重新引入V1.6之前的标签页累积、跨模块关页和重启冲突问题。

## 第六部分：测试与验收

必须采用完全离线假IMAP、假Google、假CDP/页面、假市场来源及假SMTP进行测试。

重点验证：

- RFQ-016三个CEO缺陷均修复，原7天/自然月及人工单笔年龄豁免保持。
- A/B/C/SHAHAB重要询价触发条件没有变化。
- 采购待跟进3个工作小时规则没有变化。
- 两种现有业务邮件生成完整的六来源报价内容，缺失数据不造假。
- 原TP调研算法只存在一套权威实现，新增邮件没有复制第二套价格算法。
- “调研 MPN”邮件正确识别，其他发件人、格式错误的主题不触发。
- 最近唯一同型号订单匹配；同名多单取最近；同日相同时间无法唯一定位时不乱匹配。
- 无匹配订单时仍可查询并发送参考单价报告。
- IMAP断线、UID变化、程序重启、收到同一邮件重复扫描，不重复发报告。
- 主业务处于暂停/停止/手工操作中，IMAP仍每120秒检查。
- 新标签页被关闭后，能够安全创建新专属页并继续只读研究。
- 新模块关闭自己的标签页，不影响主业务或Owner的任何页面。
- 整个CDP暂时断开不会导致新服务重启主Chrome或停止主业务。
- 真正需要人工处理的严重故障，仅向229通知一次；暂时性错误误报邮件数量为0。
- 并行运行一段足够长的模拟时钟周期后，没有线程泄漏、无限队列增长、标签页累积及跨任务状态污染。
- 保护所有现有生产数据库、SMTP SENT/UNKNOWN、报价UNKNOWN与回滚状态。

先跑有针对性的失败复现与修复测试，然后进行完整回归。

## 第七部分：执行与交付要求

1. 先核对真实Git分支、遗留提交和现有生产版本，避免误伤上一位Executor的成果。
2. 仅修改源码和离线测试，不干扰当前生产运行。
3. 以RFQ-016三个安全缺陷为优先，随后实现公共详细调研，再实现邮件模板升级和独立IMAP模块。
4. 每一阶段做有明确证据的测试，避免一次性大规模重构。
5. 不使用Computer Use。程序原有业务Playwright/CDP功能允许，但Codex Agent不得操控生产桌面。
6. 不发送真实测试邮件，不导入历史旧订单，不清除UNKNOWN。
7. 不重启、不强杀、不覆盖运行中的EXE，不抢生产浏览器。
8. 完成后提交源码、测试、审计说明和完整Git SHA。
9. 更新原RFQ-016报告，并给新邮件调研功能建立独立子任务记录，避免把未完成部分伪装成RFQ-016已全部验收。
10. 交CEO进行源码复审，随后由Owner单独授权正式安装。

**最终目标：旧订单不再乱处理、任务中心状态真实、误报邮件不再骚扰Owner；重要询价和采购待跟进邮件具备TP级详细信息；独立IMAP调研服务每2分钟持续检查并能够安全恢复误关闭的专属标签页，且不影响原正常主业务。**

`COMPUTER_USE_NOT_USED`

## CEO independent audit of detailed-mail extension (2026-10-31)

**`CHANGES_REQUESTED / SOURCE_NOT_APPROVED / NOT_DEPLOYED`.** Final source `08a00cf6abacc73a4c06b7721f4dfff51fd5e373` and document/report `e2965645360ecbbab59fc30780c3de34f8986f37`. All previously identified A/B/C correctness fixes are provisionally accepted as source paths; no production effect is established. Exact review findings and regression gates are in **`control-room/RFQ-016/TASK_SPEC.md`**, section *CEO independent SOURCE Re-Review — RFQ016 + detailed mail/IMAP extension*.

**D / P0:** `InquiryCatalog.match` can call an old local SQLite/cache MPN record “最近询价” while the independent IMAP service operates with main Google polling stopped. Without proven fresh/complete source, never attach that possibly obsolete customer's quantity/name/estimated total; still allow MPN-only research and send an honest unmatched report. Demonstrate main-paused and stale-after-restart cases.

**E / P1:** the shared `ResearchBudget` `RLock` gives foreground priority only if main wins the race; when background already holds the lock, due foreground jobs wait for that entire read. Prove bounded/no-harm foreground progress with background-first/hung-source tests while retaining same CDP and exact page ownership. Do not solve by opening extra uncontrolled Chrome, closing human pages or changing due clocks.

**Sender check / P1:** syntactic `From` equality alone cannot certify that email truly came from `sales2@inso-hk.com`. Require actual provider-verifiable sender authenticity or an explicitly authorized narrowly documented risk boundary. Existing malformed-From tests do not test forged exact From.

Only source patch, fake adapters, targeted red→green/full regression, refreshed original reports and new SHA are authorized. No release/build swap or live mailbox/network test. Do not collapse new IMAP code into original business Owner; protect source tests/production and enforce `COMPUTER_USE_NOT_USED`.


## Sender authenticity decision — second-review source remediation

Status: **QQ_PROVIDER_CONTRACT_NOT_VERIFIED / SECURITY_ENABLEMENT_BLOCKED**. No live mailbox inspection, real test mail or risk acceptance was authorized. Public documentation lookup is not a mailbox test. From equality remains only a syntactic candidate check; it does not prove control of sales2@inso-hk.com. The current production verifier returns false and has no config enable switch. Matching candidates keep the original UID cursor, record local SENDER_AUTH_UNVERIFIED and are not researched or emailed. Subsequent120s scans continue; no guessed credential/Google-failure alert is generated. Earlier queued requests lack proof and are blocked/suppressed; SENT/UNKNOWN are retained. Other legitimate business/TP mail paths are unchanged.

Actual available evidence: the existing QQ IMAP client can retrieve requested RFC headers via BODY.PEEK, over authenticated TLS for229's mailbox. TLS proves the receiving endpoint/account connection, not the original sender. No QQ-specific, authenticated per-message sender assertion has been established. QQ's public help catalog lists “发件人地址已验证”, but the available public page does not specify a machine-readable IMAP field, trusted authserv-id, injected-header stripping policy or an exact-mailbox identity binding. Tencent Cloud SES DKIM documentation describes a different outbound product and is not proof of QQ inbound semantics. We did not assume equivalent behavior.

Minimum proposed route before live enablement: (1) obtain provider-confirmed semantics for receiver-origin authentication metadata, including removal/renaming of forged inbound copies and exact trusted receiving boundary; (2) validate domain-aligned DKIM/DMARC using those trusted results, and establish the sending provider's binding between the authenticated submitting account and the exact sales2 address (domain authentication alone is not proof of a specific mailbox/person); (3) add a narrow verifier at the existing receiver boundary, covering no-result, failure, duplicate/forged authentication/Received headers, forwarding and spoofed exact From with offline provider fixtures; (4) CEO independently reviews the contract and any explicit residual domain/account delegation risk before enabling real commands. If that contract cannot be obtained, retain the block; only Owner may explicitly accept a precisely documented weaker sender rule. No such acceptance is presumed in this patch.

Do not implement SPF by looking only at Return-Path, trust an arbitrary Received chain/authserv-id, or accept an Authentication-Results header saying pass. Local DKIM verification would additionally need the complete signed message/body hash and trusted key retrieval; the current header-only restriction does not authorize that change. No body/attachment/link is fetched or executed.

Primary sources consulted2026-10-31:
- QQ official help catalog, including the “发件人地址已验证” entry: https://service.mail.qq.com/detail/0/75 — no validated IMAP authenticity contract obtained.
- IMAP protocol, RFC9051: https://www.rfc-editor.org/rfc/rfc9051.html — FETCH/ENVELOPE are message data, not an authenticated originating sender assertion.
- Authentication-Results, RFC8601 sections1.2/7.1: https://www.rfc-editor.org/rfc/rfc8601.html — trust boundary and forged header treatment are essential; the header itself supplies no authentication service.
- Tencent Cloud outbound SES authentication FAQ: https://cloud.tencent.com.cn/document/faq/1288/60652 — outbound domain auth only; not imported as QQ receiving semantics.

Synthetic verified test fixtures use an explicitly injected boundary verifier/ResearchMail proof. These are offline test capabilities, **not a delivered live QQ verifier**. No custom SMTP, credentials, dependencies or headers-as-commands were added.

## CEO final D/E/sender review: one optional-service isolation blocker (2026-10-31)

Source `1dd31b283ec34126637e173830dbc3c321b7c89d`, delivery `0f33b97ed2abfde9ca7fbc94b47e4ca36030f5c4`. The previous D and E fixes are source-level provisionally accepted, with synthetic tests; authentic QQ sender proof remains **NOT IMPLEMENTED / SECURITY_ENABLEMENT_BLOCKED** by design, so real new IMAP commands cannot research or send.

**`CHANGES_REQUESTED` for original business-mail degradation:** if new optional service startup fails (`backend._mail_research_service=None`) or its owned page is persistently blocked, `prepare_business_report` returns `None` forever, causing original verified IMPORTANT_ORDER and PURCHASE_FOLLOW_UP_REQUIRED alerts to be indefinitely deferred in existing V12 mail worker. This violates the Owner's requirement that the new independent module cannot stop normal business functionality. Add a bounded, truthful no-invented-market-data fallback for current, already-authorized original business emails, retaining send-time source/status/cooldown/recipient/UNKNOWN protections. Do not treat failed enrichment as false business success; preserve full-six-source content when available.

Exact test matrix and source paths in original `control-room/RFQ-016/TASK_SPEC.md`, CEO SOURCE Re-Review #3. No production deployment or automatic mail enablement authorized; source patch and fake-SMTP regression only.


## F-only third-review remediation — bounded original business notice content

Original important/follow-up notices retain their native trigger, recipients and
actual-send review. Detailed report acquisition is optional, with120s elapsed
from the existing durable notice creation time (not a new timer, startup time,
last attempt or job creation). Retry/restart cannot extend it. Fresh complete
six-source content wins whenever available; otherwise the first eligible send
after the deadline uses current verified order identity/metadata and business
purpose, plus “详细市场报价暂不可用／未核实”. It never copies historical market
price, inventory or estimated totals, nor claims research succeeded/market empty.
Confirmed original follow-up time is retained. No automatic later supplementary
mail is generated. SENT/UNKNOWN remain terminal for the original recipient.

Only launcher/mail_research_composition.py changes in production source; no
A/B/C/D/E, main scheduler, manual/TP actions, native page lifecycle, sender
verification, V12 queue or SMTP changes. A failed optional startup/cache/queue,
persisted local resource protection, unavailable background admission, stale or
malformed result cannot starve these still-valid notices. Core source/event/age
or recipient validation remains mandatory and can still prevent a mail. Actual
SMTP/provider/browser behavior remains NOT_VERIFIED and no release is authorized.
Final source `55ba0f230ce4a42eeda78d4aa942e9065bfc4ba3`; src tree `555f1ddf94cd9cb3cbec3643976ba25ff9f4444c`, tests tree `49c68dafc92ec8586a118edd46fccca009347bf6`.39targetedPASS11.79s; full3393PASS/1SKIP211.28s. Source/test receipt and cleanup are in original RFQ evidence; no production claim.

## CEO fourth independent source review — F closed / QQ live command still held (2026-10-31)

**SOURCE_ACCEPTED_FOR_CONTROLLED_RELEASE_DECISION / PRODUCTION_NOT_DEPLOYED** for reviewed application `55ba0f230ce4a42eeda78d4aa942e9065bfc4ba3` (source tree `555f1ddf94cd9cb3cbec3643976ba25ff9f4444c`, tests tree `49c68dafc92ec8586a118edd46fccca009347bf6`). Original important inquiry and three-working-hour procurement follow-up mail can no longer be indefinitely held solely because the optional independent research service fails: verified notices use full six-source data when ready; otherwise they fall back after120s from the original durable notice creation on the next eligible dispatch, with no invented price/stock/total and original source/event/recipient/SENT/UNKNOWN review intact. Reviewed actual production patch and real-preparer+V12-worker+fake-QQSMTP integration tests; Executor reports39 targeted PASS and3393 full PASS/1 environment SKIP. Original A/B/C/D/E paths unchanged.

**NOT IMPLEMENTED / SECURITY_ENABLEMENT_BLOCKED:** real QQ IMAP sender authenticity. `verify_sender_origin` still returns false; no live `调研 MPN` command may research or mail Shawn. This cannot be represented as implemented-and-verified. Only a separately reviewed authenticated provider binding (or a narrow explicitly Owner-accepted sender-spoofing residual risk) can enable real commands.

**NOT DEPLOYED / NOT VERIFIED:** actual live mailbox, source freshness, Chrome resources, SMTP provider delivery, production EXE and user-observed false alert recovery. This review does not authorize a build/install, testing through live SMTP, or switching off native UNKNOWN protection. Exact independent CEO review details in `control-room/RFQ-016/TASK_SPEC.md`, Re-Review #4.


## Owner final subject-only controlled deployment — 2026-10-31
Explicit final Owner instruction supersedes prior sender-authentication hold and separate CEO release gate for this change only. Any sender may trigger a new legal decoded subject `调研 MPN`; no sender identity verification is claimed or required. Body/attachment/link instructions remain prohibited. Original UIDVALIDITY/UID/task/outbox protections remain mandatory; first enablement establishes an atomic current UID baseline rather than draining old blocked messages. Six-source detailed research, current-source freshness, browser ownership/main priority and original120s truthful business-notice fallback are preserved. Only new IMAP entry policy and its persistence/review gates changed. Controlled build/backup/install/start is authorized without another routine source review. Original historical review records below remain historical, not current blockers.
Source4b61f521c0f1f0836be71e3cfc792c66e5e4610d:46 targeted PASS;3414 full PASS/1 environment SKIP. Installed formal V1.6 after verified program/data backup; full receipt in TEST_REPORT.json and release report. Actual IMAP login/baseline verified; live new-mail research/provider delivery remains pending natural trigger. COMPUTER_USE_NOT_USED.


## Owner2026-11-01 correction: on-demand verified order association and controlled redeployment
Trigger: real mail report omitted an existing order because catalog requires post-request live observations but independent worker did not acquire them. Owner explicitly requests complete bug repair and overwrite/run. Scope: reuse canonical Sheets native reader, same Chrome/profile9222 and exact owned pages; acquire all configured worksheets plus existing date/brief evidence on demand in independent worker, including stopped main; retain fresh-source/current-order/ambiguity gates and original A–F, sender-subject UID baseline, main-priority, SENT/UNKNOWN protections. No source business writes, synthetic real messages or automatic resend of already SENT report. Diagnose read-only, add offline red/green/thread/ownership/regression cases, run full offline suite, commit/build/verified backup/safe application stop/install/start/observe using original release procedure. If running app cannot safely exit through existing supported interface without forbidden Computer Use/force kill, prepare tested package and require only Owner normal exit. No extra routine CEO approval. Never infer current Google order solely from historical SQLite. COMPUTER_USE_NOT_USED required. Executor owns implementation/evidence/owned disposable cleanup; no new long-term daemon/framework or browser instance.

2026-11-01 correction receipt:source5bb8c941d8f772ea6cfb209b077a91c678b400ea,172 targeted PASS/3428full PASS+1environment SKIP;14new regressions, original behaviors retained. Canonical V1.6 package/scan/self-check PASS; only original tray normal exit remains required before authorized backup/install/start. BLOCKED_NORMAL_EXIT, no live fix claim and no old SENT report resend. Exact SHA/paths/evidence and required next step in RFQ016 current TEST_REPORT/FINAL_REPORT.

2026-11-01 deployment completion supersedes prior normal-exit blocker: Owner original trayExit normal0 verified; correction source5bb8c941 installed after consistent verified program/runtime/SQLite backup, full manifest/self-check/prestart table+config identity. NewGUI163608 starts original normal business and independent process service. No old SENT/UNKNOWN replay. Existing records and Chrome untouched; candidate/temporary helpers retired. Real new-request order association/SMTP receipt pending natural trigger; see current RFQ016 receipt. No further Owner approval/action.


## Owner2026-11-01 second correction: raw/source brand binding + visible retained quotations
Owner requests another complete fix/test/package/backup/overwrite/run after a real later report still lacked order association and questioned single-price rendering. Scope: fix catalog immutable-intake binding by reusing existing public expected_source_brand contract, never treating a research-derived brand as a confirmed Google write. Preserve current full source/post-receipt freshness, exact row/model/quantity and ambiguous-date protection; display local intake dates explicitly approximate. For target-free detailed mail, display all currently validated retained source quote records with date/stock, single-quote explanation and vertically readable layout; do not invent quotes, claim exhaustive website coverage, or change ordinary TP selection/comparison. No automatic resend of existing SENT/UNKNOWN reports. Original controlled release authorization continues; no production/CDP test probes, no Computer Use/force kill. Only original normal tray exit may require Owner operation. Extend production-shaped red/green/native source-to-original fake SMTP regressions, run complete offline suite, original canonical release/verified backup/only-program install/start/natural verification and owned cleanup. Preserve all RFQ016 accepted business/age/UNKNOWN/UID/mail/browser safeguards.

Second correction release completion2026-11-01:immutable source325cd19052a17c05c1d2b59a4528a2a38183b8bb,148targetedPASS8.95s,3450fullPASS/1symlinkSKIP316.43s;22new cases. Test-only main-thread GC fixes full-collection Font destructor waiting without changing deadlines/semantic assertions. Owner normal original tray exit confirmednormal0; consistent verified backup/2875asset manifest/old+new self-checks/prestart original table+config identity PASS. Program-only installed, all three natural cycles completed, BUSINESS_RUNNING. Raw source brand/blank optional date/approximate multi-order ambiguity and truthful retained-quote stock display corrected; priorSENT/UNKNOWN/UID/age/main-priority protections retained.35owned temporary assets retired. Real new mail end-to-end remains pending natural trigger, no old report resend or test external effects. Evidence in original RFQ016 files.


## Owner2026-11-02生产资产与架构专项体检（已完成，仅审计）

按Owner新指令由原V1.6窗口独立执行；基线23aaf84。只读Windows元数据和静态源码，未改业务/部署/生产状态。Profile仍落旧Research载体、业务DB仍落v1-2工作树；明确保护、回滚容量/独立性及三个小步优化建议。完整证据及NOT_VERIFIED见 [专项审计](../control-room/RFQ-016/ASSET_ARCHITECTURE_AUDIT_2026-11-02.md)。本次排除GitHub公开性和IMAP专项；COMPUTER_USE_NOT_USED。


## Owner2026-11-03生产暂停且无通知修复（IN_PROGRESS）

Owner要求定位并修复。只读原运行日志确认10:47:45报价失败、10:47:46 GOOGLE_TAB_IDENTITY_UNCONFIRMED，GUI进程仍在；上次11-02退出有owner_exit/normal0记录，不冒称崩溃。范围：复用原Google retained目标身份保护，修复无关页面身份探测导致误停的路径；补齐经验证的真实主业务安全暂停通知及原邮件worker收口发送，保留UNKNOWN/最终审核/持久去重与旧单保护。先离线复现再修复、专项及全量测试；不接生产CDP、不读凭据、不测试外发、不清保护、不强杀或关闭Chrome。继续复用原发布流程，安全退出若需Owner原托盘操作，仅在通过验证的具体包就绪后提出。

Owner追加明确要求：Google手工可用时不得将程序读取/页识别瞬态问题升级全业务停止。扩大本次最小修复至只读native证明失败的有界重试，以及超过三小时仍按原模块周期自动恢复、其余模块继续；写入UNKNOWN、身份确实冲突、权限及人工页面保护不放松。此前3465PASS/1SKIP是第一阶段结果，扩大后必须重新专项及全量验证。

修复交付：源码6b85130df1cb579ac184a0ca6ef989f9d53e495f，专项369PASS/完整3474PASS+1环境SKIP；原流程构建、自检、扫描、2875清单和5修改冻结模块匹配PASS。候选EXE9c0ba24bcd53f7b97d19e4f530b7bc65680b01ccca94d519d17f967690c64b34。BLOCKED_NORMAL_EXIT：已向Owner提出唯一原托盘正常退出操作；正式旧55be53be仍在，尚未备份覆盖/启动修复版，不宣称生产解决。原Chrome/DB/UNKNOWN未改，COMPUTER_USE_NOT_USED。


## Owner2026-11-04：新单日期漏读严重缺陷及关联逻辑排查（IN_PROGRESS）
Owner要求彻底修复、排查关联逻辑、打包运行并跟踪指定真实新订单。只读现场已验证：2026源表新单status未发且W列quote_date为当日，但原读取/映射只保留A:G，RFQ_BRIEF无该单日期，未入队前本地created_at也不存在，准入静默排除。Owner已授权本次业务空闲只读CDP例外，未读Cookie/令牌、未改Google或采购；原API调用不可用，后续凭据材料探查被自动审批拒绝并已停止。源码/evidence只用合成单，不提交实际型号、客户或表格内容。
最小修复：复用同一下载的、表头明确且与源行型号/品牌/数量一致的日期元数据；保留原A:G业务输入与单一缓存，不新建调度/SMTP/数据库。新记录以原表日期通过年龄门槛后才正常入队，日期依据随原身份JSON持久保存，不重设历史created_at、不拿今天冒充旧日期。排查缓存/重启/日期改动/输入修正/手工重跑/报价邮件最终审核是否会丢失或延后年龄依据。缺失、冲突、未来、超期、身份改变仍拒绝；UNKNOWN/SENT及原月限制保留。完整离线回归后原受控发布，真实新单仅走正式原调度，不另开采购客户端或补发旧订单。


### 2026-11-05 same authorized run: INSO page-identity failure discovered
Date fixd5117ec is installed and the real new order entered original queue, duplicate check confirmed. First original research deferred after631.484s withINSO_WAITING_RECOVERY; no purchase or unknown external write. Quotation76.875s/TP10.047s completed, prior175terminal recipients unchanged, one transient incident suppressedEVENT_NOT_CURRENT. Owner explicitly authorized a further idle-only read-only diagnosis of this order in existingChrome9222. Original hand-built Stock_VenQuote HTTP returns409/PAGE_IDENTITY_REQUIRED; no rows and no isLogin proof. Diagnostic did not read credentials/Cookies/tokens, navigate/close pages or execute writes; all18originalpages retained, driver disconnected. Generic diagnostic AttributeError from unsupported response metadata method corrected, not a production result.
Scope extension under original Owner request to fix related logic: reuse existing audited PlaywrightProcurementHistoryPage native Stock_VenQuote query (already used by normal quotation) through the same leased shell_frame in research. Do not forge/extract page tokens or disable server checks; remove direct request.post from market source, no fallback/bypass. Preserve raw row parser/MPN/currency/date/market rules, original credential/session/ownership, bounded retries, SMTP/UNKNOWN protection and native pager settlement validation. Reproduce409 offline before change, extend source/session/empty/native-failure and service-path tests; run full offline gate and original build/backup/program-only deployment. Agent must NOT call native locator UI as a diagnostic workaround: only the authorized application's normal runtime executes existing native query. No manual purchase/replay. If current app has no safe exit interface, only Owner tray normalExit is required after concrete verified repair package.

Related restart defect reproduced1FAIL/3PASS: current released read retry would becomeINTERRUPTED_UNSENT on restart. Minimum exception only forRESEARCH_RETRY_WAIT+QUEUED+attempt0+new verified durable original date+recent immutable intake+no purchase state+noSAVE_DISPATCH_ARMED/SAVE_CLICK_COMPLETED. Original polling still freshly checks identity/status/age/UNKNOWN before research or write; absent/old source date and armed/unknown remain quarantined. No live record modification or manual hold clearing. Existing historic rows have no new date and retain prior behavior.

Completion2026-11-05: finalsource97f0ac6959e4efb3bd30bac48fa6e812b001c238 deployed under Owner normalexit.165target/3515fullPASS+1originalOSskip;2875programfiles/13frozenmodules and old/new/idle selfchecksPASS;16protectedtables/config unchanged before normalstart. Newrun inquiry333.578s/quotation58.219s/TP8.687s completed; same realorder source date preserved and safe retry resumed without quarantine. Allsixsources noquote producedEXCEPTION/NO_MATCHING_PRODUCT; originalno-price rule correctly leavesRESEARCH_FAILED with no purchase/Googlewrite, no savedispatch/click/saveevents. Do not call this purchase success or evidence of mistypedMPN.175oldterminalrecipients and1protectedunknown unchanged; no newruntime recoveryfault/falseexternalmail. FinalstatusBUSINESS_RUNNING, source repair and requested naturalrun observed; future actualpurchase/quote outcomes and long-term health remain NOT_VERIFIED. No furtherautomaticreplay/manualholdclear. Originalreport contains release/rollback/evidence; COMPUTER_USE_NOT_USED.


## Owner2026-11-05: restore confirmed no-quote business notice (IN_PROGRESS)
Owner explicitly commands continuation after pointing out no mail for the current legitimate no-quote order. OriginalPurchaseCompletionActions.notify still has owner229+Shawn no-quote recipients-v2 path, but broad unknown-write-only guard makes it unreachable; backend evidence/review also lacks this confirmed business reason. Prior explanation attributing this solely to C-tier was incomplete.
Reuse originalPURCHASE_EXCEPTION durable outbox, originalno-quote recipient pair/command identity, SMTP adapter, completion hook and existing periodic completion reconciliation. Restore a typed confirmed-business NO_MATCHING_PRODUCT notice only for durableFAILED/EXCEPTION/no-quote+RESEARCH_FAILED, recent boundsource and failureevent, currentGoogle未发, no purchase/dispatch/unknown, exactidentity and originalrecipients. Subject/body says no validmarketquote/未发采购/needsbusinessfollow-up, not website outage, wrong customerMPN or success. Stable per-order legacycommand protectsSENT/UNKNOWN and priorlegacydeliveries; no new table/scheduler/browser/mail pipeline. Sending must recheck event stillvalid, currentstate/date/sourcebinding/recipients and no newer recovery/write. Existing reconciliation may notify this still-current unfinished realorder without rerunning research/procurement or patchingDB; old/expired/recovered/purchased/UNKNOWN must never externalize. Keep important/TP/follow-up and strict technicalfault policy.
Add actualBackend evidence + originalcompletion/queue + fakeSMTP red/green, alltiers, current-order reconciliation, stale/old/closed/changedidentity/researchincomplete/technicalfailure/unknownpurchase, post-enqueue recovery, per-recipientSENTUNKNOWN/restart/legacy idempotency tests. Full offline regression then original commit/build/backup/program-only deployment, normalOwnerexit if no safe remoteexit, observe legitimate no-quote businessmail only (no real testmail). No new productionCDP diagnosis, noComputerUse. Original release authorization continues; no repeated source approval.


### Owner2026-11-05 extension: audit every mail gate, restore legitimate notices
Owner requires complete inspection of false-positive protections, not merely one no-price case. Scope includes every original NotificationCommand producer, queue/retry/restart and final SMTP gate. Confirmed additional losses: durable unsubmitted purchase validation, verified shared-session manual challenge before order binding, IC.net explicit human challenge hidden in generic defer, and actual typed manual sales-header stop. Reuse existing original per-module outboxes/SMTP and nullable V13 migration; no schema/new service/scheduler/browser change. Restore only evidence-backed, currently actionable categories; transient/unverified/stale/recovered/old/wrong-recipient/SENT/UNKNOWN protections stay. Model-difference notice must not infer final write outcome. Include positive/negative producer inventory regression, actual Backend/completion/manual producer plus original queue and fake SMTP, per-recipient retry/restart/legacy protection. Owner authorizes existing controlled release after offline gates; normal tray Exit remains the only manual-only prerequisite if the app is running. No agent Computer Use, production CDP diagnostic or synthetic real mail/order. Existing no-price order may receive its still-valid original business notice through normal completion reconciliation, without research/procurement replay or DB edits.

Owner later explicitly authorizes only this stalled formalGUI forceexit (“现在我也关不掉，你强杀吧”); supersedes normal-exit-only blocker for this one instance, not blanket forcekill/Chrome authority. Originalconsistent pre-forcebackup, exactPIDidentity, noChrome action, originalmutex/fullcoldbackup/programonlyinstall/16tableconfigidentity and newoldidleselfchecks verified. Source2bb0c0b installed andoriginalnormalbusiness started; natural current-source/no-quote SMTP result remains observationpending. Exact previous read hang rootcause is NOT_VERIFIED, not claimed fixed by this mail patch.

Finalscope2026-11-05: mailrepairsource2bb0c0b installed afterprotectedbackup/selfchecks, but newfirstread remainspending beyond26min, so **HEALTH_HOLD**, notbusinessacceptance. Ownerallowedone readonlyCDPmetadata diagnosis; all9targets preserved, Chrome/Googlepages respondimmediately, noCookie/token/UI/businesswrites. Exact apppendingcommandNOT_VERIFIED. Currentnoquote commandnotcreated, no bypasssourcefreshness or replay. Existing175mail/1unknown/50dates intact. RemainingP0 native/read transportdeadline+safeexitdrain requires continued scoped diagnosis and offline reproduction, preserving allownership/UNKNOWN rules. No speculativeglobalstop relaxation or blanketmailenablement.


## Owner2026-11-05 new-order processing restoration and accountability report (IN_PROGRESS)
Owner explicitly requires both2026/SHAHAB new valid orders reliably read/admitted/processed, thorough related logic audit, repair/full offline regression/original controlled build-backup-program-only deployment-natural observation, then a Chinese accountability report over3000characters. Do not promise zerofuturefaults or substitute package/gui_ready for businesscompletion. Currentformal2bb0c0b unchanged; Owner restarted21:59PID9852/originalobserver6660, inquirydeferred18.047s withgoogle-navigation-error-page/GOOGLE_SPREADSHEET_UNAVAILABLE; quotation116.047s/TP13.406s completed,0newitems sincepriorinstall. Preserve originals50items/175terminalmail/1unknown, no manualDB/source edits or forcedorderretry. Prior one-off force/CDP exceptions notblanketauthority; request necessary newdiagnostic exception only if needed. COMPUTER_USE_NOT_USED.
Confirmed source design flaw: optional dashboard counts read all worksheets before normal business; a single failed read aborts inquiry before anyworksheet processed. CombinedCycle inquiry loop also aborts remainingworksheets on typed temporary read failures. Reproduce these productionBackend/Combined boundaries offline first; isolate ONLY safe read failures and allowhealthyworksheet path, keep unavailablecountUNKNOWN and moduledeferredaccurate, never swallow DB/auth/ownership/schema/unknown-write faults. Investigate actualChromeerrorpage navigation/retry/nativeowner/protocol deadlines and source freshness/date/header/status gates using originalservices; no browser/scheduler/DB/mail rewrite. Add bothsheets,new/old/manual/duplicate/UNKNOWN/recovery/partial-read tests plus real-thread timing where relevant. Record exact observed/unknown causes rather than treating Google overall unavailable. Final3000+Chinesechar report must own missedbasics, falsecompletionclaims/testgaps, factual changes/evidence, remainingunknown and concrete prevention; exclude customer/secret/rawproductiondata.


Owner subsequently broadens readonly permission for this repair: “读读读，别他妈每次都问我，需要读就读读怎么了”. Necessary read-only diagnostics on existing9222/nativeprogramownedstate may proceed without repeatedquestions. Keep noComputerUse/noCookie-token/customerunnecessarycontent/noGooglewrite/purchase/navigation/close/newChrome boundaries; this is not forcekill or externalwrite permission. Onebounded diagnostic read13targetsunchanged, owned2026/SHAHAB/RFQ_BRIEF allready, no activeerrorpage remains. Laternaturalpoll foundone newSHAHAB order; genuine source temporaryResearchfailure becameFAILED afterattempt1, no purchase/saveevents. Never commit itsactualMPN; usewatch-order-2. Thus transientnavigationalone is not wholeGooglefailure, and originalsource misses include separate terminalretryprojection bug.


## Owner 2026-11-06 完整Google读取排查与交叉复审
Owner明确要求完整排查Google读取相关代码并交叉复审；继续原修复、离线回归、受控发布和自然业务观察授权，不重新申请已允许的只读诊断。两名只读内部复审者分别检查原生读取/身份/截止时间与业务准入/持久恢复/通知分类；只用合成依赖，不接生产、不开新执行窗口。完整发现与关闭证据见GOOGLE_READ_CROSS_REVIEW_2026-11-06.md。普通读表不可因报价菜单异常、可恢复读取、日期持久化遗漏或已完成调研后的再次读失败而漏单/永久停轮询；外部写UNKNOWN、身份、权限、旧单、邮件终态保护保留。不能保证外网永不故障，必须准确区分程序读取未完成与已证实网络不可达。COMPUTER_USE_NOT_USED。


## Owner 2026-11-06 consolidated stability repair and explicit important amount correction (IN_PROGRESS)
Owner reports repeated business stops, requests related full-chain audit/cross-review rather than isolated patches, original controlled build/backup/install/start, new and existing eligible order observation. Owner confirms original app exited normally; verified exit event is owner_exit/application_exit_code0. Latest explicit authorization: 修完之后补发正常带金额的重要邮件. Reuse original durable notification queue and SMTP worker only; create one deterministic correction command for the specific original important notice, preserve original SENT/UNKNOWN, no purchase/research replay, final current identity/status/age/trigger/recipient review mandatory. Verify historical recorded amount/time against original frozen basis or specifically verified legacy basis; label historical routing reference versus unavailable current market data. No invented total/current price or stale original notice reopening.
Consolidated scope: native write selection/focus settlement, same-owner protocol deadlines, typed exception/cause preservation through actual Sheets adapter/quotation updater, lost/moved page retention, accurate actual-stop notification independent of last order, notification creation timestamp after research and optional verified decision snapshot. Retain original seven-day/month admission, all UNKNOWN/SENT protections, original scheduling and browser/session/SMTP owners. All test traffic uses fake Sheets/IMAP/CDP/SMTP. COMPUTER_USE_NOT_USED.


Completion of Owner2026-11-06 consolidated increment: 2026-11-06 final controlled release: source92d18b093b2ad6f724dd8268989a66534b392a2c, full3667PASS/1originalWindows permissionSKIP255.12s; Ruff/diff and byte fingerprints PASS. EXE fcdc8b70d0f1d89bc578a942fb479a547385083b623326cf452bb51eaacfad02,2875files/16frozenmodules match. Owner normal exit verified; latest backupD:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.6-stability-bundle-20261106T042044Z;16tables/config unchanged before normal start. GUI29816/original observer24300, Chrome19208/9222 kept. Natural inquiry197.516s/quotation211.047s/TP9.594s allcompleted; one existing procurement reply positively verified native insertion and original source status then original confirm_dispatch closed same new guard; baseline8→9. No manual hold change or rawDB repair. New watched purchase remainsSAVED/one dispatch, no repeat; noquote watch remains original confirmed terminal/no purchase. Original177mailterminal/51intakes/1protectedunknown unchanged, integrityok. Owner-authorized specific amount correction via original queue→SMTP accepted2originalrecipients once each, totalSENT177→179; no extra false alert/duplicates observed. Historical amount/source/time labels, no current market or成交 price claim; actual inbox reading NOT_VERIFIED. All selfchecks0 and final formal+rollback asset hashes/config/code gates PASS. Seventeen owned fake-test dirs and canonical owned stage retired749363004+268159197bytes, protected assets kept; small unique receipts retained. No new production CDP client, ComputerUse, synthetic real mail, purchase replay, schedule change, UNKNOWN clear or DBrestore. BUSINESS_RUNNING for observed cycle; future external availability/long-term stability not guaranteed. Independent IMAP new-message flow/manual GUI not re-exercised this round. COMPUTER_USE_NOT_USED.


## Owner2026-11-09 SHA H A B new-order incident: complete related repair and independent review (IN_PROGRESS)
Owner reports3newSHAHAB orders unprocessed, then explicitly commands comprehensive related code repair and independent review. Same originalExecutor/worktree; preserve all unique history. Currentformal92d/source unchanged, GUI47420/observer64964 alive sinceNov7; last successfulinquiry Nov8 09:13 thenquotation hangs after09:13:33, no later schedulercycle throughNov9 13:25. CentralDBquick_checkok/51items/no newintake sinceNov7. Nonblocking no-locals py-spy shows poller originalSDKdispatcher, workerEventwait, launcherrefresh andGUIalive; exactpendingprotocolmethod NOT_VERIFIED. Three ownedGoogle sourcepages respond immediate readonlymetadata, no activewrite flags.
Reuse originalCLI/program APIs, original9222/profile/outbox; necessary bounded readonly source diagnostics carry Owner standing permission. No Cookie/token, GUI controls, navigation/new/close page, procurement/quotation replay, rawDB edits or UNKNOWN clear. Diagnose3current sourceorders using only MPN/date/status/qty needed; do not commit raw production rows. Independentreviewers restricted toreadonlysource/syntheticoffline, Root handles implementation andlive. Scope includes quotation read path/native client deadlines and callback/lifecycle boundaries, shared poller liveness, accurate prolonged no-progress handling; no parallel scheduler/mail/Chrome or orphaning/canceling unknown writes. Reproduce first; preserve all age/status/identity/permissions/UNKNOWN and source verification. Normal deployment remains original controlled authorization; if liveExit cannotfinish safely, no forcekill without new explicitOwnergrant. COMPUTER_USE_NOT_USED.


Owner2026-11-09 explicit force-exit grant: originalprogram cannotexit; Owner directs Executor to force-exit currentinstance, finish verifiedrepair/originalbuild-backup-program-onlyinstall/start andfollow3neworders. Grant applies only to currentformalGUI PID47420 anditsverifiedrun42e4e87cb42e4fe6afbf761bb1f2fe8c; no Chrome/Profile/unknownrecord manipulation or blanket futureforceauthority. Before termination preserve consistent currentDB/config/runtime evidence; verify exactEXE/processidentity/hash andOwnergrant, terminate only exactGUI PID (not tree/Chrome); originalobserver may exitnormally. Retain abnormal-exittruth; do notforgeowner_exit/code0. Then latestcolddata backup andoriginalprotectedinstallation, notDBrestore.


## Owner 2026-11-09 consolidated outstanding acceptance (IN_PROGRESS)
Last ten exchanges reiterate one task, not ten separate completions: reproduce and repair repeated Google read/recovery stops and missed new intake; repair related purchase-session preparation and diagnostics; investigate actual important-notice delivery and missing detailed report; preserve manual completion of three orders with no procurement replay; independently review related paths; run targeted red/green and full offline regressions; commit tested source; build, backup, program-only install and start via original release; verify two latest real orders against fresh source and durable submission/delivery evidence. Do not stop at findings, partial tests, packaging or GUI startup. No blanket claim of zero unknown bugs. Current HEAD635ddfef remains installed baseline; uncommitted session/diagnostic changes and added tests are NOT_DEPLOYED. Existing SMTP queue, 120s original-notice bound, SENT/UNKNOWN, age/date/status/identity protections stay binding. Live target/status and exact initial preparation-control cause remain NOT_VERIFIED. COMPUTER_USE_NOT_USED.

## Owner follow-up 2026-11-11: task-center status clarity

- Scope: concise list status derived from the latest uniquely matched, fresh source observation; keep processing history and unconfirmed-write warnings available in order details. Correct stale/missing source values and task-center classification without changing Google, procurement, mail, or persisted order state.
- Acceptance: source status is never presented as current when missing, stale, or being refreshed; unknown writes remain visible and block retry; a confirmed customer-quoted state is not obscured by purchase history; compact list, detail, filtering, and sorting remain consistent. Verify with synthetic GUI/source-projection tests; live source contents remain NOT_VERIFIED until a normally authorized read.

## Owner follow-up 2026-11-11: quotation input without observed update

- Owner reports the latest affected order reached the quote-input sheet but the expected update button did not complete the source update; Owner has since updated it manually. Do not replay the order, click the button, clear holds, edit the source, or resend notifications.
- Read-only local evidence: one exact local item has an active QUOTE_INPUT_WRITE_FAILED hold, episode 1, whose source status is a historical observation. The related later notification is MODEL_DIFFERENCE_CONFIRMED; neither the current source state nor the actual button click is proven by that notification. Installed executable bytecode verifies input write and readback precede the protected button click, and default dialog wait is 30 seconds. A reproduced post-click error can nevertheless be mislabeled as input write failure, so do not infer no click from the hold alone.
- Acceptance: protect an armed quotation dispatch against later row-error overwrite, retain idempotency across restart, preserve normal pre-click failure handling and verified successful dispatch, and test a simulated 15-second result delay without a real button click. No raw production records, customer information or prices in tests or logs.


## Owner follow-up 2026-11-12: remove quotation input readback

Owner explicitly directs removal of quotation-input post-write readback, including both workflow and native web adapter checks, so a completed saved input can proceed directly to the update button. The Apps Script performs the source-row update. Preserve source identity/status and input location checks, native write/save errors, dispatch uncertainty protection, popup/result handling and the existing supplier-model difference remark and notice. Other sheets retain their own write verification. Do not replay the manually completed order or send any messages. The actual historical input/readback difference and native click remain UNKNOWN. Verify with offline synthetic tests only; this change explicitly accepts that silent quotation-input corruption will no longer be detected by readback.


## Owner follow-up 2026-11-12: durable Google resource protection

Scope: address protected Google read surfaces and uncertain writes across service instances and application restarts. A resource hold is distinct from an order or notification hold; never reuse the latter's clear/retry rules. Persist only bounded document/target identity, generation, type, and pure-read provenance in the existing workflow database, with a verified pre-migration backup. Restore holds before any browser write can be admitted; storage errors fail closed. A read-only resource hold may be removed only on positive, exact target-identity and settlement/disappearance evidence, with generation-checked compare-and-set and synchronization against writers. Never release an unknown write merely because a page closes or a read hold clears. Do not access production or operate actual pages during tests; use synthetic stores and browser doubles. Scope includes concurrent admission, restart and crash-window tests and full regression before any authorized release. UNKNOWN: whether a protected historical page was taken over or an operation completed when reliable evidence is absent.


## Owner 2026-11-12 morning: repeated Google-triggered global pause

Owner reports manual Google Sheets access remained normal when the application paused. Sanitized local log records a 10:37:57 native sheet-download read timeout, after which that inquiry cycle completed; at 10:41:21 the quotation cycle reported GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED and global fault. This establishes neither a site-wide Google outage nor whether a write actually happened. Offline inspection of the installed baseline reproduced a pure-read protected-page cleanup raising that same write-uncertain code without any write. The morning incident is compatible with that defect, but exact target/operation provenance is UNKNOWN and genuine unknown writes remain protected. Scope: repair only positively proven read-only target recovery and source-to-global-fault classification; cover both next-read and next-write, cross-scope, missing identity, historical write and auth cases. Do not clear existing unknown holds, replay orders, send mail, access live browser, or claim production recovery before verified release and normal operation.


## Owner 2026-11-12: prioritize business continuity

Owner clarifies that necessary existing checks should remain, but over-designed protections must not cause false alarms to stop normal business. This supersedes the experimental durable Google resource ledger and additional global admission gates above. Preserve existing genuine unknown-write and page-identity handling, and do not replay purchase orders or resend mail. Investigate proven read-only recovery failures with synthetic fixtures. Do not deploy until relevant failures are resolved and verification passes. Actual morning target and write outcome remain UNKNOWN.


## Owner 2026-11-12: close program-created failed read pages

Owner expressly permits automatic closure of abnormal Google Sheets pages created by the program after read failure, including the possibility that the Owner later switched to such a page and unsaved activity could be lost. Scope this behavior to an exact program-owned page with confirmed read-only history and a temporary read failure; preserve authentication challenges, uncertain or actual writes, other user pages, and the last browser page. Do not send or replay business transactions. Verify retries, non-owned pages, write uncertainty, authentication, and fallback when cleanup cannot be proved before release.


## Owner 2026-11-12: quotation result popup timeout

After dispatching Update Quotation, wait up to 60 seconds for the result popup. If it does not appear, skip the affected order, notify only 229 through the existing notification mechanism, and allow other business work to continue; do not re-click the uncertain update or resend historical messages. Do not infer success or failure from the absence of a popup. Use synthetic tests only, with no real email or production order changes.


## Owner 2026-11-12: purchase failure diagnosis logging

Add actionable local diagnostics for future INSO purchase-entry failures. Record the exact internal step, a fixed non-sensitive cause code and safe source location where available, and the precise pre/post-login recovery status. Never log credentials, page text, customer/order values or arbitrary exception messages. Keep purchase behavior unchanged; use synthetic tests and do not send mail, replay orders, or touch live pages. The cause of the latest real failure remains UNKNOWN because the installed version retained only SecurityViolation and SESSION_STALE.


## Owner 2026-11-12: requested program replacement after normal exit

Owner states the old program has exited and requests program replacement and launch if there are no other problems. Owner previously explicitly chose not to repair the 26 outstanding special-case test failures and requested only normal-order checks, and requested the purchase-failure logging addition after the real incident. Known limits remain: normal paths were tested offline; the latest actual INSO purchase exception is not root-caused, 26 historical/global-barrier tests still fail, and actual production acceptance remains UNKNOWN. Prepare and verify a consistent database/config/program backup, preserve runtime junction and state, never replay manually completed orders or resend historic mail, and use the original one-instance controlled installation and normal launch if the release checks establish no additional blocker.
