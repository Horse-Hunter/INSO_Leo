# RFQ-016 subtask: detailed mail research and independent IMAP

Status: REVIEW_REQUIRED / NOT_DEPLOYED / SECURITY_ENABLEMENT_BLOCKED (real IMAP commands). Final second-review source `1dd31b283ec34126637e173830dbc3c321b7c89d`;3354PASS/1SKIP,20new cases,31final targeted. Evidence: `control-room/RFQ-016/TEST_REPORT.json`. Prior3334tests retained; A/B/C not rewritten. Production remains NOT_VERIFIED. Requirements: original Owner attachment and CEO50dfe3d.

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
