# Research 模块

## RFQ-003 来源故障隔离（2026-10-07）

复用 ResearchService 和现有全部 adapters；聚合/价格算法不变。
生产组合注入 typed source observer / query recovery，不新增第二套调研。
IC.net 不可用暂停 V1.2；INSO 认证立即全局停止，历史查询失败按 fresh-tab
初次加三次重试恢复；其他来源超时/登录/验证只记该来源失败，继续其余来源。
人工登录/验证提醒仍走既有通知账本至 Owner 229。无报价仍保持真实无报价，
Workflow V1.2 将本行调研失败安全终结而非自动重跑；重要/重复通知规则不变。
共享 CDP 有限恢复失败必须向上抛 GLOBAL_STOP，不能被可选来源降格吞掉。

## Public Contract

入口：`ResearchService.execute(ResearchInput) -> ResearchResult`。

- Input：`inquiry_id`、`mpn`、可选 `brand`、`quantity`、`importance_raw`。
- Status：`SUCCESS | PARTIAL_SUCCESS | EXCEPTION | RETRYABLE_FAILURE`。
- Research 不决定采购类型、通知资格或 V1.2 路由。

## 来源

IC.net 只用于 Brand 与货量，不是价格源。价格源为 Findchips、HQEW、LCSC、Bom.Ai、INSO。

- IC.net：严格 MPN；库存只统计严格匹配且带 SSCP/ICCP 标识的行。无合格库存或总量 `<= 3 × quantity` → `货少`；否则 `货多`。技术失败 → `待验证`，不得当作零。
- Findchips：读取可见价格档位；分别保留有库存/无库存最低价。
- Findchips 明确空结果页：已核证 `p.alert.alert-info.no-results` 的完整文本
  `No results were found for <当前型号>.` 是正常无结果，即便没有报价表格。
  必须与当前型号一致；空白页、普通文本、脚本中的提示、登录页或错误页不能据此判空。
  表格记录与空结果标记并存按冲突报错。继续复用原有 source outcome/聚合规则。
- HQEW：只读目标型号历史市场报价，最近 1 个自然月最低价。
- LCSC：取已展示最低 unit price，分别保留有库存/无库存最低价。
- Bom.Ai：只读目标型号报价区域，最近 1 个自然月最低价。
- INSO：只读历史询价“供方未税价”；先 1 个自然月，无有效价再扩大到 2、3 个自然月。

Findchips/HQEW/LCSC/Bom.Ai 的型号比较按现有 canonical normalization；禁止模糊猜测变体。INSO Research 复用 launcher 提供的 authenticated `InsoOperationAccess`，不得自行枚举/接管任意浏览器页面。

## FX 与聚合

USD/RMB、HKD/RMB 使用同日 ECB reference；缺失、重复、日期不一致、非正数或非有限值均 fail closed。

正常价格池：
- Findchips 有库存最低价
- HQEW 最低价
- LCSC 有库存最低价
- Bom.Ai 最低价
- INSO 最低价

统一 RMB 后取最低价作为市场最低参考价，乘 quantity 得预估订单总价。仅无库存价格可在所有正常来源均无有效价时作为兜底，并返回 `PARTIAL_SUCCESS`。

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
`型号 | 品牌 | 数量 | 重要等级 | 货量标识 | 预估订单总价 | 市场最低参考价 | INSO | Findchips | 华强 | 立创 | 正能量 | 备注 | 处理时间`

隐藏 `_inquiry_id` 用于幂等，隐藏 `_research_status` 保存结果状态。Excel load/schema/save 失败 → `RETRYABLE_FAILURE`。技术失败详情只进备注，不伪装成业务“无结果”。

## 边界

Research 只做调研与本地 Excel 持久化；不读写 Google Sheets，不执行主动采购，不决定 V1.2 通知/采购业务规则。Credential 只走 Core Provider。普通 browser/session readiness 复用共享 runtime；CAPTCHA/OTP/设备验证才需要人工。

Owner 2026-10-08: all source MPN filtering now delegates to core.mpn.lookup_mpn_matches; native query URLs use lookup_mpn_prefix exactly once, result parsers retain the full original target. INSO history records retain observed PartNo for filtering/evidence; records without an observed model cannot supply a price. Existing source-specific windows/stock/price rules remain. Research native first-page coverage limits remain unchanged.
